"""
Pydantic Schemas for EvidenceBridge Foundational Layer.
Defines core data models for Claims, Provenance, Extraction, and API contracts.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field


class SourceType(str, Enum):
    CLINICAL_NOTE = "clinical_note"
    PATIENT_REPORT = "patient_report"
    HOSPITAL_BILL = "hospital_bill"
    FORUM_POST = "forum_post"
    OTHER = "other"


class SentimentType(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"


class ExtractedFields(BaseModel):
    """Structured clinical and billing fields extracted by the model."""
    model_config = ConfigDict(extra="ignore")

    entity: str = Field(
        ...,
        description="Medical entity: drug name, procedure, diagnostic test, or billed line item"
    )
    effect_or_outcome: Optional[str] = Field(
        None,
        description="Observed clinical outcome, patient effect, side effect, or procedure finding"
    )
    cost_range: Optional[str] = Field(
        None,
        description="Billed charge, copay, price range, or financial figure if mentioned (e.g. '$1,200', '$4,500 - $6,000')"
    )
    location_city: Optional[str] = Field(
        None,
        description="City, state, or hospital/facility name if present in text"
    )
    sentiment: SentimentType = Field(
        default=SentimentType.NEUTRAL,
        description="Sentiment towards medical outcome or hospital billing experience"
    )
    reasoning: Optional[str] = Field(
        None,
        description="Brief justification or explanation of extraction"
    )
    raw_model_output: Optional[dict[str, Any]] = Field(
        None,
        description="Full raw JSON response from local Ollama model for provenance and debugging"
    )


class ProvenanceMetadata(BaseModel):
    """
    Immutable provenance metadata linking structured claims back to raw ground-truth source.
    """
    model_config = ConfigDict(extra="ignore")

    source_hash: str = Field(
        ...,
        description="Cryptographic SHA-256 hash of the exact original raw text"
    )
    original_snippet: str = Field(
        ...,
        description="Verbatim initial snippet/anchor from the raw text"
    )
    text_length: int = Field(
        ...,
        description="Character count of original raw text"
    )
    source_type: str = Field(
        ...,
        description="Document origin classification (clinical_note, patient_report, hospital_bill, etc.)"
    )
    source_url: Optional[str] = Field(
        None,
        description="Source URL, document URI, or EHR record identifier"
    )
    source_timestamp: Optional[datetime] = Field(
        None,
        description="Timestamp recorded at origin if available"
    )
    ingested_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when EvidenceBridge ingested the record"
    )


class Claim(BaseModel):
    """
    Core Claim entity in EvidenceBridge.
    Combines extracted medical/cost data with strict provenance tracking.
    """
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    claim_id: str = Field(
        ...,
        description="Unique identifier for the claim (prefixed UUID, e.g. clm_a1b2c3d4...)"
    )
    original_text: str = Field(
        ...,
        description="Full original text from which the claim was extracted"
    )
    source_type: str = Field(
        ...,
        description="Source classification type"
    )
    source_url: Optional[str] = Field(
        None,
        description="Original source link or identifier"
    )
    timestamp: datetime = Field(
        ...,
        description="Timestamp of claim (source timestamp if known, otherwise ingestion time)"
    )
    extracted_fields: ExtractedFields = Field(
        ...,
        description="Structured extracted entities and outcomes"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score of the extraction between 0.0 and 1.0"
    )
    provenance: ProvenanceMetadata = Field(
        ...,
        description="Strict source provenance metadata"
    )
    indexed_vector: bool = Field(
        default=False,
        description="Whether this claim has been indexed into the local vector store"
    )


class ExtractionRequest(BaseModel):
    """Input payload to trigger extraction and provenance tracking."""
    text: str = Field(
        ...,
        min_length=3,
        description="Verbatim clinical note, patient report, or hospital bill line text"
    )
    source_type: Optional[str] = Field(
        default="clinical_note",
        description="Origin classification: clinical_note, patient_report, hospital_bill, forum_post, other"
    )
    source_url: Optional[str] = Field(
        default=None,
        description="Optional origin URL, EMR/EHR ID, or public forum link"
    )
    source_timestamp: Optional[datetime] = Field(
        default=None,
        description="Optional original creation date/time (ISO 8601)"
    )
    store_claim: bool = Field(
        default=True,
        description="Whether to persist the extracted claim into MongoDB"
    )


class ExtractionResponse(BaseModel):
    """API response containing extracted claim, provenance, and storage status."""
    success: bool = True
    claim: Claim
    stored: bool
    message: str = "Claim successfully extracted and linked with provenance"


class ClaimListResponse(BaseModel):
    """Paginated list response for claims."""
    total: int
    count: int
    claims: list[Claim]


class HealthResponse(BaseModel):
    """System health status."""
    status: str
    app_name: str
    version: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    services: dict[str, Any]
