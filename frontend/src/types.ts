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
  cost_currency?: string | null
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
  benchmark_matched?: boolean
  currency?: string | null
  benchmark_currency?: string | null
  extracted_amount: number | null
  benchmark_min: number | null
  benchmark_max: number | null
  multiplier: number | null
  threshold_multiplier: number
  severity: string | null
  explanation: string
  benchmark_name?: string | null
  benchmark_source?: string | null
  cpt_code?: string | null
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
  user_id?: string | null
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
  raw_model_verdict?: string | null
  raw_model_support_score?: number | null
  policy_override_applied?: boolean
  policy_override_reason?: string | null
  created_at: string
}

// ---- Trust Density ----

export interface TrustDensityMetrics {
  location_key: string
  city: string
  state_or_region: string | null
  total_claims: number
  /** Total claims that have undergone verification audit (including supported, flagged, and abstained). Labeled in UI as "Audited". */
  verified_claims: number
  supported_count: number
  partially_supported_count: number
  contradicted_count: number
  flagged_count: number
  abstained_count: number
  cost_anomaly_count: number
  /** Ratio of cost anomalies to audited claims: cost_anomaly_count / verified_claims */
  cost_anomaly_rate: number
  /** Ratio of clinical support among conclusive audits: (supported + 0.5 * partially_supported) / conclusive audits. Evaluates to 0.0 when 0 conclusive audits exist. */
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

// ---- Layer 6: Evaluation Harness Types ----

export interface MetricResult {
  precision: number
  recall: number
  f1_score: number
  accuracy?: number | null
  support_count: number
  predicted_count: number
  true_positives: number
  false_positives: number
  false_negatives: number
}

export interface CalibrationBin {
  bin_index: number
  bin_lower: number
  bin_upper: number
  sample_count: number
  avg_confidence: number
  empirical_accuracy: number
  calibration_error: number
}

export interface AbstentionMetrics {
  total_samples: number
  total_abstained: number
  abstention_rate: number
  correct_abstentions: number
  over_abstentions: number
  under_abstentions: number
  abstention_precision: number
  abstention_recall: number
  abstention_f1: number
}

export interface SampleEvaluationDetail {
  case_id: string
  predicted_verdict: string
  gold_verdict: string
  verdict_correct: boolean
  predicted_action: string
  gold_action: string
  action_correct: boolean
  predicted_cost_anomaly: boolean
  gold_cost_anomaly: boolean
  cost_anomaly_correct: boolean
  support_score: number
  rule_triggered?: string | null
  claim_id?: string | null
  explanation?: string | null
}

export interface EvaluationReport {
  run_id: string
  timestamp: string
  dataset_name: string
  total_samples: number
  overall_verdict_accuracy: number
  macro_verdict_f1: number
  verdict_metrics: Record<string, MetricResult>
  overall_action_accuracy: number
  macro_action_f1: number
  action_metrics: Record<string, MetricResult>
  cost_anomaly_metrics: MetricResult
  abstention_metrics: AbstentionMetrics
  calibration_bins: CalibrationBin[]
  expected_calibration_error: number
  markdown_report: string
  recommendations: string[]
  sample_evaluations: SampleEvaluationDetail[]
}

export interface EvaluationRunResponse {
  success: boolean
  run_id: string
  report: EvaluationReport
  message: string
}

export interface EvaluationListResponse {
  total: number
  count: number
  runs: EvaluationReport[]
}

// ---------------------------------------------------------------------------
// Community Stories (Recovery Stories)
// ---------------------------------------------------------------------------

export interface CommunityStory {
  story_id: string
  title?: string | null
  story_text: string
  author_name: string
  condition_or_topic?: string | null
  location?: string | null
  category?: string | null
  contact_email?: string | null
  contact_instagram?: string | null
  consent_acknowledged: boolean
  created_at: string
  is_demo?: boolean
}

export interface CommunityStoryCreate {
  title?: string
  story_text: string
  author_name?: string
  condition_or_topic?: string
  location?: string
  category?: string
  contact_email?: string
  contact_instagram?: string
  consent_acknowledged: boolean
}

export interface CommunityStoryListResponse {
  total: number
  count: number
  stories: CommunityStory[]
}

// ---------------------------------------------------------------------------
// Visual Insights & Dashboard Statistics
// ---------------------------------------------------------------------------

export interface DecisionOverview {
  approved: number
  flagged: number
  held: number
  total: number
}

export interface PriceAlertsOverview {
  normal_charges: number
  price_alerts: number
  moderate: number
  severe: number
  extreme: number
  total: number
}

export interface GuidelineSupportOverview {
  supported: number
  partially_supported: number
  contradicted: number
  insufficient_evidence: number
  total: number
}

export interface GapsAndRisks {
  insufficient_evidence_claims: number
  extreme_price_markups: number
  held_by_safety_rules: number
  unbenchmarked_high_cost: number
}

export interface ProcedureFrequency {
  procedure_name: string
  count: number
}

export interface LocationFrequency {
  location_name: string
  claims_count: number
  anomalies_count: number
}

export interface ClaimHighlight {
  claim_id: string
  entity: string
  action: string
  verdict?: string | null
  cost_range?: string | null
  cost_currency?: string | null
  reason?: string | null
  timestamp?: string | null
}

export interface InsightsSummaryResponse {
  total_claims: number
  total_verified: number
  decision_overview: DecisionOverview
  price_alerts_overview: PriceAlertsOverview
  guideline_support_overview: GuidelineSupportOverview
  gaps_and_risks: GapsAndRisks
  top_procedures: ProcedureFrequency[]
  top_locations: LocationFrequency[]
  recent_risk_claims: ClaimHighlight[]
  is_baseline_fallback: boolean
}

// ---- Authentication & User Profiles (Part 2) ----

export interface UserResponse {
  user_id: string
  name: string
  email: string
  role: string
  organization?: string
  created_at: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: UserResponse
}

export interface UserCreateRequest {
  name: string
  email: string
  password: string
  organization?: string
}

export interface UserLoginRequest {
  email: string
  password: string
}


