"""
Unit tests for EvidenceBridge Pydantic models.
"""

from datetime import datetime, timezone
import pytest
from pydantic import ValidationError

from app.models.schemas import (
    Claim,
    ExtractedFields,
    ExtractionRequest,
    ExtractionResponse,
    ProvenanceMetadata,
    SentimentType,
    SourceType,
)


def test_extracted_fields_valid():
    fields = ExtractedFields(
        entity="Lisinopril 20mg",
        effect_or_outcome="Blood pressure reduced to 120/80",
        cost_range="$15/month",
        location_city="Boston, MA",
        sentiment=SentimentType.POSITIVE,
    )
    assert fields.entity == "Lisinopril 20mg"
    assert fields.sentiment == SentimentType.POSITIVE
    assert fields.cost_range == "$15/month"


def test_extracted_fields_missing_entity():
    with pytest.raises(ValidationError):
        ExtractedFields(
            effect_or_outcome="Improved outcome",
            sentiment=SentimentType.POSITIVE,
        )


def test_provenance_metadata_valid():
    prov = ProvenanceMetadata(
        source_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        original_snippet="Sample clinical note snippet",
        text_length=120,
        source_type="clinical_note",
        source_url="https://example.com/record/1",
    )
    assert prov.text_length == 120
    assert prov.source_type == "clinical_note"
    assert prov.ingested_at is not None


def test_claim_confidence_validation(sample_extracted_fields):
    now = datetime.now(timezone.utc)
    prov = ProvenanceMetadata(
        source_hash="abc123hash",
        original_snippet="Sample snippet",
        text_length=50,
        source_type="clinical_note",
    )

    # Valid confidence
    claim = Claim(
        claim_id="clm_test01",
        original_text="Full text",
        source_type="clinical_note",
        timestamp=now,
        extracted_fields=sample_extracted_fields,
        confidence=0.85,
        provenance=prov,
    )
    assert claim.confidence == 0.85

    # Invalid confidence > 1.0
    with pytest.raises(ValidationError):
        Claim(
            claim_id="clm_test02",
            original_text="Full text",
            source_type="clinical_note",
            timestamp=now,
            extracted_fields=sample_extracted_fields,
            confidence=1.5,
            provenance=prov,
        )


def test_extraction_request_empty_text():
    with pytest.raises(ValidationError):
        ExtractionRequest(text="")
