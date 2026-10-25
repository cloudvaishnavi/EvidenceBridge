import React, { useState, useEffect } from 'react'
import { listClaims, getVerification } from '../api/client'
import type { Claim, VerificationResult } from '../types'
import { ClaimCard } from '../components/ClaimCard'

export default function Claims() {
  const [claims, setClaims] = useState<Claim[]>([])
  const [verifications, setVerifications] = useState<Record<string, VerificationResult>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [total, setTotal] = useState(0)
  const [skip, setSkip] = useState(0)
  const limit = 20

  // Filter state
  const [actionFilter, setActionFilter] = useState<'all' | 'accept' | 'flag' | 'abstain'>('all')
  const [anomalyOnly, setAnomalyOnly] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [locationQuery, setLocationQuery] = useState('')

  const loadClaims = async (currentSkip: number, locFilter?: string) => {
    setLoading(true)
    setError(null)
    try {
      const res = await listClaims({
        limit,
        skip: currentSkip,
        location: locFilter?.trim() || undefined,
      })
      setClaims(res.claims)
      setTotal(res.total)

      // Fetch verifications for all retrieved claims
      const verifMap: Record<string, VerificationResult> = {}
      await Promise.allSettled(
        res.claims.map(async (c) => {
          try {
            const v = await getVerification(c.claim_id)
            if (v) verifMap[c.claim_id] = v
          } catch {
            // Unverified claim or offline is expected
          }
        })
      )
      setVerifications(verifMap)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load claims.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadClaims(skip, locationQuery)
  }, [skip])

  const handleLocationSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setSkip(0)
    loadClaims(0, locationQuery)
  }

  // Client-side filtering for action, anomaly, and free text search
  const filteredClaims = claims.filter((c) => {
    const v = verifications[c.claim_id]

    if (actionFilter !== 'all') {
      if (!v || v.action.toLowerCase() !== actionFilter) {
        return false
      }
    }

    if (anomalyOnly) {
      if (!v || !v.cost_anomaly_flag) {
        return false
      }
    }

    if (searchQuery.trim()) {
      const q = searchQuery.trim().toLowerCase()
      const entity = (c.extracted_fields?.entity || '').toLowerCase()
      const text = c.original_text.toLowerCase()
      const outcome = (c.extracted_fields?.effect_or_outcome || '').toLowerCase()
      if (!entity.includes(q) && !text.includes(q) && !outcome.includes(q)) {
        return false
      }
    }

    return true
  })

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Page Header */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 sm:p-7 shadow-card">
        <div className="flex flex-col md:flex-row justify-between md:items-center gap-4 mb-6">
          <div>
            <div className="inline-flex items-center gap-2 px-2.5 py-0.5 rounded-full bg-sky-50 text-sky-800 text-[11px] font-bold uppercase tracking-wider mb-1.5 border border-sky-200">
              Audit Database
            </div>
            <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
              Hospital Claims Explorer
            </h1>
            <p className="text-xs sm:text-sm text-slate-500 mt-1 max-w-xl">
              Inspect all audited medical bills, clinical chart records, and price anomaly flags with complete cryptographic provenance.
            </p>
          </div>

          <div className="text-right sm:self-start bg-slate-50 px-4 py-3 rounded-xl border border-slate-200">
            <span className="text-[10px] uppercase font-bold text-slate-400 block">Total Ingested</span>
            <span className="text-xl font-black font-mono text-slate-800">
              {total} Claim{total === 1 ? '' : 's'}
            </span>
          </div>
        </div>

        {/* Filter Controls Row */}
        <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-4 pt-5 border-t border-slate-100">
          {/* Action Filter Pills */}
          <div className="flex items-center gap-1.5 bg-slate-100/80 p-1 rounded-xl flex-wrap">
            <button
              type="button"
              onClick={() => setActionFilter('all')}
              className={`px-3 py-1.5 text-xs font-bold rounded-lg transition-colors ${
                actionFilter === 'all'
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              All Claims
            </button>
            <button
              type="button"
              onClick={() => setActionFilter('accept')}
              className={`px-3 py-1.5 text-xs font-bold rounded-lg transition-colors ${
                actionFilter === 'accept'
                  ? 'bg-emerald-600 text-white shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              ✓ Approved
            </button>
            <button
              type="button"
              onClick={() => setActionFilter('flag')}
              className={`px-3 py-1.5 text-xs font-bold rounded-lg transition-colors ${
                actionFilter === 'flag'
                  ? 'bg-amber-500 text-white shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              ! Flagged for Review
            </button>
            <button
              type="button"
              onClick={() => setActionFilter('abstain')}
              className={`px-3 py-1.5 text-xs font-bold rounded-lg transition-colors ${
                actionFilter === 'abstain'
                  ? 'bg-slate-700 text-white shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              ⏸ Held for Info
            </button>
          </div>

          {/* Search Inputs */}
          <div className="flex items-center gap-3 flex-wrap">
            <label className="inline-flex items-center gap-2 text-xs font-bold text-slate-700 cursor-pointer select-none bg-slate-50 px-3 py-2 rounded-lg border border-slate-200">
              <input
                type="checkbox"
                checked={anomalyOnly}
                onChange={(e) => setAnomalyOnly(e.target.checked)}
                className="w-4 h-4 rounded text-sky-600 focus:ring-sky-500 border-slate-300"
              />
              <span>Price Alerts Only</span>
            </label>

            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by procedure name..."
              className="px-3.5 py-2 rounded-xl border border-slate-300 text-xs w-48 focus:outline-none focus:ring-2 focus:ring-sky-500"
            />

            <form onSubmit={handleLocationSearch} className="flex items-center gap-1.5">
              <input
                type="text"
                value={locationQuery}
                onChange={(e) => setLocationQuery(e.target.value)}
                placeholder="City (e.g. houston_tx)"
                className="px-3 py-2 rounded-xl border border-slate-300 text-xs w-36 focus:outline-none focus:ring-2 focus:ring-sky-500 font-mono"
              />
              <button
                type="submit"
                className="px-3.5 py-2 bg-slate-900 text-white rounded-xl text-xs font-bold hover:bg-slate-800 transition-colors shadow-sm"
              >
                Filter
              </button>
            </form>
          </div>
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-900 text-xs sm:text-sm">
          Failed to load claims: {error}
        </div>
      )}

      {/* Loading Skeletons */}
      {loading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="bg-white rounded-2xl border border-slate-200 p-6 animate-pulse space-y-3"
            >
              <div className="h-4 bg-slate-200 rounded w-1/4" />
              <div className="h-6 bg-slate-200 rounded w-2/3" />
              <div className="h-3 bg-slate-200 rounded w-1/2" />
            </div>
          ))}
        </div>
      ) : filteredClaims.length === 0 ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center shadow-card">
          <div className="text-4xl mb-3">📋</div>
          <h3 className="text-base font-bold text-slate-800">No Matching Claims Found</h3>
          <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
            {locationQuery || actionFilter !== 'all' || anomalyOnly || searchQuery
              ? 'No claims match your current filter settings. Try resetting the filters.'
              : 'No claims in the database yet. Submit a clinical bill via the Audit page to begin.'}
          </p>
        </div>
      ) : (
        /* Claims List */
        <div className="space-y-4">
          {filteredClaims.map((claim) => (
            <ClaimCard
              key={claim.claim_id}
              claim={claim}
              verification={verifications[claim.claim_id]}
            />
          ))}
        </div>
      )}

      {/* Pagination Controls */}
      <div className="flex items-center justify-between pt-4 border-t border-slate-200">
        <button
          type="button"
          disabled={skip === 0 || loading}
          onClick={() => setSkip(Math.max(0, skip - limit))}
          className="px-4 py-2 rounded-xl border border-slate-300 bg-white text-xs font-bold text-slate-700 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed shadow-sm transition-colors"
        >
          &larr; Previous Page
        </button>

        <span className="text-xs text-slate-500">
          Showing {filteredClaims.length > 0 ? skip + 1 : 0}&ndash;
          {Math.min(skip + limit, total)} of {total} claims
        </span>

        <button
          type="button"
          disabled={skip + limit >= total || loading}
          onClick={() => setSkip(skip + limit)}
          className="px-4 py-2 rounded-xl border border-slate-300 bg-white text-xs font-bold text-slate-700 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed shadow-sm transition-colors"
        >
          Next Page &rarr;
        </button>
      </div>
    </div>
  )
}
