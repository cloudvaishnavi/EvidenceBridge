"""
Tests for Hyperlocal Trust Density Service (Layer 4).
Validates trust density formula computation, tier assignment, time-decay weighting,
insight generation, and edge cases (empty, single-claim, all-abstained).
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.models.schemas import (
    Claim,
    CostAnomalyDetails,
    ExtractedFields,
    LocationInfo,
    LocationInsight,
    ProvenanceMetadata,
    SentimentType,
    TrustDensityMetrics,
    TrustTier,
    VerificationAction,
    VerificationResult,
    VerificationVerdict,
)
from app.services.trust_density import TrustDensityService


# ==============================================================================
# Helpers
# ==============================================================================

def _make_claim(
    claim_id: str,
    entity: str = "MRI",
    cost: str | None = None,
    location_key: str = "houston_tx",
    city: str = "Houston",
    state: str = "TX",
    timestamp: datetime | None = None,
) -> Claim:
    now = timestamp or datetime.now(timezone.utc)
    return Claim(
        claim_id=claim_id,
        original_text=f"Test claim for {entity} at {city}, {state}",
        source_type="hospital_bill",
        timestamp=now,
        extracted_fields=ExtractedFields(
            entity=entity,
            effect_or_outcome="Procedure completed",
            cost_range=cost,
            location_city=f"{city}, {state}",
            sentiment=SentimentType.NEUTRAL,
            reasoning="Test extraction",
        ),
        confidence=0.9,
        provenance=ProvenanceMetadata(
            source_hash="testhash",
            original_snippet="test",
            text_length=50,
            source_type="hospital_bill",
            ingested_at=now,
        ),
        location=LocationInfo(
            city=city,
            state_or_region=state,
            country="US",
            normalized_key=location_key,
        ),
    )


def _make_verification(
    claim_id: str,
    verdict: VerificationVerdict = VerificationVerdict.SUPPORTED,
    action: VerificationAction = VerificationAction.ACCEPT,
    support_score: float = 0.85,
    cost_anomaly: bool = False,
) -> VerificationResult:
    return VerificationResult(
        claim_id=claim_id,
        support_score=support_score,
        verdict=verdict,
        action=action,
        reasoning="Test verification",
        evidence_snippets=[],
        cost_anomaly_flag=cost_anomaly,
        anomaly_details=CostAnomalyDetails(
            is_anomaly=True,
            extracted_amount=5000.0,
            benchmark_min=100.0,
            benchmark_max=500.0,
            multiplier=10.0,
            threshold_multiplier=3.0,
            severity="extreme",
            explanation="Test anomaly",
        ) if cost_anomaly else None,
        verified_at=datetime.now(timezone.utc),
    )


# ==============================================================================
# Core Metric Calculation Tests
# ==============================================================================

class TestTrustDensityCalculation:
    """Tests for TrustDensityService.calculate_metrics()."""

    def setup_method(self):
        self.svc = TrustDensityService(
            support_weight=0.45,
            anomaly_weight=0.35,
            volume_weight=0.20,
            min_volume=5,
            time_decay_days=45.0,
        )

    def test_all_supported_no_anomalies(self):
        """Clean location with all-supported claims should score high."""
        claims = [_make_claim(f"clm_{i}", entity="Metformin") for i in range(5)]
        verifications = [
            _make_verification(f"clm_{i}", VerificationVerdict.SUPPORTED, VerificationAction.ACCEPT)
            for i in range(5)
        ]

        metrics, insight = self.svc.calculate_metrics(
            location_key="houston_tx",
            city="Houston",
            state_or_region="TX",
            claims=claims,
            verifications=verifications,
        )

        assert metrics.location_key == "houston_tx"
        assert metrics.total_claims == 5
        assert metrics.verified_claims == 5
        assert metrics.supported_count == 5
        assert metrics.contradicted_count == 0
        assert metrics.cost_anomaly_count == 0
        assert metrics.support_ratio == 1.0
        assert metrics.cost_anomaly_rate == 0.0
        assert metrics.density_score >= 0.75
        assert metrics.trust_tier == TrustTier.HIGH

    def test_all_contradicted_high_anomalies(self):
        """Location with all contradictions and anomalies should score critical."""
        claims = [_make_claim(f"clm_{i}", entity="Saline IV") for i in range(4)]
        verifications = [
            _make_verification(
                f"clm_{i}",
                VerificationVerdict.CONTRADICTED,
                VerificationAction.FLAG,
                support_score=0.1,
                cost_anomaly=True,
            )
            for i in range(4)
        ]

        metrics, insight = self.svc.calculate_metrics(
            location_key="badcity_oh",
            city="BadCity",
            state_or_region="OH",
            claims=claims,
            verifications=verifications,
        )

        assert metrics.supported_count == 0
        assert metrics.contradicted_count == 4
        assert metrics.cost_anomaly_count == 4
        assert metrics.cost_anomaly_rate == 1.0
        assert metrics.support_ratio == 0.0
        assert metrics.density_score < 0.30
        assert metrics.trust_tier == TrustTier.CRITICAL_ALERT

    def test_mixed_verdicts_moderate_tier(self):
        """Location with a mix of outcomes should be moderate."""
        claims = [_make_claim(f"clm_{i}", entity="ER Visit") for i in range(6)]
        verifications = [
            _make_verification("clm_0", VerificationVerdict.SUPPORTED, VerificationAction.ACCEPT),
            _make_verification("clm_1", VerificationVerdict.SUPPORTED, VerificationAction.ACCEPT),
            _make_verification("clm_2", VerificationVerdict.PARTIALLY_SUPPORTED, VerificationAction.FLAG),
            _make_verification("clm_3", VerificationVerdict.CONTRADICTED, VerificationAction.FLAG, cost_anomaly=True),
            _make_verification("clm_4", VerificationVerdict.SUPPORTED, VerificationAction.ACCEPT),
            _make_verification("clm_5", VerificationVerdict.INSUFFICIENT_EVIDENCE, VerificationAction.ABSTAIN),
        ]

        metrics, insight = self.svc.calculate_metrics(
            location_key="mixed_tx",
            city="MixedCity",
            state_or_region="TX",
            claims=claims,
            verifications=verifications,
        )

        assert metrics.total_claims == 6
        assert metrics.verified_claims == 6
        assert metrics.supported_count == 3
        assert metrics.partially_supported_count == 1
        assert metrics.cost_anomaly_count == 1
        assert 0.40 <= metrics.density_score <= 0.85
        assert metrics.trust_tier in (TrustTier.MODERATE, TrustTier.HIGH)

    def test_support_ratio_with_partial(self):
        """Partially supported claims should count as half in support ratio."""
        claims = [_make_claim(f"clm_{i}") for i in range(4)]
        verifications = [
            _make_verification("clm_0", VerificationVerdict.SUPPORTED, VerificationAction.ACCEPT),
            _make_verification("clm_1", VerificationVerdict.PARTIALLY_SUPPORTED, VerificationAction.FLAG),
            _make_verification("clm_2", VerificationVerdict.CONTRADICTED, VerificationAction.FLAG),
            _make_verification("clm_3", VerificationVerdict.SUPPORTED, VerificationAction.ACCEPT),
        ]

        metrics, _ = self.svc.calculate_metrics(
            "test_loc", "TestCity", "TS", claims, verifications
        )

        # support_ratio = (2 + 0.5*1) / (2 + 1 + 1) = 2.5/4 = 0.625
        assert abs(metrics.support_ratio - 0.625) < 0.01


# ==============================================================================
# Edge Cases
# ==============================================================================

class TestTrustDensityEdgeCases:
    """Edge case tests for trust density service."""

    def setup_method(self):
        self.svc = TrustDensityService(
            support_weight=0.45,
            anomaly_weight=0.35,
            volume_weight=0.20,
            min_volume=5,
            time_decay_days=45.0,
        )

    def test_zero_claims(self):
        """Empty location should yield insufficient data."""
        metrics, insight = self.svc.calculate_metrics(
            "empty_loc", "Empty", None, [], []
        )

        assert metrics.total_claims == 0
        assert metrics.verified_claims == 0
        assert metrics.trust_tier == TrustTier.INSUFFICIENT_DATA

    def test_single_claim_insufficient_data(self):
        """One verified claim is below minimum threshold."""
        claims = [_make_claim("clm_single")]
        verifications = [_make_verification("clm_single")]

        metrics, insight = self.svc.calculate_metrics(
            "single_loc", "Single", "XX", claims, verifications
        )

        assert metrics.total_claims == 1
        assert metrics.verified_claims == 1
        assert metrics.trust_tier == TrustTier.INSUFFICIENT_DATA

    def test_claims_with_no_verifications(self):
        """Claims exist but none are verified."""
        claims = [_make_claim(f"clm_{i}") for i in range(3)]

        metrics, insight = self.svc.calculate_metrics(
            "unverified_loc", "Unverified", "UV", claims, []
        )

        assert metrics.total_claims == 3
        assert metrics.verified_claims == 0
        assert metrics.cost_anomaly_rate == 0.0
        assert metrics.trust_tier == TrustTier.INSUFFICIENT_DATA

    def test_all_abstained(self):
        """All verifications abstained - should handle gracefully."""
        claims = [_make_claim(f"clm_{i}") for i in range(4)]
        verifications = [
            _make_verification(
                f"clm_{i}",
                VerificationVerdict.INSUFFICIENT_EVIDENCE,
                VerificationAction.ABSTAIN,
                support_score=0.0,
            )
            for i in range(4)
        ]

        metrics, insight = self.svc.calculate_metrics(
            "abstain_loc", "AbstainCity", "AB", claims, verifications
        )

        assert metrics.abstained_count == 4
        assert metrics.supported_count == 0
        assert metrics.contradicted_count == 0
        assert metrics.cost_anomaly_count == 0
        # With 0 conclusive evaluations, support_ratio must be strictly 0.0 (never 0.5)
        assert metrics.support_ratio == 0.0
        # Narrative must not claim billing anomalies when anomaly rate is 0.0%
        assert "occasional billing anomalies" not in insight.summary_text
        assert "zero detected billing anomalies" in insight.summary_text
        assert "inconclusive" in insight.summary_text.lower()

    def test_houston_all_abstained_clean_billing(self):
        """Simulate Houston scenario: 4 audited claims, all abstained, zero anomalies."""
        claims = [_make_claim(f"hou_{i}", entity="MRI", city="Houston", state="TX") for i in range(4)]
        verifications = [
            _make_verification(
                f"hou_{i}",
                VerificationVerdict.INSUFFICIENT_EVIDENCE,
                VerificationAction.ABSTAIN,
                support_score=0.0,
                cost_anomaly=False,
            )
            for i in range(4)
        ]

        metrics, insight = self.svc.calculate_metrics(
            "houston_tx", "Houston", "TX", claims, verifications
        )

        assert metrics.total_claims == 4
        assert metrics.verified_claims == 4
        assert metrics.supported_count == 0
        assert metrics.flagged_count == 0
        assert metrics.contradicted_count == 0
        assert metrics.abstained_count == 4
        assert metrics.cost_anomaly_count == 0
        assert metrics.cost_anomaly_rate == 0.0
        # Support ratio is strictly 0.0 when supported is 0
        assert metrics.support_ratio == 0.0
        # Narrative is consistent with 0 anomalies and inconclusive guideline support
        assert "zero detected billing anomalies" in insight.summary_text
        assert "occasional billing anomalies" not in insight.summary_text
        assert "inconclusive" in insight.summary_text.lower()


# ==============================================================================
# Time Decay Tests
# ==============================================================================

class TestTimeDecay:
    """Tests for time-decay recency weighting."""

    def setup_method(self):
        self.svc = TrustDensityService(
            support_weight=0.45,
            anomaly_weight=0.35,
            volume_weight=0.20,
            min_volume=5,
            time_decay_days=45.0,
        )

    def test_recent_claims_weighted_more(self):
        """Recent claims should contribute more to recency_weighted_volume."""
        now = datetime.now(timezone.utc)
        recent_claims = [_make_claim(f"clm_{i}", timestamp=now) for i in range(3)]
        old_claims = [
            _make_claim(f"clm_old_{i}", timestamp=now - timedelta(days=180))
            for i in range(3)
        ]

        metrics_recent, _ = self.svc.calculate_metrics(
            "recent_loc", "RecentCity", "RC", recent_claims, []
        )
        metrics_old, _ = self.svc.calculate_metrics(
            "old_loc", "OldCity", "OC", old_claims, []
        )

        assert metrics_recent.recency_weighted_volume > metrics_old.recency_weighted_volume


# ==============================================================================
# Insight Generation Tests
# ==============================================================================

class TestInsightGeneration:
    """Tests for LocationInsight generation."""

    def setup_method(self):
        self.svc = TrustDensityService(
            support_weight=0.45,
            anomaly_weight=0.35,
            volume_weight=0.20,
            min_volume=5,
            time_decay_days=45.0,
        )

    def test_high_trust_insight_text(self):
        """High trust tier should produce an optimistic summary."""
        claims = [_make_claim(f"clm_{i}", entity="Metformin") for i in range(5)]
        verifications = [
            _make_verification(f"clm_{i}") for i in range(5)
        ]

        _, insight = self.svc.calculate_metrics(
            "good_tx", "GoodCity", "TX", claims, verifications
        )

        assert "HIGH TRUST" in insight.summary_text
        assert insight.trust_tier == TrustTier.HIGH
        assert insight.recommendation is not None

    def test_critical_alert_insight_text(self):
        """Critical alert location should produce warning summary."""
        claims = [_make_claim(f"clm_{i}", entity="Saline") for i in range(4)]
        verifications = [
            _make_verification(
                f"clm_{i}",
                VerificationVerdict.CONTRADICTED,
                VerificationAction.FLAG,
                cost_anomaly=True,
            )
            for i in range(4)
        ]

        _, insight = self.svc.calculate_metrics(
            "bad_oh", "BadCity", "OH", claims, verifications
        )

        assert "CRITICAL" in insight.summary_text
        assert insight.trust_tier == TrustTier.CRITICAL_ALERT
        assert insight.recommendation is not None

    def test_insufficient_data_insight(self):
        """Insufficient data location should get appropriate messaging."""
        claims = [_make_claim("clm_lone")]
        verifications = [_make_verification("clm_lone")]

        _, insight = self.svc.calculate_metrics(
            "lone_tx", "LoneCity", "TX", claims, verifications
        )

        assert insight.trust_tier == TrustTier.INSUFFICIENT_DATA
        assert "insufficient" in insight.summary_text.lower() or "Insufficient" in insight.summary_text

    def test_top_anomalous_entities_populated(self):
        """Entities with cost anomalies should appear in top_anomalous_entities."""
        claims = [
            _make_claim("clm_0", entity="MRI"),
            _make_claim("clm_1", entity="MRI"),
            _make_claim("clm_2", entity="Saline IV"),
        ]
        verifications = [
            _make_verification("clm_0", cost_anomaly=True),
            _make_verification("clm_1", cost_anomaly=True),
            _make_verification("clm_2", cost_anomaly=True),
        ]

        _, insight = self.svc.calculate_metrics(
            "anomaly_tx", "AnomalyCity", "TX", claims, verifications
        )

        assert len(insight.top_anomalous_entities) >= 1
        assert "MRI" in insight.top_anomalous_entities

    def test_sample_claim_ids_limited(self):
        """sample_claim_ids should contain at most 5 IDs."""
        claims = [_make_claim(f"clm_{i}") for i in range(10)]
        verifications = [_make_verification(f"clm_{i}") for i in range(10)]

        _, insight = self.svc.calculate_metrics(
            "big_tx", "BigCity", "TX", claims, verifications
        )

        assert len(insight.sample_claim_ids) <= 5


# ==============================================================================
# Schema Validation Tests
# ==============================================================================

class TestTrustDensitySchemas:
    """Tests for Layer 4 Pydantic schema validation."""

    def test_location_info_creation(self):
        loc = LocationInfo(
            city="Houston",
            state_or_region="TX",
            country="US",
            normalized_key="houston_tx",
        )
        assert loc.city == "Houston"
        assert loc.latitude is None

    def test_trust_density_metrics_defaults(self):
        m = TrustDensityMetrics(
            location_key="test_tx",
            city="Test",
        )
        assert m.total_claims == 0
        assert m.density_score == 0.5
        assert m.trust_tier == TrustTier.INSUFFICIENT_DATA

    def test_density_score_clamped(self):
        """Score should be between 0.0 and 1.0."""
        m = TrustDensityMetrics(
            location_key="test_tx",
            city="Test",
            density_score=0.0,
        )
        assert m.density_score == 0.0

    def test_trust_tier_enum_values(self):
        assert TrustTier.HIGH.value == "high"
        assert TrustTier.MODERATE.value == "moderate"
        assert TrustTier.LOW.value == "low"
        assert TrustTier.CRITICAL_ALERT.value == "critical_alert"
        assert TrustTier.INSUFFICIENT_DATA.value == "insufficient_data"


# ==============================================================================
# Hand-Calculated Mathematical & Small-Sample Hardening Tests (Step 5)
# ==============================================================================

class TestHandCalculatedTrustDensity:
    """
    Exhaustive mathematical verification of Trust Density formulas using hand-calculated
    ground truth values. Validates exact numerical consistency, time-decay constants,
    tier threshold cutoffs, and small-sample / abstention narrative transparency.
    """

    def setup_method(self):
        self.svc = TrustDensityService(
            support_weight=0.45,
            anomaly_weight=0.35,
            volume_weight=0.20,
            min_volume=5,
            time_decay_days=45.0,
        )

    def test_hand_calculated_synthetic_4_claims_moderate(self):
        """
        Hand-calculated scenario with 4 contemporaneous claims (t = now):
        - Claim 0: SUPPORTED (ACCEPT), no cost anomaly
        - Claim 1: SUPPORTED (ACCEPT), no cost anomaly
        - Claim 2: PARTIALLY_SUPPORTED (FLAG), no cost anomaly
        - Claim 3: CONTRADICTED (FLAG), cost anomaly = True

        Hand calculation:
        - total_claims = 4, verified_claims = 4
        - supported = 2, partially_supported = 1, contradicted = 1
        - flagged_count = 2, abstained_count = 0, cost_anomaly_count = 1
        - eval_conclusive = 2 + 1 + 1 = 4
        - support_ratio = (2 + 0.5 * 1) / 4 = 2.5 / 4 = 0.6250
        - cost_anomaly_rate = 1 / 4 = 0.2500
        - recency_volume = 1.0 + 1.0 + 1.0 + 1.0 = 4.000
        - volume_factor = min(1.0, 4.0 / 5) = 0.8000
        - raw_density = 0.45 * 0.625 + 0.35 * (1 - 0.25) + 0.20 * 0.80
                      = 0.28125 + 0.2625 + 0.1600 = 0.70375
        - density_score = round(0.70375, 4) = 0.7037 (Python IEEE-754 round-to-even / float representation)
        - trust_tier: 0.7037 is in [0.50, 0.75) -> MODERATE
        """
        now = datetime.now(timezone.utc)
        claims = [_make_claim(f"syn_{i}", timestamp=now) for i in range(4)]
        verifications = [
            _make_verification("syn_0", VerificationVerdict.SUPPORTED, VerificationAction.ACCEPT, cost_anomaly=False),
            _make_verification("syn_1", VerificationVerdict.SUPPORTED, VerificationAction.ACCEPT, cost_anomaly=False),
            _make_verification("syn_2", VerificationVerdict.PARTIALLY_SUPPORTED, VerificationAction.FLAG, cost_anomaly=False),
            _make_verification("syn_3", VerificationVerdict.CONTRADICTED, VerificationAction.FLAG, cost_anomaly=True),
        ]

        metrics, insight = self.svc.calculate_metrics("austin_tx", "Austin", "TX", claims, verifications)

        # Assert exact metrics
        assert metrics.total_claims == 4
        assert metrics.verified_claims == 4
        assert metrics.supported_count == 2
        assert metrics.partially_supported_count == 1
        assert metrics.contradicted_count == 1
        assert metrics.flagged_count == 2
        assert metrics.abstained_count == 0
        assert metrics.cost_anomaly_count == 1
        assert metrics.support_ratio == 0.625
        assert metrics.cost_anomaly_rate == 0.25
        assert metrics.recency_weighted_volume == 4.0
        assert metrics.density_score == 0.7037
        assert metrics.trust_tier == TrustTier.MODERATE

        # Assert narrative small-sample transparency (N=4 claims is sparse sample: < min_volume 5)
        assert insight.summary_text.startswith("PRELIMINARY ASSESSMENT (4 audited claims): MODERATE TRUST in Austin, TX")
        assert "62.5% support ratio across 4 conclusive audit(s)" in insight.summary_text
        assert "1 billing anomaly(ies) (25.0% rate)" in insight.summary_text

    def test_hand_calculated_time_decay_exact(self):
        """
        Hand-calculated exponential time-decay test:
        Decay constant tau = 45.0 days.
        Claim 0: Age 0.0 days  -> w_0 = exp(-0/45) = 1.000000
        Claim 1: Age 45.0 days -> w_1 = exp(-45/45) = exp(-1) = 0.367879
        Claim 2: Age 90.0 days -> w_2 = exp(-90/45) = exp(-2) = 0.135335

        Sum of weights = 1.0 + 0.367879 + 0.135335 = 1.503214 -> recency_volume ~= 1.503
        volume_factor = min(1.0, 1.503214 / 5) = 0.300643

        All 3 claims supported, zero cost anomalies:
        - support_ratio = 1.0000
        - cost_anomaly_rate = 0.0000
        - raw_density = 0.45 * 1.0 + 0.35 * (1 - 0) + 0.20 * 0.300643
                      = 0.45 + 0.35 + 0.060129 = 0.860129
        - density_score = round(0.860129, 4) = 0.8601
        - trust_tier = HIGH (>= 0.75)
        """
        now = datetime.now(timezone.utc)
        claims = [
            _make_claim("decay_0", timestamp=now),
            _make_claim("decay_1", timestamp=now - timedelta(days=45)),
            _make_claim("decay_2", timestamp=now - timedelta(days=90)),
        ]
        verifications = [
            _make_verification(f"decay_{i}", VerificationVerdict.SUPPORTED, VerificationAction.ACCEPT, cost_anomaly=False)
            for i in range(3)
        ]

        metrics, insight = self.svc.calculate_metrics("dallas_tx", "Dallas", "TX", claims, verifications)

        assert metrics.total_claims == 3
        assert metrics.verified_claims == 3
        assert metrics.supported_count == 3
        assert metrics.support_ratio == 1.0
        assert metrics.cost_anomaly_rate == 0.0
        assert metrics.recency_weighted_volume == 1.503
        assert metrics.density_score == 0.8601
        assert metrics.trust_tier == TrustTier.HIGH

        # Verify preliminary notice for N=3 sparse claims
        assert insight.summary_text.startswith("PRELIMINARY ASSESSMENT (3 audited claims): HIGH TRUST in Dallas, TX")
        assert "Clinical guideline support is high (100.0% support ratio across 3 conclusive audit(s))" in insight.summary_text
        assert "zero detected cost anomalies" in insight.summary_text

    def test_hand_calculated_sparse_all_abstained_low_tier(self):
        """
        Sparse sample (3 claims) where all claims are abstained due to missing local guidelines,
        with old timestamps (100 days old) and zero cost anomalies.

        Hand calculation:
        - total_claims = 3, verified_claims = 3
        - supported = 0, partially_supported = 0, contradicted = 0, abstained = 3
        - eval_conclusive = 0 -> support_ratio = 0.0000
        - cost_anomaly_count = 0 -> cost_anomaly_rate = 0.0000
        - delta_days = 100 -> w = exp(-100 / 45) ~= 0.108368
        - recency_volume = 3 * 0.108368 = 0.325104 -> recency_volume ~= 0.325
        - volume_factor = 0.325104 / 5 = 0.065021
        - raw_density = 0.45 * 0.0 + 0.35 * (1 - 0) + 0.20 * 0.065021
                      = 0.0 + 0.35 + 0.013004 = 0.363004
        - density_score = round(0.363004, 4) = 0.3630
        - trust_tier = LOW (since 0.3630 < 0.50)

        CRITICAL REQUIREMENT:
        Because cost_anomaly_count == 0 and contradicted_count == 0, the narrative MUST NOT
        assert 'ELEVATED RISK'. Instead, it must classify as 'UNRESOLVED BASELINE', note that
        guidelines were unrepresented, and report zero detected billing anomalies.
        """
        now = datetime.now(timezone.utc)
        claims = [
            _make_claim(f"abst_{i}", timestamp=now - timedelta(days=100))
            for i in range(3)
        ]
        verifications = [
            _make_verification(
                f"abst_{i}",
                VerificationVerdict.INSUFFICIENT_EVIDENCE,
                VerificationAction.ABSTAIN,
                support_score=0.0,
                cost_anomaly=False,
            )
            for i in range(3)
        ]

        metrics, insight = self.svc.calculate_metrics("sparse_loc", "SparseCity", "SC", claims, verifications)

        assert metrics.total_claims == 3
        assert metrics.verified_claims == 3
        assert metrics.abstained_count == 3
        assert metrics.supported_count == 0
        assert metrics.contradicted_count == 0
        assert metrics.cost_anomaly_count == 0
        assert metrics.support_ratio == 0.0
        assert metrics.cost_anomaly_rate == 0.0
        assert metrics.recency_weighted_volume == 0.325
        assert metrics.density_score == 0.363
        assert metrics.trust_tier == TrustTier.LOW

        # Narrative assertions
        assert "ELEVATED RISK" not in insight.summary_text
        assert "PRELIMINARY ASSESSMENT (3 audited claims): UNRESOLVED BASELINE in SparseCity, SC" in insight.summary_text
        assert "Clinical guideline adherence is inconclusive (3 claim(s) abstained due to unrepresented clinical guidelines)" in insight.summary_text
        assert "Zero detected billing anomalies across 3 audited claims" in insight.summary_text
        assert "Low score reflects lack of guideline coverage rather than confirmed non-compliance" in insight.summary_text
        assert "Expand local clinical guideline coverage" in insight.recommendation

    def test_zero_claims_score_strictly_zero(self):
        """Zero claims must yield density_score = 0.0 and INSUFFICIENT_DATA."""
        metrics, insight = self.svc.calculate_metrics("empty_oh", "EmptyCity", "OH", [], [])

        assert metrics.total_claims == 0
        assert metrics.verified_claims == 0
        assert metrics.density_score == 0.0
        assert metrics.support_ratio == 0.0
        assert metrics.cost_anomaly_rate == 0.0
        assert metrics.recency_weighted_volume == 0.0
        assert metrics.trust_tier == TrustTier.INSUFFICIENT_DATA
        assert "zero recorded claims" in insight.summary_text
        assert "Insufficient data to evaluate trust" in insight.summary_text

    def test_single_claim_insufficient_data_with_details(self):
        """Single claim must be marked INSUFFICIENT_DATA with explicit minimum sample warning."""
        claims = [_make_claim("single_1")]
        verifications = [_make_verification("single_1", VerificationVerdict.SUPPORTED, VerificationAction.ACCEPT)]

        metrics, insight = self.svc.calculate_metrics("single_ca", "Solitary", "CA", claims, verifications)

        assert metrics.total_claims == 1
        assert metrics.verified_claims == 1
        assert metrics.trust_tier == TrustTier.INSUFFICIENT_DATA
        assert "1 audited claim" in insight.summary_text
        assert "minimum 2 verified claims required" in insight.summary_text

    def test_future_timestamp_clamped_safely(self):
        """Future timestamp must be clamped to delta_days = 0 (weight = 1.0) and not produce negative numbers or blow up."""
        now = datetime.now(timezone.utc)
        claims = [
            _make_claim("future_0", timestamp=now + timedelta(days=10)),
            _make_claim("future_1", timestamp=now + timedelta(days=365)),
        ]
        verifications = [
            _make_verification("future_0"),
            _make_verification("future_1"),
        ]

        metrics, _ = self.svc.calculate_metrics("future_ny", "FutureCity", "NY", claims, verifications)

        # Clamped delta means each future claim gets exp(0) = 1.0
        assert metrics.recency_weighted_volume == 2.0
        assert 0.0 <= metrics.density_score <= 1.0
