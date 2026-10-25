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
  const conclusiveCount =
    metrics.supported_count +
    metrics.partially_supported_count +
    metrics.contradicted_count

  // Color for density score
  const scoreColor =
    metrics.density_score >= 0.75
      ? 'text-emerald-700 bg-emerald-500'
      : metrics.density_score >= 0.50
      ? 'text-sky-700 bg-sky-500'
      : metrics.density_score >= 0.30
      ? 'text-amber-700 bg-amber-500'
      : 'text-rose-700 bg-rose-500'

  return (
    <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-card">
      {/* Header */}
      <div className="p-6 sm:p-7 bg-gradient-to-r from-slate-50 via-white to-slate-50 border-b border-slate-200">
        <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-4">
          <div>
            <div className="flex items-center gap-3 flex-wrap">
              <h2 className="text-2xl font-black text-slate-900 tracking-tight">
                {metrics.city}
                {metrics.state_or_region ? `, ${metrics.state_or_region}` : ''}
              </h2>
              <TrustTierBadge tier={metrics.trust_tier} />
              {metrics.verified_claims >= 2 && metrics.verified_claims < 5 && (
                <span
                  className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-amber-50 text-amber-800 border border-amber-200"
                  title="Sample size is limited (< 5 audited claims). Metric scores and narratives are preliminary assessments."
                >
                  Preliminary (Sparse Data)
                </span>
              )}
            </div>
            <div className="font-mono text-xs text-slate-500 mt-1">
              Locality Key: <span className="text-slate-800 font-semibold">{metrics.location_key}</span> &bull; Updated:{' '}
              {new Date(metrics.last_updated).toLocaleString()}
            </div>
          </div>

          {onRecompute && (
            <button
              type="button"
              onClick={onRecompute}
              disabled={isRecomputing}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl border border-slate-300 bg-white text-xs font-bold text-slate-700 hover:bg-slate-50 shadow-sm transition-colors disabled:opacity-50 self-start sm:self-auto"
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
              {isRecomputing ? 'Recomputing...' : 'Recompute Score'}
            </button>
          )}
        </div>

        {/* Primary Density Score Bar */}
        <div className="mt-6 p-5 rounded-2xl bg-white border border-slate-200 shadow-subtle">
          <div className="flex items-baseline justify-between mb-2">
            <div>
              <span className="text-xs font-bold uppercase tracking-wider text-slate-600 block">
                Regional Hospital Reliability Score
              </span>
              <span className="text-[11px] text-slate-400">
                Composite metric combining clinical compliance (50%), pricing consistency (35%), and claim volume (15%)
              </span>
            </div>
            <div className="text-right">
              <span className={`text-3xl font-black font-mono ${scoreColor.split(' ')[0]}`}>
                {densityPct}%
              </span>
              <span className="text-xs font-mono font-bold text-slate-400 ml-1.5 block">
                Index: {metrics.density_score.toFixed(3)}
              </span>
            </div>
          </div>

          <div className="w-full bg-slate-100 h-3 rounded-full overflow-hidden mt-3">
            <div
              className={`h-full rounded-full transition-all duration-500 ${scoreColor.split(' ')[1]}`}
              style={{ width: `${Math.min(100, Math.max(0, densityPct))}%` }}
            />
          </div>
          <div className="flex justify-between text-[11px] text-slate-400 mt-1.5 font-medium">
            <span>0.0 Critical Alert</span>
            <span>0.3 Needs Scrutiny</span>
            <span>0.5 Moderate</span>
            <span>0.75+ High Trust</span>
          </div>
        </div>
      </div>

      {/* 4 Core Plain-English Metric Cards */}
      <div className="p-6 grid grid-cols-2 sm:grid-cols-4 gap-3 border-b border-slate-200 bg-slate-50/50">
        <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-subtle text-center">
          <div className="text-xs text-slate-500 font-semibold">Total Audited Claims</div>
          <div className="text-2xl font-black font-mono text-slate-900 mt-1">
            {metrics.verified_claims}
          </div>
          <div className="text-[10px] text-slate-400 mt-0.5">
            {metrics.total_claims} ingested
          </div>
        </div>

        <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-subtle text-center">
          <div className="text-xs text-emerald-800 font-semibold">Guideline Compliance</div>
          <div className="text-2xl font-black font-mono text-emerald-600 mt-1">
            {supportPct}%
          </div>
          <div className="text-[10px] text-slate-400 mt-0.5">
            {metrics.supported_count} of {conclusiveCount} conclusive
          </div>
        </div>

        <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-subtle text-center">
          <div className="text-xs text-rose-800 font-semibold">Price Anomaly Rate</div>
          <div className="text-2xl font-black font-mono text-rose-600 mt-1">
            {anomalyPct}%
          </div>
          <div className="text-[10px] text-slate-400 mt-0.5">
            {metrics.cost_anomaly_count} high markups
          </div>
        </div>

        <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-subtle text-center">
          <div className="text-xs text-sky-800 font-semibold">Recent Activity Volume</div>
          <div className="text-2xl font-black font-mono text-sky-700 mt-1">
            {metrics.recency_weighted_volume.toFixed(1)}
          </div>
          <div className="text-[10px] text-slate-400 mt-0.5">
            Time-decayed weight
          </div>
        </div>
      </div>

      {/* Breakdown by Audit Status */}
      <div className="p-6 border-b border-slate-200 bg-white">
        <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-3">
          Clinical Audit Verdict Breakdown
        </h4>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs">
          <div className="p-3 rounded-lg bg-emerald-50/70 border border-emerald-200">
            <span className="text-emerald-800 font-semibold block text-[11px]">Supported</span>
            <span className="text-lg font-bold font-mono text-emerald-900">{metrics.supported_count}</span>
            <span className="text-[10px] text-emerald-700 block mt-0.5">Adheres to guidelines</span>
          </div>

          <div className="p-3 rounded-lg bg-amber-50/70 border border-amber-200">
            <span className="text-amber-800 font-semibold block text-[11px]">Flagged for Review</span>
            <span className="text-lg font-bold font-mono text-amber-900">{metrics.flagged_count}</span>
            <span className="text-[10px] text-amber-700 block mt-0.5">High markup or conflict</span>
          </div>

          <div className="p-3 rounded-lg bg-rose-50/70 border border-rose-200">
            <span className="text-rose-800 font-semibold block text-[11px]">Contradicted</span>
            <span className="text-lg font-bold font-mono text-rose-900">{metrics.contradicted_count}</span>
            <span className="text-[10px] text-rose-700 block mt-0.5">Guideline violation</span>
          </div>

          <div className="p-3 rounded-lg bg-slate-100 border border-slate-200">
            <span className="text-slate-700 font-semibold block text-[11px]">Held (Abstained)</span>
            <span className="text-lg font-bold font-mono text-slate-800">{metrics.abstained_count}</span>
            <span className="text-[10px] text-slate-500 block mt-0.5">Safe refusal / no data</span>
          </div>
        </div>
      </div>

      {/* Synthesized Location Insight */}
      {insight && (
        <div className="p-6 bg-white space-y-4">
          <div>
            <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
              Automated Hospital Reliability Summary
            </h3>
            <p className="text-xs sm:text-sm text-slate-700 leading-relaxed bg-slate-50 p-4 rounded-xl border border-slate-200">
              {insight.summary_text}
            </p>
          </div>

          {insight.recommendation && (
            <div className="p-4 rounded-xl bg-sky-50 border border-sky-200 text-xs text-sky-950 flex items-start gap-2.5">
              <span className="text-base flex-shrink-0">💡</span>
              <div>
                <strong className="font-bold block text-sky-950">Reviewer Recommendation:</strong>
                <span className="text-sky-900 mt-0.5 block leading-relaxed">{insight.recommendation}</span>
              </div>
            </div>
          )}

          {/* Top Anomalous Items */}
          {insight.top_anomalous_entities.length > 0 && (
            <div>
              <span className="text-xs font-bold text-rose-900 uppercase tracking-wider block mb-2">
                Frequently Marked-Up Line Items
              </span>
              <div className="flex flex-wrap gap-2">
                {insight.top_anomalous_entities.map((item, idx) => (
                  <span
                    key={idx}
                    className="inline-flex items-center px-3 py-1 rounded-lg text-xs font-bold bg-rose-50 text-rose-800 border border-rose-200"
                  >
                    ⚠️ {item}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Sample Claim Links */}
          {insight.sample_claim_ids.length > 0 && (
            <div className="pt-2 flex items-center gap-2 flex-wrap text-xs text-slate-500">
              <span className="font-semibold text-slate-700">Audited Claims in this Metro:</span>
              {insight.sample_claim_ids.map((cid, idx) => (
                <Link
                  key={idx}
                  to={`/claims/${encodeURIComponent(cid)}`}
                  className="font-mono text-sky-600 hover:text-sky-800 font-bold hover:underline bg-slate-50 px-2 py-0.5 rounded border border-slate-200"
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
