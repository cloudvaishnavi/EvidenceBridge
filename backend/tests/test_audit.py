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

    abstention_decision = AbstentionDecision(should_abstain=False)

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
