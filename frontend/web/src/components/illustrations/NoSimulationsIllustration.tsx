export function NoSimulationsIllustration({ className = "w-32 h-24" }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 160 100"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      {/* Qubit wires */}
      <line x1="20" y1="25" x2="140" y2="25" stroke="var(--line)" strokeWidth="1.5" strokeDasharray="4 4" />
      <line x1="20" y1="50" x2="140" y2="50" stroke="var(--line)" strokeWidth="1.5" />
      <line x1="20" y1="75" x2="140" y2="75" stroke="var(--line)" strokeWidth="1.5" strokeDasharray="4 4" />

      {/* Wire labels */}
      <text x="10" y="28" fill="var(--ink-3)" fontSize="9" fontFamily="var(--font-mono)">q0</text>
      <text x="10" y="53" fill="var(--ink-3)" fontSize="9" fontFamily="var(--font-mono)">q1</text>
      <text x="10" y="78" fill="var(--ink-3)" fontSize="9" fontFamily="var(--font-mono)">q2</text>

      {/* Ghost Gate outlines */}
      <rect x="45" y="15" width="20" height="20" rx="4" stroke="var(--gate-h)" strokeWidth="1.5" strokeDasharray="2 2" fill="var(--bg-subtle)" fillOpacity="0.4" />
      <text x="52" y="29" fill="var(--gate-h)" fontSize="10" fontWeight="bold" fontFamily="var(--font-mono)">H</text>

      <rect x="75" y="40" width="20" height="20" rx="4" stroke="var(--gate-pauli)" strokeWidth="1.5" strokeDasharray="2 2" fill="var(--bg-subtle)" fillOpacity="0.4" />
      <text x="82" y="54" fill="var(--gate-pauli)" fontSize="10" fontWeight="bold" fontFamily="var(--font-mono)">X</text>

      {/* Entanglement connector */}
      <circle cx="115" cy="50" r="3" fill="var(--gate-multi)" />
      <line x1="115" y1="50" x2="115" y2="75" stroke="var(--gate-multi)" strokeWidth="1.5" strokeDasharray="2 2" />
      <circle cx="115" cy="75" r="5" stroke="var(--gate-multi)" strokeWidth="1.5" />
      <line x1="115" y1="70" x2="115" y2="80" stroke="var(--gate-multi)" strokeWidth="1.5" />
      <line x1="110" y1="75" x2="120" y2="75" stroke="var(--gate-multi)" strokeWidth="1.5" />
    </svg>
  );
}
