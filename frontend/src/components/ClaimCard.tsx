import React from 'react'
import { Link } from 'react-router-dom'
import type { Claim, VerificationResult } from '../types'
import { VerificationBadge, VerdictBadge } from './VerificationBadge'
import { formatCurrency } from '../utils/currency'

interface ClaimCardProps {
  claim: Claim
  verification?: VerificationResult | null
}

export function ClaimCard({ claim, verification }: ClaimCardProps) {
  const entity = claim.extracted_fields?.entity || 'Unspecified Medical Procedure'
  const cost = claim.extracted_fields?.cost_range
  const outcome = claim.extracted_fields?.effect_or_outcome
  const location = claim.location

  const displayCost = (() => {
    if (!cost) return null
    const hasSymbol = /[\$₹€£]/.test(cost) || /rs\.?/i.test(cost) || /usd|inr|eur|gbp/i.test(cost)
    if (hasSymbol) {
      return `${cost}${claim.extracted_fields?.cost_currency ? ` (${claim.extracted_fields.cost_currency})` : ''}`
    }
    const cleanNum = parseFloat(cost.replace(/,/g, ''))
    if (!isNaN(cleanNum)) {
      return formatCurrency(cleanNum, claim.extracted_fields?.cost_currency || 'INR')
    }
    return `${cost}${claim.extracted_fields?.cost_currency ? ` (${claim.extracted_fields.cost_currency})` : ''}`
  })()

  return (
    <Link
      to={`/claims/${encodeURIComponent(claim.claim_id)}`}
      className="block bg-white rounded-2xl border border-slate-200 p-5 sm:p-6 shadow-subtle hover:shadow-card hover:border-sky-300 transition-all group"
    >
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 mb-3">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-mono text-xs px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-700 font-semibold">
            {claim.claim_id}
          </span>
          <span className="text-xs px-2.5 py-0.5 rounded-full bg-sky-50 text-sky-700 font-semibold capitalize border border-sky-100">
            {claim.source_type.replace(/_/g, ' ')}
          </span>
          {location && (
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-indigo-50 text-indigo-700 font-semibold flex items-center gap-1 border border-indigo-100">
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              {location.city}{location.state_or_region ? `, ${location.state_or_region}` : ''}
            </span>
          )}
        </div>

        {/* Verification Status Pills */}
        {verification && (
          <div className="flex items-center gap-2 flex-wrap">
            <VerificationBadge action={verification.action} size="sm" />
            <VerdictBadge verdict={verification.verdict} />
            {verification.cost_anomaly_flag && (
              <span
                title="Billed charge significantly exceeds regional benchmark schedules."
                className="inline-flex items-center gap-1 text-xs font-bold text-rose-700 bg-rose-50 border border-rose-200 px-2 py-0.5 rounded-md"
              >
                <span>⚠️</span> Price Alert
              </span>
            )}
          </div>
        )}
      </div>

      {/* Main Entity Title */}
      <h3 className="text-base font-bold text-slate-900 group-hover:text-sky-600 transition-colors line-clamp-1 mb-1.5">
        {entity}
      </h3>

      {/* Clinical indication or snippet */}
      {outcome ? (
        <p className="text-xs text-slate-600 line-clamp-2 mb-3 leading-relaxed">
          {outcome}
        </p>
      ) : (
        <p className="text-xs text-slate-400 line-clamp-1 mb-3 font-mono">
          {claim.original_text.substring(0, 140)}...
        </p>
      )}

      {/* Footer Metrics */}
      <div className="pt-3 border-t border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between text-xs text-slate-500 gap-2">
        <div className="flex items-center gap-3 sm:gap-4 flex-wrap">
          {displayCost ? (
            <span className="font-bold text-slate-900 bg-slate-50 px-2.5 py-0.5 rounded-md border border-slate-200 font-mono text-xs">
              Billed: {displayCost}
            </span>
          ) : (
            <span className="text-slate-400 italic text-[11px]">Price data not available</span>
          )}

          {verification && (
            <span className="text-slate-600">
              Guideline Confidence:{' '}
              <strong className="text-slate-800 font-mono">
                {Math.round((verification.support_score || 0) * 100)}%
              </strong>
            </span>
          )}
        </div>

        <span className="text-slate-400 text-[11px]">
          Audited: {new Date(claim.timestamp).toLocaleDateString()}
        </span>
      </div>
    </Link>
  )
}
export default ClaimCard
