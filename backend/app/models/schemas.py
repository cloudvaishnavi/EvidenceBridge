"""
Pydantic Schemas for EvidenceBridge Foundational Layer.
Defines core data models for Claims, Provenance, Extraction, and API contracts.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
import uuid
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


class LocationInfo(BaseModel):
    """Normalized geographic location associated with a healthcare claim."""
    model_config = ConfigDict(extra="ignore")

    city: str = Field(..., description="City or municipality (e.g. 'Chicago', 'Atlanta')")
    state_or_region: Optional[str] = Field(None, description="State, province, or region code (e.g. 'IL', 'GA', 'TX')")
    country: str = Field(default="US", description="ISO country code")
    normalized_key: str = Field(..., description="Normalized canonical identifier (e.g. 'chicago_il', 'atlanta_ga')")
    raw_mention: Optional[str] = Field(None, description="Original verbatim location mention in text")
    latitude: Optional[float] = None
    longitude: Optional[float] = None


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
    location: Optional[LocationInfo] = Field(
        default=None,
        description="Geographic location resolved from text or source metadata"
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


# ==============================================================================
# Layer 2: Verification, Support Scoring & Cost Anomaly Schemas
# ==============================================================================

class VerificationVerdict(str, Enum):
    """Verdict representing whether medical evidence supports or refutes a claim."""
    SUPPORTED = "supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    CONTRADICTED = "contradicted"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class VerificationAction(str, Enum):
    """Decision action based on verification verdict and cost anomaly flag."""
    ACCEPT = "accept"    # Supported claim, fair or expected pricing
    FLAG = "flag"        # Contradicted, partially supported, or cost anomaly detected
    ABSTAIN = "abstain"  # Insufficient or inconclusive evidence in knowledge base


class CostBenchmark(BaseModel):
    """Public pricing benchmark for a procedure, test, drug, or hospital service."""
    model_config = ConfigDict(extra="ignore")

    entity: str
    keywords: list[str] = Field(default_factory=list)
    category: Optional[str] = None
    typical_min: float
    typical_max: float
    currency: str = "USD"
    unit: Optional[str] = None
    source: str
    cpt_code: Optional[str] = None


class CostAnomalyDetails(BaseModel):
    """Details of cost anomaly evaluation against public benchmarks."""
    model_config = ConfigDict(extra="ignore")

    is_anomaly: bool = False
    extracted_amount: Optional[float] = None
    benchmark_min: Optional[float] = None
    benchmark_max: Optional[float] = None
    multiplier: Optional[float] = None
    threshold_multiplier: float = 3.0
    severity: str = "none"  # "none", "moderate", "severe", "extreme"
    explanation: str


class EvidenceSnippet(BaseModel):
    """Clinical guideline passage retrieved from local knowledge base."""
    model_config = ConfigDict(extra="ignore")

    guideline_id: str
    title: str
    source: str
    text: str
    relevance_score: Optional[float] = None


class EvidencePassage(BaseModel):
    """
    Detailed evidence passage evaluated during hybrid retrieval,
    tracking relevance score, whether it was utilized, or why it was discarded.
    """
    model_config = ConfigDict(extra="ignore")

    passage_id: str = Field(
        default_factory=lambda: f"pas_{uuid.uuid4().hex[:12]}",
        description="Unique passage identifier"
    )
    guideline_id: Optional[str] = None
    title: str
    source: str
    text: str
    relevance_score: float = Field(
        ...,
        description="Composite relevance score (0.0 to 1.0) combining vector similarity & BM25 keyword match"
    )
    used_in_decision: bool = Field(
        default=True,
        description="Whether this passage exceeded the relevance threshold and was fed to the verification model"
    )
    discard_reason: Optional[str] = Field(
        default=None,
        description="Reason for discarding (e.g. 'Below relevance threshold 0.35', 'Entity mismatch')"
    )


class DecisionStep(BaseModel):
    """Single auditable execution step in the claim processing and verification pipeline."""
    model_config = ConfigDict(extra="ignore")

    step_name: str = Field(..., description="Stage name (e.g. EXTRACTION, RETRIEVAL, COST_CHECK, ABSTENTION_GATE, FINAL_ACTION)")
    input_summary: str
    output_summary: str
    details: Optional[dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class VerificationResult(BaseModel):
    """
    Complete audit result for an extracted claim:
    evidence-based support score, verdict, action decision, and cost anomaly flags.
    """
    model_config = ConfigDict(extra="ignore")

    verification_id: str = Field(
        default_factory=lambda: f"ver_{uuid.uuid4().hex[:16]}",
        description="Unique verification audit identifier"
    )
    claim_id: str
    audit_trail_id: Optional[str] = Field(
        default=None,
        description="Reference to full decision audit trail"
    )
    support_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Numeric score (0.0 to 1.0) indicating strength of evidence support"
    )
    verdict: VerificationVerdict
    action: VerificationAction
    reasoning: str
    evidence_snippets: list[EvidenceSnippet] = Field(default_factory=list)
    passages_considered: list[EvidencePassage] = Field(default_factory=list)
    cost_anomaly_flag: bool = False
    anomaly_details: Optional[CostAnomalyDetails] = None
    location: Optional[LocationInfo] = Field(
        default=None,
        description="Geographic location of the audited claim"
    )
    abstain_reason: Optional[str] = None
    verified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AuditTrail(BaseModel):
    """
    Full transparent decision graph and lineage for a claim:
    tracks all intermediate pipeline steps, considered evidence, and exact rationale.
    """
    model_config = ConfigDict(extra="ignore")

    audit_id: str = Field(
        default_factory=lambda: f"aud_{uuid.uuid4().hex[:16]}",
        description="Unique audit identifier"
    )
    claim_id: str
    verification_id: str
    steps: list[DecisionStep] = Field(default_factory=list)
    passages_considered: list[EvidencePassage] = Field(default_factory=list)
    final_verdict: Optional[VerificationVerdict] = None
    final_action: VerificationAction
    final_reasoning: str
    abstain_triggered: bool = False
    abstain_reason: Optional[str] = None
    cost_anomaly_flag: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class VerificationResponse(BaseModel):
    """Response returned by verification endpoint."""
    success: bool = True
    verification: VerificationResult
    audit_trail_id: Optional[str] = None
    message: str = "Claim verification completed successfully"


class ExtractAndVerifyResponse(BaseModel):
    """Combined response for extraction and verification pipeline."""
    success: bool = True
    claim: Claim
    verification: VerificationResult
    audit_trail_id: Optional[str] = None
    stored: bool
    message: str = "Claim extracted, verified, and linked with provenance"


class AuditResponse(BaseModel):
    """Response returned by audit trail endpoint."""
    success: bool = True
    audit_trail: AuditTrail
    message: str = "Audit trail retrieved successfully"


# ==============================================================================
# Layer 4: Hyperlocal Trust Density Schemas
# ==============================================================================

class TrustTier(str, Enum):
    """Categorical trust tier assigned to a geographic location."""
    HIGH = "high"                      # Clean guidelines, very few anomalies, high support
    MODERATE = "moderate"              # Mixed reports, minor or occasional anomalies
    LOW = "low"                        # Elevated cost anomaly density or frequent contradictions
    CRITICAL_ALERT = "critical_alert"  # Extreme cost markups (>5x) or systematic contradictions
    INSUFFICIENT_DATA = "insufficient_data"  # Fewer than minimum required claims to formulate score


class TrustDensityMetrics(BaseModel):
    """
    Aggregated location-level trust and anomaly density metrics.
    """
    model_config = ConfigDict(extra="ignore")

    location_key: str = Field(..., description="Canonical key, e.g. 'chicago_il'")
    city: str
    state_or_region: Optional[str] = None
    total_claims: int = Field(default=0, description="Total ingested claims in this locality")
    verified_claims: int = Field(default=0, description="Claims that have undergone verification")
    supported_count: int = 0
    partially_supported_count: int = 0
    contradicted_count: int = 0
    flagged_count: int = 0
    abstained_count: int = 0
    cost_anomaly_count: int = 0
    cost_anomaly_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    support_ratio: float = Field(default=0.0, ge=0.0, le=1.0)
    recency_weighted_volume: float = 0.0
    density_score: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Composite trust density score (0.0 to 1.0) where 1.0 is peak clinical & billing reliability"
    )
    trust_tier: TrustTier = Field(default=TrustTier.INSUFFICIENT_DATA)
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class LocationInsight(BaseModel):
    """
    Synthesized audit insight and risk summary for a geographic locality.
    """
    model_config = ConfigDict(extra="ignore")

    location_key: str
    city: str
    state_or_region: Optional[str] = None
    density_score: float
    trust_tier: TrustTier
    top_anomalous_entities: list[str] = Field(default_factory=list)
    top_procedures_audited: list[str] = Field(default_factory=list)
    summary_text: str
    sample_claim_ids: list[str] = Field(default_factory=list)
    recommendation: Optional[str] = None


class TrustDensityResponse(BaseModel):
    """Response payload for a single location trust density query."""
    success: bool = True
    metrics: TrustDensityMetrics
    insight: Optional[LocationInsight] = None
    message: str = "Trust density metrics retrieved successfully"


class TrustDensityListResponse(BaseModel):
    """Paginated list of location trust density records."""
    total: int
    count: int
    locations: list[TrustDensityMetrics]
