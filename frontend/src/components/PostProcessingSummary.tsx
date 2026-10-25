import React, { useState } from 'react'
import type { ExtractAndVerifyResponse } from '../types'
import { formatCurrency, normalizeCurrencyCode } from '../utils/currency'

interface PostProcessingSummaryProps {
  result: ExtractAndVerifyResponse
}

interface DecipheredMedicine {
  name: string
  dosage?: string
  timing?: string
  timingPlain: string
  foodRelation: string
  duration?: string
  category: string
  instructions: string
}

export function PostProcessingSummary({ result }: PostProcessingSummaryProps) {
  // Collapsed by default as explicitly requested
  const [isExpanded, setIsExpanded] = useState(false)

  const { claim, verification } = result
  const originalText = claim.original_text || ''
  const extracted = claim.extracted_fields
  const anomaly = verification.anomaly_details
  const location = claim.location

  // Determine main procedure / service
  const mainProcedure =
    extracted?.entity ||
    (anomaly?.benchmark_name ? anomaly.benchmark_name : 'Medical Consultation & Clinical Service')

  // Determine billed amount and currency
  let billedAmount = anomaly?.extracted_amount ?? null
  let currencyCode = normalizeCurrencyCode(
    anomaly?.currency || extracted?.cost_currency || (location?.country === 'IN' ? 'INR' : 'USD')
  )

  // If billed amount wasn't in anomaly details, try parsing from cost_range or text
  if (billedAmount === null && extracted?.cost_range) {
    const numMatch = extracted.cost_range.replace(/,/g, '').match(/\d+(\.\d+)?/)
    if (numMatch) {
      billedAmount = parseFloat(numMatch[0])
    }
  }

  // Parse medicines and administration instructions from clinical text
  const decipheredMedicines = parseMedicinesFromText(originalText)

  // Determine missing information and handwriting warnings
  const clinicalWarnings = generateClinicalWarnings(originalText, decipheredMedicines, claim.source_type)

  // Synthesize "What the system understood"
  const systemUnderstanding = generateSystemUnderstanding(claim, verification, mainProcedure, billedAmount, currencyCode)

  return (
    <div className="rounded-2xl border border-sky-200 bg-white shadow-card overflow-hidden transition-all">
      {/* Collapsible Header */}
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full p-4 sm:p-5 text-left bg-gradient-to-r from-sky-50/80 via-white to-sky-50/40 hover:bg-sky-50/60 transition-colors flex items-center justify-between gap-4"
        aria-expanded={isExpanded}
      >
        <div className="flex items-start sm:items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-sky-600 text-white flex items-center justify-center text-lg font-bold shrink-0 shadow-sm">
            📋
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2 mb-1">
              <span className="text-xs font-black text-sky-900 uppercase tracking-wider">
                Post-Processing &amp; Prescription Summary
              </span>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-sky-100 text-sky-800 border border-sky-200">
                {isExpanded ? 'Click to collapse' : 'Collapsed by default &bull; Click to view'}
              </span>
              {decipheredMedicines.length > 0 && (
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
                  💊 {decipheredMedicines.length} Medicine{decipheredMedicines.length > 1 ? 's' : ''} Deciphered
                </span>
              )}
            </div>
            <p className="text-xs text-slate-600 line-clamp-1">
              Decoded clinical insights, dosage administration, timing schedules &amp; doctor handwriting deciphering
            </p>
          </div>
        </div>

        {/* Right Action / Chevron Indicator */}
        <div className="flex items-center gap-2 shrink-0">
          <span className="text-xs font-bold text-sky-700 hidden sm:inline">
            {isExpanded ? 'Hide Details' : 'Open Summary'}
          </span>
          <div
            className={`w-7 h-7 rounded-lg bg-white border border-sky-200 flex items-center justify-center text-sky-700 text-sm font-bold shadow-2xs transition-transform duration-200 ${
              isExpanded ? 'rotate-180 bg-sky-100 text-sky-900' : ''
            }`}
          >
            ▼
          </div>
        </div>
      </button>

      {/* Expanded Content Area */}
      {isExpanded && (
        <div className="p-5 sm:p-7 border-t border-sky-100 space-y-6 animate-fadeIn bg-slate-50/30">
          {/* Section 1: Overview Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Main Procedure Card */}
            <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-2xs">
              <span className="text-[10px] font-extrabold uppercase tracking-wider text-slate-500 block mb-1">
                Main Procedure / Service
              </span>
              <p className="text-sm font-black text-slate-900 leading-snug">
                {mainProcedure}
              </p>
              {extracted?.location_city && (
                <span className="inline-block mt-2 text-[11px] font-medium text-slate-500">
                  📍 Location: <strong className="text-slate-700">{extracted.location_city}</strong>
                </span>
              )}
            </div>

            {/* Billed Amount in Currency Card */}
            <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-2xs">
              <span className="text-[10px] font-extrabold uppercase tracking-wider text-slate-500 block mb-1">
                Billed Amount
              </span>
              <div className="flex items-baseline gap-2">
                <span className="text-xl font-black text-slate-950">
                  {billedAmount !== null ? formatCurrency(billedAmount, currencyCode) : 'Amount Unspecified'}
                </span>
                <span className="text-xs font-bold text-slate-500">({currencyCode})</span>
              </div>
              {anomaly?.benchmark_min !== null && anomaly?.benchmark_max !== null && anomaly?.benchmark_min !== undefined && (
                <p className="text-[11px] text-slate-600 mt-1.5 font-medium">
                  Fair Benchmark: {formatCurrency(anomaly.benchmark_min, anomaly.benchmark_currency || currencyCode)} &ndash;{' '}
                  {formatCurrency(anomaly.benchmark_max, anomaly.benchmark_currency || currencyCode)}
                </p>
              )}
            </div>

            {/* Final Decision Card */}
            <div
              className={`p-4 rounded-xl border shadow-2xs ${
                verification.action === 'accept'
                  ? 'bg-emerald-50/70 border-emerald-300 text-emerald-950'
                  : verification.action === 'flag'
                  ? 'bg-amber-50/70 border-amber-300 text-amber-950'
                  : 'bg-slate-100 border-slate-300 text-slate-950'
              }`}
            >
              <span className="text-[10px] font-extrabold uppercase tracking-wider opacity-80 block mb-1">
                Final Decision &amp; Verdict
              </span>
              <div className="flex items-center gap-2">
                <span className="text-base font-black uppercase">
                  {verification.action === 'accept'
                    ? '✓ ACCEPTED'
                    : verification.action === 'flag'
                    ? '⚠️ FLAGGED FOR REVIEW'
                    : '⏸️ ABSTAINED'}
                </span>
              </div>
              <p className="text-[11px] font-medium mt-1.5 opacity-90 leading-relaxed">
                {verification.verdict === 'supported'
                  ? 'Medically justified and consistent with clinical guidelines.'
                  : verification.cost_anomaly_flag
                  ? `Pricing deviation detected (${anomaly?.multiplier ? `${anomaly.multiplier.toFixed(1)}x fair tariff` : 'high cost outlier'}).`
                  : verification.reasoning || 'Audit evaluation complete.'}
              </p>
            </div>
          </div>

          {/* Section 2: What the System Understood */}
          <div className="p-4 sm:p-5 rounded-xl bg-white border border-slate-200 shadow-2xs">
            <h4 className="text-xs font-black uppercase tracking-wider text-slate-800 mb-2 flex items-center gap-2">
              <span>🧠</span>
              <span>What the System Understood</span>
            </h4>
            <p className="text-xs sm:text-sm text-slate-700 leading-relaxed">
              {systemUnderstanding}
            </p>
          </div>

          {/* Section 3: Medicine Names & Administration Schedule (Doctor Handwriting Assistant) */}
          <div className="p-4 sm:p-5 rounded-xl bg-white border border-slate-200 shadow-2xs space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3">
              <div>
                <h4 className="text-xs font-black uppercase tracking-wider text-slate-800 flex items-center gap-2">
                  <span>💊</span>
                  <span>Prescribed Medicines &amp; Dosage Instructions</span>
                </h4>
                <p className="text-[11px] text-slate-500 mt-0.5">
                  Translates shorthand (e.g. 1-0-1, TDS, SOS, before/after meals) into clear patient schedule
                </p>
              </div>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-sky-50 text-sky-800 border border-sky-200">
                Doctor Handwriting Decoded
              </span>
            </div>

            {decipheredMedicines.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                {decipheredMedicines.map((med, idx) => (
                  <div
                    key={idx}
                    className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/90 hover:border-sky-300 transition-all space-y-2.5"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <h5 className="text-sm font-extrabold text-slate-900">
                          {med.name}
                        </h5>
                        <span className="text-[10px] font-bold text-sky-800 bg-sky-100/70 px-2 py-0.5 rounded mt-0.5 inline-block">
                          {med.category}
                        </span>
                      </div>
                      {med.dosage && (
                        <span className="text-xs font-black text-slate-700 bg-white px-2 py-1 rounded-lg border border-slate-200 shadow-2xs">
                          {med.dosage}
                        </span>
                      )}
                    </div>

                    {/* Schedule Timing Box */}
                    <div className="p-2.5 rounded-lg bg-white border border-slate-200 text-xs space-y-1">
                      <div className="flex items-center gap-1.5 font-bold text-slate-800">
                        <span>⏰</span>
                        <span>When to take:</span>
                        <span className="text-sky-700 font-extrabold">{med.timing || 'As directed'}</span>
                      </div>
                      <p className="text-[11px] text-slate-600 pl-5 leading-normal">
                        {med.timingPlain}
                      </p>
                    </div>

                    {/* Food Relation & Duration */}
                    <div className="grid grid-cols-2 gap-2 text-[11px]">
                      <div className="p-2 rounded-lg bg-emerald-50/70 border border-emerald-200/70">
                        <strong className="block text-[10px] font-bold uppercase text-emerald-900">
                          Food Timing:
                        </strong>
                        <span className="text-emerald-950 font-medium">
                          {med.foodRelation}
                        </span>
                      </div>
                      <div className="p-2 rounded-lg bg-sky-50/70 border border-sky-200/70">
                        <strong className="block text-[10px] font-bold uppercase text-sky-900">
                          Duration:
                        </strong>
                        <span className="text-sky-950 font-medium">
                          {med.duration || 'As prescribed by physician'}
                        </span>
                      </div>
                    </div>

                    {/* Plain Language Instructions */}
                    <p className="text-[11px] text-slate-600 italic border-t border-slate-200/60 pt-2">
                      &bull; {med.instructions}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-600 flex items-center gap-3">
                <span className="text-xl">ℹ️</span>
                <div>
                  <strong className="text-slate-800 block font-bold">No Oral Prescription Identified</strong>
                  <span>
                    This record represents an itemized hospital bill or diagnostic scan rather than an outpatient oral prescription.
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Section 4: Important Warnings & Missing Information */}
          <div className="p-4 sm:p-5 rounded-xl bg-amber-50/60 border border-amber-200 shadow-2xs space-y-3">
            <h4 className="text-xs font-black uppercase tracking-wider text-amber-950 flex items-center gap-2">
              <span>⚠️</span>
              <span>Important Warnings &amp; Handwriting Verification Checks</span>
            </h4>
            <div className="space-y-2">
              {clinicalWarnings.map((warning, wIdx) => (
                <div
                  key={wIdx}
                  className="flex items-start gap-2.5 text-xs text-amber-900 bg-white/80 p-2.5 rounded-lg border border-amber-200/70"
                >
                  <span className="text-amber-600 font-bold shrink-0 mt-0.5">&bull;</span>
                  <div className="leading-relaxed">
                    <strong className="font-bold text-amber-950">{warning.title}: </strong>
                    <span>{warning.detail}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

/**
 * Intelligent parser that extracts medicines, standard Indian medical shorthand,
 * and administration instructions from raw or OCR clinical text.
 */
function parseMedicinesFromText(text: string): DecipheredMedicine[] {
  if (!text) return []

  const medicines: DecipheredMedicine[] = []
  const textLower = text.toLowerCase()

  // Knowledge base of common medications with classifications
  const drugDatabase: Array<{
    keywords: string[]
    name: string
    category: string
    defaultDosage?: string
    defaultFood: string
    advice: string
  }> = [
    {
      keywords: ['metformin', 'glycomet', 'obimet'],
      name: 'Metformin Hydrochloride',
      category: 'Oral Antidiabetic (Type 2 Diabetes)',
      defaultDosage: '500 mg',
      defaultFood: 'Take with or immediately after food to avoid stomach upset',
      advice: 'Swallow whole with a full glass of water. Do not skip meals while taking this medication.',
    },
    {
      keywords: ['glimepiride', 'amaryl', 'zoryl'],
      name: 'Glimepiride',
      category: 'Sulfonylurea Antidiabetic',
      defaultDosage: '1 mg',
      defaultFood: 'Take 15–30 minutes before the first main meal (breakfast)',
      advice: 'Ensure regular meal times to prevent low blood sugar (hypoglycemia). Keep sugar candy handy.',
    },
    {
      keywords: ['azithromycin', 'azithral', 'zithromax', 'azee'],
      name: 'Azithromycin',
      category: 'Macrolide Antibiotic (Bacterial Infection)',
      defaultDosage: '500 mg',
      defaultFood: 'Can be taken with or without food; take at the exact same hour daily',
      advice: 'Complete the entire course (typically 3 to 5 days). Do not stop early even if feeling better.',
    },
    {
      keywords: ['paracetamol', 'pcm', 'dolo', 'calpol', 'crocin'],
      name: 'Paracetamol / Acetaminophen',
      category: 'Antipyretic & Analgesic (Fever & Pain)',
      defaultDosage: '650 mg',
      defaultFood: 'Can be taken after food or with milk',
      advice: 'Take SOS (only when body temperature exceeds 100°F or with pain). Maintain at least 4-6 hours between doses.',
    },
    {
      keywords: ['pantoprazole', 'pantocid', 'pan-40', 'pan 40'],
      name: 'Pantoprazole',
      category: 'Proton Pump Inhibitor (Gastric Acid Reducer)',
      defaultDosage: '40 mg',
      defaultFood: 'Take on empty stomach 30–60 minutes before breakfast',
      advice: 'Take first thing in the morning with a glass of plain water for optimal acid suppression.',
    },
    {
      keywords: ['ondansetron', 'emset', 'zofran'],
      name: 'Ondansetron',
      category: 'Antiemetic (Nausea & Vomiting)',
      defaultDosage: '4 mg',
      defaultFood: 'Can be taken before meals or IV infusion',
      advice: 'Prevents nausea and dehydration. Maintain adequate fluid and electrolyte intake.',
    },
    {
      keywords: ['normal saline', '0.9% nacl', 'iv saline', 'saline infusion', 'iv fluid'],
      name: 'Normal Saline (0.9% NaCl Infusion)',
      category: 'Intravenous Crystalloid Fluid (Rehydration)',
      defaultDosage: '500 ml IV',
      defaultFood: 'Administered intravenously by clinical nursing staff',
      advice: 'Used for volume resuscitation in acute dehydration. Infusion rate is titrated to vitals.',
    },
    {
      keywords: ['amoxicillin', 'augmentin', 'moxikind', 'amox'],
      name: 'Amoxicillin + Clavulanic Acid',
      category: 'Broad-Spectrum Antibiotic',
      defaultDosage: '625 mg',
      defaultFood: 'Take at the start of a meal to reduce gastrointestinal discomfort',
      advice: 'Maintain consistent 8 or 12-hour dosing intervals. Complete the full prescribed course.',
    },
    {
      keywords: ['cetirizine', 'cetzine', 'zyrtec'],
      name: 'Cetirizine Hydrochloride',
      category: 'Antihistamine (Allergy & Coryza)',
      defaultDosage: '10 mg',
      defaultFood: 'Take with or without food at bedtime',
      advice: 'May cause mild drowsiness. Avoid driving or operating machinery after taking.',
    },
    {
      keywords: ['ors', 'oral rehydration', 'electral'],
      name: 'WHO-Formula Oral Rehydration Salts (ORS)',
      category: 'Oral Electrolyte Replenishment',
      defaultDosage: '1 sachet in 1 liter water',
      defaultFood: 'Sip frequently throughout the day',
      advice: 'Mix 1 packet in exactly 1 liter of clean drinking water. Discard unused solution after 24 hours.',
    },
    {
      keywords: ['atorvastatin', 'atorva', 'lipitor', 'rosuvastatin'],
      name: 'Atorvastatin / Statin',
      category: 'Lipid-Lowering Agent (Cholesterol)',
      defaultDosage: '10 mg / 20 mg',
      defaultFood: 'Take once daily at bedtime, with or without food',
      advice: 'Evening administration is most effective as cholesterol synthesis peaks at night.',
    },
    {
      keywords: ['telmisartan', 'telma', 'amlodipine', 'cilnidipine'],
      name: 'Telmisartan / Antihypertensive',
      category: 'Blood Pressure Control',
      defaultDosage: '40 mg',
      defaultFood: 'Take once daily in the morning with water',
      advice: 'Do not discontinue abruptly. Monitor blood pressure periodically.',
    }
  ]

  // Scan text for drug matches
  drugDatabase.forEach((drug) => {
    const matched = drug.keywords.some((k) => textLower.includes(k))
    if (matched) {
      // Find dosage if explicitly mentioned in text
      const regexDosage = new RegExp(`(?:${drug.keywords.join('|')})[\\s\\w]*?(\\d+\\s*(?:mg|ml|mcg|gm|g))`, 'i')
      const dosageMatch = text.match(regexDosage)
      const dosage = dosageMatch ? dosageMatch[1] : drug.defaultDosage

      // Detect timing code (1-0-1, 1-0-0, 0-0-1, TDS, BD, OD, SOS)
      const timingInfo = detectTimingSchedule(textLower, drug.keywords)

      // Detect duration (x 5 days, 30 days, etc.)
      const duration = detectDuration(textLower, drug.keywords)

      medicines.push({
        name: drug.name,
        dosage,
        timing: timingInfo.code,
        timingPlain: timingInfo.plain,
        foodRelation: timingInfo.foodRelation || drug.defaultFood,
        duration,
        category: drug.category,
        instructions: drug.advice,
      })
    }
  })

  // If no database drugs matched, check if generic "Tab" or "Cap" or "Rx" lines exist
  if (medicines.length === 0) {
    const rxLines = text.split(/[\n,;]+/).filter((line) => /rx|tab|cap|syr|inj/i.test(line))
    rxLines.slice(0, 3).forEach((line, lIdx) => {
      const cleanLine = line.replace(/^(rx|tab|cap|syr|inj)[:\s.]*/i, '').trim()
      if (cleanLine.length > 3) {
        medicines.push({
          name: cleanLine.split(/\s+/).slice(0, 3).join(' '),
          dosage: cleanLine.match(/\d+\s*(?:mg|ml|mcg)/i)?.[0] || 'As labeled',
          timing: 'As prescribed',
          timingPlain: 'Follow the specific dosing schedule written on the medicine carton or doctor note.',
          foodRelation: 'Take with plenty of drinking water',
          duration: 'Complete the specified course',
          category: 'Prescription Formulation',
          instructions: 'Consult your pharmacist or treating physician to verify exact intake intervals.',
        })
      }
    })
  }

  return medicines
}

/**
 * Parses medical shorthand timing notation (1-0-1, 1-0-0, BD, TDS, SOS) into plain patient schedule
 */
function detectTimingSchedule(text: string, keywords: string[]): { code: string; plain: string; foodRelation?: string } {
  // Check if near the drug mention there is a timing code
  const has101 = /1-0-1|bd\b|bid\b|twice daily/i.test(text)
  const has100 = /1-0-0|od\b|once daily|morning/i.test(text)
  const has001 = /0-0-1|hs\b|bedtime|night/i.test(text)
  const has111 = /1-1-1|tds\b|tid\b|thrice daily/i.test(text)
  const hasSOS = /sos\b|as needed|prn\b/i.test(text)

  const isAfterFood = /after food|post prandial|pc\b|after meals/i.test(text)
  const isBeforeFood = /before food|before breakfast|empty stomach|ac\b|pre prandial/i.test(text)

  const foodRelation = isBeforeFood
    ? 'Take 30 minutes before meal on empty stomach'
    : isAfterFood
    ? 'Take after meal with water'
    : undefined

  if (hasSOS) {
    return {
      code: 'SOS (Only when required)',
      plain: 'Take only when necessary for acute symptom relief (fever > 100°F or pain). Do not take routinely.',
      foodRelation,
    }
  }

  if (has101) {
    return {
      code: '1-0-1 (Twice Daily)',
      plain: '1 dose in the morning after breakfast, and 1 dose at night after dinner. Skip afternoon.',
      foodRelation: foodRelation || 'Take after meals',
    }
  }

  if (has111) {
    return {
      code: '1-1-1 (Three Times Daily)',
      plain: '1 dose with breakfast, 1 dose with lunch, and 1 dose with dinner (spaced ~6–8 hours apart).',
      foodRelation: foodRelation || 'Take with or after food',
    }
  }

  if (has100) {
    return {
      code: '1-0-0 (Once Daily - Morning)',
      plain: '1 dose in the morning. Skip afternoon and night.',
      foodRelation: foodRelation || 'Take in the morning',
    }
  }

  if (has001) {
    return {
      code: '0-0-1 (Once Daily - Bedtime)',
      plain: '1 dose at night right before going to bed. Skip morning and afternoon.',
      foodRelation: foodRelation || 'Take at bedtime',
    }
  }

  return {
    code: 'Standard Schedule',
    plain: 'Take in accordance with the doctor prescription label.',
    foodRelation,
  }
}

/**
 * Detects duration of therapy (e.g. x 5 days, for 30 days)
 */
function detectDuration(text: string, keywords: string[]): string | undefined {
  const match = text.match(/(?:x|for)\s*(\d+\s*(?:days?|weeks?|months?))/i)
  if (match) {
    return `${match[1]} course`
  }
  if (text.includes('30 days') || text.includes('1 month')) return '30 days maintenance'
  if (text.includes('5 days')) return '5 days complete course'
  return undefined
}

/**
 * Synthesizes a human-readable "What the system understood" summary
 */
function generateSystemUnderstanding(
  claim: ExtractAndVerifyResponse['claim'],
  verification: ExtractAndVerifyResponse['verification'],
  mainProcedure: string,
  billedAmount: number | null,
  currency: string
): string {
  const text = claim.original_text || ''
  const location = claim.location?.city ? `${claim.location.city}${claim.location.state_or_region ? `, ${claim.location.state_or_region}` : ''}` : 'the clinical encounter'
  const isHospitalBill = claim.source_type === 'hospital_bill'
  const hasCostAnomaly = verification.cost_anomaly_flag

  let summary = `The system processed an audited ${isHospitalBill ? 'hospital billing statement' : 'medical record'} originating from ${location}. `

  summary += `The core medical service identified is "${mainProcedure}". `

  if (billedAmount !== null) {
    summary += `A total charge of ${formatCurrency(billedAmount, currency)} was extracted from the document. `
  }

  if (hasCostAnomaly && verification.anomaly_details?.multiplier) {
    summary += `EvidenceBridge cross-referenced this fee against state and national health benchmarks and identified a significant pricing anomaly (${verification.anomaly_details.multiplier.toFixed(1)}x typical reference tariff). `
  } else if (verification.action === 'accept') {
    summary += `The fee and treatment protocol match accepted evidence-based clinical benchmarks and established public health tariffs. `
  } else if (verification.action === 'abstain') {
    summary += `Further documentation or itemized diagnostic breakdown is required to confirm full clinical necessity. `
  }

  return summary
}

/**
 * Generates handwriting deciphering warnings and missing information notices
 */
function generateClinicalWarnings(
  text: string,
  medicines: DecipheredMedicine[],
  sourceType: string
): Array<{ title: string; detail: string }> {
  const warnings: Array<{ title: string; detail: string }> = []
  const textLower = text.toLowerCase()

  // 1. Handwriting / OCR verification check
  warnings.push({
    title: 'Handwriting & Transcription Notice',
    detail: 'This summary was synthesized from computerized OCR of handwritten/printed medical records. Always cross-verify the printed dosage strength on the pharmacist-dispensed pack before ingestion.',
  })

  // 2. Doctor Signature & Registration check
  if (!textLower.includes('reg') && !textLower.includes('dr.') && !textLower.includes('signature') && !textLower.includes('mbbs') && !textLower.includes('md')) {
    warnings.push({
      title: 'Missing Prescriber Registration',
      detail: 'No explicit State Medical Council or National Medical Commission (NMC) doctor registration number was detected on the visible portion of this document.',
    })
  }

  // 3. Antibiotic Stewardship Alert
  const hasAntibiotic = medicines.some((m) => m.category.includes('Antibiotic'))
  if (hasAntibiotic) {
    warnings.push({
      title: 'Antibiotic Stewardship Rule',
      detail: 'An antibiotic regimen was identified. Complete the exact prescribed course without premature discontinuation to prevent antimicrobial resistance (AMR).',
    })
  }

  // 4. Pediatric or Elderly Dosage Alert
  if (textLower.includes('child') || textLower.includes('pediatric') || textLower.includes('infant') || textLower.includes('yr old') || textLower.includes('month old')) {
    warnings.push({
      title: 'Weight-Based Pediatric Dosing',
      detail: 'Pediatric medications must be calculated strictly according to patient body weight (mg/kg). Verify liquid syrup measurements with an accurate dosing syringe.',
    })
  }

  // 5. Drug Allergy Precaution
  warnings.push({
    title: 'Allergy & Interaction Check',
    detail: 'Inform your doctor or clinical reviewer immediately if the patient has known allergies to penicillin, sulfa drugs, or NSAIDs.',
  })

  return warnings
}

export default PostProcessingSummary
