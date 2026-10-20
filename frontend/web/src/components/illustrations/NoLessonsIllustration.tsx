export function NoLessonsIllustration({ className = "w-32 h-24" }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 160 100"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      {/* Open Book Outline */}
      <path
        d="M80 75C70 70 45 70 25 74V32C45 28 70 28 80 34C90 28 115 28 135 32V74C115 70 90 70 80 75Z"
        stroke="var(--line)"
        strokeWidth="1.5"
        fill="var(--bg-subtle)"
        fillOpacity="0.3"
      />
      <line x1="80" y1="34" x2="80" y2="75" stroke="var(--line)" strokeWidth="1.5" />

      {/* Pages lines left */}
      <line x1="35" y1="42" x2="70" y2="42" stroke="var(--line-soft)" strokeWidth="1.2" />
      <line x1="35" y1="50" x2="65" y2="50" stroke="var(--line-soft)" strokeWidth="1.2" />
      <line x1="35" y1="58" x2="55" y2="58" stroke="var(--line-soft)" strokeWidth="1.2" />

      {/* Quantum superposition wave right */}
      <path
        d="M90 52C95 40 105 40 110 52C115 64 125 64 130 52"
        stroke="var(--gate-h)"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
      
      {/* Glowing state glyph */}
      <circle cx="110" cy="52" r="2.5" fill="var(--accent)" />
      <text x="96" y="38" fill="var(--accent-ink)" fontSize="10" fontFamily="var(--font-mono)">|0⟩+|1⟩</text>
    </svg>
  );
}
