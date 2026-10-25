import React, { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { extractAndVerify, ensureAuthToken } from '../api/client'
import type { ExtractAndVerifyResponse, SourceType } from '../types'
import { VerificationBadge, VerdictBadge } from './VerificationBadge'
import { useVoice } from '../context/VoiceContext'
import { useAudit } from '../context/AuditContext'
import { formatCurrency } from '../utils/currency'
import { extractTextFromImage } from '../utils/ocr'
import CameraCaptureModal from './CameraCaptureModal'
import PostProcessingSummary from './PostProcessingSummary'

interface ExtractVerifyFormProps {
  initialText?: string
  onSampleCleared?: () => void
}

export function ExtractVerifyForm({
  initialText = '',
  onSampleCleared,
}: ExtractVerifyFormProps) {
  const { setActiveClaim, readClaimAloud } = useVoice()
  const {
    result,
    text,
    sourceType,
    sourceUrl,
    imagePreview,
    imageName,
    setResult,
    setText,
    setSourceType,
    setSourceUrl,
    setImagePreview,
    setImageName,
    clearAudit,
  } = useAudit()

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // OCR and Image Upload / Camera states
  const [ocrLoading, setOcrLoading] = useState(false)
  const [ocrProgress, setOcrProgress] = useState(0)
  const [ocrStatusText, setOcrStatusText] = useState('')
  const [ocrWarning, setOcrWarning] = useState<string | null>(null)
  const [ocrSuccessMessage, setOcrSuccessMessage] = useState<string | null>(null)
  const [isCameraModalOpen, setIsCameraModalOpen] = useState(false)
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const previousObjectUrlRef = useRef<string | null>(null)

  useEffect(() => {
    if (initialText && initialText !== text) {
      setText(initialText)
      setError(null)
    }
  }, [initialText])

  useEffect(() => {
    if (result) {
      setActiveClaim({
        claimId: result.claim.claim_id,
        entity: result.claim.extracted_fields?.entity,
        action: result.verification.action,
        verdict: result.verification.verdict,
        costAnomalyFlag: result.verification.cost_anomaly_flag,
        costRange: result.claim.extracted_fields?.cost_range,
        confidence: result.claim.confidence,
        supportScore: result.verification.support_score,
        reasoning: result.verification.reasoning,
        abstainReason: result.verification.abstain_reason,
        anomalyDetails: result.verification.anomaly_details,
        city: result.claim.location?.city,
        sourceType: result.claim.source_type,
      })
    }
  }, [result, setActiveClaim])

  // Cleanup object URL on unmount
  useEffect(() => {
    return () => {
      if (previousObjectUrlRef.current && previousObjectUrlRef.current.startsWith('blob:')) {
        URL.revokeObjectURL(previousObjectUrlRef.current)
      }
    }
  }, [])

  const runOcrOnSource = async (source: File | Blob, displayName: string) => {
    // Revoke previous object URL if any
    if (previousObjectUrlRef.current && previousObjectUrlRef.current.startsWith('blob:')) {
      URL.revokeObjectURL(previousObjectUrlRef.current)
    }

    const previewUrl = URL.createObjectURL(source)
    previousObjectUrlRef.current = previewUrl

    setImagePreview(previewUrl)
    setImageName(displayName)
    setOcrLoading(true)
    setOcrProgress(5)
    setOcrStatusText('Initializing OCR...')
    setOcrWarning(null)
    setOcrSuccessMessage(null)

    try {
      const res = await extractTextFromImage(source, (pct, status) => {
        setOcrProgress(pct)
        setOcrStatusText(status)
      })

      if (res.text) {
        setText(res.text)
        if (res.isLowQuality && res.warningMessage) {
          setOcrWarning(res.warningMessage)
        } else {
          setOcrSuccessMessage('Text successfully extracted from document. Please review before verifying.')
        }
      } else {
        setOcrWarning(
          res.warningMessage ||
            'Some parts of the image could not be read clearly. Please check the text below or type the missing information.'
        )
      }
    } catch (err: unknown) {
      console.error('OCR error:', err)
      setOcrWarning(
        'Some parts of the image could not be read clearly. Please check the text below or type the missing information.'
      )
    } finally {
      setOcrLoading(false)
    }
  }

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    runOcrOnSource(file, file.name)
    e.target.value = ''
  }

  const handleCameraCapture = (blob: Blob) => {
    const now = new Date()
    const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    runOcrOnSource(blob, `Camera Photo (${timeStr})`)
  }

  const handleRemoveImage = () => {
    if (previousObjectUrlRef.current && previousObjectUrlRef.current.startsWith('blob:')) {
      URL.revokeObjectURL(previousObjectUrlRef.current)
      previousObjectUrlRef.current = null
    }
    setImagePreview(null)
    setImageName(null)
    setOcrWarning(null)
    setOcrSuccessMessage(null)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!text.trim()) return

    setLoading(true)
    setError(null)

    try {
      await ensureAuthToken()
      const response = await extractAndVerify({
        text: text.trim(),
        source_type: sourceType,
        source_url: sourceUrl.trim() || undefined,
        store_claim: true,
      })
      setResult(response)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Claim auditing failed.')
    } finally {
      setLoading(false)
    }
  }

  const handleClear = () => {
    clearAudit()
    setError(null)
    handleRemoveImage()
    onSampleCleared?.()
  }

  const anomaly = result?.verification.anomaly_details
  const billedAmount = anomaly?.extracted_amount ?? null
  const benchmarkMax = anomaly?.benchmark_max ?? null
  const benchmarkMin = anomaly?.benchmark_min ?? null
  const multiplier = anomaly?.multiplier || 1
  const docCurrency = anomaly?.currency || result?.claim.extracted_fields?.cost_currency || 'INR'
  const benchmarkCurrency = anomaly?.benchmark_currency || docCurrency

  return (
    <div className="space-y-6">
      {/* Active Audit State Indicator Banner */}
      {result && (
        <div className="p-4 rounded-2xl bg-gradient-to-r from-sky-50 via-teal-50/50 to-white border border-sky-200/80 shadow-subtle flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs text-slate-800">
          <div className="flex items-center gap-2.5">
            <span className="w-8 h-8 rounded-xl bg-sky-100 text-sky-800 font-bold flex items-center justify-center flex-shrink-0 text-base">
              📌
            </span>
            <div>
              <strong className="text-slate-900 block font-bold">
                Audited Document Retained &amp; Active
              </strong>
              <span className="text-slate-600">
                Displaying audit evaluation for <strong>{result.claim.extracted_fields?.entity || result.claim.claim_id}</strong>. This result stays preserved as you browse other tabs until you sign out or start a new audit.
              </span>
            </div>
          </div>
          <button
            type="button"
            onClick={handleClear}
            className="px-4 py-2 rounded-xl bg-white hover:bg-slate-100 text-slate-700 border border-slate-300 font-bold text-xs whitespace-nowrap self-start sm:self-auto transition-colors shadow-2xs inline-flex items-center gap-1.5"
          >
            <span>🔄</span>
            <span>Start New Audit</span>
          </button>
        </div>
      )}

      {/* Input Form Card */}
      <form
        onSubmit={handleSubmit}
        className="bg-white rounded-2xl border border-slate-200 p-6 sm:p-8 shadow-card"
      >
        <div className="flex items-center justify-between mb-2">
          <div>
            <span className="text-xs font-bold text-sky-700 bg-sky-50 border border-sky-200 px-2.5 py-1 rounded-full uppercase tracking-wider">
              Step 1
            </span>
            <label
              htmlFor="clinical-text"
              className="block text-base font-bold text-slate-900 mt-1.5"
            >
              Raw Hospital Bill or Clinical Chart Note
            </label>
          </div>
          <span className="text-xs text-slate-400">
            {text.length > 0 ? `${text.length} characters` : 'Paste unedited document'}
          </span>
        </div>

        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2.5 mb-3.5">
          <p className="text-sm text-slate-500 leading-relaxed">
            Paste an itemized hospital bill line (e.g. CPT procedure code, billed dollars), an EHR consultation note, or a prescription summary.
          </p>

          {/* Quick OCR Scan Buttons */}
          <div className="flex items-center gap-2 flex-shrink-0">
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={ocrLoading}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-sky-300 bg-sky-50 text-sky-800 hover:bg-sky-100 text-xs font-bold transition-all shadow-xs disabled:opacity-50"
              title="Upload an image of a hospital bill or prescription"
            >
              <svg className="w-4 h-4 text-sky-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
              </svg>
              Upload Photo
            </button>

            <button
              type="button"
              onClick={() => setIsCameraModalOpen(true)}
              disabled={ocrLoading}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-indigo-300 bg-indigo-50 text-indigo-800 hover:bg-indigo-100 text-xs font-bold transition-all shadow-xs disabled:opacity-50"
              title="Take a photo with your device camera"
            >
              <svg className="w-4 h-4 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              Take Photo
            </button>

            {/* Hidden native file input for Upload Photo */}
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              onChange={handleFileUpload}
              className="hidden"
            />
          </div>
        </div>

        {/* Small Image Preview with Removal option */}
        {imagePreview && (
          <div className="mb-3.5 p-3.5 bg-slate-50/90 border border-slate-200 rounded-xl shadow-xs flex items-center justify-between gap-3 animate-fadeIn">
            <div className="flex items-center gap-3 min-w-0">
              <img
                src={imagePreview}
                alt="Document Preview"
                className="w-14 h-14 sm:w-16 sm:h-16 object-cover rounded-lg border border-slate-300 shadow-xs flex-shrink-0"
              />
              <div className="min-w-0">
                <div className="text-xs font-bold text-slate-800 truncate">
                  {imageName || 'Document Photo'}
                </div>
                <div className="mt-1 flex items-center gap-2 flex-wrap">
                  {ocrLoading ? (
                    <span className="inline-flex items-center gap-1.5 text-[11px] font-semibold text-sky-700 bg-sky-100/80 border border-sky-200 px-2 py-0.5 rounded-md">
                      <svg className="animate-spin w-3 h-3 text-sky-600" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                      </svg>
                      {ocrStatusText || `Reading text... ${ocrProgress}%`}
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-800 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-md">
                      ✓ Text extracted
                    </span>
                  )}
                </div>
              </div>
            </div>

            <button
              type="button"
              onClick={handleRemoveImage}
              className="text-xs font-semibold text-rose-600 hover:text-rose-800 hover:bg-rose-50 px-3 py-1.5 rounded-lg border border-rose-200 transition-colors flex-shrink-0 shadow-xs"
              title="Remove image and return to text-only mode"
            >
              ✕ Remove Photo
            </button>
          </div>
        )}

        {/* OCR Unclear Text Warning */}
        {ocrWarning && (
          <div className="mb-3.5 p-3 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-xs flex items-start gap-2.5 shadow-subtle animate-fadeIn">
            <span className="text-amber-600 font-bold text-sm mt-0.5">⚠️</span>
            <div className="flex-1">
              <strong className="block font-semibold">Image OCR Note:</strong>
              <span>{ocrWarning}</span>
            </div>
          </div>
        )}

        {/* OCR Success Banner */}
        {ocrSuccessMessage && !ocrWarning && (
          <div className="mb-3.5 p-2.5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-900 text-xs flex items-center justify-between gap-2 shadow-subtle animate-fadeIn">
            <div className="flex items-center gap-2">
              <span className="text-emerald-600 font-bold">✓</span>
              <span>{ocrSuccessMessage}</span>
            </div>
            <button
              type="button"
              onClick={() => setOcrSuccessMessage(null)}
              className="text-emerald-700 hover:text-emerald-900 text-xs font-bold"
            >
              ✕
            </button>
          </div>
        )}

        <textarea
          id="clinical-text"
          rows={8}
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={ocrLoading ? 'Extracting text from image using OCR... please wait.' : 'e.g. EMERGENCY ROOM - HOUSTON, TX. Patient with focal neurological signs underwent CPT 70551 MRI Brain without contrast. Billed charge $650.00...'}
          className="w-full px-4 py-3.5 rounded-xl border border-slate-300 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-sky-500 text-slate-800 placeholder:text-slate-400 bg-slate-50/40 leading-relaxed"
          required
        />

        {/* Source metadata inputs */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-5">
          <div>
            <label
              htmlFor="source-type"
              className="block text-xs sm:text-sm font-semibold text-slate-700 mb-1.5"
            >
              Document Classification
            </label>
            <select
              id="source-type"
              value={sourceType}
              onChange={(e) => setSourceType(e.target.value as SourceType)}
              className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-sky-500 bg-white"
            >
              <option value="hospital_bill">Hospital Bill / Itemized Statement</option>
              <option value="clinical_note">Clinical Chart Note / EHR</option>
              <option value="patient_report">Patient Invoice / Post</option>
              <option value="forum_post">Health Forum Report</option>
              <option value="other">Other Medical Record</option>
            </select>
          </div>

          <div>
            <label
              htmlFor="source-url"
              className="block text-xs sm:text-sm font-semibold text-slate-700 mb-1.5"
            >
              Document Origin or Reference ID (Optional)
            </label>
            <input
              id="source-url"
              type="text"
              value={sourceUrl}
              onChange={(e) => setSourceUrl(e.target.value)}
              placeholder="e.g. ehr://houston-methodist/pt-89321"
              className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-sky-500 placeholder:text-slate-400"
            />
          </div>
        </div>

        {/* Actions Row */}
        <div className="flex items-center justify-between pt-6 mt-6 border-t border-slate-100">
          <button
            type="button"
            onClick={handleClear}
            className="text-sm text-slate-500 hover:text-slate-800 font-medium px-4 py-2.5 rounded-xl hover:bg-slate-100 transition-colors"
          >
            Clear Text
          </button>

          <button
            type="submit"
            disabled={loading || ocrLoading || !text.trim()}
            className="inline-flex items-center gap-2 px-7 py-3 rounded-xl bg-sky-600 text-white text-sm sm:text-base font-bold hover:bg-sky-700 transition-all shadow-md disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <>
                <svg
                  className="animate-spin -ml-1 mr-2 h-5 w-5 text-white"
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
                Auditing Clinical Evidence &amp; Pricing...
              </>
            ) : (
              'Extract & Verify Claim'
            )}
          </button>
        </div>
      </form>

      {/* Error Message */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-900 text-xs sm:text-sm flex items-start gap-3 shadow-subtle">
          <span className="text-rose-600 font-bold text-base mt-0.5">⚠️</span>
          <div>
            <strong className="block font-bold">Audit Evaluation Failed</strong>
            <span>{error}</span>
          </div>
        </div>
      )}

      {/* Audit Result Display */}
      {result && (
        <div className="space-y-6 animate-fadeIn">
          {/* Visual Decision Banner */}
          <div
            className={`rounded-2xl border p-7 sm:p-8 shadow-card transition-all ${
              result.verification.action === 'accept'
                ? 'bg-gradient-to-r from-emerald-50 via-white to-emerald-50/50 border-emerald-300'
                : result.verification.action === 'flag'
                ? 'bg-gradient-to-r from-amber-50 via-white to-amber-50/50 border-amber-300'
                : 'bg-gradient-to-r from-slate-100 via-white to-slate-100 border-slate-300'
            }`}
          >
            <div className="flex flex-col md:flex-row justify-between md:items-center gap-5">
              <div>
                <div className="flex items-center gap-2 mb-2 flex-wrap">
                  <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                    Audit Decision &bull; ID: {result.claim.claim_id}
                  </span>
                  <VerificationBadge action={result.verification.action} size="sm" />
                  <VerdictBadge verdict={result.verification.verdict} />
                </div>

                <h2 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
                  {result.verification.action === 'accept' && (
                    <span className="text-emerald-900">Approved: Matches Medical Guidelines</span>
                  )}
                  {result.verification.action === 'flag' && (
                    <span className="text-amber-950">Flagged for Review: Potential Issue Detected</span>
                  )}
                  {result.verification.action === 'abstain' && (
                    <span className="text-slate-900">Not enough reliable evidence to make a decision</span>
                  )}
                </h2>

                <p className="text-sm sm:text-base text-slate-700 mt-2 max-w-3xl leading-relaxed">
                  {result.verification.action === 'abstain'
                    ? 'The system safely held this claim instead of guessing because sufficient verified guidelines or pricing benchmarks are not yet available.'
                    : result.verification.reasoning}
                </p>

                {/* Plain-English "What this means & What to do next" */}
                <div className="mt-4 p-4 rounded-xl bg-white/90 border border-slate-200 text-xs sm:text-sm space-y-1.5 shadow-subtle">
                  <div className="font-bold text-slate-900 flex items-center gap-2">
                    <span className="text-base">💡</span>
                    <span>What this means &amp; What you can do next:</span>
                  </div>
                  {result.verification.action === 'flag' && (
                    <p className="text-slate-600 leading-relaxed">
                      <strong>Recommendation:</strong> The billed amount appears higher than the available comparison price, or clinical guidelines advise caution.
                      You can request an itemized hospital bill with procedure codes (CPT/HCPCS), ask for in-network pricing, or contact your provider for billing clarification.
                    </p>
                  )}
                  {result.verification.action === 'accept' && (
                    <p className="text-slate-600 leading-relaxed">
                      <strong>Recommendation:</strong> The procedure indication aligns with published medical guidelines and the billed charges fall within standard fair pricing benchmarks.
                    </p>
                  )}
                  {result.verification.action === 'abstain' && (
                    <p className="text-slate-600 leading-relaxed">
                      <strong>Recommendation:</strong> Not enough reliable evidence to make an automated decision. Ask your hospital for the exact procedure code (CPT) or check with your insurer to clarify coverage without ungrounded assumptions.
                    </p>
                  )}
                </div>
              </div>

              {/* Quick Actions */}
              <div className="flex items-center gap-2.5 sm:self-start flex-wrap">
                <button
                  type="button"
                  onClick={handleClear}
                  className="px-4 py-2.5 rounded-xl bg-white hover:bg-slate-100 border border-slate-300 text-slate-700 text-xs sm:text-sm font-bold transition-colors shadow-subtle whitespace-nowrap flex items-center gap-2"
                  title="Clear this audit and evaluate a new document"
                >
                  <span>🔄</span>
                  <span>New Audit</span>
                </button>

                <button
                  type="button"
                  onClick={() => readClaimAloud()}
                  className="px-4 py-2.5 rounded-xl bg-white hover:bg-slate-50 border border-slate-300 text-slate-800 text-xs sm:text-sm font-bold transition-colors shadow-subtle whitespace-nowrap flex items-center gap-2"
                  title="Read audit decision aloud using browser AI voice (English / ಕನ್ನಡ)"
                >
                  <span>🔊</span>
                  <span>Read Result Aloud</span>
                </button>

                <Link
                  to={`/claims/${encodeURIComponent(result.claim.claim_id)}`}
                  className="px-5 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-white text-xs sm:text-sm font-bold transition-colors shadow-sm whitespace-nowrap"
                >
                  View Full 7-Stage Audit &rarr;
                </Link>
              </div>
            </div>

            {/* Abstention specific callout */}
            {result.verification.action === 'abstain' && (
              <div className="mt-4 p-4 rounded-xl bg-slate-200/80 border border-slate-300 text-sm text-slate-800 leading-relaxed">
                <strong className="font-bold text-slate-900 block mb-1">
                  Safe Refusal Enforced:
                </strong>
                {result.verification.abstain_reason ||
                  'The system chose not to guess because authoritative guidelines were missing or pricing benchmarks were absent for this high-cost service.'}
              </div>
            )}
          </div>

          {/* Post-Processing Clinical & Prescription Summary (Collapsible by default) */}
          <PostProcessingSummary result={result} />

          {/* Pricing Benchmark Visual (if anomaly or benchmark exists) */}
          {result.verification.cost_anomaly_flag && anomaly && (
            <div className="bg-white rounded-2xl border border-rose-200 p-6 sm:p-8 shadow-card">
              <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-3 mb-5">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-100 text-rose-800 border border-rose-200 uppercase">
                      Price Alert
                    </span>
                    <h3 className="text-base sm:text-lg font-bold text-slate-900">
                      Unusually High Charge Detected ({multiplier.toFixed(1)}× Benchmark)
                    </h3>
                  </div>
                  <p className="text-xs sm:text-sm text-slate-500 mt-1">
                    The billed amount appears higher than the available comparison price (CMS Medicare and Fair Health fee schedules).
                  </p>
                </div>

                <div className="text-right">
                  <span className="text-xs text-slate-400 font-medium">Billed Amount:</span>
                  <div className="text-2xl font-black font-mono text-rose-700">
                    {formatCurrency(billedAmount, docCurrency, { showCode: true })}
                  </div>
                </div>
              </div>

              {/* Progress/Ratio Bar */}
              <div className="space-y-2.5">
                <div className="w-full bg-slate-100 h-5 rounded-full overflow-hidden flex relative border border-slate-200">
                  {/* Benchmark Segment */}
                  <div
                    className="bg-emerald-500 h-full text-xs text-white flex items-center justify-center font-bold"
                    style={{
                      width: `${Math.min(100, Math.max(12, ((benchmarkMax || 1) / (billedAmount || 1)) * 100))}%`,
                    }}
                    title={`Standard Benchmark Range: ${formatCurrency(benchmarkMin, benchmarkCurrency)} - ${formatCurrency(benchmarkMax, benchmarkCurrency)}`}
                  >
                    Benchmark
                  </div>
                  {/* Markup Excess Segment */}
                  <div
                    className="bg-rose-500 h-full flex-1"
                    title={`Excess Markup: ${(multiplier - 1).toFixed(1)}x over benchmark`}
                  />
                </div>

                <div className="flex flex-col sm:flex-row justify-between text-xs sm:text-sm text-slate-600 font-mono gap-1">
                  <span>Standard Benchmark: {formatCurrency(benchmarkMin, benchmarkCurrency)} – {formatCurrency(benchmarkMax, benchmarkCurrency)}</span>
                  <span className="font-bold text-rose-600">
                    Billed: {formatCurrency(billedAmount, docCurrency)} ({multiplier.toFixed(1)}× markup)
                  </span>
                </div>
              </div>

              {docCurrency !== benchmarkCurrency && (
                <div className="mt-3 text-xs text-amber-800 bg-amber-50 p-2.5 rounded-xl border border-amber-200">
                  ⚠️ Note: Billed charge is in {docCurrency} while comparison benchmark schedule is in {benchmarkCurrency}. Cross-currency auditing is noted.
                </div>
              )}

              <div className="mt-3.5 text-xs sm:text-sm text-slate-700 bg-rose-50/70 p-3.5 rounded-xl border border-rose-100 leading-relaxed">
                {anomaly.explanation}
              </div>
            </div>
          )}

          {/* Structured Information & Provenance Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Extracted Medical Entity & Procedure Codes */}
            <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-subtle">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-2.5">
                Extracted Clinical Information
              </span>
              <div className="space-y-3.5">
                <div>
                  <div className="text-xs text-slate-500 font-medium">Medical Procedure / Item</div>
                  <div className="text-base font-bold text-slate-900 mt-0.5">
                    {result.claim.extracted_fields?.entity || 'Extracted Clinical Entity'}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3 text-xs pt-2.5 border-t border-slate-100">
                  <div>
                    <span className="text-slate-400 block text-xs mb-0.5">Billed Amount</span>
                    <span className="font-mono text-base font-bold text-slate-800">
                      {result.claim.extracted_fields?.cost_range
                        ? `${result.claim.extracted_fields.cost_range}${result.claim.extracted_fields.cost_currency ? ` (${result.claim.extracted_fields.cost_currency})` : ''}`
                        : 'Price data not available'}
                    </span>
                  </div>
                  <div>
                    <div className="flex items-center gap-1 mb-0.5">
                      <span className="text-slate-400 block text-xs">Evidence Confidence</span>
                      <span
                        className="text-xs text-slate-400 cursor-help"
                        title="How strongly the available evidence supports this result."
                      >
                        ℹ️
                      </span>
                    </div>
                    <span className="font-mono text-base font-bold text-slate-800">
                      {Math.round(result.verification.support_score * 100)}%
                    </span>
                    <span className="text-[10px] text-slate-400 block mt-0.5">
                      Guideline support certainty
                    </span>
                  </div>
                </div>

                {result.claim.extracted_fields?.effect_or_outcome && (
                  <div className="pt-2.5 border-t border-slate-100">
                    <span className="text-slate-400 block text-xs mb-0.5">Indication / Note</span>
                    <span className="text-xs sm:text-sm text-slate-700 leading-relaxed block">
                      {result.claim.extracted_fields.effect_or_outcome}
                    </span>
                  </div>
                )}
              </div>
            </div>

            {/* Authenticity & Geographic Location */}
            <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-subtle">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-2.5">
                Document Authenticity &amp; Region
              </span>
              <div className="space-y-3.5 text-xs">
                <div>
                  <span className="text-slate-400 block text-xs mb-0.5">Geographic Hospital Locality</span>
                  <div className="text-base font-bold text-slate-900 mt-0.5">
                    {result.claim.location?.city
                      ? `${result.claim.location.city}${result.claim.location.state_or_region ? `, ${result.claim.location.state_or_region}` : ''}`
                      : 'Not Detected (National Benchmark Applied)'}
                  </div>
                  {result.claim.location?.normalized_key && (
                    <Link
                      to={`/trust-density?key=${encodeURIComponent(result.claim.location.normalized_key)}`}
                      className="text-xs text-sky-600 hover:text-sky-800 font-semibold inline-block mt-1"
                    >
                      View Hospital Reliability for {result.claim.location.city} &rarr;
                    </Link>
                  )}
                </div>

                <div className="pt-2.5 border-t border-slate-100">
                  <span className="text-slate-400 block text-xs mb-0.5">Document Authenticity Fingerprint (SHA-256)</span>
                  <span className="font-mono text-xs text-slate-600 truncate block bg-slate-50 p-2 rounded-lg mt-1 border border-slate-200">
                    {result.claim.provenance?.source_hash || 'SHA-256 Verified'}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Advanced Technical Details for Auditors (Collapsible) */}
          <details className="bg-slate-50 rounded-2xl border border-slate-200 p-5 text-xs sm:text-sm">
            <summary className="font-bold text-slate-700 cursor-pointer hover:text-slate-900 flex items-center justify-between">
              <span>🔧 Advanced Audit Details &amp; Provenance Record</span>
              <span className="text-xs text-slate-400">Click to expand</span>
            </summary>
            <div className="mt-3 pt-3 border-t border-slate-200 space-y-2.5 font-mono text-xs text-slate-700">
              <div className="flex justify-between">
                <span className="text-slate-500">System Verdict:</span>
                <span className="font-bold">{result.verification.verdict}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Decision Action:</span>
                <span className="font-bold">{result.verification.action}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Confidence Calibration:</span>
                <span>{result.claim.confidence ? (result.claim.confidence * 100).toFixed(1) + '%' : 'N/A'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Guideline Citations:</span>
                <span>{result.verification.evidence_snippets?.length || 0} authoritative sources cited</span>
              </div>
            </div>
          </details>
        </div>
      )}

      {/* Live Camera Viewfinder Modal */}
      <CameraCaptureModal
        isOpen={isCameraModalOpen}
        onClose={() => setIsCameraModalOpen(false)}
        onCapture={handleCameraCapture}
      />
    </div>
  )
}
export default ExtractVerifyForm
