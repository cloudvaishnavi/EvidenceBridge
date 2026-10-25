import React, { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import { EbMark } from './Logo'

interface AuthModalProps {
  isOpen: boolean
  onClose: () => void
  initialMode?: 'login' | 'signup'
  onSuccess?: () => void
}

export function AuthModal({
  isOpen,
  onClose,
  initialMode = 'login',
  onSuccess,
}: AuthModalProps) {
  const { login, signup, demoLogin } = useAuth()
  const [mode, setMode] = useState<'login' | 'signup'>(initialMode)
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [organization, setOrganization] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setMode(initialMode)
    setError(null)
  }, [initialMode, isOpen])

  if (!isOpen) return null

  const resetForm = () => {
    setName('')
    setEmail('')
    setPassword('')
    setConfirmPassword('')
    setOrganization('')
    setError(null)
  }

  const handleModeSwitch = (newMode: 'login' | 'signup') => {
    setMode(newMode)
    setError(null)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    // Client-side validations
    if (mode === 'signup') {
      if (!name.trim()) {
        setError('Please enter your full name.')
        return
      }
      if (!email.trim() || !email.includes('@')) {
        setError('Please enter a valid email address.')
        return
      }
      if (password.length < 6) {
        setError('Password must be at least 6 characters long.')
        return
      }
      if (password !== confirmPassword) {
        setError('Passwords do not match. Please verify both password fields.')
        return
      }
    } else {
      if (!email.trim()) {
        setError('Please enter your registered email address.')
        return
      }
      if (!password) {
        setError('Please enter your password.')
        return
      }
    }

    setLoading(true)

    try {
      if (mode === 'login') {
        await login(email, password)
      } else {
        // Sign up automatically logs the user in on success
        await signup(name, email, password, organization)
      }
      resetForm()
      onClose()
      if (onSuccess) onSuccess()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err)
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  const handleDemoSignIn = async () => {
    setError(null)
    setLoading(true)
    try {
      await demoLogin()
      resetForm()
      onClose()
      if (onSuccess) onSuccess()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Could not start demo session.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-navy-950/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div
        className="relative bg-white rounded-2xl max-w-md w-full p-6 sm:p-8 shadow-2xl border border-slate-100 animate-in fade-in zoom-in-95 duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close Button */}
        <button
          type="button"
          onClick={onClose}
          className="absolute top-5 right-5 text-slate-400 hover:text-slate-600 transition-colors p-1.5 rounded-lg hover:bg-slate-100"
          aria-label="Close authentication modal"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>

        {/* Brand Header */}
        <div className="text-center mb-5">
          <div className="flex justify-center mb-2.5">
            <EbMark size={42} />
          </div>
          <h2 className="text-xl font-extrabold text-slate-900 tracking-tight">
            EvidenceBridge
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Clinical Evidence &amp; Medical Price Auditing
          </p>
        </div>

        {/* 2-Mode Segmented Tab Switcher */}
        <div className="grid grid-cols-2 p-1 bg-slate-100 rounded-xl mb-5 border border-slate-200/80">
          <button
            type="button"
            onClick={() => handleModeSwitch('login')}
            className={`py-2 text-xs font-bold rounded-lg transition-all ${
              mode === 'login'
                ? 'bg-white text-slate-900 shadow-xs'
                : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            Sign In
          </button>
          <button
            type="button"
            onClick={() => handleModeSwitch('signup')}
            className={`py-2 text-xs font-bold rounded-lg transition-all ${
              mode === 'signup'
                ? 'bg-white text-slate-900 shadow-xs'
                : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            Create Account
          </button>
        </div>

        {/* Mode Heading & Subtext */}
        <div className="mb-4">
          <h3 className="text-sm font-bold text-slate-800">
            {mode === 'login' ? 'Sign In to Your Workspace' : 'Set Up Your Personal Memory'}
          </h3>
          <p className="text-[11px] text-slate-500 mt-0.5">
            {mode === 'login'
              ? 'Enter your credentials to access your personal claims and audit records.'
              : 'Create an account to persist claims, stories, and insights after deployment.'}
          </p>
        </div>

        {/* 1-Click Demo Shortcut */}
        <div className="mb-5 p-3 bg-gradient-to-r from-sky-50 to-clinical-50 border border-sky-200/80 rounded-xl text-center">
          <div className="text-[11px] font-semibold text-slate-700 mb-1.5 flex items-center justify-center gap-1">
            <span>Evaluating the prototype?</span>
          </div>
          <button
            type="button"
            onClick={handleDemoSignIn}
            disabled={loading}
            className="w-full py-2 px-3 bg-sky-600 hover:bg-sky-700 text-white rounded-lg text-xs font-bold shadow-xs transition-all flex items-center justify-center gap-1.5 disabled:opacity-50"
          >
            <span>⚡</span>
            <span>Sign In as Demo Reviewer (1-Click)</span>
          </button>
          <div className="text-[10px] text-slate-500 mt-1">
            Pre-configured session for Dr. Sarah Chen, Senior Clinical Claims Reviewer
          </div>
        </div>

        {/* Divider */}
        <div className="relative flex items-center justify-center mb-4">
          <div className="border-t border-slate-200 w-full" />
          <span className="bg-white px-2.5 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
            {mode === 'login' ? 'or sign in with password' : 'or register with email'}
          </span>
        </div>

        {/* Error Alert Box */}
        {error && (
          <div className="mb-4 p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-start gap-2 animate-in fade-in duration-150">
            <span className="text-rose-600 font-bold mt-0.5">⚠️</span>
            <div className="flex-1 leading-snug">{error}</div>
          </div>
        )}

        {/* Auth Form */}
        <form onSubmit={handleSubmit} className="space-y-3">
          {mode === 'signup' && (
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Full Name <span className="text-rose-500">*</span>
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Dr. Robert Vance"
                className="w-full px-3.5 py-2 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-sky-500 text-slate-800"
                required
              />
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Email Address <span className="text-rose-500">*</span>
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="e.g. auditor@hospital.org"
              className="w-full px-3.5 py-2 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-sky-500 text-slate-800"
              required
            />
          </div>

          {mode === 'signup' && (
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Hospital or Organization <span className="text-slate-400 font-normal">(Optional)</span>
              </label>
              <input
                type="text"
                value={organization}
                onChange={(e) => setOrganization(e.target.value)}
                placeholder="e.g. St. Jude Regional Hospital"
                className="w-full px-3.5 py-2 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-sky-500 text-slate-800"
              />
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Password <span className="text-rose-500">*</span>
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={mode === 'signup' ? 'At least 6 characters' : '••••••••'}
              className="w-full px-3.5 py-2 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-sky-500 text-slate-800"
              required
            />
          </div>

          {mode === 'signup' && (
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Confirm Password <span className="text-rose-500">*</span>
              </label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Re-enter your password"
                className="w-full px-3.5 py-2 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-sky-500 text-slate-800"
                required
              />
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full mt-2 py-2.5 px-4 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-bold transition-colors shadow-sm disabled:opacity-50 flex items-center justify-center gap-1.5"
          >
            {loading ? (
              <span>Please wait...</span>
            ) : mode === 'login' ? (
              <span>Sign In to EvidenceBridge &rarr;</span>
            ) : (
              <span>Create Account &amp; Sign In &rarr;</span>
            )}
          </button>
        </form>

        {/* Footer Toggle Text */}
        <div className="mt-4 pt-3 border-t border-slate-100 text-center text-xs text-slate-500">
          {mode === 'login' ? (
            <div>
              Don&apos;t have an account yet?{' '}
              <button
                type="button"
                onClick={() => handleModeSwitch('signup')}
                className="text-sky-600 font-bold hover:underline"
              >
                Create one now
              </button>
            </div>
          ) : (
            <div>
              Already have an auditor account?{' '}
              <button
                type="button"
                onClick={() => handleModeSwitch('login')}
                className="text-sky-600 font-bold hover:underline"
              >
                Sign in
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
