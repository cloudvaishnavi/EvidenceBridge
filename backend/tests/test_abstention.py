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
            passage_id="pas_supports",
            title="Relevant Guideline A",
            source="AHA",
            text="Guideline excerpt supporting the clinical utility of this drug.",
            relevance_score=0.85,
            used_in_decision=True
        ),
        EvidencePassage(
            passage_id="pas_opposes",
            title="Relevant Guideline B",
            source="FDA",
            text="Guideline excerpt discouraging this drug for this cohort.",
            relevance_score=0.82,
            used_in_decision=True
        )
    ]
    cost_details = CostAnomalyDetails(is_anomaly=False, explanation="No cost")

    decision = abstention_service.evaluate(
        base_claim,
        passages,
        cost_details,
        model_verdict=VerificationVerdict.PARTIALLY_SUPPORTED,
        model_support_score=0.50,
        model_reasoning="Guideline recommendations differ for this cohort.",
        model_conflict_assessment={
            "has_conflict": True,
            "supporting_passage_ids": ["pas_supports"],
            "opposing_passage_ids": ["pas_opposes"],
            "explanation": "One passage supports use and another discourages it."
        }
    )

    assert decision.should_abstain is True
    assert decision.rule_triggered == AbstentionRule.CONFLICTING_EVIDENCE
    assert decision.details["conflict_assessment_valid"] is True
    assert decision.details["original_model_verdict"] == VerificationVerdict.PARTIALLY_SUPPORTED.value
    assert decision.details["supporting_passage_ids"] == ["pas_supports"]
    assert "opposing positions" in decision.reason.lower()


@pytest.mark.parametrize(
    "assessment",
    [
        {
            "has_conflict": True,
            "supporting_passage_ids": ["pas_usable"],
            "opposing_passage_ids": ["pas_not_retrieved"]
        },
        {
            "has_conflict": True,
            "supporting_passage_ids": ["pas_usable"],
            "opposing_passage_ids": []
        }
    ],
    ids=["unknown-passage-id", "missing-opposing-reference"]
)
def test_unverified_conflict_references_do_not_trigger_conflict(
    abstention_service,
    base_claim,
    assessment
):
    passages = [
        EvidencePassage(
            passage_id="pas_usable",
            title="Relevant Guideline",
            source="AHA",
            text="Relevant passage.",
            relevance_score=0.85,
            used_in_decision=True
        )
    ]
    decision = abstention_service.evaluate(
        base_claim,
        passages,
        CostAnomalyDetails(is_anomaly=False, explanation="No cost"),
        model_verdict=VerificationVerdict.PARTIALLY_SUPPORTED,
        model_support_score=0.50,
        model_reasoning="There are conflicting recommendations.",
        model_conflict_assessment=assessment
    )

    assert decision.should_abstain is True
    assert decision.rule_triggered == AbstentionRule.INSUFFICIENT_EVIDENCE
    assert decision.details["conflict_assessment_valid"] is False


def test_conflict_wording_without_assessment_does_not_trigger_conflict(abstention_service, base_claim):
    passages = [
        EvidencePassage(
            passage_id="pas_keyword_only",
            title="Relevant Guideline",
            source="AHA",
            text="Relevant passage.",
            relevance_score=0.85,
            used_in_decision=True
        )
    ]
    decision = abstention_service.evaluate(
        base_claim,
        passages,
        CostAnomalyDetails(is_anomaly=False, explanation="No cost"),
        model_verdict=VerificationVerdict.PARTIALLY_SUPPORTED,
        model_support_score=0.50,
        model_reasoning="There are conflicting recommendations."
    )

    assert decision.should_abstain is False
    assert decision.rule_triggered is None
    assert decision.details["conflict_assessment_valid"] is False


