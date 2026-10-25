import React, { useRef, useState, useEffect } from 'react'

interface CameraCaptureModalProps {
  isOpen: boolean
  onClose: () => void
  onCapture: (blob: Blob, dataUrl: string) => void
}

export default function CameraCaptureModal({
  isOpen,
  onClose,
  onCapture,
}: CameraCaptureModalProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null)
  const [stream, setStream] = useState<MediaStream | null>(null)
  const [cameraError, setCameraError] = useState<string | null>(null)
  const [facingMode, setFacingMode] = useState<'environment' | 'user'>('environment')
  const [availableDevices, setAvailableDevices] = useState<MediaDeviceInfo[]>([])
  const fallbackInputRef = useRef<HTMLInputElement | null>(null)

  // Start camera stream when modal opens or facingMode changes
  useEffect(() => {
    if (!isOpen) {
      if (stream) {
        stream.getTracks().forEach((track) => track.stop())
        setStream(null)
      }
      return
    }

    let isCancelled = false
    setCameraError(null)

    async function initCamera() {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        setCameraError('Camera access is not supported by your browser. You can use the photo file picker instead.')
        return
      }

      try {
        // Enumerate devices to check if multiple cameras are available
        try {
          const devices = await navigator.mediaDevices.enumerateDevices()
          const videoInputs = devices.filter((d) => d.kind === 'videoinput')
          if (!isCancelled) setAvailableDevices(videoInputs)
        } catch {
          // ignore enumeration error
        }

        // Stop any existing stream
        if (stream) {
          stream.getTracks().forEach((track) => track.stop())
        }

        const newStream = await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: { ideal: facingMode },
            width: { ideal: 1920 },
            height: { ideal: 1080 },
          },
          audio: false,
        })

        if (isCancelled) {
          newStream.getTracks().forEach((track) => track.stop())
          return
        }

        setStream(newStream)
        if (videoRef.current) {
          videoRef.current.srcObject = newStream
          videoRef.current.play().catch(() => {})
        }
      } catch (err: unknown) {
        if (isCancelled) return
        const msg = err instanceof Error ? err.message : 'Unable to access camera.'
        console.warn('Camera access denied or failed:', err)
        setCameraError(
          `Camera access could not be started (${msg}). Please allow camera permissions or upload an image file directly.`
        )
      }
    }

    initCamera()

    return () => {
      isCancelled = true
      if (stream) {
        stream.getTracks().forEach((track) => track.stop())
      }
    }
  }, [isOpen, facingMode])

  // Stop camera tracks on close
  const handleClose = () => {
    if (stream) {
      stream.getTracks().forEach((track) => track.stop())
      setStream(null)
    }
    onClose()
  }

  // Capture frame to canvas
  const handleCapture = () => {
    if (!videoRef.current) return
    const video = videoRef.current
    const canvas = document.createElement('canvas')
    const width = video.videoWidth || 1280
    const height = video.videoHeight || 720
    canvas.width = width
    canvas.height = height

    const ctx = canvas.getContext('2d')
    if (!ctx) return
    ctx.drawImage(video, 0, 0, width, height)

    canvas.toBlob(
      (blob) => {
        if (blob) {
          const dataUrl = canvas.toDataURL('image/jpeg', 0.92)
          handleClose()
          onCapture(blob, dataUrl)
        }
      },
      'image/jpeg',
      0.92
    )
  }

  // Toggle between front and back camera
  const toggleFacingMode = () => {
    setFacingMode((prev) => (prev === 'environment' ? 'user' : 'environment'))
  }

  // Handle fallback file capture (native mobile camera)
  const handleFallbackFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      const dataUrl = URL.createObjectURL(file)
      handleClose()
      onCapture(file, dataUrl)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/80 backdrop-blur-sm animate-fadeIn">
      <div className="relative w-full max-w-xl bg-white rounded-2xl shadow-2xl overflow-hidden border border-slate-200">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100 bg-slate-50/80">
          <div className="flex items-center gap-2">
            <span className="p-1.5 rounded-lg bg-sky-100 text-sky-700">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"
                />
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M15 13a3 3 0 11-6 0 3 3 0 016 0z"
                />
              </svg>
            </span>
            <div>
              <h3 className="font-bold text-slate-900 text-sm sm:text-base">Capture Bill or Prescription</h3>
              <p className="text-xs text-slate-500">Align document clearly within the frame</p>
            </div>
          </div>
          <button
            type="button"
            onClick={handleClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 transition-colors"
            title="Close camera"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Viewfinder or Error State */}
        <div className="relative bg-black min-h-[340px] flex items-center justify-center overflow-hidden">
          {cameraError ? (
            <div className="p-6 text-center max-w-md">
              <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-amber-500/20 text-amber-400 flex items-center justify-center text-xl">
                📷
              </div>
              <p className="text-sm text-slate-200 mb-4">{cameraError}</p>
              <div className="flex flex-col sm:flex-row gap-2 justify-center">
                <button
                  type="button"
                  onClick={() => fallbackInputRef.current?.click()}
                  className="px-4 py-2 bg-sky-600 text-white text-xs font-semibold rounded-lg hover:bg-sky-500 transition-colors"
                >
                  Choose or Take Photo with System Camera
                </button>
                <button
                  type="button"
                  onClick={handleClose}
                  className="px-4 py-2 bg-slate-800 text-slate-300 text-xs font-semibold rounded-lg hover:bg-slate-700 transition-colors"
                >
                  Cancel
                </button>
              </div>
              {/* Native fallback file input */}
              <input
                ref={fallbackInputRef}
                type="file"
                accept="image/*"
                capture="environment"
                className="hidden"
                onChange={handleFallbackFileChange}
              />
            </div>
          ) : (
            <>
              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                className="w-full h-full object-cover max-h-[460px]"
              />

              {/* Document Alignment Frame */}
              <div className="absolute inset-8 border-2 border-dashed border-sky-400/80 rounded-xl pointer-events-none flex flex-col justify-between p-3">
                <div className="flex justify-between">
                  <div className="w-4 h-4 border-t-2 border-l-2 border-sky-300"></div>
                  <div className="w-4 h-4 border-t-2 border-r-2 border-sky-300"></div>
                </div>
                <div className="text-center">
                  <span className="inline-block px-3 py-1 bg-black/60 backdrop-blur-sm text-white/90 text-[11px] rounded-full font-medium tracking-wide">
                    Position hospital bill or prescription flat &amp; well-lit
                  </span>
                </div>
                <div className="flex justify-between">
                  <div className="w-4 h-4 border-b-2 border-l-2 border-sky-300"></div>
                  <div className="w-4 h-4 border-b-2 border-r-2 border-sky-300"></div>
                </div>
              </div>

              {/* Flip camera button if multiple cameras detected */}
              {availableDevices.length > 1 && (
                <button
                  type="button"
                  onClick={toggleFacingMode}
                  className="absolute top-4 right-4 p-2 bg-black/60 text-white rounded-full hover:bg-black/80 transition-colors shadow-md text-xs flex items-center gap-1.5"
                  title="Switch camera"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth="2"
                      d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                    />
                  </svg>
                  <span>Flip</span>
                </button>
              )}
            </>
          )}
        </div>

        {/* Footer Controls */}
        {!cameraError && (
          <div className="flex items-center justify-between px-6 py-4 bg-slate-50 border-t border-slate-100">
            <button
              type="button"
              onClick={handleClose}
              className="text-xs sm:text-sm font-semibold text-slate-500 hover:text-slate-800 px-3 py-2 rounded-lg hover:bg-slate-200/50 transition-colors"
            >
              Cancel
            </button>

            <button
              type="button"
              onClick={handleCapture}
              className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl bg-sky-600 hover:bg-sky-700 text-white font-bold text-sm shadow-md transition-all active:scale-95"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="2" />
                <circle cx="12" cy="12" r="4" fill="currentColor" />
              </svg>
              Capture Photo
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
