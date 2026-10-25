"""
Hyperlocal Trust Density Service for EvidenceBridge.
Calculates geographic trust scores, aggregates cost anomaly density, computes recency-weighted activity,
and synthesizes actionable location-level audit insights.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import logging
import math
from typing import Any, Optional

from app.config import get_settings
from app.models.schemas import (
    Claim,
    LocationInsight,
    TrustDensityMetrics,
    TrustTier,
    VerificationAction,
    VerificationResult,
    VerificationVerdict,
)

logger = logging.getLogger(__name__)


class TrustDensityService:
    """Computes, updates, and synthesizes hyperlocal trust density and risk metrics."""

    def __init__(
        self,
        support_weight: float | None = None,
        anomaly_weight: float | None = None,
        volume_weight: float | None = None,
        min_volume: int | None = None,
        time_decay_days: float | None = None,
    ) -> None:
        _settings = get_settings()
        self.w_support = support_weight if support_weight is not None else _settings.TRUST_DENSITY_SUPPORT_WEIGHT
        self.w_anomaly = anomaly_weight if anomaly_weight is not None else _settings.TRUST_DENSITY_ANOMALY_WEIGHT
        self.w_volume = volume_weight if volume_weight is not None else _settings.TRUST_DENSITY_VOLUME_WEIGHT
        self.min_volume = max(1, min_volume if min_volume is not None else _settings.TRUST_DENSITY_MIN_VOLUME)
        self.time_decay_days = max(1.0, time_decay_days if time_decay_days is not None else _settings.TRUST_DENSITY_TIME_DECAY_DAYS)

    def calculate_metrics(
        self,
        location_key: str,
        city: str,
        state_or_region: Optional[str],
        claims: list[Claim],
        verifications: list[VerificationResult],
    ) -> tuple[TrustDensityMetrics, LocationInsight]:
        """
        Pure calculation function: computes TrustDensityMetrics and LocationInsight
        from a list of claims and corresponding verification results for a location.

        Formulas & Definitions:
        -----------------------
        1. Conclusive Support Ratio (support_ratio):
           support_ratio = (supported_count + 0.5 * partially_supported_count) / eval_conclusive
           where eval_conclusive = supported_count + partially_supported_count + contradicted_count.
           If eval_conclusive == 0 (e.g. all claims abstained or no verified claims), support_ratio = 0.0.
           Abstained claims (INSUFFICIENT_EVIDENCE) are excluded from the denominator to avoid treating
           lack of local guideline coverage as evidence of clinical contradiction.

        2. Cost Anomaly Rate (cost_anomaly_rate):
           cost_anomaly_rate = cost_anomaly_count / verified_claims (0.0 if verified_claims == 0).

        3. Recency-Weighted Volume (recency_volume):
           For each claim i with timestamp t_i:
             delta_days = max(0.0, (now_utc - t_i).total_seconds()) / 86400.0
             weight_i = exp(-delta_days / time_decay_days)
             recency_volume = sum(weight_i)
           volume_factor = min(1.0, recency_volume / min_volume)
           Where time_decay_days = 45.0 (decay constant tau; half-life t_half = tau * ln(2) ~= 31.19 days),
           and min_volume = 5 claims.

        4. Composite Density Score (density_score):
           raw_density = (
               w_support * support_ratio
               + w_anomaly * (1.0 - cost_anomaly_rate)
               + w_volume * volume_factor
           )
           Clamped strictly to [0.0, 1.0], rounded to 4 decimals.
           Default weights: w_support = 0.45, w_anomaly = 0.35, w_volume = 0.20.
           If verified_claims == 0, density_score evaluates strictly to 0.0.

        5. Trust Tier Thresholds:
           - verified_claims < 2: INSUFFICIENT_DATA
           - (cost_anomaly_rate >= 0.50 and cost_anomaly_count >= 2) or (density_score < 0.30 and flagged_count >= 2): CRITICAL_ALERT
           - density_score >= 0.75: HIGH
           - density_score >= 0.50: MODERATE
           - otherwise: LOW
        """
        # Total ingested claims vs total claims evaluated by the verification audit pipeline
        total_claims = len(claims)
        verified_claims = len(verifications)

        supported_count = 0
        partially_supported_count = 0
        contradicted_count = 0
        flagged_count = 0
        abstained_count = 0
        cost_anomaly_count = 0

        anomalous_entities: list[str] = []
        all_entities: list[str] = []

        # Map claim_id to claim for entity lookups
        claim_map = {c.claim_id: c for c in claims}

        for c in claims:
            entity = c.extracted_fields.entity.strip()
            if entity:
                all_entities.append(entity)

        for v in verifications:
            if v.action == VerificationAction.ACCEPT or v.verdict == VerificationVerdict.SUPPORTED:
                supported_count += 1
            elif v.verdict == VerificationVerdict.PARTIALLY_SUPPORTED:
                partially_supported_count += 1
            elif v.verdict == VerificationVerdict.CONTRADICTED:
                contradicted_count += 1

            if v.action == VerificationAction.FLAG:
                flagged_count += 1
            elif v.action == VerificationAction.ABSTAIN:
                abstained_count += 1

            if v.cost_anomaly_flag:
                cost_anomaly_count += 1
                matched_claim = claim_map.get(v.claim_id)
                if matched_claim:
                    anomalous_entities.append(matched_claim.extracted_fields.entity.strip())

        # 1. Conclusive Support Ratio:
        # Measures the proportion of conclusive clinical audits that support the claim.
        # Conclusive audits = (supported + partially_supported + contradicted).
        # Abstained claims (INSUFFICIENT_EVIDENCE) are excluded from the denominator
        # because lack of local guideline coverage is not clinical contradiction.
        # However, if there are NO conclusive evaluations (eval_conclusive == 0),
        # the ratio is strictly 0.0 (never default to 0.5 when supported is 0).
        eval_conclusive = supported_count + partially_supported_count + contradicted_count
        if eval_conclusive > 0:
            support_ratio = (supported_count + 0.5 * partially_supported_count) / eval_conclusive
        else:
            support_ratio = 0.0

        # 2. Cost anomaly rate
        if verified_claims > 0:
            cost_anomaly_rate = cost_anomaly_count / verified_claims
        else:
            cost_anomaly_rate = 0.0

        # 3. Recency-weighted volume calculation using exponential decay
        now = datetime.now(timezone.utc)
        recency_volume = 0.0
        for c in claims:
            # Ensure claim timestamp is offset-aware UTC
            claim_time = c.timestamp
            if claim_time.tzinfo is None:
                claim_time = claim_time.replace(tzinfo=timezone.utc)
            delta_seconds = max(0.0, (now - claim_time).total_seconds())
            delta_days = delta_seconds / 86400.0
            weight = math.exp(-delta_days / self.time_decay_days)
            recency_volume += weight

        volume_factor = min(1.0, recency_volume / self.min_volume)

        # 4. Composite Density Score (0.0 to 1.0)
        # Higher score = stronger clinical support, fewer cost anomalies, higher verified volume.
        # If zero claims have completed verification audit, score is 0.0.
        if verified_claims == 0:
            density_score = 0.0
        else:
            raw_density = (
                self.w_support * support_ratio
                + self.w_anomaly * (1.0 - cost_anomaly_rate)
                + self.w_volume * volume_factor
            )
            density_score = round(max(0.0, min(1.0, raw_density)), 4)

        # 5. Determine Categorical Trust Tier
        if verified_claims < 2:
            trust_tier = TrustTier.INSUFFICIENT_DATA
        elif (cost_anomaly_rate >= 0.50 and cost_anomaly_count >= 2) or (density_score < 0.30 and flagged_count >= 2):
            trust_tier = TrustTier.CRITICAL_ALERT
        elif density_score >= 0.75:
            trust_tier = TrustTier.HIGH
        elif density_score >= 0.50:
            trust_tier = TrustTier.MODERATE
        else:
            trust_tier = TrustTier.LOW

        metrics = TrustDensityMetrics(
            location_key=location_key,
            city=city,
            state_or_region=state_or_region,
            total_claims=total_claims,
            verified_claims=verified_claims,
            supported_count=supported_count,
            partially_supported_count=partially_supported_count,
            contradicted_count=contradicted_count,
            flagged_count=flagged_count,
            abstained_count=abstained_count,
            cost_anomaly_count=cost_anomaly_count,
            cost_anomaly_rate=round(cost_anomaly_rate, 4),
            support_ratio=round(support_ratio, 4),
            recency_weighted_volume=round(recency_volume, 3),
            density_score=density_score,
            trust_tier=trust_tier,
            last_updated=now,
        )

        # Synthesize top entities and insights
        top_anomalies = [ent for ent, _ in Counter(anomalous_entities).most_common(5) if ent]
        top_procedures = [ent for ent, _ in Counter(all_entities).most_common(5) if ent]
        sample_ids = [c.claim_id for c in claims[:5]]

        # Human-auditable summary narrative & small-sample transparency
        loc_display = f"{city}, {state_or_region}" if state_or_region else city
        is_sparse_sample = (2 <= verified_claims < self.min_volume)
        sparse_prefix = f"PRELIMINARY ASSESSMENT ({verified_claims} audited claims): " if is_sparse_sample else ""

        if trust_tier == TrustTier.INSUFFICIENT_DATA:
            if total_claims == 0:
                summary = (
                    f"Locality {loc_display} has zero recorded claims. "
                    f"Insufficient data to evaluate trust."
                )
                recommendation = "Ingest and verify claims from this area before applying automated billing trust rules."
            elif verified_claims == 0:
                summary = (
                    f"Locality {loc_display} has {total_claims} ingested claim(s) and 0 audited. "
                    f"Insufficient data to evaluate trust."
                )
                recommendation = "Run the verification audit pipeline on ingested claims for this locality to establish baseline trust metrics."
            else:
                summary = (
                    f"Locality {loc_display} has {total_claims} ingested claim(s) and {verified_claims} audited claim. "
                    f"Insufficient sample volume (minimum 2 verified claims required) to establish a conclusive trust tier."
                )
                recommendation = "Ingest and verify additional claims from this area before applying automated billing trust rules."

        elif trust_tier == TrustTier.CRITICAL_ALERT:
            summary = (
                f"{sparse_prefix}CRITICAL RISK in {loc_display}: Trust density score is {density_score:.2f} with a {cost_anomaly_rate * 100:.1f}% "
                f"cost-anomaly rate ({cost_anomaly_count}/{verified_claims} audited claims flagged). High markup or non-standard billing detected."
            )
            recommendation = (
                f"Flag all incoming claims from {loc_display} for mandatory line-item itemization and prior authorization audit, "
                f"specifically for: {', '.join(top_anomalies) if top_anomalies else 'billed procedures'}."
            )

        elif trust_tier == TrustTier.LOW:
            # Distinguish between genuine contradiction/anomaly risk vs abstained/unestablished baseline
            if cost_anomaly_count == 0 and contradicted_count == 0:
                summary = (
                    f"{sparse_prefix}UNRESOLVED BASELINE in {loc_display}: Trust density score is {density_score:.2f}. "
                    f"Clinical guideline adherence is inconclusive ({abstained_count} claim(s) abstained due to unrepresented clinical guidelines). "
                    f"Zero detected billing anomalies across {verified_claims} audited claims. "
                    f"Low score reflects lack of guideline coverage rather than confirmed non-compliance."
                )
                recommendation = (
                    f"Expand local clinical guideline coverage for procedures in {loc_display} "
                    f"before treating this score as an indicator of provider risk."
                )
            else:
                if cost_anomaly_count > 0 and contradicted_count > 0:
                    findings_desc = (
                        f"{contradicted_count} claim(s) contradicted by guidelines and "
                        f"{cost_anomaly_count} cost anomaly(ies) detected ({cost_anomaly_rate * 100:.1f}% rate)"
                    )
                elif cost_anomaly_count > 0:
                    findings_desc = (
                        f"{cost_anomaly_count} cost anomaly(ies) detected across {verified_claims} audited claims "
                        f"({cost_anomaly_rate * 100:.1f}% rate)"
                    )
                else:
                    findings_desc = (
                        f"{contradicted_count} claim(s) contradicted by clinical guidelines "
                        f"({support_ratio * 100:.1f}% support ratio)"
                    )

                summary = (
                    f"{sparse_prefix}ELEVATED RISK in {loc_display}: Trust density score is {density_score:.2f}. "
                    f"Findings include {findings_desc}."
                )
                recommendation = "Recommend secondary clinical necessity and price-benchmark verification for high-cost line items."

        elif trust_tier == TrustTier.MODERATE:
            if cost_anomaly_count > 0:
                anomaly_desc = f"{cost_anomaly_count} billing anomaly(ies) ({cost_anomaly_rate * 100:.1f}% rate)"
            else:
                anomaly_desc = "zero detected billing anomalies"

            if eval_conclusive > 0:
                adherence_desc = (
                    f"Adherence to clinical guidelines is stable "
                    f"({support_ratio * 100:.1f}% support ratio across {eval_conclusive} conclusive audit(s))"
                )
            else:
                adherence_desc = (
                    f"Clinical guideline adherence is inconclusive "
                    f"({abstained_count} claim(s) abstained due to unrepresented guidelines)"
                )

            summary = (
                f"{sparse_prefix}MODERATE TRUST in {loc_display}: Trust density score is {density_score:.2f} across {verified_claims} audited claims. "
                f"{adherence_desc} with {anomaly_desc}."
            )
            if eval_conclusive == 0 and cost_anomaly_count == 0:
                recommendation = (
                    f"Expand clinical guideline coverage for procedures in {loc_display} "
                    f"to convert abstained claims into conclusive audits."
                )
            else:
                recommendation = "Standard automated verification with spot audits on outliers."

        else:  # HIGH
            if cost_anomaly_count > 0:
                anomaly_desc = f"{cost_anomaly_count} cost anomaly(ies) ({cost_anomaly_rate * 100:.1f}% rate)"
            else:
                anomaly_desc = "zero detected cost anomalies"

            if eval_conclusive > 0:
                guideline_desc = (
                    f"Clinical guideline support is high "
                    f"({support_ratio * 100:.1f}% support ratio across {eval_conclusive} conclusive audit(s))"
                )
            else:
                guideline_desc = (
                    f"Clinical guidelines were unrepresented "
                    f"({abstained_count} claim(s) abstained)"
                )

            summary = (
                f"{sparse_prefix}HIGH TRUST in {loc_display}: Trust density score is {density_score:.2f} across {verified_claims} audited claims. "
                f"{guideline_desc} with {anomaly_desc}."
            )
            recommendation = "Area demonstrates high billing fidelity and guideline compliance; eligible for expedited verification."

        insight = LocationInsight(
            location_key=location_key,
            city=city,
            state_or_region=state_or_region,
            density_score=density_score,
            trust_tier=trust_tier,
            top_anomalous_entities=top_anomalies,
            top_procedures_audited=top_procedures,
            summary_text=summary,
            sample_claim_ids=sample_ids,
            recommendation=recommendation,
        )

        return metrics, insight

    async def recompute_and_save(
        self,
        location_key: str,
        storage_service: Any,
    ) -> Optional[tuple[TrustDensityMetrics, LocationInsight]]:
        """
        Loads claims and verifications for a location_key from storage,
        calculates updated TrustDensityMetrics and LocationInsight, and saves to MongoDB.
        """
        if not storage_service or not storage_service.is_connected:
            return None

        # Fetch claims for this location
        claims_data = await storage_service.get_claims_by_location(location_key)
        if not claims_data:
            return None

        claims = [Claim.model_validate(c) for c in claims_data]
        city = claims[0].location.city if (claims[0].location and claims[0].location.city) else location_key
        state_or_region = claims[0].location.state_or_region if claims[0].location else None

        # Fetch verifications for all these claims
        verifications: list[VerificationResult] = []
        for claim in claims:
            v_data = await storage_service.get_verification_by_claim_id(claim.claim_id)
            if v_data:
                verifications.append(VerificationResult.model_validate(v_data))

        metrics, insight = self.calculate_metrics(
            location_key=location_key,
            city=city,
            state_or_region=state_or_region,
            claims=claims,
            verifications=verifications,
        )

        # Upsert into storage
        await storage_service.upsert_trust_density(
            metrics_dict=metrics.model_dump(mode="json"),
            insight_dict=insight.model_dump(mode="json"),
        )

        return metrics, insight


# Global singleton instance
trust_density_service = TrustDensityService()
