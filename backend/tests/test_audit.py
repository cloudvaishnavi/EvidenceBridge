"""
Unit tests for the Decision Audit Trail Service (Layer 3).
Verifies step-by-step decision graphs, passage tracking, and audit assembly.
"""

from datetime import datetime, timezone
import pytest

from app.models.schemas import (
    Claim,
    CostAnomalyDetails,
    EvidencePassage,
    ExtractedFields,
    ProvenanceMetadata,
    SentimentType,
    VerificationAction,
    VerificationResult,
    VerificationVerdict,
)
from app.services.abstention import AbstentionDecision
from app.services.audit import AuditService


def test_create_step():
    step = AuditService.create_step(
        step_name="EXTRACTION",
        input_summary="Raw clinical note input",
        output_summary="Extracted entity and confidence",
        details={"entity": "Metformin", "confidence": 0.95}
    )
    assert step.step_name == "EXTRACTION"
    assert step.input_summary == "Raw clinical note input"
    assert step.output_summary == "Extracted entity and confidence"
    assert step.details["entity"] == "Metformin"
    assert step.timestamp is not None


def test_record_full_audit_assembly():
    now = datetime.now(timezone.utc)
    claim = Claim(
        claim_id="clm_audit_001",
        original_text="Patient prescribed Lisinopril 20mg daily for Stage 2 hypertension. BP reduced to 122/78 mmHg.",
        source_type="clinical_note",
        timestamp=now,
        extracted_fields=ExtractedFields(
            entity="Lisinopril 20 mg",
            effect_or_outcome="Blood pressure reduced to 122/78 mmHg",
            cost_range=None,
            sentiment=SentimentType.POSITIVE
        ),
        confidence=0.94,
        provenance=ProvenanceMetadata(
            source_hash="hash123",
            original_snippet="Patient prescribed Lisinopril",
            text_length=85,
            source_type="clinical_note",
            ingested_at=now
        )
    )

    passages = [
        EvidencePassage(
            passage_id="pas_101",
            guideline_id="GUIDE-HTN-002",
            title="ACC/AHA Guideline for Prevention and Management of High Blood Pressure",
            source="ACC/AHA",
            text="First-line therapy for Stage 2 hypertension includes ACE inhibitors such as Lisinopril...",
            relevance_score=0.91,
            used_in_decision=True
        ),
        EvidencePassage(
            passage_id="pas_102",
            guideline_id="GUIDE-DIAB-001",
            title="ADA Standards of Care: Metformin in Type 2 Diabetes",
            source="ADA",
            text="Metformin is first-line for diabetes...",
            relevance_score=0.18,
            used_in_decision=False,
            discard_reason="Below relevance threshold 0.35 (score: 0.18)"
        )
    ]

    cost_details = CostAnomalyDetails(
        is_anomaly=False,
        explanation="No cost reported."
    )

    verification = VerificationResult(
        verification_id="ver_audit_001",
        claim_id=claim.claim_id,
        support_score=0.92,
        verdict=VerificationVerdict.SUPPORTED,
        action=VerificationAction.ACCEPT,
        reasoning="ACC/AHA guideline confirms Lisinopril 20mg as recommended first-line therapy for hypertension with expected BP reduction.",
        evidence_snippets=[],
        passages_considered=passages,
        cost_anomaly_flag=False,
        anomaly_details=cost_details,
        abstain_reason=None,
        verified_at=now
    )

    abstention_decision = AbstentionDecision(
        should_abstain=False,
        details={
            "original_model_verdict": VerificationVerdict.SUPPORTED.value,
            "conflict_assessment": {
                "has_conflict": False,
                "supporting_passage_ids": [],
                "opposing_passage_ids": []
            },
            "conflict_assessment_valid": False
        }
    )

    audit_trail = AuditService.record_full_audit(
        claim=claim,
        verification=verification,
        passages=passages,
        cost_details=cost_details,
        abstention_decision=abstention_decision
    )

    # Validate audit structure
    assert audit_trail.audit_id.startswith("aud_")
    assert audit_trail.claim_id == "clm_audit_001"
    assert audit_trail.verification_id == "ver_audit_001"
    assert len(audit_trail.steps) == 7

    # Verify all 7 decision steps exist in exact order
    step_names = [s.step_name for s in audit_trail.steps]
    expected_steps = [
        "EXTRACTION",
        "PROVENANCE",
        "HYBRID_RETRIEVAL",
        "COST_AUDIT",
        "CLINICAL_VERIFICATION",
        "ABSTENTION_GATE",
        "FINAL_ACTION"
    ]
    assert step_names == expected_steps

    # Verify passage tracking (used vs discarded)
    assert len(audit_trail.passages_considered) == 2
    assert audit_trail.passages_considered[0].used_in_decision is True
    assert audit_trail.passages_considered[1].used_in_decision is False
    assert "Below relevance threshold" in audit_trail.passages_considered[1].discard_reason

    # Verify final verdict and action
    assert audit_trail.final_action == VerificationAction.ACCEPT
    assert audit_trail.final_verdict == VerificationVerdict.SUPPORTED
    assert audit_trail.abstain_triggered is False
    abstention_step = next(step for step in audit_trail.steps if step.step_name == "ABSTENTION_GATE")
    assert abstention_step.details["details"]["original_model_verdict"] == "supported"
    assert abstention_step.details["details"]["conflict_assessment"]["has_conflict"] is False


