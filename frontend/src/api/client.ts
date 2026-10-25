// ============================================================
// EvidenceBridge API client — typed fetch wrappers
// All calls go to /api/v1 (proxied by Vite to :8000)
// ============================================================

import {
  ApiError,
  AuditResponse,
  AuthResponse,
  Claim,
  ClaimListResponse,
  CommunityStory,
  CommunityStoryCreate,
  CommunityStoryListResponse,
  ExtractionRequest,
  ExtractionResponse,
  ExtractAndVerifyResponse,
  HealthResponse,
  InsightsSummaryResponse,
  TrustDensityListResponse,
  TrustDensityResponse,
  UserCreateRequest,
  UserLoginRequest,
  UserResponse,
  VerificationResponse,
  VerificationResult,
} from '../types'


export const API_BASE = (import.meta.env.VITE_API_BASE_URL || '/api/v1').replace(/\/+$/, '')

export const TOKEN_STORAGE_KEY = 'evidencebridge_token'
export const USER_STORAGE_KEY = 'evidencebridge_user'

// In-memory token cache for synchronous, zero-race-condition access
let memoryAuthToken: string | null = null
let autoDemoPromise: Promise<string | null> | null = null

// Initialize memory token synchronously on script load
try {
  if (typeof window !== 'undefined') {
    memoryAuthToken =
      localStorage.getItem(TOKEN_STORAGE_KEY) ||
      sessionStorage.getItem(TOKEN_STORAGE_KEY) ||
      null
  }
} catch {
  // Storage access might be restricted in some iframe / sandboxed environments
}

export function getAuthToken(): string | null {
  if (memoryAuthToken && memoryAuthToken.trim()) {
    return memoryAuthToken.trim()
  }
  if (typeof window !== 'undefined') {
    try {
      const local = localStorage.getItem(TOKEN_STORAGE_KEY)
      if (local && local.trim()) {
        memoryAuthToken = local.trim()
        return memoryAuthToken
      }
      const session = sessionStorage.getItem(TOKEN_STORAGE_KEY)
      if (session && session.trim()) {
        memoryAuthToken = session.trim()
        return memoryAuthToken
      }
    } catch {
      // Storage access might be restricted
    }
  }
  return null
}

export function setAuthToken(token: string | null): void {
  memoryAuthToken = token && token.trim() ? token.trim() : null
  if (typeof window !== 'undefined') {
    try {
      if (memoryAuthToken) {
        localStorage.setItem(TOKEN_STORAGE_KEY, memoryAuthToken)
        sessionStorage.setItem(TOKEN_STORAGE_KEY, memoryAuthToken)
      } else {
        localStorage.removeItem(TOKEN_STORAGE_KEY)
        sessionStorage.removeItem(TOKEN_STORAGE_KEY)
      }
    } catch {
      // Storage access might be restricted
    }
  }
}

/**
 * Ensures a valid session token exists before issuing protected requests.
 * If user is unauthenticated, acquires a canonical Demo Auditor session
 * to prevent 401 Unauthorized errors on first load.
 */
export async function ensureAuthToken(): Promise<string | null> {
  const existing = getAuthToken()
  if (existing) {
    return existing
  }

  if (autoDemoPromise) {
    return autoDemoPromise
  }

  autoDemoPromise = (async () => {
    try {
      const res = await fetch(`${API_BASE}/auth/demo`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      })
      if (res.ok) {
        const data = await res.json()
        if (data?.access_token) {
          setAuthToken(data.access_token)
          if (typeof window !== 'undefined' && data.user) {
            try {
              const u = {
                id: data.user.user_id,
                name: data.user.name,
                email: data.user.email,
                role: data.user.role,
                organization: data.user.organization,
              }
              localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(u))
              sessionStorage.setItem(USER_STORAGE_KEY, JSON.stringify(u))
            } catch {
              // ignore
            }
          }
          return data.access_token
        }
      }
    } catch (err) {
      console.warn('Auto demo authentication failed:', err)
    } finally {
      autoDemoPromise = null
    }

    // Ultimate offline fallback token recognizable by backend
    setAuthToken('demo_bearer_token')
    return 'demo_bearer_token'
  })()

  return autoDemoPromise
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  // Public endpoints do not require an Authorization header
  const isPublic =
    path.startsWith('/health') ||
    path.startsWith('/auth/login') ||
    path.startsWith('/auth/signup') ||
    path.startsWith('/auth/demo')

  let token = getAuthToken()
  if (!token && !isPublic) {
    token = await ensureAuthToken()
  }

  const authHeaders: Record<string, string> = {}
  if (token) {
    authHeaders['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders,
      ...(init?.headers ?? {}),
    },
    ...init,
  })
  if (!res.ok) {
    let msg = `HTTP ${res.status}`
    try {
      const body = await res.json()
      msg = body?.detail ?? body?.message ?? msg
      if (typeof msg === 'object') msg = JSON.stringify(msg)
    } catch {
      // leave msg as-is
    }
    throw new ApiError(String(msg), res.status)
  }
  return res.json() as Promise<T>
}

// ---- Health ----

export function getHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>('/health')
}

// ---- Extraction ----

export function extractOnly(req: ExtractionRequest): Promise<ExtractionResponse> {
  return apiFetch<ExtractionResponse>('/extract', {
    method: 'POST',
    body: JSON.stringify({ store_claim: true, ...req }),
  })
}

export function extractAndVerify(
  req: ExtractionRequest,
): Promise<ExtractAndVerifyResponse> {
  return apiFetch<ExtractAndVerifyResponse>('/extract-and-verify', {
    method: 'POST',
    body: JSON.stringify({ store_claim: true, ...req }),
  })
}

