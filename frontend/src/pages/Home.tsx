import { useState, useEffect } from 'react'
import { getHealth } from '../api/client'
import ExtractVerifyForm from '../components/ExtractVerifyForm'
import type { HealthStatus } from '../types'

const SAMPLE_TEXT = `HOUSTON METHODIST HOSPITAL - HOUSTON, TX
Patient Account: #HM-2024-089321

ITEMIZED BILL SUMMARY
───────────────────────────────────────────
CPT 70551  MRI Brain w/o Contrast               $1,100.00
CPT 99285  Emergency Dept Visit - Level 5        $2,850.00
CPT 36415  Routine Venipuncture                    $125.00
CPT 80053  Comprehensive Metabolic Panel           $340.00
CPT 71046  Chest X-Ray 2 Views                    $480.00
───────────────────────────────────────────
Subtotal:                                        $4,895.00
Insurance Adjustment:                           -$1,200.00
Patient Responsibility:                          $3,695.00

Note: MRI Brain (CPT 70551) billed at $1,100 — national average for Houston TX market is $520–$680. Please review for cost anomaly.`

type HealthState =
  | { status: 'loading' }
  | { status: 'ok'; data: HealthStatus }
  | { status: 'error'; message: string }

export default function Home() {
  const [health, setHealth] = useState<HealthState>({ status: 'loading' })
  const [sampleLoaded, setSampleLoaded] = useState(false)

  useEffect(() => {
    let cancelled = false
    getHealth()
      .then((data) => {
        if (!cancelled) setHealth({ status: 'ok', data })
      })
      .catch((err: unknown) => {
        if (!cancelled)
          setHealth({
            status: 'error',
            message: err instanceof Error ? err.message : 'Backend unreachable',
          })
      })
    return () => { cancelled = true }
  }, [])

  return (
    <div className="max-w-3xl mx-auto py-10 px-4">
      {/* Health status bar */}
      <div className="mb-6">
        {health.status === 'loading' && (
          <div className="flex items-center gap-2 text-sm text-slate-400 bg-slate-100 rounded-lg px-4 py-2">
            <span className="inline-block w-2 h-2 rounded-full bg-slate-300 animate-pulse" />
            Checking backend status…
          </div>
        )}
        {health.status === 'ok' && (
          <div className="flex items-center gap-2 text-sm text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-lg px-4 py-2">
            <span className="inline-block w-2 h-2 rounded-full bg-emerald-500" />
            <span>
              Backend online &mdash;{' '}
              <span className="font-medium">{health.data.app_name}</span>{' '}
              v{health.data.version}
            </span>
            <span className="ml-auto text-emerald-600 font-mono text-xs">
              Status: {health.data.status}
            </span>
          </div>
        )}
        {health.status === 'error' && (
          <div className="flex items-center gap-2 text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-4 py-2">
            <span className="inline-block w-2 h-2 rounded-full bg-red-500" />
            Backend unavailable — {health.message}
          </div>
        )}
      </div>

      {/* Page heading */}
      <div className="mb-8 text-center">
        <h1 className="text-3xl font-bold text-slate-900 mb-2">
          Submit Clinical Text for Audit
        </h1>
        <p className="text-slate-500 text-base max-w-xl mx-auto">
          Paste a hospital bill, clinical note, or insurance claim. EvidenceBridge
          will extract structured claims, verify them against evidence, detect cost
          anomalies, and return a full audit trail.
        </p>
      </div>

      {/* Sample text button */}
      <div className="mb-6 flex justify-center">
        <button
          type="button"
          onClick={() => setSampleLoaded(true)}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-slate-300 bg-white text-slate-700 text-sm font-medium hover:bg-slate-50 hover:border-slate-400 transition-colors shadow-sm"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="h-4 w-4 text-slate-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
          </svg>
          Try a sample hospital bill
        </button>
      </div>

      {/* Main form */}
      <ExtractVerifyForm
        initialText={sampleLoaded ? SAMPLE_TEXT : ''}
        onSampleCleared={() => setSampleLoaded(false)}
      />
    </div>
  )
}