def test_audit_trail_preserves_original_model_verdict_on_abstention_override():
    """Verify that when an abstention safety gate overrides the model, original verdict is preserved."""
    now = datetime.now(timezone.utc)
    claim = Claim(
        claim_id="clm_override_abstain",
        original_text="Patient prescribed experimental peptide therapy without public benchmark billed at $2,400.",
        source_type="hospital_bill",
        timestamp=now,
        extracted_fields=ExtractedFields(
            entity="Experimental Peptide",
            cost_range="$2,400",
            effect_or_outcome="Therapy ongoing",
            sentiment=SentimentType.NEUTRAL,
        ),
        confidence=0.88,
        provenance=ProvenanceMetadata(
            source_hash="sha256_mock_hash",
            original_snippet="Patient prescribed experimental peptide",
            text_length=95,
            source_type="hospital_bill",
            ingested_at=now,
        )
    )

    passages = [
        EvidencePassage(
            passage_id="pas_exp_01",
            title="Investigational Peptide Research Brief",
            source="NIH",
            text="Peptide under clinical trial investigation.",
            relevance_score=0.72,
            used_in_decision=True
        )
    ]

    cost_details = CostAnomalyDetails(
        is_anomaly=False,
        extracted_amount=2400.0,
        threshold_multiplier=3.0,
        explanation="No public pricing benchmark found for entity 'Experimental Peptide'. Auditing deferred.",
        benchmark_name=None,
    )

    # Final verification after abstention gate forced ABSTAIN
    verification = VerificationResult(
        verification_id="ver_override_01",
        claim_id=claim.claim_id,
        support_score=0.0,
        verdict=VerificationVerdict.INSUFFICIENT_EVIDENCE,
        action=VerificationAction.ABSTAIN,
        reasoning="Pre-flight or post-gate safety abstention.",
        evidence_snippets=[],
        passages_considered=passages,
        cost_anomaly_flag=False,
        anomaly_details=cost_details,
        abstain_reason="Unbenchmarked high cost ($2,400.00) exceeds safety threshold",
        verified_at=now,
    )

    abstention_decision = AbstentionDecision(
        should_abstain=True,
        rule_triggered="UNBENCHMARKED_HIGH_COST",
        reason="Unbenchmarked high cost ($2,400.00) exceeds safety threshold",
        details={
            "original_model_verdict": "supported",
            "extracted_amount": 2400.0,
            "threshold": 100.0,
        }
    )

    # Record audit trail passing raw model outputs before policy override
    audit_trail = AuditService.record_full_audit(
        claim=claim,
        verification=verification,
        passages=passages,
        cost_details=cost_details,
        abstention_decision=abstention_decision,
        raw_model_verdict=VerificationVerdict.SUPPORTED,
        raw_model_support_score=0.88,
        raw_model_reasoning="Trial brief indicates positive response, but cost is unbenchmarked.",
    )

    assert len(audit_trail.steps) == 7
    # Original model assessment preserved
    assert audit_trail.raw_model_verdict == "supported"
    assert audit_trail.raw_model_support_score == 0.88
    # Policy override tracked
    assert audit_trail.policy_override_applied is True
    assert "UNBENCHMARKED_HIGH_COST" in audit_trail.policy_override_reason
    assert audit_trail.final_action == VerificationAction.ABSTAIN
    assert audit_trail.final_verdict == VerificationVerdict.INSUFFICIENT_EVIDENCE

    # Check Step 5 (CLINICAL_VERIFICATION) retains raw verdict
    step5 = next(s for s in audit_trail.steps if s.step_name == "CLINICAL_VERIFICATION")
    assert step5.details["raw_model_verdict"] == "supported"
    assert step5.details["raw_model_support_score"] == 0.88

    # Check Step 6 (ABSTENTION_GATE) records override
    step6 = next(s for s in audit_trail.steps if s.step_name == "ABSTENTION_GATE")
    assert step6.details["should_abstain"] is True
    assert step6.details["policy_override_applied"] is True

    # Check Step 7 (FINAL_ACTION) records policy enforcement
    step7 = next(s for s in audit_trail.steps if s.step_name == "FINAL_ACTION")
    assert step7.details["final_action"] == "abstain"
    assert step7.details["policy_override_applied"] is True


