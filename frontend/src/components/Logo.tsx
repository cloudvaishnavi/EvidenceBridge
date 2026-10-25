import React from 'react'

interface LogoProps {
  size?: 'sm' | 'md' | 'lg' | 'xl' | number
  variant?: 'badge' | 'glyph' | 'white'
  showText?: boolean
  subtext?: string
  className?: string
}

export function EbMark({
  size = 36,
  variant = 'badge',
  className = '',
}: {
  size?: number
  variant?: 'badge' | 'glyph' | 'white'
  className?: string
}) {
  const isWhite = variant === 'white'

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={`select-none flex-shrink-0 ${className}`}
      aria-label="EvidenceBridge EB Logo"
    >
      <defs>
        {/* Background Gradient */}
        <linearGradient id="eb-bg-grad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#0B192C" />
          <stop offset="55%" stopColor="#005B96" />
          <stop offset="100%" stopColor="#0284C7" />
        </linearGradient>

        {/* Glow Accent */}
        <linearGradient id="eb-cyan-glow" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#38BDF8" />
          <stop offset="100%" stopColor="#06B6D4" />
        </linearGradient>

        {/* Shimmer Highlight */}
        <linearGradient id="eb-highlight" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="#FFFFFF" stopOpacity="0.28" />
          <stop offset="100%" stopColor="#FFFFFF" stopOpacity="0.02" />
        </linearGradient>

        {/* Subtle Drop Shadow */}
        <filter id="eb-shadow" x="-10%" y="-10%" width="125%" height="125%">
          <feDropShadow dx="0" dy="2" stdDeviation="2.5" floodColor="#001F3F" floodOpacity="0.35" />
        </filter>
      </defs>

      {/* Rounded Container Badge */}
      <rect
        x="2"
        y="2"
        width="44"
        height="44"
        rx="12"
        fill={isWhite ? '#FFFFFF' : 'url(#eb-bg-grad)'}
        filter="url(#eb-shadow)"
      />

      {/* Glossy Top Bevel Ring */}
      <rect
        x="2.5"
        y="2.5"
        width="43"
        height="43"
        rx="11.5"
        stroke="url(#eb-highlight)"
        strokeWidth="1.2"
        fill="none"
      />

      {/* Letter 'E' Path */}
      {/* Spine + 3 horizontal bars with clinical cross notch in middle */}
      <path
        d="M 12 14.5
           C 12 13.67 12.67 13 13.5 13
           L 21.5 13
           C 22.33 13 23 13.67 23 14.5
           C 23 15.33 22.33 16 21.5 16
           L 16.5 16
           L 16.5 22.25
           L 20.5 22.25
           C 21.33 22.25 22 22.92 22 23.75
           C 22 24.58 21.33 25.25 20.5 25.25
           L 16.5 25.25
           L 16.5 31.5
           L 21.5 31.5
           C 22.33 31.5 23 32.17 23 33
           C 23 33.83 22.33 34.5 21.5 34.5
           L 13.5 34.5
           C 12.67 34.5 12 33.83 12 33
           Z"
        fill={isWhite ? '#0369A1' : '#FFFFFF'}
      />

      {/* Letter 'B' Path */}
      {/* Precision geometric B with smooth dual loops and medical bridge */}
      <path
        fillRule="evenodd"
        clipRule="evenodd"
        d="M 25 14.5
           C 25 13.67 25.67 13 26.5 13
           L 31.2 13
           C 34.6 13 37 15.2 37 18.2
           C 37 20.5 35.5 22.3 33.3 22.9
           C 36 23.6 37.8 25.7 37.8 28.9
           C 37.8 32.3 34.9 34.5 31.2 34.5
           L 26.5 34.5
           C 25.67 34.5 25 33.83 25 33
           Z
           M 29.5 16.5
           L 29.5 22.2
           L 31 22.2
           C 32.7 22.2 33.8 21.2 33.8 19.3
           C 33.8 17.5 32.6 16.5 31 16.5
           Z
           M 29.5 25.3
           L 29.5 31
           L 31.2 31
           C 33 31 34.3 29.9 34.3 28.1
           C 34.3 26.4 33 25.3 31.2 25.3
           Z"
        fill={isWhite ? '#0369A1' : '#FFFFFF'}
      />

      {/* Central Medical Cross Accent Bridge between E and B */}
      <circle cx="24" cy="23.75" r="1.6" fill={isWhite ? '#0284C7' : 'url(#eb-cyan-glow)'} />
      <path
        d="M 23 23.75 L 25 23.75"
        stroke={isWhite ? '#0284C7' : '#38BDF8'}
        strokeWidth="1.2"
        strokeLinecap="round"
      />
    </svg>
  )
}

export default function Logo({
  size = 'md',
  variant = 'badge',
  showText = true,
  subtext = 'Clinical Evidence & Pricing Audit',
  className = '',
}: LogoProps) {
  const pixelSize =
    typeof size === 'number'
      ? size
      : size === 'sm'
      ? 28
      : size === 'md'
      ? 36
      : size === 'lg'
      ? 44
      : 52

  return (
    <div className={`flex items-center gap-2.5 ${className}`}>
      <EbMark size={pixelSize} variant={variant} />
      {showText && (
        <div className="leading-tight">
          <div className="font-extrabold text-slate-900 tracking-tight text-base sm:text-lg flex items-center gap-1.5">
            <span>Evidence</span>
            <span className="text-sky-600 font-black">Bridge</span>
          </div>
          {subtext && (
            <div className="text-[11px] text-slate-500 font-medium tracking-normal mt-0.5">
              {subtext}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
