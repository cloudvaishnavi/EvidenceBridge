import React from 'react'
import { Link } from 'react-router-dom'
import type { TrustDensityMetrics, LocationInsight } from '../types'
import { TrustTierBadge } from './VerificationBadge'

interface TrustDensityPanelProps {
  metrics: TrustDensityMetrics
  insight?: LocationInsight | null
  onRecompute?: () => void
  isRecomputing?: boolean
}

export function TrustDensityPanel({
  metrics,
  insight,
  onRecompute,
  isRecomputing = false,
}: TrustDensityPanelProps) {
  const densityPct = Math.round(metrics.density_score * 100)
  const supportPct = Math.round(metrics.support_ratio * 100)
  const anomalyPct = Math.round(metrics.cost_anomaly_rate * 100)

  // Color for density score
  const scoreColor =
    metrics.density_score >= 0.75
      ? 'text-emerald-600 bg-emerald-500'
      : metrics.density_score >= 0.50
      ? 'text-sky-600 bg-sky-500'
      : metrics.density_score >= 0.30
      ? 'text-amber-600 bg-amber-500'
      : 'text-rose-600 bg-rose-500'

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
      {/* Header */}
      <div className="p-6 bg-gradient-to-r from-slate-50 to-white border-b border-slate-200">
        <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-4">
          <div>
            <div className="flex items-center gap-3">
              <h2 className="text-xl font-bold text-slate-900">
                {metrics.city}
                {metrics.state_or_region ? `, ${metrics.state_or_region}` : ''}
              </h2>
              <TrustTierBadge tier={metrics.trust_tier} />
            </div>
            <div className="font-mono text-xs text-slate-500 mt-1">
              Key: <span className="text-slate-700">{metrics.location_key}</span> &bull; Updated:{' '}
              {new Date(metrics.last_updated).toLocaleString()}
            </div>
          </div>

          {onRecompute && (
            <button
              type="button"
              onClick={onRecompute}
              disabled={isRecomputing}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-300 bg-white text-xs font-semibold text-slate-700 hover:bg-slate-50 hover:border-slate-400 transition-colors shadow-sm disabled:opacity-50"
            >
              <svg
                className={`w-3.5 h-3.5 ${isRecomputing ? 'animate-spin' : ''}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                />
              </svg>
              {isRecomputing ? 'Recomputing...' : 'Recompute Metrics'}
            </button>
          )}
        </div>

        {/* Primary Density Score Bar */}
        <div className="mt-5 p-4 rounded-xl bg-slate-50 border border-slate-200">
          <div className="flex items-baseline justify-between mb-2">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Composite Trust Density Score
            </span>
            <span className={`text-2xl font-black font-mono ${scoreColor.split(' ')[0]}`}>
              {metrics.density_score.toFixed(3)}
              <span className="text-xs font-normal text-slate-400 ml-1">/ 1.000</span>
            </span>
          </div>
          <div className="w-full bg-slate-200 h-2.5 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${scoreColor.split(' ')[1]}`}
              style={{ width: `${Math.min(100, Math.max(0, densityPct))}%` }}
            />
          </div>
          <div className="flex justify-between text-[10px] text-slate-400 mt-1 font-mono">
            <span>0.0 Critical</span>
            <span>0.5 Moderate</span>
            <span>1.0 High Trust</span>
          </div>
        </div>
      </div>

      {/* Numerical Metrics Grid */}
      <div className="p-6 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 border-b border-slate-200 bg-white">
        <div className="p-3 rounded-lg bg-slate-50 border border-slate-100 text-center">
          <div className="text-xs text-slate-500 font-medium">Total Claims</div>
          <div className="text-xl font-bold font-mono text-slate-900 mt-1">
            {metrics.total_claims}
          </div>
        </div>
        <div className="p-3 rounded-lg bg-slate-50 border border-slate-100 text-center">
          <div className="text-xs text-slate-500 font-medium">Verified</div>
          <div className="text-xl font-bold font-mono text-slate-900 mt-1">
            {metrics.verified_claims}
          </div>
        </div>
        <div className="p-3 rounded-lg bg-emerald-50/50 border border-emerald-100 text-center">
          <div className="text-xs text-emerald-700 font-medium">Supported</div>
          <div className="text-xl font-bold font-mono text-emerald-800 mt-1">
            {metrics.supported_count}
          </div>
        </div>
        <div className="p-3 rounded-lg bg-amber-50/50 border border-amber-100 text-center">
          <div className="text-xs text-amber-700 font-medium">Flagged</div>
          <div className="text-xl font-bold font-mono text-amber-800 mt-1">
            {metrics.flagged_count}
          </div>
        </div>
        <div className="p-3 rounded-lg bg-rose-50/50 border border-rose-100 text-center">
          <div className="text-xs text-rose-700 font-medium">Contradicted</div>
          <div className="text-xl font-bold font-mono text-rose-800 mt-1">
            {metrics.contradicted_count}
          </div>
        </div>
        <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-center">
          <div className="text-xs text-rose-800 font-semibold">Cost Anomalies</div>
          <div className="text-xl font-black font-mono text-rose-700 mt-1">
            {metrics.cost_anomaly_count}
          </div>
        </div>
      </div>

      {/* Ratios & Time-Decay Volume */}
      <div className="p-6 grid grid-cols-1 sm:grid-cols-3 gap-4 border-b border-slate-200 bg-slate-50/50">
        <div>
          <div className="flex justify-between text-xs text-slate-600 mb-1">
            <span>Support Ratio</span>
            <span className="font-mono font-bold text-slate-800">{supportPct}%</span>
          </div>
          <div className="w-full bg-slate-200 h-2 rounded-full overflow-hidden">
            <div
              className="bg-emerald-500 h-full rounded-full"
              style={{ width: `${Math.min(100, Math.max(0, supportPct))}%` }}
            />
          </div>
        </div>

        <div>
          <div className="flex justify-between text-xs text-slate-600 mb-1">
            <span>Cost Anomaly Rate</span>
            <span className="font-mono font-bold text-rose-700">{anomalyPct}%</span>
          </div>
          <div className="w-full bg-slate-200 h-2 rounded-full overflow-hidden">
            <div
              className="bg-rose-500 h-full rounded-full"
              style={{ width: `${Math.min(100, Math.max(0, anomalyPct))}%` }}
            />
          </div>
        </div>

        <div>
          <div className="flex justify-between text-xs text-slate-600 mb-1">
            <span>Recency-Weighted Volume</span>
            <span className="font-mono font-bold text-slate-800">
              {metrics.recency_weighted_volume.toFixed(1)}
            </span>
          </div>
          <div className="text-[11px] text-slate-400">
            Exponential time decay (45d half-life)
          </div>
        </div>
      </div>

      {/* Synthesized Location Insight */}
      {insight && (
        <div className="p-6 bg-white space-y-4">
          <div>
            <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1">
              Synthesized Locality Audit
            </h3>
            <p className="text-sm text-slate-800 leading-relaxed bg-slate-50 p-4 rounded-lg border border-slate-200">
              {insight.summary_text}
            </p>
          </div>

          {insight.recommendation && (
            <div className="p-3.5 rounded-lg bg-sky-50 border border-sky-200 text-xs text-sky-900">
              <strong className="font-semibold block mb-0.5">Audit Recommendation:</strong>
              {insight.recommendation}
            </div>
          )}

          {/* Top Anomalous Entities */}
          {insight.top_anomalous_entities.length > 0 && (
            <div>
              <span className="text-xs font-bold text-rose-800 uppercase tracking-wider block mb-2">
                Elevated Anomaly Line Items
              </span>
              <div className="flex flex-wrap gap-1.5">
                {insight.top_anomalous_entities.map((item, idx) => (
                  <span
                    key={idx}
                    className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-medium bg-rose-50 text-rose-800 border border-rose-200"
                  >
                    ⚠ {item}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Top Audited Procedures */}
          {insight.top_procedures_audited.length > 0 && (
            <div>
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block mb-2">
                Primary Audited Procedures
              </span>
              <div className="flex flex-wrap gap-1.5">
                {insight.top_procedures_audited.map((item, idx) => (
                  <span
                    key={idx}
                    className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-slate-100 text-slate-700"
                  >
                    {item}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Sample Claim Links */}
          {insight.sample_claim_ids.length > 0 && (
            <div className="pt-2 flex items-center gap-2 flex-wrap text-xs text-slate-500">
              <span>Sample Claims:</span>
              {insight.sample_claim_ids.map((cid, idx) => (
                <Link
                  key={idx}
                  to={`/claims/${encodeURIComponent(cid)}`}
                  className="font-mono text-sky-600 hover:text-sky-800 hover:underline"
                >
                  {cid}
                </Link>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
export default TrustDensityPanel