def test_audit_trail_preserves_original_model_verdict_on_cost_anomaly_flag():
    """Verify that when a cost anomaly forces FLAG on a supported claim, both are visible."""
    now = datetime.now(timezone.utc)
    claim = Claim(
        claim_id="clm_saline_audit",
        original_text="MIDWEST HOSPITAL: 0.9% Sodium Chloride IV Solution 1000mL bag billed at $720.00",
        source_type="hospital_bill",
        timestamp=now,
        extracted_fields=ExtractedFields(
            entity="0.9% Sodium Chloride IV Solution 1000mL",
            cost_range="$720.00",
            effect_or_outcome="Hydration completed",
            sentiment=SentimentType.NEUTRAL,
        ),
        confidence=0.96,
        provenance=ProvenanceMetadata(
            source_hash="sha256_saline_test",
            original_snippet="0.9% Sodium Chloride IV Solution 1000mL bag billed at $720.00",
            text_length=76,
            source_type="hospital_bill",
            ingested_at=now,
        )
    )

    passages = [
        EvidencePassage(
            passage_id="pas_sal_01",
            title="USP Guidelines: 0.9% Sodium Chloride IV Solution",
            source="USP",
            text="Normal saline is first-line fluid for intravascular volume replacement.",
            relevance_score=0.94,
            used_in_decision=True
        )
    ]

    cost_details = CostAnomalyDetails(
        is_anomaly=True,
        extracted_amount=720.0,
        benchmark_min=5.0,
        benchmark_max=45.0,
        multiplier=16.0,
        threshold_multiplier=3.0,
        severity="extreme",
        explanation="Billed amount of $720.00 is 16.0× higher than benchmark max of $45.00",
        benchmark_name="0.9% Sodium Chloride IV Solution 1,000 mL",
        benchmark_source="CMS Medicare Part B / Fair Health 2026",
        cpt_code="J7030",
    )

    # Verification has action=FLAG due to cost anomaly, but verdict=SUPPORTED
    verification = VerificationResult(
        verification_id="ver_saline_01",
        claim_id=claim.claim_id,
        support_score=0.92,
        verdict=VerificationVerdict.SUPPORTED,
        action=VerificationAction.FLAG,
        reasoning="Normal saline is clinically indicated, but price is an extreme 16× markup anomaly.",
        evidence_snippets=[],
        passages_considered=passages,
        cost_anomaly_flag=True,
        anomaly_details=cost_details,
        abstain_reason=None,
        verified_at=now,
    )

    abstention_decision = AbstentionDecision(
        should_abstain=False,
        details={"original_model_verdict": "supported"}
    )

    audit_trail = AuditService.record_full_audit(
        claim=claim,
        verification=verification,
        passages=passages,
        cost_details=cost_details,
        abstention_decision=abstention_decision,
        raw_model_verdict=VerificationVerdict.SUPPORTED,
        raw_model_support_score=0.92,
        raw_model_reasoning="Normal saline is fully indicated per USP.",
    )

    assert len(audit_trail.steps) == 7
    assert audit_trail.raw_model_verdict == "supported"
    assert audit_trail.final_action == VerificationAction.FLAG
    assert audit_trail.final_verdict == VerificationVerdict.SUPPORTED
    assert audit_trail.cost_anomaly_flag is True
    assert audit_trail.policy_override_applied is True
    assert "Cost anomaly detected" in audit_trail.policy_override_reason

    # Verify Step 4 (COST_AUDIT) contains explicit benchmark details
    step4 = next(s for s in audit_trail.steps if s.step_name == "COST_AUDIT")
    assert step4.details["benchmark_matched"] is True
    assert "0.9% Sodium Chloride" in step4.details["benchmark_name"]
    assert step4.details["cpt_code"] == "J7030"
    assert step4.details["multiplier"] == 16.0
    assert step4.details["severity"] == "extreme"

    # Verify Step 7 (FINAL_ACTION) notes the cost anomaly override
    step7 = next(s for s in audit_trail.steps if s.step_name == "FINAL_ACTION")
    assert step7.details["policy_override_applied"] is True
    assert step7.details["final_action"] == "flag"


