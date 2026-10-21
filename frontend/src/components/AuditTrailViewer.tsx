import React, { useState } from 'react'
import type { AuditTrail, DecisionStep, EvidencePassage } from '../types'
import { VerificationBadge, VerdictBadge } from './VerificationBadge'

interface AuditTrailViewerProps {
  auditTrail: AuditTrail
}

export function AuditTrailViewer({ auditTrail }: AuditTrailViewerProps) {
  const [expandedSteps, setExpandedSteps] = useState<Record<number, boolean>>({ 0: true })
  const [showAllPassages, setShowAllPassages] = useState(false)

  const toggleStep = (idx: number) => {
    setExpandedSteps((prev) => ({ ...prev, [idx]: !prev[idx] }))
  }

  const steps: DecisionStep[] = auditTrail.steps || []
  const passages: EvidencePassage[] = auditTrail.passages_considered || []

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
      {/* Header */}
      <div className="px-6 py-4 bg-slate-50 border-b border-slate-200 flex flex-col sm:flex-row justify-between sm:items-center gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-base font-bold text-slate-900">Decision Audit Graph</h3>
            <span className="font-mono text-xs px-2 py-0.5 rounded bg-slate-200 text-slate-700">
              {auditTrail.audit_id}
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Deterministic 7-stage traceable verification trail
          </p>
        </div>

        <div className="flex items-center gap-2">
          <VerificationBadge action={auditTrail.final_action} size="sm" />
          <VerdictBadge verdict={auditTrail.final_verdict} />
        </div>
      </div>

      {/* Final Decision Rationale */}
      <div className="px-6 py-4 bg-sky-50/50 border-b border-sky-100">
        <div className="text-xs font-semibold text-sky-800 uppercase tracking-wider mb-1">
          Final Audit Outcome
        </div>
        <p className="text-sm text-slate-800 leading-relaxed">
          {auditTrail.final_reasoning}
        </p>
        {auditTrail.abstain_triggered && (
          <div className="mt-2 text-xs text-amber-800 bg-amber-50 border border-amber-200 p-2 rounded">
            <strong>Abstention Triggered:</strong> {auditTrail.abstain_reason || 'Safety rule triggered'}
          </div>
        )}
      </div>

      {/* 7-Stage Decision Steps Timeline */}
      <div className="px-6 py-6 border-b border-slate-200">
        <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-4">
          Pipeline Execution Graph ({steps.length} Steps)
        </h4>

        <div className="relative border-l-2 border-slate-200 ml-4 space-y-6">
          {steps.map((step, idx) => {
            const isExpanded = !!expandedSteps[idx]
            return (
              <div key={idx} className="relative pl-6">
                {/* Timeline node */}
                <div
                  className={`absolute -left-[9px] top-1 w-4 h-4 rounded-full border-2 bg-white ${
                    step.step_name.includes('ABSTAIN')
                      ? 'border-amber-500'
                      : step.step_name.includes('FINAL')
                      ? 'border-emerald-500'
                      : 'border-sky-500'
                  }`}
                />

                <div className="bg-slate-50 rounded-lg border border-slate-200 p-3.5 hover:border-slate-300 transition-colors">
                  <div
                    className="flex items-center justify-between cursor-pointer select-none"
                    onClick={() => toggleStep(idx)}
                  >
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold text-slate-700 px-2 py-0.5 rounded bg-white border border-slate-200">
                        {step.step_name}
                      </span>
                      <span className="text-xs text-slate-500 font-mono">
                        {new Date(step.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                    <button
                      type="button"
                      className="text-xs text-sky-600 hover:text-sky-800 font-medium"
                    >
                      {isExpanded ? 'Hide' : 'Inspect'}
                    </button>
                  </div>

                  {/* Summary row */}
                  <div className="mt-2 text-xs text-slate-700">
                    <div>
                      <strong className="text-slate-500">Output:</strong> {step.output_summary}
                    </div>
                  </div>

                  {/* Expandable details */}
                  {isExpanded && (
                    <div className="mt-3 pt-3 border-t border-slate-200 text-xs space-y-1.5 font-mono bg-white p-2.5 rounded border border-slate-100">
                      <div>
                        <span className="text-slate-400">Input:</span> {step.input_summary}
                      </div>
                      {step.details && Object.keys(step.details).length > 0 && (
                        <div>
                          <span className="text-slate-400">Details:</span>
                          <pre className="text-[11px] text-slate-700 overflow-x-auto p-1.5 mt-1 bg-slate-50 rounded">
                            {JSON.stringify(step.details, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Considered Evidence Passages */}
      {passages.length > 0 && (
        <div className="px-6 py-6">
          <div className="flex items-center justify-between mb-4">
            <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider">
              Evidence Passages Evaluated ({passages.length})
            </h4>
            <button
              type="button"
              onClick={() => setShowAllPassages(!showAllPassages)}
              className="text-xs text-sky-600 hover:text-sky-800 font-medium"
            >
              {showAllPassages ? 'Collapse' : 'Show All'}
            </button>
          </div>

          <div className="space-y-3">
            {(showAllPassages ? passages : passages.slice(0, 3)).map((p, idx) => {
              const scorePct = Math.round(p.relevance_score * 100)
              const scoreColor =
                p.relevance_score >= 0.6
                  ? 'bg-emerald-500'
                  : p.relevance_score >= 0.35
                  ? 'bg-amber-500'
                  : 'bg-rose-400'

              return (
                <div
                  key={idx}
                  className={`p-3.5 rounded-lg border text-xs ${
                    p.used_in_decision
                      ? 'bg-white border-slate-200'
                      : 'bg-slate-50/70 border-slate-200 opacity-75'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2 mb-1.5">
                    <div className="font-semibold text-slate-900 truncate">
                      {p.title}
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <span className="text-[11px] text-slate-500">{p.source}</span>
                      {p.used_in_decision ? (
                        <span className="px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-800 text-[10px] font-bold">
                          USED
                        </span>
                      ) : (
                        <span className="px-1.5 py-0.5 rounded bg-slate-200 text-slate-600 text-[10px] font-medium">
                          DISCARDED
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Relevance Score Bar */}
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-[11px] text-slate-500 font-mono w-14">
                      Rel: {scorePct}%
                    </span>
                    <div className="flex-1 bg-slate-100 h-1.5 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${scoreColor}`}
                        style={{ width: `${Math.min(100, Math.max(0, scorePct))}%` }}
                      />
                    </div>
                  </div>

                  {/* Passage Text */}
                  <p className="text-slate-700 leading-relaxed text-[11px] line-clamp-3 bg-slate-50 p-2 rounded">
                    "{p.text}"
                  </p>

                  {p.discard_reason && (
                    <div className="mt-1.5 text-[11px] text-rose-600 italic">
                      Discard Reason: {p.discard_reason}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
export default AuditTrailViewer
