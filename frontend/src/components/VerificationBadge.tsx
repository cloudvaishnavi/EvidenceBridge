import React from 'react'
import type { VerificationAction, VerificationVerdict, TrustTier } from '../types'

interface VerificationBadgeProps {
  action: VerificationAction | string
  className?: string
  size?: 'sm' | 'md' | 'lg'
}

export function VerificationBadge({
  action,
  className = '',
  size = 'md',
}: VerificationBadgeProps) {
  const normAction = (action || '').toLowerCase()

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-1 text-xs',
    lg: 'px-3 py-1.5 text-sm',
  }[size]

  if (normAction === 'accept') {
    return (
      <span
        className={`inline-flex items-center font-bold tracking-wide rounded-full bg-emerald-100 text-emerald-800 border border-emerald-300 ${sizeClasses} ${className}`}
      >
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-600 mr-1.5" />
        ACCEPT
      </span>
    )
  }

  if (normAction === 'flag') {
    return (
      <span
        className={`inline-flex items-center font-bold tracking-wide rounded-full bg-amber-100 text-amber-900 border border-amber-300 ${sizeClasses} ${className}`}
      >
        <span className="w-1.5 h-1.5 rounded-full bg-amber-600 mr-1.5" />
        FLAG
      </span>
    )
  }

  if (normAction === 'abstain') {
    return (
      <span
        className={`inline-flex items-center font-bold tracking-wide rounded-full bg-slate-100 text-slate-700 border border-slate-300 ${sizeClasses} ${className}`}
      >
        <span className="w-1.5 h-1.5 rounded-full bg-slate-500 mr-1.5" />
        ABSTAIN
      </span>
    )
  }

  return (
    <span
      className={`inline-flex items-center font-medium rounded-full bg-slate-100 text-slate-600 ${sizeClasses} ${className}`}
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
          className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200 ${className}`}
        >
          Supported
        </span>
      )
    case 'partially_supported':
      return (
        <span
          className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-amber-50 text-amber-800 border border-amber-200 ${className}`}
        >
          Partially Supported
        </span>
      )
    case 'contradicted':
      return (
        <span
          className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-rose-50 text-rose-700 border border-rose-200 ${className}`}
        >
          Contradicted
        </span>
      )
    case 'insufficient_evidence':
    default:
      return (
        <span
          className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-50 text-slate-600 border border-slate-200 ${className}`}
        >
          Insufficient Evidence
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
          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-300 ${className}`}
        >
          HIGH TRUST
        </span>
      )
    case 'moderate':
      return (
        <span
          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-800 border border-blue-300 ${className}`}
        >
          MODERATE
        </span>
      )
    case 'low':
      return (
        <span
          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 border border-amber-300 ${className}`}
        >
          LOW TRUST
        </span>
      )
    case 'critical_alert':
      return (
        <span
          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-100 text-rose-800 border border-rose-300 animate-pulse ${className}`}
        >
          CRITICAL ALERT
        </span>
      )
    case 'insufficient_data':
    default:
      return (
        <span
          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-600 border border-slate-300 ${className}`}
        >
          INSUFFICIENT DATA
        </span>
      )
  }
}
