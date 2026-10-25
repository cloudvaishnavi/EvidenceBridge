import { useState, useEffect } from 'react'
import { getHealth } from '../api/client'
import ExtractVerifyForm from '../components/ExtractVerifyForm'
import type { HealthResponse } from '../types'

interface SampleCase {
  label: string
  category: 'Approved' | 'Markup Flag' | 'Guideline Flag' | 'Safe Abstain'
  description: string
  text: string
}

const SAMPLE_CASES: SampleCase[] = [
  {
    label: 'Saline IV Overcharge ($720)',
    category: 'Markup Flag',
    description: '16× hospital markup on routine commodity IV fluid',
    text: `EMERGENCY ROOM CHARGE SUMMARY
MIDWEST REGIONAL MEDICAL CENTER - CLEVELAND, OH
Patient: Jane Doe (Acct #MR-2024-99120)

Supply Item: 0.9% Sodium Chloride (Normal Saline) 1,000 mL IV infusion bag for emergency hydration.
Billed Charge: $720.00
Clinical Note: Emergency administration of normal saline for acute dehydration following gastroenteritis.`,
  },
  {
    label: 'Routine Diabetes Metformin ($15)',
    category: 'Approved',
    description: 'First-line standard of care conforming to ADA guidelines',
    text: `CLINICAL VISIT NOTE
METROPOLITAN INTERNAL MEDICINE CLINIC - CHICAGO, IL
Patient: 54-year-old male with confirmed diagnosis of Type 2 Diabetes Mellitus (HbA1c 7.9%).

Prescription: Metformin hydrochloride 500 mg orally twice daily with meals (60 tablets, 30-day supply).
Total Pharmacy Cost: $15.00
Clinical Assessment: First-line pharmacotherapy initiated per standard diabetes clinical guidelines.`,
  },
  {
    label: 'Brain MRI for Severe Headache ($650)',
    category: 'Approved',
    description: 'Neurological indication matching ACR appropriateness criteria',
    text: `OUTPATIENT NEUROLOGY CONSULTATION & IMAGING ORDER
HOUSTON METHODIST HOSPITAL - HOUSTON, TX
Patient: 48-year-old female presenting with progressive unilateral headache, papilledema, and new focal neurological deficit.

Procedure: CPT 70551 Magnetic Resonance Imaging (MRI) Brain without contrast.
Total Billed Facility Charge: $650.00
Clinical Indication: Neuroimaging indicated to rule out intracranial mass or acute cerebrovascular lesion.`,
  },
  {
    label: 'Bronchitis Antibiotic ($24)',
    category: 'Guideline Flag',
    description: 'Inappropriate antibiotic for uncomplicated viral bronchitis',
    text: `URGENT CARE CLINIC ENCOUNTER
ATLANTA HEALTHCARE PARTNERS - ATLANTA, GA
Patient: 32-year-old presenting with 4-day history of non-productive cough, afebrile, lungs clear to auscultation.

Diagnosis: Acute viral bronchitis without complications.
Prescription: Azithromycin 250 mg (Z-Pak, 6 tablets total).
Total Billed Charge: $24.00
Clinical Note: Prescribed antibiotic for symptomatic cough relief.`,
  },
  {
    label: 'Novel Unbenchmarked Therapy ($45,000)',
    category: 'Safe Abstain',
    description: 'High-cost experimental treatment without reference benchmarks',
    text: `SPECIALTY INFUSION SUITE
PACIFIC ADVANCED MEDICINE - SAN FRANCISCO, CA
Patient: 61-year-old with refractory musculoskeletal pain.

Administered: Experimental synthetic peptide bioregulator infusion (3-day cycle).
Total Billed Charge: $45,000.00
Clinical Note: Off-label regenerative cellular restorative therapy administered per compassionate protocol.`,
  },
]

