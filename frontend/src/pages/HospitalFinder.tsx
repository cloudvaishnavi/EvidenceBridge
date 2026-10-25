import React, { useState, useEffect, useCallback } from 'react'
import { formatCurrency } from '../utils/currency'
import { API_BASE } from '../api/client'

export interface HospitalProcedurePrice {
  service_name: string
  cpt_code?: string | null
  min_price: number
  max_price: number
  typical_price?: number | null
  currency: string
  price_type: string
  source: string
  last_updated: string
}

export interface HospitalDetail {
  id: string
  name: string
  address: string
  neighborhood?: string | null
  city: string
  state_or_region?: string | null
  country: string
  lat: number
  lon: number
  distance_km?: number | null
  distance_miles?: number | null
  distance_label: string
  facility_type: string
  verified_services: string[]
  phone?: string | null
  website?: string | null
  directions_url?: string | null
  price_available: boolean
  consultation_fee?: number | null
  consultation_fee_currency: string
  consultation_fee_source?: string | null
  consultation_fee_date?: string | null
  price_type: string
  procedure_prices: HospitalProcedurePrice[]
  public_rating?: number | null
  review_count?: number | null
  review_source?: string | null
  review_date?: string | null
  accreditations: string[]
  trust_score?: number | null
  trust_score_explanation?: string | null
  why_appears: string
  data_source: string
  last_updated: string
}

export interface EmergencyAlert {
  is_emergency: boolean
  warning_title?: string | null
  warning_message?: string | null
  emergency_phone?: string | null
  action_advice?: string | null
}

export interface HospitalSearchResponse {
  query_city: string
  search_coordinates?: { lat: number; lon: number } | null
  total_results: number
  symptom_filter?: string | null
  symptom_guidance?: string | null
  emergency_alert?: EmergencyAlert | null
  hospitals: HospitalDetail[]
  data_sources_used: string[]
  disclaimer: string
}

