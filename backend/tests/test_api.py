"""
Integration tests for FastAPI endpoints.
Uses FastAPI TestClient with mocked extraction and storage.
"""

from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.models.schemas import Claim, ExtractedFields, ProvenanceMetadata, SentimentType


@pytest.fixture
def client():
    return TestClient(app)


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["engine"] == "EvidenceBridge"
    assert "Foundational Layer 1" in data["layer"]
    assert "This layer only does extraction + provenance" in data["note"]


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "services" in data
    assert "mongodb" in data["services"]
    assert "ollama" in data["services"]


@patch("app.api.routes.extraction_service.extract_structured_claim")
@patch("app.api.routes.storage_service.insert_claim")
@patch("app.api.routes.vector_store_service.add_claim")
def test_extract_endpoint_success(mock_add_vector, mock_insert, mock_extract, client):
    mock_extract.return_value = (
        ExtractedFields(
            entity="Metformin 1,000 mg",
            effect_or_outcome="Reduction in HbA1c to 7.1%",
            cost_range=None,
            location_city=None,
            sentiment=SentimentType.POSITIVE,
            reasoning="Clear glycemic improvement.",
        ),
        0.92,
    )
    mock_insert.return_value = None
    mock_add_vector.return_value = True

    payload = {
        "text": "Patient with T2D started Metformin 1000mg BID. HbA1c dropped to 7.1%.",
        "source_type": "clinical_note",
        "source_url": "ehr://test-ehr/pt-101",
        "store_claim": True,
    }

    response = client.post("/extract", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert data["success"] is True
    assert data["stored"] is True
    claim = data["claim"]
    assert claim["claim_id"].startswith("clm_")
    assert claim["extracted_fields"]["entity"] == "Metformin 1,000 mg"
    assert claim["confidence"] == 0.92
    assert "provenance" in claim
    assert claim["provenance"]["source_hash"] is not None
    assert claim["provenance"]["original_snippet"] is not None


@patch("app.api.routes.storage_service.get_claim")
def test_get_claim_by_id_found(mock_get, client, sample_extracted_fields):
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    mock_claim = Claim(
        claim_id="clm_12345",
        original_text="Metformin note sample",
        source_type="clinical_note",
        timestamp=now,
        extracted_fields=sample_extracted_fields,
        confidence=0.90,
        provenance=ProvenanceMetadata(
            source_hash="b2d2949ff96a17b077a119777174db62c9388df233ec7c9a9244465b82b99fa7",
            original_snippet="Metformin note sample",
            text_length=21,
            source_type="clinical_note",
            ingested_at=now,
        ),
    )
    mock_get.return_value = mock_claim

    response = client.get("/claims/clm_12345")
    assert response.status_code == 200
    assert response.json()["claim_id"] == "clm_12345"


@patch("app.api.routes.storage_service.get_claim")
def test_get_claim_by_id_not_found(mock_get, client):
    mock_get.return_value = None
    response = client.get("/claims/clm_nonexistent")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_extract_invalid_payload(client):
    response = client.post("/extract", json={"text": ""})
    # FastAPI/Pydantic returns 422 for min_length validation failure
    assert response.status_code == 422
