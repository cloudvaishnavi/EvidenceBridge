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


def test_hybrid_ranking_brain_mri_cpt_70551(verification_service):
    """
    Ensure CPT 70551 Brain MRI retrieves the authoritative Brain MRI guideline
    and appropriately discards or deprioritizes unrelated knee MRI guidelines.
    """
    passages = verification_service.retrieve_hybrid_passages(
        entity="CPT 70551 MRI Brain w/o Contrast",
        claim_text="Persistent headache with focal neurological signs, brain MRI ordered CPT 70551",
        k=5
    )
    assert len(passages) > 0
    top_p = passages[0]
    assert top_p.guideline_id == "GUIDE-IMAG-013"
    assert "Brain" in top_p.title
    assert "70551" in top_p.title
    assert top_p.relevance_score >= 0.70
    assert top_p.used_in_decision is True
    assert top_p.discard_reason is None

    # Verify Knee MRI (CPT 73721) is either not in top-k or flagged as discarded with mismatch
    knee_passages = [p for p in passages if p.guideline_id == "GUIDE-IMAG-007"]
    for kp in knee_passages:
        assert kp.used_in_decision is False
        assert kp.discard_reason is not None
        assert "mismatch" in kp.discard_reason.lower()


def test_hybrid_ranking_routine_venipuncture_cpt_36415(verification_service):
    """Ensure CPT 36415 Routine Venipuncture retrieves the venipuncture guideline."""
    passages = verification_service.retrieve_hybrid_passages(
        entity="Routine Venipuncture (CPT 36415)",
        claim_text="Routine venipuncture blood draw collection for laboratory analysis CPT 36415",
        k=5
    )
    assert len(passages) > 0
    top_p = passages[0]
    assert top_p.guideline_id == "GUIDE-LAB-014"
    assert "Venipuncture" in top_p.title
    assert top_p.relevance_score >= 0.60
    assert top_p.used_in_decision is True


def test_hybrid_ranking_chest_xray_cpt_71046(verification_service):
    """Ensure CPT 71046 Chest X-Ray retrieves the chest radiography guideline."""
    passages = verification_service.retrieve_hybrid_passages(
        entity="Chest X-Ray 2 Views (CPT 71046)",
        claim_text="Acute respiratory dyspnea and cough, chest x-ray 2 views CPT 71046",
        k=5
    )
    assert len(passages) > 0
    top_p = passages[0]
    assert top_p.guideline_id == "GUIDE-RAD-015"
    assert "Chest Radiography" in top_p.title or "Chest X-Ray" in top_p.title
    assert top_p.relevance_score >= 0.60
    assert top_p.used_in_decision is True

