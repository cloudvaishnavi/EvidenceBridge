"""
Unit tests for Provenance Service.
"""

from app.models.schemas import ExtractedFields, SentimentType
from app.services.provenance import ProvenanceService


def test_compute_sha256_deterministic():
    text = "Metformin 500mg daily"
    hash1 = ProvenanceService.compute_sha256(text)
    hash2 = ProvenanceService.compute_sha256(text)
    assert hash1 == hash2
    assert len(hash1) == 64

    # Different text produces different hash
    hash3 = ProvenanceService.compute_sha256("Metformin 1000mg daily")
    assert hash1 != hash3


def test_extract_snippet_truncation():
    short_text = "Patient was admitted for acute bronchitis."
    assert ProvenanceService.extract_snippet(short_text, max_length=100) == short_text

    long_text = "Word " * 50
    snippet = ProvenanceService.extract_snippet(long_text, max_length=50)
    assert len(snippet) <= 53  # includes ellipsis
    assert snippet.endswith("...")


def test_assemble_claim_and_verify(sample_clinical_text, sample_extracted_fields):
    claim = ProvenanceService.assemble_claim(
        original_text=sample_clinical_text,
        extracted_fields=sample_extracted_fields,
        confidence=0.92,
        source_type="clinical_note",
        source_url="ehr://test-ehr/pt-1",
    )

    assert claim.claim_id.startswith("clm_")
    assert claim.provenance.source_hash == ProvenanceService.compute_sha256(sample_clinical_text)
    assert claim.provenance.source_url == "ehr://test-ehr/pt-1"
    assert claim.provenance.text_length == len(sample_clinical_text)
    assert claim.confidence == 0.92

    # Verification passes
    assert ProvenanceService.verify_provenance(claim) is True

    # Tampering with original text causes verification to fail
    tampered_claim = claim.model_copy(update={"original_text": "TAMPERED TEXT CONTENT"})
    assert ProvenanceService.verify_provenance(tampered_claim) is False
