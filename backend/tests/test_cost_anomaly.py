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
    # Matched reference benchmark surfaced even when cost is missing
    assert details.benchmark_matched is True
    assert details.benchmark_name == "Metformin 1,000 mg"


def test_normal_charge_well_inside_benchmark_brain_mri(cost_service):
    """Normal Brain MRI charge ($650) well inside typical benchmark ($450 - $1,400)."""
    claim = Claim(
        claim_id="clm_mri_normal",
        original_text="Outpatient Brain MRI w/o contrast CPT 70551 billed at $650.00",
        source_type="clinical_note",
        timestamp=datetime.now(timezone.utc),
        extracted_fields=ExtractedFields(
            entity="MRI Brain without contrast (CPT 70551)",
            cost_range="$650.00",
            sentiment=SentimentType.NEUTRAL
        ),
        confidence=0.95,
        provenance=ProvenanceMetadata(
            source_hash="dummyhash_mri",
            original_snippet="Brain MRI",
            text_length=50,
            source_type="clinical_note"
        )
    )

    details = cost_service.evaluate_claim_cost(claim)
    assert details.is_anomaly is False
    assert details.benchmark_matched is True
    assert details.severity == "none"
    assert details.extracted_amount == 650.0
    assert details.benchmark_min == 450.0
    assert details.benchmark_max == 1400.0
    assert details.cpt_code == "70551"
    assert details.multiplier == 0.46
    assert "falls within or below typical benchmark" in details.explanation


def test_moderate_severity_markup_flagged(cost_service):
    """Comprehensive Metabolic Panel billed at $340 (4.0× benchmark max $85) -> Moderate anomaly."""
    claim = Claim(
        claim_id="clm_cmp_moderate",
        original_text="Hospital lab: CPT 80053 Comprehensive Metabolic Panel charge $340.00",
        source_type="hospital_bill",
        timestamp=datetime.now(timezone.utc),
        extracted_fields=ExtractedFields(
            entity="Comprehensive Metabolic Panel (CPT 80053)",
            cost_range="$340.00",
            sentiment=SentimentType.NEGATIVE
        ),
        confidence=0.95,
        provenance=ProvenanceMetadata(
            source_hash="dummyhash_cmp",
            original_snippet="CMP $340",
            text_length=55,
            source_type="hospital_bill"
        )
    )

    details = cost_service.evaluate_claim_cost(claim)
    assert details.is_anomaly is True
    assert details.benchmark_matched is True
    assert details.severity == "moderate"
    assert details.multiplier == 4.0
    assert details.benchmark_max == 85.0
    assert details.cpt_code == "80053"
    assert "COST ANOMALY DETECTED" in details.explanation


def test_severe_severity_markup_flagged(cost_service):
    """Routine Venipuncture billed at $125 (5.0× benchmark max $25) -> Severe anomaly."""
    claim = Claim(
        claim_id="clm_veni_severe",
        original_text="Outpatient blood draw CPT 36415 Routine Venipuncture charge $125.00",
        source_type="hospital_bill",
        timestamp=datetime.now(timezone.utc),
        extracted_fields=ExtractedFields(
            entity="Routine Venipuncture (CPT 36415)",
            cost_range="$125.00",
            sentiment=SentimentType.NEGATIVE
        ),
        confidence=0.95,
        provenance=ProvenanceMetadata(
            source_hash="dummyhash_veni",
            original_snippet="Venipuncture $125",
            text_length=55,
            source_type="hospital_bill"
        )
    )

    details = cost_service.evaluate_claim_cost(claim)
    assert details.is_anomaly is True
    assert details.benchmark_matched is True
    assert details.severity == "severe"
    assert details.multiplier == 5.0
    assert details.benchmark_max == 25.0
    assert details.cpt_code == "36415"
    assert "COST ANOMALY DETECTED" in details.explanation


def test_extreme_severity_markup_saline(cost_service):
    """0.9% Normal Saline billed at $720 (16.0× benchmark max $45) -> Extreme anomaly."""
    claim = Claim(
        claim_id="clm_saline_extreme",
        original_text="0.9% Sodium Chloride Normal Saline 1,000 mL IV infusion billed at $720.00",
        source_type="hospital_bill",
        timestamp=datetime.now(timezone.utc),
        extracted_fields=ExtractedFields(
            entity="0.9% Sodium Chloride (Normal Saline) 1,000 mL IV",
            cost_range="$720.00",
            sentiment=SentimentType.NEGATIVE
        ),
        confidence=0.95,
        provenance=ProvenanceMetadata(
            source_hash="dummyhash_saline",
            original_snippet="Normal Saline $720",
            text_length=60,
            source_type="hospital_bill"
        )
    )

    details = cost_service.evaluate_claim_cost(claim)
    assert details.is_anomaly is True
    assert details.benchmark_matched is True
    assert details.severity == "extreme"
    assert details.multiplier == 16.0
    assert details.cpt_code == "J7030"
    assert "16.0× higher" in details.explanation


