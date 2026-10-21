"""
Unit tests for Hybrid Retrieval Quality & Passage Ranking (Layer 3).
Tests BM25 term weighting, vector integration, relevance thresholds,
and used vs. discarded passage labeling.
"""

import pytest
from app.services.verification import VerificationService


@pytest.fixture
def verification_service():
    return VerificationService()


def test_hybrid_ranking_top_guideline(verification_service):
    # Search for Metformin diabetes therapy
    passages = verification_service.retrieve_hybrid_passages(
        entity="Metformin 1,000 mg",
        claim_text="Type 2 diabetes HbA1c reduction",
        k=5
    )
    assert len(passages) > 0
    top_p = passages[0]
    assert "Metformin" in top_p.title or "Diabetes" in top_p.title
    assert top_p.relevance_score >= 0.50
    assert top_p.used_in_decision is True
    assert top_p.discard_reason is None


def test_hybrid_ranking_hypertension(verification_service):
    # Search for Lisinopril hypertension therapy
    passages = verification_service.retrieve_hybrid_passages(
        entity="Lisinopril 20 mg",
        claim_text="Stage 2 essential hypertension blood pressure reduction",
        k=5
    )
    assert len(passages) > 0
    top_p = passages[0]
    assert "Lisinopril" in top_p.text or "Hypertension" in top_p.title or "Blood Pressure" in top_p.title
    assert top_p.relevance_score >= 0.50
    assert top_p.used_in_decision is True


def test_hybrid_ranking_bronchitis_antibiotic(verification_service):
    # Search for Azithromycin for acute bronchitis
    passages = verification_service.retrieve_hybrid_passages(
        entity="Azithromycin 250 mg",
        claim_text="Acute viral bronchitis non-productive cough",
        k=5
    )
    assert len(passages) > 0
    top_p = passages[0]
    assert "Bronchitis" in top_p.title or "Antibiotic" in top_p.title
    assert top_p.relevance_score >= 0.50


def test_discard_reason_for_low_relevance(verification_service):
    # Search for specific knee arthroscopy; cancer or diabetes guidelines should be discarded
    passages = verification_service.retrieve_hybrid_passages(
        entity="Left Knee Arthroscopy",
        claim_text="Meniscus tear repair surgery recovery",
        k=5
    )
    assert len(passages) > 0

    # The top passage should be Ortho/Arthroscopy
    assert "Arthroscopy" in passages[0].title or "Meniscal" in passages[0].title
    assert passages[0].used_in_decision is True

    # At least one lower-ranked passage should be discarded due to low relevance or entity mismatch
    discarded = [p for p in passages if not p.used_in_decision]
    assert len(discarded) > 0
    for d in discarded:
        assert d.discard_reason is not None
        assert "threshold" in d.discard_reason.lower() or "mismatch" in d.discard_reason.lower()


def test_backward_compatible_snippets(verification_service):
    snippets = verification_service.retrieve_evidence_passages(
        entity="Semaglutide 0.5mg",
        claim_text="Weekly GLP-1 injection for weight loss and blood glucose",
        k=3
    )
    assert len(snippets) > 0
    for s in snippets:
        assert hasattr(s, "guideline_id")
        assert hasattr(s, "title")
        assert hasattr(s, "relevance_score")
        assert s.relevance_score >= 0.35