export default function Home() {
  const [health, setHealth] = useState<{
    loading: boolean
    ok: boolean
    data?: HealthResponse
  }>({ loading: true, ok: false })

  const [selectedText, setSelectedText] = useState('')
  const [activePreset, setActivePreset] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    getHealth()
      .then((data) => {
        if (active) setHealth({ loading: false, ok: data.status === 'ok' || data.status === 'healthy', data })
      })
      .catch(() => {
        if (active) setHealth({ loading: false, ok: false })
      })
    return () => {
      active = false
    }
  }, [])

  const handleSelectSample = (sample: SampleCase) => {
    setSelectedText(sample.text)
    setActivePreset(sample.label)
  }

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Page Title & Plain-English Explainer */}
      <div className="text-center max-w-3xl mx-auto">
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-sky-50 border border-sky-200 text-sky-800 text-xs font-semibold mb-3 shadow-subtle">
          <span>🩺 Clinical Claims &amp; Billing Auditor</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight">
          Audit Clinical Notes &amp; Hospital Bills
        </h1>
        <p className="mt-2.5 text-base text-slate-600 leading-relaxed">
          Paste any hospital bill line, itemized charge, or patient chart. EvidenceBridge verifies clinical indications against medical guidelines and audits charges against regional pricing benchmarks.
        </p>
      </div>

      {/* Stepped Process Visual */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-subtle flex items-start gap-3.5">
          <div className="w-8 h-8 rounded-xl bg-sky-100 text-sky-700 font-bold text-sm flex items-center justify-center flex-shrink-0">
            1
          </div>
          <div>
            <div className="text-sm font-bold text-slate-800">Input Document</div>
            <div className="text-xs text-slate-500 mt-1 leading-normal">
              Paste bill text, EHR notes, or select a pre-filled sample case.
            </div>
          </div>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-subtle flex items-start gap-3.5">
          <div className="w-8 h-8 rounded-xl bg-indigo-100 text-indigo-700 font-bold text-sm flex items-center justify-center flex-shrink-0">
            2
          </div>
          <div>
            <div className="text-sm font-bold text-slate-800">Check Evidence &amp; Price</div>
            <div className="text-xs text-slate-500 mt-1 leading-normal">
              Searches medical guidelines and compares against CMS price benchmarks.
            </div>
          </div>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-subtle flex items-start gap-3.5">
          <div className="w-8 h-8 rounded-xl bg-emerald-100 text-emerald-700 font-bold text-sm flex items-center justify-center flex-shrink-0">
            3
          </div>
          <div>
            <div className="text-sm font-bold text-slate-800">Review 7-Stage Audit</div>
            <div className="text-xs text-slate-500 mt-1 leading-normal">
              Inspect full decision trail, guideline citations, and markup ratios.
            </div>
          </div>
        </div>
      </div>

      {/* Sample Cases Picker */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 sm:p-7 shadow-subtle">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
              Try a Pre-Configured Sample Case
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Click any realistic clinical scenario to pre-populate the input form
            </p>
          </div>
          {activePreset && (
            <button
              type="button"
              onClick={() => {
                setSelectedText('')
                setActivePreset(null)
              }}
              className="text-xs text-slate-400 hover:text-slate-600 font-medium"
            >
              Clear selection
            </button>
          )}
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {SAMPLE_CASES.map((sample) => {
            const isSelected = activePreset === sample.label
            const badgeColor =
              sample.category === 'Approved'
                ? 'bg-emerald-100 text-emerald-800'
                : sample.category === 'Markup Flag'
                ? 'bg-amber-100 text-amber-900'
                : sample.category === 'Guideline Flag'
                ? 'bg-rose-100 text-rose-800'
                : 'bg-slate-200 text-slate-800'

            return (
              <button
                key={sample.label}
                type="button"
                onClick={() => handleSelectSample(sample)}
                className={`text-left p-4 rounded-xl border transition-all ${
                  isSelected
                    ? 'border-sky-500 bg-sky-50/70 shadow-sm'
                    : 'border-slate-200 bg-slate-50/50 hover:bg-slate-100 hover:border-slate-300'
                }`}
              >
                <div className="flex items-center justify-between mb-1.5">
                  <span className={`px-2.5 py-0.5 rounded text-xs font-bold ${badgeColor}`}>
                    {sample.category}
                  </span>
                  <span className="text-xs text-sky-600 font-semibold">Select &rarr;</span>
                </div>
                <div className="font-bold text-sm text-slate-900">{sample.label}</div>
                <div className="text-xs text-slate-500 mt-1 line-clamp-2 leading-relaxed">
                  {sample.description}
                </div>
              </button>
            )
          })}
        </div>
      </div>

      {/* Main Extract & Verify Form */}
      <ExtractVerifyForm
        initialText={selectedText}
        onSampleCleared={() => {
          setSelectedText('')
          setActivePreset(null)
        }}
      />
    </div>
  )
}
