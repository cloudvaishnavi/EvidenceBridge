import { useState, useEffect, useRef } from 'react'
import { NavLink, Outlet, useNavigate, useLocation } from 'react-router-dom'
import { getHealth, API_BASE } from '../api/client'
import type { HealthResponse } from '../types'
import { useAuth } from '../context/AuthContext'
import { useVoice } from '../context/VoiceContext'
import { AuthModal } from './AuthModal'
import { VoiceAssistant } from './VoiceAssistant'
import Logo, { EbMark } from './Logo'

export default function Layout() {
  const { user, isAuthenticated, logout, demoLogin } = useAuth()
  const { setIsOpen: setVoiceOpen, setIsEnabled: setIsVoiceEnabled } = useVoice()
  const navigate = useNavigate()
  const location = useLocation()
  const [profileModalOpen, setProfileModalOpen] = useState(false)
  const [authModalOpen, setAuthModalOpen] = useState(false)
  const [authModalMode, setAuthModalMode] = useState<'login' | 'signup'>('login')
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [moreDropdownOpen, setMoreDropdownOpen] = useState(false)
  const moreRef = useRef<HTMLDivElement>(null)

  const [health, setHealth] = useState<{
    loading: boolean
    ok: boolean
    data?: HealthResponse
  }>({ loading: true, ok: false })

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

  // Close menus on page navigation
  useEffect(() => {
    setMobileMenuOpen(false)
    setMoreDropdownOpen(false)
  }, [location.pathname])

  // Click outside to close 'More' dropdown
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (moreRef.current && !moreRef.current.contains(event.target as Node)) {
        setMoreDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const navLinkClasses = ({ isActive }: { isActive: boolean }) =>
    `inline-flex items-center px-2 py-1 text-xs font-semibold rounded-lg transition-colors whitespace-nowrap ${
      isActive
        ? 'bg-sky-50 text-sky-700 font-bold border border-sky-200 shadow-xs'
        : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
    }`

  const handleSignOut = () => {
    logout()
    navigate('/')
  }

  const getUserInitials = (name: string) => {
    return name
      .split(' ')
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase())
      .join('')
  }

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900 font-sans w-full max-w-full overflow-x-hidden">
      {/* Top Header */}
      <header className="bg-white/95 backdrop-blur-sm border-b border-slate-200 sticky top-0 z-30 shadow-xs w-full">
        <div className="w-full max-w-7xl mx-auto px-2 sm:px-4 lg:px-6">
          <div className="flex items-center justify-between h-14 gap-1.5 sm:gap-3">
            {/* Left Cluster: Logo + Navigation Links */}
            <div className="flex items-center gap-1 sm:gap-2.5 min-w-0 flex-1">
              {/* Logo */}
              <NavLink to="/welcome" className="flex items-center flex-shrink-0 mr-1 sm:mr-2">
                <Logo size="sm" showText={true} />
              </NavLink>

              {/* Full Desktop Navigation (large screens >= 1200px) */}
              <nav className="hidden xl:flex items-center gap-0.5 2xl:gap-1 min-w-0">
                <NavLink to="/audit" className={navLinkClasses} title="Audit a healthcare claim or hospital bill">
                  Audit Claim
                </NavLink>
                <NavLink to="/claims" className={navLinkClasses} title="Browse verified claims history">
                  Claims Explorer
                </NavLink>
                <NavLink to="/hospitals" className={navLinkClasses} title="Find nearby hospitals, fair costs & trusted facilities">
                  Hospitals
                </NavLink>
                <NavLink to="/insights" className={navLinkClasses} title="Interactive statistics and summary charts">
                  Insights
                </NavLink>
                <NavLink to="/trust-density" className={navLinkClasses} title="Regional healthcare trust indicators">
                  Regional Trust
                </NavLink>
                <NavLink to="/evaluation" className={navLinkClasses} title="Controlled clinical validation benchmark suite">
                  Evaluation
                </NavLink>
                <NavLink to="/community" className={navLinkClasses} title="Real patient stories & billing recovery guidance">
                  Stories
                </NavLink>
                <NavLink to="/welcome" className={navLinkClasses} title="Platform overview and architecture">
                  Overview
                </NavLink>
              </nav>

              {/* Medium Screen Navigation (md to xl: 768px - 1199px) */}
              <nav className="hidden md:flex xl:hidden items-center gap-0.5 min-w-0">
                <NavLink to="/audit" className={navLinkClasses}>
                  Audit
                </NavLink>
                <NavLink to="/claims" className={navLinkClasses}>
                  Claims
                </NavLink>
                <NavLink to="/hospitals" className={navLinkClasses}>
                  Hospitals
                </NavLink>
                <NavLink to="/insights" className={navLinkClasses}>
                  Insights
                </NavLink>

                {/* More Dropdown for secondary pages */}
                <div className="relative" ref={moreRef}>
                  <button
                    type="button"
                    onClick={() => setMoreDropdownOpen((prev) => !prev)}
                    className="inline-flex items-center gap-1 px-2 py-1 text-xs font-semibold rounded-lg text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-colors"
                  >
                    <span>More</span>
                    <span className="text-[10px]">▾</span>
                  </button>
                  {moreDropdownOpen && (
                    <div className="absolute left-0 mt-1 w-44 bg-white rounded-xl shadow-lg border border-slate-200 py-1.5 z-40 animate-in fade-in zoom-in-95 duration-100">
                      <NavLink
                        to="/trust-density"
                        className={({ isActive }) =>
                          `block px-3 py-1.5 text-xs font-semibold transition-colors ${
                            isActive ? 'bg-sky-50 text-sky-700' : 'text-slate-700 hover:bg-slate-50'
                          }`
                        }
                      >
                        Regional Trust
                      </NavLink>
                      <NavLink
                        to="/evaluation"
                        className={({ isActive }) =>
                          `block px-3 py-1.5 text-xs font-semibold transition-colors ${
                            isActive ? 'bg-sky-50 text-sky-700' : 'text-slate-700 hover:bg-slate-50'
                          }`
                        }
                      >
                        Evaluation
                      </NavLink>
                      <NavLink
                        to="/community"
                        className={({ isActive }) =>
                          `block px-3 py-1.5 text-xs font-semibold transition-colors ${
                            isActive ? 'bg-sky-50 text-sky-700' : 'text-slate-700 hover:bg-slate-50'
                          }`
                        }
                      >
                        Community Stories
                      </NavLink>
                      <NavLink
                        to="/welcome"
                        className={({ isActive }) =>
                          `block px-3 py-1.5 text-xs font-semibold transition-colors ${
                            isActive ? 'bg-sky-50 text-sky-700' : 'text-slate-700 hover:bg-slate-50'
                          }`
                        }
                      >
                        Overview
                      </NavLink>
                    </div>
                  )}
                </div>
              </nav>
            </div>

            {/* Right Cluster: Local Engine, Voice AI, User Profile, Sign Out */}
            <div className="flex-shrink-0 flex items-center gap-1.5 sm:gap-2">
              {/* Backend Health Pill */}
              <div
                className="hidden 2xl:flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium border bg-slate-50 border-slate-200"
                title={
                  health.loading
                    ? 'Checking backend status...'
                    : health.ok
                    ? `Backend Online (${health.data?.app_name || 'FastAPI'} v${health.data?.version || '0.1'})`
                    : `Backend Offline (${API_BASE})`
                }
              >
                <span
                  className={`w-2 h-2 rounded-full ${
                    health.loading
                      ? 'bg-amber-400 animate-pulse'
                      : health.ok
                      ? 'bg-emerald-500'
                      : 'bg-rose-500'
                  }`}
                />
                <span className="text-slate-600 text-[11px] whitespace-nowrap">
                  {health.loading
                    ? 'Connecting...'
                    : health.ok
                    ? 'Local Engine Active'
                    : 'Backend Offline'}
                </span>
              </div>

              {/* Voice AI Header Button */}
              {isAuthenticated && (
                <button
                  type="button"
                  onClick={() => {
                    setIsVoiceEnabled(true)
                    setVoiceOpen(true)
                  }}
                  className="flex items-center gap-1 px-2 py-1 rounded-lg border border-sky-200 bg-sky-50 hover:bg-sky-100 text-xs font-bold text-sky-800 transition-colors shadow-xs"
                  title="Open AI Voice Assistant (English / ಕನ್ನಡ)"
                >
                  <span className="text-xs leading-none">🎙️</span>
                  <span className="hidden sm:inline text-xs">Voice AI</span>
                </button>
              )}

              {/* User Authentication Pill & Always-Visible Sign Out */}
              {isAuthenticated && user ? (
                <div className="flex items-center gap-1.5">
                  <button
                    type="button"
                    onClick={() => setProfileModalOpen(true)}
                    className="flex items-center gap-1.5 py-1 px-2 rounded-xl bg-slate-50 hover:bg-slate-100 border border-slate-200 shadow-2xs transition-colors cursor-pointer group text-left"
                    title="Click to view profile details"
                  >
                    <div className="w-6 h-6 rounded-full bg-clinical-600 group-hover:bg-clinical-700 text-white font-bold text-[10px] flex items-center justify-center flex-shrink-0 transition-colors">
                      {getUserInitials(user.name) || 'V'}
                    </div>
                    <div className="text-left hidden sm:block max-w-[110px]">
                      <div className="text-xs font-bold text-slate-800 leading-tight truncate">
                        {user.name}
                      </div>
                      <div className="text-[9px] text-slate-500 font-medium leading-none truncate">
                        {user.role}
                      </div>
                    </div>
                  </button>

                  {/* Sign Out Button - Always visible in the top bar */}
                  <button
                    type="button"
                    onClick={handleSignOut}
                    className="text-xs font-semibold text-rose-600 hover:text-rose-700 px-2 py-1 rounded-lg hover:bg-rose-50 border border-transparent hover:border-rose-200 transition-colors whitespace-nowrap"
                    title="Sign Out of Auditor Session"
                  >
                    Sign Out
                  </button>
                </div>
              ) : (
                <div className="flex items-center gap-1 sm:gap-1.5">
                  <button
                    type="button"
                    onClick={() => {
                      setAuthModalMode('login')
                      setAuthModalOpen(true)
                    }}
                    className="text-xs font-semibold text-slate-700 hover:text-slate-900 px-2 py-1 rounded-lg hover:bg-slate-100 transition-colors"
                  >
                    Sign In
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setAuthModalMode('signup')
                      setAuthModalOpen(true)
                    }}
                    className="hidden sm:inline-flex text-xs font-semibold text-sky-700 bg-sky-50 hover:bg-sky-100 border border-sky-200 px-2 py-1 rounded-lg transition-colors"
                  >
                    Sign Up
                  </button>
                  <button
                    type="button"
                    onClick={async () => {
                      await demoLogin()
                    }}
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-sky-600 hover:bg-sky-700 text-white text-xs font-bold shadow-xs transition-colors whitespace-nowrap"
                    title="1-click demo login as Vasavi (Clinical Claims Reviewer)"
                  >
                    <span>⚡ Demo (Vasavi)</span>
                  </button>
                </div>
              )}

              {/* Mobile Menu Hamburger (screens < md) */}
              <button
                type="button"
                onClick={() => setMobileMenuOpen((prev) => !prev)}
                className="md:hidden p-1.5 rounded-lg text-slate-600 hover:text-slate-900 hover:bg-slate-100"
                aria-label="Toggle Navigation Menu"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  {mobileMenuOpen ? (
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                  ) : (
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h16M4 18h16" />
                  )}
                </svg>
              </button>
            </div>
          </div>
        </div>

        {/* Mobile Navigation Dropdown (< md screens) */}
        {mobileMenuOpen && (
          <div className="md:hidden border-t border-slate-200 bg-white px-3 py-2 space-y-1 shadow-lg animate-in slide-in-from-top-2 duration-150">
            <NavLink to="/audit" className={navLinkClasses}>
              Audit Claim
            </NavLink>
            <NavLink to="/claims" className={navLinkClasses}>
              Claims Explorer
            </NavLink>
            <NavLink to="/hospitals" className={navLinkClasses}>
              Hospitals
            </NavLink>
            <NavLink to="/insights" className={navLinkClasses}>
              Insights
            </NavLink>
            <NavLink to="/trust-density" className={navLinkClasses}>
              Regional Trust
            </NavLink>
            <NavLink to="/evaluation" className={navLinkClasses}>
              Evaluation
            </NavLink>
            <NavLink to="/community" className={navLinkClasses}>
              Community Stories
            </NavLink>
            <NavLink to="/welcome" className={navLinkClasses}>
              Overview
            </NavLink>
          </div>
        )}
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-3 sm:px-6 lg:px-8 py-6 sm:py-8">
        <Outlet />
      </main>

      {/* Trust-Focused Medical Footer */}
      <footer className="bg-white border-t border-slate-200 py-6 text-xs text-slate-500 w-full">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row justify-between items-center gap-3">
          <div className="flex items-center gap-2">
            <EbMark size={20} />
            <span className="font-bold text-slate-700">EvidenceBridge</span>
            <span>&bull;</span>
            <span>Local-First Clinical Evidence &amp; Medical Price Auditing</span>
          </div>

          <div className="flex items-center gap-4 text-slate-400 text-[11px] flex-wrap justify-center">
            <span className="flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
              100% Offline Engine
            </span>
            <span>&bull;</span>
            <span>Zero PHI Cloud Leakage</span>
            <span>&bull;</span>
            <span>7-Stage Traceable Graph</span>
            <span>&bull;</span>
            <span>Layers 1&ndash;6 Complete</span>
          </div>
        </div>
      </footer>

      {/* Global Auth Modal */}
      <AuthModal
        isOpen={authModalOpen}
        initialMode={authModalMode}
        onClose={() => setAuthModalOpen(false)}
      />

      {/* User Profile Modal */}
      {profileModalOpen && user && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-150">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200 relative animate-in zoom-in-95 duration-150">
            {/* Close Button */}
            <button
              type="button"
              onClick={() => setProfileModalOpen(false)}
              className="absolute top-4 right-4 text-slate-400 hover:text-slate-600 p-1.5 rounded-lg hover:bg-slate-100 transition-colors"
              title="Close modal"
            >
              ✕
            </button>

            {/* Profile Header */}
            <div className="flex items-center gap-4 mb-5">
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-clinical-600 to-sky-500 text-white font-black text-xl flex items-center justify-center shadow-md">
                {getUserInitials(user.name) || 'V'}
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-lg font-black text-slate-900">{user.name}</h3>
                  <span className="px-2 py-0.5 rounded-md text-[10px] font-extrabold bg-emerald-50 text-emerald-800 border border-emerald-200">
                    Verified
                  </span>
                </div>
                <p className="text-xs font-semibold text-clinical-700">{user.role}</p>
                <p className="text-[11px] text-slate-500 mt-0.5">{user.organization || 'EvidenceBridge Clinical Review Network'}</p>
              </div>
            </div>

            {/* Details Cards */}
            <div className="space-y-2.5 text-xs bg-slate-50 p-4 rounded-xl border border-slate-200 mb-5">
              <div className="flex items-center justify-between py-1 border-b border-slate-200/70">
                <span className="text-slate-500 font-medium">Email Address:</span>
                <span className="font-semibold text-slate-800">{user.email}</span>
              </div>
              <div className="flex items-center justify-between py-1 border-b border-slate-200/70">
                <span className="text-slate-500 font-medium">Reviewer ID:</span>
                <span className="font-mono text-slate-700">{user.id}</span>
              </div>
              <div className="flex items-center justify-between py-1 border-b border-slate-200/70">
                <span className="text-slate-500 font-medium">Account Access:</span>
                <span className="font-semibold text-emerald-700">1-Click Demo Reviewer &bull; Full Access</span>
              </div>
              <div className="flex items-center justify-between py-1">
                <span className="text-slate-500 font-medium">Assigned Territory:</span>
                <span className="font-semibold text-slate-800">Karnataka &bull; All-India National Benchmarks</span>
              </div>
            </div>

            {/* Modal Actions */}
            <div className="flex items-center justify-between gap-3 pt-2">
              <button
                type="button"
                onClick={() => setProfileModalOpen(false)}
                className="flex-1 py-2.5 px-4 rounded-xl border border-slate-300 text-slate-700 hover:bg-slate-50 text-xs font-bold transition-colors"
              >
                Close Profile
              </button>
              <button
                type="button"
                onClick={() => {
                  setProfileModalOpen(false)
                  handleSignOut()
                }}
                className="py-2.5 px-4 rounded-xl bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold transition-colors shadow-xs"
              >
                Sign Out
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Floating AI Voice Assistant */}
      <VoiceAssistant />
    </div>
  )
}