def test_audit_trail_provenance_and_passages_integrity():
    """Verify provenance cryptographic verification and hybrid passage tracking."""
    now = datetime.now(timezone.utc)
    claim = Claim(
        claim_id="clm_prov_audit",
        original_text="Cardiology follow-up note for Metformin 500mg daily in Atlanta, GA.",
        source_type="clinical_note",
        timestamp=now,
        extracted_fields=ExtractedFields(
            entity="Metformin 500mg",
            location_city="Atlanta, GA",
            sentiment=SentimentType.NEUTRAL,
        ),
        confidence=0.92,
        provenance=ProvenanceMetadata(
            source_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            original_snippet="Cardiology follow-up note for Metformin",
            text_length=68,
            source_type="clinical_note",
            source_url="ehr://emory-healthcare/pt-992",
            ingested_at=now,
        )
    )

    passages = [
        EvidencePassage(
            passage_id="pas_met_01",
            guideline_id="GUIDE-DIAB-001",
            title="ADA Standards of Care: Metformin",
            source="ADA",
            text="Metformin is first-line pharmacologic treatment.",
            relevance_score=0.89,
            used_in_decision=True,
            discard_reason=None,
        ),
        EvidencePassage(
            passage_id="pas_mig_01",
            guideline_id="GUIDE-MIGR-005",
            title="AHS Guideline: Acute Migraine",
            source="AHS",
            text="Triptans are first-line for acute migraine.",
            relevance_score=0.12,
            used_in_decision=False,
            discard_reason="Below relevance threshold 0.35 (score: 0.12)",
        )
    ]

    cost_details = CostAnomalyDetails(
        is_anomaly=False,
        explanation="No cost reported."
    )

    verification = VerificationResult(
        verification_id="ver_prov_01",
        claim_id=claim.claim_id,
        support_score=0.90,
        verdict=VerificationVerdict.SUPPORTED,
        action=VerificationAction.ACCEPT,
        reasoning="ADA guideline supports Metformin.",
        evidence_snippets=[],
        passages_considered=passages,
        cost_anomaly_flag=False,
        anomaly_details=cost_details,
        abstain_reason=None,
        verified_at=now,
    )

    abstention_decision = AbstentionDecision(should_abstain=False)

    audit_trail = AuditService.record_full_audit(
        claim=claim,
        verification=verification,
        passages=passages,
        cost_details=cost_details,
        abstention_decision=abstention_decision,
        raw_model_verdict=VerificationVerdict.SUPPORTED,
        raw_model_support_score=0.90,
    )

    # Step 1: Extraction check
    step1 = audit_trail.steps[0]
    assert step1.step_name == "EXTRACTION"
    assert "Metformin 500mg" in step1.output_summary
    assert step1.details["confidence"] == 0.92

    # Step 2: Provenance check
    step2 = audit_trail.steps[1]
    assert step2.step_name == "PROVENANCE"
    assert step2.details["source_hash"] == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert step2.details["tamper_check_passed"] is True
    assert "ehr://emory-healthcare/pt-992" in step2.details["source_url"]

    # Step 3: Hybrid Retrieval check
    step3 = audit_trail.steps[2]
    assert step3.step_name == "HYBRID_RETRIEVAL"
    assert step3.details["used_count"] == 1
    assert step3.details["discarded_count"] == 1
    assert step3.details["passages"][1]["discard_reason"] == "Below relevance threshold 0.35 (score: 0.12)"

    # Step 4: Cost audit check
    step4 = audit_trail.steps[3]
    assert step4.step_name == "COST_AUDIT"
    assert "No numeric cost figure" in step4.output_summary


