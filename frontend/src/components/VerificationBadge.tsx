import React from 'react'
import type { VerificationAction, VerificationVerdict, TrustTier } from '../types'

interface VerificationBadgeProps {
  action: VerificationAction | string
  className?: string
  size?: 'sm' | 'md' | 'lg'
  showDescription?: boolean
}

export function VerificationBadge({
  action,
  className = '',
  size = 'md',
  showDescription = false,
}: VerificationBadgeProps) {
  const normAction = (action || '').toLowerCase()

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-1 text-xs',
    lg: 'px-3.5 py-1.5 text-sm',
  }[size]

  if (normAction === 'accept') {
    return (
      <span
        title="Approved: Claim is consistent with authoritative clinical guidelines and billing is within acceptable regional pricing benchmarks."
        className={`inline-flex items-center font-bold tracking-tight rounded-full bg-emerald-50 text-emerald-800 border border-emerald-300 shadow-subtle ${sizeClasses} ${className}`}
      >
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-600 mr-1.5 flex-shrink-0" />
        <span>Approved</span>
        {showDescription && (
          <span className="ml-1 text-[11px] font-normal text-emerald-700">
            • Guideline Match
          </span>
        )}
      </span>
    )
  }

  if (normAction === 'flag') {
    return (
      <span
        title="Flagged for Review: Potential issue detected, such as excessive billing markup or contradiction of medical practice guidelines."
        className={`inline-flex items-center font-bold tracking-tight rounded-full bg-amber-50 text-amber-900 border border-amber-300 shadow-subtle ${sizeClasses} ${className}`}
      >
        <span className="w-1.5 h-1.5 rounded-full bg-amber-600 mr-1.5 flex-shrink-0" />
        <span>Flagged for Review</span>
        {showDescription && (
          <span className="ml-1 text-[11px] font-normal text-amber-800">
            • Potential Issue
          </span>
        )}
      </span>
    )
  }

  if (normAction === 'abstain') {
    return (
      <span
        title="Held for Information (Abstain): Not enough reliable evidence to make a decision without ungrounded assumptions."
        className={`inline-flex items-center font-bold tracking-tight rounded-full bg-slate-100 text-slate-800 border border-slate-300 shadow-subtle ${sizeClasses} ${className}`}
      >
        <span className="w-1.5 h-1.5 rounded-full bg-slate-500 mr-1.5 flex-shrink-0" />
        <span>Held for Information</span>
        {showDescription && (
          <span className="ml-1 text-[11px] font-normal text-slate-600">
            • Not enough evidence
          </span>
        )}
      </span>
    )
  }

  return (
    <span
      className={`inline-flex items-center font-medium rounded-full bg-slate-100 text-slate-700 border border-slate-200 ${sizeClasses} ${className}`}
    >
      {normAction.toUpperCase() || 'UNKNOWN'}
    </span>
  )
}

interface VerdictBadgeProps {
  verdict: VerificationVerdict | string
  className?: string
}

export function VerdictBadge({ verdict, className = '' }: VerdictBadgeProps) {
  const normVerdict = (verdict || '').toLowerCase()

  switch (normVerdict) {
    case 'supported':
      return (
        <span
          title="Clinical assessment confirms alignment with authoritative published guidelines."
          className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 ${className}`}
        >
          ✓ Supported by Guidelines
        </span>
      )
    case 'partially_supported':
      return (
        <span
          title="Clinical evidence partially justifies the claim or suggests conditional indications."
          className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-semibold bg-amber-50 text-amber-800 border border-amber-200 ${className}`}
        >
          ◐ Partially Supported
        </span>
      )
    case 'contradicted':
      return (
        <span
          title="Clinical assessment directly conflicts with authoritative medical guidelines."
          className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200 ${className}`}
        >
          ✕ Guideline Contradicted
        </span>
      )
    case 'insufficient_evidence':
    default:
      return (
        <span
          title="Local knowledge base did not find an authoritative guideline directly matching this procedure and diagnosis."
          className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-semibold bg-slate-100 text-slate-600 border border-slate-200 ${className}`}
        >
          — Insufficient Evidence
        </span>
      )
  }
}

interface TrustTierBadgeProps {
  tier: TrustTier | string
  className?: string
}

export function TrustTierBadge({ tier, className = '' }: TrustTierBadgeProps) {
  const norm = (tier || '').toLowerCase()
  switch (norm) {
    case 'high':
      return (
        <span
          title="High Trust: High clinical guideline adherence and normal billing distribution."
          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-300 ${className}`}
        >
          HIGH TRUST
        </span>
      )
    case 'moderate':
      return (
        <span
          title="Moderate Trust: General compliance with occasional anomalies or moderate sample volume."
          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-sky-100 text-sky-800 border border-sky-300 ${className}`}
        >
          MODERATE TRUST
        </span>
      )
    case 'low':
      return (
        <span
          title="Needs Scrutiny: Elevated frequency of cost anomalies or guideline contradictions."
          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-100 text-amber-800 border border-amber-300 ${className}`}
        >
          NEEDS SCRUTINY
        </span>
      )
    case 'critical_alert':
      return (
        <span
          title="Critical Alert: High rate of extreme billing markups and severe guideline violations."
          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-100 text-rose-800 border border-rose-300 animate-pulse ${className}`}
        >
          CRITICAL ALERT
        </span>
      )
    case 'insufficient_data':
    default:
      return (
        <span
          title="Insufficient Data: Fewer than 2 verified claims recorded for this geographic locality."
          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-600 border border-slate-300 ${className}`}
        >
          INSUFFICIENT DATA
        </span>
      )
  }
}
