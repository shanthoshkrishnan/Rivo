import React from 'react';

export interface RivoLogoProps {
  variant?: 'full' | 'compact' | 'icon';
  theme?: 'light' | 'dark';
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export const RivoLogo: React.FC<RivoLogoProps> = ({
  variant = 'full',
  theme = 'light',
  size = 'md',
  className = '',
}) => {
  const isDark = theme === 'dark';

  // Sizing definitions for icon mark
  const iconDim = size === 'sm' ? 30 : size === 'lg' ? 44 : 36;

  // Sizing definitions for typography
  const titleSize = size === 'sm' ? 'text-lg' : size === 'lg' ? 'text-2xl' : 'text-xl';
  const subSize = size === 'sm' ? 'text-[9px]' : size === 'lg' ? 'text-[11px]' : 'text-[10px]';

  return (
    <div className={`inline-flex items-center space-x-3 select-none ${className}`}>
      {/* 1. Geometric SVG Vector Mark: Location Pin + Home Gable + Modern R + Yellow Accent */}
      <svg
        width={iconDim}
        height={iconDim}
        viewBox="0 0 36 36"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="shrink-0 transition-transform duration-200 hover:scale-105"
        aria-label="RIVO Brand Mark"
      >
        <defs>
          <linearGradient id="rivoBgGrad" x1="0" y1="0" x2="36" y2="36" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#06243A" />
            <stop offset="100%" stopColor="#0B1F3A" />
          </linearGradient>
          <linearGradient id="rivoRGrad" x1="10" y1="8" x2="26" y2="28" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#FFFFFF" />
            <stop offset="100%" stopColor="#E2F1FD" />
          </linearGradient>
          <linearGradient id="rivoBlueGrad" x1="8" y1="26" x2="28" y2="26" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#0878D1" />
            <stop offset="100%" stopColor="#13A8E8" />
          </linearGradient>
        </defs>

        {/* Base rounded square container */}
        <rect
          width="36"
          height="36"
          rx="10"
          fill="url(#rivoBgGrad)"
          stroke={isDark ? 'rgba(255,255,255,0.15)' : 'rgba(8, 120, 209, 0.25)'}
          strokeWidth="1.2"
        />

        {/* Mobility path line at base */}
        <path
          d="M 8 28.5 C 13 28.5, 17 26, 28 26"
          stroke="url(#rivoBlueGrad)"
          strokeWidth="2.2"
          strokeLinecap="round"
          opacity="0.8"
        />

        {/* Stylized Modern "R" intersecting location-pin geometry & housing roof */}
        {/* Left vertical pillar */}
        <path
          d="M 11.5 8.5 L 11.5 27.5"
          stroke="url(#rivoRGrad)"
          strokeWidth="3.2"
          strokeLinecap="round"
        />

        {/* Pin Loop / Roof Gable of R */}
        <path
          d="M 11.5 9.5 H 18.2 C 22.2 9.5, 24.2 12.2, 24.2 15.2 C 24.2 18.2, 22.2 20.2, 18.2 20.2 H 11.5"
          stroke="url(#rivoRGrad)"
          strokeWidth="3.2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* Dynamic diagonal kick of R pointing toward destination */}
        <path
          d="M 17.5 19.5 L 24.8 27.5"
          stroke="#13A8E8"
          strokeWidth="3.2"
          strokeLinecap="round"
        />

        {/* Signature Sustain-a-thon Hackathon Yellow Accent Pinpoint */}
        <circle
          cx="27.5"
          cy="8.5"
          r="3"
          fill="#F5C542"
          stroke="#06243A"
          strokeWidth="1.2"
        />
      </svg>

      {/* 2. Brand Typography (Variants: Full & Compact) */}
      {variant !== 'icon' && (
        <div className="flex flex-col justify-center leading-none">
          <div className="flex items-center space-x-2">
            <span
              className={`${titleSize} font-extrabold tracking-tight ${
                isDark ? 'text-white' : 'text-[#06243A]'
              }`}
            >
              RIVO
            </span>
            <span
              className="text-[9px] font-bold px-1.5 py-0.5 rounded-md bg-[#13A8E8]/10 text-[#0878D1] border border-[#13A8E8]/20 tracking-wider uppercase"
            >
              Chennai
            </span>
          </div>

          {variant === 'full' && (
            <span
              className={`${subSize} font-medium mt-1 tracking-tight ${
                isDark ? 'text-slate-300' : 'text-[#607080]'
              }`}
            >
              Worker Housing &amp; Mobility Intelligence
            </span>
          )}
        </div>
      )}
    </div>
  );
};
