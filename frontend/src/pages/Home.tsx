import { useState, useEffect } from 'react'
import { getHealth } from '../api/client'
import ExtractVerifyForm from '../components/ExtractVerifyForm'
import type { HealthResponse } from '../types'
import { useAudit } from '../context/AuditContext'

interface SampleCase {
  label: string
  category: 'Approved' | 'Markup Flag' | 'Guideline Flag' | 'Safe Abstain'
  description: string
  text: string
}

const SAMPLE_CASES: SampleCase[] = [
  {
    label: 'Saline IV Infusion Markup (₹1,800)',
    category: 'Markup Flag',
    description: '15× markup on routine emergency IV fluid exceeding NPPA national ceiling price benchmark (₹105)',
    text: `EMERGENCY DEPARTMENT CHARGE SUMMARY
MANIPAL HOSPITAL - BENGALURU, KARNATAKA
Patient: Ramesh Kumar (Acct #MH-BLR-2026-4412)

Item: 0.9% Sodium Chloride (Normal Saline) 1,000 mL IV infusion bag for emergency rehydration.
Billed Charge: ₹1,800.00
Clinical Note: Emergency IV hydration administered for acute gastroenteritis dehydration.`,
  },
  {
    label: 'Type 2 Diabetes Rx - Metformin (₹75)',
    category: 'Approved',
    description: 'First-line diabetes maintenance therapy conforming to ICMR & RSSDI clinical guidelines',
    text: `CLINICAL OUTPATIENT CONSULTATION & PRESCRIPTION
APOLLO CLINIC - DAVANGERE, KARNATAKA
Patient: 52-year-old male with confirmed Type 2 Diabetes Mellitus (HbA1c 7.8%).

Rx Prescribed:
1. Tab. Metformin Hydrochloride 500 mg (Glycomet)
   Dosage & Instructions: Take 1 tablet twice daily after meals (morning and night) with water for 30 days (60 tablets).

Total Pharmacy Billed Charge: ₹75.00
Clinical Assessment: First-line oral monotherapy initiated per standard ICMR/RSSDI diabetes guidelines.`,
  },
  {
    label: 'Acute Bronchitis Rx - Antibiotic (₹450)',
    category: 'Guideline Flag',
    description: 'Antibiotic overprescription flagged: ICMR advises against routine antibiotics for viral bronchitis',
    text: `DISTRICT CIVIL HOSPITAL - OUTPATIENT PRESCRIPTION
DISTRICT HOSPITAL - BALLARI, KARNATAKA
Patient: 34-year-old male presenting with acute uncomplicated bronchitis, low-grade fever, and non-productive cough for 4 days.

Rx Prescribed:
1. Tab. Azithromycin 500 mg (Zithromax)
   Dosage & Instructions: Take 1 tablet orally once daily 1 hour before meals for 5 days.
2. Tab. Paracetamol 650 mg (Dolo)
   Dosage & Instructions: Take 1 tablet as needed (SOS) for fever/body ache every 6-8 hours after food.

Total Pharmacy Charge: ₹450.00
Clinical Note: Empirical antibiotic therapy initiated for viral bronchitis without secondary infection.`,
  },
  {
    label: 'Diagnostic Brain MRI Scan (₹5,500)',
    category: 'Approved',
    description: 'Appropriate neuroimaging conforming to CGHS benchmark tariff and neurological criteria',
    text: `NEUROLOGY CONSULTATION & IMAGING ORDER
KMC HOSPITAL (KASTURBA MEDICAL COLLEGE) - MANGALURU, KARNATAKA
Patient: 46-year-old female presenting with progressive unilateral headache, papilledema, and new focal neurological signs.

Procedure: CPT 70551 Magnetic Resonance Imaging (MRI) Brain without contrast.
Total Billed Charge: ₹5,500.00
Clinical Indication: Urgent neuroimaging indicated to evaluate focal intracranial pathology per clinical guidelines.`,
  },
  {
    label: 'Uncoded Experimental Therapy (₹85,000)',
    category: 'Safe Abstain',
    description: 'Safe refusal: High-cost experimental therapy without established NPPA/CGHS tariff benchmarks',
    text: `REGENERATIVE MEDICINE SPECIALTY SUITE
CITY SUPER SPECIALITY HOSPITAL - BELAGAVI, KARNATAKA
Patient: 58-year-old with refractory degenerative musculoskeletal pain.

Administered: Autologous experimental cellular restorative therapy protocol.
Total Billed Charge: ₹85,000.00
Clinical Note: Off-label experimental regenerative restorative session administered without standard procedure code.`,
  },
  {
    label: 'US Emergency Normal Saline ($720 USD)',
    category: 'Markup Flag',
    description: 'Foreign currency demonstration: 16× markup evaluated against CMS Medicare USD schedule',
    text: `EMERGENCY ROOM CHARGE SUMMARY
MIDWEST REGIONAL MEDICAL CENTER - CLEVELAND, OH
Patient: Jane Doe (Acct #MR-2024-99120)

Supply Item: 0.9% Sodium Chloride (Normal Saline) 1,000 mL IV infusion bag for emergency hydration.
Billed Charge: $720.00
Clinical Note: Emergency administration of normal saline for acute dehydration following gastroenteritis.`,
  },
]

export default function Home() {
  const [health, setHealth] = useState<{
    loading: boolean
    ok: boolean
    data?: HealthResponse
  }>({ loading: true, ok: false })

  const { activePreset, setText: setAuditText, setActivePreset } = useAudit()

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
    setAuditText(sample.text)
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
          Upload a bill photo, take a camera snapshot, or paste any clinical chart note or itemized hospital charge. EvidenceBridge extracts document text with OCR, verifies clinical indications against medical guidelines, and audits charges against regional pricing benchmarks.
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
              Upload a bill photo, take a picture with camera, paste text, or select a sample case.
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
      <ExtractVerifyForm />
    </div>
  )
}