// ---- Claims ----

export function listClaims(params?: {
  limit?: number
  skip?: number
  location?: string
  user_id?: string
}): Promise<ClaimListResponse> {
  const qs = new URLSearchParams()
  if (params?.limit !== undefined) qs.set('limit', String(params.limit))
  if (params?.skip !== undefined) qs.set('skip', String(params.skip))
  if (params?.location) qs.set('location', params.location)
  if (params?.user_id) qs.set('user_id', params.user_id)
  const q = qs.toString()
  return apiFetch<ClaimListResponse>(`/claims${q ? `?${q}` : ''}`)
}

export function getClaim(claimId: string): Promise<Claim> {
  return apiFetch<Claim>(`/claims/${encodeURIComponent(claimId)}`)
}

// ---- Verification ----

export function verifyClaim(claimId: string): Promise<VerificationResponse> {
  return apiFetch<VerificationResponse>(
    `/verify/${encodeURIComponent(claimId)}`,
    { method: 'POST' },
  )
}

export function getVerification(claimId: string): Promise<VerificationResult> {
  return apiFetch<VerificationResult>(
    `/verification/${encodeURIComponent(claimId)}`,
  )
}

// ---- Audit ----

export function getAudit(claimId: string): Promise<AuditResponse> {
  return apiFetch<AuditResponse>(`/audit/${encodeURIComponent(claimId)}`)
}

// ---- Trust Density ----

export function listTrustDensity(params?: {
  limit?: number
  skip?: number
  sort_by?: string
}): Promise<TrustDensityListResponse> {
  const qs = new URLSearchParams()
  if (params?.limit !== undefined) qs.set('limit', String(params.limit))
  if (params?.skip !== undefined) qs.set('skip', String(params.skip))
  if (params?.sort_by) qs.set('sort_by', params.sort_by)
  const q = qs.toString()
  return apiFetch<TrustDensityListResponse>(`/trust-density${q ? `?${q}` : ''}`)
}

export function getTrustDensity(locationKey: string): Promise<TrustDensityResponse> {
  return apiFetch<TrustDensityResponse>(
    `/trust-density/${encodeURIComponent(locationKey)}`,
  )
}

export function recomputeTrustDensity(
  locationKey: string,
): Promise<TrustDensityResponse> {
  return apiFetch<TrustDensityResponse>(
    `/trust-density/${encodeURIComponent(locationKey)}/recompute`,
    { method: 'POST' },
  )
}

// ---- Layer 6: Evaluation Harness ----

import type {
  EvaluationReport,
  EvaluationRunResponse,
  EvaluationListResponse,
} from '../types'

export function runEvaluation(options?: {
  dataset_path?: string
  force_reverify?: boolean
  offline_mode?: boolean
}): Promise<EvaluationRunResponse> {
  return apiFetch<EvaluationRunResponse>('/evaluate', {
    method: 'POST',
    body: JSON.stringify(options ?? { offline_mode: true }),
  })
}

export function getEvaluationReport(runId: string): Promise<EvaluationReport> {
  return apiFetch<EvaluationReport>(`/evaluate/${encodeURIComponent(runId)}`)
}

export function listEvaluationRuns(
  limit = 20,
  skip = 0,
): Promise<EvaluationListResponse> {
  return apiFetch<EvaluationListResponse>(`/evaluate?limit=${limit}&skip=${skip}`)
}

export function listStories(
  limit = 50,
  skip = 0,
  userId?: string,
): Promise<CommunityStoryListResponse> {
  const qs = new URLSearchParams({ limit: String(limit), skip: String(skip) })
  if (userId) qs.set('user_id', userId)
  return apiFetch<CommunityStoryListResponse>(`/stories?${qs.toString()}`)
}

export function createStory(
  story: CommunityStoryCreate,
): Promise<CommunityStory> {
  return apiFetch<CommunityStory>('/stories', {
    method: 'POST',
    body: JSON.stringify(story),
  })
}

export function getInsightsSummary(
  paramsOrUserId?: string | { userId?: string; benchmark?: boolean; allowFallback?: boolean },
): Promise<InsightsSummaryResponse> {
  let userId: string | undefined
  let benchmark: boolean | undefined
  let allowFallback: boolean | undefined

  if (typeof paramsOrUserId === 'string') {
    userId = paramsOrUserId
  } else if (paramsOrUserId) {
    userId = paramsOrUserId.userId
    benchmark = paramsOrUserId.benchmark
    allowFallback = paramsOrUserId.allowFallback
  }

  const qs = new URLSearchParams()
  if (userId) qs.set('user_id', userId)
  if (benchmark !== undefined) qs.set('benchmark', String(benchmark))
  if (allowFallback !== undefined) qs.set('allow_fallback', String(allowFallback))
  const q = qs.toString()
  return apiFetch<InsightsSummaryResponse>(`/insights/summary${q ? `?${q}` : ''}`)
}

// ---- Authentication & User Accounts (Part 2) ----

export function loginApi(req: UserLoginRequest): Promise<AuthResponse> {
  return apiFetch<AuthResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify(req),
  })
}

export function signupApi(req: UserCreateRequest): Promise<AuthResponse> {
  return apiFetch<AuthResponse>('/auth/signup', {
    method: 'POST',
    body: JSON.stringify(req),
  })
}

export function demoAuthApi(): Promise<AuthResponse> {
  return apiFetch<AuthResponse>('/auth/demo', {
    method: 'POST',
  })
}

export function getMeApi(): Promise<UserResponse> {
  return apiFetch<UserResponse>('/auth/me')
}


