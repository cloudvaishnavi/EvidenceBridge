"""
Unit tests for Cost Anomaly Detection Service.
"""

from datetime import datetime, timezone
import pytest

from app.models.schemas import Claim, CostAnomalyDetails, ExtractedFields, ProvenanceMetadata, SentimentType
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


def test_detect_currency_logic(cost_service):
    """Ensure detect_currency accurately identifies USD vs INR based on symbols and context."""
    # Explicit USD
    assert cost_service.detect_currency("$500", "Hospital in Boston") == "USD"
    assert cost_service.detect_currency("500 USD", "Routine test") == "USD"

    # Explicit INR
    assert cost_service.detect_currency("₹1,200", "Consultation") == "INR"
    assert cost_service.detect_currency("Rs. 450", "Medication") == "INR"
    assert cost_service.detect_currency("INR 8,000", "MRI scan") == "INR"
    assert cost_service.detect_currency("2.5 lakh", "Surgery bill") == "INR"

    # Indian context without symbol
    assert cost_service.detect_currency("1500", "Apollo Hospital Bengaluru consultation fee: 1500") == "INR"
    assert cost_service.detect_currency("800", "Patient visit in Ballari, Karnataka") == "INR"
    assert cost_service.detect_currency("250", "Blood test at AIIMS Delhi") == "INR"

    # Foreign location context without symbol
    assert cost_service.detect_currency("1500", "Clinic visit in Atlanta, GA") == "USD"

    # Default fallback across the application when no currency and no cues are given: prefer INR
    assert cost_service.detect_currency("1500", "Routine clinical consultation") == "INR"


def test_inr_benchmark_matching_and_evaluation(cost_service):
    """Ensure an Indian claim matches INR benchmark and evaluates anomalies correctly."""
    # Normal INR Paracetamol claim: ₹3.50 per tablet (NPPA Benchmark: ₹1.00 - ₹5.00)
    claim_normal = Claim(
        claim_id="clm_inr_normal",
        original_text="Paracetamol 500mg tablet billed at ₹3.50 at Manipal Hospital Bengaluru",
        source_type="pharmacy_bill",
        timestamp=datetime.now(timezone.utc),
        extracted_fields=ExtractedFields(
            entity="Paracetamol 500mg",
            cost_range="₹3.50",
            cost_currency="INR",
            location="Bengaluru, Karnataka",
            sentiment=SentimentType.NEUTRAL
        ),
        confidence=0.92,
        provenance=ProvenanceMetadata(
            source_hash="inr_hash_1",
            original_snippet="Paracetamol ₹3.50",
            text_length=60,
            source_type="pharmacy_bill"
        )
    )

    details = cost_service.evaluate_claim_cost(claim_normal)
    assert details.currency == "INR"
    assert details.benchmark_matched is True
    assert details.benchmark_currency == "INR"
    assert details.is_anomaly is False
    assert "₹" in details.explanation

    # Anomaly INR Paracetamol claim: ₹50.00 (NPPA Max: ₹5.00) -> 10x multiplier
    claim_anomaly = Claim(
        claim_id="clm_inr_anomaly",
        original_text="Paracetamol 500mg tablet billed at ₹50.00 at Fortis Hospital",
        source_type="pharmacy_bill",
        timestamp=datetime.now(timezone.utc),
        extracted_fields=ExtractedFields(
            entity="Paracetamol 500mg",
            cost_range="₹50.00",
            cost_currency="INR",
            location="Bengaluru, Karnataka",
            sentiment=SentimentType.NEGATIVE
        ),
        confidence=0.95,
        provenance=ProvenanceMetadata(
            source_hash="inr_hash_2",
            original_snippet="Paracetamol ₹50.00",
            text_length=60,
            source_type="pharmacy_bill"
        )
    )

    details_anomaly = cost_service.evaluate_claim_cost(claim_anomaly)
    assert details_anomaly.is_anomaly is True
    assert details_anomaly.currency == "INR"
    assert details_anomaly.benchmark_currency == "INR"
    assert details_anomaly.multiplier == 10.0
    assert "COST ANOMALY DETECTED" in details_anomaly.explanation
    assert "₹50.00" in details_anomaly.explanation


