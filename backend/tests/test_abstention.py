"""
Unit tests for the Abstention Policy Service (Layer 3).
Tests deterministic rules: missing entity, no relevant evidence,
conflicting guidelines, low confidence floor, and unbenchmarked high costs.
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
    VerificationVerdict,
)
from app.services.abstention import AbstentionPolicyService, AbstentionRule


@pytest.fixture
def abstention_service():
    return AbstentionPolicyService()


@pytest.fixture
def base_claim():
    return Claim(
        claim_id="clm_abs_test",
        original_text="Patient administered specialized therapeutic compound for chronic fatigue.",
        source_type="clinical_note",
        timestamp=datetime.now(timezone.utc),
        extracted_fields=ExtractedFields(
            entity="Therapeutic Compound X",
            effect_or_outcome="Fatigue improved",
            cost_range=None,
            sentiment=SentimentType.POSITIVE
        ),
        confidence=0.85,
        provenance=ProvenanceMetadata(
            source_hash="dummyhash",
            original_snippet="Patient administered specialized compound",
            text_length=70,
            source_type="clinical_note"
        )
    )


def test_abstention_on_unspecified_entity(abstention_service, base_claim):
    # Entity is unspecified/unknown
    claim = base_claim.model_copy(update={
        "extracted_fields": ExtractedFields(
            entity="Unspecified Medical Entity",
            sentiment=SentimentType.NEUTRAL
        )
    })
    passages = []
    cost_details = CostAnomalyDetails(is_anomaly=False, explanation="No cost")

    decision = abstention_service.evaluate(claim, passages, cost_details)
    assert decision.should_abstain is True
    assert decision.rule_triggered == AbstentionRule.ENTITY_NOT_FOUND
    assert "Entity could not be identified" in decision.reason


def test_abstention_on_no_relevant_evidence(abstention_service, base_claim):
    # Passages exist but all below threshold 0.35
    passages = [
        EvidencePassage(
            passage_id="pas_1",
            title="Unrelated Oncology Guideline",
            source="NCCN",
            text="Guideline on melanoma treatment...",
            relevance_score=0.15,
            used_in_decision=False,
            discard_reason="Below relevance threshold 0.35"
        )
    ]
    cost_details = CostAnomalyDetails(is_anomaly=False, explanation="No cost")

    decision = abstention_service.evaluate(base_claim, passages, cost_details)
    assert decision.should_abstain is True
    assert decision.rule_triggered == AbstentionRule.NO_RELEVANT_EVIDENCE
    assert "threshold" in decision.reason.lower()


def test_abstention_on_conflicting_guidelines(abstention_service, base_claim):
    passages = [
        EvidencePassage(
            passage_id="pas_2",
            title="Relevant Guideline A",
            source="AHA",
            text="Guideline excerpt...",
            relevance_score=0.85,
            used_in_decision=True
        )
    ]
    cost_details = CostAnomalyDetails(is_anomaly=False, explanation="No cost")

    # Model reports contradictory evidence
    reasoning = "There are conflicting guidelines and contradictory evidence regarding the clinical utility of this drug in this cohort."
    decision = abstention_service.evaluate(
        base_claim,
        passages,
        cost_details,
        model_verdict=VerificationVerdict.PARTIALLY_SUPPORTED,
        model_support_score=0.50,
        model_reasoning=reasoning
    )

    assert decision.should_abstain is True
    assert decision.rule_triggered == AbstentionRule.CONFLICTING_EVIDENCE
    assert "conflicting recommendations" in decision.reason.lower()


def test_abstention_on_low_confidence_floor(abstention_service, base_claim):
    passages = [
        EvidencePassage(
            passage_id="pas_3",
            title="Relevant Guideline B",
            source="FDA",
            text="Guideline excerpt...",
            relevance_score=0.80,
            used_in_decision=True
        )
    ]
    cost_details = CostAnomalyDetails(is_anomaly=False, explanation="No cost")

    # Score below 0.40 confidence floor without being an explicit contradiction
    decision = abstention_service.evaluate(
        base_claim,
        passages,
        cost_details,
        model_verdict=VerificationVerdict.PARTIALLY_SUPPORTED,
        model_support_score=0.32,
        model_reasoning="Weak evidence connection."
    )

    assert decision.should_abstain is True
    assert decision.rule_triggered == AbstentionRule.LOW_MODEL_CONFIDENCE
    assert "confidence floor" in decision.reason.lower()


def test_abstention_on_unbenchmarked_high_cost(abstention_service, base_claim):
    passages = [
        EvidencePassage(
            passage_id="pas_4",
            title="Relevant Guideline C",
            source="ADA",
            text="Guideline excerpt...",
            relevance_score=0.88,
            used_in_decision=True
        )
    ]
    # High charge of $3,500 with no benchmark in knowledge base
    cost_details = CostAnomalyDetails(
        is_anomaly=False,
        extracted_amount=3500.0,
        benchmark_max=None,
        explanation="No public pricing benchmark found for entity 'Therapeutic Compound X'."
    )

    decision = abstention_service.evaluate(
        base_claim,
        passages,
        cost_details,
        model_verdict=VerificationVerdict.SUPPORTED,
        model_support_score=0.88,
        model_reasoning="Therapeutic compound is supported."
    )

    assert decision.should_abstain is True
    assert decision.rule_triggered == AbstentionRule.UNBENCHMARKED_HIGH_COST
    assert "no public pricing benchmark exists" in decision.reason.lower()


def test_no_abstention_when_evidence_and_cost_are_solid(abstention_service, base_claim):
    passages = [
        EvidencePassage(
            passage_id="pas_5",
            title="ADA Metformin Guidelines",
            source="ADA",
            text="Metformin 1000mg is first-line for type 2 diabetes...",
            relevance_score=0.92,
            used_in_decision=True
        )
    ]
    cost_details = CostAnomalyDetails(
        is_anomaly=False,
        extracted_amount=15.0,
        benchmark_max=25.0,
        explanation="Billed amount falls within benchmark range."
    )

    decision = abstention_service.evaluate(
        base_claim,
        passages,
        cost_details,
        model_verdict=VerificationVerdict.SUPPORTED,
        model_support_score=0.92,
        model_reasoning="Clinical trial evidence and ADA guideline directly corroborate the claim."
    )

    assert decision.should_abstain is False
    assert decision.rule_triggered is None
    assert decision.reason is None
