import React, { useState } from "react";
import {
  BookOpen,
  ChevronDown,
  ChevronUp,
  Atom,
  Binary,
  Layers,
  HardDrive,
} from "lucide-react";
import { Badge } from "../ui";

export const QuditLearnPanel: React.FC = () => {
  const [openSection, setOpenSection] = useState<string | null>("what-is-qudit");

  const toggle = (id: string) => {
    setOpenSection((prev) => (prev === id ? null : id));
  };

  return (
    <div className="rounded-xl border border-line bg-card/60 backdrop-blur-md p-4 shadow-sm space-y-3">
      <div className="flex items-center gap-2 border-b border-line/60 pb-3">
        <BookOpen className="h-4 w-4 text-accent" />
        <h2 className="text-sm font-semibold tracking-wide text-ink">
          Interactive Qudit Foundations & Mathematics
        </h2>
        <Badge tone="neutral">
          Guide
        </Badge>
      </div>

      <div className="space-y-2">
        {/* Section 1 */}
        <div className="rounded-lg border border-line/80 bg-subtle/30 overflow-hidden">
          <button
            type="button"
            onClick={() => toggle("what-is-qudit")}
            className="w-full flex items-center justify-between p-3 text-left text-xs font-semibold text-ink hover:text-accent transition-colors"
          >
            <div className="flex items-center gap-2">
              <Atom className="h-4 w-4 text-accent" />
              <span>1. What is a Qudit? (Dimension d ≥ 2)</span>
            </div>
            {openSection === "what-is-qudit" ? (
              <ChevronUp className="h-4 w-4 text-ink-3" />
            ) : (
              <ChevronDown className="h-4 w-4 text-ink-3" />
            )}
          </button>
          {openSection === "what-is-qudit" && (
            <div className="p-3 pt-0 text-xs text-ink-2 space-y-2 border-t border-line/40">
              <p>
                A <b>qudit</b> is a d-level quantum system existing in a d-dimensional complex Hilbert space ℂ^d. While standard quantum computers operate on 2-level <b>qubits</b> (|0⟩, |1⟩), physical quantum architectures (such as superconducting transmons, trapped ions, and photonic modes) naturally possess higher discrete energy levels:
              </p>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 font-mono text-[11px] my-2">
                <div className="p-2 rounded bg-bg border border-line">
                  <span className="text-accent font-bold">d = 2: Qubit</span>
                  <div className="text-ink-3">|0⟩, |1⟩</div>
                </div>
                <div className="p-2 rounded bg-bg border border-line">
                  <span className="text-accent font-bold">d = 3: Qutrit</span>
                  <div className="text-ink-3">|0⟩, |1⟩, |2⟩</div>
                </div>
                <div className="p-2 rounded bg-bg border border-line">
                  <span className="text-accent font-bold">d = 4: Ququart</span>
                  <div className="text-ink-3">|0⟩, |1⟩, |2⟩, |3⟩</div>
                </div>
                <div className="p-2 rounded bg-bg border border-line">
                  <span className="text-accent font-bold">d = 5: 5-Qudit</span>
                  <div className="text-ink-3">|0⟩ .. |4⟩</div>
                </div>
              </div>
              <p>
                A circuit containing <b>n</b> qudits of dimension <b>d</b> spans a total Hilbert space of dimension <b>D = d^n</b>. This exponential growth allows compact algorithmic information storage with fewer physical wires.
              </p>
            </div>
          )}
        </div>

        {/* Section 2 */}
        <div className="rounded-lg border border-line/80 bg-subtle/30 overflow-hidden">
          <button
            type="button"
            onClick={() => toggle("generalized-gates")}
            className="w-full flex items-center justify-between p-3 text-left text-xs font-semibold text-ink hover:text-accent transition-colors"
          >
            <div className="flex items-center gap-2">
              <Binary className="h-4 w-4 text-accent" />
              <span>2. Generalized Qudit Gates: Shift, Phase & Fourier</span>
            </div>
            {openSection === "generalized-gates" ? (
              <ChevronUp className="h-4 w-4 text-ink-3" />
            ) : (
              <ChevronDown className="h-4 w-4 text-ink-3" />
            )}
          </button>
          {openSection === "generalized-gates" && (
            <div className="p-3 pt-0 text-xs text-ink-2 space-y-2 border-t border-line/40">
              <p>
                In higher dimensions, single-qubit Pauli matrices generalize to dimension-d unitary operators:
              </p>
              <ul className="list-disc list-inside space-y-1.5 pl-1 font-mono text-[11px]">
                <li>
                  <b className="text-accent">Generalized Shift X_d:</b> X_d |j⟩ = |(j+1) mod d⟩. Satisfies (X_d)^d = I.
                </li>
                <li>
                  <b className="text-accent">Generalized Phase Z_d:</b> Z_d |j⟩ = ω^j |j⟩ where ω = exp(2πi / d). Satisfies (Z_d)^d = I.
                </li>
                <li>
                  <b className="text-accent">Generalized Fourier F_d:</b> F_d |j⟩ = (1/√d) ∑_(k=0)^(d-1) ω^(j·k) |k⟩. This creates a uniform equal superposition across all d levels (generalizing the Hadamard gate for qubits, where F_2 = H).
                </li>
                <li>
                  <b className="text-accent">Controlled-Addition SUM_d:</b> SUM_d |a, b⟩ = |a, (a+b) mod d⟩. Generalizes CNOT to modular arithmetic.
                </li>
              </ul>
            </div>
          )}
        </div>

        {/* Section 3 */}
        <div className="rounded-lg border border-line/80 bg-subtle/30 overflow-hidden">
          <button
            type="button"
            onClick={() => toggle("density-matrix")}
            className="w-full flex items-center justify-between p-3 text-left text-xs font-semibold text-ink hover:text-accent transition-colors"
          >
            <div className="flex items-center gap-2">
              <Layers className="h-4 w-4 text-accent" />
              <span>3. Density Matrices & Quantum Mixed States</span>
            </div>
            {openSection === "density-matrix" ? (
              <ChevronUp className="h-4 w-4 text-ink-3" />
            ) : (
              <ChevronDown className="h-4 w-4 text-ink-3" />
            )}
          </button>
          {openSection === "density-matrix" && (
            <div className="p-3 pt-0 text-xs text-ink-2 space-y-2 border-t border-line/40">
              <p>
                Unlike state vectors |ψ⟩ which only describe pure, isolated quantum states, a <b>density matrix ρ ∈ ℂ^(D×D)</b> can represent statistical mixtures and open quantum systems subjected to decoherence:
              </p>
              <div className="p-2 rounded bg-bg border border-line font-mono text-[11px] text-center">
                ρ = ∑_i p_i |ψ_i⟩⟨ψ_i|, with ∑_i p_i = 1 and p_i ≥ 0
              </div>
              <p>
                <b>Key Physical Diagnostics:</b>
              </p>
              <ul className="list-disc list-inside space-y-1 pl-1 text-[11px]">
                <li><b>Unit Trace:</b> Tr(ρ) = 1 (total probability sums to 1).</li>
                <li><b>Hermiticity:</b> ρ = ρ† (real observables).</li>
                <li><b>Positivity:</b> All eigenvalues λ_i ≥ 0.</li>
                <li><b>Purity γ = Tr(ρ²):</b> For a pure state, γ = 1. For a mixed state, 1/D ≤ γ &lt; 1. For a maximally mixed state, γ = 1/D.</li>
                <li><b>Von Neumann Entropy:</b> S(ρ) = -Tr(ρ log₂ ρ) = -∑ λ_i log₂ λ_i (measures quantum mixedness and lack of information).</li>
              </ul>
            </div>
          )}
        </div>

        {/* Section 4 */}
        <div className="rounded-lg border border-line/80 bg-subtle/30 overflow-hidden">
          <button
            type="button"
            onClick={() => toggle("resource-scaling")}
            className="w-full flex items-center justify-between p-3 text-left text-xs font-semibold text-ink hover:text-accent transition-colors"
          >
            <div className="flex items-center gap-2">
              <HardDrive className="h-4 w-4 text-accent" />
              <span>4. Memory Scaling & Safety Resource Policies</span>
            </div>
            {openSection === "resource-scaling" ? (
              <ChevronUp className="h-4 w-4 text-ink-3" />
            ) : (
              <ChevronDown className="h-4 w-4 text-ink-3" />
            )}
          </button>
          {openSection === "resource-scaling" && (
            <div className="p-3 pt-0 text-xs text-ink-2 space-y-2 border-t border-line/40">
              <p>
                Simulating a full density matrix throughout circuit execution requires storing D × D complex numbers in <b>complex128</b> (16 bytes per entry):
              </p>
              <div className="p-2 rounded bg-bg border border-line font-mono text-[11px] text-center text-accent">
                M_ρ = 16 · D² = 16 · d^(2n) bytes
              </div>
              <p>
                Notice how rapidly memory scales as both dimension <b>d</b> and qudit count <b>n</b> increase:
              </p>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 font-mono text-[10px]">
                <div className="p-1.5 rounded bg-bg border border-line">
                  <b>d = 2 (10 qubits):</b>
                  <div>D = 1024, ρ = 16 MiB</div>
                </div>
                <div className="p-1.5 rounded bg-bg border border-line">
                  <b>d = 3 (6 qutrits):</b>
                  <div>D = 729, ρ = 8.1 MiB</div>
                </div>
                <div className="p-1.5 rounded bg-bg border border-line">
                  <b>d = 4 (5 ququarts):</b>
                  <div>D = 1024, ρ = 16 MiB</div>
                </div>
                <div className="p-1.5 rounded bg-bg border border-line">
                  <b>d = 5 (4 qudits):</b>
                  <div>D = 625, ρ = 6.0 MiB</div>
                </div>
              </div>
              <p className="text-[11px] text-ink-3">
                Qudit Lab enforces admission control and pre-execution resource estimation to safeguard system stability.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
