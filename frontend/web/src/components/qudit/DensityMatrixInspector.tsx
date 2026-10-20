import React, { useState } from "react";
import {
  Activity,
  CheckCircle2,
  AlertTriangle,
  Layers,
  Sparkles,
  BarChart3,
  Split,
} from "lucide-react";
import {
  type ComplexVal,
  type SimulationResult,
} from "../../api/quditLab";
import { Badge } from "../ui";

interface DensityMatrixInspectorProps {
  result: SimulationResult | null;
  loading?: boolean;
}

type ViewMode = "mag" | "real" | "imag" | "phase";

export const DensityMatrixInspector: React.FC<DensityMatrixInspectorProps> = ({
  result,
  loading = false,
}) => {
  const [viewMode, setViewMode] = useState<ViewMode>("mag");
  const [selectedCell, setSelectedCell] = useState<{
    r: number;
    c: number;
    val: ComplexVal;
    rowLabel: string;
    colLabel: string;
  } | null>(null);
  const [activeTab, setActiveTab] = useState<"matrix" | "probabilities" | "reduced">("matrix");
  const [selectedReducedWire, setSelectedReducedWire] = useState<string>("q0");

  if (loading) {
    return (
      <div className="rounded-xl border border-line bg-card/60 backdrop-blur-md p-8 flex flex-col items-center justify-center min-h-[350px] space-y-3">
        <div className="h-8 w-8 rounded-full border-2 border-accent border-t-transparent animate-spin" />
        <span className="text-sm text-ink-3">Simulating density matrix evolution (Cirq)...</span>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="rounded-xl border border-line bg-card/60 backdrop-blur-md p-8 flex flex-col items-center justify-center min-h-[350px] text-center space-y-2">
        <Activity className="h-10 w-10 text-ink-3/40" />
        <h3 className="text-sm font-semibold text-ink">No Simulation Data Yet</h3>
        <p className="text-xs text-ink-3 max-w-sm">
          Run your qudit circuit to compute and inspect the exact density matrix, physical invariants, and subsystem reduced states.
        </p>
      </div>
    );
  }

  const { state_validation: sv, total_dim, basis_labels, density_matrix, probabilities, samples, reduced_states } = result;

  // Cell color mapping based on view mode
  const getCellColor = (val: ComplexVal, isDiagonal: boolean): string => {
    if (viewMode === "mag") {
      const alpha = Math.min(1.0, val.mag);
      if (alpha < 0.001) return "bg-subtle/20 border-white/5";
      return isDiagonal
        ? `bg-blue-500/${Math.max(15, Math.round(alpha * 90))} border-blue-400/40 text-blue-200`
        : `bg-indigo-500/${Math.max(15, Math.round(alpha * 80))} border-indigo-400/30 text-indigo-200`;
    } else if (viewMode === "real") {
      const r = val.real;
      if (Math.abs(r) < 0.001) return "bg-subtle/20 border-white/5";
      if (r > 0) {
        const intensity = Math.min(90, Math.max(15, Math.round(r * 90)));
        return `bg-emerald-500/${intensity} border-emerald-400/30 text-emerald-200`;
      } else {
        const intensity = Math.min(90, Math.max(15, Math.round(Math.abs(r) * 90)));
        return `bg-rose-500/${intensity} border-rose-400/30 text-rose-200`;
      }
    } else if (viewMode === "imag") {
      const i = val.imag;
      if (Math.abs(i) < 0.001) return "bg-subtle/20 border-white/5";
      if (i > 0) {
        const intensity = Math.min(90, Math.max(15, Math.round(i * 90)));
        return `bg-amber-500/${intensity} border-amber-400/30 text-amber-200`;
      } else {
        const intensity = Math.min(90, Math.max(15, Math.round(Math.abs(i) * 90)));
        return `bg-purple-500/${intensity} border-purple-400/30 text-purple-200`;
      }
    } else {
      // Phase angle (-pi to +pi)
      return val.mag < 0.01
        ? "bg-subtle/20 border-white/5"
        : `border-accent/30 text-white`;
    }
  };

  const isPure = sv.purity >= 0.999;

  return (
    <div className="rounded-xl border border-line bg-card/60 backdrop-blur-md p-4 shadow-sm space-y-4">
      {/* Top Bar: Tabs & View Controls */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line/60 pb-3">
        {/* Navigation Tabs */}
        <div className="flex items-center gap-1.5 bg-subtle/60 p-1 rounded-lg border border-line/60">
          <button
            type="button"
            onClick={() => setActiveTab("matrix")}
            className={`px-3 py-1 rounded-md text-xs font-medium transition-all ${
              activeTab === "matrix"
                ? "bg-accent text-accent-ink shadow-sm"
                : "text-ink-3 hover:text-ink"
            }`}
          >
            <Layers className="h-3.5 w-3.5 inline mr-1" />
            Density Matrix (ρ)
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("probabilities")}
            className={`px-3 py-1 rounded-md text-xs font-medium transition-all ${
              activeTab === "probabilities"
                ? "bg-accent text-accent-ink shadow-sm"
                : "text-ink-3 hover:text-ink"
            }`}
          >
            <BarChart3 className="h-3.5 w-3.5 inline mr-1" />
            Measurement Distribution
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("reduced")}
            className={`px-3 py-1 rounded-md text-xs font-medium transition-all ${
              activeTab === "reduced"
                ? "bg-accent text-accent-ink shadow-sm"
                : "text-ink-3 hover:text-ink"
            }`}
          >
            <Split className="h-3.5 w-3.5 inline mr-1" />
            Reduced Subsystems
          </button>
        </div>

        {/* View Mode Toggle when matrix tab is active */}
        {activeTab === "matrix" && (
          <div className="flex items-center gap-1 text-xs">
            <span className="text-ink-3 mr-1 text-[11px]">Display:</span>
            {(["mag", "real", "imag", "phase"] as ViewMode[]).map((mode) => (
              <button
                key={mode}
                type="button"
                onClick={() => setViewMode(mode)}
                className={`px-2 py-0.5 rounded text-[11px] font-mono capitalize transition-colors ${
                  viewMode === mode
                    ? "bg-accent/20 text-accent font-bold border border-accent/40"
                    : "text-ink-3 hover:text-ink bg-subtle/40 border border-transparent"
                }`}
              >
                {mode === "mag" ? "|ρ|" : mode === "real" ? "Re(ρ)" : mode === "imag" ? "Im(ρ)" : "∠ρ"}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Quantum Physical Invariants Card */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-2.5 p-3 rounded-lg bg-subtle/30 border border-line/60 text-xs">
        {/* Trace */}
        <div className="space-y-0.5">
          <div className="text-ink-3 text-[11px] flex items-center gap-1">
            <span>Trace Tr(ρ)</span>
            {Math.abs(sv.trace - 1.0) < 1e-4 ? (
              <CheckCircle2 className="h-3 w-3 text-emerald-400" />
            ) : (
              <AlertTriangle className="h-3 w-3 text-rose-400" />
            )}
          </div>
          <div className="font-mono font-bold text-ink">
            {sv.trace.toFixed(4)}
          </div>
        </div>

        {/* Hermiticity */}
        <div className="space-y-0.5">
          <div className="text-ink-3 text-[11px]">Hermiticity</div>
          <div className="font-mono font-bold flex items-center gap-1">
            {sv.is_hermitian ? (
              <Badge tone="ok">
                ρ = ρ†
              </Badge>
            ) : (
              <Badge tone="danger">
                Non-Hermitian
              </Badge>
            )}
          </div>
        </div>

        {/* Positivity */}
        <div className="space-y-0.5">
          <div className="text-ink-3 text-[11px]">Positivity</div>
          <div className="font-mono font-bold">
            {sv.is_positive_semidefinite ? (
              <Badge tone="ok">
                λ_min ≥ 0
              </Badge>
            ) : (
              <Badge tone="danger">
                λ_min &lt; 0
              </Badge>
            )}
          </div>
        </div>

        {/* Purity */}
        <div className="space-y-0.5">
          <div className="text-ink-3 text-[11px]">Purity γ = Tr(ρ²)</div>
          <div className="font-mono font-bold flex items-center gap-1.5">
            <span className={isPure ? "text-emerald-400" : "text-amber-400"}>
              {sv.purity.toFixed(4)}
            </span>
            <Badge tone={isPure ? "accent" : "warn"}>
              {isPure ? "Pure" : "Mixed"}
            </Badge>
          </div>
        </div>

        {/* Von Neumann Entropy */}
        <div className="space-y-0.5">
          <div className="text-ink-3 text-[11px]">Entropy S(ρ)</div>
          <div className="font-mono font-bold text-ink">
            {sv.entropy !== null && sv.entropy !== undefined ? `${sv.entropy.toFixed(4)} bits` : "—"}
          </div>
        </div>
      </div>

      {/* Main Tab Content */}
      {activeTab === "matrix" && (
        <div className="space-y-3">
          {result.density_matrix_truncated ? (
            <div className="p-4 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs">
              Density matrix dimension (D = {total_dim}) exceeds full interactive browser threshold (D &gt; 64). Compact summaries and reduced subsystem matrices are active below.
            </div>
          ) : density_matrix ? (
            <div className="overflow-x-auto pb-2 scrollbar-thin">
              <div className="inline-block min-w-full">
                {/* Column Basis Headers */}
                <div className="flex pl-16 mb-1 gap-1">
                  {basis_labels.map((colLabel, c) => (
                    <div
                      key={`col-${c}`}
                      className="w-14 text-center font-mono text-[10px] text-ink-3 truncate"
                      title={colLabel}
                    >
                      {colLabel}
                    </div>
                  ))}
                </div>

                {/* Matrix Rows */}
                <div className="flex flex-col gap-1">
                  {density_matrix.map((row, r) => (
                    <div key={`row-${r}`} className="flex items-center gap-1">
                      {/* Row Basis Header */}
                      <div
                        className="w-16 text-right pr-2 font-mono text-[10px] text-ink-3 truncate shrink-0"
                        title={basis_labels[r]}
                      >
                        {basis_labels[r]}
                      </div>

                      {/* Row Cells */}
                      {row.map((cell, c) => {
                        const isDiag = r === c;
                        const isCellSelected =
                          selectedCell?.r === r && selectedCell?.c === c;

                        return (
                          <div
                            key={`cell-${r}-${c}`}
                            onClick={() =>
                              setSelectedCell({
                                r,
                                c,
                                val: cell,
                                rowLabel: basis_labels[r],
                                colLabel: basis_labels[c],
                              })
                            }
                            className={`w-14 h-11 flex flex-col items-center justify-center rounded border font-mono text-[10px] cursor-pointer transition-all duration-150 select-none ${getCellColor(
                              cell,
                              isDiag
                            )} ${isCellSelected ? "ring-2 ring-accent scale-105 z-10" : ""}`}
                            title={`⟨${basis_labels[r]}|ρ|${basis_labels[c]}⟩ = ${cell.real >= 0 ? "+" : ""}${cell.real.toFixed(3)} ${cell.imag >= 0 ? "+" : ""}${cell.imag.toFixed(3)}i`}
                          >
                            <span className="font-bold leading-none">
                              {viewMode === "mag"
                                ? cell.mag.toFixed(3)
                                : viewMode === "real"
                                ? cell.real.toFixed(3)
                                : viewMode === "imag"
                                ? cell.imag.toFixed(3)
                                : `${(cell.phase / Math.PI).toFixed(2)}π`}
                            </span>
                            {isDiag && (
                              <span className="text-[8px] text-ink-3/70 leading-none mt-0.5">
                                pop
                              </span>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : null}

          {/* Cell Detail Card */}
          {selectedCell && (
            <div className="rounded-lg border border-accent/40 bg-accent/10 p-3 text-xs flex flex-wrap items-center justify-between gap-3 animate-in fade-in duration-150">
              <div className="space-y-0.5 font-mono">
                <span className="text-accent font-semibold">
                  ⟨{selectedCell.rowLabel} | ρ | {selectedCell.colLabel}⟩:
                </span>{" "}
                <span className="text-ink font-bold">
                  {selectedCell.val.real >= 0 ? "+" : ""}
                  {selectedCell.val.real.toFixed(5)}{" "}
                  {selectedCell.val.imag >= 0 ? "+" : ""}
                  {selectedCell.val.imag.toFixed(5)}i
                </span>
              </div>
              <div className="flex items-center gap-4 text-ink-2 font-mono">
                <span>Magnitude: <b>{selectedCell.val.mag.toFixed(5)}</b></span>
                <span>Phase: <b>{(selectedCell.val.phase / Math.PI).toFixed(4)}π rad</b></span>
                <span>Type: <b>{selectedCell.r === selectedCell.c ? "Diagonal (Population)" : "Off-Diagonal (Coherence)"}</b></span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Probabilities Tab */}
      {activeTab === "probabilities" && (
        <div className="space-y-4">
          <div className="text-xs text-ink-3">
            Exact Born-rule probability distribution P(|j⟩) = ⟨j|ρ|j⟩ calculated from diagonal density-matrix elements.
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {basis_labels.map((label) => {
              const prob = probabilities[label] ?? 0.0;
              const sampleCount = samples ? samples[label] ?? 0 : null;
              const pct = (prob * 100).toFixed(2);

              return (
                <div
                  key={`prob-${label}`}
                  className="p-3 rounded-lg border border-line/80 bg-subtle/30 space-y-2"
                >
                  <div className="flex items-center justify-between font-mono text-xs">
                    <span className="font-bold text-accent">{label}</span>
                    <span className="text-ink font-semibold">{pct}%</span>
                  </div>

                  {/* Probability Bar */}
                  <div className="h-2 w-full rounded-full bg-subtle overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-accent to-accent-2 transition-all duration-300 rounded-full"
                      style={{ width: `${Math.min(100, prob * 100)}%` }}
                    />
                  </div>

                  {samples && (
                    <div className="flex items-center justify-between text-[11px] text-ink-3">
                      <span>Shots sample:</span>
                      <span className="font-mono font-medium text-ink">
                        {sampleCount} shots
                      </span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Reduced Subsystem Tab */}
      {activeTab === "reduced" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs text-ink-3">
              Partial trace Tr_{"{rest}"}(ρ) yields the exact local reduced density matrix for a selected qudit subsystem:
            </span>

            {/* Wire Selector */}
            <div className="flex items-center gap-1.5">
              <span className="text-xs text-ink-3">Subsystem:</span>
              <div className="flex items-center gap-1 bg-subtle p-0.5 rounded border border-line">
                {Object.keys(reduced_states).map((wireId) => (
                  <button
                    key={wireId}
                    type="button"
                    onClick={() => setSelectedReducedWire(wireId)}
                    className={`px-2 py-0.5 rounded text-xs font-mono font-bold transition-colors ${
                      selectedReducedWire === wireId
                        ? "bg-accent text-accent-ink"
                        : "text-ink-3 hover:text-ink"
                    }`}
                  >
                    {wireId}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Subsystem State Card */}
          {reduced_states[selectedReducedWire] && (
            <div className="p-4 rounded-xl border border-line bg-subtle/40 space-y-4">
              {(() => {
                const red = reduced_states[selectedReducedWire];
                const dim = red.dimension;
                const isSubPure = red.purity >= 0.999;

                return (
                  <>
                    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line/60 pb-3">
                      <div className="flex items-center gap-2">
                        <Badge tone="accent">
                          Wire {selectedReducedWire}
                        </Badge>
                        <span className="text-xs font-semibold text-ink">
                          Reduced State ρ_{selectedReducedWire} (Dimension {dim})
                        </span>
                      </div>

                      <div className="flex items-center gap-4 text-xs font-mono">
                        <div>
                          <span className="text-ink-3 mr-1">Subsystem Purity γ:</span>
                          <b className={isSubPure ? "text-emerald-400" : "text-amber-400"}>
                            {red.purity.toFixed(4)}
                          </b>
                        </div>
                        <div>
                          <span className="text-ink-3 mr-1">Subsystem Entropy S:</span>
                          <b className="text-ink">
                            {red.entropy !== null && red.entropy !== undefined
                              ? `${red.entropy.toFixed(4)} bits`
                              : "—"}
                          </b>
                        </div>
                      </div>
                    </div>

                    {/* Small Reduced Matrix Heatmap */}
                    <div className="flex flex-col items-center justify-center p-2">
                      <div className="grid gap-1.5" style={{ gridTemplateColumns: `repeat(${dim}, minmax(0, 1fr))` }}>
                        {red.density_matrix.map((row, r) =>
                          row.map((cell, c) => (
                            <div
                              key={`red-${r}-${c}`}
                              className="w-16 h-12 flex flex-col items-center justify-center rounded border border-line bg-card p-1 text-center font-mono text-[11px]"
                            >
                              <span className="font-bold text-accent">
                                {cell.mag.toFixed(3)}
                              </span>
                              <span className="text-[9px] text-ink-3">
                                |{r}⟩⟨{c}|
                              </span>
                            </div>
                          ))
                        )}
                      </div>
                    </div>

                    {/* Pedagogical Callout */}
                    {!isSubPure && isPure && (
                      <div className="p-3 rounded-lg bg-indigo-500/10 border border-indigo-500/30 text-xs text-indigo-300 space-y-1">
                        <div className="font-semibold flex items-center gap-1.5">
                          <Sparkles className="h-3.5 w-3.5" />
                          Signature of Quantum Entanglement Detected!
                        </div>
                        <p className="text-[11px] leading-relaxed">
                          The global circuit density matrix is pure (γ = 1.000), but tracing out the other subsystems leaves wire {selectedReducedWire} in a mixed state (purity γ = {red.purity.toFixed(4)} &lt; 1). This loss of local purity while preserving global purity is the hallmark of genuine quantum entanglement!
                        </p>
                      </div>
                    )}
                  </>
                );
              })()}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
