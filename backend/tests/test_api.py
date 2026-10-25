"""
Integration tests for FastAPI endpoints.
Uses FastAPI TestClient with mocked extraction and storage.
"""

from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.models.schemas import (
    AuditTrail,
    Claim,
    CostAnomalyDetails,
    DecisionStep,
    EvidencePassage,
    EvidenceSnippet,
    ExtractedFields,
    LocationInfo,
    LocationInsight,
    ProvenanceMetadata,
    SentimentType,
    TrustDensityMetrics,
    TrustTier,
    VerificationAction,
    VerificationResult,
    VerificationVerdict,
)


@pytest.fixture
def client():
    from app.services.auth import (
        create_access_token,
        DEMO_USER_ID,
        DEMO_USER_EMAIL,
        DEMO_USER_NAME,
    )
    c = TestClient(app)
    token = create_access_token(DEMO_USER_ID, DEMO_USER_EMAIL, DEMO_USER_NAME)
    c.headers["Authorization"] = f"Bearer {token}"
    return c


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


# ==============================================================================
# Layer 2: Verification Endpoint Tests
# ==============================================================================

@patch("app.api.routes.storage_service.get_claim")
@patch("app.api.routes.verification_service.verify_claim")
@patch("app.api.routes.storage_service.insert_verification")
def test_verify_claim_by_id_success(mock_insert_verif, mock_verify, mock_get_claim, client, sample_extracted_fields):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)

    mock_claim = Claim(
        claim_id="clm_audit_test",
        original_text="Metformin note sample",
        source_type="clinical_note",
        timestamp=now,
        extracted_fields=sample_extracted_fields,
        confidence=0.90,
        provenance=ProvenanceMetadata(
            source_hash="dummyhash",
            original_snippet="Metformin note sample",
            text_length=21,
            source_type="clinical_note",
            ingested_at=now,
        ),
    )
    mock_get_claim.return_value = mock_claim

    mock_verif_result = VerificationResult(
        claim_id="clm_audit_test",
        support_score=0.95,
        verdict=VerificationVerdict.SUPPORTED,
        action=VerificationAction.ACCEPT,
        reasoning="ADA guideline strongly supports Metformin 1000mg for T2D HbA1c reduction.",
        evidence_snippets=[
            EvidenceSnippet(
                guideline_id="GUIDE-DIAB-001",
                title="ADA Standards of Care: Metformin in Type 2 Diabetes",
                source="ADA Clinical Guidelines",
                text="Metformin is first-line therapy...",
                relevance_score=0.95
            )
        ],
        cost_anomaly_flag=False,
        anomaly_details=None,
        abstain_reason=None,
        verified_at=now
    )
    mock_verify.return_value = mock_verif_result
    mock_insert_verif.return_value = mock_verif_result

    response = client.post("/verify/clm_audit_test")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["verification"]["claim_id"] == "clm_audit_test"
    assert data["verification"]["verdict"] == "supported"
    assert data["verification"]["action"] == "accept"
    assert data["verification"]["support_score"] == 0.95


@patch("app.api.routes.storage_service.get_claim")
def test_verify_claim_by_id_not_found(mock_get_claim, client):
    mock_get_claim.return_value = None
    response = client.post("/verify/clm_nonexistent")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


