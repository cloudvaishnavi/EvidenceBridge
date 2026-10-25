"""
Unit tests for Verification and Support Scoring Service.
"""

from datetime import datetime, timezone
import pytest

from app.models.schemas import (
    Claim,
    ExtractedFields,
    ProvenanceMetadata,
    SentimentType,
    VerificationAction,
    VerificationVerdict,
)
from app.services.verification import VerificationService


@pytest.fixture
def verification_service():
    return VerificationService()


def test_retrieve_evidence_passages(verification_service):
    # Test retrieving diabetes guideline
    snippets = verification_service.retrieve_evidence_passages("Metformin 1000mg", "Type 2 diabetes HbA1c drop")
    assert len(snippets) > 0
    top_snippet = snippets[0]
    assert "Metformin" in top_snippet.title or "Diabetes" in top_snippet.title
    assert "ADA" in top_snippet.source or "American Diabetes Association" in top_snippet.source

    # Test retrieving acute bronchitis guideline
    bronchitis_snippets = verification_service.retrieve_evidence_passages("Azithromycin", "Acute viral bronchitis cough")
    assert len(bronchitis_snippets) > 0
    assert any("Bronchitis" in s.title or "Antibiotic" in s.title for s in bronchitis_snippets)


def test_parse_verification_output_supported(verification_service):
    raw_json = """
    {
      "verdict": "supported",
      "support_score": 0.92,
      "reasoning": "ADA guideline recommends Metformin 1,000 mg twice daily as first-line therapy for type 2 diabetes with expected HbA1c reduction."
    }
    """
    verdict, score, reasoning = verification_service._parse_verification_output(raw_json)
    assert verdict == VerificationVerdict.SUPPORTED
    assert score == 0.92
    assert "ADA guideline" in reasoning


def test_parse_verification_output_contradicted(verification_service):
    raw_markdown = """```json
    {
      "verdict": "contradicted",
      "support_score": 0.10,
      "reasoning": "CDC and GOLD guidelines explicitly state antibiotics like Azithromycin should NOT be prescribed for acute viral bronchitis."
    }
    ```"""
    verdict, score, reasoning = verification_service._parse_verification_output(raw_markdown)
    assert verdict == VerificationVerdict.CONTRADICTED
    assert score == 0.10
    assert "contradicted" in verdict.value


def test_parse_verification_response_conflict_assessment(verification_service):
    raw_json = """
    {
      "verdict": "partially_supported",
      "support_score": 0.55,
      "reasoning": "The guidance differs by patient cohort.",
      "conflict_assessment": {
        "has_conflict": true,
        "supporting_passage_ids": ["pas_a"],
        "opposing_passage_ids": ["pas_b"],
        "explanation": "The cited passages recommend opposite positions."
      }
    }
    """
    verdict, score, reasoning, assessment = (
        verification_service._parse_verification_response(raw_json)
    )

    assert verdict == VerificationVerdict.PARTIALLY_SUPPORTED
    assert score == 0.55
    assert "differs by patient cohort" in reasoning
    assert assessment["supporting_passage_ids"] == ["pas_a"]
    assert assessment["opposing_passage_ids"] == ["pas_b"]


def test_determine_action_matrix(verification_service):
    # Case 1: Supported + Fair Price -> ACCEPT
    action, reason = verification_service._determine_action(
        verdict=VerificationVerdict.SUPPORTED,
        support_score=0.90,
        has_cost_anomaly=False
    )
    assert action == VerificationAction.ACCEPT
    assert reason is None

    # Case 2: Supported + Cost Anomaly -> FLAG
    action, reason = verification_service._determine_action(
        verdict=VerificationVerdict.SUPPORTED,
        support_score=0.90,
        has_cost_anomaly=True
    )
    assert action == VerificationAction.FLAG

    # Case 3: Contradicted claim -> FLAG
    action, reason = verification_service._determine_action(
        verdict=VerificationVerdict.CONTRADICTED,
        support_score=0.15,
        has_cost_anomaly=False
    )
    assert action == VerificationAction.FLAG

    # Case 4: Insufficient Evidence -> ABSTAIN
    action, reason = verification_service._determine_action(
        verdict=VerificationVerdict.INSUFFICIENT_EVIDENCE,
        support_score=0.10,
        has_cost_anomaly=False
    )
    assert action == VerificationAction.ABSTAIN
    assert reason is not None


@pytest.mark.asyncio
async def test_abstention_on_unverified_entity(verification_service):
    """When a claim references an entity with zero evidence in knowledge base, abstain."""
    claim = Claim(
        claim_id="clm_rare_herb",
        original_text="Himalayan Blue Root Tincture cured my late-stage disease in 2 weeks for $450.",
        source_type="forum_post",
        timestamp=datetime.now(timezone.utc),
        extracted_fields=ExtractedFields(
            entity="Himalayan Blue Root Tincture",
            effect_or_outcome="Cured late-stage disease",
            cost_range="$450",
            sentiment=SentimentType.POSITIVE
        ),
        confidence=0.8,
        provenance=ProvenanceMetadata(
            source_hash="dummyhash_herb",
            original_snippet="Himalayan Blue Root",
            text_length=70,
            source_type="forum_post"
        )
    )

    result = await verification_service.verify_claim(claim)
    assert result.verdict == VerificationVerdict.INSUFFICIENT_EVIDENCE
    assert result.action == VerificationAction.ABSTAIN
    assert result.abstain_reason is not None
    assert "abstain" in result.reasoning.lower() or "abstaining" in result.reasoning.lower()
