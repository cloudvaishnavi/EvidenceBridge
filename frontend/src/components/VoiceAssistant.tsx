import React from 'react'
import { useNavigate } from 'react-router-dom'
import { useVoice } from '../context/VoiceContext'
import { useAuth } from '../context/AuthContext'

export function VoiceAssistant() {
  const { isAuthenticated } = useAuth()
  const navigate = useNavigate()
  const {
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
    startListening,
    stopListening,
    speak,
    stopSpeaking,
    readClaimAloud,
    explainClaim,
    clearHistory,
  } = useVoice()

  // Do not render on public landing page or when unauthenticated
  if (!isAuthenticated || !isEnabled) {
    return null
  }

  const toggleListen = () => {
    if (status === 'listening') {
      stopListening()
    } else {
      startListening(true)
    }
  }

  return (
    <>
      {/* Floating Microphone Action Button */}
      {!isOpen && (
        <div className="fixed bottom-6 right-6 z-40 flex items-center gap-2">
          {/* Status Label Tooltip */}
          {status === 'speaking' && (
            <button
              type="button"
              onClick={stopSpeaking}
              className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-slate-900 text-white text-xs font-bold shadow-elevated border border-slate-700 animate-in fade-in"
            >
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span>Speaking &bull; Click to Stop</span>
            </button>
          )}

          {status === 'listening' && (
            <button
              type="button"
              onClick={stopListening}
              className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-rose-600 text-white text-xs font-bold shadow-elevated animate-pulse hover:bg-rose-700"
              title="Click to pause listening"
            >
              <span className="w-2 h-2 rounded-full bg-white" />
              <span>Listening (Active) &bull; Pause</span>
            </button>
          )}

          {status === 'idle' && isContinuous && (
            <div className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-emerald-800 text-white text-xs font-semibold shadow-sm">
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
              <span>Voice Ready</span>
            </div>
          )}

          <button
            type="button"
            onClick={() => setIsOpen(true)}
            className={`relative p-3.5 rounded-2xl shadow-elevated transition-all transform hover:scale-105 active:scale-95 flex items-center justify-center ${
              status === 'listening'
                ? 'bg-rose-600 text-white ring-4 ring-rose-400/40 animate-pulse'
                : status === 'speaking'
                ? 'bg-clinical-600 text-white ring-4 ring-clinical-400/40'
                : 'bg-navy-900 text-white hover:bg-navy-800'
            }`}
            title="EvidenceBridge AI Voice Assistant (English / ಕನ್ನಡ)"
            aria-label="Open Voice Assistant"
          >
            {/* Mic Icon */}
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
              />
            </svg>

            {/* Language Tag */}
            <span className="absolute -top-1.5 -right-1.5 px-1.5 py-0.5 rounded-full text-[9px] font-black bg-sky-500 text-white shadow-xs">
              {language === 'kn' ? 'ಕನ್ನಡ' : 'EN'}
            </span>
          </button>
        </div>
      )}

      {/* Floating Voice Assistant Panel */}
      {isOpen && (
        <div className="fixed bottom-6 right-6 z-50 w-full sm:w-[400px] max-w-[calc(100vw-2rem)] bg-white rounded-2xl shadow-2xl border border-slate-200 overflow-hidden flex flex-col max-h-[82vh] animate-in fade-in zoom-in-95 duration-200 font-sans">
          {/* Header */}
          <div className="bg-navy-900 text-white p-4 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-sky-600 to-teal-500 flex items-center justify-center text-white text-base shadow-sm">
                🎙️
              </div>
              <div>
                <h3 className="text-xs font-bold text-white tracking-tight leading-none">
                  Clinical AI Voice Assistant
                </h3>
                <span className="text-[10px] text-slate-300 font-medium mt-0.5 block">
                  Bilingual navigation &amp; claim Q&amp;A
                </span>
              </div>
            </div>

            <div className="flex items-center gap-1.5">
              {/* Language Switcher */}
              <div className="bg-navy-950 p-0.5 rounded-lg flex items-center text-[10px] font-bold border border-navy-800">
                <button
                  type="button"
                  onClick={() => setLanguage('en')}
                  className={`px-2 py-0.5 rounded-md transition-colors ${
                    language === 'en' ? 'bg-sky-600 text-white' : 'text-slate-400 hover:text-white'
                  }`}
                >
                  EN
                </button>
                <button
                  type="button"
                  onClick={() => setLanguage('kn')}
                  className={`px-2 py-0.5 rounded-md transition-colors ${
                    language === 'kn' ? 'bg-sky-600 text-white' : 'text-slate-400 hover:text-white'
                  }`}
                >
                  ಕನ್ನಡ
                </button>
              </div>

              {/* Close Button */}
              <button
                type="button"
                onClick={() => {
                  stopSpeaking()
                  stopListening()
                  setIsOpen(false)
                }}
                className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-navy-800 transition-colors"
                aria-label="Close"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>

          {/* Kannada Notice Banner */}
          {language === 'kn' && (
            <div
              className={`px-3.5 py-2 text-xs border-b flex flex-col gap-0.5 ${
                kannadaVoiceAvailable
                  ? 'bg-emerald-50 text-emerald-900 border-emerald-200'
                  : 'bg-amber-50 text-amber-900 border-amber-200'
              }`}
            >
              <div className="flex items-center gap-1.5 font-bold">
                <span>{kannadaVoiceAvailable ? '🔊' : 'ℹ️'}</span>
                <span>
                  {kannadaVoiceAvailable
                    ? 'ಕನ್ನಡ ಧ್ವನಿ ಸಕ್ರಿಯವಾಗಿದೆ (ಬ್ರೌಸರ್ ಎಂಜಿನ್)'
                    : 'ಕನ್ನಡ ಸ್ಪೀಚ್ ಸಿಂಥೆಸಿಸ್ (ಆಡಿಯೋ ಫಾಲ್‌ಬ್ಯಾಕ್ ಸಕ್ರಿಯ)'}
                </span>
              </div>
              <p className="text-[11px] leading-tight opacity-90">
                {kannadaVoiceAvailable
                  ? 'ಕನ್ನಡದಲ್ಲಿ ಮಾತನಾಡಿ ಪ್ರಶ್ನೆ ಕೇಳಬಹುದು ಅಥವಾ ಫಲಿತಾಂಶಗಳನ್ನು ಆಲಿಸಬಹುದು.'
                  : 'ಆಡಿಯೋ ಕೇಳಲು "Repeat" (🔊) ಕ್ಲಿಕ್ ಮಾಡಿ. ಫಲಿತಾಂಶ ಪಠ್ಯ ರೂಪದಲ್ಲೂ ಲಭ್ಯವಿದೆ.'}
              </p>
            </div>
          )}

          {/* Body Content */}
          <div className="p-4 space-y-3 overflow-y-auto flex-1">
            {/* Active Document Card (if claim loaded on screen) */}
            {activeClaim ? (
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                    Active Document Context
                  </span>
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      activeClaim.action === 'accept'
                        ? 'bg-emerald-100 text-emerald-800'
                        : activeClaim.action === 'flag'
                        ? 'bg-amber-100 text-amber-800'
                        : 'bg-slate-200 text-slate-700'
                    }`}
                  >
                    {activeClaim.action.toUpperCase()}
                  </span>
                </div>
                <div className="font-bold text-xs text-slate-800 line-clamp-1">
                  {activeClaim.entity || activeClaim.claimId}
                </div>
                {activeClaim.costAnomalyFlag && (
                  <div className="text-[11px] text-rose-700 font-semibold mt-0.5 flex items-center gap-1">
                    <span>⚠️</span> Price alert ({activeClaim.anomalyDetails?.multiplier?.toFixed(1) || '3.0'}× markup)
                  </div>
                )}
              </div>
            ) : (
              <div className="p-2.5 rounded-xl bg-sky-50/50 border border-sky-100 text-[11px] text-slate-600">
                💡 Open any claim on screen to ask guideline or pricing questions.
              </div>
            )}

            {/* Live Audio / Status Indicator */}
            <div
              className={`p-3 rounded-xl border flex flex-col items-center justify-center text-center transition-all ${
                status === 'listening'
                  ? 'bg-rose-50 border-rose-200 text-rose-900'
                  : status === 'speaking'
                  ? 'bg-clinical-50 border-clinical-200 text-clinical-900'
                  : status === 'thinking'
                  ? 'bg-amber-50 border-amber-200 text-amber-900'
                  : 'bg-slate-50 border-slate-200 text-slate-700'
              }`}
            >
              <div className="flex items-center gap-2 mb-1">
                <span
                  className={`w-2.5 h-2.5 rounded-full ${
                    status === 'listening'
                      ? 'bg-rose-500 animate-ping'
                      : status === 'speaking'
                      ? 'bg-clinical-500 animate-pulse'
                      : status === 'thinking'
                      ? 'bg-amber-500 animate-spin'
                      : 'bg-slate-400'
                  }`}
                />
                <span className="text-xs font-bold uppercase tracking-wider">
                  {status === 'listening'
                    ? language === 'kn'
                      ? 'ಆಲಿಸಲಾಗುತ್ತಿದೆ (Listening)...'
                      : 'Listening (Active)...'
                    : status === 'speaking'
                    ? language === 'kn'
                      ? 'ಮಾತನಾಡಲಾಗುತ್ತಿದೆ...'
                      : 'Speaking answer...'
                    : status === 'thinking'
                    ? language === 'kn'
                      ? 'ವಿಶ್ಲೇಷಿಸಲಾಗುತ್ತಿದೆ...'
                      : 'Analyzing with local AI...'
                    : language === 'kn'
                    ? 'ಸಿದ್ಧವಾಗಿದೆ (Ready)'
                    : 'Ready to listen'}
                </span>
              </div>

              {/* Live Transcript / Feedback */}
              {transcript ? (
                <p className="text-xs font-medium text-slate-900 bg-white/80 px-3 py-1.5 rounded-lg border border-slate-200 w-full mt-1">
                  &ldquo;{transcript}&rdquo;
                </p>
              ) : status === 'listening' ? (
                <p className="text-[11px] text-slate-500">
                  {language === 'kn'
                    ? 'ಈಗ ಮಾತನಾಡಿ ("ಆಸ್ಪತ್ರೆ ಹುಡುಕಿ", "ಫಲಿತಾಂಶ ಓದಿ", "ನಿಲ್ಲಿಸು")'
                    : 'Speak now (e.g. "Find hospitals", "Why was this flagged?", "Stop listening")'}
                </p>
              ) : null}

              {/* Action Buttons for Speaking / Listening */}
              <div className="flex items-center gap-2 mt-2">
                {status === 'speaking' && (
                  <button
                    type="button"
                    onClick={stopSpeaking}
                    className="px-3 py-1 rounded-lg bg-rose-600 hover:bg-rose-700 text-white text-[11px] font-bold transition-colors"
                  >
                    ⏹ Stop Speaking
                  </button>
                )}
                {status === 'listening' && (
                  <button
                    type="button"
                    onClick={stopListening}
                    className="px-3 py-1 rounded-lg bg-slate-800 hover:bg-slate-900 text-white text-[11px] font-bold transition-colors"
                  >
                    ⏸ Pause Listening
                  </button>
                )}
              </div>
            </div>

            {/* Error Message */}
            {error && (
              <div className="p-2.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs">
                <strong>Notice:</strong> {error}
              </div>
            )}

            {/* Latest Assistant Spoken Text Card */}
            {lastSpoken && status !== 'listening' && (
              <div className="p-3 rounded-xl bg-slate-900 text-white text-xs space-y-1.5">
                <div className="flex items-center justify-between text-[10px] text-slate-400 uppercase font-bold tracking-wider">
                  <span>Assistant Answer</span>
                  <button
                    type="button"
                    onClick={() => speak(lastSpoken)}
                    className="text-sky-400 hover:text-sky-300 font-bold"
                  >
                    🔊 Repeat
                  </button>
                </div>
                <p className="text-slate-100 leading-relaxed text-xs">{lastSpoken}</p>
              </div>
            )}

            {/* Quick Actions & Navigation */}
            <div>
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1.5">
                Quick Actions
              </span>
              <div className="grid grid-cols-2 gap-1.5">
                <button
                  type="button"
                  onClick={() => {
                    navigate('/hospitals')
                    setIsOpen(false)
                  }}
                  className="p-2 rounded-lg bg-emerald-50 hover:bg-emerald-100 text-emerald-900 border border-emerald-200 text-xs font-semibold text-left transition-colors flex items-center gap-1.5"
                >
                  <span>🏥</span>
                  <span className="truncate">{language === 'kn' ? 'ಆಸ್ಪತ್ರೆ ಹುಡುಕಿ' : 'Find Hospitals'}</span>
                </button>

                <button
                  type="button"
                  onClick={() => readClaimAloud()}
                  className="p-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-semibold text-left transition-colors flex items-center gap-1.5"
                >
                  <span>🔊</span>
                  <span className="truncate">{language === 'kn' ? 'ಫಲಿತಾಂಶ ಓದಿ' : 'Read Result'}</span>
                </button>

                <button
                  type="button"
                  onClick={() => explainClaim('why_flagged')}
                  className="p-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-semibold text-left transition-colors flex items-center gap-1.5"
                >
                  <span>❓</span>
                  <span className="truncate">{language === 'kn' ? 'ಏಕೆ ಫ್ಲ್ಯಾಗ್?' : 'Why Flagged?'}</span>
                </button>

                <button
                  type="button"
                  onClick={() => explainClaim('price_problem')}
                  className="p-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-semibold text-left transition-colors flex items-center gap-1.5"
                >
                  <span>💰</span>
                  <span className="truncate">{language === 'kn' ? 'ಬೆಲೆಯ ಸಮಸ್ಯೆ?' : 'Price Problem?'}</span>
                </button>
              </div>
            </div>

            {/* Continuous Mode Setting */}
            <div className="flex items-center justify-between p-2.5 rounded-xl bg-slate-50 border border-slate-200 text-xs">
              <span className="text-slate-600 font-medium">Keep listening after answers</span>
              <button
                type="button"
                onClick={() => setIsContinuous(!isContinuous)}
                className={`px-2.5 py-1 rounded-md text-[11px] font-bold transition-colors ${
                  isContinuous ? 'bg-emerald-600 text-white' : 'bg-slate-200 text-slate-700'
                }`}
              >
                {isContinuous ? 'ON' : 'OFF'}
              </button>
            </div>

            {/* History Accordion */}
            {history.length > 0 && (
              <details className="text-xs pt-1 border-t border-slate-100">
                <summary className="cursor-pointer text-[11px] text-slate-500 font-semibold hover:text-slate-800 py-1 flex items-center justify-between">
                  <span>Voice History ({history.length})</span>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.preventDefault()
                      clearHistory()
                    }}
                    className="text-[10px] text-slate-400 hover:text-rose-600 font-normal"
                  >
                    Clear
                  </button>
                </summary>
                <div className="space-y-1.5 mt-2 max-h-32 overflow-y-auto pr-1">
                  {history.map((msg) => (
                    <div
                      key={msg.id}
                      className={`p-2 rounded-lg text-[11px] ${
                        msg.sender === 'user'
                          ? 'bg-sky-50 text-sky-950 font-medium'
                          : 'bg-slate-100 text-slate-800'
                      }`}
                    >
                      <strong className="block text-[9px] uppercase tracking-wider text-slate-400 mb-0.5">
                        {msg.sender === 'user' ? 'You' : 'Voice Assistant'}
                      </strong>
                      {msg.text}
                    </div>
                  ))}
                </div>
              </details>
            )}
          </div>

          {/* Footer Controls */}
          <div className="p-3 bg-slate-50 border-t border-slate-200 flex items-center justify-between gap-2">
            <button
              type="button"
              onClick={toggleListen}
              className={`flex-1 py-2 px-3 rounded-xl text-xs font-bold shadow-sm transition-all flex items-center justify-center gap-1.5 ${
                status === 'listening'
                  ? 'bg-rose-600 hover:bg-rose-700 text-white animate-pulse'
                  : 'bg-sky-600 hover:bg-sky-700 text-white'
              }`}
            >
              <span>{status === 'listening' ? '⏹ Stop Listening' : '🎙️ Tap to Speak'}</span>
            </button>

            <button
              type="button"
              onClick={() => {
                stopListening()
                setIsEnabled(false)
              }}
              className="px-2.5 py-2 rounded-xl text-[10px] text-slate-400 hover:text-rose-600 font-medium"
              title="Disable voice assistant"
            >
              Disable
            </button>
          </div>
        </div>
      )}
    </>
  )
}
export default VoiceAssistant
