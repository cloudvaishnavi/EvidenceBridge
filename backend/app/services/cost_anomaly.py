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
    def detect_currency(cost_str: Optional[str], text: str = "", location_str: str = "") -> str:
        """
        Detect currency code (INR, USD, EUR, GBP) from cost range string,
        document text, and geographic location context.
        Rules:
          - If source text clearly contains $ or USD, keep it as USD.
          - If source text contains ₹, Rs, INR, or no currency symbol (and context is Indian), use INR.
          - If source text contains € / EUR -> EUR.
          - If source text contains £ / GBP -> GBP.
          - Otherwise defaults to USD.
        """
        cost_lower = (cost_str or "").lower()
        text_lower = (text or "").lower()
        loc_lower = (location_str or "").lower()
        combined = f"{cost_lower} {text_lower} {loc_lower}"

        # 1. Explicit EUR / GBP in cost or text
        if "€" in cost_lower or "eur" in cost_lower or "euro" in cost_lower:
            return "EUR"
        if "£" in cost_lower or "gbp" in cost_lower or "pound" in cost_lower:
            return "GBP"

        # 2. Check cost string for $ vs ₹
        has_usd_symbol = "$" in cost_lower or "usd" in cost_lower or "dollars" in cost_lower or "dollar" in cost_lower
        has_inr_symbol = (
            "₹" in cost_lower
            or "rs." in cost_lower
            or "rs " in cost_lower
            or "rs:" in cost_lower
            or "inr" in cost_lower
            or "rupees" in cost_lower
            or "rupee" in cost_lower
            or "lakh" in cost_lower
            or "crore" in cost_lower
        )

        if has_usd_symbol and not has_inr_symbol:
            return "USD"
        if has_inr_symbol and not has_usd_symbol:
            return "INR"

        # 3. Check document text for explicit currency
        if "$" in text_lower or "usd" in text_lower:
            if not ("₹" in text_lower or "inr" in text_lower or "rs." in text_lower or "rupees" in text_lower):
                return "USD"

        if "₹" in text_lower or "inr" in text_lower or "rs." in text_lower or "rupees" in text_lower:
            return "INR"

        # 4. No currency symbol in cost_str or text: check if context is Indian
        indian_context_indicators = {
            "india", "karnataka", "bengaluru", "bangalore", "ballari", "bellary", "davangere",
            "hubballi", "hubli", "dharwad", "mysuru", "mysore", "mangaluru", "mangalore",
            "belagavi", "belgaum", "shivamogga", "shimoga", "delhi", "mumbai", "bombay",
            "hyderabad", "chennai", "madras", "kolkata", "calcutta", "pune", "ahmedabad",
            "jaipur", "lucknow", "chandigarh", "bhopal", "patna", "kerala", "tamil nadu",
            "andhra", "telangana", "maharashtra", "gujarat", "rajasthan", "uttar pradesh",
            "apollo", "fortis", "manipal", "narayana", "aiims", "nimhans", "vims", "ssims",
            "chigateri", "kims", "cghs", "pmjay", "nppa", "ayushman"
        }
        if any(re.search(r"\b" + re.escape(w) + r"\b", combined) for w in indian_context_indicators):
            return "INR"

        if "€" in text_lower or "eur" in text_lower:
            return "EUR"
        if "£" in text_lower or "gbp" in text_lower:
            return "GBP"

        # 5. Check if document has explicit foreign location context
        foreign_context_indicators = {
            "usa", "united states", "atlanta", "georgia", "chicago", "illinois", "cleveland", "ohio",
            "houston", "texas", "san francisco", "california", "boston", "massachusetts", "new york",
            "seattle", "washington", "miami", "florida", "dallas", "los angeles", "uk", "london"
        }
        if any(re.search(r"\b" + re.escape(w) + r"\b", combined) for w in foreign_context_indicators):
            return "USD"

        # 6. Default fallback across the application: prefer INR (₹)
        return "INR"

    @staticmethod
    def extract_numeric_cost(cost_str: Optional[str]) -> Optional[float]:
        """
        Extract primary numeric value from a cost range string across currencies (USD, INR, EUR, GBP).
        Examples:
            '$4,850.00' -> 4850.0
            '₹45,000' -> 45000.0
            'Rs. 1,200.00' -> 1200.0
            '$148.00 ($74.00 per tablet)' -> 148.0
            '$980 per month' -> 980.0
            '$4,500 - $6,000' -> 6000.0 (uses upper range)
            'total billed charge: 720.00 USD' -> 720.0
            '1,250 USD' -> 1250.0
            'amount: 850' -> 850.0
            '720.00' -> 720.0
        """
        if not cost_str or not isinstance(cost_str, str):
            return None

        # 1. Look for currency symbols ($, ₹, €, £) followed by digits
        matches = re.findall(r"[\$₹€£]\s*([\d,]+(?:\.\d{1,2})?)", cost_str)

        # 2. Look for Rs. / INR / USD / EUR / GBP followed by digits
        if not matches:
            matches = re.findall(r"(?:rs\.?|inr|usd|eur|gbp)\s*([\d,]+(?:\.\d{1,2})?)", cost_str, re.IGNORECASE)

        # 3. Number followed by currency code/word (e.g. 1,250 USD, 50,000 INR, 720 dollars, 1200 rupees)
        if not matches:
            matches = re.findall(r"\b([\d,]+(?:\.\d{1,2})?)\s*(?:USD|INR|EUR|GBP|dollars?|rupees?|euros?|pounds?)\b", cost_str, re.IGNORECASE)

        # 4. Currency/billing keywords preceding number (e.g. total: 1,250, charge 720.00, billed 850)
        if not matches:
            matches = re.findall(r"(?:USD|INR|cost|charge|billed|total|amount|fee|price)\s*[:=]?\s*([\d,]+(?:\.\d{1,2})?)", cost_str, re.IGNORECASE)

        # 5. Pure numeric string fallback (e.g. "720" or "1,250.00")
        if not matches:
            matches = re.findall(r"^\s*([\d,]+(?:\.\d{1,2})?)\s*$", cost_str)

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

    def find_matching_benchmark(
        self,
        entity: str,
        text: str = "",
        preferred_currency: Optional[str] = None,
    ) -> Optional[CostBenchmark]:
        """
        Find best matching price benchmark for a medical entity or procedure.
        Prioritizes:
          1. Exact CPT/HCPCS code match in entity (currency-aligned if available)
          2. Exact CPT/HCPCS code match in text (filtered by relevance to entity)
          3. Entity title and keyword relevance scoring with anatomical validation
        """
        entity_lower = entity.lower().strip()
        text_lower = text.lower().strip()
        code_pattern = re.compile(r"\b(?:[A-Z]\d{4}|\d{5})\b", re.IGNORECASE)

        # 1. Priority: CPT/HCPCS code present in entity itself
        entity_codes = {c.upper() for c in code_pattern.findall(entity_lower)}
        if entity_codes:
            matched_bms = [bm for bm in self.benchmarks if bm.cpt_code and bm.cpt_code.upper() in entity_codes]
            if matched_bms:
                if preferred_currency:
                    curr_matched = [bm for bm in matched_bms if bm.currency == preferred_currency]
                    if curr_matched:
                        return curr_matched[0]
                return matched_bms[0]

        # 2. Priority: CPT/HCPCS code in text, provided it aligns with the entity
        text_codes = {c.upper() for c in code_pattern.findall(text_lower)}
        if text_codes:
            candidate_bms = [bm for bm in self.benchmarks if bm.cpt_code and bm.cpt_code.upper() in text_codes]
            aligned_bms = []
            for bm in candidate_bms:
                bm_words = set(re.findall(r"\w+", bm.entity.lower()))
                entity_words = set(re.findall(r"\w+", entity_lower))
                if bm_words & entity_words - {"cpt", "without", "with", "oral", "tablet", "procedure"}:
                    aligned_bms.append(bm)
            if aligned_bms:
                if preferred_currency:
                    curr_aligned = [bm for bm in aligned_bms if bm.currency == preferred_currency]
                    if curr_aligned:
                        return curr_aligned[0]
                return aligned_bms[0]

        # 3. Match by entity name & keywords with scoring
        best_match: Optional[CostBenchmark] = None
        highest_score = 0

        # Anatomical conflict check between entity and benchmark
        try:
            from app.services.verification import ANATOMICAL_REGIONS
            entity_regions = {
                region for region, keywords in ANATOMICAL_REGIONS.items()
                if any(re.search(r"\b" + re.escape(kw) + r"\b", entity_lower) for kw in keywords)
            }
        except ImportError:
            entity_regions = set()
            ANATOMICAL_REGIONS = {}

        for bm in self.benchmarks:
            bm_entity_lower = bm.entity.lower()
            bm_regions = {
                region for region, keywords in ANATOMICAL_REGIONS.items()
                if any(re.search(r"\b" + re.escape(kw) + r"\b", bm_entity_lower) for kw in keywords)
            }
            # Reject if there is a direct anatomical conflict (e.g. brain vs knee)
            if entity_regions and bm_regions and not (entity_regions & bm_regions):
                continue

            score = 0
            # Exact or substring match in entity
            if bm_entity_lower in entity_lower or entity_lower in bm_entity_lower:
                score += 15

            # Significant keyword overlap in entity
            for kw in bm.keywords:
                kw_lower = kw.lower()
                if re.search(r"\b" + re.escape(kw_lower) + r"\b", entity_lower):
                    score += 6
                elif re.search(r"\b" + re.escape(kw_lower) + r"\b", text_lower):
                    score += 2

            # Overlap with benchmark entity words
            bm_tokens = set(re.findall(r"\w+", bm_entity_lower)) - {"without", "with", "cpt", "per", "the", "and"}
            entity_tokens = set(re.findall(r"\w+", entity_lower)) - {"without", "with", "cpt", "per", "the", "and"}
            token_overlap = len(bm_tokens & entity_tokens)
            score += token_overlap * 3

            # Preferred currency bonus to align same-currency benchmarks (only if entity/text matched)
            if score > 0 and preferred_currency and bm.currency == preferred_currency:
                score += 8

            if score > highest_score and score >= 4:
                highest_score = score
                best_match = bm

        return best_match

    def evaluate_claim_cost(self, claim: Claim) -> CostAnomalyDetails:
        """
        Evaluate claim's cost_range against local price benchmarks.
        Returns CostAnomalyDetails indicating if the claim is a flagged anomaly.
        Preserves original document currency (INR, USD, EUR, GBP) and reports
        benchmark range and currency with strict transparency.
        """
        cost_str = claim.extracted_fields.cost_range
        loc_str = ""
        if claim.location and claim.location.city:
            loc_str = f"{claim.location.city} {claim.location.state_or_region or ''}"
        elif claim.extracted_fields.location_city:
            loc_str = claim.extracted_fields.location_city

        claim_currency = self.detect_currency(cost_str, claim.original_text, loc_str)
        extracted_amount = self.extract_numeric_cost(cost_str)
        entity = claim.extracted_fields.entity

        # Synchronize detected currency to extracted_fields if not explicitly set
        if claim.extracted_fields.cost_currency is None and cost_str:
            claim.extracted_fields.cost_currency = claim_currency

        benchmark = self.find_matching_benchmark(entity, claim.original_text, preferred_currency=claim_currency)
        curr_symbol = "₹" if claim_currency == "INR" else ("€" if claim_currency == "EUR" else ("£" if claim_currency == "GBP" else "$"))

        if extracted_amount is None:
            explanation = "No numeric cost figure identified in claim for anomaly auditing."
            if benchmark:
                bm_symbol = "₹" if benchmark.currency == "INR" else ("€" if benchmark.currency == "EUR" else ("£" if benchmark.currency == "GBP" else "$"))
                explanation += f" Matched benchmark reference: '{benchmark.entity}' ({bm_symbol}{benchmark.typical_min:,.2f} - {bm_symbol}{benchmark.typical_max:,.2f} {benchmark.currency} {benchmark.unit or ''})."
            return CostAnomalyDetails(
                is_anomaly=False,
                benchmark_matched=bool(benchmark is not None),
                currency=claim_currency,
                benchmark_currency=benchmark.currency if benchmark else None,
                threshold_multiplier=self.threshold_multiplier,
                explanation=explanation,
                benchmark_name=benchmark.entity if benchmark else None,
                benchmark_source=benchmark.source if benchmark else None,
                cpt_code=benchmark.cpt_code if benchmark else None,
                benchmark_min=benchmark.typical_min if benchmark else None,
                benchmark_max=benchmark.typical_max if benchmark else None,
            )

        if not benchmark:
            return CostAnomalyDetails(
                is_anomaly=False,
                benchmark_matched=False,
                currency=claim_currency,
                benchmark_currency=None,
                extracted_amount=extracted_amount,
                threshold_multiplier=self.threshold_multiplier,
                explanation=f"No public pricing benchmark found for entity '{entity}'. Auditing deferred.",
                benchmark_name=None,
                benchmark_source=None,
                cpt_code=None,
            )

        # Compare against benchmark range
        b_min = benchmark.typical_min
        b_max = benchmark.typical_max
        bm_symbol = "₹" if benchmark.currency == "INR" else ("€" if benchmark.currency == "EUR" else ("£" if benchmark.currency == "GBP" else "$"))

        # Guard against comparing different currencies directly without verified exchange rate
        if benchmark.currency != claim_currency:
            return CostAnomalyDetails(
                is_anomaly=False,
                benchmark_matched=True,
                currency=claim_currency,
                benchmark_currency=benchmark.currency,
                extracted_amount=extracted_amount,
                benchmark_min=b_min,
                benchmark_max=b_max,
                threshold_multiplier=self.threshold_multiplier,
                severity="none",
                explanation=(
                    f"Billed amount of {curr_symbol}{extracted_amount:,.2f} ({claim_currency}) noted. "
                    f"Matched benchmark '{benchmark.entity}' is published in {benchmark.currency} "
                    f"({bm_symbol}{b_min:,.2f} - {bm_symbol}{b_max:,.2f}, source: {benchmark.source}). "
                    f"Cross-currency comparison noted: billed currency ({claim_currency}) differs from benchmark schedule currency ({benchmark.currency}). "
                    f"Direct markup auditing deferred to avoid inaccurate alerts."
                ),
                benchmark_name=benchmark.entity,
                benchmark_source=benchmark.source,
                cpt_code=benchmark.cpt_code,
            )

        # Normal within benchmark
        if extracted_amount <= b_max:
            multiplier = round(extracted_amount / b_max, 2) if b_max > 0 else 1.0
            return CostAnomalyDetails(
                is_anomaly=False,
                benchmark_matched=True,
                currency=claim_currency,
                benchmark_currency=benchmark.currency,
                extracted_amount=extracted_amount,
                benchmark_min=b_min,
                benchmark_max=b_max,
                multiplier=multiplier,
                threshold_multiplier=self.threshold_multiplier,
                severity="none",
                explanation=(
                    f"Billed amount of {curr_symbol}{extracted_amount:,.2f} ({claim_currency}) falls within or below typical benchmark "
                    f"({curr_symbol}{b_min:,.2f} - {curr_symbol}{b_max:,.2f} {claim_currency} {benchmark.unit or ''}, source: {benchmark.source})."
                ),
                benchmark_name=benchmark.entity,
                benchmark_source=benchmark.source,
                cpt_code=benchmark.cpt_code,
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
                f"COST ANOMALY DETECTED: Billed amount of {curr_symbol}{extracted_amount:,.2f} ({claim_currency}) is {multiplier:.1f}× higher "
                f"than the benchmark maximum of {curr_symbol}{b_max:,.2f} ({claim_currency}) "
                f"(typical range: {curr_symbol}{b_min:,.2f} - {curr_symbol}{b_max:,.2f} {claim_currency} {benchmark.unit or ''}, "
                f"threshold: {self.threshold_multiplier}×, source: {benchmark.source})."
            )
            logger.warning(f"Claim {claim.claim_id}: {explanation}")
        else:
            explanation = (
                f"Billed amount of {curr_symbol}{extracted_amount:,.2f} ({claim_currency}) exceeds typical maximum of {curr_symbol}{b_max:,.2f} ({claim_currency}) "
                f"({multiplier:.1f}×), but remains below the anomaly threshold multiplier of {self.threshold_multiplier}×."
            )

        return CostAnomalyDetails(
            is_anomaly=is_anomaly,
            benchmark_matched=True,
            currency=claim_currency,
            benchmark_currency=benchmark.currency,
            extracted_amount=extracted_amount,
            benchmark_min=b_min,
            benchmark_max=b_max,
            multiplier=multiplier,
            threshold_multiplier=self.threshold_multiplier,
            severity=severity,
            explanation=explanation,
            benchmark_name=benchmark.entity,
            benchmark_source=benchmark.source,
            cpt_code=benchmark.cpt_code,
        )


cost_anomaly_service = CostAnomalyService()
