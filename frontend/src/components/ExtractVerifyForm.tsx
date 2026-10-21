import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { extractAndVerify } from '../api/client'
import type { ExtractAndVerifyResponse, SourceType } from '../types'
import { VerificationBadge, VerdictBadge } from './VerificationBadge'

interface ExtractVerifyFormProps {
  initialText?: string
  onSampleCleared?: () => void
}

export function ExtractVerifyForm({
  initialText = '',
  onSampleCleared,
}: ExtractVerifyFormProps) {
  const [text, setText] = useState(initialText)
  const [sourceType, setSourceType] = useState<SourceType>('hospital_bill')
  const [sourceUrl, setSourceUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<ExtractAndVerifyResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (initialText) {
      setText(initialText)
      setResult(null)
      setError(null)
    }
  }, [initialText])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!text.trim()) return

    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const response = await extractAndVerify({
        text: text.trim(),
        source_type: sourceType,
        source_url: sourceUrl.trim() || undefined,
        store_claim: true,
      })
      setResult(response)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Extraction and verification failed.')
    } finally {
      setLoading(false)
    }
  }

  const handleClear = () => {
    setText('')
    setSourceUrl('')
    setResult(null)
    setError(null)
    onSampleCleared?.()
  }

  return (
    <div className="space-y-6">
      {/* Input Form Card */}
      <form
        onSubmit={handleSubmit}
        className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm"
      >
        <div className="mb-4">
          <label
            htmlFor="clinical-text"
            className="block text-sm font-bold text-slate-800 mb-1"
          >
            Raw Clinical or Hospital Bill Text
          </label>
          <p className="text-xs text-slate-500 mb-2">
            Paste unedited patient charts, itemized bill lines with CPT codes, or clinic notes.
          </p>
          <textarea
            id="clinical-text"
            rows={7}
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Paste text here, e.g. 'MEMORIAL HOSPITAL - ATLANTA, GA. Emergency Dept Visit CPT 99285. Total charge $6,825.00'..."
            className="w-full px-3.5 py-2.5 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-sky-500 font-mono text-slate-800 placeholder:text-slate-400"
            required
          />
        </div>

        {/* Source options */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
          <div>
            <label
              htmlFor="source-type"
              className="block text-xs font-semibold text-slate-700 mb-1"
            >
              Document Source Type
            </label>
            <select
              id="source-type"
              value={sourceType}
              onChange={(e) => setSourceType(e.target.value as SourceType)}
              className="w-full px-3 py-2 rounded-lg border border-slate-300 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-sky-500 bg-white"
            >
              <option value="hospital_bill">Hospital Bill / Itemized Statement</option>
              <option value="clinical_note">Clinical Note / EHR Chart</option>
              <option value="patient_report">Patient Post / Survey Report</option>
              <option value="forum_post">Health Forum Post</option>
              <option value="other">Other Healthcare Record</option>
            </select>
          </div>

          <div>
            <label
              htmlFor="source-url"
              className="block text-xs font-semibold text-slate-700 mb-1"
            >
              Source Identifier or URI (Optional)
            </label>
            <input
              id="source-url"
              type="text"
              value={sourceUrl}
              onChange={(e) => setSourceUrl(e.target.value)}
              placeholder="e.g. hospital://atlanta-regional/inv-99285"
              className="w-full px-3 py-2 rounded-lg border border-slate-300 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-sky-500 placeholder:text-slate-400"
            />
          </div>
        </div>

        {/* Form Actions */}
        <div className="flex items-center justify-between pt-4 border-t border-slate-100">
          <button
            type="button"
            onClick={handleClear}
            className="text-xs text-slate-500 hover:text-slate-700 font-medium px-3 py-2 rounded"
          >
            Clear Text
          </button>

          <button
            type="submit"
            disabled={loading || !text.trim()}
            className="inline-flex items-center gap-2 px-6 py-2.5 rounded-lg bg-sky-600 text-white text-sm font-bold hover:bg-sky-700 transition-colors shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <>
                <svg
                  className="animate-spin -ml-1 mr-2 h-4 w-4 text-white"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
                Auditing Claim with Local Model...
              </>
            ) : (
              'Extract &amp; Verify Claim'
            )}
          </button>
        </div>
      </form>

      {/* Error Message */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-sm">
          <div className="font-bold mb-1 flex items-center gap-2">
            <span>⚠</span> Audit Failed
          </div>
          <p>{error}</p>
        </div>
      )}

      {/* Audit Result Display */}
      {result && (
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm animate-fadeIn">
          {/* Header Badge Strip */}
          <div className="p-6 bg-slate-50 border-b border-slate-200 flex flex-col sm:flex-row justify-between sm:items-center gap-3">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                  Audit Verdict
                </span>
                <span className="font-mono text-xs text-slate-500">
                  {result.claim.claim_id}
                </span>
              </div>
              <div className="text-lg font-bold text-slate-900 mt-1">
                {result.claim.extracted_fields?.entity || 'Extracted Entity'}
              </div>
            </div>

            <div className="flex items-center gap-2 flex-wrap">
              <VerificationBadge action={result.verification.action} size="lg" />
              <VerdictBadge verdict={result.verification.verdict} />
            </div>
          </div>

          {/* Verification Details */}
          <div className="p-6 space-y-5">
            {/* Cost Anomaly Alert */}
            {result.verification.cost_anomaly_flag && result.verification.anomaly_details && (
              <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-900">
                <div className="flex items-center justify-between mb-2">
                  <div className="font-bold flex items-center gap-1.5 text-sm text-rose-700">
                    <span>⚠</span> Cost Anomaly Detected
                  </div>
                  <span className="text-xs font-mono font-bold bg-rose-200 text-rose-900 px-2 py-0.5 rounded uppercase">
                    {result.verification.anomaly_details.severity} (
                    {result.verification.anomaly_details.multiplier}x benchmark)
                  </span>
                </div>
                <p className="text-xs text-rose-800 leading-relaxed">
                  {result.verification.anomaly_details.explanation}
                </p>
                <div className="mt-2 text-xs text-rose-700 font-mono">
                  Billed: ${result.verification.anomaly_details.extracted_amount?.toFixed(2)} &bull; Benchmark Range: $
                  {result.verification.anomaly_details.benchmark_min?.toFixed(2)} - $
                  {result.verification.anomaly_details.benchmark_max?.toFixed(2)}
                </div>
              </div>
            )}

            {/* Abstention notice */}
            {result.verification.action === 'abstain' && (
              <div className="p-4 rounded-xl bg-slate-100 border border-slate-300 text-slate-800 text-xs">
                <strong className="block font-bold text-slate-900 mb-1">
                  Safety Gate Triggered: System Abstained
                </strong>
                {result.verification.abstain_reason || 'Evidence was inconclusive or confidence was below safety threshold.'}
              </div>
            )}

            {/* Clinical Reasoning */}
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
              <div className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1">
                Clinical Audit Rationale
              </div>
              <p className="text-sm text-slate-800 leading-relaxed">
                {result.verification.reasoning}
              </p>
            </div>

            {/* Key Field Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
              <div className="p-3 rounded-lg bg-slate-50 border border-slate-100">
                <span className="text-slate-500 block mb-0.5">Billed Charge</span>
                <span className="font-mono font-bold text-slate-900 text-sm">
                  {result.claim.extracted_fields?.cost_range || 'None Listed'}
                </span>
              </div>

              <div className="p-3 rounded-lg bg-slate-50 border border-slate-100">
                <span className="text-slate-500 block mb-0.5">Support Score</span>
                <span className="font-mono font-bold text-slate-900 text-sm">
                  {Math.round(result.verification.support_score * 100)}%
                </span>
              </div>

              <div className="p-3 rounded-lg bg-slate-50 border border-slate-100">
                <span className="text-slate-500 block mb-0.5">Extraction Conf</span>
                <span className="font-mono font-bold text-slate-900 text-sm">
                  {Math.round(result.claim.confidence * 100)}%
                </span>
              </div>

              <div className="p-3 rounded-lg bg-slate-50 border border-slate-100">
                <span className="text-slate-500 block mb-0.5">Location</span>
                <span className="font-semibold text-slate-900 truncate block">
                  {result.claim.location?.city
                    ? `${result.claim.location.city}${result.claim.location.state_or_region ? `, ${result.claim.location.state_or_region}` : ''}`
                    : 'Not Detected'}
                </span>
              </div>
            </div>

            {/* Link to Full Audit Trail */}
            <div className="pt-2 flex justify-end">
              <Link
                to={`/claims/${encodeURIComponent(result.claim.claim_id)}`}
                className="inline-flex items-center gap-1.5 text-xs font-bold text-sky-600 hover:text-sky-800 hover:underline"
              >
                Inspect Full 7-Stage Audit Trail &rarr;
              </Link>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
export default ExtractVerifyForm
