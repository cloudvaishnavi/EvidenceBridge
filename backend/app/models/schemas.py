"""
Pydantic Schemas for EvidenceBridge Foundational Layer.
Defines core data models for Claims, Provenance, Extraction, and API contracts.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field, model_validator


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
    user_id: Optional[str] = Field(
        default=None,
        description="ID of the user who owns or submitted this claim for personal memory and data isolation"
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
    user_id: Optional[str] = Field(
        default=None,
        description="Optional ID of the authenticated user to attribute the claim to"
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
    benchmark_matched: bool = False
    currency: str = "USD"
    extracted_amount: Optional[float] = None
    benchmark_min: Optional[float] = None
    benchmark_max: Optional[float] = None
    multiplier: Optional[float] = None
    threshold_multiplier: float = 3.0
    severity: str = "none"  # "none", "moderate", "severe", "extreme"
    explanation: str
    benchmark_name: Optional[str] = None
    benchmark_source: Optional[str] = None
    cpt_code: Optional[str] = None

    @model_validator(mode="after")
    def sync_benchmark_matched(self) -> "CostAnomalyDetails":
        if self.benchmark_max is not None and not self.benchmark_matched:
            self.benchmark_matched = True
        return self


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
    raw_model_verdict: Optional[str] = Field(default=None, description="Raw model verdict before safety gate policy overrides")
    raw_model_support_score: Optional[float] = Field(default=None, description="Raw model support score before safety gate policy overrides")
    policy_override_applied: bool = Field(default=False, description="Whether safety gates or cost rules overrode the raw model verdict")
    policy_override_reason: Optional[str] = Field(default=None, description="Explicit rationale for policy override")
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
    verified_claims: int = Field(
        default=0,
        description="Total claims that have undergone verification audit (including accepted, flagged, and abstained). Labeled in UI as 'Audited (Verified)'",
    )
    supported_count: int = Field(default=0, description="Claims verified as SUPPORTED by clinical guidelines")
    partially_supported_count: int = Field(default=0, description="Claims verified as PARTIALLY_SUPPORTED")
    contradicted_count: int = Field(default=0, description="Claims verified as CONTRADICTED by clinical guidelines")
    flagged_count: int = Field(default=0, description="Claims flagged for manual review")
    abstained_count: int = Field(default=0, description="Claims where verification abstained due to insufficient evidence")
    cost_anomaly_count: int = Field(default=0, description="Claims flagged with pricing markup anomalies")
    cost_anomaly_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="Ratio of cost anomalies to audited claims: cost_anomaly_count / verified_claims")
    support_ratio: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Ratio of clinical support among conclusive audits: (supported + 0.5 * partially_supported) / (supported + partially_supported + contradicted). Evaluates to 0.0 when 0 conclusive audits exist.",
    )
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


# ==============================================================================
# Layer 6: Evaluation Harness & Calibration Schemas
# ==============================================================================

class EvaluationLabel(BaseModel):
    """Ground truth gold label for an evaluation benchmark case."""
    model_config = ConfigDict(extra="ignore")

    case_id: str
    category: Optional[str] = None
    raw_text: str
    source_type: str = "clinical_note"
    expected_entity: Optional[str] = None
    gold_verdict: str  # "supported", "partially_supported", "contradicted", "insufficient_evidence"
    gold_action: str   # "ACCEPT", "FLAG", "ABSTAIN"
    cost_anomaly_flag: bool = False
    expected_rule_triggered: Optional[str] = None
    note: Optional[str] = None


class MetricResult(BaseModel):
    """Statistical evaluation metrics for a specific class or binary task."""
    model_config = ConfigDict(extra="ignore")

    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    accuracy: Optional[float] = None
    support_count: int = 0
    predicted_count: int = 0
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0


class CalibrationBin(BaseModel):
    """Reliability calibration bin for expected calibration error (ECE)."""
    model_config = ConfigDict(extra="ignore")

    bin_index: int
    bin_lower: float
    bin_upper: float
    sample_count: int = 0
    avg_confidence: float = 0.0
    empirical_accuracy: float = 0.0
    calibration_error: float = 0.0


class AbstentionMetrics(BaseModel):
    """Metrics assessing the precision, recall, and safety calibration of the abstention gate."""
    model_config = ConfigDict(extra="ignore")

    total_samples: int = 0
    total_abstained: int = 0
    abstention_rate: float = 0.0
    correct_abstentions: int = 0  # True positive abstentions (gold was insufficient_evidence / ABSTAIN)
    over_abstentions: int = 0     # False positive abstentions (system abstained when gold was conclusive)
    under_abstentions: int = 0    # False negative abstentions (system was conclusive when gold was abstain)
    abstention_precision: float = 0.0
    abstention_recall: float = 0.0
    abstention_f1: float = 0.0


class SampleEvaluationDetail(BaseModel):
    """Detailed side-by-side comparison for a single evaluation sample."""
    model_config = ConfigDict(extra="ignore")

    case_id: str
    predicted_verdict: str
    gold_verdict: str
    verdict_correct: bool
    predicted_action: str
    gold_action: str
    action_correct: bool
    predicted_cost_anomaly: bool
    gold_cost_anomaly: bool
    cost_anomaly_correct: bool
    support_score: float
    rule_triggered: Optional[str] = None
    claim_id: Optional[str] = None
    explanation: Optional[str] = None


class EvaluationReport(BaseModel):
    """Comprehensive evaluation report stored in MongoDB and returned via API."""
    model_config = ConfigDict(extra="ignore")

    run_id: str = Field(default_factory=lambda: f"eval_{uuid.uuid4().hex[:12]}")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    dataset_name: str = "controlled_cases.json"
    total_samples: int = 0

    # Verdict performance
    overall_verdict_accuracy: float = 0.0
    macro_verdict_f1: float = 0.0
    verdict_metrics: dict[str, MetricResult] = Field(default_factory=dict)

    # Action performance
    overall_action_accuracy: float = 0.0
    macro_action_f1: float = 0.0
    action_metrics: dict[str, MetricResult] = Field(default_factory=dict)

    # Cost anomaly performance
    cost_anomaly_metrics: MetricResult = Field(default_factory=MetricResult)

    # Abstention gate calibration
    abstention_metrics: AbstentionMetrics = Field(default_factory=AbstentionMetrics)

    # Confidence calibration
    calibration_bins: list[CalibrationBin] = Field(default_factory=list)
    expected_calibration_error: float = 0.0

    # Human-readable report & guidance
    markdown_report: str = ""
    recommendations: list[str] = Field(default_factory=list)
    sample_evaluations: list[SampleEvaluationDetail] = Field(default_factory=list)
    user_id: Optional[str] = Field(default=None, description="User ID who executed this evaluation run")


class EvaluationRunRequest(BaseModel):
    """Payload to trigger an evaluation run."""
    model_config = ConfigDict(extra="ignore")

    dataset_path: Optional[str] = None
    case_ids: Optional[list[str]] = None
    force_reverify: bool = False
    offline_mode: bool = False
    custom_labels: Optional[list[EvaluationLabel]] = None
    user_id: Optional[str] = Field(default=None, description="Optional user ID attributing the evaluation run")


class EvaluationRunResponse(BaseModel):
    """Response payload returning evaluation execution results."""
    success: bool = True
    run_id: str
    report: EvaluationReport
    message: str = "Evaluation run completed successfully"


class EvaluationListResponse(BaseModel):
    """List of recent evaluation reports."""
    total: int
    count: int
    runs: list[EvaluationReport]


# ---------------------------------------------------------------------------
# Community Stories (Recovery Stories)
# ---------------------------------------------------------------------------

class CommunityStoryCreate(BaseModel):
    """Payload to post a voluntary personal recovery or coping story."""
    model_config = ConfigDict(extra="ignore")

    title: Optional[str] = Field(None, max_length=150, description="Optional brief title for the story")
    story_text: str = Field(..., min_length=10, max_length=5000, description="Personal story and what helped cope or recover")
    author_name: Optional[str] = Field("Community Member", max_length=80, description="Name or alias")
    condition_or_topic: Optional[str] = Field(None, max_length=100, description="Optional topic or condition tag")
    contact_email: Optional[str] = Field(None, max_length=120, description="Optional voluntary public email")
    contact_instagram: Optional[str] = Field(None, max_length=80, description="Optional voluntary public Instagram handle")
    consent_acknowledged: bool = Field(True, description="Confirmation that story and contact will be public")
    user_id: Optional[str] = Field(None, description="Optional user ID of author if authenticated")


class CommunityStory(BaseModel):
    """Stored community recovery story."""
    model_config = ConfigDict(extra="ignore")

    story_id: str
    title: Optional[str] = None
    story_text: str
    author_name: str = "Community Member"
    condition_or_topic: Optional[str] = None
    contact_email: Optional[str] = None
    contact_instagram: Optional[str] = None
    consent_acknowledged: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    user_id: Optional[str] = Field(None, description="User ID of author if authenticated")


class CommunityStoryListResponse(BaseModel):
    """Response containing list of community recovery stories."""
    total: int
    count: int
    stories: list[CommunityStory]


# ---------------------------------------------------------------------------
# Visual Insights & Statistics
# ---------------------------------------------------------------------------

class DecisionOverview(BaseModel):
    """Decision breakdown: Approved, Flagged, Held."""
    approved: int = Field(default=0, description="Claims approved (ACCEPT)")
    flagged: int = Field(default=0, description="Claims flagged for review (FLAG)")
    held: int = Field(default=0, description="Claims held for information (ABSTAIN)")
    total: int = Field(default=0, description="Total verified claims")


class PriceAlertsOverview(BaseModel):
    """Price markup breakdown: Normal vs Anomaly tiers."""
    normal_charges: int = Field(default=0, description="Charges within normal benchmark (<3x)")
    price_alerts: int = Field(default=0, description="Charges triggering price markup alerts (>=3x)")
    moderate: int = Field(default=0, description="Moderate markups (3x - 5x)")
    severe: int = Field(default=0, description="Severe markups (5x - 10x)")
    extreme: int = Field(default=0, description="Extreme markups (>=10x)")
    total: int = Field(default=0, description="Total cost-audited claims")


class GuidelineSupportOverview(BaseModel):
    """Clinical guideline match verdict breakdown."""
    supported: int = Field(default=0, description="Conclusive evidence supporting claim")
    partially_supported: int = Field(default=0, description="Partial evidence supporting claim")
    contradicted: int = Field(default=0, description="Evidence contradicting or contraindicating claim")
    insufficient_evidence: int = Field(default=0, description="No or inadequate guideline evidence found")
    total: int = Field(default=0, description="Total verified claims")


class GapsAndRisks(BaseModel):
    """High-priority systemic gaps and clinical risks."""
    insufficient_evidence_claims: int = Field(default=0, description="Claims lacking guideline evidence")
    extreme_price_markups: int = Field(default=0, description="Claims with >=10x hospital markups")
    held_by_safety_rules: int = Field(default=0, description="Claims where safety rules halted automated decision")
    unbenchmarked_high_cost: int = Field(default=0, description="High-cost items without standard benchmarks")


class ProcedureFrequency(BaseModel):
    """Procedure occurrence count in audited corpus."""
    procedure_name: str
    count: int


class LocationFrequency(BaseModel):
    """Metropolitan occurrence count and pricing anomaly rate."""
    location_name: str
    claims_count: int
    anomalies_count: int = 0


class ClaimHighlight(BaseModel):
    """Summary of a notable risk or flagged claim."""
    claim_id: str
    entity: str
    action: str
    verdict: Optional[str] = None
    cost_range: Optional[str] = None
    reason: Optional[str] = None
    timestamp: Optional[datetime] = None


class InsightsSummaryResponse(BaseModel):
    """Aggregated statistics and visual metrics across claims and verifications."""
    model_config = ConfigDict(extra="ignore")

    total_claims: int = 0
    total_verified: int = 0
    decision_overview: DecisionOverview = Field(default_factory=DecisionOverview)
    price_alerts_overview: PriceAlertsOverview = Field(default_factory=PriceAlertsOverview)
    guideline_support_overview: GuidelineSupportOverview = Field(default_factory=GuidelineSupportOverview)
    gaps_and_risks: GapsAndRisks = Field(default_factory=GapsAndRisks)
    top_procedures: list[ProcedureFrequency] = Field(default_factory=list)
    top_locations: list[LocationFrequency] = Field(default_factory=list)
    recent_risk_claims: list[ClaimHighlight] = Field(default_factory=list)
    is_baseline_fallback: bool = False


# ---------------------------------------------------------------------------
# User Authentication & Profiles (Part 2)
# ---------------------------------------------------------------------------

class UserCreateRequest(BaseModel):
    """Payload for user sign up."""
    model_config = ConfigDict(extra="ignore")

    name: str = Field(..., min_length=1, max_length=100, description="Full name")
    email: str = Field(..., min_length=3, max_length=150, description="Email address or username")
    password: str = Field(..., min_length=4, max_length=100, description="Raw password")
    organization: Optional[str] = Field(None, max_length=150, description="Hospital or organization")


class UserLoginRequest(BaseModel):
    """Payload for user login."""
    model_config = ConfigDict(extra="ignore")

    email: str = Field(..., min_length=1, description="Email address or username")
    password: str = Field(..., min_length=1, description="Password")


class UserResponse(BaseModel):
    """Safe user profile response without password hash."""
    model_config = ConfigDict(extra="ignore")

    user_id: str
    name: str
    email: str
    role: str = "Clinical Claims Reviewer"
    organization: Optional[str] = "Independent Clinical Reviewer"
    created_at: datetime


class AuthResponse(BaseModel):
    """Response returned upon successful login or sign up."""
    model_config = ConfigDict(extra="ignore")

    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ---------------------------------------------------------------------------
# Hospital Finder & Price Comparison Schemas
# ---------------------------------------------------------------------------

class HospitalProcedurePrice(BaseModel):
    """Verified or benchmark price for a procedure or consultation."""
    model_config = ConfigDict(extra="ignore")

    service_name: str
    cpt_code: Optional[str] = None
    min_price: float
    max_price: float
    typical_price: Optional[float] = None
    currency: str = "USD"
    price_type: str = "Official Published Benchmark"
    source: str
    last_updated: str


class HospitalDetail(BaseModel):
    """Comprehensive hospital/facility detail with attributable trust and real prices."""
    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    address: str
    neighborhood: Optional[str] = None
    city: str
    state_or_region: Optional[str] = None
    country: str = "US"
    lat: float
    lon: float
    distance_km: Optional[float] = None
    distance_miles: Optional[float] = None
    distance_label: str = "Straight-line distance"
    facility_type: str = "General Hospital"
    verified_services: list[str] = Field(default_factory=list)
    phone: Optional[str] = None
    website: Optional[str] = None
    directions_url: Optional[str] = None

    # Real prices & cost comparison
    price_available: bool = False
    consultation_fee: Optional[float] = None
    consultation_fee_currency: str = "USD"
    consultation_fee_source: Optional[str] = None
    consultation_fee_date: Optional[str] = None
    price_type: str = "Unavailable"
    procedure_prices: list[HospitalProcedurePrice] = Field(default_factory=list)

    # Local trust & accreditation
    public_rating: Optional[float] = None
    review_count: Optional[int] = None
    review_source: Optional[str] = None
    review_date: Optional[str] = None
    accreditations: list[str] = Field(default_factory=list)
    trust_score: Optional[float] = None
    trust_score_explanation: Optional[str] = None

    why_appears: str = "Located in your requested area."
    data_source: str = "OpenStreetMap & Published Healthcare Benchmarks"
    last_updated: str = Field(default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%d"))


class EmergencyAlert(BaseModel):
    """Immediate high-priority guidance for urgent clinical symptoms."""
    model_config = ConfigDict(extra="ignore")

    is_emergency: bool = False
    warning_title: Optional[str] = None
    warning_message: Optional[str] = None
    emergency_phone: Optional[str] = None
    action_advice: Optional[str] = None


class HospitalSearchResponse(BaseModel):
    """Payload returned by Hospital Finder search."""
    model_config = ConfigDict(extra="ignore")

    query_city: str
    search_coordinates: Optional[dict[str, float]] = None
    total_results: int
    symptom_filter: Optional[str] = None
    symptom_guidance: Optional[str] = None
    emergency_alert: Optional[EmergencyAlert] = None
    hospitals: list[HospitalDetail] = Field(default_factory=list)
    data_sources_used: list[str] = Field(default_factory=list)
    disclaimer: str = (
        "EvidenceBridge Hospital Finder provides facility location, published price benchmarks, and "
        "accreditation data for informational comparison only. This is not a medical diagnosis or treatment recommendation. "
        "Distances are calculated as straight-line distance from specified coordinates."
    )

