import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { AuthModal } from '../components/AuthModal'
import Logo, { EbMark } from '../components/Logo'

export default function Landing() {
  const { isAuthenticated, demoLogin } = useAuth()
  const navigate = useNavigate()
  const [authModalOpen, setAuthModalOpen] = useState(false)
  const [authModalMode, setAuthModalMode] = useState<'login' | 'signup'>('login')

  const handleGetStarted = () => {
    if (isAuthenticated) {
      navigate('/audit')
    } else {
      demoLogin()
      navigate('/audit')
    }
  }

  const handleOpenAuth = (mode: 'login' | 'signup') => {
    setAuthModalMode(mode)
    setAuthModalOpen(true)
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans text-slate-800">
      {/* Top Navbar */}
      <header className="bg-white/95 backdrop-blur-sm sticky top-0 z-40 border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          {/* Brand */}
          <div className="flex items-center gap-3">
            <Logo size="md" showText={true} subtext="Medical Evidence & Billing Audit" />
          </div>

          {/* Navigation & CTAs */}
          <div className="flex items-center gap-3">
            <a
              href="#how-it-works"
              className="hidden md:inline-block text-xs font-semibold text-slate-600 hover:text-slate-900 px-3 py-1.5 transition-colors"
            >
              How It Works
            </a>
            <a
              href="#sample-scenarios"
              className="hidden md:inline-block text-xs font-semibold text-slate-600 hover:text-slate-900 px-3 py-1.5 transition-colors"
            >
              Sample Audits
            </a>

            {isAuthenticated ? (
              <button
                type="button"
                onClick={() => navigate('/audit')}
                className="px-4 py-2 text-xs font-bold rounded-lg bg-sky-600 hover:bg-sky-700 text-white transition-colors shadow-sm"
              >
                Go to Workspace &rarr;
              </button>
            ) : (
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => handleOpenAuth('login')}
                  className="px-3 py-2 text-xs font-bold text-slate-700 hover:text-slate-900 transition-colors"
                >
                  Sign In
                </button>
                <button
                  type="button"
                  onClick={handleGetStarted}
                  className="px-4 py-2 text-xs font-bold rounded-lg bg-sky-600 hover:bg-sky-700 text-white transition-colors shadow-sm inline-flex items-center gap-1.5"
                >
                  <span>⚡ Try Demo (1-Click)</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative overflow-hidden bg-gradient-to-b from-white via-slate-50 to-slate-100/70 pt-12 pb-20 border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto">
            {/* Pill Banner */}
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-sky-50 border border-sky-200 text-sky-800 text-xs font-semibold mb-6 shadow-subtle">
              <span className="w-2 h-2 rounded-full bg-sky-500 animate-pulse" />
              <span>Offline-First Clinical Auditing &bull; Zero Data Leaks &bull; Full Transparency</span>
            </div>

            {/* Main Headline */}
            <h1 className="text-3xl sm:text-5xl font-black text-slate-900 tracking-tight leading-tight">
              Audit hospital bills &amp; medical claims with{' '}
              <span className="bg-gradient-to-r from-sky-600 to-teal-600 bg-clip-text text-transparent">
                total transparency.
              </span>
            </h1>

            {/* Subtitle in Plain English */}
            <p className="mt-5 text-base sm:text-lg text-slate-600 leading-relaxed">
              We check medical claims against authoritative guidelines and public pricing benchmarks.
              Every decision is explained in plain English with an inspectable 7-stage audit trail — no guessing, no black boxes.
            </p>

            {/* CTA Group */}
            <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-3">
              <button
                type="button"
                onClick={handleGetStarted}
                className="w-full sm:w-auto px-7 py-3 rounded-xl bg-sky-600 hover:bg-sky-700 text-white font-bold text-sm shadow-md transition-all flex items-center justify-center gap-2"
              >
                <span>Audit a Claim Now</span>
                <span>&rarr;</span>
              </button>

              <button
                type="button"
                onClick={() => {
                  demoLogin()
                  navigate('/claims')
                }}
                className="w-full sm:w-auto px-6 py-3 rounded-xl bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 font-bold text-sm shadow-sm transition-all flex items-center justify-center gap-2"
              >
                <span>Browse Audited Claims</span>
              </button>
            </div>

            {/* Trust Badges */}
            <div className="mt-8 pt-6 border-t border-slate-200/80 flex flex-wrap items-center justify-center gap-6 text-xs text-slate-500">
              <div className="flex items-center gap-1.5">
                <span className="text-emerald-600 font-bold">✓</span>
                <span>100% Local &amp; Private</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="text-emerald-600 font-bold">✓</span>
                <span>CMS &amp; Fair Health Benchmarks</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="text-emerald-600 font-bold">✓</span>
                <span>SHA-256 Tamper Verification</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="text-emerald-600 font-bold">✓</span>
                <span>Deterministic Safety Rules</span>
              </div>
            </div>
          </div>

          {/* Interactive Hero Graphic: Sample Real Audit Card */}
          <div className="mt-14 max-w-4xl mx-auto bg-white rounded-2xl border border-slate-200 shadow-xl overflow-hidden">
            <div className="bg-gradient-to-r from-slate-900 to-navy-900 text-white p-4 sm:px-6 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <span className="w-3 h-3 rounded-full bg-rose-500" />
                <span className="w-3 h-3 rounded-full bg-amber-500" />
                <span className="w-3 h-3 rounded-full bg-emerald-500" />
                <span className="text-xs font-mono text-slate-300 ml-2">
                  Sample Audit Line &bull; MidWest General Hospital
                </span>
              </div>
              <span className="text-[11px] font-mono bg-white/10 px-2 py-0.5 rounded text-slate-300">
                Tamper-Verified SHA-256
              </span>
            </div>

            <div className="p-6 sm:p-8 space-y-6">
              {/* Claim Description */}
              <div className="flex flex-col sm:flex-row justify-between sm:items-start gap-4 pb-6 border-b border-slate-100">
                <div>
                  <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                    Billed Hospital Item
                  </span>
                  <h3 className="text-lg font-bold text-slate-900 mt-0.5">
                    0.9% Sodium Chloride (Normal Saline) IV Solution, 1,000 mL Infusion Bag
                  </h3>
                  <p className="text-xs text-slate-500 mt-1">
                    Indication: Emergency department acute dehydration &bull; Cleveland, OH
                  </p>
                </div>

                <div className="text-right sm:self-start bg-slate-50 p-3 rounded-xl border border-slate-200">
                  <div className="text-[10px] uppercase font-semibold text-slate-500">Billed Charge</div>
                  <div className="text-2xl font-black font-mono text-slate-900 mt-0.5">$720.00</div>
                  <div className="text-[10px] text-slate-500">Benchmark: $5 – $45</div>
                </div>
              </div>

              {/* The Dual Decision Outcome */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Clinical Guideline Review */}
                <div className="p-4 rounded-xl bg-emerald-50/70 border border-emerald-200">
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-xs font-bold text-emerald-900 uppercase tracking-wide">
                      1. Medical Guidelines
                    </span>
                    <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-emerald-100 text-emerald-800">
                      ✓ Supported
                    </span>
                  </div>
                  <p className="text-xs text-emerald-900 leading-relaxed">
                    Normal saline is standard, essential clinical therapy for extracellular fluid replacement and acute dehydration under USP &amp; CDC guidelines.
                  </p>
                </div>

                {/* Price Benchmark Audit */}
                <div className="p-4 rounded-xl bg-amber-50/80 border border-amber-200">
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-xs font-bold text-amber-900 uppercase tracking-wide">
                      2. Price Benchmark Audit
                    </span>
                    <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-amber-100 text-amber-900">
                      ⚠ 16.0× Markup Anomaly
                    </span>
                  </div>
                  <p className="text-xs text-amber-900 leading-relaxed">
                    Typical hospital acquisition and supply benchmark is $5 to $45. The billed charge of $720.00 is an extreme markup requiring review.
                  </p>
                </div>
              </div>

              {/* Final Operational Decision Callout */}
              <div className="p-4 rounded-xl bg-slate-900 text-white flex flex-col sm:flex-row items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-amber-500/20 text-amber-400 flex items-center justify-center font-bold text-lg border border-amber-500/30">
                    !
                  </div>
                  <div>
                    <div className="text-xs font-bold text-amber-300 uppercase tracking-wider">
                      Audit Policy Decision: Flag for Human Itemization Review
                    </div>
                    <div className="text-xs text-slate-300 mt-0.5">
                      Safety policy intervened: Flagged for extreme price markup despite medical necessity.
                    </div>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={handleGetStarted}
                  className="px-4 py-2 text-xs font-bold bg-sky-500 hover:bg-sky-400 text-slate-950 rounded-lg transition-colors whitespace-nowrap"
                >
                  Inspect Full 7-Stage Audit Graph &rarr;
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 3 Core Pillars Section */}
      <section className="py-16 bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-2xl mx-auto mb-12">
            <h2 className="text-xs font-bold uppercase tracking-widest text-sky-600 mb-2">
              Why Healthcare Auditing Needs Transparency
            </h2>
            <p className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight">
              Built to replace black-box automated denials with clear evidence.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {/* Pillar 1 */}
            <div className="bg-slate-50 rounded-2xl p-6 border border-slate-200/80 hover:shadow-md transition-shadow">
              <div className="w-12 h-12 rounded-xl bg-sky-100 text-sky-700 flex items-center justify-center text-xl mb-4">
                🩺
              </div>
              <h3 className="text-base font-bold text-slate-900">
                See Why a Claim Was Decided
              </h3>
              <p className="text-xs text-slate-600 mt-2 leading-relaxed">
                No cryptic reason codes. Every audit cites authoritative excerpts from medical organizations like the ADA, ACR, and CDC, clearly explaining clinical relevance.
              </p>
            </div>

            {/* Pillar 2 */}
            <div className="bg-slate-50 rounded-2xl p-6 border border-slate-200/80 hover:shadow-md transition-shadow">
              <div className="w-12 h-12 rounded-xl bg-amber-100 text-amber-700 flex items-center justify-center text-xl mb-4">
                💰
              </div>
              <h3 className="text-base font-bold text-slate-900">
                Spot Hidden Price Markups
              </h3>
              <p className="text-xs text-slate-600 mt-2 leading-relaxed">
                Compares line items against CMS Medicare and Fair Health public benchmarks. Instantly flags 3×, 5×, and 16× markup anomalies on routine items like saline and venipuncture.
              </p>
            </div>

            {/* Pillar 3 */}
            <div className="bg-slate-50 rounded-2xl p-6 border border-slate-200/80 hover:shadow-md transition-shadow">
              <div className="w-12 h-12 rounded-xl bg-clinical-100 text-clinical-700 flex items-center justify-center text-xl mb-4">
                🛡️
              </div>
              <h3 className="text-base font-bold text-slate-900">
                Safe Refusals — We Never Guess
              </h3>
              <p className="text-xs text-slate-600 mt-2 leading-relaxed">
                When guidelines are missing or price benchmarks do not exist for high-cost experimental procedures, EvidenceBridge safely holds the claim for human review instead of hallucinating.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Human-Centered Story & Patient Advocacy Spotlight */}
      <section className="py-20 bg-gradient-to-b from-white via-sky-50/40 to-slate-50 border-b border-slate-200 overflow-hidden">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-14 items-center">
            {/* Left Column: Doctor-Patient Image Card */}
            <div className="lg:col-span-6 relative">
              {/* Soft Ambient Glow */}
              <div className="absolute -inset-4 bg-gradient-to-tr from-sky-200/50 to-teal-100/40 rounded-3xl blur-2xl -z-10" />

              <div className="relative rounded-2xl sm:rounded-3xl overflow-hidden border border-slate-200/90 shadow-2xl bg-white group">
                <img
                  src="/doctor-patient.jpg"
                  alt="Doctor showing healthcare brochure to patient during consultation"
                  className="w-full h-auto object-cover aspect-[16/10] sm:aspect-[16/9] group-hover:scale-[1.02] transition-transform duration-500"
                  loading="lazy"
                />

                {/* Floating Trust Overlay Card */}
                <div className="absolute bottom-4 left-4 right-4 sm:left-6 sm:right-6 p-3.5 sm:p-4 rounded-xl sm:rounded-2xl bg-white/95 backdrop-blur-md border border-slate-200/90 shadow-lg flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-sky-100 text-sky-700 flex items-center justify-center text-xl flex-shrink-0">
                    🤝
                  </div>
                  <div>
                    <div className="text-xs font-bold text-slate-900">
                      Patient Advocacy &amp; Billing Clarity
                    </div>
                    <div className="text-[11px] text-slate-600 font-medium leading-tight mt-0.5">
                      Citing medical guidelines and regional fair prices so patients can understand their care.
                    </div>
                  </div>
                </div>
              </div>

              {/* Subtitle Caption */}
              <p className="mt-3 text-center sm:text-left text-xs text-slate-500 italic">
                EvidenceBridge helps patients and clinical reviewers verify that every charge is medically sound and reasonably priced.
              </p>
            </div>

            {/* Right Column: Narrative & Values */}
            <div className="lg:col-span-6 space-y-6">
              <div>
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-sky-100/80 text-sky-800 border border-sky-200 mb-3">
                  <span className="w-1.5 h-1.5 rounded-full bg-sky-600" />
                  Human-Centered Clinical Auditing
                </span>
                <h2 className="text-2xl sm:text-4xl font-extrabold text-slate-900 tracking-tight leading-tight">
                  Healthcare bills you can actually understand and discuss.
                </h2>
                <p className="mt-3 text-sm sm:text-base text-slate-600 leading-relaxed">
                  Medical bills shouldn&apos;t feel like a foreign language or an unchallengeable demand. EvidenceBridge replaces confusing denial codes and opaque hospital charges with clear, evidence-based explanations.
                </p>
              </div>

              <div className="space-y-3.5 pt-1">
                {/* Benefit 1 */}
                <div className="flex items-start gap-3.5 p-3.5 rounded-xl bg-white border border-slate-200/80 shadow-xs">
                  <div className="w-8 h-8 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold text-sm flex-shrink-0 mt-0.5">
                    ✓
                  </div>
                  <div>
                    <div className="text-xs font-bold text-slate-900">
                      Plain-English Explanations, Not Bureaucratic Acronyms
                    </div>
                    <div className="text-xs text-slate-600 mt-0.5 leading-relaxed">
                      See exactly why an IV bag, MRI scan, or medication was prescribed and how established clinical guidelines evaluate its medical indication.
                    </div>
                  </div>
                </div>

                {/* Benefit 2 */}
                <div className="flex items-start gap-3.5 p-3.5 rounded-xl bg-white border border-slate-200/80 shadow-xs">
                  <div className="w-8 h-8 rounded-lg bg-amber-100 text-amber-700 flex items-center justify-center font-bold text-sm flex-shrink-0 mt-0.5">
                    ⚠
                  </div>
                  <div>
                    <div className="text-xs font-bold text-slate-900">
                      Transparent Protection Against Extreme Price Markups
                    </div>
                    <div className="text-xs text-slate-600 mt-0.5 leading-relaxed">
                      Identify when routine items like a saline bag are marked up 16× above CMS and Fair Health public benchmarks ($720 vs $5–$45).
                    </div>
                  </div>
                </div>

                {/* Benefit 3 */}
                <div className="flex items-start gap-3.5 p-3.5 rounded-xl bg-white border border-slate-200/80 shadow-xs">
                  <div className="w-8 h-8 rounded-lg bg-sky-100 text-sky-700 flex items-center justify-center font-bold text-sm flex-shrink-0 mt-0.5">
                    🛡️
                  </div>
                  <div>
                    <div className="text-xs font-bold text-slate-900">
                      Constructive, Evidence-Backed Dialogue
                    </div>
                    <div className="text-xs text-slate-600 mt-0.5 leading-relaxed">
                      Equip patients, hospital advocates, and insurance reviewers with objective, reproducible audit reports so discussions remain respectful and fact-based.
                    </div>
                  </div>
                </div>
              </div>

              {/* Action Button */}
              <div className="pt-2 flex flex-col sm:flex-row items-center gap-3">
                <button
                  type="button"
                  onClick={handleGetStarted}
                  className="w-full sm:w-auto px-6 py-2.5 rounded-xl bg-sky-600 hover:bg-sky-700 text-white font-bold text-xs shadow-subtle transition-all flex items-center justify-center gap-2"
                >
                  <span>Audit a Bill with EvidenceBridge</span>
                  <span>&rarr;</span>
                </button>
                <a
                  href="#sample-scenarios"
                  className="text-xs font-semibold text-sky-700 hover:text-sky-900 hover:underline px-3 py-2 transition-colors"
                >
                  Explore real benchmark examples &darr;
                </a>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section id="how-it-works" className="py-16 bg-slate-50 border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-2xl mx-auto mb-12">
            <h2 className="text-xs font-bold uppercase tracking-widest text-sky-600 mb-2">
              Simple 3-Step Verification
            </h2>
            <p className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight">
              From raw hospital bill to verifiable decision.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 relative">
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm relative">
              <div className="text-xs font-bold text-sky-600 mb-2 font-mono">STEP 01</div>
              <h3 className="text-base font-bold text-slate-900">Paste or Ingest Document</h3>
              <p className="text-xs text-slate-500 mt-2 leading-relaxed">
                Provide a raw clinical note, hospital bill line, or patient report. The system calculates an immutable SHA-256 digital fingerprint to prevent tampering.
              </p>
            </div>

            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm relative">
              <div className="text-xs font-bold text-sky-600 mb-2 font-mono">STEP 02</div>
              <h3 className="text-base font-bold text-slate-900">Hybrid Evidence &amp; Price Match</h3>
              <p className="text-xs text-slate-500 mt-2 leading-relaxed">
                AI and BM25 search evaluate authoritative guidelines and check billed charges against standard CMS/Fair Health price schedules.
              </p>
            </div>

            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm relative">
              <div className="text-xs font-bold text-sky-600 mb-2 font-mono">STEP 03</div>
              <h3 className="text-base font-bold text-slate-900">Inspect the 7-Stage Audit Graph</h3>
              <p className="text-xs text-slate-500 mt-2 leading-relaxed">
                Review the step-by-step decision trail: extraction, provenance, evidence retrieval, cost audit, clinical judgment, safety gates, and final action.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Real-World Controlled Cases Showcase */}
      <section id="sample-scenarios" className="py-16 bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-2xl mx-auto mb-10">
            <h2 className="text-xs font-bold uppercase tracking-widest text-sky-600 mb-2">
              Tested Against Real Clinical Benchmarks
            </h2>
            <p className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight">
              Pre-built scenarios ready to audit in one click.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 hover:border-sky-300 transition-colors">
              <span className="inline-block px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 mb-2">
                ACCEPT &bull; Supported
              </span>
              <h4 className="text-xs font-bold text-slate-900">Type 2 Diabetes Metformin</h4>
              <p className="text-[11px] text-slate-500 mt-1">
                30-day supply ($15.00) matching ADA first-line standards.
              </p>
            </div>

            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 hover:border-sky-300 transition-colors">
              <span className="inline-block px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 mb-2">
                ACCEPT &bull; Supported
              </span>
              <h4 className="text-xs font-bold text-slate-900">Brain MRI (CPT 70551)</h4>
              <p className="text-[11px] text-slate-500 mt-1">
                Progressive headache with neurological signs ($650 charge).
              </p>
            </div>

            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 hover:border-sky-300 transition-colors">
              <span className="inline-block px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800 mb-2">
                FLAG &bull; 16× Markup
              </span>
              <h4 className="text-xs font-bold text-slate-900">Normal Saline IV Overcharge</h4>
              <p className="text-[11px] text-slate-500 mt-1">
                $720 billed for a commodity saline bag (typical max $45).
              </p>
            </div>

            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 hover:border-sky-300 transition-colors">
              <span className="inline-block px-2 py-0.5 rounded text-[10px] font-bold bg-rose-100 text-rose-800 mb-2">
                FLAG &bull; Contradicted
              </span>
              <h4 className="text-xs font-bold text-slate-900">Antibiotics for Bronchitis</h4>
              <p className="text-[11px] text-slate-500 mt-1">
                Azithromycin prescribed for viral bronchitis against CDC guidance.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Call to Action Banner */}
      <section className="py-16 bg-gradient-to-r from-slate-900 via-navy-900 to-sky-950 text-white text-center">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-2xl sm:text-3xl font-black tracking-tight">
            Ready to audit medical claims with verifiable clinical integrity?
          </h2>
          <p className="mt-3 text-sm text-slate-300 max-w-xl mx-auto">
            Run the local-first engine on your machine. Zero cloud accounts required.
          </p>

          <div className="mt-8 flex justify-center gap-3">
            <button
              type="button"
              onClick={handleGetStarted}
              className="px-8 py-3 rounded-xl bg-sky-500 hover:bg-sky-400 text-slate-950 font-bold text-sm shadow-lg transition-colors"
            >
              Launch Auditor Workspace &rarr;
            </button>
          </div>
        </div>
      </section>

      {/* Modern Medical Footer */}
      <footer className="bg-slate-900 text-slate-400 py-10 border-t border-slate-800 text-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row justify-between items-center gap-4">
          <div className="flex items-center gap-2.5">
            <EbMark size={22} />
            <span className="font-bold text-white">EvidenceBridge</span>
            <span>&bull;</span>
            <span>Healthcare Evidence Auditing &amp; Price Anomaly Engine</span>
          </div>

          <div className="text-[11px] text-slate-500 text-center sm:text-right">
            Open-source under Apache-2.0. Designed for healthcare transparency and administrative auditing.
          </div>
        </div>
      </footer>

      {/* Authentication Modal */}
      <AuthModal
        isOpen={authModalOpen}
        onClose={() => setAuthModalOpen(false)}
        initialMode={authModalMode}
        onSuccess={() => navigate('/audit')}
      />
    </div>
  )
}
