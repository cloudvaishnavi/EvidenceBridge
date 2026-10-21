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

  // Client-side filtering for action and cost anomaly
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

    return true
  })

  return (
    <div className="space-y-6">
      {/* Header and Filter Controls */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
        <div className="flex flex-col md:flex-row justify-between md:items-center gap-4 mb-6">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Healthcare Claims Explorer</h1>
            <p className="text-xs text-slate-500 mt-1">
              Browse, filter, and inspect stored claims with full cryptographic provenance
            </p>
          </div>

          <span className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-slate-100 text-slate-700 w-fit">
            {total} Total Claim{total === 1 ? '' : 's'} Tracked
          </span>
        </div>

        {/* Filter Controls Row */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4 pt-4 border-t border-slate-100">
          {/* Action Filter Button Group */}
          <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg">
            {(['all', 'accept', 'flag', 'abstain'] as const).map((filter) => (
              <button
                key={filter}
                type="button"
                onClick={() => setActionFilter(filter)}
                className={`px-3 py-1.5 text-xs font-semibold rounded-md capitalize transition-colors ${
                  actionFilter === filter
                    ? 'bg-white text-slate-900 shadow-sm'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {filter}
              </button>
            ))}
          </div>

          {/* Anomaly Checkbox & Location Filter */}
          <div className="flex items-center gap-4 flex-wrap">
            <label className="inline-flex items-center gap-2 text-xs font-medium text-slate-700 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={anomalyOnly}
                onChange={(e) => setAnomalyOnly(e.target.checked)}
                className="w-4 h-4 rounded text-sky-600 focus:ring-sky-500 border-slate-300"
              />
              Cost Anomalies Only
            </label>

            {/* Location Search Form */}
            <form onSubmit={handleLocationSearch} className="flex items-center gap-2">
              <input
                type="text"
                value={locationQuery}
                onChange={(e) => setLocationQuery(e.target.value)}
                placeholder="Filter by city / key..."
                className="px-3 py-1.5 rounded-lg border border-slate-300 text-xs w-44 focus:outline-none focus:ring-2 focus:ring-sky-500"
              />
              <button
                type="submit"
                className="px-3 py-1.5 bg-slate-800 text-white rounded-lg text-xs font-medium hover:bg-slate-900 transition-colors"
              >
                Filter
              </button>
            </form>
          </div>
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-sm">
          Failed to load claims: {error}
        </div>
      )}

      {/* Loading Skeletons */}
      {loading ? (
        <div className="space-y-4">
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="bg-white rounded-xl border border-slate-200 p-6 animate-pulse space-y-3"
            >
              <div className="h-4 bg-slate-200 rounded w-1/4" />
              <div className="h-6 bg-slate-200 rounded w-2/3" />
              <div className="h-3 bg-slate-200 rounded w-1/2" />
            </div>
          ))}
        </div>
      ) : filteredClaims.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-200 p-12 text-center">
          <div className="text-3xl mb-2">📋</div>
          <h3 className="text-base font-bold text-slate-800">No Claims Found</h3>
          <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
            {locationQuery || actionFilter !== 'all' || anomalyOnly
              ? 'No claims match your current filter settings. Try clearing the filters.'
              : 'No claims in database yet. Submit text via the Audit page or run the seeder script.'}
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
          className="px-4 py-2 rounded-lg border border-slate-300 bg-white text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed shadow-sm"
        >
          &larr; Previous Page
        </button>

        <span className="text-xs text-slate-500">
          Showing {filteredClaims.length > 0 ? skip + 1 : 0}&ndash;
          {Math.min(skip + limit, total)} of {total}
        </span>

        <button
          type="button"
          disabled={skip + limit >= total || loading}
          onClick={() => setSkip(skip + limit)}
          className="px-4 py-2 rounded-lg border border-slate-300 bg-white text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed shadow-sm"
        >
          Next Page &rarr;
        </button>
      </div>
    </div>
  )
}
