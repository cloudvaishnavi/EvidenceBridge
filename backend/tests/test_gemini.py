"""
Focused tests for Google Gemini API integration in EvidenceBridge.
Mocks external API calls to avoid consuming live quota during test runs.
"""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
import httpx
from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import (
    Claim,
    ExtractedFields,
    ProvenanceMetadata,
    SentimentType,
    VerificationAction,
    VerificationVerdict,
)
from app.services.extraction import (
    ExtractionError,
    ExtractionService,
    GeminiConnectionError,
    LLMConnectionError,
)
from app.services.verification import VerificationService


MOCK_GEMINI_EXTRACTION_JSON = {
    "candidates": [
        {
            "content": {
                "parts": [
                    {
                        "text": json.dumps({
                            "entity": "Metformin 1,000 mg",
                            "effect_or_outcome": "HbA1c reduced to 6.8%",
                            "cost_range": "$15.00",
                            "location_city": "Bengaluru",
                            "sentiment": "positive",
                            "confidence": 0.95,
                            "reasoning": "Standard first-line type 2 diabetes maintenance medication."
                        })
                    }
                ],
                "role": "model"
            },
            "finishReason": "STOP"
        }
    ]
}

MOCK_GEMINI_VERIFICATION_JSON = {
    "candidates": [
        {
            "content": {
                "parts": [
                    {
                        "text": json.dumps({
                            "verdict": "supported",
                            "support_score": 0.92,
                            "reasoning": "Metformin is validated by ADA guidelines as first-line pharmacotherapy for type 2 diabetes.",
                            "conflict_assessment": {
                                "has_conflict": False,
                                "nature": "none",
                                "explanation": "Guidelines are unanimous."
                            }
                        })
                    }
                ],
                "role": "model"
            },
            "finishReason": "STOP"
        }
    ]
}


@pytest.fixture
def client():
    """Returns a FastAPI TestClient."""
    return TestClient(app)


@pytest.fixture
def gemini_extraction_service():
    """Returns an ExtractionService configured for Gemini."""
    service = ExtractionService(provider="gemini")
    service.gemini_api_key = "mock_test_gemini_key_12345"
    return service


@pytest.fixture
def gemini_verification_service():
    """Returns a VerificationService configured for Gemini."""
    service = VerificationService(provider="gemini")
    service.gemini_api_key = "mock_test_gemini_key_12345"
    return service


# ==============================================================================
# Extraction Service Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_gemini_extraction_success(gemini_extraction_service):
    """Verify Gemini API extracts structured fields and confidence accurately."""
    mock_resp = httpx.Response(
        status_code=200,
        content=json.dumps(MOCK_GEMINI_EXTRACTION_JSON).encode("utf-8"),
        request=httpx.Request("POST", "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent")
    )

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        fields, confidence = await gemini_extraction_service.extract_structured_claim(
            "Patient started Metformin 1,000 mg oral daily in Bengaluru, cost $15."
        )

        assert fields.entity == "Metformin 1,000 mg"
        assert fields.sentiment == SentimentType.POSITIVE
        assert fields.cost_range == "$15.00"
        assert fields.location_city == "Bengaluru"
        assert confidence == 0.95


@pytest.mark.asyncio
async def test_gemini_extraction_missing_api_key():
    """Verify GeminiConnectionError is raised when GEMINI_API_KEY is missing."""
    service = ExtractionService(provider="gemini")
    service.gemini_api_key = None

    with pytest.raises((GeminiConnectionError, LLMConnectionError)) as exc_info:
        await service.extract_structured_claim("Some clinical note text")

    assert "GEMINI_API_KEY is not configured" in str(exc_info.value)


@pytest.mark.asyncio
async def test_gemini_extraction_malformed_json_triggers_heuristic(gemini_extraction_service):
    """Verify malformed JSON from Gemini triggers heuristic fallback extraction with reduced confidence."""
    bad_payload = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": "Sorry, I cannot process this unstructured text into JSON."}],
                    "role": "model"
                }
            }
        ]
    }
    mock_resp = httpx.Response(
        status_code=200,
        content=json.dumps(bad_payload).encode("utf-8"),
        request=httpx.Request("POST", "https://generativelanguage.googleapis.com/v1beta/test")
    )

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        fields, confidence = await gemini_extraction_service.extract_structured_claim("Aspirin 81 mg daily for heart")

        assert fields.entity is not None
        assert confidence <= 0.60


