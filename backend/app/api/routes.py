"""
API Routes for EvidenceBridge.
Endpoints for structured extraction, provenance tracking, claim retrieval,
claim verification, cost anomaly detection, and system health.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.config import get_settings
from app.models.schemas import (
    Claim,
    ClaimListResponse,
    ExtractAndVerifyResponse,
    ExtractionRequest,
    ExtractionResponse,
    HealthResponse,
    VerificationResponse,
    VerificationResult,
)
from app.services.extraction import (
    ExtractionError,
    ExtractionService,
    OllamaConnectionError,
)
from app.services.provenance import ProvenanceService
from app.services.storage import StorageError, storage_service
from app.services.vector_store import vector_store_service
from app.services.verification import verification_service
from app.utils.logger import logger

router = APIRouter()
settings = get_settings()
extraction_service = ExtractionService()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Check status of backend, MongoDB connection, local Ollama LLM, and local vector store."
)
async def health_check() -> HealthResponse:
    """System health check endpoint."""
    mongo_health = await storage_service.check_health()
    ollama_health = await extraction_service.check_health()
    vector_health = vector_store_service.check_health()

    is_mongo_ok = mongo_health.get("status") == "healthy"
    is_ollama_ok = ollama_health.get("status") == "healthy"

    overall_status = "ok" if (is_mongo_ok and is_ollama_ok) else "degraded"

    return HealthResponse(
        status=overall_status,
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        services={
            "mongodb": mongo_health,
            "ollama": ollama_health,
            "vector_store": vector_health,
        }
    )


@router.post(
    "/extract",
    response_model=ExtractionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Extract structured claim with provenance",
    description="Accepts raw clinical notes, patient forum reports, or hospital bill lines. Runs extraction via local Ollama LLM, attaches tamper-evident provenance, and stores the claim."
)
async def extract_claim(request: ExtractionRequest) -> ExtractionResponse:
    """Submit raw text and get back structured claim with full provenance."""
    raw_text = request.text.strip()
    if not raw_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Input text cannot be empty."
        )

    # 1. Run local extraction
    try:
        extracted_fields, confidence = await extraction_service.extract_structured_claim(raw_text)
    except OllamaConnectionError as e:
        logger.error(f"Ollama connection error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "Ollama LLM is unreachable",
                "message": str(e),
                "resolution": f"Ensure Ollama is running at {settings.OLLAMA_BASE_URL} and model '{settings.OLLAMA_MODEL}' is pulled (`ollama pull {settings.OLLAMA_MODEL}`)."
            }
        )
    except ExtractionError as e:
        logger.error(f"Extraction error: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Extraction model error: {e}"
        )

    # 2. Attach strict provenance
    claim = ProvenanceService.assemble_claim(
        original_text=raw_text,
        extracted_fields=extracted_fields,
        confidence=confidence,
        source_type=request.source_type,
        source_url=request.source_url,
        source_timestamp=request.source_timestamp,
    )

    # 3. Store in MongoDB if requested
    stored = False
    if request.store_claim:
        try:
            await storage_service.insert_claim(claim)
            stored = True
            # 4. Asynchronously index into local vector store for semantic retrieval
            indexed = vector_store_service.add_claim(claim)
            claim.indexed_vector = indexed
        except StorageError as e:
            logger.warning(f"Could not persist claim to MongoDB: {e}")
            stored = False

    return ExtractionResponse(
        success=True,
        claim=claim,
        stored=stored,
        message="Claim successfully extracted and linked with provenance" + (" (stored)" if stored else " (storage skipped or offline)")
    )


@router.get(
    "/claims/{claim_id}",
    response_model=Claim,
    summary="Get claim by ID",
    description="Retrieve a stored claim and its full provenance trail by its unique claim ID."
)
async def get_claim(claim_id: str) -> Claim:
    """Retrieve single claim by ID."""
    try:
        claim = await storage_service.get_claim(claim_id)
    except StorageError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database storage service error: {e}"
        )

    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Claim with ID '{claim_id}' not found."
        )

    # Verify provenance integrity before returning
    if not ProvenanceService.verify_provenance(claim):
        logger.warning(f"Provenance digest mismatch detected for {claim_id}")

    return claim


@router.get(
    "/claims",
    response_model=ClaimListResponse,
    summary="List stored claims",
    description="Retrieve a paginated list of claims with provenance, sorted newest first."
)
async def list_claims(
    limit: int = Query(default=20, ge=1, le=100, description="Max claims to return"),
    skip: int = Query(default=0, ge=0, description="Number of claims to skip")
) -> ClaimListResponse:
    """List claims stored in EvidenceBridge."""
    try:
        claims = await storage_service.list_claims(limit=limit, skip=skip)
        total = await storage_service.count_claims()
        return ClaimListResponse(
            total=total,
            count=len(claims),
            claims=claims
        )
    except StorageError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database storage service error: {e}"
        )


# ==============================================================================
# Layer 2: Claim Verification & Cost Anomaly Endpoints
# ==============================================================================

@router.post(
    "/verify/{claim_id}",
    response_model=VerificationResponse,
    summary="Verify existing claim by ID",
    description="Audits an existing claim against local clinical guidelines and pricing benchmarks using local Ollama model. Produces support score, verdict, action decision, and cost anomaly flags."
)
async def verify_claim_by_id(claim_id: str) -> VerificationResponse:
    """Verify an existing stored claim by its unique ID."""
    # 1. Fetch claim from database
    try:
        claim = await storage_service.get_claim(claim_id)
    except StorageError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Storage error fetching claim: {e}"
        )

    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Claim with ID '{claim_id}' not found for verification."
        )

    # 2. Run verification pipeline
    try:
        verification = await verification_service.verify_claim(claim)
    except OllamaConnectionError as e:
        logger.error(f"Ollama connection error during verification: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "Ollama LLM is unreachable for verification",
                "message": str(e),
                "resolution": f"Ensure Ollama is running at {settings.OLLAMA_BASE_URL}."
            }
        )
    except ExtractionError as e:
        logger.error(f"Verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Verification model error: {e}"
        )

    # 3. Save verification result linked to claim_id
    try:
        await storage_service.insert_verification(verification)
    except StorageError as e:
        logger.warning(f"Could not persist verification result to MongoDB: {e}")

    return VerificationResponse(
        success=True,
        verification=verification,
        message=f"Claim '{claim_id}' verified. Verdict: {verification.verdict.value}, Action: {verification.action.value}."
    )


@router.post(
    "/extract-and-verify",
    response_model=ExtractAndVerifyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Extract claim and verify in one step",
    description="Submits raw text, runs extraction, binds provenance, and immediately runs clinical evidence verification and cost anomaly checks."
)
async def extract_and_verify(request: ExtractionRequest) -> ExtractAndVerifyResponse:
    """Extract structured claim and immediately audit it against knowledge base."""
    raw_text = request.text.strip()
    if not raw_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Input text cannot be empty."
        )

    # 1. Extract claim
    try:
        extracted_fields, confidence = await extraction_service.extract_structured_claim(raw_text)
    except OllamaConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "Ollama LLM is unreachable",
                "message": str(e),
                "resolution": f"Ensure Ollama is running at {settings.OLLAMA_BASE_URL}."
            }
        )
    except ExtractionError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Extraction model error: {e}"
        )

    # 2. Assemble claim with tamper-evident provenance
    claim = ProvenanceService.assemble_claim(
        original_text=raw_text,
        extracted_fields=extracted_fields,
        confidence=confidence,
        source_type=request.source_type,
        source_url=request.source_url,
        source_timestamp=request.source_timestamp,
    )

    # 3. Store claim
    stored = False
    if request.store_claim:
        try:
            await storage_service.insert_claim(claim)
            stored = True
            indexed = vector_store_service.add_claim(claim)
            claim.indexed_vector = indexed
        except StorageError as e:
            logger.warning(f"Could not persist claim to MongoDB: {e}")

    # 4. Run verification and cost anomaly audit
    try:
        verification = await verification_service.verify_claim(claim)
    except Exception as e:
        logger.error(f"Verification stage failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Verification failed: {e}"
        )

    # 5. Store verification result
    if request.store_claim:
        try:
            await storage_service.insert_verification(verification)
        except StorageError as e:
            logger.warning(f"Could not persist verification result: {e}")

    return ExtractAndVerifyResponse(
        success=True,
        claim=claim,
        verification=verification,
        stored=stored,
        message=f"Claim extracted and verified. Verdict: {verification.verdict.value}, Action: {verification.action.value}."
    )


@router.get(
    "/verification/{claim_id}",
    response_model=VerificationResult,
    summary="Get verification result by claim ID",
    description="Retrieve the audit outcome, support score, evidence snippets, and cost anomaly details for a specific claim ID."
)
async def get_verification(claim_id: str) -> VerificationResult:
    """Retrieve existing verification result by claim ID."""
    try:
        verification = await storage_service.get_verification(claim_id)
    except StorageError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database storage error: {e}"
        )

    if not verification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No verification record found for claim ID '{claim_id}'. Run POST /verify/{claim_id} first."
        )

    return verification
