import React from 'react'
import { Link } from 'react-router-dom'
import type { Claim, VerificationResult } from '../types'
import { VerificationBadge, VerdictBadge } from './VerificationBadge'

interface ClaimCardProps {
  claim: Claim
  verification?: VerificationResult | null
}

export function ClaimCard({ claim, verification }: ClaimCardProps) {
  const entity = claim.extracted_fields?.entity || 'Unspecified Entity'
  const cost = claim.extracted_fields?.cost_range
  const outcome = claim.extracted_fields?.effect_or_outcome
  const location = claim.location

  return (
    <Link
      to={`/claims/${encodeURIComponent(claim.claim_id)}`}
      className="block bg-white rounded-xl border border-slate-200 p-5 shadow-sm hover:shadow-md hover:border-sky-300 transition-all group"
    >
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-mono text-xs px-2 py-0.5 rounded bg-slate-100 text-slate-600 font-medium">
            {claim.claim_id}
          </span>
          <span className="text-xs px-2 py-0.5 rounded bg-sky-50 text-sky-700 font-medium capitalize">
            {claim.source_type.replace(/_/g, ' ')}
          </span>
          {location && (
            <span className="text-xs px-2 py-0.5 rounded bg-indigo-50 text-indigo-700 font-medium flex items-center gap-1">
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              {location.city}{location.state_or_region ? `, ${location.state_or_region}` : ''}
            </span>
          )}
        </div>

        {/* Verification Status */}
        {verification && (
          <div className="flex items-center gap-2 flex-wrap">
            <VerificationBadge action={verification.action} size="sm" />
            <VerdictBadge verdict={verification.verdict} />
            {verification.cost_anomaly_flag && (
              <span className="inline-flex items-center gap-1 text-xs font-bold text-rose-700 bg-rose-50 border border-rose-200 px-2 py-0.5 rounded">
                <span className="text-rose-500">⚠</span> Anomaly
              </span>
            )}
          </div>
        )}
      </div>

      {/* Main Entity Title */}
      <h3 className="text-base font-semibold text-slate-900 group-hover:text-sky-600 transition-colors line-clamp-1 mb-1">
        {entity}
      </h3>

      {/* Outcome or description */}
      {outcome && (
        <p className="text-xs text-slate-600 line-clamp-2 mb-3">
          {outcome}
        </p>
      )}

      {/* Footer Metrics */}
      <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
        <div className="flex items-center gap-4">
          {cost ? (
            <span className="font-semibold text-slate-900 bg-slate-50 px-2 py-0.5 rounded border border-slate-200">
              {cost}
            </span>
          ) : (
            <span className="text-slate-400">No cost listed</span>
          )}
          <span>
            Conf: <strong className="text-slate-700">{Math.round((claim.confidence || 0) * 100)}%</strong>
          </span>
          {verification && (
            <span>
              Support: <strong className="text-slate-700">{Math.round((verification.support_score || 0) * 100)}%</strong>
            </span>
          )}
        </div>

        <span className="text-slate-400">
          {new Date(claim.timestamp).toLocaleDateString()}
        </span>
      </div>
    </Link>
  )
}
export default ClaimCard
