import React from "react";
import { cn } from "../ui";

interface QuantumLogoProps {
  className?: string;
  size?: number | string;
  variant?: "badge" | "icon";
  animated?: boolean;
}

/**
 * Custom QuantumLearn Logo Component
 * Recreates the iconic dual-axis quantum orbital atom with central nucleus
 * in high-fidelity SVG with electric cyan/blue gradients and glow.
 */
export const QuantumLogoIcon: React.FC<{
  className?: string;
  size?: number | string;
  animated?: boolean;
}> = ({ className, size = 24, animated = true }) => {
  const s = typeof size === "number" ? `${size}px` : size;

  return (
    <svg
      width={s}
      height={s}
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={cn("shrink-0 select-none", className)}
      aria-hidden="true"
    >
      <defs>
        {/* Electric cyan-to-blue quantum gradient */}
        <linearGradient id="ql-quantum-grad" x1="4" y1="4" x2="44" y2="44" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#38bdf8" />
          <stop offset="50%" stopColor="#3b82f6" />
          <stop offset="100%" stopColor="#60a5fa" />
        </linearGradient>

        {/* Nucleus radiant core glow */}
        <radialGradient id="ql-core-grad" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#e0f2fe" />
          <stop offset="50%" stopColor="#38bdf8" />
          <stop offset="100%" stopColor="#2563eb" />
        </radialGradient>

        {/* Ambient glow filter */}
        <filter id="ql-glow" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="1.5" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      <g className={animated ? "animate-spin-slow origin-center" : undefined} style={{ transformOrigin: "24px 24px" }}>
        {/* Orbital Ellipse 1 (Rotated +45 deg) */}
        <ellipse
          cx="24"
          cy="24"
          rx="15"
          ry="6.5"
          transform="rotate(45 24 24)"
          stroke="url(#ql-quantum-grad)"
          strokeWidth="2.75"
          strokeLinecap="round"
          strokeLinejoin="round"
          filter="url(#ql-glow)"
        />

        {/* Orbital Ellipse 2 (Rotated -45 deg) */}
        <ellipse
          cx="24"
          cy="24"
          rx="15"
          ry="6.5"
          transform="rotate(-45 24 24)"
          stroke="url(#ql-quantum-grad)"
          strokeWidth="2.75"
          strokeLinecap="round"
          strokeLinejoin="round"
          filter="url(#ql-glow)"
        />

        {/* Orbital superposition nodal particles */}
        <circle cx="34.6" cy="13.4" r="1.4" fill="#38bdf8" opacity="0.9" />
        <circle cx="13.4" cy="34.6" r="1.4" fill="#38bdf8" opacity="0.9" />
        <circle cx="13.4" cy="13.4" r="1.4" fill="#60a5fa" opacity="0.9" />
        <circle cx="34.6" cy="34.6" r="1.4" fill="#60a5fa" opacity="0.9" />
      </g>

      {/* Central Quantum Nucleus / Core */}
      <circle
        cx="24"
        cy="24"
        r="3.4"
        fill="url(#ql-core-grad)"
        filter="url(#ql-glow)"
      />
    </svg>
  );
};

export const QuantumLogo: React.FC<QuantumLogoProps> = ({
  className,
  size,
  variant = "badge",
  animated = true,
}) => {
  if (variant === "icon") {
    return <QuantumLogoIcon className={className} size={size} animated={animated} />;
  }

  return (
    <div
      className={cn(
        "relative grid place-items-center rounded-xl bg-gradient-to-b from-[#0e1738] via-[#09102a] to-[#060a1c] border border-blue-500/40 shadow-[0_0_16px_-2px_rgba(59,130,246,0.45)] select-none overflow-hidden group",
        className
      )}
    >
      {/* Subtle ambient interior glow */}
      <div className="absolute inset-0 bg-radial-gradient from-blue-500/15 via-cyan-500/5 to-transparent pointer-events-none rounded-xl" />

      {/* Glossy top reflection */}
      <div className="absolute inset-x-0 top-0 h-[45%] bg-gradient-to-b from-white/10 to-transparent pointer-events-none rounded-t-xl" />

      <QuantumLogoIcon
        size={size || "70%"}
        animated={animated}
        className="relative z-10 drop-shadow-[0_0_8px_rgba(56,189,248,0.6)]"
      />
    </div>
  );
};
