export function NoAttemptsIllustration({ className = "w-32 h-24" }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 160 100"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      {/* Outer Bloch Sphere Circle */}
      <circle cx="80" cy="50" r="38" stroke="var(--line)" strokeWidth="1.5" />
      
      {/* Equator Ellipse */}
      <ellipse cx="80" cy="50" rx="38" ry="12" stroke="var(--line-soft)" strokeWidth="1" strokeDasharray="3 3" />
      
      {/* Z-Axis */}
      <line x1="80" y1="8" x2="80" y2="92" stroke="var(--line-focus)" strokeWidth="1.2" strokeOpacity="0.6" />
      
      {/* Poles */}
      <circle cx="80" cy="12" r="2.5" fill="var(--accent)" />
      <circle cx="80" cy="88" r="2.5" fill="var(--accent)" />
      <text x="85" y="16" fill="var(--ink-2)" fontSize="9" fontFamily="var(--font-mono)">|0⟩</text>
      <text x="85" y="90" fill="var(--ink-2)" fontSize="9" fontFamily="var(--font-mono)">|1⟩</text>
      
      {/* State vector in superposition */}
      <line x1="80" y1="50" x2="105" y2="28" stroke="var(--gate-phase)" strokeWidth="1.8" />
      <circle cx="105" cy="28" r="3" fill="var(--gate-phase)" />
      <text x="110" y="27" fill="var(--gate-phase)" fontSize="9" fontFamily="var(--font-mono)">|ψ⟩</text>
    </svg>
  );
}
