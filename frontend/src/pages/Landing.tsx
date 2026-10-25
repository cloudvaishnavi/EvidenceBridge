import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { AuthModal } from '../components/AuthModal'
import Logo, { EbMark } from '../components/Logo'

export default function Landing() {
  const { isAuthenticated, demoLogin } = useAuth()
  const navigate = useNavigate()
  const [authModalOpen, setAuthModalOpen] = useState(false)
  const [authModalMode, setAuthModalMode] = useState<'login' | 'signup'>('login')

  const handleGetStarted = async () => {
    if (isAuthenticated) {
      navigate('/audit')
    } else {
      await demoLogin()
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
          <div className="flex items-center gap-2 sm:gap-4">
            <a
              href="#how-it-works"
              className="hidden md:inline-block text-xs font-semibold text-slate-600 hover:text-slate-900 px-2 py-1.5 transition-colors"
            >
              How It Works
            </a>
            <a
              href="#prescription-clarity"
              className="hidden md:inline-block text-xs font-semibold text-slate-600 hover:text-slate-900 px-2 py-1.5 transition-colors"
            >
              Prescription Clarity
            </a>
            <Link
              to="/community"
              className="hidden lg:inline-block text-xs font-semibold text-slate-600 hover:text-slate-900 px-2 py-1.5 transition-colors"
            >
              Community Stories
            </Link>
            <Link
              to="/hospitals"
              className="hidden lg:inline-block text-xs font-semibold text-slate-600 hover:text-slate-900 px-2 py-1.5 transition-colors"
            >
              Hospital Finder
            </Link>

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
                  className="px-3.5 sm:px-4 py-2 text-xs font-bold rounded-lg bg-sky-600 hover:bg-sky-700 text-white transition-colors shadow-sm inline-flex items-center gap-1.5"
                >
                  <span>⚡ Try Demo</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative overflow-hidden bg-gradient-to-b from-white via-sky-50/20 to-slate-100/60 pt-10 pb-16 sm:pt-14 sm:pb-20 border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-12 items-center">
            {/* Left Column: Headline & Action */}
            <div className="lg:col-span-7 space-y-6">
              {/* Pill Banner */}
              <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-sky-50 border border-sky-200 text-sky-800 text-xs font-semibold shadow-xs">
                <span className="w-2 h-2 rounded-full bg-sky-500 animate-pulse" />
                <span>Local-First Clinical Audit &bull; Karnataka &amp; Pan-India Benchmarks &bull; Zero Data Leaks</span>
              </div>

              {/* Main Headline */}
              <h1 className="text-3xl sm:text-5xl font-black text-slate-900 tracking-tight leading-[1.15]">
                Audit hospital bills &amp; medical claims with{' '}
                <span className="bg-gradient-to-r from-sky-600 via-teal-600 to-emerald-600 bg-clip-text text-transparent">
                  total transparency.
                </span>
              </h1>

              {/* Subtitle */}
              <p className="text-base sm:text-lg text-slate-600 leading-relaxed max-w-2xl">
                Cross-reference hospital bills, clinical notes, and prescriptions against authoritative medical guidelines (WHO, ICMR) and public pricing benchmarks (CGHS, PM-JAY). Every decision is backed by an inspectable 7-stage audit trail — no black boxes, no arbitrary denials.
              </p>

              {/* CTA Group */}
              <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 pt-2">
                <button
                  type="button"
                  onClick={handleGetStarted}
                  className="px-7 py-3 rounded-xl bg-sky-600 hover:bg-sky-700 text-white font-bold text-sm shadow-md transition-all flex items-center justify-center gap-2 group"
                >
                  <span>Audit a Claim Now</span>
                  <span className="group-hover:translate-x-0.5 transition-transform">&rarr;</span>
                </button>

                <button
                  type="button"
                  onClick={async () => {
                    await demoLogin()
                    navigate('/claims')
                  }}
                  className="px-6 py-3 rounded-xl bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 font-bold text-sm shadow-xs transition-all flex items-center justify-center gap-2"
                >
                  <span>Browse Audited Claims</span>
                </button>

                <Link
                  to="/community"
                  className="px-5 py-3 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs sm:text-sm transition-all flex items-center justify-center gap-1.5"
                >
                  <span>💬 Patient Stories</span>
                </Link>
              </div>

              {/* Trust Markers */}
              <div className="pt-4 border-t border-slate-200/80 grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs text-slate-600">
                <div className="flex items-center gap-1.5">
                  <span className="text-emerald-600 font-bold text-sm">✓</span>
                  <span>100% Local &amp; Private</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="text-emerald-600 font-bold text-sm">✓</span>
                  <span>CGHS &amp; Indian Benchmarks</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="text-emerald-600 font-bold text-sm">✓</span>
                  <span>SHA-256 Tamper Proof</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="text-emerald-600 font-bold text-sm">✓</span>
                  <span>Deterministic Safety</span>
                </div>
              </div>
            </div>

            {/* Right Column: Visual Showcase featuring Bill Review Photo */}
            <div className="lg:col-span-5 relative">
              {/* Soft Ambient Glow */}
              <div className="absolute -inset-3 bg-gradient-to-tr from-sky-200/60 to-emerald-200/40 rounded-3xl blur-2xl -z-10" />

              <div className="relative rounded-2xl overflow-hidden border border-slate-200 shadow-2xl bg-white group">
                {/* Photo: Medical Bill Review in Clinical Setting */}
                <div className="relative overflow-hidden aspect-[4/3] bg-slate-100">
                  <img
                    src="/medical-bill-review.jpg"
                    alt="Healthcare advisor and patient reviewing an itemized hospital bill at clinic desk"
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700 ease-out"
                    loading="eager"
                  />
                  {/* Subtle Gradient Scrim */}
                  <div className="absolute inset-0 bg-gradient-to-t from-slate-950/80 via-slate-950/20 to-transparent" />

                  {/* Top Floating Badge */}
                  <div className="absolute top-3.5 left-3.5 bg-white/95 backdrop-blur-md px-3 py-1 rounded-full border border-white/60 shadow-md flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
                    <span className="text-[11px] font-bold text-slate-800">Live Itemized Bill Review</span>
                  </div>

                  {/* Bottom Text Overlay */}
                  <div className="absolute bottom-3 left-3 right-3 text-white">
                    <div className="text-[11px] font-semibold text-sky-300 uppercase tracking-wider">
                      Transparent Verification
                    </div>
                    <div className="text-sm font-bold text-white mt-0.5 leading-snug">
                      Comparing hospital charges against public CGHS &amp; Indian market rates
                    </div>
                  </div>
                </div>

                {/* Floating Metric Callout Card */}
                <div className="p-4 bg-white border-t border-slate-100 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="w-2.5 h-2.5 rounded-full bg-rose-500" />
                      <span className="text-xs font-bold text-slate-800">Saline Infusion Markup</span>
                    </div>
                    <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-amber-100 text-amber-900 border border-amber-200">
                      ⚠ 30.0× Anomaly
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-2 bg-slate-50 p-2.5 rounded-xl border border-slate-200/80 text-center">
                    <div>
                      <div className="text-[10px] uppercase font-semibold text-slate-500">Billed Charge</div>
                      <div className="text-base font-black font-mono text-rose-600 mt-0.5">₹1,800</div>
                    </div>
                    <div className="border-l border-slate-200">
                      <div className="text-[10px] uppercase font-semibold text-slate-500">CGHS / Market</div>
                      <div className="text-base font-black font-mono text-emerald-700 mt-0.5">₹30 – ₹60</div>
                    </div>
                  </div>

                  <p className="text-[11px] text-slate-500 leading-normal">
                    Medically justified for acute fluid loss, but flagged for billing desk audit prior to payment.
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Interactive Real Audit Card */}
          <div className="mt-14 max-w-4xl mx-auto bg-white rounded-2xl border border-slate-200 shadow-xl overflow-hidden">
            <div className="bg-gradient-to-r from-slate-900 to-navy-900 text-white p-4 sm:px-6 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <span className="w-3 h-3 rounded-full bg-rose-500" />
                <span className="w-3 h-3 rounded-full bg-amber-500" />
                <span className="w-3 h-3 rounded-full bg-emerald-500" />
                <span className="text-xs font-mono text-slate-300 ml-2">
                  Sample Audit Record &bull; Bengaluru General Care
                </span>
              </div>
              <span className="text-[11px] font-mono bg-white/10 px-2 py-0.5 rounded text-slate-300">
                SHA-256 Verified
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
                    Indication: Emergency department acute dehydration &bull; Bengaluru, Karnataka
                  </p>
                </div>

                <div className="text-right sm:self-start bg-slate-50 p-3 rounded-xl border border-slate-200">
                  <div className="text-[10px] uppercase font-semibold text-slate-500">Billed Charge</div>
                  <div className="text-2xl font-black font-mono text-slate-900 mt-0.5">₹1,800.00</div>
                  <div className="text-[10px] text-slate-500">Benchmark: ₹30 – ₹60</div>
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
                    Normal saline is standard, essential clinical therapy for extracellular fluid replacement and acute dehydration under WHO &amp; ICMR guidelines.
                  </p>
                </div>

                {/* Price Benchmark Audit */}
                <div className="p-4 rounded-xl bg-amber-50/80 border border-amber-200">
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-xs font-bold text-amber-900 uppercase tracking-wide">
                      2. Price Benchmark Audit
                    </span>
                    <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-amber-100 text-amber-900">
                      ⚠ 30.0× Markup Anomaly
                    </span>
                  </div>
                  <p className="text-xs text-amber-900 leading-relaxed">
                    Typical hospital acquisition and supply benchmark is ₹30 to ₹60. The billed charge of ₹1,800.00 is an extreme markup requiring review.
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
            <div className="bg-slate-50 rounded-2xl p-6 border border-slate-200/80 hover:shadow-md transition-shadow flex flex-col justify-between">
              <div>
                <div className="w-12 h-12 rounded-xl bg-sky-100 text-sky-700 flex items-center justify-center text-xl mb-4">
                  🩺
                </div>
                <h3 className="text-base font-bold text-slate-900">
                  Evidence-Based Clinical Auditing
                </h3>
                <p className="text-xs text-slate-600 mt-2 leading-relaxed">
                  No cryptic reason codes. Every audit cites authoritative excerpts from recognized medical organizations like WHO, ICMR, ADA, and ACR, clearly explaining clinical relevance and indication.
                </p>
              </div>
              <div className="mt-4 pt-3 border-t border-slate-200/70 text-[11px] text-sky-700 font-semibold">
                WHO &bull; ICMR &bull; ADA &bull; ACR
              </div>
            </div>

            {/* Pillar 2 */}
            <div className="bg-slate-50 rounded-2xl p-6 border border-slate-200/80 hover:shadow-md transition-shadow flex flex-col justify-between">
              <div>
                <div className="w-12 h-12 rounded-xl bg-amber-100 text-amber-700 flex items-center justify-center text-xl mb-4">
                  💰
                </div>
                <h3 className="text-base font-bold text-slate-900">
                  Transparent Pricing &amp; Anomaly Detection
                </h3>
                <p className="text-xs text-slate-600 mt-2 leading-relaxed">
                  Compares line items against CGHS rate lists and regional public benchmarks. Instantly flags 3×, 5×, and 30× markup anomalies on routine items like saline bags, syringes, and venipuncture.
                </p>
              </div>
              <div className="mt-4 pt-3 border-t border-slate-200/70 text-[11px] text-amber-700 font-semibold">
                CGHS &bull; PM-JAY &bull; Regional Karnataka Tariffs
              </div>
            </div>

            {/* Pillar 3 */}
            <div className="bg-slate-50 rounded-2xl p-6 border border-slate-200/80 hover:shadow-md transition-shadow flex flex-col justify-between">
              <div>
                <div className="w-12 h-12 rounded-xl bg-teal-100 text-teal-700 flex items-center justify-center text-xl mb-4">
                  🛡️
                </div>
                <h3 className="text-base font-bold text-slate-900">
                  Safe Refusals — We Never Guess
                </h3>
                <p className="text-xs text-slate-600 mt-2 leading-relaxed">
                  When guidelines are missing or price benchmarks do not exist for high-cost experimental procedures, EvidenceBridge safely holds the claim for human review instead of hallucinating.
                </p>
              </div>
              <div className="mt-4 pt-3 border-t border-slate-200/70 text-[11px] text-teal-700 font-semibold">
                Abstention Gates &bull; Zero Hallucinations
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Prescription Guidance & Medication Clarity Spotlight (New visual feature) */}
      <section id="prescription-clarity" className="py-20 bg-gradient-to-b from-slate-50 via-sky-50/30 to-white border-b border-slate-200 overflow-hidden">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-14 items-center">
            {/* Left Column: Visual of Doctor / Pharmacist Prescription Guidance */}
            <div className="lg:col-span-6 relative">
              <div className="absolute -inset-4 bg-gradient-to-tr from-teal-200/50 to-sky-200/40 rounded-3xl blur-2xl -z-10" />

              <div className="relative rounded-2xl sm:rounded-3xl overflow-hidden border border-slate-200 shadow-2xl bg-white group">
                <img
                  src="/prescription-guidance.jpg"
                  alt="Doctor patiently explaining prescription schedule and generic medicines to patient"
                  className="w-full h-auto object-cover aspect-[4/3] group-hover:scale-105 transition-transform duration-700"
                  loading="lazy"
                />

                {/* Floating Prescription Clarity Pill */}
                <div className="absolute bottom-4 left-4 right-4 sm:left-6 sm:right-6 p-3.5 sm:p-4 rounded-xl sm:rounded-2xl bg-white/95 backdrop-blur-md border border-slate-200/90 shadow-lg flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-teal-100 text-teal-800 flex items-center justify-center text-xl flex-shrink-0">
                    💊
                  </div>
                  <div>
                    <div className="text-xs font-bold text-slate-900">
                      Prescription Schedule &amp; Generic Alternatives
                    </div>
                    <div className="text-[11px] text-slate-600 font-medium leading-tight mt-0.5">
                      Clear timings (Morning/Night, Before/After Food) and Jan Aushadhi generic equivalents.
                    </div>
                  </div>
                </div>
              </div>

              <p className="mt-3 text-center sm:text-left text-xs text-slate-500 italic">
                Upload or capture any prescription photo to decode handwritten medicine names, instructions, and fair pricing.
              </p>
            </div>

            {/* Right Column: Prescription Features & Benefits */}
            <div className="lg:col-span-6 space-y-6">
              <div>
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-teal-100 text-teal-800 border border-teal-200 mb-3">
                  <span className="w-1.5 h-1.5 rounded-full bg-teal-600" />
                  Prescription &amp; Medication Intelligence
                </span>
                <h2 className="text-2xl sm:text-4xl font-extrabold text-slate-900 tracking-tight leading-tight">
                  Clear medicine schedules you can follow with confidence.
                </h2>
                <p className="mt-3 text-sm sm:text-base text-slate-600 leading-relaxed">
                  Doctor prescriptions are often rushed or written in medical shorthand. EvidenceBridge transcribes your prescription, provides plain-language daily schedules, and checks whether affordable generic equivalents are available.
                </p>
              </div>

              <div className="space-y-3.5 pt-1">
                <div className="flex items-start gap-3.5 p-3.5 rounded-xl bg-white border border-slate-200/80 shadow-xs">
                  <div className="w-8 h-8 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold text-sm flex-shrink-0 mt-0.5">
                    ⏰
                  </div>
                  <div>
                    <div className="text-xs font-bold text-slate-900">
                      When to Take Each Medicine
                    </div>
                    <div className="text-xs text-slate-600 mt-0.5 leading-relaxed">
                      Instant breakdown of dosage timings: Morning, Noon, Night, Before Meals, or After Meals to avoid stomach irritation or missed doses.
                    </div>
                  </div>
                </div>

                <div className="flex items-start gap-3.5 p-3.5 rounded-xl bg-white border border-slate-200/80 shadow-xs">
                  <div className="w-8 h-8 rounded-lg bg-sky-100 text-sky-700 flex items-center justify-center font-bold text-sm flex-shrink-0 mt-0.5">
                    🏷️
                  </div>
                  <div>
                    <div className="text-xs font-bold text-slate-900">
                      Generic Equivalents (Jan Aushadhi)
                    </div>
                    <div className="text-xs text-slate-600 mt-0.5 leading-relaxed">
                      Identify exact molecule names and generic options that cost 60%–80% less than branded formulations for chronic conditions like diabetes and hypertension.
                    </div>
                  </div>
                </div>

                <div className="flex items-start gap-3.5 p-3.5 rounded-xl bg-white border border-slate-200/80 shadow-xs">
                  <div className="w-8 h-8 rounded-lg bg-amber-100 text-amber-700 flex items-center justify-center font-bold text-sm flex-shrink-0 mt-0.5">
                    ⚠️
                  </div>
                  <div>
                    <div className="text-xs font-bold text-slate-900">
                      Unnecessary Antibiotic Detection
                    </div>
                    <div className="text-xs text-slate-600 mt-0.5 leading-relaxed">
                      Flags when broad-spectrum antibiotics are prescribed for routine viral coughs or colds, protecting you from antibiotic resistance and unnecessary expense.
                    </div>
                  </div>
                </div>
              </div>

              <div className="pt-2 flex flex-col sm:flex-row items-center gap-3">
                <button
                  type="button"
                  onClick={handleGetStarted}
                  className="w-full sm:w-auto px-6 py-2.5 rounded-xl bg-teal-700 hover:bg-teal-800 text-white font-bold text-xs shadow-xs transition-all flex items-center justify-center gap-2"
                >
                  <span>Upload Prescription or Bill</span>
                  <span>&rarr;</span>
                </button>
                <Link
                  to="/community"
                  className="text-xs font-semibold text-teal-800 hover:text-teal-950 hover:underline px-3 py-2 transition-colors"
                >
                  Read how patients saved on medicines &rarr;
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Human-Centered Story & Patient Advocacy Spotlight */}
      <section className="py-20 bg-white border-b border-slate-200 overflow-hidden">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-14 items-center">
            {/* Left Column: Narrative & Values */}
            <div className="lg:col-span-6 space-y-6 order-2 lg:order-1">
              <div>
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-sky-100 text-sky-800 border border-sky-200 mb-3">
                  <span className="w-1.5 h-1.5 rounded-full bg-sky-600" />
                  Human-Centered Patient Advocacy
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
                <div className="flex items-start gap-3.5 p-3.5 rounded-xl bg-slate-50 border border-slate-200/80 shadow-xs">
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
                <div className="flex items-start gap-3.5 p-3.5 rounded-xl bg-slate-50 border border-slate-200/80 shadow-xs">
                  <div className="w-8 h-8 rounded-lg bg-amber-100 text-amber-700 flex items-center justify-center font-bold text-sm flex-shrink-0 mt-0.5">
                    ⚠
                  </div>
                  <div>
                    <div className="text-xs font-bold text-slate-900">
                      Transparent Protection Against Extreme Markups
                    </div>
                    <div className="text-xs text-slate-600 mt-0.5 leading-relaxed">
                      Identify when routine items like a saline bag are marked up 30× above public health benchmarks (₹1,800 vs ₹30–₹60).
                    </div>
                  </div>
                </div>

                {/* Benefit 3 */}
                <div className="flex items-start gap-3.5 p-3.5 rounded-xl bg-slate-50 border border-slate-200/80 shadow-xs">
                  <div className="w-8 h-8 rounded-lg bg-sky-100 text-sky-700 flex items-center justify-center font-bold text-sm flex-shrink-0 mt-0.5">
                    🤝
                  </div>
                  <div>
                    <div className="text-xs font-bold text-slate-900">
                      Constructive, Evidence-Backed Dialogue
                    </div>
                    <div className="text-xs text-slate-600 mt-0.5 leading-relaxed">
                      Equip patients, hospital billing desks, and insurance reviewers with objective, reproducible audit reports so discussions remain respectful and fact-based.
                    </div>
                  </div>
                </div>
              </div>

              {/* Action Button */}
              <div className="pt-2 flex flex-col sm:flex-row items-center gap-3">
                <button
                  type="button"
                  onClick={handleGetStarted}
                  className="w-full sm:w-auto px-6 py-2.5 rounded-xl bg-sky-600 hover:bg-sky-700 text-white font-bold text-xs shadow-xs transition-all flex items-center justify-center gap-2"
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

            {/* Right Column: Doctor-Patient Image Card */}
            <div className="lg:col-span-6 relative order-1 lg:order-2">
              <div className="absolute -inset-4 bg-gradient-to-tr from-sky-200/50 to-teal-100/40 rounded-3xl blur-2xl -z-10" />

              <div className="relative rounded-2xl sm:rounded-3xl overflow-hidden border border-slate-200 shadow-2xl bg-white group">
                <img
                  src="/doctor-patient.jpg"
                  alt="Doctor showing healthcare brochure to patient during consultation"
                  className="w-full h-auto object-cover aspect-[4/3] group-hover:scale-105 transition-transform duration-700"
                  loading="lazy"
                />

                {/* Floating Trust Overlay Card */}
                <div className="absolute bottom-4 left-4 right-4 sm:left-6 sm:right-6 p-3.5 sm:p-4 rounded-xl sm:rounded-2xl bg-white/95 backdrop-blur-md border border-slate-200 shadow-lg flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-sky-100 text-sky-700 flex items-center justify-center text-xl flex-shrink-0">
                    🤝
                  </div>
                  <div>
                    <div className="text-xs font-bold text-slate-900">
                      Patient Advocacy &amp; Fact-Based Reviews
                    </div>
                    <div className="text-[11px] text-slate-600 font-medium leading-tight mt-0.5">
                      Citing medical guidelines and regional fair prices so patients can understand their care.
                    </div>
                  </div>
                </div>
              </div>

              <p className="mt-3 text-center sm:text-left text-xs text-slate-500 italic">
                EvidenceBridge helps patients and clinical reviewers verify that every charge is medically sound and reasonably priced.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Community Stories & Regional Trust Spotlight (New interactive section) */}
      <section className="py-16 bg-gradient-to-b from-slate-50 to-slate-100/70 border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row md:items-end justify-between mb-10 gap-4">
            <div>
              <span className="text-xs font-bold uppercase tracking-widest text-sky-600">
                Patient Voices Across Karnataka
              </span>
              <h2 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight mt-1">
                Real recovery stories &amp; hospital billing experiences
              </h2>
              <p className="text-xs sm:text-sm text-slate-500 mt-1 max-w-2xl">
                Read how patients and families across Bengaluru, Mysuru, Hubli, Davangere, and Ballari navigated unexpected hospital charges and prescription schedules.
              </p>
            </div>
            <Link
              to="/community"
              className="inline-flex items-center gap-1.5 text-xs font-bold text-sky-700 hover:text-sky-900 hover:underline flex-shrink-0"
            >
              <span>View all 8 Community Stories &rarr;</span>
            </Link>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Story Teaser 1 */}
            <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between hover:shadow-md transition-shadow">
              <div>
                <div className="flex items-center justify-between gap-2 mb-2">
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-100 text-amber-900">
                    Billing Dispute
                  </span>
                  <span className="text-[11px] text-slate-400 font-medium">📍 Bengaluru</span>
                </div>
                <h4 className="text-sm font-bold text-slate-900 mb-2">
                  Challenged a ₹1,800 Saline Charge in Whitefield
                </h4>
                <p className="text-xs text-slate-600 line-clamp-3 leading-relaxed">
                  My father was admitted for acute food poisoning. When I reviewed the itemized bill, they had charged ₹1,800 for two normal saline bottles (MRP ₹45 each). I requested an itemized reconciliation at the billing desk and they corrected it to ₹90.
                </p>
              </div>
              <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
                <span>By Rajesh M. (Software Engineer)</span>
                <span className="font-semibold text-emerald-700">Saved ₹1,710</span>
              </div>
            </div>

            {/* Story Teaser 2 */}
            <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between hover:shadow-md transition-shadow">
              <div>
                <div className="flex items-center justify-between gap-2 mb-2">
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-teal-100 text-teal-900">
                    Prescription Clarity
                  </span>
                  <span className="text-[11px] text-slate-400 font-medium">📍 Mysuru</span>
                </div>
                <h4 className="text-sm font-bold text-slate-900 mb-2">
                  Decoded Handwritten Diabetic Prescriptions
                </h4>
                <p className="text-xs text-slate-600 line-clamp-3 leading-relaxed">
                  My mother takes 5 different daily tablets. The doctor’s slip was completely unreadable and she took Metformin on an empty stomach. Getting the exact morning/night schedule and Jan Aushadhi generic equivalents reduced her monthly cost from ₹1,400 to ₹320.
                </p>
              </div>
              <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
                <span>By Sunitha R. (Teacher)</span>
                <span className="font-semibold text-emerald-700">Saved ₹1,080/mo</span>
              </div>
            </div>

            {/* Story Teaser 3 */}
            <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between hover:shadow-md transition-shadow">
              <div>
                <div className="flex items-center justify-between gap-2 mb-2">
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-900">
                    Transparent Pricing
                  </span>
                  <span className="text-[11px] text-slate-400 font-medium">📍 Davangere</span>
                </div>
                <h4 className="text-sm font-bold text-slate-900 mb-2">
                  Normal Delivery Package With No Hidden Surcharges
                </h4>
                <p className="text-xs text-slate-600 line-clamp-3 leading-relaxed">
                  We opted for a mother and child hospital near MCC B Block that published clear package tariffs (₹28,000 all-inclusive for normal delivery). Every item from nursing to nursery charges matched the quotation perfectly.
                </p>
              </div>
              <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
                <span>By Deepa &amp; Santosh</span>
                <span className="font-semibold text-sky-700">100% Transparent</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section id="how-it-works" className="py-16 bg-white border-b border-slate-200">
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
            <div className="bg-slate-50 p-6 rounded-2xl border border-slate-200 shadow-xs relative">
              <div className="text-xs font-bold text-sky-600 mb-2 font-mono">STEP 01</div>
              <h3 className="text-base font-bold text-slate-900">Paste Text or Upload Photo</h3>
              <p className="text-xs text-slate-500 mt-2 leading-relaxed">
                Provide a raw clinical note, hospital bill line, or take a picture with OCR text extraction. The system calculates an immutable SHA-256 digital fingerprint to prevent tampering.
              </p>
            </div>

            <div className="bg-slate-50 p-6 rounded-2xl border border-slate-200 shadow-xs relative">
              <div className="text-xs font-bold text-sky-600 mb-2 font-mono">STEP 02</div>
              <h3 className="text-base font-bold text-slate-900">Hybrid Evidence &amp; Price Match</h3>
              <p className="text-xs text-slate-500 mt-2 leading-relaxed">
                Local-first AI and BM25 search evaluate authoritative guidelines and check billed charges against standard CGHS, PM-JAY, and regional Karnataka price schedules.
              </p>
            </div>

            <div className="bg-slate-50 p-6 rounded-2xl border border-slate-200 shadow-xs relative">
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
      <section id="sample-scenarios" className="py-16 bg-slate-50 border-b border-slate-200">
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
            <div className="p-4 rounded-xl bg-white border border-slate-200 hover:border-sky-300 transition-colors shadow-xs">
              <span className="inline-block px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 mb-2">
                ACCEPT &bull; Supported
              </span>
              <h4 className="text-xs font-bold text-slate-900">Type 2 Diabetes Metformin</h4>
              <p className="text-[11px] text-slate-500 mt-1">
                30-day generic supply (₹75.00) matching ICMR first-line standards.
              </p>
            </div>

            <div className="p-4 rounded-xl bg-white border border-slate-200 hover:border-sky-300 transition-colors shadow-xs">
              <span className="inline-block px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 mb-2">
                ACCEPT &bull; Supported
              </span>
              <h4 className="text-xs font-bold text-slate-900">Brain MRI (CPT 70551)</h4>
              <p className="text-[11px] text-slate-500 mt-1">
                Neurological trauma scan (₹5,500 regional diagnostic fee).
              </p>
            </div>

            <div className="p-4 rounded-xl bg-white border border-slate-200 hover:border-sky-300 transition-colors shadow-xs">
              <span className="inline-block px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800 mb-2">
                FLAG &bull; 30× Markup
              </span>
              <h4 className="text-xs font-bold text-slate-900">Normal Saline IV Overcharge</h4>
              <p className="text-[11px] text-slate-500 mt-1">
                ₹1,800 billed for commodity saline (typical benchmark ₹30–₹60).
              </p>
            </div>

            <div className="p-4 rounded-xl bg-white border border-slate-200 hover:border-sky-300 transition-colors shadow-xs">
              <span className="inline-block px-2 py-0.5 rounded text-[10px] font-bold bg-rose-100 text-rose-800 mb-2">
                FLAG &bull; Contradicted
              </span>
              <h4 className="text-xs font-bold text-slate-900">Antibiotics for Viral Coryza</h4>
              <p className="text-[11px] text-slate-500 mt-1">
                Azithromycin (₹450) prescribed for mild cold against ICMR guidelines.
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

          <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-3">
            <button
              type="button"
              onClick={handleGetStarted}
              className="w-full sm:w-auto px-8 py-3 rounded-xl bg-sky-500 hover:bg-sky-400 text-slate-950 font-bold text-sm shadow-lg transition-colors"
            >
              Launch Auditor Workspace &rarr;
            </button>
            <Link
              to="/hospitals"
              className="w-full sm:w-auto px-6 py-3 rounded-xl bg-white/10 hover:bg-white/20 text-white font-bold text-sm border border-white/20 transition-colors"
            >
              Explore Karnataka Hospitals
            </Link>
          </div>
        </div>
      </section>

      {/* Modern Medical Footer */}
      <footer className="bg-slate-900 text-slate-400 py-12 border-t border-slate-800 text-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8 pb-8 border-b border-slate-800">
            {/* Column 1: Brand */}
            <div className="md:col-span-2 space-y-3">
              <div className="flex items-center gap-2.5">
                <EbMark size={24} />
                <span className="font-bold text-white text-base">EvidenceBridge</span>
              </div>
              <p className="text-xs text-slate-400 max-w-md leading-relaxed">
                Healthcare Evidence Auditing &amp; Price Anomaly Engine. Empowering patients, hospital administrators, and reviewers with verifiable clinical evidence and fair regional pricing benchmarks.
              </p>
              <div className="text-[11px] text-slate-500">
                Built for Karnataka &bull; Bengaluru &bull; Ballari &bull; Mysuru &bull; Davangere &bull; Hubli &bull; Mangaluru &bull; Belagavi
              </div>
            </div>

            {/* Column 2: Navigation */}
            <div>
              <div className="text-white font-bold mb-3 uppercase tracking-wider text-[11px]">
                Features &amp; Tools
              </div>
              <ul className="space-y-2 text-xs">
                <li>
                  <button type="button" onClick={handleGetStarted} className="hover:text-white transition-colors">
                    Audit Claim &amp; Bill
                  </button>
                </li>
                <li>
                  <Link to="/claims" className="hover:text-white transition-colors">
                    Claims History Explorer
                  </Link>
                </li>
                <li>
                  <Link to="/hospitals" className="hover:text-white transition-colors">
                    Hospital Finder &amp; Fees
                  </Link>
                </li>
                <li>
                  <Link to="/trust-density" className="hover:text-white transition-colors">
                    Regional Trust Scores
                  </Link>
                </li>
                <li>
                  <Link to="/insights" className="hover:text-white transition-colors">
                    Audit Insights &amp; Analytics
                  </Link>
                </li>
              </ul>
            </div>

            {/* Column 3: Community & Safety */}
            <div>
              <div className="text-white font-bold mb-3 uppercase tracking-wider text-[11px]">
                Community &amp; Ethics
              </div>
              <ul className="space-y-2 text-xs">
                <li>
                  <Link to="/community" className="hover:text-white transition-colors">
                    Patient Recovery Stories
                  </Link>
                </li>
                <li>
                  <Link to="/evaluation" className="hover:text-white transition-colors">
                    7-Stage Audit Benchmark Runs
                  </Link>
                </li>
                <li>
                  <span className="text-slate-500">WHO &amp; ICMR Aligned</span>
                </li>
                <li>
                  <span className="text-slate-500">CGHS / PM-JAY Rate Index</span>
                </li>
              </ul>
            </div>
          </div>

          <div className="pt-6 flex flex-col sm:flex-row justify-between items-center gap-3 text-[11px] text-slate-500">
            <div>
              &copy; {new Date().getFullYear()} EvidenceBridge. Open-source under Apache-2.0.
            </div>
            <div className="text-center sm:text-right">
              Informational &amp; auditing tool only. Not a substitute for formal medical advice.
            </div>
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
