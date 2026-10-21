import React, { useState, useEffect } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { getHealth } from '../api/client'
import type { HealthResponse } from '../types'

export default function Layout() {
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

  const navLinkClasses = ({ isActive }: { isActive: boolean }) =>
    `inline-flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors ${
      isActive
        ? 'bg-sky-50 text-sky-700 font-semibold'
        : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
    }`

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900">
      {/* Top Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            {/* Logo and Brand */}
            <div className="flex items-center gap-6">
              <NavLink to="/" className="flex items-center gap-2 group">
                <div className="w-9 h-9 rounded-lg bg-sky-600 flex items-center justify-center text-white font-bold text-lg shadow-sm group-hover:bg-sky-700 transition-colors">
                  EB
                </div>
                <div>
                  <div className="font-bold text-lg text-slate-900 tracking-tight leading-none group-hover:text-sky-600 transition-colors">
                    EvidenceBridge
                  </div>
                  <div className="text-[11px] text-slate-500 font-medium">
                    Evidence-Auditing &amp; Cost-Anomaly Engine
                  </div>
                </div>
              </NavLink>

              {/* Navigation Links */}
              <nav className="hidden md:flex space-x-1 pl-4 border-l border-slate-200">
                <NavLink to="/" className={navLinkClasses}>
                  Audit / Extract
                </NavLink>
                <NavLink to="/claims" className={navLinkClasses}>
                  Claims Explorer
                </NavLink>
                <NavLink to="/trust-density" className={navLinkClasses}>
                  Hyperlocal Trust Density
                </NavLink>
              </nav>
            </div>

            {/* Right Health Indicator */}
            <div className="flex items-center gap-3">
              <div
                className="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium border bg-slate-50 border-slate-200"
                title={
                  health.loading
                    ? 'Checking backend status...'
                    : health.ok
                    ? `Backend Online (${health.data?.app_name || 'FastAPI'} v${health.data?.version || '0.1'})`
                    : 'Backend Offline at http://localhost:8000'
                }
              >
                <span
                  className={`w-2.5 h-2.5 rounded-full ${
                    health.loading
                      ? 'bg-amber-400 animate-pulse'
                      : health.ok
                      ? 'bg-emerald-500'
                      : 'bg-rose-500'
                  }`}
                />
                <span className="hidden sm:inline text-slate-700">
                  {health.loading
                    ? 'Checking...'
                    : health.ok
                    ? 'Backend Online'
                    : 'Backend Offline'}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Mobile Nav */}
        <div className="md:hidden border-t border-slate-100 px-4 py-2 flex space-x-2 bg-slate-50">
          <NavLink to="/" className={navLinkClasses}>
            Audit / Extract
          </NavLink>
          <NavLink to="/claims" className={navLinkClasses}>
            Claims
          </NavLink>
          <NavLink to="/trust-density" className={navLinkClasses}>
            Trust Density
          </NavLink>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-slate-200 py-4 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row justify-between items-center gap-2">
          <div>EvidenceBridge &copy; 2026 &middot; Local-First Healthcare Auditing</div>
          <div className="flex items-center gap-3 text-slate-400">
            <span>Layers 1&ndash;5 Complete</span>
            <span>&bull;</span>
            <span>Ollama + ChromaDB + MongoDB</span>
            <span>&bull;</span>
            <span>Apache-2.0</span>
          </div>
        </div>
      </footer>
    </div>
  )
}
