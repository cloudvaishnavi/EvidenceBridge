import React, { createContext, useContext, useState, useEffect } from 'react'
import type { ExtractAndVerifyResponse, SourceType } from '../types'

interface AuditContextType {
  result: ExtractAndVerifyResponse | null
  text: string
  sourceType: SourceType
  sourceUrl: string
  activePreset: string | null
  imagePreview: string | null
  imageName: string | null
  setResult: (res: ExtractAndVerifyResponse | null) => void
  setText: (t: string) => void
  setSourceType: (s: SourceType) => void
  setSourceUrl: (u: string) => void
  setActivePreset: (p: string | null) => void
  setImagePreview: (url: string | null) => void
  setImageName: (name: string | null) => void
  clearAudit: () => void
}

const AUDIT_STORAGE_KEY = 'evidencebridge_active_audit'

const AuditContext = createContext<AuditContextType | undefined>(undefined)

interface PersistedAuditState {
  result: ExtractAndVerifyResponse | null
  text: string
  sourceType: SourceType
  sourceUrl: string
  activePreset: string | null
  imageName: string | null
}

export function AuditProvider({ children }: { children: React.ReactNode }) {
  // Load persisted audit state synchronously on initialization
  const [result, setResultState] = useState<ExtractAndVerifyResponse | null>(() => {
    try {
      if (typeof window !== 'undefined') {
        const stored = sessionStorage.getItem(AUDIT_STORAGE_KEY)
        if (stored) {
          const parsed = JSON.parse(stored) as PersistedAuditState
          return parsed.result || null
        }
      }
    } catch {
      // Storage access might fail
    }
    return null
  })

  const [text, setTextState] = useState<string>(() => {
    try {
      if (typeof window !== 'undefined') {
        const stored = sessionStorage.getItem(AUDIT_STORAGE_KEY)
        if (stored) {
          const parsed = JSON.parse(stored) as PersistedAuditState
          return parsed.text || ''
        }
      }
    } catch {
      // Storage access might fail
    }
    return ''
  })

  const [sourceType, setSourceTypeState] = useState<SourceType>(() => {
    try {
      if (typeof window !== 'undefined') {
        const stored = sessionStorage.getItem(AUDIT_STORAGE_KEY)
        if (stored) {
          const parsed = JSON.parse(stored) as PersistedAuditState
          return parsed.sourceType || 'hospital_bill'
        }
      }
    } catch {
      // Storage access might fail
    }
    return 'hospital_bill'
  })

  const [sourceUrl, setSourceUrlState] = useState<string>(() => {
    try {
      if (typeof window !== 'undefined') {
        const stored = sessionStorage.getItem(AUDIT_STORAGE_KEY)
        if (stored) {
          const parsed = JSON.parse(stored) as PersistedAuditState
          return parsed.sourceUrl || ''
        }
      }
    } catch {
      // Storage access might fail
    }
    return ''
  })

  const [activePreset, setActivePresetState] = useState<string | null>(() => {
    try {
      if (typeof window !== 'undefined') {
        const stored = sessionStorage.getItem(AUDIT_STORAGE_KEY)
        if (stored) {
          const parsed = JSON.parse(stored) as PersistedAuditState
          return parsed.activePreset || null
        }
      }
    } catch {
      // Storage access might fail
    }
    return null
  })

  const [imagePreview, setImagePreviewState] = useState<string | null>(null)
  const [imageName, setImageNameState] = useState<string | null>(() => {
    try {
      if (typeof window !== 'undefined') {
        const stored = sessionStorage.getItem(AUDIT_STORAGE_KEY)
        if (stored) {
          const parsed = JSON.parse(stored) as PersistedAuditState
          return parsed.imageName || null
        }
      }
    } catch {
      // Storage access might fail
    }
    return null
  })

  // Persist whenever state changes
  useEffect(() => {
    try {
      if (typeof window !== 'undefined') {
        if (result || text || activePreset) {
          const stateToSave: PersistedAuditState = {
            result,
            text,
            sourceType,
            sourceUrl,
            activePreset,
            imageName,
          }
          sessionStorage.setItem(AUDIT_STORAGE_KEY, JSON.stringify(stateToSave))
        } else {
          sessionStorage.removeItem(AUDIT_STORAGE_KEY)
        }
      }
    } catch {
      // Storage quota or restriction
    }
  }, [result, text, sourceType, sourceUrl, activePreset, imageName])

  const setResult = (res: ExtractAndVerifyResponse | null) => {
    setResultState(res)
  }

  const setText = (t: string) => {
    setTextState(t)
  }

  const setSourceType = (s: SourceType) => {
    setSourceTypeState(s)
  }

  const setSourceUrl = (u: string) => {
    setSourceUrlState(u)
  }

  const setActivePreset = (p: string | null) => {
    setActivePresetState(p)
  }

  const setImagePreview = (url: string | null) => {
    setImagePreviewState(url)
  }

  const setImageName = (name: string | null) => {
    setImageNameState(name)
  }

  const clearAudit = () => {
    setResultState(null)
    setTextState('')
    setActivePresetState(null)
    setImagePreviewState(null)
    setImageNameState(null)
    setSourceUrlState('')
    try {
      if (typeof window !== 'undefined') {
        sessionStorage.removeItem(AUDIT_STORAGE_KEY)
        localStorage.removeItem(AUDIT_STORAGE_KEY)
      }
    } catch {
      // ignore
    }
  }

  return (
    <AuditContext.Provider
      value={{
        result,
        text,
        sourceType,
        sourceUrl,
        activePreset,
        imagePreview,
        imageName,
        setResult,
        setText,
        setSourceType,
        setSourceUrl,
        setActivePreset,
        setImagePreview,
        setImageName,
        clearAudit,
      }}
    >
      {children}
    </AuditContext.Provider>
  )
}

export function useAudit(): AuditContextType {
  const context = useContext(AuditContext)
  if (!context) {
    throw new Error('useAudit must be used within an AuditProvider')
  }
  return context
}
