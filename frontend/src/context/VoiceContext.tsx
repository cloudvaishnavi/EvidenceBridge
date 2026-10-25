import React, { createContext, useContext, useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from './AuthContext'

export interface ActiveClaimContext {
  claimId: string
  entity?: string | null
  action: 'accept' | 'flag' | 'abstain' | string
  verdict?: 'supported' | 'partially_supported' | 'contradicted' | 'insufficient_evidence' | string
  costAnomalyFlag?: boolean
  costRange?: string | null
  confidence?: number
  supportScore?: number
  reasoning?: string | null
  abstainReason?: string | null
  anomalyDetails?: {
    is_anomaly: boolean
    extracted_amount?: number | null
    benchmark_min?: number | null
    benchmark_max?: number | null
    multiplier?: number | null
    severity?: string | null
    explanation?: string
    benchmark_name?: string | null
  } | null
  city?: string | null
  sourceType?: string | null
}

export interface VoiceMessage {
  id: string
  sender: 'user' | 'assistant'
  text: string
  timestamp: Date
}

interface VoiceContextType {
  // Panel state
  isOpen: boolean
  setIsOpen: (open: boolean) => void
  isEnabled: boolean
  setIsEnabled: (enabled: boolean) => void

  // Language state
  language: 'en' | 'kn'
  setLanguage: (lang: 'en' | 'kn') => void

  // Speech engine state
  status: 'idle' | 'listening' | 'thinking' | 'speaking'
  isContinuous: boolean
  setIsContinuous: (continuous: boolean) => void
  kannadaVoiceAvailable: boolean
  transcript: string
  lastSpoken: string
  history: VoiceMessage[]
  error: string | null

  // Active document context
  activeClaim: ActiveClaimContext | null
  setActiveClaim: (claim: ActiveClaimContext | null) => void

  // Speech actions
  startListening: (continuousMode?: boolean) => void
  stopListening: () => void
  speak: (text: string, langOverride?: 'en' | 'kn') => void
  stopSpeaking: () => void

  // Pre-configured voice tasks
  readClaimAloud: (claimOverride?: ActiveClaimContext) => void
  explainClaim: (type?: 'explain' | 'why_flagged' | 'price_problem') => Promise<void>
  clearHistory: () => void
}

const VoiceContext = createContext<VoiceContextType | undefined>(undefined)

const STORAGE_LANG_KEY = 'evidencebridge_voice_lang'
const STORAGE_ENABLED_KEY = 'evidencebridge_voice_enabled'
const STORAGE_CONTINUOUS_KEY = 'evidencebridge_voice_continuous'

// Voice search helpers (browser-agnostic)
export function findKannadaVoice(voices: SpeechSynthesisVoice[]): SpeechSynthesisVoice | undefined {
  if (!voices || voices.length === 0) return undefined

  // 1. Primary: Match BCP-47 / ISO language codes (kn, kn-IN, kan, kan-IN)
  const langMatch = voices.find((v) => {
    const lang = (v.lang || '').toLowerCase().replace(/_/g, '-')
    return (
      lang === 'kn-in' ||
      lang === 'kn' ||
      lang.startsWith('kn-') ||
      lang === 'kan' ||
      lang.startsWith('kan-')
    )
  })
  if (langMatch) return langMatch

  // 2. Secondary: Match by voice name or URI (English "kannada", native script "ಕನ್ನಡ", Windows "gagan"/"sapna")
  return voices.find((v) => {
    const nameLower = (v.name || '').toLowerCase()
    const rawName = v.name || ''
    const uriLower = (v.voiceURI || '').toLowerCase()
    const rawUri = v.voiceURI || ''

    return (
      nameLower.includes('kannada') ||
      rawName.includes('ಕನ್ನಡ') ||
      nameLower.includes('gagan') ||
      nameLower.includes('sapna') ||
      uriLower.includes('kannada') ||
      rawUri.includes('ಕನ್ನಡ') ||
      uriLower.includes('kn-in') ||
      uriLower.includes('kn_in') ||
      uriLower.includes('kn-') ||
      uriLower.includes('kn_')
    )
  })
}

export function findEnglishVoice(voices: SpeechSynthesisVoice[]): SpeechSynthesisVoice | undefined {
  if (!voices || voices.length === 0) return undefined
  return (
    voices.find(
      (v) =>
        (v.lang || '').toLowerCase().startsWith('en') &&
        (v.name.includes('Google') ||
          v.name.includes('Natural') ||
          v.name.includes('Samantha') ||
          v.name.includes('Jenny') ||
          v.name.includes('Guy') ||
          v.name.includes('Zira') ||
          v.name.includes('David'))
    ) ||
    voices.find((v) => (v.lang || '').toLowerCase().startsWith('en')) ||
    voices[0]
  )
}

// Helper to query local Ollama LLM
async function queryLocalOllama(prompt: string, systemPrompt?: string): Promise<string | null> {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), 7000)

  const payload = {
    model: 'phi3:mini',
    prompt,
    system:
      systemPrompt ||
      'You are EvidenceBridge AI Voice Assistant for clinical claims and medical bills. Provide a clear, natural, spoken answer in 1 or 2 concise sentences without markdown or bullet points.',
    stream: false,
  }

  const customOllamaUrl = import.meta.env.VITE_OLLAMA_BASE_URL
  if (customOllamaUrl) {
    try {
      const res = await fetch(`${customOllamaUrl.replace(/\/+$/, '')}/api/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: controller.signal,
      })
      clearTimeout(timeoutId)
      if (res.ok) {
        const data = await res.json()
        return data.response?.trim() || null
      }
    } catch {
      clearTimeout(timeoutId)
      return null
    }
  }

  const isLocalHost =
    typeof window !== 'undefined' &&
    (window.location.hostname === 'localhost' ||
      window.location.hostname === '127.0.0.1' ||
      window.location.hostname === '[::1]')

  try {
    const res = await fetch('/ollama/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: controller.signal,
    })
    clearTimeout(timeoutId)
    if (!res.ok) throw new Error('Proxy failed')
    const data = await res.json()
    return data.response?.trim() || null
  } catch {
    clearTimeout(timeoutId)
    if (!isLocalHost) {
      return null
    }
    try {
      const res2 = await fetch('http://localhost:11434/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!res2.ok) return null
      const data2 = await res2.json()
      return data2.response?.trim() || null
    } catch {
      return null
    }
  }
}

export function VoiceProvider({ children }: { children: React.ReactNode }) {
  const { logout } = useAuth()
  const navigate = useNavigate()

  const [isOpen, setIsOpen] = useState(false)
  const [isEnabled, setIsEnabled] = useState<boolean>(() => {
    try {
      const val = localStorage.getItem(STORAGE_ENABLED_KEY)
      return val !== null ? JSON.parse(val) : true
    } catch {
      return true
    }
  })

  const [isContinuous, setIsContinuousState] = useState<boolean>(() => {
    try {
      const val = localStorage.getItem(STORAGE_CONTINUOUS_KEY)
      return val !== null ? JSON.parse(val) : false
    } catch {
      return false
    }
  })

  const [kannadaVoiceAvailable, setKannadaVoiceAvailable] = useState<boolean>(false)

  const [language, setLanguageState] = useState<'en' | 'kn'>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_LANG_KEY)
      return saved === 'kn' ? 'kn' : 'en'
    } catch {
      return 'en'
    }
  })

  const [status, setStatus] = useState<'idle' | 'listening' | 'thinking' | 'speaking'>('idle')
  const [transcript, setTranscript] = useState('')
  const [lastSpoken, setLastSpoken] = useState('')
  const [history, setHistory] = useState<VoiceMessage[]>([])
  const [error, setError] = useState<string | null>(null)
  const [activeClaim, setActiveClaim] = useState<ActiveClaimContext | null>(null)

  // Web Speech API refs
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const recognitionRef = useRef<any>(null)
  const availableVoicesRef = useRef<SpeechSynthesisVoice[]>([])
  const activeUtteranceRef = useRef<SpeechSynthesisUtterance | null>(null)
  const isContinuousRef = useRef(isContinuous)
  isContinuousRef.current = isContinuous

  const statusRef = useRef(status)
  statusRef.current = status

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const restartListeningTimeoutRef = useRef<any>(null)

  const setIsContinuous = (continuous: boolean) => {
    setIsContinuousState(continuous)
    isContinuousRef.current = continuous
    try {
      localStorage.setItem(STORAGE_CONTINUOUS_KEY, JSON.stringify(continuous))
    } catch {
      // ignore
    }
  }

  // Dynamic voice query and refresh
  const updateVoices = useCallback(() => {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
      setKannadaVoiceAvailable(false)
      return
    }
    const voices = window.speechSynthesis.getVoices()
    if (voices && voices.length > 0) {
      availableVoicesRef.current = voices
      const hasKn = !!findKannadaVoice(voices)
      setKannadaVoiceAvailable(hasKn)
    }
  }, [])

  // Persist language
  const setLanguage = (lang: 'en' | 'kn') => {
    setLanguageState(lang)
    try {
      localStorage.setItem(STORAGE_LANG_KEY, lang)
    } catch {
      // ignore
    }
    setError(null)
    if (lang === 'kn') {
      updateVoices()
    }
  }

  // Persist isEnabled
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_ENABLED_KEY, JSON.stringify(isEnabled))
    } catch {
      // ignore
    }
  }, [isEnabled])

  // Load and cache browser voices at runtime (handling async voice loading)
  useEffect(() => {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) return

    updateVoices()
    window.speechSynthesis.onvoiceschanged = updateVoices

    // Check at staggered intervals to catch asynchronous voice loading
    const t1 = setTimeout(updateVoices, 100)
    const t2 = setTimeout(updateVoices, 400)
    const t3 = setTimeout(updateVoices, 1200)

    return () => {
      clearTimeout(t1)
      clearTimeout(t2)
      clearTimeout(t3)
      if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
        window.speechSynthesis.onvoiceschanged = null
        try {
          window.speechSynthesis.cancel()
        } catch {
          // ignore
        }
      }
      activeUtteranceRef.current = null
      if (restartListeningTimeoutRef.current) {
        clearTimeout(restartListeningTimeoutRef.current)
      }
    }
  }, [updateVoices])

  // Stop speaking
  const stopSpeaking = useCallback(() => {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      try {
        window.speechSynthesis.cancel()
        if (window.speechSynthesis.paused) {
          window.speechSynthesis.resume()
        }
      } catch {
        // ignore
      }
    }
    activeUtteranceRef.current = null
    setStatus((prev) => (prev === 'speaking' ? 'idle' : prev))
  }, [])

  // Text-To-Speech implementation using native browser SpeechSynthesis
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const startListeningRef = useRef<any>(null)

  const speak = useCallback(
    (text: string, langOverride?: 'en' | 'kn') => {
      const activeLang = langOverride || language
      stopSpeaking()
      setLastSpoken(text)

      // Add to conversation history
      setHistory((prev) => [
        ...prev.slice(-15),
        {
          id: `msg_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`,
          sender: 'assistant',
          text,
          timestamp: new Date(),
        },
      ])

      if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
        setStatus('idle')
        setError(
          activeLang === 'kn'
            ? 'Kannada voice is not available on this device. Showing text instead.'
            : 'Speech synthesis is not supported on this browser. Showing text instead.'
        )
        return
      }

      // Dynamically query available voices at runtime
      const liveVoices = window.speechSynthesis.getVoices()
      if (liveVoices && liveVoices.length > 0) {
        availableVoicesRef.current = liveVoices
      }
      const voices = (liveVoices && liveVoices.length > 0) ? liveVoices : availableVoicesRef.current

      if (activeLang === 'kn') {
        const knVoice = findKannadaVoice(voices)
        if (!knVoice) {
          // HONEST FALLBACK:
          // Never set status to 'speaking'. Never show speaking animation.
          // Explicitly inform the user that Kannada voice is unavailable and text is shown instead.
          setKannadaVoiceAvailable(false)
          activeUtteranceRef.current = null
          setStatus('idle')
          setError('Kannada voice is not available on this device. Showing text instead.')
          return
        }

        // Suitable Kannada voice is available on this device
        setKannadaVoiceAvailable(true)
        setError(null)

        const utterance = new SpeechSynthesisUtterance(text)
        utterance.voice = knVoice
        utterance.lang = knVoice.lang || 'kn-IN'
        utterance.rate = 0.95
        utterance.pitch = 1.0

        activeUtteranceRef.current = utterance

        utterance.onstart = () => {
          setStatus('speaking')
        }

        utterance.onend = () => {
          activeUtteranceRef.current = null
          setStatus('idle')
          if (isContinuousRef.current) {
            if (restartListeningTimeoutRef.current) clearTimeout(restartListeningTimeoutRef.current)
            restartListeningTimeoutRef.current = setTimeout(() => {
              if (isContinuousRef.current && statusRef.current === 'idle') {
                startListeningRef.current?.()
              }
            }, 450)
          }
        }

        utterance.onerror = (e) => {
          console.warn('Kannada SpeechSynthesis error:', e)
          activeUtteranceRef.current = null
          setStatus('idle')
        }

        // Unstick any paused audio stream in Chromium
        if (window.speechSynthesis.paused) {
          window.speechSynthesis.resume()
        }
        window.speechSynthesis.speak(utterance)
        return
      }

      // English voice path
      const enVoice = findEnglishVoice(voices)
      setError(null)

      const utterance = new SpeechSynthesisUtterance(text)
      if (enVoice) {
        utterance.voice = enVoice
        utterance.lang = enVoice.lang || 'en-US'
      } else {
        utterance.lang = 'en-US'
      }
      utterance.rate = 1.0
      utterance.pitch = 1.0

      activeUtteranceRef.current = utterance

      utterance.onstart = () => {
        setStatus('speaking')
      }

      utterance.onend = () => {
        activeUtteranceRef.current = null
        setStatus('idle')
        if (isContinuousRef.current) {
          if (restartListeningTimeoutRef.current) clearTimeout(restartListeningTimeoutRef.current)
          restartListeningTimeoutRef.current = setTimeout(() => {
            if (isContinuousRef.current && statusRef.current === 'idle') {
              startListeningRef.current?.()
            }
          }, 450)
        }
      }

      utterance.onerror = (e) => {
        console.warn('English SpeechSynthesis error:', e)
        activeUtteranceRef.current = null
        setStatus('idle')
      }

      if (window.speechSynthesis.paused) {
        window.speechSynthesis.resume()
      }
      window.speechSynthesis.speak(utterance)
    },
    [language, stopSpeaking]
  )

  // Read current claim aloud
  const readClaimAloud = useCallback(
    (claimOverride?: ActiveClaimContext) => {
      const claim = claimOverride || activeClaim
      if (!claim) {
        const noDocMsg =
          language === 'kn'
            ? 'ಪ್ರಸ್ತುತ ಯಾವುದೇ ಕ್ಲೈಮ್ ಆಯ್ಕೆಯಾಗಿಲ್ಲ. ದಯವಿಟ್ಟು ಕ್ಲೈಮ್ ಅನ್ನು ತೆರೆಯಿರಿ.'
            : 'No claim is currently open on your screen to read aloud.'
        speak(noDocMsg)
        return
      }

      let textToSpeak = ''

      if (language === 'kn') {
        const actionKn =
          claim.action === 'accept'
            ? 'ಅನುಮೋದಿಸಲಾಗಿದೆ'
            : claim.action === 'flag'
            ? 'ಪರಿಶೀಲನೆಗಾಗಿ ಫ್ಲ್ಯಾಗ್ ಮಾಡಲಾಗಿದೆ'
            : 'ಮಾಹಿತಿಗಾಗಿ ತಡೆಹಿಡಿಯಲಾಗಿದೆ'

        textToSpeak = `ಕ್ಲೈಮ್ ಆಡಿಟ್ ಫಲಿತಾಂಶ: ${actionKn}. `
        if (claim.entity) {
          textToSpeak += `ಕಾರ್ಯವಿಧಾನ: ${claim.entity}. `
        }
        if (claim.costAnomalyFlag && claim.anomalyDetails?.multiplier) {
          textToSpeak += `ಬೆಲೆ ಎಚ್ಚರಿಕೆ: ಬಿಲ್ ಮಾಡಿದ ಮೊತ್ತ ಸಾಮಾನ್ಯ ಬೆಲೆಗಿಂತ ${claim.anomalyDetails.multiplier.toFixed(1)} ಪಟ್ಟು ಹೆಚ್ಚಾಗಿದೆ. `
        }
        if (claim.reasoning) {
          textToSpeak += `ವಿವರಣೆ: ${claim.reasoning}`
        }
      } else {
        const actionEn =
          claim.action === 'accept'
            ? 'Approved'
            : claim.action === 'flag'
            ? 'Flagged for Review'
            : 'Held for Information'

        textToSpeak = `Audit Verdict: ${actionEn}. `
        if (claim.entity) {
          textToSpeak += `For ${claim.entity}. `
        }
        if (claim.costAnomalyFlag && claim.anomalyDetails) {
          const mult = claim.anomalyDetails.multiplier ? claim.anomalyDetails.multiplier.toFixed(1) : '3.0'
          textToSpeak += `Price Alert: Charge was billed at ${mult} times the benchmark maximum. `
        }
        if (claim.reasoning) {
          textToSpeak += `Clinical rationale: ${claim.reasoning}`
        }
      }

      speak(textToSpeak)
    },
    [activeClaim, language, speak]
  )

  // Explain claim with local Ollama or deterministic synthesis
  const explainClaim = useCallback(
    async (type: 'explain' | 'why_flagged' | 'price_problem' = 'explain') => {
      if (!activeClaim) {
        const msg =
          language === 'kn'
            ? 'ಪ್ರಸ್ತುತ ಪರದೆಯ ಮೇಲೆ ಯಾವುದೇ ಕ್ಲೈಮ್ ಆಯ್ಕೆಯಾಗಿಲ್ಲ.'
            : 'No claim is currently open to explain. Open a claim first.'
        speak(msg)
        return
      }

      setStatus('thinking')

      // Synthesize prompt for Ollama
      const claimDetails = `
Claim: ${activeClaim.entity || 'Medical service'}
Billed: ${activeClaim.costRange || 'unspecified'}
Verdict: ${activeClaim.verdict || 'unknown'}
Action: ${activeClaim.action}
Support Score: ${Math.round((activeClaim.supportScore || 0) * 100)}%
Cost Anomaly Flag: ${activeClaim.costAnomalyFlag ? 'Yes' : 'No'}
Multiplier: ${activeClaim.anomalyDetails?.multiplier || '1.0'}x
Benchmark: ₹${activeClaim.anomalyDetails?.benchmark_min || 0} - ₹${activeClaim.anomalyDetails?.benchmark_max || 0}
Reasoning: ${activeClaim.reasoning || 'None'}
`

      let userQuery = 'Explain this medical claim in simple plain terms for a patient or reviewer.'
      if (type === 'why_flagged') {
        userQuery = 'Explain specifically why this claim was flagged for review in simple terms.'
      } else if (type === 'price_problem') {
        userQuery = 'Explain the pricing benchmark and markup problem for this billed procedure.'
      }

      const prompt = `Here is the audited claim data:\n${claimDetails}\n\nQuestion: ${userQuery}\nAnswer in 1 or 2 concise, spoken sentences.`

      // Try local Ollama first
      const ollamaAnswer = await queryLocalOllama(prompt)

      if (ollamaAnswer && language === 'en') {
        speak(ollamaAnswer)
        return
      }

      // Currency check
      const isUsd =
        (activeClaim.costRange || '').includes('$') ||
        (activeClaim.costRange || '').toUpperCase().includes('USD') ||
        (activeClaim.anomalyDetails?.explanation || '').includes('$')
      const currencySymbolEn = isUsd ? '$' : '₹'
      const currencyNameKn = isUsd ? 'ಡಾಲರ್' : 'ರೂಪಾಯಿ'

      // High-quality deterministic fallback (and Kannada synthesis)
      let fallbackText = ''

      if (language === 'kn') {
        if (type === 'why_flagged') {
          if (activeClaim.costAnomalyFlag && activeClaim.anomalyDetails?.multiplier) {
            fallbackText = `ಈ ಕ್ಲೈಮ್ ಅನ್ನು ಫ್ಲ್ಯಾಗ್ ಮಾಡಲಾಗಿದೆ ಏಕೆಂದರೆ ಬಿಲ್ ಮಾಡಿದ ಶುಲ್ಕ ಸಾಮಾನ್ಯ ಮಾನದಂಡಕ್ಕಿಂತ ${activeClaim.anomalyDetails.multiplier.toFixed(1)} ಪಟ್ಟು ಹೆಚ್ಚಾಗಿದೆ.`
          } else if (activeClaim.verdict === 'contradicted') {
            fallbackText = `ಈ ಕಾರ್ಯವಿಧಾನವು ಅಧಿಕೃತ ವೈದ್ಯಕೀಯ ಮಾರ್ಗಸೂಚಿಗಳಿಗೆ ವಿರುದ್ಧವಾಗಿರುವುದರಿಂದ ಇದನ್ನು ಪರಿಶೀಲನೆಗೆ ಇರಿಸಲಾಗಿದೆ.`
          } else {
            fallbackText = `ಮಾರ್ಗಸೂಚಿ ವ್ಯತ್ಯಾಸ ಅಥವಾ ಬೆಲೆಯ ಹೆಚ್ಚಳದ ಕಾರಣ ಈ ಕ್ಲೈಮ್ ಅನ್ನು ಫ್ಲ್ಯಾಗ್ ಮಾಡಲಾಗಿದೆ.`
          }
        } else if (type === 'price_problem') {
          if (activeClaim.anomalyDetails) {
            const mult = activeClaim.anomalyDetails.multiplier?.toFixed(1) || '3.0'
            const max = activeClaim.anomalyDetails.benchmark_max?.toLocaleString('en-IN') || '0'
            fallbackText = `ಬಿಲ್ ಮಾಡಿದ ಮೊತ್ತವು ಸಾಮಾನ್ಯ ಮಾನದಂಡದ ಗರಿಷ್ಠ ${currencyNameKn} ${max} ಕ್ಕಿಂತ ${mult} ಪಟ್ಟು ಹೆಚ್ಚಾಗಿದೆ. ಇದು ಅಸಹಜ ಬೆಲೆ ಹೆಚ್ಚಳವಾಗಿದೆ.`
          } else {
            fallbackText = `ಈ ಸೇವೆಗೆ ಯಾವುದೇ ಸಾರ್ವಜನಿಕ ಬೆಲೆಯ ಮಾನದಂಡ ಲಭ್ಯವಿಲ್ಲ.`
          }
        } else {
          fallbackText = `ಇದು ${activeClaim.entity} ಕ್ಲೈಮ್ ಆಗಿದೆ. ಇದರ ಅಂತಿಮ ನಿರ್ಧಾರ ${activeClaim.action === 'accept' ? 'ಅನುಮೋದನೆ' : 'ಪರಿಶೀಲನೆ'}. ವೈದ್ಯಕೀಯ ಮಾರ್ಗಸೂಚಿ ಹೊಂದಾಣಿಕೆ ಶೇಕಡಾ ${Math.round((activeClaim.supportScore || 0) * 100)} ರಷ್ಟಿದೆ.`
        }
      } else {
        if (type === 'why_flagged') {
          if (activeClaim.costAnomalyFlag && activeClaim.anomalyDetails?.multiplier) {
            fallbackText = `This claim was flagged because the billed charge is ${activeClaim.anomalyDetails.multiplier.toFixed(1)} times higher than the regional benchmark for this procedure.`
          } else if (activeClaim.verdict === 'contradicted') {
            fallbackText = `This claim was flagged because clinical guidelines advise against this procedure for the stated diagnosis.`
          } else {
            fallbackText = `This claim was flagged due to potential pricing markups or clinical guideline conflicts requiring itemization review.`
          }
        } else if (type === 'price_problem') {
          if (activeClaim.anomalyDetails) {
            const mult = activeClaim.anomalyDetails.multiplier?.toFixed(1) || '3.0'
            const max = activeClaim.anomalyDetails.benchmark_max?.toLocaleString('en-IN') || '0'
            fallbackText = `The billed amount exceeds the expected maximum of ${currencySymbolEn}${max} by ${mult} times, triggering a high-severity price alert.`
          } else {
            fallbackText = `There is no standard public pricing benchmark available for this high-cost line item.`
          }
        } else {
          fallbackText = `This is a claim for ${activeClaim.entity || 'this procedure'}. The audit outcome is ${activeClaim.action.toUpperCase()}, with a guideline match confidence of ${Math.round((activeClaim.supportScore || 0) * 100)}%.`
        }
      }

      speak(fallbackText)
    },
    [activeClaim, language, speak]
  )

  // Voice Command Dispatcher
  const handleVoiceCommand = useCallback(
    async (recognizedText: string) => {
      const rawText = (recognizedText || '').trim()
      if (!rawText) return

      // Add user transcript to conversation history
      setHistory((prev) => [
        ...prev.slice(-15),
        {
          id: `msg_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`,
          sender: 'user',
          text: rawText,
          timestamp: new Date(),
        },
      ])

      const rawLower = rawText.toLowerCase()
      // Strip zero-width non-joiners (\u200C), joiners (\u200D), and normalize spaces
      const text = rawLower.replace(/[\u200B-\u200D\uFEFF]/g, '').replace(/\s+/g, ' ')

      const matchesAny = (...patterns: string[]) => {
        return patterns.some((p) => {
          const cleanP = p.toLowerCase().replace(/[\u200B-\u200D\uFEFF]/g, '').trim()
          return text.includes(cleanP) || rawLower.includes(p.toLowerCase()) || text === cleanP
        })
      }

      // 1. Natural Stop / Disable Voice Assistant Commands
      if (
        matchesAny(
          'stop listening',
          'disable voice',
          'turn off voice',
          'pause voice',
          'pause listening',
          'shut down voice',
          'stop assistant',
          'quiet',
          'shut up',
          'ನಿಲ್ಲಿಸು',
          'ನಿಲ್ಲಿಸಿ',
          'ಮುಕ್ತಾಯ',
          'ಸಾಕು',
          'ಕೇಳಬೇಡ',
          'ಧ್ವನಿ ನಿಲ್ಲಿಸು',
          'ಧ್ವನಿ ನಿಲ್ಲಿಸಿ'
        )
      ) {
        setIsContinuous(false)
        stopSpeaking()
        if (recognitionRef.current) {
          try {
            recognitionRef.current.stop()
          } catch {
            // ignore
          }
        }
        setStatus('idle')
        const stoppedMsg =
          language === 'kn'
            ? 'ಧ್ವನಿ ಆಲಿಸುವಿಕೆಯನ್ನು ನಿಲ್ಲಿಸಲಾಗಿದೆ. ನೀವು ಯಾವಾಗ ಬೇಕಾದರೂ ಮತ್ತೆ ಮೈಕ್ರೊಫೋನ್ ಒತ್ತಬಹುದು.'
            : 'Voice listening is now paused. Tap the microphone anytime to resume.'
        speak(stoppedMsg)
        return
      }

      // Simple Stop / Cancel Speech
      if (text === 'stop' || text === 'cancel' || text === 'silence' || text === 'ನಿಲ್ಲು') {
        stopSpeaking()
        return
      }

      // 2. Read Result Aloud
      // Requirements: “ಫಲಿತಾಂಶವನ್ನು ಓದಿ” / “ಫಲಿತಾಂಶ ಓದಿ” → Read result aloud
      if (
        matchesAny(
          'read result',
          'read this result',
          'read aloud',
          'read claim',
          'ಫಲಿತಾಂಶವನ್ನು ಓದಿ',
          'ಫಲಿತಾಂಶ ಓದಿ',
          'ಫಲಿತಾಂಶವನ್ನು ಹೇಳಿ',
          'ಫಲಿತಾಂಶ ಹೇಳಿ',
          'ಫಲಿತಾಂಶ',
          'ಓದಿ',
          'ಹೇಳಿ'
        )
      ) {
        readClaimAloud()
        return
      }

      // 3. Hospital Finder
      // Requirements: “ಆಸ್ಪತ್ರೆ” / “ಹಾಸ್ಪಿಟಲ್” → Go to Hospital Finder (/hospitals)
      if (
        matchesAny(
          'hospital',
          'find hospital',
          'find hospitals',
          'search hospital',
          'locate hospital',
          'nearby care',
          'clinic',
          'doctor',
          'ಆಸ್ಪತ್ರೆ',
          'ಆಸ್ಪತ್ರೆಗಳು',
          'ಆಸ್ಪತ್ರೆ ಹುಡುಕಿ',
          'ಹಾಸ್ಪಿಟಲ್',
          'ಹಾಸ್ಪಿಟಲ್ಸ್',
          'ಹಾಸ್ಪಿಟಲ್ ಹುಡುಕಿ'
        )
      ) {
        navigate('/hospitals')
        const navMsg =
          language === 'kn'
            ? 'ಹತ್ತಿರದ ಆಸ್ಪತ್ರೆಗಳು ಮತ್ತು ವೆಚ್ಚ ಹುಡುಕುವ ಪುಟಕ್ಕೆ ಹೋಗುತ್ತಿದ್ದೇವೆ.'
            : 'Opening Hospital Finder to locate nearby facilities and compare prices.'
        speak(navMsg)
        return
      }

      // 4. Audit Workspace / Home
      // Requirements: “ಮುಖಪುಟಕ್ಕೆ ಹೋಗಿ” / “ಆಡಿಟ್” → Go to Audit (/audit)
      if (
        matchesAny(
          'go to home',
          'go home',
          'go to audit',
          'open audit',
          'audit',
          'home',
          'ಮುಖಪುಟಕ್ಕೆ ಹೋಗಿ',
          'ಮುಖಪುಟ',
          'ಆಡಿಟ್',
          'ಆಡಿಟ್‌'
        )
      ) {
        navigate('/audit')
        const navMsg = language === 'kn' ? 'ಮುಖಪುಟಕ್ಕೆ ಹೋಗುತ್ತಿದ್ದೇವೆ.' : 'Navigating to Audit workspace.'
        speak(navMsg)
        return
      }

      // 5. Claims Explorer
      // Requirements: “ಕ್ಲೈಮ್ಗಳು” / “ಕ್ಲೈಮ್‌ಗಳು” → Go to Claims (/claims)
      if (
        matchesAny(
          'go to claims',
          'show claims',
          'browse claims',
          'open claims',
          'claims',
          'claims explorer',
          'ಕ್ಲೈಮ್ಗಳು',
          'ಕ್ಲೈಮ್‌ಗಳು',
          'ಕ್ಲೈಮ್',
          'ಕ್ಲೈಮ್ಸ್',
          'ಕ್ಲೈಮುಗಳು'
        )
      ) {
        navigate('/claims')
        const navMsg = language === 'kn' ? 'ಕ್ಲೈಮ್‌ಗಳ ಪಟ್ಟಿಗೆ ಹೋಗುತ್ತಿದ್ದೇವೆ.' : 'Opening Claims Explorer.'
        speak(navMsg)
        return
      }

      // 6. Insights Dashboard
      // Requirements: “ಒಳನೋಟ” / “ಇನ್ಸೈಟ್ಸ್” → Go to Insights (/insights)
      if (
        matchesAny(
          'insights',
          'dashboard',
          'statistics',
          'visual analytics',
          'analytics',
          'ಒಳನೋಟ',
          'ಒಳನೋಟಗಳು',
          'ಇನ್ಸೈಟ್ಸ್',
          'ಇನ್‌ಸೈಟ್ಸ್',
          'ಗಣಾಂಕ',
          'ವಿಶ್ಲೇಷಣೆ'
        )
      ) {
        navigate('/insights')
        const navMsg =
          language === 'kn'
            ? 'ಒಳನೋಟಗಳು ಮತ್ತು ಗಣಾಂಕಗಳ ಪುಟಕ್ಕೆ ಹೋಗುತ್ತಿದ್ದೇವೆ.'
            : 'Opening Visual Insights Dashboard.'
        speak(navMsg)
        return
      }

      // 7. Community Stories
      // Requirements: “ಸಮುದಾಯ” / “ಕಥೆಗಳು” → Go to Community Stories (/community)
      if (
        matchesAny(
          'community',
          'stories',
          'recovery stories',
          'patient stories',
          'ಸಮುದಾಯ',
          'ಕಥೆಗಳು',
          'ಕಮ್ಯೂನಿಟಿ'
        )
      ) {
        navigate('/community')
        const navMsg = language === 'kn' ? 'ಸಮುದಾಯ ಕಥೆಗಳ ಪುಟಕ್ಕೆ ಹೋಗುತ್ತಿದ್ದೇವೆ.' : 'Opening Community Stories.'
        speak(navMsg)
        return
      }

      // 8. Log Out
      // Requirements: “ಲಾಗ್ ಔಟ್” → Log out
      if (
        matchesAny(
          'log out',
          'logout',
          'sign out',
          'signout',
          'ಲಾಗ್ ಔಟ್',
          'ಲಾಗೌಟ್',
          'ಸೈನ್ ಔಟ್',
          'ಸೈನ್‌ಔಟ್'
        )
      ) {
        const logoutMsg = language === 'kn' ? 'ಖಾತೆಯಿಂದ ಲಾಗ್ ಔಟ್ ಮಾಡಲಾಗುತ್ತಿದೆ.' : 'Signing out of auditor session.'
        speak(logoutMsg)
        setTimeout(() => {
          logout()
          navigate('/')
        }, 1200)
        return
      }

      // 9. Help
      // Requirements: “ಸಹಾಯ” / “ಹೆಲ್ಪ್” → Help
      if (
        matchesAny(
          'help',
          'commands',
          'what can you do',
          'options',
          'ಸಹಾಯ',
          'ಹೆಲ್ಪ್'
        )
      ) {
        const helpText =
          language === 'kn'
            ? 'ನೀವು ಹೀಗೆ ಹೇಳಬಹುದು: ಮುಖಪುಟಕ್ಕೆ ಹೋಗಿ, ಕ್ಲೈಮ್‌ಗಳು, ಆಸ್ಪತ್ರೆ, ಒಳನೋಟ, ಸಮುದಾಯ, ಫಲಿತಾಂಶವನ್ನು ಓದಿ, ಅಥವಾ ಲಾಗ್ ಔಟ್.'
            : 'You can say: Go to audit, Claims, Hospital finder, Insights, Community stories, Read the result, or Log out.'
        speak(helpText)
        return
      }

      // 10. Regional Trust Density
      if (
        matchesAny(
          'trust density',
          'regional trust',
          'hospital reliability',
          'ನಂಬಿಕೆ',
          'ಟ್ರಸ್ಟ್'
        )
      ) {
        navigate('/trust-density')
        const navMsg = language === 'kn' ? 'ಪ್ರಾದೇಶಿಕ ನಂಬಿಕೆ ಪುಟಕ್ಕೆ ಹೋಗುತ್ತಿದ್ದೇವೆ.' : 'Opening Regional Trust Density.'
        speak(navMsg)
        return
      }

      // 11. Evaluation Harness
      if (
        matchesAny(
          'evaluation',
          'harness',
          'benchmark',
          'ಮೌಲ್ಯಮಾಪನ',
          'ಇವಾಲ್ಯುಯೇಷನ್'
        )
      ) {
        navigate('/evaluation')
        const navMsg = language === 'kn' ? 'ಮೌಲ್ಯಮಾಪನ ಪುಟಕ್ಕೆ ಹೋಗುತ್ತಿದ್ದೇವೆ.' : 'Opening Evaluation Harness.'
        speak(navMsg)
        return
      }

      // 12. Landing / Overview
      if (matchesAny('overview', 'welcome', 'landing', 'ವಿವರಣೆ')) {
        navigate('/welcome')
        speak(language === 'kn' ? 'ವಿವರಣೆ ಪುಟಕ್ಕೆ ಹೋಗುತ್ತಿದ್ದೇವೆ.' : 'Opening Platform Overview.')
        return
      }

      // 13. Filter Flagged Claims / Price Alerts
      if (matchesAny('filter flagged', 'show flagged', 'ಫ್ಲ್ಯಾಗ್ ಮಾಡಿದ ಕ್ಲೈಮ್', 'ಫ್ಲ್ಯಾಗ್')) {
        navigate('/claims')
        speak(language === 'kn' ? 'ಫ್ಲ್ಯಾಗ್ ಮಾಡಿದ ಕ್ಲೈಮ್‌ಗಳನ್ನು ತೋರಿಸಲಾಗುತ್ತಿದೆ.' : 'Showing flagged claims.')
        return
      }

      if (matchesAny('price alert', 'price problem', 'cost anomaly', 'ಬೆಲೆ ಎಚ್ಚರಿಕೆ', 'ಬೆಲೆಯ ಸಮಸ್ಯೆ', 'ಬೆಲೆ')) {
        if (activeClaim && matchesAny('why', 'problem', 'ಏನು', 'ವಿವರಿಸಿ')) {
          await explainClaim('price_problem')
          return
        }
        navigate('/claims')
        speak(language === 'kn' ? 'ಬೆಲೆಯ ಎಚ್ಚರಿಕೆ ಕ್ಲೈಮ್‌ಗಳನ್ನು ತೋರಿಸಲಾಗುತ್ತಿದೆ.' : 'Showing claims with price alerts.')
        return
      }

      // 14. Document-Aware Queries: Why Flagged?
      if (matchesAny('why flagged', 'why was this flagged', 'why is this flagged', 'ಏಕೆ ಫ್ಲ್ಯಾಗ್')) {
        await explainClaim('why_flagged')
        return
      }

      // 15. Document-Aware Queries: Explain Claim
      if (matchesAny('explain this claim', 'explain claim', 'explain this', 'ವಿವರಿಸಿ')) {
        await explainClaim('explain')
        return
      }

      // 16. General Fallback Query
      setStatus('thinking')
      const generalPrompt = `The user asked: "${rawText}". Provide a concise 1-sentence answer about EvidenceBridge healthcare auditing.`
      const generalAnswer = await queryLocalOllama(generalPrompt)

      if (generalAnswer && language === 'en') {
        speak(generalAnswer)
      } else {
        const fallback =
          language === 'kn'
            ? `ಕ್ಷಮಿಸಿ, "${rawText}" ಅರ್ಥವಾಗಲಿಲ್ಲ. ಸಹಾಯಕ್ಕಾಗಿ "ಸಹಾಯ" ಎಂದು ಹೇಳಿ.`
            : `I heard "${rawText}". Try saying "Read the result", "Explain this claim", or "Help".`
        speak(fallback)
      }
    },
    [activeClaim, explainClaim, language, logout, navigate, readClaimAloud, speak, stopSpeaking]
  )

  // Speech-To-Text implementation
  const startListening = useCallback(
    (continuousMode?: boolean) => {
      if (typeof window === 'undefined') return

      if (continuousMode !== undefined) {
        setIsContinuous(continuousMode)
      }

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition

      if (!SpeechRecognition) {
        setError('Speech recognition is not supported in this browser. Please use Google Chrome or Microsoft Edge.')
        return
      }

      stopSpeaking()
      setError(null)
      setTranscript('')

      try {
        const recognition = new SpeechRecognition()
        recognitionRef.current = recognition

        recognition.continuous = false
        recognition.interimResults = true
        recognition.lang = language === 'kn' ? 'kn-IN' : 'en-US'

        recognition.onstart = () => {
          setStatus('listening')
        }

        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        recognition.onresult = (event: any) => {
          let currentTranscript = ''
          for (let i = event.resultIndex; i < event.results.length; i++) {
            currentTranscript += event.results[i][0].transcript
          }
          setTranscript(currentTranscript)

          if (event.results[0].isFinal) {
            setStatus('thinking')
            handleVoiceCommand(currentTranscript)
          }
        }

        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        recognition.onerror = (event: any) => {
          console.warn('SpeechRecognition error:', event.error)
          if (event.error === 'not-allowed') {
            setError('Microphone permission was denied. Please allow microphone access in your browser.')
            setIsContinuous(false)
          } else if (event.error === 'no-speech') {
            // In continuous mode, no-speech is normal; wait briefly and retry if still active
            if (!isContinuousRef.current) {
              setError('No speech was detected. Please click the microphone and try again.')
            }
          } else if (event.error === 'language-not-supported' && language === 'kn') {
            setError('Kannada recognition is not supported on this browser engine. Falling back to English.')
            setLanguage('en')
          } else {
            setError(`Voice input error: ${event.error}`)
          }
          setStatus('idle')
        }

        recognition.onend = () => {
          if (statusRef.current === 'listening') {
            setStatus('idle')
          }
          // If continuous listening is enabled and assistant isn't speaking or thinking, auto-resume listening
          if (
            isContinuousRef.current &&
            statusRef.current !== 'speaking' &&
            statusRef.current !== 'thinking'
          ) {
            if (restartListeningTimeoutRef.current) {
              clearTimeout(restartListeningTimeoutRef.current)
            }
            restartListeningTimeoutRef.current = setTimeout(() => {
              if (isContinuousRef.current && statusRef.current === 'idle') {
                startListeningRef.current?.()
              }
            }, 350)
          }
        }

        recognition.start()
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : 'Failed to initialize microphone.')
        setStatus('idle')
      }
    },
    [handleVoiceCommand, language, stopSpeaking]
  )

  startListeningRef.current = startListening

  const stopListening = useCallback(() => {
    setIsContinuous(false)
    if (restartListeningTimeoutRef.current) {
      clearTimeout(restartListeningTimeoutRef.current)
    }
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop()
      } catch {
        // ignore
      }
    }
    setStatus('idle')
  }, [])

  const clearHistory = () => {
    setHistory([])
    setTranscript('')
    setError(null)
  }

  return (
    <VoiceContext.Provider
      value={{
        isOpen,
        setIsOpen,
        isEnabled,
        setIsEnabled,
        language,
        setLanguage,
        status,
        isContinuous,
        setIsContinuous,
        kannadaVoiceAvailable,
        transcript,
        lastSpoken,
        history,
        error,
        activeClaim,
        setActiveClaim,
        startListening,
        stopListening,
        speak,
        stopSpeaking,
        readClaimAloud,
        explainClaim,
        clearHistory,
      }}
    >
      {children}
    </VoiceContext.Provider>
  )
}

export function useVoice() {
  const context = useContext(VoiceContext)
  if (!context) {
    throw new Error('useVoice must be used within a VoiceProvider')
  }
  return context
}