@patch("app.api.routes.extraction_service.extract_structured_claim")
@patch("app.api.routes.storage_service.insert_claim")
@patch("app.api.routes.vector_store_service.add_claim")
@patch("app.api.routes.verification_service.verify_claim")
@patch("app.api.routes.storage_service.insert_verification")
def test_extract_and_verify_pipeline(
    mock_insert_verif, mock_verify, mock_add_vector, mock_insert_claim, mock_extract, client
):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)

    mock_extract.return_value = (
        ExtractedFields(
            entity="0.9% Sodium Chloride Normal Saline 1,000 mL IV",
            effect_or_outcome="Hydration maintenance",
            cost_range="$720.00",
            location_city="Cleveland, OH",
            sentiment=SentimentType.NEGATIVE,
            reasoning="Severe saline markup detected.",
        ),
        0.94,
    )
    mock_insert_claim.return_value = None
    mock_add_vector.return_value = True

    mock_verif = VerificationResult(
        claim_id="clm_saline_test",
        support_score=0.88,
        verdict=VerificationVerdict.SUPPORTED,
        action=VerificationAction.FLAG,  # Flagged because of extreme cost anomaly
        reasoning="Saline is indicated, but cost is an extreme 16x markup anomaly.",
        evidence_snippets=[],
        cost_anomaly_flag=True,
        anomaly_details=CostAnomalyDetails(
            is_anomaly=True,
            extracted_amount=720.0,
            benchmark_min=5.0,
            benchmark_max=45.0,
            multiplier=16.0,
            threshold_multiplier=3.0,
            severity="extreme",
            explanation="Billed amount of $720.00 is 16.0x higher than benchmark max of $45.00"
        ),
        abstain_reason=None,
        verified_at=now
    )
    mock_verify.return_value = mock_verif
    mock_insert_verif.return_value = mock_verif

    payload = {
        "text": "MIDWEST HOSPITAL: Normal Saline 1000mL IV bag billed at $720.00 in Cleveland OH",
        "source_type": "hospital_bill",
        "store_claim": True
    }

    response = client.post("/extract-and-verify", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["claim"]["extracted_fields"]["entity"] == "0.9% Sodium Chloride Normal Saline 1,000 mL IV"
    assert data["verification"]["cost_anomaly_flag"] is True
    assert data["verification"]["action"] == "flag"
    assert data["verification"]["anomaly_details"]["severity"] == "extreme"


@patch("app.api.routes.storage_service.get_verification")
def test_get_verification_by_id_found(mock_get_verif, client):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)

    mock_get_verif.return_value = VerificationResult(
        claim_id="clm_test_verified",
        support_score=0.91,
        verdict=VerificationVerdict.SUPPORTED,
        action=VerificationAction.ACCEPT,
        reasoning="Audit complete and passed.",
        evidence_snippets=[],
        cost_anomaly_flag=False,
        anomaly_details=None,
        abstain_reason=None,
        verified_at=now
    )

    response = client.get("/verification/clm_test_verified")
    assert response.status_code == 200
    data = response.json()
    assert data["claim_id"] == "clm_test_verified"
    assert data["verdict"] == "supported"


@patch("app.api.routes.storage_service.get_verification")
def test_get_verification_by_id_not_found(mock_get_verif, client):
    mock_get_verif.return_value = None
    response = client.get("/verification/clm_nonexistent")
    assert response.status_code == 404
    assert "no verification record found" in response.json()["detail"].lower()


# ==============================================================================
# Layer 3: Decision Audit Trail Endpoint Tests
# ==============================================================================

@patch("app.api.routes.storage_service.get_audit_trail_by_claim_id")
def test_get_audit_by_claim_id_found(mock_get_audit, client):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)

    mock_audit = AuditTrail(
        audit_id="aud_123456",
        claim_id="clm_audit_claim",
        verification_id="ver_audit_verif",
        steps=[
            DecisionStep(
                step_name="EXTRACTION",
                input_summary="Input note",
                output_summary="Entity=Metformin",
                details={},
                timestamp=now
            )
        ],
        passages_considered=[
            EvidencePassage(
                passage_id="pas_001",
                title="ADA Guidelines",
                source="ADA",
                text="Text...",
                relevance_score=0.95,
                used_in_decision=True
            )
        ],
        final_verdict=VerificationVerdict.SUPPORTED,
        final_action=VerificationAction.ACCEPT,
        final_reasoning="Verified via guidelines",
        abstain_triggered=False,
        abstain_reason=None,
        cost_anomaly_flag=False,
        created_at=now
    )
    mock_get_audit.return_value = mock_audit

    response = client.get("/audit/clm_audit_claim")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["audit_trail"]["audit_id"] == "aud_123456"
    assert data["audit_trail"]["claim_id"] == "clm_audit_claim"
    assert len(data["audit_trail"]["steps"]) == 1
    assert data["audit_trail"]["final_action"] == "accept"


@patch("app.api.routes.storage_service.get_audit_trail_by_claim_id")
def test_get_audit_by_claim_id_not_found(mock_get_audit, client):
    mock_get_audit.return_value = None
    response = client.get("/audit/clm_missing_audit")
    assert response.status_code == 404
    assert "no audit trail found" in response.json()["detail"].lower()


@patch("app.api.routes.storage_service.get_audit_trail_by_verification_id")
def test_get_audit_by_verification_id_found(mock_get_audit, client):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)

    mock_audit = AuditTrail(
        audit_id="aud_verif_999",
        claim_id="clm_target",
        verification_id="ver_target",
        steps=[],
        passages_considered=[],
        final_verdict=VerificationVerdict.SUPPORTED,
        final_action=VerificationAction.ACCEPT,
        final_reasoning="Direct pass",
        abstain_triggered=False,
        created_at=now
    )
    mock_get_audit.return_value = mock_audit

    response = client.get("/audit/verification/ver_target")
    assert response.status_code == 200
    data = response.json()
    assert data["audit_trail"]["verification_id"] == "ver_target"
    assert data["audit_trail"]["audit_id"] == "aud_verif_999"


