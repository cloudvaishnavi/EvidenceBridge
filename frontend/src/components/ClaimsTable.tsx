import React from 'react'
import { Link } from 'react-router-dom'
import type { Claim, VerificationResult } from '../types'
import { VerificationBadge, VerdictBadge } from './VerificationBadge'

interface ClaimsTableProps {
  claims: Claim[]
  verifications?: Record<string, VerificationResult>
}

export function ClaimsTable({ claims, verifications = {} }: ClaimsTableProps) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
            <tr>
              <th className="px-6 py-3">Claim ID</th>
              <th className="px-6 py-3">Entity</th>
              <th className="px-6 py-3">Type</th>
              <th className="px-6 py-3">Location</th>
              <th className="px-6 py-3">Billed</th>
              <th className="px-6 py-3">Action</th>
              <th className="px-6 py-3">Verdict</th>
              <th className="px-6 py-3 text-right">Inspect</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {claims.map((claim) => {
              const v = verifications[claim.claim_id]
              const loc = claim.location

              return (
                <tr
                  key={claim.claim_id}
                  className="hover:bg-slate-50 transition-colors"
                >
                  <td className="px-6 py-3.5 font-mono text-slate-600 font-medium">
                    {claim.claim_id}
                  </td>
                  <td className="px-6 py-3.5 font-semibold text-slate-900 max-w-xs truncate">
                    {claim.extracted_fields?.entity}
                  </td>
                  <td className="px-6 py-3.5 text-slate-500 capitalize">
                    {claim.source_type.replace(/_/g, ' ')}
                  </td>
                  <td className="px-6 py-3.5 text-slate-700">
                    {loc ? `${loc.city}${loc.state_or_region ? `, ${loc.state_or_region}` : ''}` : '—'}
                  </td>
                  <td className="px-6 py-3.5 font-mono font-bold text-slate-800">
                    {claim.extracted_fields?.cost_range || '—'}
                  </td>
                  <td className="px-6 py-3.5">
                    {v ? <VerificationBadge action={v.action} size="sm" /> : <span className="text-slate-400">—</span>}
                  </td>
                  <td className="px-6 py-3.5">
                    {v ? <VerdictBadge verdict={v.verdict} /> : <span className="text-slate-400">—</span>}
                  </td>
                  <td className="px-6 py-3.5 text-right">
                    <Link
                      to={`/claims/${encodeURIComponent(claim.claim_id)}`}
                      className="font-semibold text-sky-600 hover:text-sky-800"
                    >
                      View &rarr;
                    </Link>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
export default ClaimsTable
