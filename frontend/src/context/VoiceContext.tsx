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
  const audioFallbackRef = useRef<HTMLAudioElement | null>(null)
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

  // Persist language
  const setLanguage = (lang: 'en' | 'kn') => {
    setLanguageState(lang)
    try {
      localStorage.setItem(STORAGE_LANG_KEY, lang)
    } catch {
      // ignore
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

  // Load and cache browser voices
  useEffect(() => {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) return

    const updateVoices = () => {
      const voices = window.speechSynthesis.getVoices()
      if (voices.length > 0) {
        availableVoicesRef.current = voices
        const hasKn = voices.some(
          (v) =>
            v.lang.toLowerCase().startsWith('kn') ||
            v.lang.toLowerCase().replace('_', '-').includes('kn-in') ||
            v.name.toLowerCase().includes('kannada') ||
            v.name.toLowerCase().includes('gagan') ||
            v.name.toLowerCase().includes('sapna')
        )
        // Accurately reflect whether local browser voice pack exists
        setKannadaVoiceAvailable(hasKn)
      }
    }

    updateVoices()
    window.speechSynthesis.onvoiceschanged = updateVoices

    return () => {
      window.speechSynthesis.cancel()
      if (audioFallbackRef.current) {
        try {
          audioFallbackRef.current.pause()
        } catch {
          // ignore
        }
      }
      if (restartListeningTimeoutRef.current) {
        clearTimeout(restartListeningTimeoutRef.current)
      }
    }
  }, [])

  // Stop speaking
  const stopSpeaking = useCallback(() => {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel()
    }
    if (audioFallbackRef.current) {
      try {
        audioFallbackRef.current.pause()
        audioFallbackRef.current.currentTime = 0
      } catch {
        // ignore
      }
    }
    setStatus((prev) => (prev === 'speaking' ? 'idle' : prev))
  }, [])

  // Text-To-Speech implementation
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const startListeningRef = useRef<any>(null)

  const playAudioFallback = useCallback(
    (fallbackText: string, fallbackLang: 'en' | 'kn') => {
      try {
        if (audioFallbackRef.current) {
          try {
            audioFallbackRef.current.pause()
            audioFallbackRef.current.currentTime = 0
          } catch {
            // ignore
          }
        }
        const cleanSnippet = fallbackText.trim().replace(/\s+/g, ' ').slice(0, 350)
        // Use /api/tts which is reliably proxied to FastAPI backend
        const ttsUrl = `/api/tts?lang=${fallbackLang}&text=${encodeURIComponent(cleanSnippet)}`
        const audio = new Audio(ttsUrl)
        audioFallbackRef.current = audio

        audio.onplay = () => {
          setStatus('speaking')
        }
        audio.onended = () => {
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
        audio.onerror = (ev) => {
          console.warn('Audio fallback stream failed:', ev)
          setStatus('idle')
          setError(
            fallbackLang === 'kn'
              ? 'ಕನ್ನಡ ಆಡಿಯೋ ಲೋಡ್ ಆಗಲಿಲ್ಲ. ಪಠ್ಯವನ್ನು ಪರದೆಯ ಮೇಲೆ ಪ್ರದರ್ಶಿಸಲಾಗಿದೆ.'
              : 'Spoken audio could not be generated. Text is displayed on screen.'
          )
        }
        audio.play().catch((playErr) => {
          console.warn('Audio play restricted by browser autoplay policy:', playErr)
          setStatus('idle')
          if (playErr.name === 'NotAllowedError') {
            setError(
              fallbackLang === 'kn'
                ? 'ಆಡಿಯೋ ಕೇಳಲು ಕೆಳಗಿನ Repeat (🔊) ಬಟನ್ ಒತ್ತಿ.'
                : 'Click Repeat (🔊) to hear the spoken response.'
            )
          }
        })
      } catch (err) {
        console.warn('Audio fallback exception:', err)
        setStatus('idle')
      }
    },
    []
  )

  const speak = useCallback(
    (text: string, langOverride?: 'en' | 'kn') => {
      const activeLang = langOverride || language
      stopSpeaking()
      setError(null)
      setStatus('speaking')
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
        // Fallback to audio stream if browser SpeechSynthesis is absent
        playAudioFallback(text, activeLang)
        return
      }

      // Dynamically query available voices at runtime
      const liveVoices = window.speechSynthesis.getVoices()
      if (liveVoices.length > 0) {
        availableVoicesRef.current = liveVoices
      }
      const voices = liveVoices.length > 0 ? liveVoices : availableVoicesRef.current

      let matchedVoice: SpeechSynthesisVoice | undefined

      if (activeLang === 'kn') {
        matchedVoice = voices.find(
          (v) =>
            v.lang.toLowerCase().startsWith('kn') ||
            v.lang.toLowerCase().replace('_', '-').includes('kn-in') ||
            v.name.toLowerCase().includes('kannada') ||
            v.name.toLowerCase().includes('gagan') ||
            v.name.toLowerCase().includes('sapna')
        )

        // If no local Kannada voice pack in browser, seamlessly stream clean synthesized audio!
        if (!matchedVoice) {
          playAudioFallback(text, 'kn')
          return
        }
      } else {
        matchedVoice =
          voices.find(
            (v) =>
              v.lang.startsWith('en') &&
              (v.name.includes('Google') ||
                v.name.includes('Natural') ||
                v.name.includes('Samantha') ||
                v.name.includes('Zira'))
          ) || voices.find((v) => v.lang.startsWith('en'))
      }

      const utterance = new SpeechSynthesisUtterance(text)
      if (matchedVoice) {
        utterance.voice = matchedVoice
      }
      utterance.lang = activeLang === 'kn' ? 'kn-IN' : 'en-US'
      utterance.rate = activeLang === 'kn' ? 0.95 : 1.0
      utterance.pitch = 1.0

      utterance.onend = () => {
        setStatus('idle')
        // Auto-resume continuous listening if explicitly enabled
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
        console.warn('SpeechSynthesis error:', e)
        if (activeLang === 'kn') {
          // Failover to streaming audio on synthesis error
          playAudioFallback(text, 'kn')
          return
        }
        setStatus('idle')
        if (isContinuousRef.current) {
          if (restartListeningTimeoutRef.current) clearTimeout(restartListeningTimeoutRef.current)
          restartListeningTimeoutRef.current = setTimeout(() => {
            if (isContinuousRef.current && statusRef.current === 'idle') {
              startListeningRef.current?.()
            }
          }, 500)
        }
      }

      window.speechSynthesis.speak(utterance)
    },
    [language, playAudioFallback, stopSpeaking]
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
Benchmark: $${activeClaim.anomalyDetails?.benchmark_min || 0} - $${activeClaim.anomalyDetails?.benchmark_max || 0}
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
            const max = activeClaim.anomalyDetails.benchmark_max?.toFixed(2) || '0'
            fallbackText = `ಬಿಲ್ ಮಾಡಿದ ಮೊತ್ತವು ಅನುಮೋದಿತ ಗರಿಷ್ಠ ${max} ಡಾಲರ್ ಬೆಲೆಗಿಂತ ${mult} ಪಟ್ಟು ಹೆಚ್ಚಾಗಿದೆ. ಇದು ಅಸಹಜ ಬೆಲೆ ಹೆಚ್ಚಳವಾಗಿದೆ.`
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
            const max = activeClaim.anomalyDetails.benchmark_max?.toFixed(2) || '0'
            fallbackText = `The billed amount exceeds the expected maximum of $${max} by ${mult} times, triggering a high-severity price alert.`
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
      const text = recognizedText.trim().toLowerCase()
      if (!text) return

      // Add to history
      setHistory((prev) => [
        ...prev.slice(-15),
        {
          id: `msg_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`,
          sender: 'user',
          text: recognizedText,
          timestamp: new Date(),
        },
      ])

      // 1. Natural Stop / Disable Voice Assistant Commands
      if (
        text.includes('stop listening') ||
        text.includes('disable voice') ||
        text.includes('turn off voice') ||
        text.includes('pause voice') ||
        text.includes('pause listening') ||
        text.includes('shut down voice') ||
        text.includes('stop assistant') ||
        text.includes('quiet') ||
        text.includes('shut up') ||
        text.includes('ನಿಲ್ಲಿಸು') ||
        text.includes('ನಿಲ್ಲಿಸಿ') ||
        text.includes('ಮುಕ್ತಾಯ') ||
        text.includes('ಸಾಕು') ||
        text.includes('ಕೇಳಬೇಡ') ||
        text.includes('ಧ್ವನಿ ನಿಲ್ಲಿಸು')
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
      if (text === 'stop' || text === 'cancel' || text === 'silence') {
        stopSpeaking()
        return
      }

      // 1b. Navigation: Hospital Finder
      if (
        text.includes('hospital') ||
        text.includes('find hospital') ||
        text.includes('search hospital') ||
        text.includes('locate hospital') ||
        text.includes('nearby care') ||
        text.includes('clinic') ||
        text.includes('doctor') ||
        text.includes('ಆಸ್ಪತ್ರೆ') ||
        text.includes('ಆಸ್ಪತ್ರೆ ಹುಡುಕಿ') ||
        text.includes('ಆಸ್ಪತ್ರೆಗಳು')
      ) {
        navigate('/hospitals')
        const navMsg =
          language === 'kn'
            ? 'ಹತ್ತಿರದ ಆಸ್ಪತ್ರೆಗಳು ಮತ್ತು ವೆಚ್ಚ ಹುಡುಕುವ ಪುಟಕ್ಕೆ ಹೋಗುತ್ತಿದ್ದೇವೆ.'
            : 'Opening Hospital Finder to locate nearby facilities and compare prices.'
        speak(navMsg)
        return
      }

      // 2. Navigation: Home / Audit
      if (
        text.includes('go to home') ||
        text.includes('go home') ||
        text.includes('go to audit') ||
        text.includes('open audit') ||
        text.includes('ಮುಖಪುಟ') ||
        text.includes('ಆಡಿಟ್')
      ) {
        navigate('/audit')
        speak(language === 'kn' ? 'ಮುಖಪುಟಕ್ಕೆ ಹೋಗುತ್ತಿದ್ದೇವೆ.' : 'Navigating to Audit workspace.')
        return
      }

      // 3. Navigation: Claims Explorer
      if (
        text.includes('go to claims') ||
        text.includes('show claims') ||
        text.includes('browse claims') ||
        text.includes('open claims') ||
        text.includes('ಕ್ಲೈಮ್')
      ) {
        navigate('/claims')
        speak(language === 'kn' ? 'ಕ್ಲೈಮ್‌ಗಳ ಪಟ್ಟಿಗೆ ಹೋಗುತ್ತಿದ್ದೇವೆ.' : 'Opening Claims Explorer.')
        return
      }

      // 4. Navigation: Regional Trust Density
      if (
        text.includes('trust density') ||
        text.includes('regional trust') ||
        text.includes('hospital reliability') ||
        text.includes('ನಂಬಿಕೆ')
      ) {
        navigate('/trust-density')
        speak(language === 'kn' ? 'ಪ್ರಾದೇಶಿಕ ನಂಬಿಕೆ ಪುಟಕ್ಕೆ ಹೋಗುತ್ತಿದ್ದೇವೆ.' : 'Opening Regional Trust Density.')
        return
      }

      // 5. Navigation: Evaluation Harness
      if (
        text.includes('evaluation') ||
        text.includes('harness') ||
        text.includes('benchmark') ||
        text.includes('ಮೌಲ್ಯಮಾಪನ')
      ) {
        navigate('/evaluation')
        speak(language === 'kn' ? 'ಮೌಲ್ಯಮಾಪನ ಪುಟಕ್ಕೆ ಹೋಗುತ್ತಿದ್ದೇವೆ.' : 'Opening Evaluation Harness.')
        return
      }

      // 5b. Navigation: Insights / Visual Dashboard
      if (
        text.includes('insights') ||
        text.includes('dashboard') ||
        text.includes('statistics') ||
        text.includes('visual analytics') ||
        text.includes('ಗಣಾಂಕ') ||
        text.includes('ವಿಶ್ಲೇಷಣೆ')
      ) {
        navigate('/insights')
        speak(language === 'kn' ? 'ಗಣಾಂಕ ಮತ್ತು ವಿಶ್ಲೇಷಣೆ ಪುಟಕ್ಕೆ ಹೋಗುತ್ತಿದ್ದೇವೆ.' : 'Opening Visual Insights Dashboard.')
        return
      }

      // 6. Navigation: Overview / Welcome
      if (text.includes('overview') || text.includes('welcome') || text.includes('landing') || text.includes('ವಿವರಣೆ')) {
        navigate('/welcome')
        speak(language === 'kn' ? 'ವಿವರಣೆ ಪುಟಕ್ಕೆ ಹೋಗುತ್ತಿದ್ದೇವೆ.' : 'Opening Platform Overview.')
        return
      }

      // 6b. Navigation: Community Stories
      if (
        text.includes('community') ||
        text.includes('stories') ||
        text.includes('recovery stories') ||
        text.includes('ಕಮ್ಯೂನಿಟಿ') ||
        text.includes('ಕಥೆಗಳು')
      ) {
        navigate('/community')
        speak(language === 'kn' ? 'ಸಮುದಾಯ ಕಥೆಗಳ ಪುಟಕ್ಕೆ ಹೋಗುತ್ತಿದ್ದೇವೆ.' : 'Opening Community Stories.')
        return
      }

      // 7. Filter Flagged Claims / Price Alerts
      if (text.includes('filter flagged') || text.includes('show flagged') || text.includes('ಫ್ಲ್ಯಾಗ್')) {
        navigate('/claims')
        speak(language === 'kn' ? 'ಫ್ಲ್ಯಾಗ್ ಮಾಡಿದ ಕ್ಲೈಮ್‌ಗಳನ್ನು ತೋರಿಸಲಾಗುತ್ತಿದೆ.' : 'Showing flagged claims.')
        return
      }

      if (text.includes('price alert') || text.includes('price problem') || text.includes('cost anomaly') || text.includes('ಬೆಲೆ')) {
        if (activeClaim && (text.includes('why') || text.includes('problem') || text.includes('ಏನು'))) {
          await explainClaim('price_problem')
          return
        }
        navigate('/claims')
        speak(language === 'kn' ? 'ಬೆಲೆಯ ಎಚ್ಚರಿಕೆ ಕ್ಲೈಮ್‌ಗಳನ್ನು ತೋರಿಸಲಾಗುತ್ತಿದೆ.' : 'Showing claims with price alerts.')
        return
      }

      // 8. Document-Aware Queries: Why Flagged?
      if (
        text.includes('why flagged') ||
        text.includes('why was this flagged') ||
        text.includes('why is this flagged') ||
        text.includes('ಏಕೆ ಫ್ಲ್ಯಾಗ್')
      ) {
        await explainClaim('why_flagged')
        return
      }

      // 9. Document-Aware Queries: Explain Claim
      if (
        text.includes('explain this claim') ||
        text.includes('explain claim') ||
        text.includes('explain this') ||
        text.includes('ವಿವರಿಸಿ')
      ) {
        await explainClaim('explain')
        return
      }

      // 10. Read Result Aloud
      if (
        text.includes('read result') ||
        text.includes('read this result') ||
        text.includes('read aloud') ||
        text.includes('ಓದಿ') ||
        text.includes('ಹೇಳಿ')
      ) {
        readClaimAloud()
        return
      }

      // 11. Sign out
      if (text.includes('log out') || text.includes('sign out') || text.includes('ಲಾಗ್ ಔಟ್') || text.includes('ಸೈನ್ ಔಟ್')) {
        speak(language === 'kn' ? 'ಖಾತೆಯಿಂದ ಸೈನ್ ಔಟ್ ಮಾಡಲಾಗುತ್ತಿದೆ.' : 'Signing out of auditor session.')
        setTimeout(() => {
          logout()
          navigate('/')
        }, 1200)
        return
      }

      // 12. Help
      if (text.includes('help') || text.includes('commands') || text.includes('what can you do') || text.includes('ಸಹಾಯ')) {
        const helpText =
          language === 'kn'
            ? 'ನೀವು ಹೀಗೆ ಹೇಳಬಹುದು: ಮುಖಪುಟಕ್ಕೆ ಹೋಗಿ, ಕ್ಲೈಮ್‌ಗಳನ್ನು ತೋರಿಸಿ, ಪ್ರಾದೇಶಿಕ ನಂಬಿಕೆ, ಫಲಿತಾಂಶವನ್ನು ಓದಿ, ಅಥವಾ ಈ ಕ್ಲೈಮ್ ಅನ್ನು ವಿವರಿಸಿ.'
            : 'You can say: Go to home, Go to claims, Go to trust density, Read the result, Why was this flagged, or Explain this claim.'
        speak(helpText)
        return
      }

      // 13. General query fallback - try Ollama or provide helpful feedback
      setStatus('thinking')
      const generalPrompt = `The user asked: "${recognizedText}". Provide a concise 1-sentence answer about EvidenceBridge healthcare auditing.`
      const generalAnswer = await queryLocalOllama(generalPrompt)

      if (generalAnswer && language === 'en') {
        speak(generalAnswer)
      } else {
        const fallback =
          language === 'kn'
            ? `ಕ್ಷಮಿಸಿ, "${recognizedText}" ಅರ್ಥವಾಗಲಿಲ್ಲ. ಸಹಾಯಕ್ಕಾಗಿ "ಸಹಾಯ" ಎಂದು ಹೇಳಿ.`
            : `I heard "${recognizedText}". Try saying "Read the result", "Explain this claim", or "Help".`
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