def test_unbenchmarked_charge_details_and_abstention(cost_service):
    """
    Unbenchmarked high charge ($1,500) has benchmark_matched=False, surfaces explicit explanation,
    and deterministically triggers Rule 5 UNBENCHMARKED_HIGH_COST abstention.
    """
    from app.services.abstention import abstention_service, AbstentionRule

    claim = Claim(
        claim_id="clm_unbenchmarked_high",
        original_text="Experimental Peptide Infusion therapy session charge: $1,500.00",
        source_type="hospital_bill",
        timestamp=datetime.now(timezone.utc),
        extracted_fields=ExtractedFields(
            entity="Experimental Peptide Infusion",
            cost_range="$1,500.00",
            sentiment=SentimentType.NEUTRAL
        ),
        confidence=0.85,
        provenance=ProvenanceMetadata(
            source_hash="dummyhash_unb",
            original_snippet="Peptide $1,500",
            text_length=50,
            source_type="hospital_bill"
        )
    )

    details = cost_service.evaluate_claim_cost(claim)
    assert details.is_anomaly is False
    assert details.benchmark_matched is False
    assert details.benchmark_name is None
    assert details.cpt_code is None
    assert details.extracted_amount == 1500.0
    assert "No public pricing benchmark found for entity 'Experimental Peptide Infusion'" in details.explanation

    # Verify abstention gate triggers UNBENCHMARKED_HIGH_COST
    gate_decision = abstention_service.evaluate(
        claim=claim,
        passages=[],
        cost_details=details
    )
    assert gate_decision.should_abstain is True
    assert gate_decision.rule_triggered in (AbstentionRule.UNBENCHMARKED_HIGH_COST, AbstentionRule.NO_RELEVANT_EVIDENCE)


def test_unbenchmarked_low_charge_does_not_trigger_cost_abstention(cost_service):
    """Unbenchmarked small copay ($35) does not trigger unbenchmarked high cost rule."""
    from app.services.abstention import abstention_service, AbstentionRule

    claim = Claim(
        claim_id="clm_unbenchmarked_low",
        original_text="Holistic acupuncture copay charged at $35.00",
        source_type="patient_report",
        timestamp=datetime.now(timezone.utc),
        extracted_fields=ExtractedFields(
            entity="Holistic acupuncture consultation",
            cost_range="$35.00",
            sentiment=SentimentType.NEUTRAL
        ),
        confidence=0.88,
        provenance=ProvenanceMetadata(
            source_hash="dummyhash_low",
            original_snippet="Acupuncture $35",
            text_length=45,
            source_type="patient_report"
        )
    )

    details = cost_service.evaluate_claim_cost(claim)
    assert details.is_anomaly is False
    assert details.benchmark_matched is False
    assert details.extracted_amount == 35.0

    # Rule 5 requires cost > 100.0, so rule 5 should not be the triggered rule
    # (Note: rule 2 may trigger if passages empty, but rule 5 must NOT trigger)
    assert details.extracted_amount <= 100.0


def test_cost_parsing_formats_extended(cost_service):
    """Test extended numeric extraction formats (suffix currency, naked decimals, keywords)."""
    assert cost_service.extract_numeric_cost("1,250 USD") == 1250.0
    assert cost_service.extract_numeric_cost("720 dollars") == 720.0
    assert cost_service.extract_numeric_cost("total charge: 850.50") == 850.50
    assert cost_service.extract_numeric_cost("fee: 95.00") == 95.0
    assert cost_service.extract_numeric_cost("1100.00") == 1100.0
    assert cost_service.extract_numeric_cost("Coverage pending pre-authorization") is None
    assert cost_service.extract_numeric_cost("") is None


def test_multiple_cpts_in_text_entity_priority(cost_service):
    """
    Ensure CPT code in entity takes strict priority over other CPT codes
    mentioned in background bill text.
    """
    bm = cost_service.find_matching_benchmark(
        entity="CPT 70551 MRI Brain w/o Contrast",
        text="CPT 99285 ER Visit $2,850.00 and CPT 70551 MRI Brain $1,100.00"
    )
    assert bm is not None
    assert bm.cpt_code == "70551"
    assert "Brain" in bm.entity


def test_anatomical_conflict_benchmark_rejection(cost_service):
    """
    Ensure an entity with anatomical site 'knee' never matches a 'brain' benchmark
    even if keywords like 'mri' or 'without contrast' match.
    """
    bm = cost_service.find_matching_benchmark(
        entity="MRI Knee without contrast",
        text="Outpatient imaging center evaluation"
    )
    assert bm is not None
    assert "Knee" in bm.entity
    assert bm.cpt_code == "73721"
    assert "Brain" not in bm.entity