@patch("app.api.routes.storage_service.get_audit_trail_by_verification_id")
def test_get_audit_by_verification_id_not_found(mock_get_audit, client):
    mock_get_audit.return_value = None
    response = client.get("/audit/verification/ver_missing")
    assert response.status_code == 404
    assert "no audit trail found" in response.json()["detail"].lower()


# ==============================================================================
# Layer 4: Trust Density Endpoint Tests
# ==============================================================================

@patch("app.api.routes.storage_service.get_trust_density")
def test_get_trust_density_from_cache(mock_get_td, client):
    """GET /trust-density/{location_key} returns cached metrics."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)

    cached = {
        "location_key": "houston_tx",
        "metrics": {
            "location_key": "houston_tx",
            "city": "Houston",
            "state_or_region": "TX",
            "total_claims": 10,
            "verified_claims": 8,
            "supported_count": 6,
            "partially_supported_count": 1,
            "contradicted_count": 1,
            "flagged_count": 2,
            "abstained_count": 0,
            "cost_anomaly_count": 1,
            "cost_anomaly_rate": 0.125,
            "support_ratio": 0.8125,
            "recency_weighted_volume": 8.5,
            "density_score": 0.78,
            "trust_tier": "high",
            "last_updated": now.isoformat(),
        },
        "insight": {
            "location_key": "houston_tx",
            "city": "Houston",
            "state_or_region": "TX",
            "density_score": 0.78,
            "trust_tier": "high",
            "top_anomalous_entities": ["MRI"],
            "top_procedures_audited": ["Metformin", "ER Visit"],
            "summary_text": "HIGH TRUST in Houston, TX: score 0.78",
            "sample_claim_ids": ["clm_1", "clm_2"],
            "recommendation": "Expedited verification eligible.",
        },
    }
    mock_get_td.return_value = cached

    response = client.get("/trust-density/houston_tx")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["metrics"]["location_key"] == "houston_tx"
    assert data["metrics"]["density_score"] == 0.78
    assert data["metrics"]["trust_tier"] == "high"
    assert data["insight"]["city"] == "Houston"


@patch("app.api.routes.storage_service.get_trust_density")
@patch("app.api.routes.storage_service.get_claims_by_location")
def test_get_trust_density_not_found(mock_get_claims, mock_get_td, client):
    """GET /trust-density/{location_key} returns 404 if no data exists."""
    mock_get_td.return_value = None
    mock_get_claims.return_value = []

    response = client.get("/trust-density/nonexistent_xx")
    assert response.status_code == 404
    assert "no claims" in response.json()["detail"].lower() or "not found" in response.json()["detail"].lower()


@patch("app.api.routes.storage_service.list_trust_densities")
@patch("app.api.routes.storage_service.count_trust_densities")
def test_list_trust_densities(mock_count, mock_list, client):
    """GET /trust-density returns paginated list."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)

    mock_list.return_value = [
        {
            "metrics": {
                "location_key": "houston_tx",
                "city": "Houston",
                "state_or_region": "TX",
                "total_claims": 10,
                "verified_claims": 8,
                "supported_count": 6,
                "partially_supported_count": 1,
                "contradicted_count": 1,
                "flagged_count": 2,
                "abstained_count": 0,
                "cost_anomaly_count": 1,
                "cost_anomaly_rate": 0.125,
                "support_ratio": 0.8,
                "recency_weighted_volume": 8.0,
                "density_score": 0.78,
                "trust_tier": "high",
                "last_updated": now.isoformat(),
            }
        }
    ]
    mock_count.return_value = 1

    response = client.get("/trust-density")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["count"] == 1
    assert len(data["locations"]) == 1
    assert data["locations"][0]["location_key"] == "houston_tx"


@patch("app.api.routes.storage_service.list_claims")
@patch("app.api.routes.storage_service.count_claims")
def test_list_claims_with_location_filter(mock_count, mock_list, client, sample_extracted_fields):
    """GET /claims?location=houston_tx returns filtered claims."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)

    mock_claim = Claim(
        claim_id="clm_houston_1",
        original_text="Houston hospital bill",
        source_type="hospital_bill",
        timestamp=now,
        extracted_fields=sample_extracted_fields,
        confidence=0.90,
        provenance=ProvenanceMetadata(
            source_hash="abc123",
            original_snippet="Houston hospital bill",
            text_length=21,
            source_type="hospital_bill",
            ingested_at=now,
        ),
        location=LocationInfo(
            city="Houston",
            state_or_region="TX",
            country="US",
            normalized_key="houston_tx",
        ),
    )
    mock_list.return_value = [mock_claim]
    mock_count.return_value = 1

    response = client.get("/claims?location=houston_tx")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["claims"][0]["claim_id"] == "clm_houston_1"
    assert data["claims"][0]["location"]["normalized_key"] == "houston_tx"
