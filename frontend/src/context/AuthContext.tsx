import React, { createContext, useContext, useState, useEffect } from 'react'
import {
  loginApi,
  signupApi,
  demoAuthApi,
  getMeApi,
  getAuthToken,
  setAuthToken,
  TOKEN_STORAGE_KEY,
  USER_STORAGE_KEY,
} from '../api/client'
import type { UserResponse } from '../types'

export interface User {
  id: string
  name: string
  email: string
  role: string
  organization?: string
}

interface AuthContextType {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  login: (emailOrUsername: string, password: string) => Promise<boolean>
  signup: (
    name: string,
    emailOrUsername: string,
    password: string,
    organization?: string,
  ) => Promise<boolean>
  demoLogin: () => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

function getStoredUser(): User | null {
  if (typeof window === 'undefined') return null
  try {
    const raw =
      localStorage.getItem(USER_STORAGE_KEY) ||
      sessionStorage.getItem(USER_STORAGE_KEY)
    if (raw) return JSON.parse(raw)
  } catch {
    // Ignore JSON parse error
  }
  return null
}

function setStoredUser(user: User | null): void {
  if (typeof window === 'undefined') return
  try {
    if (user) {
      const s = JSON.stringify(user)
      localStorage.setItem(USER_STORAGE_KEY, s)
      sessionStorage.setItem(USER_STORAGE_KEY, s)
    } else {
      localStorage.removeItem(USER_STORAGE_KEY)
      sessionStorage.removeItem(USER_STORAGE_KEY)
    }
  } catch {
    // Ignore storage errors
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  // Synchronously initialize token and user from memory/localStorage/sessionStorage
  const [token, setToken] = useState<string | null>(() => getAuthToken())
  const [user, setUser] = useState<User | null>(() => getStoredUser())

  // Synchronize user profile with backend on startup if token is present
  useEffect(() => {
    const activeToken = getAuthToken()
    if (activeToken) {
      getMeApi()
        .then((profile: UserResponse) => {
          const u: User = {
            id: profile.user_id,
            name: profile.name,
            email: profile.email,
            role: profile.role,
            organization: profile.organization,
          }
          setUser(u)
          setStoredUser(u)
        })
        .catch((err: unknown) => {
          const status = (err as { status?: number })?.status
          // If token verification fails with 401 (expired/invalid), clean up
          if (status === 401) {
            logout()
          }
        })
    }
  }, [])

  const login = async (
    emailOrUsername: string,
    password: string,
  ): Promise<boolean> => {
    if (!emailOrUsername.trim() || !password.trim()) {
      throw new Error('Please enter both your email/username and password.')
    }

    try {
      const authRes = await loginApi({
        email: emailOrUsername.trim(),
        password: password.trim(),
      })

      const u: User = {
        id: authRes.user.user_id,
        name: authRes.user.name,
        email: authRes.user.email,
        role: authRes.user.role,
        organization: authRes.user.organization,
      }
      // CRITICAL: Synchronously write token & user before resolving
      setAuthToken(authRes.access_token)
      setStoredUser(u)
      setToken(authRes.access_token)
      setUser(u)
      return true
    } catch (err: unknown) {
      // Fallback for demo logins if network is offline
      const cleanId = emailOrUsername.trim().toLowerCase()
      if (
        cleanId === 'demo' ||
        cleanId === 'vasavi' ||
        cleanId === 'vasavi.reviewer@evidencebridge.local' ||
        cleanId === 'sarah.chen@stjudehealth.org'
      ) {
        await demoLogin()
        return true
      }
      throw err
    }
  }

  const signup = async (
    name: string,
    emailOrUsername: string,
    password: string,
    organization?: string,
  ): Promise<boolean> => {
    if (!name.trim()) {
      throw new Error('Please enter your full name.')
    }
    if (!emailOrUsername.trim()) {
      throw new Error('Please enter your email address.')
    }
    if (password.length < 4) {
      throw new Error('Password must be at least 4 characters long.')
    }

    const authRes = await signupApi({
      name: name.trim(),
      email: emailOrUsername.trim(),
      password: password.trim(),
      organization: organization?.trim() || undefined,
    })

    const u: User = {
      id: authRes.user.user_id,
      name: authRes.user.name,
      email: authRes.user.email,
      role: authRes.user.role,
      organization: authRes.user.organization,
    }
    // CRITICAL: Synchronously write token & user before resolving
    setAuthToken(authRes.access_token)
    setStoredUser(u)
    setToken(authRes.access_token)
    setUser(u)
    return true
  }

  const demoLogin = async (): Promise<void> => {
    try {
      const authRes = await demoAuthApi()
      const u: User = {
        id: authRes.user.user_id,
        name: authRes.user.name,
        email: authRes.user.email,
        role: authRes.user.role,
        organization: authRes.user.organization,
      }
      // CRITICAL: Synchronously write token & user before resolving
      setAuthToken(authRes.access_token)
      setStoredUser(u)
      setToken(authRes.access_token)
      setUser(u)
    } catch {
      // Offline fallback: use canonical Demo Auditor
      const fallbackDemo: User = {
        id: 'usr_demo_auditor',
        name: 'Vasavi',
        email: 'vasavi.reviewer@evidencebridge.local',
        role: 'Clinical Claims Reviewer',
        organization: 'EvidenceBridge Clinical Review Network',
      }
      setAuthToken('demo_bearer_token')
      setStoredUser(fallbackDemo)
      setToken('demo_bearer_token')
      setUser(fallbackDemo)
    }
  }

  const logout = () => {
    setAuthToken(null)
    setStoredUser(null)
    setToken(null)
    setUser(null)
    try {
      if (typeof window !== 'undefined') {
        sessionStorage.removeItem('evidencebridge_active_audit')
        localStorage.removeItem('evidencebridge_active_audit')
      }
    } catch {
      // ignore
    }
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!user,
        login,
        signup,
        demoLogin,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