@pytest.mark.asyncio
async def test_gemini_extraction_provider_auth_error(gemini_extraction_service):
    """Verify GeminiConnectionError is raised when Gemini returns 401/403."""
    mock_resp = httpx.Response(
        status_code=403,
        content=b'{"error": {"code": 403, "message": "The provided API key is invalid."}}',
        request=httpx.Request("POST", "https://generativelanguage.googleapis.com/v1beta/test")
    )

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        with pytest.raises(GeminiConnectionError) as exc_info:
            await gemini_extraction_service.extract_structured_claim("Some note text")

        assert "authentication failed" in str(exc_info.value).lower()


# ==============================================================================
# Verification Service Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_gemini_verification_supported(gemini_verification_service):
    """Verify Gemini clinical audit produces supported verdict and correct action."""
    mock_resp = httpx.Response(
        status_code=200,
        content=json.dumps(MOCK_GEMINI_VERIFICATION_JSON).encode("utf-8"),
        request=httpx.Request("POST", "https://generativelanguage.googleapis.com/v1beta/test")
    )

    claim = Claim(
        claim_id="clm_gemini_01",
        original_text="Patient prescribed Metformin 1,000 mg daily for type 2 diabetes with good glycemic control.",
        source_type="clinical_note",
        timestamp=datetime.now(timezone.utc),
        extracted_fields=ExtractedFields(
            entity="Metformin 1,000 mg",
            effect_or_outcome="Glycemic control",
            sentiment=SentimentType.POSITIVE
        ),
        confidence=0.9,
        provenance=ProvenanceMetadata(
            source_hash="hash_gemini_01",
            original_snippet="Metformin 1,000 mg",
            text_length=50,
            source_type="clinical_note"
        )
    )

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        result = await gemini_verification_service.verify_claim(claim)

        assert result.verdict == VerificationVerdict.SUPPORTED
        assert result.action == VerificationAction.ACCEPT
        assert result.support_score >= 0.70
        assert result.claim_id == "clm_gemini_01"


@pytest.mark.asyncio
async def test_gemini_verification_abstention_on_unbenchmarked_therapy(gemini_verification_service):
    """Verify that unbenchmarked/unsupported experimental therapies trigger safe refusal abstention."""
    claim = Claim(
        claim_id="clm_gemini_unsupported",
        original_text="Experimental Himalayan Nano-Root Tincture cured my chronic stage-4 illness in 4 days for $8,500.",
        source_type="patient_report",
        timestamp=datetime.now(timezone.utc),
        extracted_fields=ExtractedFields(
            entity="Himalayan Nano-Root Tincture",
            effect_or_outcome="Cured stage-4 illness",
            cost_range="$8,500",
            sentiment=SentimentType.POSITIVE
        ),
        confidence=0.85,
        provenance=ProvenanceMetadata(
            source_hash="hash_nano_root",
            original_snippet="Himalayan Nano-Root",
            text_length=60,
            source_type="patient_report"
        )
    )

    # Pre-evaluation abstention must fire before even calling the external LLM
    result = await gemini_verification_service.verify_claim(claim)

    assert result.verdict == VerificationVerdict.INSUFFICIENT_EVIDENCE
    assert result.action == VerificationAction.ABSTAIN
    assert result.abstain_reason is not None


# ==============================================================================
# Health Check Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_gemini_health_check_healthy(gemini_extraction_service):
    """Verify check_health reports healthy when configured with an API key."""
    health = await gemini_extraction_service.check_health()
    assert health["status"] == "healthy"
    assert health["provider"] == "gemini"
    assert health["configured_model"] == "gemini-3.1-flash-lite"


@pytest.mark.asyncio
async def test_gemini_health_check_missing_key():
    """Verify check_health reports unhealthy when key is missing."""
    service = ExtractionService(provider="gemini")
    service.gemini_api_key = ""
    health = await service.check_health()
    assert health["status"] == "unhealthy"
    assert health["provider"] == "gemini"
    assert "error" in health


# ==============================================================================
# API Endpoint Integration Test (503 on Provider Error)
# ==============================================================================

def test_api_extract_endpoint_503_on_gemini_connection_error(client):
    """Verify /extract returns HTTP 503 with resolution hint when Gemini connection fails."""
    with patch("app.api.routes.extraction_service.extract_structured_claim") as mock_extract:
        mock_extract.side_effect = GeminiConnectionError("Failed to reach Gemini API endpoint")

        # Submit auth demo token first
        demo_resp = client.post("/auth/demo")
        assert demo_resp.status_code == 200
        token = demo_resp.json()["access_token"]

        res = client.post(
            "/extract",
            json={"text": "Metformin 500 mg daily for prediabetes"},
            headers={"Authorization": f"Bearer {token}"}
        )

        assert res.status_code == 503
        data = res.json()
        assert "detail" in data
        assert "resolution" in data["detail"]
