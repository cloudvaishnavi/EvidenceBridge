// ============================================================
// EvidenceBridge Frontend — TypeScript types
// Mirrors backend Pydantic schemas (Layer 1–4)
// ============================================================

export type SourceType =
  | 'clinical_note'
  | 'patient_report'
  | 'hospital_bill'
  | 'forum_post'
  | 'other'

export type SentimentType = 'positive' | 'negative' | 'neutral' | 'mixed'

export type VerificationVerdict =
  | 'supported'
  | 'partially_supported'
  | 'contradicted'
  | 'insufficient_evidence'

export type VerificationAction = 'accept' | 'flag' | 'abstain'

export type TrustTier =
  | 'high'
  | 'moderate'
  | 'low'
  | 'critical_alert'
  | 'insufficient_data'

// ---- Sub-schemas ----

export interface ExtractedFields {
  entity: string
  effect_or_outcome: string | null
  cost_range: string | null
  location_city: string | null
  sentiment: SentimentType
  reasoning: string | null
  raw_model_output?: Record<string, unknown> | null
}

export interface ProvenanceMetadata {
  source_hash: string
  original_snippet: string
  text_length: number
  source_type: string
  source_url: string | null
  source_timestamp: string | null
  ingested_at: string
}

export interface LocationInfo {
  city: string
  state_or_region: string | null
  country: string
  normalized_key: string
  raw_mention: string | null
  latitude: number | null
  longitude: number | null
}

export interface EvidenceSnippet {
  guideline_id: string | null
  title: string
  source: string
  text: string
  relevance_score: number
}

export interface EvidencePassage {
  passage_id: string
  guideline_id: string | null
  title: string
  source: string
  text: string
  relevance_score: number
  used_in_decision: boolean
  discard_reason: string | null
}

export interface CostAnomalyDetails {
  is_anomaly: boolean
  extracted_amount: number | null
  benchmark_min: number | null
  benchmark_max: number | null
  multiplier: number | null
  threshold_multiplier: number
  severity: string | null
  explanation: string
}

export interface DecisionStep {
  step_name: string
  input_summary: string
  output_summary: string
  details: Record<string, unknown> | null
  timestamp: string
}

// ---- Core entities ----

export interface Claim {
  claim_id: string
  original_text: string
  source_type: string
  source_url: string | null
  timestamp: string
  extracted_fields: ExtractedFields
  confidence: number
  provenance: ProvenanceMetadata
  location: LocationInfo | null
  indexed_vector: boolean
}

export interface VerificationResult {
  verification_id: string
  claim_id: string
  audit_trail_id: string | null
  support_score: number
  verdict: VerificationVerdict
  action: VerificationAction
  reasoning: string
  evidence_snippets: EvidenceSnippet[]
  passages_considered: EvidencePassage[]
  cost_anomaly_flag: boolean
  anomaly_details: CostAnomalyDetails | null
  location: LocationInfo | null
  abstain_reason: string | null
  verified_at: string
}

export interface AuditTrail {
  audit_id: string
  claim_id: string
  verification_id: string
  steps: DecisionStep[]
  passages_considered: EvidencePassage[]
  final_verdict: VerificationVerdict
  final_action: VerificationAction
  final_reasoning: string
  abstain_triggered: boolean
  abstain_reason: string | null
  cost_anomaly_flag: boolean
  created_at: string
}

// ---- Trust Density ----

export interface TrustDensityMetrics {
  location_key: string
  city: string
  state_or_region: string | null
  total_claims: number
  verified_claims: number
  supported_count: number
  partially_supported_count: number
  contradicted_count: number
  flagged_count: number
  abstained_count: number
  cost_anomaly_count: number
  cost_anomaly_rate: number
  support_ratio: number
  recency_weighted_volume: number
  density_score: number
  trust_tier: TrustTier
  last_updated: string
}

export interface LocationInsight {
  location_key: string
  city: string
  state_or_region: string | null
  density_score: number
  trust_tier: TrustTier
  top_anomalous_entities: string[]
  top_procedures_audited: string[]
  summary_text: string
  sample_claim_ids: string[]
  recommendation: string | null
}

// ---- API request/response shapes ----

export interface ExtractionRequest {
  text: string
  source_type?: SourceType
  source_url?: string | null
  source_timestamp?: string | null
  store_claim?: boolean
}

export interface ExtractionResponse {
  success: boolean
  claim: Claim
  stored: boolean
  message: string
}

export interface VerificationResponse {
  success: boolean
  verification: VerificationResult
  audit_trail_id: string | null
  message: string
}

export interface ExtractAndVerifyResponse {
  success: boolean
  claim: Claim
  verification: VerificationResult
  audit_trail_id: string | null
  stored: boolean
  message: string
}

export interface ClaimListResponse {
  total: number
  count: number
  claims: Claim[]
}

export interface AuditResponse {
  success: boolean
  audit_trail: AuditTrail
  message: string
}

export interface TrustDensityResponse {
  success: boolean
  metrics: TrustDensityMetrics
  insight: LocationInsight | null
  message: string
}

export interface TrustDensityListResponse {
  total: number
  count: number
  locations: TrustDensityMetrics[]
}

export interface HealthResponse {
  status: string
  app_name: string
  version: string
  services: {
    mongodb: Record<string, unknown>
    ollama: Record<string, unknown>
    vector_store: Record<string, unknown>
  }
}

export type HealthStatus = HealthResponse

// ---- Client error ----

export class ApiError extends Error {
  constructor(public message: string, public status: number) {
    super(message)
    this.name = 'ApiError'
  }
}