def test_unverifiable_conflict_prevents_supported_acceptance(abstention_service, base_claim):
    passages = [
        EvidencePassage(
            passage_id="pas_supported",
            title="Relevant Guideline",
            source="AHA",
            text="Relevant passage supporting the claim.",
            relevance_score=0.85,
            used_in_decision=True
        )
    ]
    decision = abstention_service.evaluate(
        base_claim,
        passages,
        CostAnomalyDetails(is_anomaly=False, explanation="No cost"),
        model_verdict=VerificationVerdict.SUPPORTED,
        model_support_score=0.90,
        model_conflict_assessment={
            "has_conflict": True,
            "supporting_passage_ids": ["pas_supported"],
            "opposing_passage_ids": ["pas_missing"]
        }
    )

    assert decision.should_abstain is True
    assert decision.rule_triggered == AbstentionRule.INSUFFICIENT_EVIDENCE


def test_negated_conflict_wording_does_not_trigger_conflict(abstention_service, base_claim):
    passages = [
        EvidencePassage(
            passage_id="pas_no_conflict",
            title="Relevant Guideline",
            source="AHA",
            text="Relevant passage.",
            relevance_score=0.85,
            used_in_decision=True
        )
    ]
    decision = abstention_service.evaluate(
        base_claim,
        passages,
        CostAnomalyDetails(is_anomaly=False, explanation="No cost"),
        model_verdict=VerificationVerdict.PARTIALLY_SUPPORTED,
        model_support_score=0.50,
        model_reasoning="There is no conflicting evidence.",
        model_conflict_assessment={
            "has_conflict": False,
            "supporting_passage_ids": [],
            "opposing_passage_ids": []
        }
    )

    assert decision.should_abstain is False
    assert decision.rule_triggered is None


def test_abstention_on_insufficient_evidence_without_conflict(abstention_service, base_claim):
    passages = [
        EvidencePassage(
            passage_id="pas_insufficient",
            title="Relevant Guideline",
            source="FDA",
            text="Relevant guideline excerpt without enough facts to assess the claimed outcome.",
            relevance_score=0.80,
            used_in_decision=True
        )
    ]
    cost_details = CostAnomalyDetails(is_anomaly=False, explanation="No cost")

    decision = abstention_service.evaluate(
        base_claim,
        passages,
        cost_details,
        model_verdict=VerificationVerdict.INSUFFICIENT_EVIDENCE,
        model_support_score=0.20,
        model_reasoning="The evidence is inconclusive and does not provide enough facts to judge the claim."
    )

    assert decision.should_abstain is True
    assert decision.rule_triggered == AbstentionRule.INSUFFICIENT_EVIDENCE
    assert "not provide enough" in decision.reason.lower()
    assert "conflict" not in decision.reason.lower()


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


def test_explicit_contradiction_is_not_reclassified_as_conflict(abstention_service, base_claim):
    passages = [
        EvidencePassage(
            passage_id="pas_contradicts",
            title="Guideline A",
            source="CDC",
            text="Guideline excerpt explicitly contradicting the claim.",
            relevance_score=0.80,
            used_in_decision=True
        ),
        EvidencePassage(
            passage_id="pas_supports",
            title="Guideline B",
            source="FDA",
            text="Guideline excerpt supporting the claim.",
            relevance_score=0.82,
            used_in_decision=True
        )
    ]
    cost_details = CostAnomalyDetails(is_anomaly=False, explanation="No cost")

    decision = abstention_service.evaluate(
        base_claim,
        passages,
        cost_details,
        model_verdict=VerificationVerdict.CONTRADICTED,
        model_support_score=0.15,
        model_reasoning="The guideline contradicts the claim, but there is no conflicting evidence.",
        model_conflict_assessment={
            "has_conflict": True,
            "supporting_passage_ids": ["pas_supports"],
            "opposing_passage_ids": ["pas_contradicts"],
            "explanation": "The cited passages have opposite recommendations."
        }
    )

    assert decision.should_abstain is False
    assert decision.rule_triggered is None
    assert decision.details["conflict_assessment_valid"] is True
    assert decision.details["original_model_verdict"] == VerificationVerdict.CONTRADICTED.value


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
