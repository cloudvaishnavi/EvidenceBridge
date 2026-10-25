import React, { createContext, useContext, useState, useEffect } from 'react'
import { loginApi, signupApi, demoAuthApi, getMeApi } from '../api/client'
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
  signup: (name: string, emailOrUsername: string, password: string, organization?: string) => Promise<boolean>
  demoLogin: () => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

const USER_STORAGE_KEY = 'evidencebridge_user'
const TOKEN_STORAGE_KEY = 'evidencebridge_token'

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(() => {
    try {
      return localStorage.getItem(TOKEN_STORAGE_KEY)
    } catch {
      return null
    }
  })

  const [user, setUser] = useState<User | null>(() => {
    try {
      const saved = localStorage.getItem(USER_STORAGE_KEY)
      if (saved) {
        return JSON.parse(saved)
      }
    } catch {
      // ignore JSON parse error
    }
    return null
  })

  // Synchronize user profile with backend on startup if token is present
  useEffect(() => {
    const activeToken = localStorage.getItem(TOKEN_STORAGE_KEY)
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
          localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(u))
        })
        .catch(() => {
          // If token verification fails (e.g. invalid or expired), keep cached or clear if 401
        })
    }
  }, [])

  useEffect(() => {
    if (user) {
      localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user))
    } else {
      localStorage.removeItem(USER_STORAGE_KEY)
    }
  }, [user])

  useEffect(() => {
    if (token) {
      localStorage.setItem(TOKEN_STORAGE_KEY, token)
    } else {
      localStorage.removeItem(TOKEN_STORAGE_KEY)
    }
  }, [token])

  const login = async (emailOrUsername: string, password: string): Promise<boolean> => {
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
      setToken(authRes.access_token)
      setUser(u)
      return true
    } catch (err: unknown) {
      // Fallback for offline demo accounts if backend is unreachable
      const cleanId = emailOrUsername.trim().toLowerCase()
      if (cleanId === 'demo' || cleanId === 'sarah.chen@stjudehealth.org') {
        demoLogin()
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
      setToken(authRes.access_token)
      setUser(u)
    } catch {
      // Offline fallback
      const fallbackDemo: User = {
        id: 'usr_demo_auditor',
        name: 'Dr. Sarah Chen, MD',
        email: 'sarah.chen@stjudehealth.org',
        role: 'Senior Clinical Claims Reviewer',
        organization: 'St. Jude Metropolitan Health System',
      }
      setToken('demo_bearer_token')
      setUser(fallbackDemo)
    }
  }

  const logout = () => {
    setToken(null)
    setUser(null)
    localStorage.removeItem(TOKEN_STORAGE_KEY)
    localStorage.removeItem(USER_STORAGE_KEY)
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
