import { useState, useEffect, useCallback, useMemo } from 'react'
import { Link } from 'react-router-dom'
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'
import { getInsightsSummary, listClaims, ensureAuthToken } from '../api/client'
import { useAudit } from '../context/AuditContext'
import type { InsightsSummaryResponse, Claim } from '../types'
import { formatCurrency } from '../utils/currency'

// Clinical Healthcare Color Palette
const COLORS = {
  emerald: '#059669',     // Approved / Supported / Fair
  emeraldLight: '#10b981',
  amber: '#d97706',       // Flagged / Moderate Markup
  amberLight: '#f59e0b',
  slate: '#64748b',       // Held / Insufficient Evidence
  slateLight: '#94a3b8',
  rose: '#e11d48',        // Contradicted / Extreme Markup
  orange: '#ea580c',      // Severe Markup
  sky: '#0284c7',         // Benchmarked / Normal Tariff
  teal: '#0d9488',        // Health Telemetry
}

export default function Insights() {
  const [data, setData] = useState<InsightsSummaryResponse | null>(null)
  const [recentClaims, setRecentClaims] = useState<Claim[]>([])
  const [loading, setLoading] = useState(true)
  const [isSyncing, setIsSyncing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'all' | 'pricing' | 'guidelines' | 'locations'>('all')
  const [viewMode, setViewMode] = useState<'my_audits' | 'benchmark'>('my_audits')

  const auditContext = useAudit()
  const sessionAudit = auditContext.result

  const fetchData = useCallback(async (mode: 'my_audits' | 'benchmark' = viewMode, showLoading = true) => {
    if (showLoading) setLoading(true)
    setIsSyncing(true)
    setError(null)
    try {
      await ensureAuthToken()

      // Fetch insights summary according to selected view mode
      // 'my_audits' requests allowFallback=false so empty user sessions are accurately reported
      // 'benchmark' explicitly requests baseline benchmark data
      const isBenchmark = mode === 'benchmark'
      const summaryPromise = getInsightsSummary({
        benchmark: isBenchmark,
        allowFallback: !isBenchmark,
      })

      // Also fetch recent claims to display spotlight for single or zero flagged cases
      const claimsPromise = listClaims({ limit: 6 }).catch(() => ({ total: 0, count: 0, claims: [] }))

      const [summary, claimsRes] = await Promise.all([summaryPromise, claimsPromise])
      setData(summary)
      setRecentClaims(claimsRes.claims || [])
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load visual insights.')
    } finally {
      setLoading(false)
      setIsSyncing(false)
    }
  }, [viewMode])

  useEffect(() => {
    fetchData(viewMode, true)
  }, [viewMode, fetchData])

  // Derive active audited claim for the spotlight card
  const latestClaimSpotlight = useMemo(() => {
    // 1. Session audit from active memory
    if (sessionAudit?.claim && sessionAudit?.verification) {
      return {
        claimId: sessionAudit.claim.claim_id,
        entity: sessionAudit.claim.extracted_fields?.entity || 'Audited Medical Item',
        action: sessionAudit.verification.action,
        verdict: sessionAudit.verification.verdict,
        costRange: sessionAudit.claim.extracted_fields?.cost_range,
        costCurrency: sessionAudit.claim.extracted_fields?.cost_currency || 'INR',
        isAnomaly: Boolean(sessionAudit.verification.cost_anomaly_flag),
        multiplier: sessionAudit.verification.anomaly_details?.multiplier,
        benchmarkMax: sessionAudit.verification.anomaly_details?.benchmark_max,
        explanation: sessionAudit.verification.anomaly_details?.explanation || sessionAudit.verification.abstain_reason || sessionAudit.verification.reasoning,
        timestamp: sessionAudit.claim.timestamp,
      }
    }

    // 2. Recent claim from API
    if (recentClaims.length > 0) {
      const first = recentClaims[0]
      const riskMatch = data?.recent_risk_claims.find((r) => r.claim_id === first.claim_id)
      return {
        claimId: first.claim_id,
        entity: first.extracted_fields?.entity || 'Audited Medical Item',
        action: riskMatch ? riskMatch.action : 'accept',
        verdict: riskMatch?.verdict || 'supported',
        costRange: first.extracted_fields?.cost_range || riskMatch?.cost_range,
        costCurrency: first.extracted_fields?.cost_currency || 'INR',
        isAnomaly: Boolean(riskMatch),
        multiplier: null,
        benchmarkMax: null,
        explanation: riskMatch?.reason || 'Verified treatment conforms to clinical practice guidelines and fair regional tariffs.',
        timestamp: first.timestamp,
      }
    }

    // 3. Fallback to first recent risk claim if available
    if (data?.recent_risk_claims && data.recent_risk_claims.length > 0) {
      const first = data.recent_risk_claims[0]
      return {
        claimId: first.claim_id,
        entity: first.entity,
        action: first.action,
        verdict: first.verdict || 'supported',
        costRange: first.cost_range,
        costCurrency: first.cost_currency || 'INR',
        isAnomaly: first.action === 'flag',
        multiplier: null,
        benchmarkMax: null,
        explanation: first.reason || 'Telemetry audit finding recorded.',
        timestamp: first.timestamp,
      }
    }

    return null
  }, [sessionAudit, recentClaims, data])

  if (loading && !data) {
    return (
      <div className="max-w-6xl mx-auto space-y-8 animate-pulse font-sans w-full py-4">
        <div className="bg-slate-900 rounded-3xl p-8 border border-slate-800 space-y-4 shadow-xl">
          <div className="h-6 bg-slate-800 rounded-full w-1/4" />
          <div className="h-8 bg-slate-800 rounded-xl w-2/3" />
          <div className="h-4 bg-slate-800 rounded-lg w-1/2" />
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-32 bg-white rounded-2xl border border-slate-200 shadow-xs" />
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="h-80 bg-white rounded-2xl border border-slate-200 shadow-xs" />
          <div className="h-80 bg-white rounded-2xl border border-slate-200 shadow-xs" />
        </div>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="max-w-xl mx-auto py-16 text-center font-sans">
        <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-rose-50 border border-rose-200 flex items-center justify-center text-3xl shadow-xs">
          📊
        </div>
        <h2 className="text-xl font-black text-slate-900 mb-1">Failed to Load Clinical Insights</h2>
        <p className="text-xs text-slate-500 mb-6">{error || 'Unable to retrieve audit telemetry statistics.'}</p>
        <button
          type="button"
          onClick={() => fetchData(viewMode, true)}
          className="px-5 py-2.5 bg-sky-600 text-white rounded-xl text-xs font-bold hover:bg-sky-700 transition-colors shadow-xs"
        >
          Retry Connection
        </button>
      </div>
    )
  }

  const totalVerified = data.total_verified || 0
  const isZeroData = totalVerified === 0
  const isSingleOrLowData = totalVerified > 0 && totalVerified <= 2

  // Chart Data Preparation
  const decisionData = [
    { name: 'Supported & Approved', value: data.decision_overview.approved, color: COLORS.emerald },
    { name: 'Flagged for Review', value: data.decision_overview.flagged, color: COLORS.amber },
    { name: 'Held (Need Evidence)', value: data.decision_overview.held, color: COLORS.slate },
  ].filter((d) => d.value > 0)

  const priceAlertsData = [
    { name: 'Normal Fair Rate', value: data.price_alerts_overview.normal_charges, color: COLORS.sky },
    { name: 'Moderate (3x–5x)', value: data.price_alerts_overview.moderate, color: COLORS.amber },
    { name: 'Severe (5x–10x)', value: data.price_alerts_overview.severe, color: COLORS.orange },
    { name: 'Extreme (≥10x)', value: data.price_alerts_overview.extreme, color: COLORS.rose },
  ]

  const guidelineData = [
    { name: 'Supported', count: data.guideline_support_overview.supported, fill: COLORS.emerald },
    { name: 'Partially Supported', count: data.guideline_support_overview.partially_supported, fill: COLORS.sky },
    { name: 'Contradicted', count: data.guideline_support_overview.contradicted, fill: COLORS.rose },
    { name: 'Insufficient Info', count: data.guideline_support_overview.insufficient_evidence, fill: COLORS.slate },
  ]

  const approvalRate = totalVerified > 0 ? Math.round((data.decision_overview.approved / totalVerified) * 100) : 0
  const anomalyRate = totalVerified > 0 ? Math.round((data.price_alerts_overview.price_alerts / totalVerified) * 100) : 0
  const heldRate = totalVerified > 0 ? Math.round((data.decision_overview.held / totalVerified) * 100) : 0

  return (
    <div className="max-w-6xl mx-auto space-y-6 sm:space-y-8 font-sans w-full pb-12">
      {/* ============================================================ */}
      {/* 1. HEALTHCARE INTELLIGENCE HEADER BANNER                      */}
      {/* ============================================================ */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-slate-900 via-sky-950 to-slate-900 border border-sky-900/60 p-6 sm:p-8 text-white shadow-xl">
        {/* Subtle decorative mesh glows */}
        <div className="absolute top-0 right-0 -mt-12 -mr-12 w-80 h-80 rounded-full bg-teal-500/10 blur-3xl pointer-events-none" />
        <div className="absolute bottom-0 left-1/3 -mb-16 w-60 h-60 rounded-full bg-sky-500/10 blur-2xl pointer-events-none" />

        <div className="relative z-10 flex flex-col md:flex-row justify-between md:items-center gap-6">
          <div className="space-y-2 max-w-2xl">
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-teal-500/20 text-teal-300 text-[11px] font-bold tracking-wide border border-teal-500/30 uppercase">
                <span className={`w-2 h-2 rounded-full ${isSyncing ? 'bg-teal-300 animate-ping' : 'bg-teal-400 animate-pulse'}`} />
                {isSyncing ? 'Refreshing Telemetry...' : 'Live Clinical Telemetry'}
              </span>
              <span className="px-2.5 py-0.5 rounded-full bg-sky-500/20 text-sky-300 text-[11px] font-medium border border-sky-500/30">
                Lead Reviewer: <strong>Vasavi</strong> (Clinical Claims)
              </span>
              <span className="px-2.5 py-0.5 rounded-full bg-slate-800/80 text-slate-300 text-[11px] font-medium border border-slate-700">
                Currency: <strong>₹ INR</strong>
              </span>
            </div>

            <h1 className="text-2xl sm:text-3xl lg:text-4xl font-black tracking-tight text-white">
              Clinical Audit &amp; Pricing Telemetry
            </h1>
            <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
              Transparent health economic analytics cross-referencing medical treatments, ICMR/CDC guidelines,
              and published regional outpatient tariff benchmarks in plain English.
            </p>
          </div>

          {/* Action Buttons & View Mode Toggle */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5 self-start md:self-auto flex-wrap">
            {/* View Mode Toggle Pill */}
            <div className="inline-flex items-center p-1 rounded-2xl bg-slate-800/90 border border-slate-700/80 shadow-inner">
              <button
                type="button"
                onClick={() => setViewMode('my_audits')}
                className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all ${
                  viewMode === 'my_audits'
                    ? 'bg-sky-500 text-slate-950 shadow-sm'
                    : 'text-slate-300 hover:text-white'
                }`}
                title="View your personal audited claims"
              >
                My Audits {totalVerified > 0 && viewMode === 'my_audits' ? `(${totalVerified})` : ''}
              </button>
              <button
                type="button"
                onClick={() => setViewMode('benchmark')}
                className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all ${
                  viewMode === 'benchmark'
                    ? 'bg-teal-400 text-slate-950 shadow-sm'
                    : 'text-slate-300 hover:text-white'
                }`}
                title="View standard 8-case benchmark telemetry"
              >
                Benchmark (8 Cases)
              </button>
            </div>

            <button
              type="button"
              onClick={() => fetchData(viewMode, false)}
              disabled={isSyncing}
              className="inline-flex items-center justify-center gap-1.5 px-3.5 py-2 rounded-xl border border-sky-400/30 bg-sky-900/30 hover:bg-sky-800/40 text-xs font-bold text-sky-200 transition-colors backdrop-blur-xs disabled:opacity-50"
            >
              <span className={isSyncing ? 'animate-spin' : ''}>🔄</span>
              <span>{isSyncing ? 'Syncing...' : 'Sync'}</span>
            </button>
            <Link
              to="/audit"
              className="inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-xl bg-gradient-to-r from-teal-400 to-sky-400 hover:from-teal-300 hover:to-sky-300 text-slate-950 text-xs font-black shadow-lg transition-all"
            >
              <span>+ Audit Document</span>
            </Link>
          </div>
        </div>

        {/* View Mode Context Banners */}
        {viewMode === 'benchmark' && (
          <div className="relative z-10 mt-6 p-3.5 rounded-2xl bg-teal-500/15 border border-teal-500/30 text-teal-100 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3 backdrop-blur-xs">
            <div className="flex items-center gap-2.5">
              <span className="text-base text-teal-300 flex-shrink-0">🏥</span>
              <span>
                <strong className="text-white">National Clinical Benchmark Dataset:</strong> Displaying audited telemetry across 8 standard hospital and outpatient reference cases (Bengaluru, Ballari, Mysuru).
              </span>
            </div>
            <button
              type="button"
              onClick={() => setViewMode('my_audits')}
              className="font-bold text-teal-300 hover:text-white underline whitespace-nowrap text-xs self-start sm:self-auto"
            >
              Switch back to My Audits &rarr;
            </button>
          </div>
        )}

        {viewMode === 'my_audits' && data.is_baseline_fallback && (
          <div className="relative z-10 mt-6 p-3.5 rounded-2xl bg-white/10 border border-white/15 text-slate-200 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3 backdrop-blur-xs">
            <div className="flex items-center gap-2.5">
              <span className="text-base text-teal-400 flex-shrink-0">💡</span>
              <span>
                <strong className="text-white">Gold-Standard Reference Baseline:</strong> No personal claims saved yet. Displaying calibrated reference telemetry. Run an audit to see your live personal cases!
              </span>
            </div>
            <Link
              to="/audit"
              className="font-bold text-teal-300 hover:text-white underline whitespace-nowrap text-xs self-start sm:self-auto"
            >
              Upload hospital bill &rarr;
            </Link>
          </div>
        )}
      </div>

      {/* ============================================================ */}
      {/* 2. BETTER EMPTY STATE (WHEN ZERO CLAIMS AUDITED)             */}
      {/* ============================================================ */}
      {isZeroData && (
        <div className="bg-gradient-to-br from-white via-sky-50/40 to-slate-50 border border-sky-200 rounded-3xl p-6 sm:p-8 shadow-sm space-y-6">
          <div className="flex flex-col md:flex-row items-center md:items-start gap-6 text-center md:text-left">
            <div className="w-16 h-16 rounded-2xl bg-sky-100 border border-sky-300 flex items-center justify-center text-3xl shadow-xs flex-shrink-0">
              📋
            </div>
            <div className="space-y-2 flex-1">
              <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-sky-100 text-sky-800 text-[11px] font-bold">
                <span>🌱 Ready for Your First Medical Audit</span>
              </div>
              <h2 className="text-xl sm:text-2xl font-black text-slate-900">
                No Audits Yet — Run Your First Claim to See Insights Here
              </h2>
              <p className="text-xs sm:text-sm text-slate-600 max-w-2xl leading-relaxed">
                Take a photo or upload a hospital bill, outpatient prescription, or discharge summary on the Audit page.
                EvidenceBridge will automatically extract line items, calculate fair-market tariffs in Indian Rupees (₹),
                and verify treatments against authoritative ICMR &amp; WHO clinical practice guidelines.
              </p>
            </div>

            <div className="flex flex-col sm:flex-row md:flex-col gap-2.5 flex-shrink-0 w-full md:w-auto">
              <Link
                to="/audit"
                className="inline-flex items-center justify-center gap-2 px-5 py-3 rounded-xl bg-gradient-to-r from-sky-600 to-teal-600 hover:from-sky-700 hover:to-teal-700 text-white font-bold text-xs shadow-md transition-all"
              >
                <span>+ Audit Your First Document</span>
                <span>&rarr;</span>
              </Link>
              <button
                type="button"
                onClick={() => setViewMode('benchmark')}
                className="inline-flex items-center justify-center gap-1.5 px-4 py-2.5 rounded-xl border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 font-bold text-xs transition-colors"
              >
                <span>Preview Benchmark Telemetry (8 Cases)</span>
              </button>
            </div>
          </div>

          {/* Educational 4-Dimension Overview Cards */}
          <div className="border-t border-slate-200/80 pt-6">
            <h3 className="text-xs font-black uppercase tracking-wider text-slate-500 mb-3">
              What EvidenceBridge Analyzes on Every Hospital Bill &amp; Prescription
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
              <div className="p-4 rounded-2xl bg-white border border-slate-200 text-xs space-y-1.5 shadow-2xs">
                <div className="text-base text-emerald-600">✓</div>
                <div className="font-bold text-slate-900">ICMR Guideline Conformance</div>
                <p className="text-[11px] text-slate-500 leading-relaxed">
                  Checks medical indications for treatments like Metformin, Azithromycin, or MRI scans against clinical standards.
                </p>
              </div>

              <div className="p-4 rounded-2xl bg-white border border-slate-200 text-xs space-y-1.5 shadow-2xs">
                <div className="text-base text-amber-600">⚠️</div>
                <div className="font-bold text-slate-900">Fair-Market Tariff Benchmarks</div>
                <p className="text-[11px] text-slate-500 leading-relaxed">
                  Flags excessive hospital markups (such as ₹1,800 IV saline vs standard ₹60 ceiling tariff in Karnataka).
                </p>
              </div>

              <div className="p-4 rounded-2xl bg-white border border-slate-200 text-xs space-y-1.5 shadow-2xs">
                <div className="text-base text-slate-600">⏸</div>
                <div className="font-bold text-slate-900">Safe Refusal Hold Gates</div>
                <p className="text-[11px] text-slate-500 leading-relaxed">
                  Responsible AI safety: Refuses to guess when clinical guidelines are absent, preventing false approvals.
                </p>
              </div>

              <div className="p-4 rounded-2xl bg-white border border-slate-200 text-xs space-y-1.5 shadow-2xs">
                <div className="text-base text-sky-600">📍</div>
                <div className="font-bold text-slate-900">Regional Healthcare Corridors</div>
                <p className="text-[11px] text-slate-500 leading-relaxed">
                  Calibrated for Indian healthcare corridors including Bengaluru, Ballari, Mysuru, Davangere, and Hubli.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ============================================================ */}
      {/* 3. LOW DATA / SINGLE CLAIM BANNER & SPOTLIGHT CARD           */}
      {/* ============================================================ */}
      {isSingleOrLowData && (
        <div className="p-4 rounded-2xl bg-amber-50/80 border border-amber-200 text-amber-900 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-2xs">
          <div className="flex items-center gap-2.5">
            <span className="text-base text-amber-600 flex-shrink-0">📊</span>
            <div>
              <strong>Emerging Telemetry ({totalVerified} {totalVerified === 1 ? 'Claim' : 'Claims'} Audited):</strong> Not enough data to draw broad statistical conclusions yet. Displaying your active verified record below.
            </div>
          </div>
          <button
            type="button"
            onClick={() => setViewMode('benchmark')}
            className="font-bold text-amber-800 hover:text-amber-950 underline whitespace-nowrap text-xs self-start sm:self-auto"
          >
            Compare with 8-Case Benchmark &rarr;
          </button>
        </div>
      )}

      {/* Featured Single Claim Spotlight Card (Shows available data nicely) */}
      {latestClaimSpotlight && (
        <div className="bg-white rounded-3xl border border-slate-200 p-6 sm:p-7 shadow-card space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-4">
            <div className="flex items-center gap-2.5">
              <span className="w-8 h-8 rounded-xl bg-teal-50 text-teal-700 flex items-center justify-center font-bold text-base border border-teal-200">
                🔍
              </span>
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                  {totalVerified <= 2 ? 'Latest Verified Claim Spotlight' : 'Featured Audited Record'}
                </span>
                <h2 className="text-base font-black text-slate-900 flex items-center gap-2">
                  <span>{latestClaimSpotlight.entity}</span>
                </h2>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <span
                className={`px-3 py-1 rounded-full text-xs font-black uppercase tracking-wide border ${
                  latestClaimSpotlight.action === 'flag'
                    ? 'bg-amber-50 text-amber-900 border-amber-200'
                    : latestClaimSpotlight.action === 'accept'
                    ? 'bg-emerald-50 text-emerald-900 border-emerald-200'
                    : 'bg-slate-100 text-slate-800 border-slate-300'
                }`}
              >
                {latestClaimSpotlight.action === 'flag'
                  ? '⚠️ Flagged for Review'
                  : latestClaimSpotlight.action === 'accept'
                  ? '✓ Medically Approved'
                  : '⏸ Held for Evidence'}
              </span>

              {latestClaimSpotlight.costRange && (
                <span className="px-3 py-1 rounded-full bg-slate-900 text-white font-mono font-bold text-xs shadow-xs">
                  {latestClaimSpotlight.costRange}
                </span>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
            <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 space-y-1">
              <span className="text-slate-500 font-bold text-[11px] block">Billed Charge vs Tariff</span>
              <div className="font-black text-slate-900 text-sm font-mono">
                {latestClaimSpotlight.costRange || 'Tariff not stated'}
              </div>
              <p className="text-[11px] text-slate-600">
                {latestClaimSpotlight.isAnomaly
                  ? `Markup detected over expected benchmark rate.`
                  : 'Charge aligned within fair regional reference tariffs.'}
              </p>
            </div>

            <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 space-y-1">
              <span className="text-slate-500 font-bold text-[11px] block">Clinical Guideline Verdict</span>
              <div className="font-black text-slate-900 text-sm capitalize">
                {latestClaimSpotlight.verdict.replace('_', ' ')}
              </div>
              <p className="text-[11px] text-slate-600">
                Cross-referenced with ICMR &amp; WHO clinical treatment indications.
              </p>
            </div>

            <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 space-y-1">
              <span className="text-slate-500 font-bold text-[11px] block">Reviewer Recommendation</span>
              <div className="font-black text-slate-900 text-sm">
                {latestClaimSpotlight.action === 'flag'
                  ? 'Dispute Line Item'
                  : latestClaimSpotlight.action === 'accept'
                  ? 'Approve for Payment'
                  : 'Request More Evidence'}
              </div>
              <p className="text-[11px] text-slate-600 line-clamp-2">
                {latestClaimSpotlight.explanation}
              </p>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row sm:items-center justify-between pt-2 gap-2 text-xs">
            <span className="text-slate-400 font-mono text-[11px]">
              Claim ID: <strong className="text-slate-600">{latestClaimSpotlight.claimId}</strong>
            </span>
            <div className="flex items-center gap-3">
              <Link
                to={`/claims/${encodeURIComponent(latestClaimSpotlight.claimId)}`}
                className="font-bold text-sky-700 hover:text-sky-900 underline"
              >
                Inspect Decision Graph &rarr;
              </Link>
              <Link
                to="/audit"
                className="font-bold text-teal-700 hover:text-teal-900 underline"
              >
                Audit Another Document &rarr;
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* ============================================================ */}
      {/* 4. PRIMARY KEY METRIC TILES (HEALTHCARE STYLED)               */}
      {/* ============================================================ */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Tile 1: Total Audited Claims */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-card hover:shadow-md transition-shadow relative overflow-hidden">
          <div className="absolute top-0 left-0 right-0 h-1.5 bg-sky-500" />
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
              Audited Case Volume
            </span>
            <div className="w-7 h-7 rounded-lg bg-sky-50 text-sky-700 flex items-center justify-center text-sm font-bold">
              📑
            </div>
          </div>
          <div className="text-3xl font-black font-mono text-slate-900 mt-2">
            {totalVerified}
          </div>
          <p className="text-[11px] text-slate-500 mt-1.5 leading-snug">
            {isZeroData
              ? 'Awaiting your first document audit.'
              : totalVerified === 1
              ? '1 medical case verified in active session.'
              : `Processed through 7-stage evidence & tariff verification.`}
          </p>
        </div>

        {/* Tile 2: Supported & Fair */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-card hover:shadow-md transition-shadow relative overflow-hidden">
          <div className="absolute top-0 left-0 right-0 h-1.5 bg-emerald-500" />
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-emerald-800">
              Guideline-Supported &amp; Fair
            </span>
            <div className="w-7 h-7 rounded-lg bg-emerald-50 text-emerald-700 flex items-center justify-center text-sm font-bold">
              ✓
            </div>
          </div>
          <div className="text-3xl font-black font-mono text-emerald-600 mt-2">
            {data.decision_overview.approved}
            <span className="text-sm font-bold text-slate-400 ml-1.5 font-sans">
              ({approvalRate}%)
            </span>
          </div>
          <p className="text-[11px] text-slate-500 mt-1.5 leading-snug">
            {data.decision_overview.approved > 0
              ? 'Treatments backed by authoritative guidelines and fair tariffs.'
              : 'Approved claims with valid medical indications.'}
          </p>
        </div>

        {/* Tile 3: Flagged for Review */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-card hover:shadow-md transition-shadow relative overflow-hidden">
          <div className="absolute top-0 left-0 right-0 h-1.5 bg-amber-500" />
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-amber-800">
              Flagged for Review
            </span>
            <div className="w-7 h-7 rounded-lg bg-amber-50 text-amber-700 flex items-center justify-center text-sm font-bold">
              ⚠️
            </div>
          </div>
          <div className="text-3xl font-black font-mono text-amber-600 mt-2">
            {data.decision_overview.flagged}
            <span className="text-sm font-bold text-slate-400 ml-1.5 font-sans">
              ({totalVerified > 0 ? Math.round((data.decision_overview.flagged / totalVerified) * 100) : 0}%)
            </span>
          </div>
          <p className="text-[11px] text-slate-500 mt-1.5 leading-snug">
            {data.decision_overview.flagged > 0
              ? `Excessive billing markups or guideline deviations.`
              : '0 flags detected — all charges conformed to fair rate.'}
          </p>
        </div>

        {/* Tile 4: Held for Evidence */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-card hover:shadow-md transition-shadow relative overflow-hidden">
          <div className="absolute top-0 left-0 right-0 h-1.5 bg-slate-500" />
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-600">
              Safe Refusal Holds
            </span>
            <div className="w-7 h-7 rounded-lg bg-slate-100 text-slate-700 flex items-center justify-center text-sm font-bold">
              ⏸
            </div>
          </div>
          <div className="text-3xl font-black font-mono text-slate-700 mt-2">
            {data.decision_overview.held}
            <span className="text-sm font-bold text-slate-400 ml-1.5 font-sans">
              ({heldRate}%)
            </span>
          </div>
          <p className="text-[11px] text-slate-500 mt-1.5 leading-snug">
            Responsible safety gate: Never guesses when evidence is missing.
          </p>
        </div>
      </div>

      {/* ============================================================ */}
      {/* 5. INTERACTIVE TELEMETRY VIEW FILTER BAR                     */}
      {/* ============================================================ */}
      <div className="flex items-center justify-between gap-3 border-b border-slate-200 pb-2">
        <div className="flex items-center gap-1.5 overflow-x-auto">
          {[
            { id: 'all', label: 'All Telemetry Views' },
            { id: 'pricing', label: 'Pricing Markups & Tariffs' },
            { id: 'guidelines', label: 'Guideline Conformance' },
            { id: 'locations', label: 'Regional Hub Breakdown' },
          ].map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id as typeof activeTab)}
              className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all whitespace-nowrap ${
                activeTab === tab.id
                  ? 'bg-slate-900 text-white shadow-xs'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
        <span className="text-[11px] text-slate-400 font-medium hidden sm:inline">
          EvidenceBridge v2.6 Telemetry Engine &bull; ₹ INR Standard
        </span>
      </div>

      {/* ============================================================ */}
      {/* 6. VISUALIZATIONS GRID: DECISION DISTRIBUTION & TARIFFS      */}
      {/* ============================================================ */}
      {(activeTab === 'all' || activeTab === 'pricing') && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Chart 1: Decision Classification Breakdown */}
          <div className="bg-white p-5 sm:p-6 rounded-2xl border border-slate-200 shadow-card flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-1">
                <h2 className="text-sm font-black text-slate-900 uppercase tracking-wide flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
                  <span>1. Clinical Decision Distribution</span>
                </h2>
                <span className="text-[11px] font-mono px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 font-bold">
                  {totalVerified} {totalVerified === 1 ? 'Claim' : 'Claims'} Evaluated
                </span>
              </div>
              <p className="text-xs text-slate-500 mb-3 leading-relaxed">
                Breakdown of audited claims across guideline approval, auditor flags, and safe holds:
              </p>
            </div>

            <div className="h-64 w-full flex items-center justify-center">
              {decisionData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={decisionData}
                      cx="50%"
                      cy="50%"
                      innerRadius={55}
                      outerRadius={85}
                      paddingAngle={decisionData.length > 1 ? 5 : 0}
                      dataKey="value"
                    >
                      {decisionData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip
                      // eslint-disable-next-line @typescript-eslint/no-explicit-any
                      formatter={(val: any) => [`${val ?? 0} Claims`, 'Count']}
                      contentStyle={{
                        backgroundColor: '#0f172a',
                        color: '#fff',
                        borderRadius: '10px',
                        fontSize: '11px',
                        border: 'none',
                      }}
                    />
                    <Legend
                      verticalAlign="bottom"
                      height={36}
                      formatter={(value: string) => (
                        <span className="text-xs font-semibold text-slate-700">{value}</span>
                      )}
                    />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="text-center p-6 rounded-2xl bg-slate-50 border border-slate-200/80 w-full max-w-sm space-y-2">
                  <div className="text-2xl">📊</div>
                  <h4 className="text-xs font-bold text-slate-800">
                    No Audited Decisions Logged Yet
                  </h4>
                  <p className="text-[11px] text-slate-500 leading-relaxed">
                    Audits are classified into Approved (guideline-backed), Flagged (billing markup), or Held (insufficient evidence).
                  </p>
                  <Link
                    to="/audit"
                    className="inline-block mt-1 text-xs font-bold text-sky-600 hover:text-sky-800 underline"
                  >
                    Run first claim to view chart &rarr;
                  </Link>
                </div>
              )}
            </div>

            {/* Plain-Language Clinical Interpretation */}
            <div className="mt-3 p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-700 space-y-1.5">
              <div className="font-bold text-slate-900 flex items-center gap-1.5">
                <span>💡</span>
                <span>Clinical Interpretation:</span>
              </div>
              {isZeroData ? (
                <p className="text-[11px] text-slate-600 leading-relaxed">
                  • Telemetry activates immediately when you verify hospital bills or prescriptions.
                  <br />
                  • <strong>Evidence-driven auditing</strong> ensures medical charges reflect recognized therapeutic protocols.
                </p>
              ) : (
                <p className="text-[11px] text-slate-600 leading-relaxed">
                  • <strong>{data.decision_overview.approved} claims ({approvalRate}%)</strong> are verified with established clinical indications and compliant tariffs.
                  <br />
                  • <strong>{data.decision_overview.flagged} claims</strong> exhibit billing markups or guideline deviations requiring reviewer scrutiny.
                  <br />
                  • <strong>{data.decision_overview.held} claims</strong> triggered responsible safe holds due to missing evidence—preventing AI guessing.
                </p>
              )}
            </div>
          </div>

          {/* Chart 2: Price Comparison & Markup Severity */}
          <div className="bg-white p-5 sm:p-6 rounded-2xl border border-slate-200 shadow-card flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-1">
                <h2 className="text-sm font-black text-slate-900 uppercase tracking-wide flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
                  <span>2. Outpatient Tariff &amp; Markup Severity</span>
                </h2>
                <span className="text-[11px] font-mono px-2 py-0.5 rounded-md bg-amber-50 text-amber-800 font-bold border border-amber-200">
                  {data.price_alerts_overview.price_alerts} Markup Alerts
                </span>
              </div>
              <p className="text-xs text-slate-500 mb-3 leading-relaxed">
                Billed procedure charges compared against state health benchmarks and fair regional rates (₹ INR):
              </p>
            </div>

            <div className="h-64 w-full">
              {totalVerified > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={priceAlertsData} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
                    <XAxis
                      dataKey="name"
                      tick={{ fontSize: 10, fill: '#64748b' }}
                      interval={0}
                      angle={-10}
                      textAnchor="end"
                    />
                    <YAxis allowDecimals={false} tick={{ fontSize: 10, fill: '#64748b' }} />
                    <Tooltip
                      // eslint-disable-next-line @typescript-eslint/no-explicit-any
                      formatter={(val: any) => [`${val ?? 0} Claims`, 'Volume']}
                      contentStyle={{
                        backgroundColor: '#0f172a',
                        color: '#fff',
                        borderRadius: '10px',
                        fontSize: '11px',
                        border: 'none',
                      }}
                    />
                    <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                      {priceAlertsData.map((entry, index) => (
                        <Cell key={`bar-${index}`} fill={entry.color} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex items-center justify-center">
                  <div className="text-center p-6 rounded-2xl bg-slate-50 border border-slate-200/80 w-full max-w-sm space-y-2">
                    <div className="text-2xl">💰</div>
                    <h4 className="text-xs font-bold text-slate-800">
                      Pricing Anomaly Engine Ready
                    </h4>
                    <p className="text-[11px] text-slate-500 leading-relaxed">
                      Tracks fair rates, moderate (3x–5x), severe (5x–10x), and extreme (≥10x) markups against Karnataka &amp; national tariffs.
                    </p>
                  </div>
                </div>
              )}
            </div>

            {/* Plain-Language Financial Interpretation */}
            <div className="mt-3 p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-700 space-y-1.5">
              <div className="font-bold text-slate-900 flex items-center gap-1.5">
                <span>💡</span>
                <span>Financial Benchmark Takeaway:</span>
              </div>
              {data.price_alerts_overview.price_alerts === 0 && totalVerified > 0 ? (
                <p className="text-[11px] text-emerald-800 font-medium leading-relaxed">
                  ✓ <strong>0 pricing anomalies detected:</strong> All {totalVerified} audited {totalVerified === 1 ? 'charge' : 'charges'} conformed with standard fair regional reference rates.
                </p>
              ) : data.price_alerts_overview.price_alerts > 0 ? (
                <p className="text-[11px] text-slate-600 leading-relaxed">
                  • <strong>{data.price_alerts_overview.normal_charges} claims</strong> were billed within published public health benchmark ranges.
                  <br />
                  • <strong>{data.price_alerts_overview.extreme} claims</strong> were flagged with extreme markup (≥10x reference rate), such as ₹1,800 IV Saline vs ₹60 ceiling tariff.
                  <br />
                  • Auditors can dispute line-item charges directly using the generated evidence audit report.
                </p>
              ) : (
                <p className="text-[11px] text-slate-600 leading-relaxed">
                  • Compare hospital charges against CGHS and Karnataka state public health ceiling tariffs.
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ============================================================ */}
      {/* 7. GUIDELINE CONFORMANCE & FREQUENT PROCEDURES              */}
      {/* ============================================================ */}
      {(activeTab === 'all' || activeTab === 'guidelines') && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Guideline Agreement Bar Chart */}
          <div className="bg-white p-5 sm:p-6 rounded-2xl border border-slate-200 shadow-card flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-1">
                <h2 className="text-sm font-black text-slate-900 uppercase tracking-wide flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-teal-500" />
                  <span>3. Medical Evidence &amp; Guideline Conformance</span>
                </h2>
                <span className="text-[11px] font-mono text-slate-500 font-bold">ICMR / WHO / CDC</span>
              </div>
              <p className="text-xs text-slate-500 mb-3 leading-relaxed">
                Treatment decisions evaluated against clinical practice guidelines:
              </p>
            </div>

            <div className="h-60 w-full">
              {totalVerified > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={guidelineData} margin={{ top: 10, right: 10, left: -20, bottom: 15 }}>
                    <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#64748b' }} />
                    <YAxis allowDecimals={false} tick={{ fontSize: 10, fill: '#64748b' }} />
                    <Tooltip
                      // eslint-disable-next-line @typescript-eslint/no-explicit-any
                      formatter={(val: any) => [`${val ?? 0} Claims`, 'Verdicts']}
                      contentStyle={{
                        backgroundColor: '#0f172a',
                        color: '#fff',
                        borderRadius: '10px',
                        fontSize: '11px',
                        border: 'none',
                      }}
                    />
                    <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                      {guidelineData.map((entry, index) => (
                        <Cell key={`bar-${index}`} fill={entry.fill} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex items-center justify-center">
                  <div className="text-center p-6 rounded-2xl bg-slate-50 border border-slate-200/80 w-full max-w-sm space-y-2">
                    <div className="text-2xl">🩺</div>
                    <h4 className="text-xs font-bold text-slate-800">
                      Medical Guideline Index Ready
                    </h4>
                    <p className="text-[11px] text-slate-500 leading-relaxed">
                      Cross-references medications and diagnostics against ICMR, WHO, and CDC guidelines.
                    </p>
                  </div>
                </div>
              )}
            </div>

            <div className="mt-3 p-3 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-600 flex flex-wrap items-center gap-2">
              <span className="font-bold text-emerald-700">✓ Supported: {data.guideline_support_overview.supported}</span>
              <span>&bull;</span>
              <span className="font-bold text-sky-700">Partial: {data.guideline_support_overview.partially_supported}</span>
              <span>&bull;</span>
              <span className="font-bold text-rose-700">Contradicted: {data.guideline_support_overview.contradicted}</span>
              <span>&bull;</span>
              <span className="font-bold text-slate-600">Missing Evidence: {data.guideline_support_overview.insufficient_evidence}</span>
            </div>
          </div>

          {/* Top Audited Procedures */}
          <div className="bg-white p-5 sm:p-6 rounded-2xl border border-slate-200 shadow-card flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-1">
                <h2 className="text-sm font-black text-slate-900 uppercase tracking-wide flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-sky-500" />
                  <span>4. Most Frequently Audited Procedures &amp; Meds</span>
                </h2>
                <span className="text-[11px] font-mono text-slate-500 font-bold">Top Volume</span>
              </div>
              <p className="text-xs text-slate-500 mb-3 leading-relaxed">
                Medical procedures, medications, and clinical supplies audited most frequently:
              </p>
            </div>

            <div className="space-y-2.5">
              {data.top_procedures.length === 0 ? (
                <div className="p-6 rounded-2xl bg-slate-50 border border-slate-200/80 text-center space-y-2">
                  <span className="text-2xl">💊</span>
                  <p className="text-xs font-bold text-slate-700">No procedures logged in this view yet.</p>
                  <p className="text-[11px] text-slate-500">
                    Frequently checked items such as IV Saline, Brain MRI, Metformin, or Azithromycin will be ranked here.
                  </p>
                </div>
              ) : (
                data.top_procedures.map((proc, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between p-3 rounded-xl bg-slate-50 border border-slate-200/80 text-xs hover:border-sky-300 transition-colors"
                  >
                    <div className="flex items-center gap-2.5 max-w-[75%] min-w-0">
                      <span className="w-5 h-5 rounded-full bg-sky-100 text-sky-800 font-black text-[10px] flex items-center justify-center flex-shrink-0">
                        {idx + 1}
                      </span>
                      <span className="font-bold text-slate-800 truncate" title={proc.procedure_name}>
                        {proc.procedure_name}
                      </span>
                    </div>
                    <span className="px-2.5 py-0.5 rounded-full font-mono font-bold bg-sky-100 text-sky-900 text-[11px] flex-shrink-0">
                      {proc.count} {proc.count === 1 ? 'record' : 'records'}
                    </span>
                  </div>
                ))
              )}
            </div>

            <div className="mt-3 p-3 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-600">
              Surfaces high-frequency billing items and tracks recurring pharmaceutical and inpatient items across audits.
            </div>
          </div>
        </div>
      )}

      {/* ============================================================ */}
      {/* 8. REGIONAL LOCATIONS HUB (KARNATAKA & INDIA CORRIDORS)       */}
      {/* ============================================================ */}
      {(activeTab === 'all' || activeTab === 'locations') && (
        <div className="bg-white p-5 sm:p-6 rounded-2xl border border-slate-200 shadow-card space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <h2 className="text-sm font-black text-slate-900 uppercase tracking-wide flex items-center gap-2">
                <span>📍</span>
                <span>Regional Healthcare Auditing Hubs</span>
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Claims volume and pricing anomaly distribution across key Karnataka urban healthcare corridors
              </p>
            </div>
            <span className="text-xs font-bold text-sky-700 bg-sky-50 px-2.5 py-1 rounded-lg border border-sky-200 self-start sm:self-auto">
              Verified Karnataka &amp; National Hubs
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
            {(data.top_locations.length > 0
              ? data.top_locations
              : [
                  { location_name: 'Bengaluru, Karnataka', claims_count: 0, anomalies_count: 0 },
                  { location_name: 'Ballari, Karnataka', claims_count: 0, anomalies_count: 0 },
                  { location_name: 'Mysuru, Karnataka', claims_count: 0, anomalies_count: 0 },
                  { location_name: 'Davangere, Karnataka', claims_count: 0, anomalies_count: 0 },
                  { location_name: 'Hubli, Karnataka', claims_count: 0, anomalies_count: 0 },
                ]
            ).map((loc, lIdx) => (
              <div
                key={lIdx}
                className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs space-y-2 hover:border-sky-300 transition-all"
              >
                <div className="font-extrabold text-slate-900 truncate" title={loc.location_name}>
                  {loc.location_name}
                </div>
                <div className="flex items-center justify-between text-[11px]">
                  <span className="text-slate-500">Audited:</span>
                  <span className="font-black text-slate-800">{loc.claims_count}</span>
                </div>
                <div className="flex items-center justify-between text-[11px]">
                  <span className="text-slate-500">Anomalies:</span>
                  <span
                    className={`font-black px-1.5 py-0.5 rounded text-[10px] ${
                      loc.anomalies_count > 0 ? 'bg-amber-100 text-amber-900' : 'bg-emerald-100 text-emerald-900'
                    }`}
                  >
                    {loc.anomalies_count}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ============================================================ */}
      {/* 9. WRITTEN SUMMARY & RECENT RISK CLAIMS                     */}
      {/* ============================================================ */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Plain-English Executive Summary */}
        <div className="lg:col-span-7 bg-white rounded-2xl border border-slate-200 p-5 sm:p-7 shadow-card space-y-4">
          <div className="flex items-center gap-2">
            <span className="text-xl">📋</span>
            <h2 className="text-sm font-black text-slate-900 uppercase tracking-wide">
              What These Findings Mean in Plain Language
            </h2>
          </div>
          <p className="text-xs text-slate-500 leading-relaxed">
            Synthesized plain-English takeaways for patients, healthcare auditors, and clinical administrators:
          </p>

          <ul className="space-y-3 text-xs text-slate-700 leading-relaxed">
            <li className="flex items-start gap-2.5 p-3 rounded-xl bg-sky-50/60 border border-sky-100">
              <span className="w-2 h-2 rounded-full bg-sky-500 mt-1.5 flex-shrink-0" />
              <div>
                <strong>{totalVerified} total {totalVerified === 1 ? 'claim' : 'claims'} evaluated:</strong>{' '}
                {isZeroData
                  ? 'No claims have been audited in this view yet. Start by uploading a bill or prescription.'
                  : `Audited across inpatient itemized bills, outpatient prescriptions, and diagnostic scans.`}
              </div>
            </li>

            <li className="flex items-start gap-2.5 p-3 rounded-xl bg-emerald-50/60 border border-emerald-100">
              <span className="w-2 h-2 rounded-full bg-emerald-500 mt-1.5 flex-shrink-0" />
              <div>
                <strong>{data.decision_overview.approved} claims medically supported ({approvalRate}%):</strong> Treatments conformed to established medical guidelines and billed charges aligned with fair regional benchmarks.
              </div>
            </li>

            <li className="flex items-start gap-2.5 p-3 rounded-xl bg-amber-50/60 border border-amber-100">
              <span className="w-2 h-2 rounded-full bg-amber-500 mt-1.5 flex-shrink-0" />
              <div>
                <strong>{data.decision_overview.flagged + data.decision_overview.held} claims held or flagged for scrutiny:</strong> Includes {data.decision_overview.flagged} pricing markups or guideline discrepancies, and {data.decision_overview.held} safety holds where evidence was insufficient.
              </div>
            </li>

            <li className="flex items-start gap-2.5 p-3 rounded-xl bg-rose-50/60 border border-rose-100">
              <span className="w-2 h-2 rounded-full bg-rose-500 mt-1.5 flex-shrink-0" />
              <div>
                {data.price_alerts_overview.price_alerts > 0 ? (
                  <span>
                    <strong>{data.price_alerts_overview.price_alerts} pricing anomalies detected:</strong> Charges exceeded expected reference rates (including {data.price_alerts_overview.extreme} extreme markup{data.price_alerts_overview.extreme === 1 ? '' : 's'} exceeding 10x benchmark).
                  </span>
                ) : (
                  <span>
                    <strong>No price anomalies detected:</strong> All audited procedure charges matched standard comparison ranges.
                  </span>
                )}
              </div>
            </li>

            <li className="flex items-start gap-2.5 pt-3 border-t border-slate-100 text-slate-500 text-[11px]">
              <span className="text-amber-500 mt-0.5 flex-shrink-0">⚠️</span>
              <div>
                <strong>Clinical &amp; Financial Scope:</strong> EvidenceBridge provides guideline compliance and billing transparency auditing assistance. It does not replace independent physician diagnostic judgment.
              </div>
            </li>
          </ul>
        </div>

        {/* Right Column: Claims Flagged for Attention */}
        <div className="lg:col-span-5 bg-white rounded-2xl border border-slate-200 p-5 sm:p-7 shadow-card space-y-3.5">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-black text-slate-900 uppercase tracking-wide">
              Claims Flagged for Attention
            </h2>
            <Link
              to="/claims"
              className="text-xs font-bold text-sky-600 hover:text-sky-800"
            >
              All Claims &rarr;
            </Link>
          </div>
          <p className="text-xs text-slate-500">
            Recent claims generating pricing anomalies, safe holds, or guideline alerts:
          </p>

          <div className="space-y-3">
            {data.recent_risk_claims.length === 0 ? (
              totalVerified > 0 ? (
                <div className="p-4 rounded-xl bg-emerald-50/80 border border-emerald-200 text-xs text-emerald-900 space-y-2 text-center">
                  <div className="text-2xl">🎉</div>
                  <div className="font-bold text-emerald-950">Clean Audit Record!</div>
                  <p className="text-[11px] text-emerald-800 leading-relaxed">
                    None of your audited claims triggered pricing anomalies or guideline contradictions. All charges conformed to fair reference tariffs.
                  </p>
                  <Link
                    to="/claims"
                    className="inline-block mt-1 font-bold text-emerald-800 hover:text-emerald-950 underline text-xs"
                  >
                    View your verified claims &rarr;
                  </Link>
                </div>
              ) : (
                <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-500 space-y-2 text-center">
                  <div className="text-2xl">🛡️</div>
                  <div className="font-bold text-slate-700">No Risk Claims Flagged</div>
                  <p className="text-[11px] text-slate-500 leading-relaxed">
                    When you audit claims that trigger price markups or guideline contradictions, they will be surfaced here for inspection.
                  </p>
                </div>
              )
            ) : (
              data.recent_risk_claims.slice(0, 4).map((claim) => (
                <div
                  key={claim.claim_id}
                  className="p-3.5 rounded-xl border border-slate-200 bg-slate-50/70 hover:bg-slate-100 transition-colors text-xs flex flex-col justify-between gap-2 shadow-2xs"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-extrabold uppercase ${
                        claim.action === 'flag'
                          ? 'bg-amber-100 text-amber-900 border border-amber-200'
                          : claim.action === 'accept'
                          ? 'bg-emerald-100 text-emerald-900 border border-emerald-200'
                          : 'bg-slate-200 text-slate-800 border border-slate-300'
                      }`}
                    >
                      {claim.action === 'flag' ? '⚠️ Flagged' : claim.action === 'accept' ? '✓ Accepted' : '⏸ Held'}
                    </span>
                    {claim.cost_range ? (
                      <span className="font-mono text-xs font-black text-slate-900">
                        {claim.cost_range}
                      </span>
                    ) : (
                      <span className="text-slate-400 italic text-[11px]">
                        Tariff not stated
                      </span>
                    )}
                  </div>
                  <div className="font-extrabold text-slate-900 truncate" title={claim.entity}>
                    {claim.entity}
                  </div>
                  {claim.reason && (
                    <p className="text-[11px] text-slate-600 line-clamp-2 leading-relaxed">
                      {claim.reason}
                    </p>
                  )}
                  <div className="flex items-center justify-between pt-1.5 border-t border-slate-200/60 text-[10px]">
                    <span className="font-mono text-slate-400">{claim.claim_id}</span>
                    <Link
                      to={`/claims/${encodeURIComponent(claim.claim_id)}`}
                      className="font-bold text-sky-700 hover:text-sky-900"
                    >
                      Audit Details &rarr;
                    </Link>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
