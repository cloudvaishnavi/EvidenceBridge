"""
Cost Anomaly Detection Service for EvidenceBridge.
Compares extracted claim costs against local public pricing benchmarks
(CMS Medicare, FAIR Health, NADAC, Healthcare Bluebook).
Flags extreme markups and out-of-range hospital bill items.
"""

import json
from pathlib import Path
import re
from typing import Optional

from app.config import get_settings
from app.models.schemas import Claim, CostAnomalyDetails, CostBenchmark
from app.utils.logger import logger


class CostAnomalyService:
    """Service to evaluate healthcare claims against known price benchmarks."""

    def __init__(self, benchmarks_file: Optional[Path] = None):
        self.settings = get_settings()
        self.benchmarks_file = benchmarks_file or self._resolve_benchmarks_path()
        self.threshold_multiplier = self.settings.COST_ANOMALY_THRESHOLD_MULTIPLIER
        self.benchmarks: list[CostBenchmark] = []
        self.load_benchmarks()

    def _resolve_benchmarks_path(self) -> Path:
        """Locate price_benchmarks.json searching relative paths."""
        candidates = [
            Path(self.settings.KNOWLEDGE_BASE_DIR) / "price_benchmarks.json",
            Path(__file__).parent.parent.parent.parent / "data" / "knowledge" / "price_benchmarks.json",
            Path("./data/knowledge/price_benchmarks.json"),
            Path("../data/knowledge/price_benchmarks.json"),
        ]
        for path in candidates:
            if path.exists():
                return path.resolve()
        # Fallback default
        return Path("./data/knowledge/price_benchmarks.json")

    def load_benchmarks(self) -> None:
        """Load benchmark pricing dataset from local JSON file."""
        if not self.benchmarks_file.exists():
            logger.warning(f"Price benchmarks file not found at: {self.benchmarks_file}")
            return

        try:
            with open(self.benchmarks_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.benchmarks = [CostBenchmark.model_validate(item) for item in data]
            logger.info(f"Loaded {len(self.benchmarks)} pricing benchmarks from {self.benchmarks_file.name}")
        except Exception as e:
            logger.error(f"Failed to load price benchmarks: {e}")

    @staticmethod
    def extract_numeric_cost(cost_str: Optional[str]) -> Optional[float]:
        """
        Extract primary numeric dollar value from a cost range string.
        Examples:
            '$4,850.00' -> 4850.0
            '$148.00 ($74.00 per tablet)' -> 148.0
            '$980 per month' -> 980.0
            '$4,500 - $6,000' -> 6000.0 (uses upper range)
        """
        if not cost_str or not isinstance(cost_str, str):
            return None

        # Look for dollar amounts with optional commas and decimals
        matches = re.findall(r"\$\s*([\d,]+(?:\.\d{1,2})?)", cost_str)
        if not matches:
            # Check for naked numbers with currency context
            matches = re.findall(r"(?:USD|cost|charge|billed|total)\s*[:=]?\s*([\d,]+(?:\.\d{1,2})?)", cost_str, re.IGNORECASE)

        if not matches:
            return None

        values = []
        for m in matches:
            clean_num = m.replace(",", "").strip()
            try:
                values.append(float(clean_num))
            except ValueError:
                continue

        if not values:
            return None

        # Return the maximum figure mentioned (e.g. for ranges like $4,500 - $6,000, evaluates upper bound)
        return max(values)

    def find_matching_benchmark(self, entity: str, text: str = "") -> Optional[CostBenchmark]:
        """
        Find best matching price benchmark for a medical entity or procedure.
        Matches via CPT codes, keywords, or entity name substrings.
        """
        combined = f"{entity} {text}".lower()

        # 1. Match by CPT code if present
        for bm in self.benchmarks:
            if bm.cpt_code and bm.cpt_code.lower() in combined:
                return bm

        # 2. Match by keywords
        best_match: Optional[CostBenchmark] = None
        highest_score = 0

        for bm in self.benchmarks:
            score = 0
            # Entity name match
            if bm.entity.lower() in combined or entity.lower() in bm.entity.lower():
                score += 5

            # Keyword matches
            for kw in bm.keywords:
                if kw.lower() in combined:
                    score += 2

            if score > highest_score and score >= 2:
                highest_score = score
                best_match = bm

        return best_match

    def evaluate_claim_cost(self, claim: Claim) -> CostAnomalyDetails:
        """
        Evaluate claim's cost_range against local price benchmarks.
        Returns CostAnomalyDetails indicating if the claim is a flagged anomaly.
        """
        cost_str = claim.extracted_fields.cost_range
        extracted_amount = self.extract_numeric_cost(cost_str)

        if extracted_amount is None:
            return CostAnomalyDetails(
                is_anomaly=False,
                threshold_multiplier=self.threshold_multiplier,
                explanation="No numeric cost figure identified in claim for anomaly auditing."
            )

        entity = claim.extracted_fields.entity
        benchmark = self.find_matching_benchmark(entity, claim.original_text)

        if not benchmark:
            return CostAnomalyDetails(
                is_anomaly=False,
                extracted_amount=extracted_amount,
                threshold_multiplier=self.threshold_multiplier,
                explanation=f"No public pricing benchmark found for entity '{entity}'. Auditing deferred."
            )

        # Compare against benchmark range
        b_min = benchmark.typical_min
        b_max = benchmark.typical_max

        # Normal within benchmark
        if extracted_amount <= b_max:
            return CostAnomalyDetails(
                is_anomaly=False,
                extracted_amount=extracted_amount,
                benchmark_min=b_min,
                benchmark_max=b_max,
                multiplier=round(extracted_amount / b_max, 2) if b_max > 0 else 1.0,
                threshold_multiplier=self.threshold_multiplier,
                severity="none",
                explanation=(
                    f"Billed amount of ${extracted_amount:,.2f} falls within or below typical benchmark "
                    f"(${b_min:,.2f} - ${b_max:,.2f} {benchmark.unit or ''}, source: {benchmark.source})."
                )
            )

        # Cost exceeds typical maximum: calculate markup multiplier
        multiplier = round(extracted_amount / b_max, 2) if b_max > 0 else 1.0
        is_anomaly = multiplier >= self.threshold_multiplier

        if multiplier >= 10.0:
            severity = "extreme"
        elif multiplier >= 5.0:
            severity = "severe"
        elif is_anomaly:
            severity = "moderate"
        else:
            severity = "none"

        if is_anomaly:
            explanation = (
                f"COST ANOMALY DETECTED: Billed amount of ${extracted_amount:,.2f} is {multiplier:.1f}× higher "
                f"than the benchmark maximum of ${b_max:,.2f} "
                f"(typical range: ${b_min:,.2f} - ${b_max:,.2f} {benchmark.unit or ''}, "
                f"threshold: {self.threshold_multiplier}×, source: {benchmark.source})."
            )
            logger.warning(f"Claim {claim.claim_id}: {explanation}")
        else:
            explanation = (
                f"Billed amount of ${extracted_amount:,.2f} exceeds typical maximum of ${b_max:,.2f} "
                f"({multiplier:.1f}×), but remains below the anomaly threshold multiplier of {self.threshold_multiplier}×."
            )

        return CostAnomalyDetails(
            is_anomaly=is_anomaly,
            extracted_amount=extracted_amount,
            benchmark_min=b_min,
            benchmark_max=b_max,
            multiplier=multiplier,
            threshold_multiplier=self.threshold_multiplier,
            severity=severity,
            explanation=explanation
        )


cost_anomaly_service = CostAnomalyService()
