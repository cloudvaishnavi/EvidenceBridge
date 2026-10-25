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

// Canonical Indian Regional Cities
const QUICK_SELECT_CITIES = [
  { key: 'bengaluru_ka', label: 'Bengaluru', shortName: 'Bengaluru' },
  { key: 'ballari_ka', label: 'Ballari', shortName: 'Ballari' },
  { key: 'mysuru_ka', label: 'Mysuru', shortName: 'Mysuru' },
  { key: 'davangere_ka', label: 'Davangere', shortName: 'Davangere' },
  { key: 'hubli_ka', label: 'Hubli / Dharwad', shortName: 'Hubli' },
  { key: 'mangaluru_ka', label: 'Mangaluru', shortName: 'Mangaluru' },
  { key: 'belagavi_ka', label: 'Belagavi', shortName: 'Belagavi' },
]

export default function TrustDensity() {
  const [searchParams, setSearchParams] = useSearchParams()
  // Default to Bengaluru if no key is in search params
  const initialKey = searchParams.get('key') || 'bengaluru_ka'

  const [locationKey, setLocationKey] = useState(initialKey)
  const [selectedMetrics, setSelectedMetrics] = useState<TrustDensityMetrics | null>(null)
  const [selectedInsight, setSelectedInsight] = useState<LocationInsight | null>(null)
  const [loadingSelected, setLoadingSelected] = useState(false)
  const [recomputing, setRecomputing] = useState(false)

  const [locations, setLocations] = useState<TrustDensityMetrics[]>([])
  const [loadingList, setLoadingList] = useState(true)
  const [sortBy, setSortBy] = useState<'density_score' | 'volume'>('density_score')
  const [error, setError] = useState<string | null>(null)

  // Load all tracked Indian locations
  const loadLocationList = async (sort: 'density_score' | 'volume') => {
    setLoadingList(true)
    try {
      const res = await listTrustDensity({ limit: 50, sort_by: sort })
      // Strictly filter out any foreign/US records
      const indianLocations = (res.locations || []).filter((loc) => {
        const key = loc.location_key.toLowerCase()
        return !['houston_tx', 'chicago_il', 'cleveland_oh', 'atlanta_ga', 'denver_co', 'boston_ma', 'san_francisco_ca'].includes(key)
      })
      setLocations(indianLocations)
    } catch {
      // Ok if error occurs
    } finally {
      setLoadingList(false)
    }
  }

  // Load specific location metrics
  const loadLocationDetail = async (key: string) => {
    if (!key.trim()) return
    setLoadingSelected(true)
    setError(null)

    // Normalize input key
    let normalized = key.trim().toLowerCase().replace(/\s+/g, '_')
    if (normalized === 'hubli' || normalized === 'dharwad' || normalized === 'hubballi') {
      normalized = 'hubli_ka'
    } else if (normalized === 'bengaluru' || normalized === 'bangalore') {
      normalized = 'bengaluru_ka'
    } else if (normalized === 'ballari' || normalized === 'bellary') {
      normalized = 'ballari_ka'
    } else if (normalized === 'mysuru' || normalized === 'mysore') {
      normalized = 'mysuru_ka'
    } else if (normalized === 'davangere' || normalized === 'davanagere') {
      normalized = 'davangere_ka'
    } else if (normalized === 'mangaluru' || normalized === 'mangalore') {
      normalized = 'mangaluru_ka'
    } else if (normalized === 'belagavi' || normalized === 'belgaum') {
      normalized = 'belagavi_ka'
    }

    try {
      const res = await getTrustDensity(normalized)
      setSelectedMetrics(res.metrics)
      setSelectedInsight(res.insight)
      setSearchParams({ key: normalized })
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
    <div className="space-y-8 max-w-5xl mx-auto font-sans">
      {/* Page Header */}
      <div>
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-sky-50 text-sky-800 text-[11px] font-bold uppercase tracking-wider mb-2 border border-sky-200">
          🇮🇳 India Geographic Health Analytics
        </div>
        <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
          Regional Hospital Reliability &amp; Trust Index
        </h1>
        <p className="text-xs sm:text-sm text-slate-600 mt-1 max-w-3xl leading-relaxed">
          How reliable are hospital billing and treatment practices across Indian cities? We continuously audit
          conformance to medical guidelines (ICMR, WHO), monitor excessive pricing markups, and verify outpatient
          fee transparency across key healthcare corridors.
        </p>
      </div>

      {/* Plain-Language Explanatory Guide Box */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5 bg-gradient-to-br from-slate-50 to-sky-50/40 p-4 sm:p-5 rounded-2xl border border-sky-100 shadow-2xs">
        <div className="p-3 bg-white rounded-xl border border-slate-200 shadow-2xs space-y-1">
          <div className="flex items-center gap-2 font-bold text-xs text-emerald-900">
            <span>🛡️</span>
            <span>Reliability Score</span>
          </div>
          <p className="text-[11px] text-slate-600 leading-relaxed">
            A score from <strong>0% to 100%</strong> measuring how consistently hospitals in this city adhere to medical treatment standards and charge fair, benchmarked prices.
          </p>
        </div>

        <div className="p-3 bg-white rounded-xl border border-slate-200 shadow-2xs space-y-1">
          <div className="flex items-center gap-2 font-bold text-xs text-amber-900">
            <span>⚠️</span>
            <span>Price Alert Rate</span>
          </div>
          <p className="text-[11px] text-slate-600 leading-relaxed">
            The percentage of audited claims that showed <strong>unusually high markups</strong> compared to government tariffs and state healthcare benchmarks.
          </p>
        </div>

        <div className="p-3 bg-white rounded-xl border border-slate-200 shadow-2xs space-y-1">
          <div className="flex items-center gap-2 font-bold text-xs text-slate-800">
            <span>⏸️</span>
            <span>Preliminary &bull; Safe Limits</span>
          </div>
          <p className="text-[11px] text-slate-600 leading-relaxed">
            Cities with fewer than <strong>5 audited claims</strong> are marked as preliminary so users are never misled by small or incomplete data samples.
          </p>
        </div>
      </div>

      {/* Search Bar & City Selector */}
      <div className="bg-white rounded-2xl border border-slate-200 p-5 sm:p-6 shadow-card space-y-4">
        <form
          onSubmit={handleSearchSubmit}
          className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3"
        >
          <div className="relative flex-1">
            <input
              type="text"
              value={locationKey}
              onChange={(e) => setLocationKey(e.target.value)}
              placeholder="Search Indian city key, e.g. bengaluru_ka, ballari_ka, mysuru_ka, davangere_ka..."
              className="w-full px-4 py-2.5 rounded-xl border border-slate-300 text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 font-mono text-slate-800 placeholder:text-slate-400 bg-slate-50/50"
            />
          </div>

          <button
            type="submit"
            disabled={loadingSelected || !locationKey.trim()}
            className="px-6 py-2.5 rounded-xl bg-sky-600 text-white text-xs sm:text-sm font-bold hover:bg-sky-700 transition-colors shadow-md disabled:opacity-50"
          >
            {loadingSelected ? 'Auditing Locality...' : 'Audit City'}
          </button>
        </form>

        {/* Quick Suggestion Pills */}
        <div className="flex items-center gap-2 text-xs text-slate-500 flex-wrap pt-1">
          <span className="font-bold text-slate-700">Quick Select:</span>
          {QUICK_SELECT_CITIES.map((c) => {
            const isSelected = selectedMetrics?.location_key === c.key || locationKey.toLowerCase().includes(c.shortName.toLowerCase())
            return (
              <button
                key={c.key}
                type="button"
                onClick={() => handleSelectLocation(c.key)}
                className={`px-3 py-1.5 rounded-xl font-bold text-xs transition-all ${
                  isSelected
                    ? 'bg-sky-600 text-white shadow-xs'
                    : 'bg-slate-100 hover:bg-sky-50 text-slate-700 hover:text-sky-800 border border-slate-200'
                }`}
              >
                📍 {c.label} ({c.key})
              </button>
            )
          })}
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
        <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-xs sm:text-sm flex items-start gap-2.5">
          <span className="text-amber-600 font-bold text-base mt-0.5">⚠️</span>
          <div>
            <strong className="block font-bold">Notice:</strong>
            <span>{error}</span>
          </div>
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

      {/* All Tracked Indian Localities Table */}
      <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-card">
        <div className="px-6 py-4 bg-slate-50 border-b border-slate-200 flex flex-col sm:flex-row justify-between sm:items-center gap-3">
          <div>
            <h2 className="text-xs sm:text-sm font-bold text-slate-900 uppercase tracking-wider">
              Tracked Indian Healthcare Hubs ({locations.length})
            </h2>
            <p className="text-[11px] text-slate-500 mt-0.5">
              Comparative reliability index and price anomaly rates across Karnataka and Indian regional cities
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
            Loading Indian locality database...
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
                  <th className="px-6 py-3.5 text-center">Audited Claims</th>
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
                            {scorePct}%
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
                        {loc.verified_claims}
                      </td>

                      <td className="px-6 py-4 text-center font-mono">
                        <span
                          className={`font-bold px-2 py-0.5 rounded text-[11px] ${
                            loc.cost_anomaly_rate > 0.2
                              ? 'bg-amber-100 text-amber-900'
                              : 'bg-emerald-50 text-emerald-800'
                          }`}
                        >
                          {anomalyPct}%
                        </span>
                      </td>

                      <td className="px-6 py-4 text-right">
                        <span className="text-xs font-bold text-sky-600 hover:text-sky-800">
                          View Deep-Dive &rarr;
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
