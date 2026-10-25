"""
End-to-End Tests for Controlled Clinical Evaluation Cases (Step 3).
Validates that extraction -> retrieval -> cost audit -> abstention -> final action
determines expected outcomes across all major verdict paths without live Ollama dependency.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import pytest

from app.models.schemas import (
    Claim,
    CostAnomalyDetails,
    ExtractedFields,
    ProvenanceMetadata,
    SentimentType,
    VerificationAction,
    VerificationResult,
    VerificationVerdict,
)
from app.services.abstention import abstention_service, AbstentionRule
from app.services.audit import audit_service
from app.services.cost_anomaly import cost_anomaly_service
from app.services.verification import VerificationService


@pytest.fixture
def controlled_cases():
    cases_path = Path(__file__).parent.parent.parent / "data" / "evaluation" / "controlled_cases.json"
    assert cases_path.exists(), f"Controlled cases file not found at {cases_path}"
    with open(cases_path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def verification_service():
    return VerificationService()


def test_controlled_cases_file_integrity(controlled_cases):
    """Confirm the evaluation set contains the expected case categories and structure."""
    assert len(controlled_cases) >= 6
    required_keys = {
        "case_id", "category", "raw_text", "source_type",
        "expected_entity", "gold_verdict", "gold_action",
        "cost_anomaly_flag", "note"
    }
    for case in controlled_cases:
        assert required_keys.issubset(case.keys()), f"Case {case.get('case_id')} missing keys"
        assert case["gold_verdict"] in ("supported", "contradicted", "insufficient_evidence", "partially_supported")
        assert case["gold_action"] in ("ACCEPT", "FLAG", "ABSTAIN")
        assert isinstance(case["cost_anomaly_flag"], bool)


def test_controlled_cases_retrieval_and_cost_anomalies(controlled_cases, verification_service):
    """
    Verify that each controlled case achieves expected retrieval matching
    and cost anomaly detection against the local knowledge base.
    """
    cases_by_id = {c["case_id"]: c for c in controlled_cases}

    # Case 1: Metformin (T2D standard therapy, normal price)
    c1 = cases_by_id["ctrl_01_supported_metformin"]
    passages1 = verification_service.retrieve_hybrid_passages(c1["expected_entity"], c1["raw_text"], k=5)
    assert len(passages1) > 0
    assert passages1[0].guideline_id == "GUIDE-DIAB-001"
    assert passages1[0].used_in_decision is True
    claim1 = Claim(
        claim_id=c1["case_id"],
        original_text=c1["raw_text"],
        source_type=c1["source_type"],
        timestamp=datetime.now(timezone.utc),
        extracted_fields=ExtractedFields(entity=c1["expected_entity"], cost_range="$15.00"),
        confidence=0.95,
        provenance=ProvenanceMetadata(source_hash="h1", original_snippet="Metformin", text_length=len(c1["raw_text"]), source_type=c1["source_type"])
    )
    cost1 = cost_anomaly_service.evaluate_claim_cost(claim1)
    assert cost1.is_anomaly is False
    assert cost1.extracted_amount == 15.0

    # Case 2: Brain MRI (CPT 70551 with red flags, normal price)
    c2 = cases_by_id["ctrl_02_supported_brain_mri"]
    passages2 = verification_service.retrieve_hybrid_passages(c2["expected_entity"], c2["raw_text"], k=5)
    assert len(passages2) > 0
    top2 = passages2[0]
    assert top2.guideline_id == "GUIDE-IMAG-013"
    assert "Brain" in top2.title
    assert "70551" in top2.title
    assert top2.used_in_decision is True
    # Verify Knee MRI is not mistakenly accepted as usable evidence
    knee_matches = [p for p in passages2 if p.guideline_id == "GUIDE-IMAG-007"]
    for kp in knee_matches:
        assert kp.used_in_decision is False
        assert "mismatch" in kp.discard_reason.lower()

    claim2 = Claim(
        claim_id=c2["case_id"],
        original_text=c2["raw_text"],
        source_type=c2["source_type"],
        timestamp=datetime.now(timezone.utc),
        extracted_fields=ExtractedFields(entity=c2["expected_entity"], cost_range="$650.00"),
        confidence=0.95,
        provenance=ProvenanceMetadata(source_hash="h2", original_snippet="MRI Brain", text_length=len(c2["raw_text"]), source_type=c2["source_type"])
    )
    cost2 = cost_anomaly_service.evaluate_claim_cost(claim2)
    assert cost2.is_anomaly is False
    assert cost2.extracted_amount == 650.0

    # Case 3: Antibiotic for viral bronchitis (Contradicted)
    c3 = cases_by_id["ctrl_03_contradicted_bronchitis_antibiotic"]
    passages3 = verification_service.retrieve_hybrid_passages(c3["expected_entity"], c3["raw_text"], k=5)
    assert len(passages3) > 0
    assert passages3[0].guideline_id == "GUIDE-RESP-011"
    assert passages3[0].used_in_decision is True

    # Case 4: Extreme Saline Markup ($720 vs $45 max)
    c4 = cases_by_id["ctrl_04_cost_anomaly_saline_extreme"]
    claim4 = Claim(
        claim_id=c4["case_id"],
        original_text=c4["raw_text"],
        source_type=c4["source_type"],
        timestamp=datetime.now(timezone.utc),
        extracted_fields=ExtractedFields(entity=c4["expected_entity"], cost_range="$720.00"),
        confidence=0.95,
        provenance=ProvenanceMetadata(source_hash="h4", original_snippet="0.9% Normal Saline", text_length=len(c4["raw_text"]), source_type=c4["source_type"])
    )
    cost4 = cost_anomaly_service.evaluate_claim_cost(claim4)
    assert cost4.is_anomaly is True
    assert cost4.multiplier >= 15.0
    assert cost4.severity == "extreme"

    # Case 5: Routine Venipuncture ($125 vs $25 max)
    c5 = cases_by_id["ctrl_05_cost_anomaly_venipuncture"]
    claim5 = Claim(
        claim_id=c5["case_id"],
        original_text=c5["raw_text"],
        source_type=c5["source_type"],
        timestamp=datetime.now(timezone.utc),
        extracted_fields=ExtractedFields(entity=c5["expected_entity"], cost_range="$125.00"),
        confidence=0.95,
        provenance=ProvenanceMetadata(source_hash="h5", original_snippet="Routine Venipuncture", text_length=len(c5["raw_text"]), source_type=c5["source_type"])
    )
    cost5 = cost_anomaly_service.evaluate_claim_cost(claim5)
    assert cost5.is_anomaly is True
    assert cost5.multiplier >= 5.0

    # Case 6: Rare entity with zero guidelines (Ozone infusion)
    c6 = cases_by_id["ctrl_06_abstain_rare_unsupported_entity"]
    passages6 = verification_service.retrieve_hybrid_passages(c6["expected_entity"], c6["raw_text"], k=5)
    usable6 = [p for p in passages6 if p.used_in_decision]
    assert len(usable6) == 0  # All passages should be discarded


def test_controlled_cases_abstention_and_final_actions(controlled_cases, verification_service):
    """
    Test deterministic safety policy gate outcomes and final action routing
    across all controlled cases.
    """
    now = datetime.now(timezone.utc)
    cases_by_id = {c["case_id"]: c for c in controlled_cases}

    # Test Case 6: Rare entity triggers NO_RELEVANT_EVIDENCE abstention
    c6 = cases_by_id["ctrl_06_abstain_rare_unsupported_entity"]
    claim6 = Claim(
        claim_id=c6["case_id"],
        original_text=c6["raw_text"],
        source_type=c6["source_type"],
        timestamp=now,
        extracted_fields=ExtractedFields(entity=c6["expected_entity"], cost_range="$180.00"),
        confidence=0.88,
        provenance=ProvenanceMetadata(source_hash="h6", original_snippet=c6["expected_entity"], text_length=len(c6["raw_text"]), source_type=c6["source_type"])
    )
    passages6 = verification_service.retrieve_hybrid_passages(claim6.extracted_fields.entity, claim6.original_text, k=5)
    cost6 = cost_anomaly_service.evaluate_claim_cost(claim6)
    gate6 = abstention_service.evaluate(claim6, passages6, cost6)
    assert gate6.should_abstain is True
    assert gate6.rule_triggered in (AbstentionRule.NO_RELEVANT_EVIDENCE, AbstentionRule.UNBENCHMARKED_HIGH_COST)

    # Test Case 7: Unbenchmarked High Cost ($12,500) triggers Rule 5 UNBENCHMARKED_HIGH_COST
    c7 = cases_by_id["ctrl_07_abstain_unbenchmarked_high_cost"]
    claim7 = Claim(
        claim_id=c7["case_id"],
        original_text=c7["raw_text"],
        source_type=c7["source_type"],
        timestamp=now,
        extracted_fields=ExtractedFields(entity=c7["expected_entity"], cost_range="$12,500.00"),
        confidence=0.90,
        provenance=ProvenanceMetadata(source_hash="h7", original_snippet=c7["expected_entity"], text_length=len(c7["raw_text"]), source_type=c7["source_type"])
    )
    passages7 = verification_service.retrieve_hybrid_passages(claim7.extracted_fields.entity, claim7.original_text, k=5)
    cost7 = cost_anomaly_service.evaluate_claim_cost(claim7)
    gate7 = abstention_service.evaluate(claim7, passages7, cost7)
    assert gate7.should_abstain is True
    assert gate7.rule_triggered in (AbstentionRule.NO_RELEVANT_EVIDENCE, AbstentionRule.UNBENCHMARKED_HIGH_COST)

    # Test Case 4: Extreme Saline Markup -> Model said supported, but policy overrides to FLAG
    c4 = cases_by_id["ctrl_04_cost_anomaly_saline_extreme"]
    claim4 = Claim(
        claim_id=c4["case_id"],
        original_text=c4["raw_text"],
        source_type=c4["source_type"],
        timestamp=now,
        extracted_fields=ExtractedFields(entity=c4["expected_entity"], cost_range="$720.00"),
        confidence=0.95,
        provenance=ProvenanceMetadata(source_hash="h4", original_snippet=c4["expected_entity"], text_length=len(c4["raw_text"]), source_type=c4["source_type"])
    )
    cost4 = cost_anomaly_service.evaluate_claim_cost(claim4)
    action4, reason4 = verification_service._determine_action(
        verdict=VerificationVerdict.SUPPORTED,
        support_score=0.92,
        has_cost_anomaly=cost4.is_anomaly
    )
    assert action4 == VerificationAction.FLAG  # Cost anomaly forces FLAG

    # Test Case 3: Contradicted claim -> FLAG
    action3, _ = verification_service._determine_action(
        verdict=VerificationVerdict.CONTRADICTED,
        support_score=0.10,
        has_cost_anomaly=False
    )
    assert action3 == VerificationAction.FLAG

    # Test Case 2: Brain MRI supported + normal cost -> ACCEPT
    c2 = cases_by_id["ctrl_02_supported_brain_mri"]
    claim2 = Claim(
        claim_id=c2["case_id"],
        original_text=c2["raw_text"],
        source_type=c2["source_type"],
        timestamp=now,
        extracted_fields=ExtractedFields(entity=c2["expected_entity"], cost_range="$650.00"),
        confidence=0.95,
        provenance=ProvenanceMetadata(source_hash="h2", original_snippet=c2["expected_entity"], text_length=len(c2["raw_text"]), source_type=c2["source_type"])
    )
    cost2 = cost_anomaly_service.evaluate_claim_cost(claim2)
    action2, _ = verification_service._determine_action(
        verdict=VerificationVerdict.SUPPORTED,
        support_score=0.88,
        has_cost_anomaly=cost2.is_anomaly
    )
    assert action2 == VerificationAction.ACCEPT


def test_controlled_cases_audit_trail_dual_retention(controlled_cases, verification_service):
    """
    Ensure the 7-stage audit trail retains both raw model verdict and final policy override
    when auditing controlled cases.
    """
    now = datetime.now(timezone.utc)
    cases_by_id = {c["case_id"]: c for c in controlled_cases}

    # Case 4: Extreme markup on normal saline
    c4 = cases_by_id["ctrl_04_cost_anomaly_saline_extreme"]
    claim = Claim(
        claim_id=c4["case_id"],
        original_text=c4["raw_text"],
        source_type=c4["source_type"],
        timestamp=now,
        extracted_fields=ExtractedFields(entity=c4["expected_entity"], cost_range="$720.00"),
        confidence=0.95,
        provenance=ProvenanceMetadata(source_hash="h4", original_snippet=c4["expected_entity"], text_length=len(c4["raw_text"]), source_type=c4["source_type"])
    )
    passages = verification_service.retrieve_hybrid_passages(claim.extracted_fields.entity, claim.original_text, k=5)
    cost_details = cost_anomaly_service.evaluate_claim_cost(claim)

    verification = VerificationResult(
        verification_id="ver_ctrl_04",
        claim_id=claim.claim_id,
        support_score=0.92,
        verdict=VerificationVerdict.SUPPORTED,
        action=VerificationAction.FLAG,
        reasoning="Normal saline is standard for hydration, but billed cost is a 16.0x extreme anomaly.",
        evidence_snippets=[],
        passages_considered=passages,
        cost_anomaly_flag=cost_details.is_anomaly,
        anomaly_details=cost_details,
        abstain_reason=None,
        verified_at=now,
    )

    abstention_decision = abstention_service.evaluate(
        claim=claim,
        passages=passages,
        cost_details=cost_details,
        model_verdict=VerificationVerdict.SUPPORTED,
        model_support_score=0.92,
        model_reasoning="Normal saline indicated.",
    )

    audit_trail = audit_service.record_full_audit(
        claim=claim,
        verification=verification,
        passages=passages,
        cost_details=cost_details,
        abstention_decision=abstention_decision,
        raw_model_verdict=VerificationVerdict.SUPPORTED,
        raw_model_support_score=0.92,
        raw_model_reasoning="Normal saline indicated.",
    )

    assert len(audit_trail.steps) == 7
    # Dual retention verified
    assert audit_trail.raw_model_verdict == "supported"
    assert audit_trail.raw_model_support_score == 0.92
    assert audit_trail.final_action == VerificationAction.FLAG
    assert audit_trail.final_verdict == VerificationVerdict.SUPPORTED
    assert audit_trail.policy_override_applied is True
    assert "Cost anomaly detected" in audit_trail.policy_override_reason
