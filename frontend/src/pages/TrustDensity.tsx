import React, { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  listTrustDensity,
  getTrustDensity,
  recomputeTrustDensity,
} from '../api/client'
import type { TrustDensityMetrics, LocationInsight } from '../types'
import { TrustDensityPanel } from '../components/TrustDensityPanel'
import { TrustTierBadge } from '../components/VerificationBadge'

export default function TrustDensity() {
  const [searchParams, setSearchParams] = useSearchParams()
  const initialKey = searchParams.get('key') || ''

  const [locationKey, setLocationKey] = useState(initialKey)
  const [selectedMetrics, setSelectedMetrics] = useState<TrustDensityMetrics | null>(null)
  const [selectedInsight, setSelectedInsight] = useState<LocationInsight | null>(null)
  const [loadingSelected, setLoadingSelected] = useState(false)
  const [recomputing, setRecomputing] = useState(false)

  const [locations, setLocations] = useState<TrustDensityMetrics[]>([])
  const [loadingList, setLoadingList] = useState(true)
  const [sortBy, setSortBy] = useState<'density_score' | 'volume'>('density_score')
  const [error, setError] = useState<string | null>(null)

  // Load all tracked locations
  const loadLocationList = async (sort: 'density_score' | 'volume') => {
    setLoadingList(true)
    try {
      const res = await listTrustDensity({ limit: 50, sort_by: sort })
      setLocations(res.locations)
    } catch {
      // ok if none exist yet
    } finally {
      setLoadingList(false)
    }
  }

  // Load specific location metrics
  const loadLocationDetail = async (key: string) => {
    if (!key.trim()) return
    setLoadingSelected(true)
    setError(null)
    try {
      const res = await getTrustDensity(key.trim().toLowerCase())
      setSelectedMetrics(res.metrics)
      setSelectedInsight(res.insight)
      setSearchParams({ key: key.trim().toLowerCase() })
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? err.message
          : `No trust density records found for '${key}'.`
      )
      setSelectedMetrics(null)
      setSelectedInsight(null)
    } finally {
      setLoadingSelected(false)
    }
  }

  useEffect(() => {
    loadLocationList(sortBy)
    if (initialKey) {
      loadLocationDetail(initialKey)
    }
  }, [sortBy])

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (locationKey.trim()) {
      loadLocationDetail(locationKey.trim())
    }
  }

  const handleSelectLocation = (key: string) => {
    setLocationKey(key)
    loadLocationDetail(key)
  }

  const handleRecompute = async () => {
    if (!selectedMetrics?.location_key) return
    setRecomputing(true)
    try {
      const res = await recomputeTrustDensity(selectedMetrics.location_key)
      setSelectedMetrics(res.metrics)
      setSelectedInsight(res.insight)
      loadLocationList(sortBy)
    } catch (err: unknown) {
      alert(`Recompute failed: ${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setRecomputing(false)
    }
  }

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900">
          Hyperlocal Trust Density
        </h1>
        <p className="text-xs text-slate-500 mt-1 max-w-2xl">
          Aggregates clinical guideline adherence, cost anomaly frequency, and
          recency-decayed claim activity into geographic reliability scores.
        </p>
      </div>

      {/* Search Bar & Quick Switcher */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
        <form
          onSubmit={handleSearchSubmit}
          className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3"
        >
          <div className="relative flex-1">
            <input
              type="text"
              value={locationKey}
              onChange={(e) => setLocationKey(e.target.value)}
              placeholder="Enter canonical key, e.g. 'houston_tx', 'chicago_il', 'atlanta_ga'..."
              className="w-full px-4 py-2.5 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 font-mono text-slate-800 placeholder:text-slate-400"
            />
          </div>

          <button
            type="submit"
            disabled={loadingSelected || !locationKey.trim()}
            className="px-6 py-2.5 rounded-lg bg-sky-600 text-white text-sm font-bold hover:bg-sky-700 transition-colors shadow-sm disabled:opacity-50"
          >
            {loadingSelected ? 'Searching...' : 'Audit Locality'}
          </button>
        </form>

        {/* Quick Suggestion Pills */}
        <div className="flex items-center gap-2 mt-4 text-xs text-slate-500 flex-wrap">
          <span className="font-medium">Common Metros:</span>
          {['houston_tx', 'chicago_il', 'atlanta_ga', 'cleveland_oh', 'denver_co'].map(
            (k) => (
              <button
                key={k}
                type="button"
                onClick={() => handleSelectLocation(k)}
                className="px-2.5 py-1 rounded-md bg-slate-100 hover:bg-slate-200 text-slate-700 font-mono text-xs transition-colors"
              >
                {k}
              </button>
            )
          )}
        </div>
      </div>

      {/* Selected Location Detail Display */}
      {loadingSelected && (
        <div className="bg-white rounded-xl border border-slate-200 p-8 text-center animate-pulse">
          <div className="h-6 bg-slate-200 rounded w-1/3 mx-auto mb-3" />
          <div className="h-4 bg-slate-200 rounded w-1/2 mx-auto" />
        </div>
      )}

      {error && !loadingSelected && (
        <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-sm">
          <strong>Notice:</strong> {error}
        </div>
      )}

      {selectedMetrics && !loadingSelected && (
        <TrustDensityPanel
          metrics={selectedMetrics}
          insight={selectedInsight}
          onRecompute={handleRecompute}
          isRecomputing={recomputing}
        />
      )}

      {/* All Tracked Localities Table */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
        <div className="px-6 py-4 bg-slate-50 border-b border-slate-200 flex flex-col sm:flex-row justify-between sm:items-center gap-3">
          <div>
            <h2 className="text-sm font-bold text-slate-900">
              Tracked Geographic Localities ({locations.length})
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Ranked overview of metropolitan reliability &amp; cost markup risk
            </p>
          </div>

          {/* Sort Switcher */}
          <div className="flex items-center gap-1 bg-slate-200 p-1 rounded-lg">
            <button
              type="button"
              onClick={() => setSortBy('density_score')}
              className={`px-3 py-1 text-xs font-semibold rounded-md transition-colors ${
                sortBy === 'density_score'
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Highest Density
            </button>
            <button
              type="button"
              onClick={() => setSortBy('volume')}
              className={`px-3 py-1 text-xs font-semibold rounded-md transition-colors ${
                sortBy === 'volume'
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Claim Volume
            </button>
          </div>
        </div>

        {loadingList ? (
          <div className="p-8 text-center text-xs text-slate-400 animate-pulse">
            Loading locality database...
          </div>
        ) : locations.length === 0 ? (
          <div className="p-12 text-center">
            <div className="text-3xl mb-2">📍</div>
            <h3 className="text-base font-bold text-slate-800">
              No Geographic Data Seeded
            </h3>
            <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
              Run <code className="bg-slate-100 px-1 py-0.5 rounded font-mono">python scripts/seed_data.py --verify</code> or submit claims from the Audit page to initialize hyperlocal scores.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50/70 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
                <tr>
                  <th className="px-6 py-3">Locality</th>
                  <th className="px-6 py-3">Trust Tier</th>
                  <th className="px-6 py-3">Density Score</th>
                  <th className="px-6 py-3 text-center">Total Claims</th>
                  <th className="px-6 py-3 text-center">Verified</th>
                  <th className="px-6 py-3 text-center">Anomaly Rate</th>
                  <th className="px-6 py-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {locations.map((loc) => {
                  const scorePct = Math.round(loc.density_score * 100)
                  const anomalyPct = Math.round(loc.cost_anomaly_rate * 100)
                  const isSelected = selectedMetrics?.location_key === loc.location_key

                  return (
                    <tr
                      key={loc.location_key}
                      onClick={() => handleSelectLocation(loc.location_key)}
                      className={`hover:bg-slate-50 cursor-pointer transition-colors ${
                        isSelected ? 'bg-sky-50/60 font-medium' : ''
                      }`}
                    >
                      <td className="px-6 py-3.5">
                        <div className="font-bold text-slate-900">
                          {loc.city}
                          {loc.state_or_region ? `, ${loc.state_or_region}` : ''}
                        </div>
                        <div className="font-mono text-[11px] text-slate-400">
                          {loc.location_key}
                        </div>
                      </td>

                      <td className="px-6 py-3.5">
                        <TrustTierBadge tier={loc.trust_tier} />
                      </td>

                      <td className="px-6 py-3.5">
                        <div className="flex items-center gap-2">
                          <span className="font-mono font-bold text-slate-800 w-10">
                            {loc.density_score.toFixed(2)}
                          </span>
                          <div className="w-20 bg-slate-100 h-2 rounded-full overflow-hidden">
                            <div
                              className={`h-full rounded-full ${
                                loc.density_score >= 0.75
                                  ? 'bg-emerald-500'
                                  : loc.density_score >= 0.50
                                  ? 'bg-sky-500'
                                  : loc.density_score >= 0.30
                                  ? 'bg-amber-500'
                                  : 'bg-rose-500'
                              }`}
                              style={{ width: `${Math.min(100, Math.max(0, scorePct))}%` }}
                            />
                          </div>
                        </div>
                      </td>

                      <td className="px-6 py-3.5 text-center font-mono text-slate-700">
                        {loc.total_claims}
                      </td>

                      <td className="px-6 py-3.5 text-center font-mono text-slate-700">
                        {loc.verified_claims}
                      </td>

                      <td className="px-6 py-3.5 text-center font-mono">
                        <span
                          className={
                            loc.cost_anomaly_rate > 0.3
                              ? 'text-rose-600 font-bold'
                              : 'text-slate-600'
                          }
                        >
                          {anomalyPct}%
                        </span>
                      </td>

                      <td className="px-6 py-3.5 text-right">
                        <span className="text-xs font-semibold text-sky-600 hover:text-sky-800">
                          Inspect &rarr;
                        </span>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