export function HospitalFinder() {
  const [cityOrArea, setCityOrArea] = useState('Bengaluru, Karnataka')
  const [symptom, setSymptom] = useState('')
  const [maxDistanceKm, setMaxDistanceKm] = useState(35)
  const [careType, setCareType] = useState('All')
  const [sortBy, setSortBy] = useState<'distance' | 'cost' | 'rating'>('distance')
  const [coords, setCoords] = useState<{ lat: number; lon: number } | null>(null)
  const [geoLocating, setGeoLocating] = useState(false)
  const [geoError, setGeoError] = useState<string | null>(null)

  const [loading, setLoading] = useState(false)
  const [searchResponse, setSearchResponse] = useState<HospitalSearchResponse | null>(null)
  const [searchError, setSearchError] = useState<string | null>(null)
  const [selectedHospital, setSelectedHospital] = useState<HospitalDetail | null>(null)
  const [showMap, setShowMap] = useState(false)
  const [expandedPrices, setExpandedPrices] = useState<Record<string, boolean>>({})

  // Fetch hospitals
  const executeSearch = useCallback(
    async (overrideCoords?: { lat: number; lon: number }, overrideCity?: string) => {
      setLoading(true)
      setSearchError(null)

      try {
        const queryCity = overrideCity !== undefined ? overrideCity : cityOrArea
        const params = new URLSearchParams()
        if (queryCity.trim()) {
          params.append('city_or_area', queryCity.trim())
        }

        // Only append coordinates if GPS override is explicitly supplied
        // or if coords are set and the user is searching with 'Your Current Geolocation'
        const activeCoords = overrideCoords || (queryCity === 'Your Current Geolocation' ? coords : null)
        if (activeCoords) {
          params.append('lat', activeCoords.lat.toString())
          params.append('lon', activeCoords.lon.toString())
        }

        if (symptom.trim()) {
          params.append('symptom', symptom.trim())
        }

        params.append('max_distance_km', maxDistanceKm.toString())
        if (careType !== 'All') {
          params.append('care_type', careType)
        }
        params.append('sort_by', sortBy)

        const res = await fetch(`${API_BASE}/hospitals/search?${params.toString()}`)
        if (!res.ok) {
          throw new Error(`Search failed with status ${res.status}`)
        }

        const data: HospitalSearchResponse = await res.json()
        setSearchResponse(data)
        if (data.hospitals.length > 0) {
          setSelectedHospital(data.hospitals[0])
        }
      } catch (err: unknown) {
        console.error('Hospital search failed:', err)
        setSearchError(
          err instanceof Error
            ? err.message
            : 'Unable to reach hospital search service. Please check your connection.'
        )
      } finally {
        setLoading(false)
      }
    },
    [careType, cityOrArea, coords, maxDistanceKm, sortBy, symptom]
  )

  // Run initial search
  useEffect(() => {
    executeSearch()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Geolocation handler
  const handleUseCurrentLocation = () => {
    if (!navigator.geolocation) {
      setGeoError('Geolocation is not supported by your browser.')
      return
    }

    setGeoLocating(true)
    setGeoError(null)

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const userCoords = {
          lat: pos.coords.latitude,
          lon: pos.coords.longitude,
        }
        setCoords(userCoords)
        setCityOrArea('Your Current Geolocation')
        setGeoLocating(false)
        executeSearch(userCoords)
      },
      (err) => {
        setGeoLocating(false)
        if (err.code === err.PERMISSION_DENIED) {
          setGeoError('Location access was denied. You can search by entering any city or area name above.')
        } else {
          setGeoError('Could not determine current location. Please type a city name.')
        }
      },
      { timeout: 8000, enableHighAccuracy: true }
    )
  }

  const togglePriceExpansion = (hospId: string) => {
    setExpandedPrices((prev) => ({
      ...prev,
      [hospId]: !prev[hospId],
    }))
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800">
              Verified Public Data &amp; OpenStreetMap
            </span>
            <span className="text-xs text-slate-500 font-medium">Free &bull; No API Keys Required</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            Hospital &amp; Care Finder
          </h1>
          <p className="text-sm text-slate-600 mt-1 max-w-3xl">
            Locate nearby hospitals, compare official published consultation fees, review verified regulatory accreditations,
            and inspect straight-line travel distances without hidden markups.
          </p>
        </div>

        {/* View Toggle */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setShowMap(!showMap)}
            className={`px-3.5 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 border ${
              showMap
                ? 'bg-navy-900 text-white border-navy-900 shadow-sm'
                : 'bg-white text-slate-700 hover:bg-slate-50 border-slate-300'
            }`}
          >
            <span>🗺️</span>
            <span>{showMap ? 'Hide Map' : 'Show Interactive Map'}</span>
          </button>
        </div>
      </div>

      {/* Emergency Red-Flag Banner (if urgent symptom is entered) */}
      {searchResponse?.emergency_alert && searchResponse.emergency_alert.is_emergency && (
        <div className="p-4 sm:p-5 rounded-2xl bg-rose-50 border-2 border-rose-500 text-rose-950 shadow-md animate-in fade-in slide-in-from-top-2">
          <div className="flex items-start gap-3.5">
            <div className="w-10 h-10 rounded-xl bg-rose-600 text-white flex items-center justify-center text-xl shrink-0">
              🚨
            </div>
            <div className="space-y-1">
              <h3 className="text-base font-extrabold text-rose-900">
                {searchResponse.emergency_alert.warning_title || 'Immediate Emergency Care Advised'}
              </h3>
              <p className="text-xs sm:text-sm text-rose-900/90 leading-relaxed font-medium">
                {searchResponse.emergency_alert.warning_message}
              </p>
              <div className="pt-2 flex flex-wrap items-center gap-3">
                <span className="px-3 py-1 rounded-lg bg-rose-700 text-white text-xs font-extrabold tracking-wide">
                  {searchResponse.emergency_alert.emergency_phone || 'Call 112 / 108 or 911'}
                </span>
                <span className="text-xs font-semibold text-rose-800">
                  {searchResponse.emergency_alert.action_advice}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Non-Diagnostic Symptom Guidance Info Box */}
      {searchResponse?.symptom_guidance && !searchResponse.emergency_alert?.is_emergency && (
        <div className="p-3.5 rounded-xl bg-sky-50 border border-sky-200 text-sky-950 flex items-start gap-3">
          <span className="text-lg">💡</span>
          <div className="text-xs leading-relaxed">
            <strong className="font-bold text-sky-900">Facility-Finding Notice:</strong>{' '}
            {searchResponse.symptom_guidance}
          </div>
        </div>
      )}

      {/* Search Input Filter Bar */}
      <div className="bg-white rounded-2xl p-4 sm:p-5 border border-slate-200 shadow-sm space-y-4">
        <form
          onSubmit={(e) => {
            e.preventDefault()
            executeSearch()
          }}
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-12 gap-3 sm:gap-4"
        >
          {/* City / Area Input */}
          <div className="sm:col-span-1 lg:col-span-4">
            <label className="block text-[11px] font-bold text-slate-700 uppercase tracking-wider mb-1">
              City or Area
            </label>
            <div className="relative">
              <input
                type="text"
                value={cityOrArea}
                onChange={(e) => {
                  setCityOrArea(e.target.value)
                  setCoords(null)
                }}
                placeholder="e.g. Bengaluru, Ballari, Chicago, Atlanta..."
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-xs sm:text-sm font-medium focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-sky-500 pr-10"
              />
              <button
                type="button"
                onClick={handleUseCurrentLocation}
                disabled={geoLocating}
                title="Use current GPS location"
                className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded-lg text-slate-400 hover:text-sky-600 hover:bg-sky-50 transition-colors"
              >
                {geoLocating ? (
                  <span className="w-4 h-4 block border-2 border-sky-600 border-t-transparent rounded-full animate-spin" />
                ) : (
                  <span className="text-sm">📍</span>
                )}
              </button>
            </div>
            {geoError && <p className="text-[10px] text-rose-600 mt-1">{geoError}</p>}
          </div>

          {/* Health Concern / Symptom Filter */}
          <div className="sm:col-span-1 lg:col-span-3">
            <label className="block text-[11px] font-bold text-slate-700 uppercase tracking-wider mb-1">
              Symptom or Concern (Optional)
            </label>
            <input
              type="text"
              value={symptom}
              onChange={(e) => setSymptom(e.target.value)}
              placeholder="e.g. Fever, Headache, Minor injury..."
              className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-xs sm:text-sm font-medium focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-sky-500"
            />
          </div>

          {/* Care Type Filter */}
          <div className="sm:col-span-1 lg:col-span-2">
            <label className="block text-[11px] font-bold text-slate-700 uppercase tracking-wider mb-1">
              Type of Care
            </label>
            <select
              value={careType}
              onChange={(e) => setCareType(e.target.value)}
              className="w-full px-3 py-2.5 rounded-xl border border-slate-300 text-xs sm:text-sm font-medium focus:outline-none focus:ring-2 focus:ring-sky-500 bg-white"
            >
              <option value="All">All Facilities</option>
              <option value="Hospital">General Hospital</option>
              <option value="Trauma">Trauma Center</option>
              <option value="Pediatric">Pediatric</option>
              <option value="Academic">Academic Center</option>
            </select>
          </div>

          {/* Search Button */}
          <div className="sm:col-span-1 lg:col-span-3 flex items-end gap-2">
            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 px-4 rounded-xl bg-sky-600 hover:bg-sky-700 disabled:bg-slate-300 text-white text-xs sm:text-sm font-bold shadow-sm transition-all flex items-center justify-center gap-1.5"
            >
              {loading ? (
                <>
                  <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>Searching...</span>
                </>
              ) : (
                <>
                  <span>🔍</span>
                  <span>Find Hospitals</span>
                </>
              )}
            </button>
          </div>
        </form>

        {/* Quick Regional City Chips for Verified Outpatient Tariffs & Trust Scores */}
        <div className="pt-2 border-t border-slate-100 flex flex-wrap items-center gap-1.5 text-xs">
          <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider mr-1">
            Verified Karnataka Hubs:
          </span>
          {[
            { label: 'Bengaluru', query: 'Bengaluru, Karnataka' },
            { label: 'Ballari', query: 'Ballari, Karnataka' },
            { label: 'Davangere', query: 'Davangere, Karnataka' },
            { label: 'Hubli / Dharwad', query: 'Hubballi-Dharwad, Karnataka' },
            { label: 'Mysuru', query: 'Mysuru, Karnataka' },
            { label: 'Mangaluru', query: 'Mangaluru, Karnataka' },
            { label: 'Belagavi', query: 'Belagavi, Karnataka' },
          ].map((c) => {
            const isSelected = cityOrArea.toLowerCase().includes(c.label.toLowerCase().split(' ')[0])
            return (
              <button
                key={c.label}
                type="button"
                onClick={() => {
                  setCityOrArea(c.query)
                  setCoords(null)
                  executeSearch(undefined, c.query)
                }}
                className={`px-2.5 py-1 rounded-lg text-[11px] font-bold transition-all ${
                  isSelected
                    ? 'bg-sky-600 text-white shadow-xs'
                    : 'bg-slate-100 hover:bg-sky-50 text-slate-700 hover:text-sky-800 border border-slate-200'
                }`}
              >
                📍 {c.label}
              </button>
            )
          })}
        </div>

        {/* Secondary Filters: Distance Slider & Sort Bar */}
        <div className="pt-3 border-t border-slate-100 flex flex-wrap items-center justify-between gap-4 text-xs">
          {/* Distance Slider */}
          <div className="flex items-center gap-2.5">
            <span className="font-bold text-slate-600">Travel Radius:</span>
            <input
              type="range"
              min="5"
              max="75"
              step="5"
              value={maxDistanceKm}
              onChange={(e) => setMaxDistanceKm(Number(e.target.value))}
              className="w-28 sm:w-36 accent-sky-600 cursor-pointer"
            />
            <span className="font-extrabold text-slate-900 bg-slate-100 px-2 py-0.5 rounded-md">
              {maxDistanceKm} km ({Math.round(maxDistanceKm * 0.621371)} miles)
            </span>
            <span className="text-[10px] text-slate-400">(Straight-line)</span>
          </div>

          {/* Sort Criteria */}
          <div className="flex items-center gap-2">
            <span className="font-bold text-slate-600">Sort by:</span>
            <div className="inline-flex rounded-lg border border-slate-200 bg-slate-50 p-0.5">
              <button
                type="button"
                onClick={() => {
                  setSortBy('distance')
                  setTimeout(executeSearch, 10)
                }}
                className={`px-2.5 py-1 rounded-md text-xs font-bold transition-colors ${
                  sortBy === 'distance' ? 'bg-white text-sky-700 shadow-xs' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Nearest
              </button>
              <button
                type="button"
                onClick={() => {
                  setSortBy('cost')
                  setTimeout(executeSearch, 10)
                }}
                className={`px-2.5 py-1 rounded-md text-xs font-bold transition-colors ${
                  sortBy === 'cost' ? 'bg-white text-sky-700 shadow-xs' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Published Fee
              </button>
              <button
                type="button"
                onClick={() => {
                  setSortBy('rating')
                  setTimeout(executeSearch, 10)
                }}
                className={`px-2.5 py-1 rounded-md text-xs font-bold transition-colors ${
                  sortBy === 'rating' ? 'bg-white text-sky-700 shadow-xs' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Public Trust
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Explanatory Notice for Sorting */}
      <div className="text-[11px] text-slate-500 bg-slate-50 px-3.5 py-2 rounded-xl border border-slate-200 flex items-center justify-between gap-2">
        <div>
          ℹ️ <strong>Choosing a Hospital:</strong> Distance, consultation fee, and public rating are separate criteria.
          The cheapest or nearest facility is not automatically the most appropriate for complex or specialized conditions.
        </div>
        <div className="shrink-0 text-[10px] text-slate-400 font-medium">
          Straight-line distance calculation &bull; No paid APIs
        </div>
      </div>

      {/* Error state */}
      {searchError && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs">
          <strong>Search Error:</strong> {searchError}
        </div>
      )}

      {/* Interactive Map Section (if toggled) */}
      {showMap && (
        <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm animate-in fade-in">
          <div className="p-3 bg-slate-900 text-white flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              <span>🗺️</span>
              <span className="font-bold">
                OpenStreetMap Cartography &bull; {selectedHospital?.name || 'Area Map'}
              </span>
            </div>
            <span className="text-[10px] text-slate-300">
              Tiles &copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer" className="underline">OpenStreetMap contributors</a>
            </span>
          </div>

          <div className="w-full h-80 sm:h-96 relative bg-slate-100">
            {selectedHospital ? (
              <iframe
                title="Hospital Location Map"
                width="100%"
                height="100%"
                frameBorder="0"
                scrolling="no"
                marginHeight={0}
                marginWidth={0}
                src={`https://www.openstreetmap.org/export/embed.html?bbox=${selectedHospital.lon - 0.05}%2C${selectedHospital.lat - 0.03}%2C${selectedHospital.lon + 0.05}%2C${selectedHospital.lat + 0.03}&layer=mapnik&marker=${selectedHospital.lat}%2C${selectedHospital.lon}`}
                className="w-full h-full border-0"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center text-xs text-slate-400">
                Select a hospital below to center map pin.
              </div>
            )}
          </div>
        </div>
      )}

      {/* Search Results Summary */}
      <div className="flex items-center justify-between">
        <h2 className="text-base sm:text-lg font-bold text-slate-900">
          Available Hospitals{' '}
          <span className="text-xs font-semibold text-slate-500">
            ({searchResponse?.total_results || 0} found in {searchResponse?.query_city || 'target region'})
          </span>
        </h2>
        {searchResponse && (
          <span className="text-xs text-slate-400">
            Straight-line distances from coordinates ({searchResponse.search_coordinates?.lat.toFixed(2)}, {searchResponse.search_coordinates?.lon.toFixed(2)})
          </span>
        )}
      </div>

      {/* Hospital Cards List */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="p-5 rounded-2xl bg-white border border-slate-200 animate-pulse space-y-3">
              <div className="h-5 bg-slate-200 rounded w-2/3" />
              <div className="h-3 bg-slate-100 rounded w-1/2" />
              <div className="h-16 bg-slate-50 rounded" />
            </div>
          ))}
        </div>
      ) : searchResponse?.hospitals && searchResponse.hospitals.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {searchResponse.hospitals.map((hosp) => {
            const isSelected = selectedHospital?.id === hosp.id
            const isPricesExpanded = !!expandedPrices[hosp.id]

            return (
              <div
                key={hosp.id}
                onClick={() => setSelectedHospital(hosp)}
                className={`bg-white rounded-2xl border transition-all p-5 flex flex-col justify-between cursor-pointer ${
                  isSelected
                    ? 'border-sky-500 shadow-md ring-2 ring-sky-200'
                    : 'border-slate-200 hover:border-slate-300 hover:shadow-xs'
                }`}
              >
                <div>
                  {/* Top Header: Name, Distance & Facility Type */}
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <div>
                      <div className="flex flex-wrap items-center gap-1.5 mb-1.5">
                        <span className="inline-block px-2.5 py-0.5 rounded-md text-[10px] font-extrabold uppercase tracking-wide bg-slate-100 text-slate-700">
                          {hosp.facility_type}
                        </span>
                        <span className="inline-block px-2 py-0.5 rounded-md text-[10px] font-bold bg-sky-50 text-sky-800 border border-sky-200">
                          {hosp.country === 'IN' ? '🇮🇳 India' : hosp.country === 'US' ? '🇺🇸 USA' : hosp.country}
                        </span>
                        <span className="inline-block px-2 py-0.5 rounded-md text-[10px] font-medium bg-slate-50 text-slate-600 border border-slate-200">
                          Source: {hosp.data_source}
                        </span>
                      </div>
                      <h3 className="text-base font-extrabold text-slate-900 leading-snug">
                        {hosp.name}
                      </h3>
                      <p className="text-xs text-slate-500 mt-0.5">
                        {hosp.neighborhood ? `${hosp.neighborhood} &bull; ` : ''}
                        {hosp.address}
                      </p>
                    </div>

                    {/* Straight-line Distance Pill */}
                    {hosp.distance_km !== undefined && hosp.distance_km !== null && (
                      <div className="text-right shrink-0 bg-sky-50 px-2.5 py-1.5 rounded-xl border border-sky-100">
                        <div className="text-xs font-black text-sky-900 leading-none">
                          {hosp.distance_km} km
                        </div>
                        <div className="text-[9px] text-sky-700 font-medium mt-0.5">
                          {hosp.distance_miles} mi (Straight-line)
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Why this hospital appears */}
                  <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-700 my-3">
                    <strong className="text-slate-900 font-bold block text-[10px] uppercase tracking-wider mb-0.5">
                      Why this hospital appears in your results:
                    </strong>
                    <p className="text-[11px] leading-relaxed text-slate-600">{hosp.why_appears}</p>
                  </div>

                  {/* Pricing Section (Real verified benchmark or honest unavailable) */}
                  <div className="p-3 rounded-xl bg-emerald-50/60 border border-emerald-200 my-3">
                    <div className="flex items-center justify-between">
                      <div>
                        <span className="text-[10px] font-extrabold uppercase tracking-wider text-emerald-900 block">
                          Published Consultation Fee
                        </span>
                        {hosp.price_available && hosp.consultation_fee !== null && hosp.consultation_fee !== undefined ? (
                          <div className="flex items-baseline gap-1.5 mt-0.5">
                            <span className="text-lg font-black text-emerald-950">
                              {formatCurrency(hosp.consultation_fee, hosp.consultation_fee_currency)}
                            </span>
                            <span className="text-[10px] text-emerald-800 font-medium">
                              ({hosp.price_type})
                            </span>
                          </div>
                        ) : (
                          <div className="flex items-center gap-1.5 text-xs font-bold text-slate-500 mt-1 italic">
                            <span>ℹ️</span>
                            <span>Price data not available</span>
                          </div>
                        )}
                      </div>

                      {/* Expand procedures button if items exist */}
                      {hosp.procedure_prices && hosp.procedure_prices.length > 0 && (
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation()
                            togglePriceExpansion(hosp.id)
                          }}
                          className="px-2.5 py-1 rounded-lg bg-emerald-100 hover:bg-emerald-200 text-emerald-900 text-[11px] font-bold transition-colors"
                        >
                          {isPricesExpanded ? 'Hide Procedures' : `View Procedures (${hosp.procedure_prices.length})`}
                        </button>
                      )}
                    </div>

                    {hosp.consultation_fee_source && (
                      <p className="text-[10px] text-emerald-800/80 mt-1 leading-tight">
                        Source: {hosp.consultation_fee_source}
                      </p>
                    )}

                    {/* Expandable Procedure Benchmark List */}
                    {isPricesExpanded && hosp.procedure_prices.length > 0 && (
                      <div className="mt-3 pt-2.5 border-t border-emerald-200 space-y-2 animate-in fade-in">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-900 block">
                          Published Procedure &amp; Test Benchmarks:
                        </span>
                        {hosp.procedure_prices.map((p, idx) => (
                          <div key={idx} className="p-2 rounded-lg bg-white border border-emerald-200 text-xs">
                            <div className="flex items-center justify-between font-bold text-slate-800">
                              <span>{p.service_name}</span>
                              <span className="text-emerald-900 font-extrabold">
                                {formatCurrency(p.min_price, p.currency)} &ndash; {formatCurrency(p.max_price, p.currency)}
                              </span>
                            </div>
                            <div className="flex items-center justify-between text-[10px] text-slate-500 mt-0.5">
                              <span>CPT: {p.cpt_code || 'Standard OPD'}</span>
                              <span>Source: {p.source}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Local Trust & Accreditation */}
                  <div className="grid grid-cols-2 gap-2 my-3 text-xs">
                    {/* Public Star Rating */}
                    <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200">
                      <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">
                        Public Rating
                      </span>
                      {hosp.public_rating ? (
                        <div className="flex items-center gap-1.5 mt-0.5">
                          <span className="text-sm font-extrabold text-amber-500">
                            ★ {hosp.public_rating.toFixed(1)}
                          </span>
                          <span className="text-[10px] text-slate-500">
                            ({hosp.review_count?.toLocaleString()} reviews)
                          </span>
                        </div>
                      ) : (
                        <span className="text-[11px] text-slate-400 font-medium">Rating unavailable</span>
                      )}
                      {hosp.review_source && (
                        <span className="text-[9px] text-slate-400 block mt-0.5 truncate">
                          {hosp.review_source}
                        </span>
                      )}
                    </div>

                    {/* EvidenceBridge Trust Score */}
                    <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200">
                      <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">
                        EvidenceBridge Trust
                      </span>
                      {hosp.trust_score ? (
                        <div className="flex items-center gap-1.5 mt-0.5">
                          <span className="text-sm font-extrabold text-sky-700">
                            {Math.round(hosp.trust_score * 100)}%
                          </span>
                          <span className="text-[10px] font-semibold text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded">
                            Verified
                          </span>
                        </div>
                      ) : (
                        <span className="text-[11px] text-slate-400">Score calculating</span>
                      )}
                      <span className="text-[9px] text-slate-400 block mt-0.5 truncate">
                        Audit &amp; Accreditation basis
                      </span>
                    </div>
                  </div>

                  {/* Accreditations Badges */}
                  {hosp.accreditations && hosp.accreditations.length > 0 && (
                    <div className="flex flex-wrap items-center gap-1.5 my-2">
                      {hosp.accreditations.map((acc, aIdx) => (
                        <span
                          key={aIdx}
                          className="px-2 py-0.5 rounded-md text-[10px] font-bold bg-sky-50 text-sky-900 border border-sky-200"
                        >
                          ✓ {acc}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                {/* Footer Actions: Contact, Directions, Website */}
                <div className="pt-3 border-t border-slate-100 flex items-center justify-between gap-2 mt-2">
                  <div className="flex items-center gap-2">
                    {hosp.phone && (
                      <a
                        href={`tel:${hosp.phone}`}
                        onClick={(e) => e.stopPropagation()}
                        className="px-2.5 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-800 text-[11px] font-bold transition-colors flex items-center gap-1"
                      >
                        <span>📞</span>
                        <span>Call</span>
                      </a>
                    )}
                    {hosp.website && (
                      <a
                        href={hosp.website}
                        target="_blank"
                        rel="noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="px-2.5 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-800 text-[11px] font-bold transition-colors flex items-center gap-1"
                      >
                        <span>🌐</span>
                        <span>Website</span>
                      </a>
                    )}
                  </div>

                  {hosp.directions_url && (
                    <a
                      href={hosp.directions_url}
                      target="_blank"
                      rel="noreferrer"
                      onClick={(e) => e.stopPropagation()}
                      className="px-3 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-700 text-white text-[11px] font-bold transition-colors flex items-center gap-1"
                    >
                      <span>🧭</span>
                      <span>Directions</span>
                    </a>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      ) : (
        <div className="p-8 text-center bg-white rounded-2xl border border-slate-200 space-y-4">
          <span className="text-3xl block">🏥</span>
          <div>
            <h3 className="text-base font-bold text-slate-900">
              No Hospitals Found Within {maxDistanceKm} km
            </h3>
            <p className="text-xs text-slate-600 max-w-lg mx-auto leading-relaxed mt-1">
              No registered medical facilities were found within {maxDistanceKm} km of{' '}
              <strong>{searchResponse?.query_city || cityOrArea}</strong>.
              EvidenceBridge strictly adheres to your travel radius and will never substitute hospitals from distant cities or foreign countries.
            </p>
          </div>

          {/* Actionable Suggestions */}
          <div className="flex flex-wrap items-center justify-center gap-2 pt-1">
            {maxDistanceKm < 50 && (
              <button
                type="button"
                onClick={() => {
                  setMaxDistanceKm(50)
                  setTimeout(() => executeSearch(), 10)
                }}
                className="px-3.5 py-2 rounded-xl bg-sky-50 hover:bg-sky-100 text-sky-700 border border-sky-200 text-xs font-bold transition-colors inline-flex items-center gap-1.5"
              >
                <span>Expand to 50 km</span>
                <span>&rarr;</span>
              </button>
            )}
            {maxDistanceKm < 75 && (
              <button
                type="button"
                onClick={() => {
                  setMaxDistanceKm(75)
                  setTimeout(() => executeSearch(), 10)
                }}
                className="px-3.5 py-2 rounded-xl bg-sky-600 hover:bg-sky-700 text-white text-xs font-bold shadow-xs transition-colors inline-flex items-center gap-1.5"
              >
                <span>Expand to 75 km Maximum</span>
                <span>&rarr;</span>
              </button>
            )}
          </div>

          {/* Regional Hub Search Shortcuts */}
          <div className="pt-3 border-t border-slate-100 max-w-lg mx-auto">
            <span className="text-[11px] font-semibold text-slate-500 block mb-2">
              Or search in major nearby regional healthcare centers:
            </span>
            <div className="flex flex-wrap items-center justify-center gap-1.5">
              {[
                'Davangere, Karnataka',
                'Bengaluru, Karnataka',
                'Ballari, Karnataka',
                'Hubli, Karnataka',
                'Mysuru, Karnataka',
                'Shivamogga, Karnataka',
                'Mangaluru, Karnataka',
              ].map((hub) => (
                <button
                  key={hub}
                  type="button"
                  onClick={() => {
                    setCityOrArea(hub)
                    setCoords(null)
                    setTimeout(() => executeSearch(), 10)
                  }}
                  className="px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-[11px] font-medium transition-colors border border-slate-200"
                >
                  {hub.split(',')[0]}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Data Source & Attribution Footer */}
      <div className="p-4 rounded-2xl bg-slate-100 border border-slate-200 text-xs text-slate-600 space-y-2">
        <div className="flex flex-wrap items-center justify-between gap-2 font-bold text-slate-700">
          <span>Data Sources &amp; Transparency Notice:</span>
          <span>Updated: {new Date().getFullYear()}</span>
        </div>
        <p className="text-[11px] text-slate-500 leading-relaxed">
          {searchResponse?.disclaimer ||
            'EvidenceBridge Hospital Finder provides facility location, published price benchmarks, and regulatory accreditation metrics for informational comparison only. This is not a medical diagnosis or treatment recommendation.'}
        </p>
        <div className="flex flex-wrap items-center gap-4 text-[10px] text-slate-400 pt-1">
          <span>• OpenStreetMap Cartography (ODbL)</span>
          <span>• CMS Hospital Price Transparency Machine-Readable Files</span>
          <span>• NABH (National Accreditation Board for Hospitals) Registry</span>
          <span>• Joint Commission International (JCI) Accredited Quality Registry</span>
        </div>
      </div>
    </div>
  )
}
export default HospitalFinder