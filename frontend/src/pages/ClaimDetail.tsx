import React, { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { getClaim, getVerification, getAudit, verifyClaim } from '../api/client'
import type { Claim, VerificationResult, AuditTrail } from '../types'
import { VerificationBadge, VerdictBadge } from '../components/VerificationBadge'
import { AuditTrailViewer } from '../components/AuditTrailViewer'

export default function ClaimDetail() {
  const { claimId } = useParams<{ claimId: string }>()

  const [claim, setClaim] = useState<Claim | null>(null)
  const [verification, setVerification] = useState<VerificationResult | null>(null)
  const [auditTrail, setAuditTrail] = useState<AuditTrail | null>(null)
  const [loading, setLoading] = useState(true)
  const [reverifying, setReverifying] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [copiedHash, setCopiedHash] = useState(false)

  const loadData = async () => {
    if (!claimId) return
    setLoading(true)
    setError(null)

    try {
      const [cRes, vRes, aRes] = await Promise.allSettled([
        getClaim(claimId),
        getVerification(claimId),
        getAudit(claimId),
      ])

      if (cRes.status === 'fulfilled') {
        setClaim(cRes.value)
      } else {
        setError('Claim not found in database.')
        setLoading(false)
        return
      }

      if (vRes.status === 'fulfilled') {
        setVerification(vRes.value)
      } else {
        setVerification(null)
      }

      if (aRes.status === 'fulfilled') {
        setAuditTrail(aRes.value.audit_trail)
      } else {
        setAuditTrail(null)
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error loading claim data.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [claimId])

  const handleReverify = async () => {
    if (!claimId) return
    setReverifying(true)
    try {
      const resp = await verifyClaim(claimId)
      setVerification(resp.verification)
      // Reload audit trail
      try {
        const aResp = await getAudit(claimId)
        setAuditTrail(aResp.audit_trail)
      } catch {
        // ok
      }
    } catch (err: unknown) {
      alert(`Re-verification failed: ${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setReverifying(false)
    }
  }

  const handleCopyHash = () => {
    if (claim?.provenance?.source_hash) {
      navigator.clipboard.writeText(claim.provenance.source_hash)
      setCopiedHash(true)
      setTimeout(() => setCopiedHash(false), 2000)
    }
  }

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto py-10 space-y-4 animate-pulse">
        <div className="h-6 bg-slate-200 rounded w-1/4" />
        <div className="h-10 bg-slate-200 rounded w-1/2" />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 pt-4">
          <div className="lg:col-span-2 h-96 bg-slate-200 rounded-xl" />
          <div className="h-96 bg-slate-200 rounded-xl" />
        </div>
      </div>
    )
  }

  if (error || !claim) {
    return (
      <div className="max-w-xl mx-auto py-16 text-center">
        <div className="text-4xl mb-3">🔍</div>
        <h2 className="text-lg font-bold text-slate-800 mb-1">Claim Not Found</h2>
        <p className="text-xs text-slate-500 mb-6">{error || `No claim with ID ${claimId}`}</p>
        <Link
          to="/claims"
          className="inline-flex items-center px-4 py-2 bg-slate-800 text-white rounded-lg text-xs font-semibold hover:bg-slate-900 transition-colors"
        >
          &larr; Back to Claims Explorer
        </Link>
      </div>
    )
  }

  const fields = claim.extracted_fields
  const location = claim.location

  return (
    <div className="space-y-6">
      {/* Top Breadcrumb & Action Row */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <Link to="/claims" className="hover:text-slate-800 hover:underline">
            Claims
          </Link>
          <span>/</span>
          <span className="font-mono text-slate-700 font-semibold">{claim.claim_id}</span>
        </div>

        <button
          type="button"
          onClick={handleReverify}
          disabled={reverifying}
          className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg border border-slate-300 bg-white text-xs font-bold text-slate-700 hover:bg-slate-50 shadow-sm transition-colors disabled:opacity-50"
        >
          <svg
            className={`w-3.5 h-3.5 ${reverifying ? 'animate-spin' : ''}`}
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
          {reverifying ? 'Auditing...' : 'Re-run Verification'}
        </button>
      </div>

      {/* Main Grid Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column (2/3): Core Claim and Evidence Details */}
        <div className="lg:col-span-2 space-y-6">
          {/* Header Card */}
          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
            <div className="flex items-center gap-2 flex-wrap mb-2">
              <span className="font-mono text-xs px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-medium">
                {claim.claim_id}
              </span>
              <span className="text-xs px-2 py-0.5 rounded bg-sky-50 text-sky-700 font-medium capitalize">
                {claim.source_type.replace(/_/g, ' ')}
              </span>
              <span className="text-xs text-slate-400">
                Ingested: {new Date(claim.timestamp).toLocaleString()}
              </span>
            </div>

            <h1 className="text-2xl font-bold text-slate-900 mb-2">
              {fields?.entity || 'Unspecified Medical Entity'}
            </h1>

            {fields?.effect_or_outcome && (
              <p className="text-sm text-slate-600 bg-slate-50 p-3 rounded-lg border border-slate-100">
                {fields.effect_or_outcome}
              </p>
            )}
          </div>

          {/* Verbatim Source Text */}
          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
            <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
              Original Verbatim Source Document
            </h3>
            <pre className="text-xs font-mono bg-slate-50 text-slate-800 p-4 rounded-lg border border-slate-200 overflow-x-auto whitespace-pre-wrap leading-relaxed max-h-56">
              {claim.original_text}
            </pre>
          </div>

          {/* Structured Extracted Fields Table */}
          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
            <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">
              Structured Extraction Fields
            </h3>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                <span className="text-slate-400 block mb-0.5">Entity</span>
                <span className="font-semibold text-slate-800">{fields?.entity}</span>
              </div>
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                <span className="text-slate-400 block mb-0.5">Billed Charge</span>
                <span className="font-mono font-bold text-slate-900">{fields?.cost_range || 'None'}</span>
              </div>
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                <span className="text-slate-400 block mb-0.5">Confidence</span>
                <span className="font-mono font-bold text-slate-900">{Math.round(claim.confidence * 100)}%</span>
              </div>
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                <span className="text-slate-400 block mb-0.5">Sentiment</span>
                <span className="font-medium text-slate-800 capitalize">{fields?.sentiment || 'Neutral'}</span>
              </div>
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                <span className="text-slate-400 block mb-0.5">Location Field</span>
                <span className="font-medium text-slate-800">{fields?.location_city || 'None'}</span>
              </div>
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                <span className="text-slate-400 block mb-0.5">Vector Indexed</span>
                <span className="font-medium text-slate-800">{claim.indexed_vector ? 'Yes (ChromaDB)' : 'No'}</span>
              </div>
            </div>
          </div>

          {/* Cryptographic Provenance */}
          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
            <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">
              Tamper-Evident Provenance
            </h3>
            <div className="space-y-2 text-xs">
              <div className="flex items-center justify-between p-2.5 bg-slate-50 rounded-lg border border-slate-200">
                <div className="truncate mr-2">
                  <span className="text-slate-400 font-mono mr-2">SHA-256:</span>
                  <span className="font-mono text-slate-800">{claim.provenance?.source_hash}</span>
                </div>
                <button
                  type="button"
                  onClick={handleCopyHash}
                  className="px-2 py-1 rounded bg-white border border-slate-200 text-slate-600 hover:text-slate-900 font-semibold text-[11px] flex-shrink-0"
                >
                  {copiedHash ? '✓ Copied' : 'Copy'}
                </button>
              </div>
              <div className="grid grid-cols-2 gap-2 text-[11px] text-slate-500">
                <div>Length: {claim.provenance?.text_length} chars</div>
                <div>Origin Type: {claim.provenance?.source_type}</div>
              </div>
            </div>
          </div>

          {/* Geographic Location Info */}
          {location && (
            <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                  Resolved Geographic Locality
                </h3>
                <Link
                  to={`/trust-density?key=${encodeURIComponent(location.normalized_key)}`}
                  className="text-xs font-semibold text-sky-600 hover:text-sky-800 hover:underline"
                >
                  View Metro Trust Density &rarr;
                </Link>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                <div className="p-3 bg-indigo-50/50 rounded-lg border border-indigo-100">
                  <span className="text-slate-400 block mb-0.5">City</span>
                  <span className="font-bold text-indigo-900">{location.city}</span>
                </div>
                <div className="p-3 bg-indigo-50/50 rounded-lg border border-indigo-100">
                  <span className="text-slate-400 block mb-0.5">State/Region</span>
                  <span className="font-bold text-indigo-900">{location.state_or_region || 'N/A'}</span>
                </div>
                <div className="p-3 bg-indigo-50/50 rounded-lg border border-indigo-100">
                  <span className="text-slate-400 block mb-0.5">Canonical Key</span>
                  <span className="font-mono font-bold text-indigo-900">{location.normalized_key}</span>
                </div>
                <div className="p-3 bg-indigo-50/50 rounded-lg border border-indigo-100">
                  <span className="text-slate-400 block mb-0.5">Country</span>
                  <span className="font-bold text-indigo-900">{location.country}</span>
                </div>
              </div>
            </div>
          )}

          {/* 7-Stage Audit Trail Viewer */}
          {auditTrail && <AuditTrailViewer auditTrail={auditTrail} />}
        </div>

        {/* Right Column (1/3): Sticky Verification Decision Card */}
        <div className="lg:col-span-1 space-y-6">
          <div className="sticky top-20 bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-5">
            <div>
              <div className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">
                Audit Decision
              </div>
              {verification ? (
                <div className="flex items-center gap-2 flex-wrap">
                  <VerificationBadge action={verification.action} size="lg" />
                  <VerdictBadge verdict={verification.verdict} />
                </div>
              ) : (
                <div className="text-xs text-amber-700 bg-amber-50 p-2.5 rounded border border-amber-200">
                  Unverified. Click "Re-run Verification" to audit this claim against clinical guidelines.
                </div>
              )}
            </div>

            {/* Support Score Bar */}
            {verification && (
              <div>
                <div className="flex justify-between text-xs text-slate-600 mb-1">
                  <span>Guideline Support Score</span>
                  <span className="font-mono font-bold text-slate-900">
                    {Math.round(verification.support_score * 100)}%
                  </span>
                </div>
                <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${
                      verification.support_score >= 0.70
                        ? 'bg-emerald-500'
                        : verification.support_score >= 0.40
                        ? 'bg-amber-500'
                        : 'bg-rose-500'
                    }`}
                    style={{ width: `${Math.min(100, Math.max(0, verification.support_score * 100))}%` }}
                  />
                </div>
              </div>
            )}

            {/* Cost Anomaly Box */}
            {verification?.cost_anomaly_flag && verification.anomaly_details && (
              <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-900 text-xs space-y-2">
                <div className="font-bold flex items-center justify-between text-rose-700">
                  <span>⚠ Cost Anomaly Alert</span>
                  <span className="font-mono uppercase font-black">
                    {verification.anomaly_details.multiplier}x Benchmark
                  </span>
                </div>
                <p className="leading-relaxed text-rose-800">
                  {verification.anomaly_details.explanation}
                </p>
                <div className="font-mono text-[11px] text-rose-700 pt-1 border-t border-rose-200">
                  Max Expected: ${verification.anomaly_details.benchmark_max?.toFixed(2)}
                </div>
              </div>
            )}

            {/* Abstain Reason */}
            {verification?.action === 'abstain' && (
              <div className="p-3.5 rounded-lg bg-slate-100 border border-slate-300 text-xs text-slate-800">
                <strong className="block font-bold text-slate-900 mb-0.5">Abstained from Verdict:</strong>
                {verification.abstain_reason || 'Inconclusive clinical evidence.'}
              </div>
            )}

            {/* Clinical Reasoning Text */}
            {verification && (
              <div>
                <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">
                  Reasoning
                </span>
                <p className="text-xs text-slate-700 leading-relaxed bg-slate-50 p-3 rounded-lg border border-slate-200">
                  {verification.reasoning}
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