def test_end_to_end_extract_verify_and_fetch_audit_trail():
    """Verify that end-to-end flow produces and returns a complete 7-stage decision trail via API."""
    from unittest.mock import AsyncMock, patch
    from fastapi.testclient import TestClient
    from app.main import app

    from app.services.auth import (
        create_access_token,
        DEMO_USER_ID,
        DEMO_USER_EMAIL,
        DEMO_USER_NAME,
    )
    client = TestClient(app)
    token = create_access_token(DEMO_USER_ID, DEMO_USER_EMAIL, DEMO_USER_NAME)
    client.headers["Authorization"] = f"Bearer {token}"
    now = datetime.now(timezone.utc)

    # 1. Build a realistic 7-stage audit trail
    claim = Claim(
        claim_id="clm_e2e_audit",
        original_text="Hospital bill: Normal Saline IV bag billed at $720.00",
        source_type="hospital_bill",
        timestamp=now,
        extracted_fields=ExtractedFields(
            entity="0.9% Sodium Chloride IV Solution",
            cost_range="$720.00",
            effect_or_outcome="Hydration completed",
            sentiment=SentimentType.NEUTRAL,
        ),
        confidence=0.95,
        provenance=ProvenanceMetadata(
            source_hash="sha256_mock_digest_12345",
            original_snippet="Normal Saline IV bag billed at $720.00",
            text_length=51,
            source_type="hospital_bill",
            ingested_at=now,
        )
    )

    passages = [
        EvidencePassage(
            passage_id="pas_e2e_01",
            title="USP Standard: 0.9% Sodium Chloride",
            source="USP",
            text="First-line hydration solution.",
            relevance_score=0.92,
            used_in_decision=True,
        )
    ]

    cost_details = CostAnomalyDetails(
        is_anomaly=True,
        extracted_amount=720.0,
        benchmark_min=5.0,
        benchmark_max=45.0,
        multiplier=16.0,
        threshold_multiplier=3.0,
        severity="extreme",
        explanation="Billed amount of $720.00 is 16.0× higher than benchmark max of $45.00",
        benchmark_name="0.9% Sodium Chloride IV Solution",
        benchmark_source="CMS / Fair Health",
    )

    verification = VerificationResult(
        verification_id="ver_e2e_audit",
        claim_id=claim.claim_id,
        support_score=0.92,
        verdict=VerificationVerdict.SUPPORTED,
        action=VerificationAction.FLAG,
        reasoning="Clinically indicated, but price is an extreme 16× markup anomaly.",
        evidence_snippets=[],
        passages_considered=passages,
        cost_anomaly_flag=True,
        anomaly_details=cost_details,
        abstain_reason=None,
        verified_at=now,
    )

    abstention_decision = AbstentionDecision(
        should_abstain=False,
        details={"original_model_verdict": "supported"}
    )

    audit_trail = AuditService.record_full_audit(
        claim=claim,
        verification=verification,
        passages=passages,
        cost_details=cost_details,
        abstention_decision=abstention_decision,
        raw_model_verdict=VerificationVerdict.SUPPORTED,
        raw_model_support_score=0.92,
        raw_model_reasoning="Normal saline indicated.",
    )

    # 2. Test GET /audit/{claim_id}
    with patch("app.api.routes.storage_service.get_audit_trail_by_claim_id", new_callable=AsyncMock) as mock_get_by_claim:
        mock_get_by_claim.return_value = audit_trail
        resp = client.get(f"/audit/{claim.claim_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        trail = data["audit_trail"]
        assert trail["claim_id"] == "clm_e2e_audit"
        assert trail["verification_id"] == "ver_e2e_audit"
        assert len(trail["steps"]) == 7

        # Check all 7 stages exist in order
        expected_stages = [
            "EXTRACTION",
            "PROVENANCE",
            "HYBRID_RETRIEVAL",
            "COST_AUDIT",
            "CLINICAL_VERIFICATION",
            "ABSTENTION_GATE",
            "FINAL_ACTION"
        ]
        assert [s["step_name"] for s in trail["steps"]] == expected_stages

        # Check raw model verdict and policy override
        assert trail["raw_model_verdict"] == "supported"
        assert trail["raw_model_support_score"] == 0.92
        assert trail["policy_override_applied"] is True
        assert trail["final_action"] == "flag"
        assert trail["cost_anomaly_flag"] is True

        # Check that each step has non-empty input and output summaries
        for step in trail["steps"]:
            assert step["input_summary"]
            assert step["output_summary"]
            assert step["details"] is not None

    # 3. Test GET /audit/verification/{verification_id}
    with patch("app.api.routes.storage_service.get_audit_trail_by_verification_id", new_callable=AsyncMock) as mock_get_by_verif:
        mock_get_by_verif.return_value = audit_trail
        resp = client.get(f"/audit/verification/{verification.verification_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["audit_trail"]["verification_id"] == "ver_e2e_audit"
