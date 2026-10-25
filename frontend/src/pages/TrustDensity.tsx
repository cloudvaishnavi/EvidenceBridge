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
    <div className="space-y-8 max-w-5xl mx-auto">
      {/* Page Header */}
      <div>
        <div className="inline-flex items-center gap-2 px-2.5 py-0.5 rounded-full bg-sky-50 text-sky-800 text-[11px] font-bold uppercase tracking-wider mb-1.5 border border-sky-200">
          Geographic Analytics
        </div>
        <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
          Regional Hospital Reliability Score
        </h1>
        <p className="text-xs sm:text-sm text-slate-500 mt-1 max-w-2xl leading-relaxed">
          How reliable are billing and clinical practices in this geographic area? We monitor clinical guideline adherence, pricing anomaly rates, and audit volume across metropolitan areas.
        </p>
      </div>

      {/* Search Bar & Metro Switcher */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-card">
        <form
          onSubmit={handleSearchSubmit}
          className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3"
        >
          <div className="relative flex-1">
            <input
              type="text"
              value={locationKey}
              onChange={(e) => setLocationKey(e.target.value)}
              placeholder="Enter canonical key, e.g. 'houston_tx', 'chicago_il', 'cleveland_oh'..."
              className="w-full px-4 py-2.5 rounded-xl border border-slate-300 text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 font-mono text-slate-800 placeholder:text-slate-400 bg-slate-50/50"
            />
          </div>

          <button
            type="submit"
            disabled={loadingSelected || !locationKey.trim()}
            className="px-6 py-2.5 rounded-xl bg-sky-600 text-white text-xs sm:text-sm font-bold hover:bg-sky-700 transition-colors shadow-md disabled:opacity-50"
          >
            {loadingSelected ? 'Auditing Locality...' : 'Audit Metro'}
          </button>
        </form>

        {/* Quick Suggestion Pills */}
        <div className="flex items-center gap-2 mt-4 text-xs text-slate-500 flex-wrap">
          <span className="font-semibold text-slate-700">Quick Select:</span>
          {['houston_tx', 'chicago_il', 'atlanta_ga', 'cleveland_oh', 'denver_co'].map(
            (k) => (
              <button
                key={k}
                type="button"
                onClick={() => handleSelectLocation(k)}
                className="px-3 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-800 font-mono text-xs font-semibold transition-colors"
              >
                {k}
              </button>
            )
          )}
        </div>
      </div>

      {/* Selected Location Detail Display */}
      {loadingSelected && (
        <div className="bg-white rounded-2xl border border-slate-200 p-8 text-center animate-pulse space-y-3">
          <div className="h-6 bg-slate-200 rounded w-1/3 mx-auto" />
          <div className="h-4 bg-slate-200 rounded w-1/2 mx-auto" />
        </div>
      )}

      {error && !loadingSelected && (
        <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-xs sm:text-sm">
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
      <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-card">
        <div className="px-6 py-4 bg-slate-50 border-b border-slate-200 flex flex-col sm:flex-row justify-between sm:items-center gap-3">
          <div>
            <h2 className="text-xs sm:text-sm font-bold text-slate-900 uppercase tracking-wider">
              Tracked Metropolitan Localities ({locations.length})
            </h2>
            <p className="text-[11px] text-slate-500 mt-0.5">
              Comparative reliability index and price anomaly rates across regions
            </p>
          </div>

          {/* Sort Switcher */}
          <div className="flex items-center gap-1 bg-slate-200/80 p-1 rounded-xl">
            <button
              type="button"
              onClick={() => setSortBy('density_score')}
              className={`px-3 py-1 text-xs font-bold rounded-lg transition-colors ${
                sortBy === 'density_score'
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Highest Reliability
            </button>
            <button
              type="button"
              onClick={() => setSortBy('volume')}
              className={`px-3 py-1 text-xs font-bold rounded-lg transition-colors ${
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
              No Geographic Data Seeded Yet
            </h3>
            <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
              Submit claims via the Audit workspace to automatically compute regional trust scores.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50/70 border-b border-slate-200 text-slate-500 font-bold uppercase tracking-wider text-[11px]">
                <tr>
                  <th className="px-6 py-3.5">Metropolitan Area</th>
                  <th className="px-6 py-3.5">Reliability Tier</th>
                  <th className="px-6 py-3.5">Reliability Score</th>
                  <th className="px-6 py-3.5 text-center">Total Claims</th>
                  <th className="px-6 py-3.5 text-center">Audited</th>
                  <th className="px-6 py-3.5 text-center">Price Alert Rate</th>
                  <th className="px-6 py-3.5 text-right">Action</th>
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
                        isSelected ? 'bg-sky-50/70 font-semibold' : ''
                      }`}
                    >
                      <td className="px-6 py-4">
                        <div className="font-bold text-slate-900 text-sm">
                          {loc.city}
                          {loc.state_or_region ? `, ${loc.state_or_region}` : ''}
                        </div>
                        <div className="font-mono text-[11px] text-slate-400">
                          {loc.location_key}
                        </div>
                      </td>

                      <td className="px-6 py-4">
                        <TrustTierBadge tier={loc.trust_tier} />
                      </td>

                      <td className="px-6 py-4">
                        <div className="flex items-center gap-2">
                          <span className="font-mono font-bold text-slate-900 w-12 text-xs">
                            {loc.density_score.toFixed(3)}
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

                      <td className="px-6 py-4 text-center font-mono text-slate-700">
                        {loc.total_claims}
                      </td>

                      <td className="px-6 py-4 text-center font-mono text-slate-700">
                        {loc.verified_claims}
                      </td>

                      <td className="px-6 py-4 text-center font-mono">
                        <span
                          className={`font-bold ${
                            loc.cost_anomaly_rate > 0.3
                              ? 'text-rose-600'
                              : 'text-slate-700'
                          }`}
                        >
                          {anomalyPct}%
                        </span>
                      </td>

                      <td className="px-6 py-4 text-right">
                        <span className="text-xs font-bold text-sky-600 hover:text-sky-800">
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
