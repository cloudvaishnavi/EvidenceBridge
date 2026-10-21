"""
Unit tests for Cost Anomaly Detection Service.
"""

from datetime import datetime, timezone
import pytest

from app.models.schemas import Claim, ExtractedFields, ProvenanceMetadata, SentimentType
from app.services.cost_anomaly import CostAnomalyService


@pytest.fixture
def cost_service():
    return CostAnomalyService()


def test_extract_numeric_cost_various_formats(cost_service):
    # Single standard dollar amount
    assert cost_service.extract_numeric_cost("$4,850.00") == 4850.0
    assert cost_service.extract_numeric_cost("$74.00 per single tablet") == 74.0
    assert cost_service.extract_numeric_cost("$148.00 ($74.00 per tablet)") == 148.0
    assert cost_service.extract_numeric_cost("$980 out of pocket per month") == 980.0
    assert cost_service.extract_numeric_cost("$4,500 - $6,000") == 6000.0  # takes upper bound
    assert cost_service.extract_numeric_cost("total billed charge: 720.00 USD") == 720.0
    assert cost_service.extract_numeric_cost(None) is None
    assert cost_service.extract_numeric_cost("Not reported") is None


def test_benchmark_matching_by_cpt_and_keywords(cost_service):
    # Match by CPT code
    bm_er = cost_service.find_matching_benchmark("Emergency Room", "CPT 99285 acute evaluation")
    assert bm_er is not None
    assert bm_er.cpt_code == "99285"

    bm_mri = cost_service.find_matching_benchmark("MRI Left Knee", "Procedure CPT 73721")
    assert bm_mri is not None
    assert bm_mri.cpt_code == "73721"

    # Match by entity name / keywords
    bm_tylenol = cost_service.find_matching_benchmark("Acetaminophen 500mg oral tablet", "Inpatient pharmacy")
    assert bm_tylenol is not None
    assert "acetaminophen" in bm_tylenol.keywords or "tylenol" in bm_tylenol.keywords

    bm_saline = cost_service.find_matching_benchmark("Normal Saline 1000 mL IV", "0.9% sodium chloride")
    assert bm_saline is not None


def test_normal_cost_within_benchmark(cost_service):
    # Lisinopril $10.00 (Benchmark: $4 - $20)
    claim = Claim(
        claim_id="clm_normal_cost",
        original_text="Lisinopril 20mg 30-day supply billed at $10.00",
        source_type="patient_report",
        timestamp=datetime.now(timezone.utc),
        extracted_fields=ExtractedFields(
            entity="Lisinopril 20 mg",
            cost_range="$10.00",
            sentiment=SentimentType.NEUTRAL
        ),
        confidence=0.9,
        provenance=ProvenanceMetadata(
            source_hash="dummyhash",
            original_snippet="Lisinopril note",
            text_length=40,
            source_type="patient_report"
        )
    )

    details = cost_service.evaluate_claim_cost(claim)
    assert details.is_anomaly is False
    assert details.severity == "none"
    assert details.extracted_amount == 10.0
    assert details.benchmark_max == 20.0


def test_extreme_cost_anomaly_flagged(cost_service):
    # Acetaminophen charged at $74.00 per tablet (Benchmark max: $1.00) -> 74x multiplier!
    claim = Claim(
        claim_id="clm_tylenol_anomaly",
        original_text="Acetaminophen 500mg oral tablet billed at $74.00 per tablet",
        source_type="hospital_bill",
        timestamp=datetime.now(timezone.utc),
        extracted_fields=ExtractedFields(
            entity="Acetaminophen 500 MG Oral Tablet",
            cost_range="$74.00",
            sentiment=SentimentType.NEGATIVE
        ),
        confidence=0.95,
        provenance=ProvenanceMetadata(
            source_hash="dummyhash2",
            original_snippet="Acetaminophen bill",
            text_length=55,
            source_type="hospital_bill"
        )
    )

    details = cost_service.evaluate_claim_cost(claim)
    assert details.is_anomaly is True
    assert details.severity == "extreme"
    assert details.multiplier is not None
    assert details.multiplier >= 10.0
    assert "COST ANOMALY DETECTED" in details.explanation


def test_missing_cost_evaluated_cleanly(cost_service):
    claim = Claim(
        claim_id="clm_no_cost",
        original_text="Patient responded well to Metformin 1000mg with no adverse effects.",
        source_type="clinical_note",
        timestamp=datetime.now(timezone.utc),
        extracted_fields=ExtractedFields(
            entity="Metformin 1,000 mg",
            cost_range=None,
            sentiment=SentimentType.POSITIVE
        ),
        confidence=0.95,
        provenance=ProvenanceMetadata(
            source_hash="dummyhash3",
            original_snippet="Metformin note",
            text_length=65,
            source_type="clinical_note"
        )
    )

    details = cost_service.evaluate_claim_cost(claim)
    assert details.is_anomaly is False
    assert details.extracted_amount is None
    assert "No numeric cost figure identified" in details.explanation
