import { useState, useEffect } from 'react'
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
import { getInsightsSummary } from '../api/client'
import type { InsightsSummaryResponse } from '../types'

// Theme Colors
const COLORS = {
  emerald: '#10b981', // Approved / Supported
  amber: '#f59e0b',   // Flagged / Moderate
  slate: '#64748b',   // Held / Insufficient
  rose: '#f43f5e',    // Contradicted / Extreme
  orange: '#f97316',  // Severe
  sky: '#0284c7',     // Normal / Benchmarked
}

export default function Insights() {
  const [data, setData] = useState<InsightsSummaryResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchData = async () => {
    setLoading(true)
    setError(null)
    try {
      const summary = await getInsightsSummary()
      setData(summary)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load visual insights.')
    } finally {
      setLoading(false)
    }
  };

  useEffect(() => {
    fetchData()
  }, [])

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto space-y-8 animate-pulse font-sans">
        <div className="bg-white rounded-2xl p-8 border border-slate-200 space-y-4 shadow-xs">
          <div className="h-6 bg-slate-200 rounded w-1/4" />
          <div className="h-4 bg-slate-200 rounded w-1/2" />
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-28 bg-white rounded-2xl border border-slate-200 shadow-xs" />
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
        <div className="text-4xl mb-3">📊</div>
        <h2 className="text-lg font-bold text-slate-800 mb-1">Failed to Load Insights</h2>
        <p className="text-xs text-slate-500 mb-6">{error || 'Unable to retrieve statistics.'}</p>
        <button
          type="button"
          onClick={fetchData}
          className="px-4 py-2 bg-sky-600 text-white rounded-xl text-xs font-bold hover:bg-sky-700 transition-colors shadow-xs"
        >
          Try Again
        </button>
      </div>
    )
  }

  // Prep Chart Data
  const decisionData = [
    { name: 'Supported & Approved', value: data.decision_overview.approved, color: COLORS.emerald },
    { name: 'Flagged for Review', value: data.decision_overview.flagged, color: COLORS.amber },
    { name: 'Held (Need Evidence)', value: data.decision_overview.held, color: COLORS.slate },
  ].filter((d) => d.value > 0)

  const priceAlertsData = [
    { name: 'Normal', value: data.price_alerts_overview.normal_charges, color: COLORS.sky },
    { name: 'Moderate (3x–5x)', value: data.price_alerts_overview.moderate, color: COLORS.amber },
    { name: 'Severe (5x–10x)', value: data.price_alerts_overview.severe, color: COLORS.orange },
    { name: 'Extreme (≥10x)', value: data.price_alerts_overview.extreme, color: COLORS.rose },
  ]

  const guidelineData = [
    { name: 'Supported', count: data.guideline_support_overview.supported, fill: COLORS.emerald },
    { name: 'Partial', count: data.guideline_support_overview.partially_supported, fill: COLORS.sky },
    { name: 'Contradicted', count: data.guideline_support_overview.contradicted, fill: COLORS.rose },
    { name: 'Insufficient', count: data.guideline_support_overview.insufficient_evidence, fill: COLORS.slate },
  ]

  const totalVerified = data.total_verified || 1
  const approvalRate = Math.round((data.decision_overview.approved / totalVerified) * 100)
  const anomalyRate = Math.round((data.price_alerts_overview.price_alerts / totalVerified) * 100)
  const heldRate = Math.round((data.decision_overview.held / totalVerified) * 100)

  return (
    <div className="max-w-6xl mx-auto space-y-6 sm:space-y-8 font-sans w-full max-w-full">
      {/* Header */}
      <div className="bg-white rounded-2xl border border-slate-200 p-5 sm:p-7 shadow-xs">
        <div className="flex flex-col md:flex-row justify-between md:items-center gap-4">
          <div>
            <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-sky-50 text-sky-800 text-[11px] font-bold uppercase tracking-wider mb-1.5 border border-sky-200">
              Plain-Language Analytics
            </div>
            <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
              Audit Insights &amp; Statistics
            </h1>
            <p className="text-xs sm:text-sm text-slate-500 mt-1 max-w-2xl leading-relaxed">
              Understand hospital billing charges, medical guideline evidence, and safety decisions in plain English.
            </p>
          </div>

          <div className="flex items-center gap-2 self-start md:self-auto flex-wrap">
            <button
              type="button"
              onClick={fetchData}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-slate-300 bg-white text-xs font-bold text-slate-700 hover:bg-slate-50 shadow-xs transition-colors"
            >
              <span>🔄</span>
              <span>Refresh</span>
            </button>
            <Link
              to="/audit"
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-sky-600 hover:bg-sky-700 text-white text-xs font-bold shadow-xs transition-colors"
            >
              <span>+ Audit Claim</span>
            </Link>
          </div>
        </div>

        {/* Baseline Fallback Banner */}
        {data.is_baseline_fallback && (
          <div className="mt-4 p-3 rounded-xl bg-sky-50/90 border border-sky-200 text-sky-950 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <span className="text-base flex-shrink-0">ℹ️</span>
              <span>
                <strong>Demonstration Baseline:</strong> Showing aggregations from the standard clinical benchmark set ({data.total_verified} claims). As you audit new claims, live results will update these charts.
              </span>
            </div>
            <Link
              to="/audit"
              className="font-bold text-sky-700 hover:text-sky-900 underline whitespace-nowrap text-xs self-start sm:self-auto"
            >
              Audit a claim &rarr;
            </Link>
          </div>
        )}
      </div>

      {/* Top 4 Key Summary Numbers with plain explanations */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
              Total Audited Claims
            </span>
            <span className="text-slate-400 text-xs" title="Total medical records examined">📋</span>
          </div>
          <div className="text-3xl font-black font-mono text-slate-900 mt-1">
            {data.total_verified}
          </div>
          <p className="text-[11px] text-slate-500 mt-1.5 leading-snug">
            Processed through 7-stage evidence and cost auditing.
          </p>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-emerald-700">
              Supported &amp; Fair
            </span>
            <span className="text-emerald-500 text-xs" title="Consistent with guidelines and fair pricing">✓</span>
          </div>
          <div className="text-3xl font-black font-mono text-emerald-600 mt-1">
            {data.decision_overview.approved}
            <span className="text-sm font-semibold text-slate-400 ml-1.5">({approvalRate}%)</span>
          </div>
          <p className="text-[11px] text-slate-500 mt-1.5 leading-snug">
            Treatments backed by medical evidence with fair billing.
          </p>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-amber-700">
              Flagged for Review
            </span>
            <span className="text-amber-500 text-xs" title="Requires human review due to price or guideline mismatch">⚠️</span>
          </div>
          <div className="text-3xl font-black font-mono text-amber-600 mt-1">
            {data.decision_overview.flagged}
            <span className="text-sm font-semibold text-slate-400 ml-1.5">({Math.round((data.decision_overview.flagged / totalVerified) * 100)}%)</span>
          </div>
          <p className="text-[11px] text-slate-500 mt-1.5 leading-snug">
            High markup ({anomalyRate}% of claims) or guideline discrepancy.
          </p>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-600">
              Held for Evidence
            </span>
            <span className="text-slate-400 text-xs" title="Not enough reliable evidence to decide">⏸</span>
          </div>
          <div className="text-3xl font-black font-mono text-slate-700 mt-1">
            {data.decision_overview.held}
            <span className="text-sm font-semibold text-slate-400 ml-1.5">({heldRate}%)</span>
          </div>
          <p className="text-[11px] text-slate-500 mt-1.5 leading-snug">
            Safely held: Not enough reliable evidence to decide.
          </p>
        </div>
      </div>

      {/* Primary Visualizations Grid with Clear Plain-Language Explanations */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Chart 1: Decision Breakdown */}
        <div className="bg-white p-5 sm:p-6 rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-1">
              <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wide">
                1. Overall Decision Breakdown
              </h2>
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-600 font-semibold">
                {data.total_verified} Total Claims
              </span>
            </div>
            <p className="text-xs text-slate-500 mb-3 leading-relaxed">
              How audited claims were classified by the system:
            </p>
          </div>

          <div className="h-60 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={decisionData}
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={80}
                  paddingAngle={4}
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
                    borderRadius: '8px',
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
          </div>

          {/* Plain Language Interpretation */}
          <div className="mt-3 p-3 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-700 space-y-1">
            <div className="font-bold text-slate-900 flex items-center gap-1.5">
              <span>💡</span>
              <span>What this chart tells you:</span>
            </div>
            <p className="text-[11px] text-slate-600 leading-relaxed">
              • <strong>{data.decision_overview.approved} claims ({approvalRate}%)</strong> are fully verified as medically indicated and priced fairly.
              <br />
              • <strong>{data.decision_overview.flagged} claims</strong> have billing markups or guideline questions needing auditor review.
              <br />
              • <strong>{data.decision_overview.held} claims</strong> were held safely because authoritative guidelines were missing—preventing AI hallucination.
            </p>
          </div>
        </div>

        {/* Chart 2: Price Alerts & Severity Breakdown */}
        <div className="bg-white p-5 sm:p-6 rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-1">
              <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wide">
                2. Price Comparison &amp; Markup Severity
              </h2>
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-amber-50 text-amber-800 font-semibold border border-amber-200">
                {data.price_alerts_overview.price_alerts} Price Alerts
              </span>
            </div>
            <p className="text-xs text-slate-500 mb-3 leading-relaxed">
              Billed amounts compared against CMS Medicare and regional fair-market pricing:
            </p>
          </div>

          <div className="h-60 w-full">
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
                    borderRadius: '8px',
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
          </div>

          {/* Plain Language Interpretation */}
          <div className="mt-3 p-3 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-700 space-y-1">
            <div className="font-bold text-slate-900 flex items-center gap-1.5">
              <span>💡</span>
              <span>What this chart tells you:</span>
            </div>
            <p className="text-[11px] text-slate-600 leading-relaxed">
              • <strong>{data.price_alerts_overview.normal_charges} claims</strong> were billed within expected fair rates.
              <br />
              • <strong>{data.price_alerts_overview.extreme} claims</strong> suffered extreme markups (≥10× over benchmark).
              <br />
              • When a price anomaly is detected, patients and auditors can dispute the specific itemized fee.
            </p>
          </div>
        </div>
      </div>

      {/* Row 3: Guideline Support & Top Procedures */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Guideline Support Bar Chart */}
        <div className="bg-white p-5 sm:p-6 rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-1">
              <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wide">
                3. Clinical Evidence Agreement
              </h2>
              <span className="text-xs font-mono text-slate-400">Medical Standards</span>
            </div>
            <p className="text-xs text-slate-500 mb-3 leading-relaxed">
              Whether clinical treatments matched published guidelines (CDC, AHA, ADA, USP):
            </p>
          </div>

          <div className="h-56 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={guidelineData} margin={{ top: 10, right: 10, left: -20, bottom: 10 }}>
                <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#64748b' }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 10, fill: '#64748b' }} />
                <Tooltip
                  // eslint-disable-next-line @typescript-eslint/no-explicit-any
                  formatter={(val: any) => [`${val ?? 0} Claims`, 'Verdicts']}
                  contentStyle={{
                    backgroundColor: '#0f172a',
                    color: '#fff',
                    borderRadius: '8px',
                    fontSize: '11px',
                    border: 'none',
                  }}
                />
                <Bar dataKey="count" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="mt-3 p-3 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-600">
            <strong>Supported:</strong> {data.guideline_support_overview.supported} claims &bull;{' '}
            <strong>Partial:</strong> {data.guideline_support_overview.partially_supported} claims &bull;{' '}
            <strong>Contradicted:</strong> {data.guideline_support_overview.contradicted} claims &bull;{' '}
            <strong>Missing Info:</strong> {data.guideline_support_overview.insufficient_evidence} claims
          </div>
        </div>

        {/* Top Procedures List */}
        <div className="bg-white p-5 sm:p-6 rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-1">
              <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wide">
                4. Most Frequently Audited Items
              </h2>
              <span className="text-xs font-mono text-slate-400">Top Frequency</span>
            </div>
            <p className="text-xs text-slate-500 mb-3 leading-relaxed">
              Medical tests, medications, and hospital lines audited most often:
            </p>
          </div>

          <div className="space-y-2">
            {data.top_procedures.length === 0 ? (
              <p className="text-xs text-slate-400 italic py-4">No procedure records logged yet.</p>
            ) : (
              data.top_procedures.map((proc, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between p-2.5 rounded-xl bg-slate-50 border border-slate-100 text-xs"
                >
                  <div className="flex items-center gap-2 max-w-[75%] min-w-0">
                    <span className="w-5 h-5 rounded-full bg-slate-200 text-slate-700 font-bold text-[10px] flex items-center justify-center flex-shrink-0">
                      {idx + 1}
                    </span>
                    <span className="font-semibold text-slate-800 truncate" title={proc.procedure_name}>
                      {proc.procedure_name}
                    </span>
                  </div>
                  <span className="px-2 py-0.5 rounded font-mono font-bold bg-sky-100 text-sky-800 text-[11px] flex-shrink-0">
                    {proc.count} {proc.count === 1 ? 'claim' : 'claims'}
                  </span>
                </div>
              ))
            )}
          </div>

          <div className="mt-3 p-3 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-600">
            Helps spot repetitive billing codes and recurring high-volume hospital charges.
          </div>
        </div>
      </div>

      {/* SECTION 6: Compact Written Summary ("What these results mean") at Bottom-Left */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Written Summary (Always visible, renders even if charts fail) */}
        <div className="lg:col-span-7 bg-white rounded-2xl border border-slate-200 p-5 sm:p-6 shadow-xs">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-lg">📋</span>
            <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wide">
              What these results mean
            </h2>
          </div>
          <p className="text-xs text-slate-500 mb-4 leading-relaxed">
            A clear summary of the data above for patients, family members, and auditors:
          </p>

          <ul className="space-y-3 text-xs text-slate-700 leading-relaxed">
            <li className="flex items-start gap-2.5">
              <span className="w-1.5 h-1.5 rounded-full bg-sky-500 mt-1.5 flex-shrink-0" />
              <div>
                <strong>{data.total_verified} claims have been audited</strong> across all clinical and hospital bill entries currently in your dataset.
              </div>
            </li>

            <li className="flex items-start gap-2.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 mt-1.5 flex-shrink-0" />
              <div>
                <strong>{data.decision_overview.approved} claims have sufficient supporting evidence</strong> ({approvalRate}% of total). These treatments matched medical guidelines and their prices were within normal comparison benchmarks.
              </div>
            </li>

            <li className="flex items-start gap-2.5">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-500 mt-1.5 flex-shrink-0" />
              <div>
                <strong>{data.decision_overview.flagged + data.decision_overview.held} claims require further review.</strong> Of these, {data.decision_overview.flagged} have noticeable price markups or guideline questions, and {data.decision_overview.held} were held because available evidence was insufficient to make a responsible automated judgment.
              </div>
            </li>

            <li className="flex items-start gap-2.5">
              <span className="w-1.5 h-1.5 rounded-full bg-rose-500 mt-1.5 flex-shrink-0" />
              <div>
                {data.price_alerts_overview.price_alerts > 0 ? (
                  <span>
                    <strong>{data.price_alerts_overview.price_alerts} price anomalies were detected</strong> by our billing rules. Billed charges were significantly higher than standard Medicare/regional comparison prices (including {data.price_alerts_overview.extreme} extreme markup{data.price_alerts_overview.extreme === 1 ? '' : 's'} exceeding 10×).
                  </span>
                ) : (
                  <span>
                    <strong>No price anomalies were detected:</strong> All audited charges with comparison benchmarks fell within expected ranges.
                  </span>
                )}
              </div>
            </li>

            <li className="flex items-start gap-2.5 pt-3 border-t border-slate-100 text-slate-500 text-[11px]">
              <span className="text-amber-500 mt-0.5 flex-shrink-0">⚠️</span>
              <div>
                <strong>Important limitations to understand:</strong>{' '}
                {data.total_verified <= 10
                  ? `This summary is based on a small sample (${data.total_verified} claims). It does not represent population-wide hospital statistics.`
                  : 'Conclusions depend on available local guidelines and public fee schedules.'}{' '}
                EvidenceBridge provides financial and guideline auditing assistance, not medical diagnosis or clinical treatment recommendations.
              </div>
            </li>
          </ul>
        </div>

        {/* Right Column: Notable High-Risk Claims */}
        <div className="lg:col-span-5 bg-white rounded-2xl border border-slate-200 p-5 sm:p-6 shadow-xs">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wide">
              Claims Flagged for Attention
            </h2>
            <Link
              to="/claims"
              className="text-xs font-bold text-sky-600 hover:text-sky-800"
            >
              All Claims &rarr;
            </Link>
          </div>
          <p className="text-xs text-slate-500 mb-3">
            Recent claims that generated price alerts or safety holds:
          </p>

          <div className="space-y-2.5">
            {data.recent_risk_claims.length === 0 ? (
              <p className="text-xs text-slate-400 italic py-4">No risk claims flagged.</p>
            ) : (
              data.recent_risk_claims.slice(0, 4).map((claim) => (
                <div
                  key={claim.claim_id}
                  className="p-3 rounded-xl border border-slate-200 bg-slate-50/60 hover:bg-slate-100/80 transition-colors text-xs flex flex-col justify-between gap-1.5"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold flex-shrink-0 ${
                        claim.action === 'flag'
                          ? 'bg-amber-100 text-amber-900'
                          : 'bg-slate-200 text-slate-800'
                      }`}
                    >
                      {claim.action === 'flag' ? '⚠️ Flagged' : '⏸ Held'}
                    </span>
                    {claim.cost_range && (
                      <span className="font-mono text-xs font-bold text-slate-800 flex-shrink-0">
                        {claim.cost_range}
                      </span>
                    )}
                  </div>
                  <div className="font-bold text-slate-900 truncate" title={claim.entity}>
                    {claim.entity}
                  </div>
                  {claim.reason && (
                    <p className="text-[11px] text-slate-500 line-clamp-1 leading-snug">
                      {claim.reason}
                    </p>
                  )}
                  <div className="flex items-center justify-between pt-1 border-t border-slate-200/60 text-[10px]">
                    <span className="font-mono text-slate-400">{claim.claim_id}</span>
                    <Link
                      to={`/claims/${claim.claim_id}`}
                      className="font-bold text-sky-600 hover:text-sky-800"
                    >
                      Inspect &rarr;
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