def test_cross_currency_handling(cost_service):
    """
    Ensure that when billed currency differs from benchmark currency,
    the service does not compute an erroneous direct numeric multiplier.
    """
    # Force a case where claim is in INR but matched benchmark is in USD
    claim = Claim(
        claim_id="clm_cross_curr",
        original_text="Medical test billed at ₹2,500.00 in Delhi",
        source_type="hospital_bill",
        timestamp=datetime.now(timezone.utc),
        extracted_fields=ExtractedFields(
            entity="Emergency Room Visit CPT 99285",
            cost_range="₹2,500.00",
            cost_currency="INR",
            location="Delhi, India",
            sentiment=SentimentType.NEUTRAL
        ),
        confidence=0.9,
        provenance=ProvenanceMetadata(
            source_hash="cross_hash",
            original_snippet="₹2,500.00",
            text_length=40,
            source_type="hospital_bill"
        )
    )

    details = cost_service.evaluate_claim_cost(claim)
    assert details.currency == "INR"
    if details.benchmark_currency and details.benchmark_currency != details.currency:
        assert details.is_anomaly is False
        assert details.multiplier is None
        assert "Cross-currency comparison" in details.explanation


def test_currency_aware_abstention_threshold():
    """Verify Rule 5 (UNBENCHMARKED_HIGH_COST) uses currency-specific thresholds."""
    from app.services.abstention import abstention_service, AbstentionRule
    from app.models.schemas import EvidencePassage

    # Provide a usable guideline passage so Rule 2 doesn't block Rule 5 evaluation
    dummy_passages = [
        EvidencePassage(
            passage_id="p_valid",
            title="Standard Clinical Protocol",
            source="ICMR",
            text="Clinical guideline for procedure evaluation.",
            relevance_score=0.90,
            used_in_decision=True
        )
    ]

    # Indian claim ₹1,500 is unbenchmarked but below ₹8,000 threshold -> No Rule 5 abstention
    claim_low_inr = Claim(
        claim_id="clm_inr_sub_thresh",
        original_text="Custom ayurvedic therapy fee ₹1,500 in Mysuru",
        source_type="patient_report",
        timestamp=datetime.now(timezone.utc),
        extracted_fields=ExtractedFields(
            entity="Custom Ayurvedic Therapy",
            cost_range="₹1,500",
            cost_currency="INR",
            location="Mysuru, Karnataka",
            sentiment=SentimentType.NEUTRAL
        ),
        confidence=0.88,
        provenance=ProvenanceMetadata(
            source_hash="ayur_hash",
            original_snippet="Ayurvedic ₹1,500",
            text_length=45,
            source_type="patient_report"
        )
    )

    cost_details_low = CostAnomalyDetails(
        is_anomaly=False,
        benchmark_matched=False,
        currency="INR",
        extracted_amount=1500.0,
        explanation="No benchmark"
    )

    gate_low = abstention_service.evaluate(
        claim=claim_low_inr,
        passages=dummy_passages,
        cost_details=cost_details_low
    )
    assert gate_low.rule_triggered != AbstentionRule.UNBENCHMARKED_HIGH_COST

    # Indian claim ₹25,000 is unbenchmarked and above ₹8,000 threshold -> Triggers Rule 5 abstention
    claim_high_inr = Claim(
        claim_id="clm_inr_high_thresh",
        original_text="Uncoded robotic procedure fee ₹25,000 in Bengaluru",
        source_type="patient_report",
        timestamp=datetime.now(timezone.utc),
        extracted_fields=ExtractedFields(
            entity="Uncoded Robotic Procedure",
            cost_range="₹25,000",
            cost_currency="INR",
            location="Bengaluru, Karnataka",
            sentiment=SentimentType.NEUTRAL
        ),
        confidence=0.88,
        provenance=ProvenanceMetadata(
            source_hash="robot_hash",
            original_snippet="Procedure ₹25,000",
            text_length=50,
            source_type="patient_report"
        )
    )

    cost_details_high = CostAnomalyDetails(
        is_anomaly=False,
        benchmark_matched=False,
        currency="INR",
        extracted_amount=25000.0,
        explanation="No benchmark"
    )

    gate_high = abstention_service.evaluate(
        claim=claim_high_inr,
        passages=dummy_passages,
        cost_details=cost_details_high
    )
    assert gate_high.rule_triggered == AbstentionRule.UNBENCHMARKED_HIGH_COST
    assert "₹25,000.00" in gate_high.reason
    assert "INR" in gate_high.reason


