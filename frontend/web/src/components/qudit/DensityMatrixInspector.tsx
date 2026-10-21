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
  /** True when the circuit or noise config has changed since this result was produced. */
  stale?: boolean;
  /** Invoked by the staleness banner's re-run action. */
  onRerun?: () => void;
}

type ViewMode = "mag" | "real" | "imag" | "phase";

export const DensityMatrixInspector: React.FC<DensityMatrixInspectorProps> = ({
  result,
  loading = false,
  stale = false,
  onRerun,
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

  // Bra-ket formatting.
  //
  // `basis_labels` already arrive from the API as kets ("|0⟩", "|12⟩").
  // Interpolating them straight into a ⟨row|ρ|col⟩ template therefore produced
  // "⟨|0⟩|ρ||0⟩⟩" — doubled bars and an unbalanced bracket. This is a teaching
  // surface, so the notation has to be the notation the lesson text uses:
  // strip the decoration back to the bare index and rebuild the matrix element.
  const ketIndex = (label: string) => label.replace(/[|⟩⟨]/g, "").trim();
  const braket = (rowLabel: string, colLabel: string) =>
    `⟨${ketIndex(rowLabel)}|ρ|${ketIndex(colLabel)}⟩`;

  // "-0.00π" is not a phase. Math.atan2 returns tiny negative angles for
  // entries that are real and positive up to floating-point noise, and
  // toFixed() keeps the sign bit when it rounds them to zero. Round first,
  // then drop a sign that only survives on a zero magnitude.
  const fmtPhasePi = (phase: number, digits: number) => {
    const s = (phase / Math.PI).toFixed(digits);
    return /^-0(\.0+)?$/.test(s) ? s.slice(1) : s;
  };

  // Cell colour mapping.
  //
  // These values are computed per cell, so the colour CANNOT be expressed as a
  // Tailwind utility: Tailwind generates CSS by statically scanning source for
  // literal class strings, and a template literal like `bg-blue-500/${n}` is
  // never emitted. An earlier version did exactly that, which is why every
  // cell rendered with a transparent background and the heatmap carried no
  // information at all. Inline styles are the correct tool for a continuous
  // scale; the class list keeps only the static parts.
  const clamp01 = (x: number) => Math.min(1, Math.max(0, x));
  const mix = (rgb: string, a: number) => `rgba(${rgb}, ${(0.10 + 0.78 * clamp01(a)).toFixed(3)})`;
  const EMPTY_CELL = { backgroundColor: "rgba(148, 163, 184, 0.06)", borderColor: "rgba(255,255,255,0.06)" };

  // Magnitude ramp, extracted so the reduced-subsystem heatmap can use the
  // identical encoding. It always displays |ρ_ij|, so it must not follow the
  // main grid's view mode.
  const magStyle = (val: ComplexVal, isDiagonal: boolean): React.CSSProperties => {
    const a = clamp01(val.mag);
    if (a < 0.001) return EMPTY_CELL;
    return isDiagonal
      ? { backgroundColor: mix("59, 130, 246", a), borderColor: "rgba(96,165,250,0.45)", color: "#dbeafe" }
      : { backgroundColor: mix("99, 102, 241", a), borderColor: "rgba(129,140,248,0.35)", color: "#e0e7ff" };
  };

  const cellStyle = (val: ComplexVal, isDiagonal: boolean): React.CSSProperties => {
    const EMPTY = EMPTY_CELL;

    if (viewMode === "mag") {
      return magStyle(val, isDiagonal);
    }
    if (viewMode === "real" || viewMode === "imag") {
      const v = viewMode === "real" ? val.real : val.imag;
      if (Math.abs(v) < 0.001) return EMPTY;
      const a = clamp01(Math.abs(v));
      return v > 0
        ? { backgroundColor: mix(viewMode === "real" ? "16, 185, 129" : "245, 158, 11", a),
            borderColor: viewMode === "real" ? "rgba(52,211,153,0.35)" : "rgba(251,191,36,0.35)",
            color: viewMode === "real" ? "#d1fae5" : "#fef3c7" }
        : { backgroundColor: mix(viewMode === "real" ? "244, 63, 94" : "168, 85, 247", a),
            borderColor: viewMode === "real" ? "rgba(251,113,133,0.35)" : "rgba(192,132,252,0.35)",
            color: viewMode === "real" ? "#ffe4e6" : "#f3e8ff" };
    }
    // Phase: hue encodes the angle, saturation fades out as magnitude -> 0, so
    // a numerically meaningless phase on a zero entry cannot look significant.
    if (val.mag < 0.01) return EMPTY;
    const deg = ((val.phase + Math.PI) / (2 * Math.PI)) * 360;
    return {
      backgroundColor: `hsla(${deg.toFixed(1)}, 70%, 50%, ${(0.18 + 0.55 * clamp01(val.mag)).toFixed(3)})`,
      borderColor: `hsla(${deg.toFixed(1)}, 70%, 65%, 0.45)`,
      color: "#ffffff",
    };
  };

  const isPure = sv.purity >= 0.999;

  return (
    <div
      className={`rounded-xl border bg-card/60 backdrop-blur-md p-4 shadow-sm space-y-4 ${
        stale ? "border-warn/50" : "border-line"
      }`}
    >
      {/* These numbers describe a circuit the user has since edited. Saying so
          is the whole point: a quantum result that silently belongs to a
          different circuit is worse than no result. */}
      {stale && (
        <div
          role="status"
          className="flex flex-wrap items-center gap-x-3 gap-y-2 rounded-lg border border-warn/40 bg-warn/10 px-3 py-2 text-xs text-warn"
        >
          <AlertTriangle className="h-4 w-4 shrink-0" />
          <span>
            <strong className="font-semibold">These results are out of date.</strong>{" "}
            The circuit or noise configuration changed after this run, so the matrix and
            metrics below do not describe what is currently on the canvas.
          </span>
          {onRerun && (
            <button
              type="button"
              onClick={onRerun}
              className="ml-auto rounded-md border border-warn/50 px-2 py-0.5 font-semibold text-warn transition-colors hover:bg-warn/20"
            >
              Re-run simulation
            </button>
          )}
        </div>
      )}

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

                        const select = () =>
                          setSelectedCell({
                            r,
                            c,
                            val: cell,
                            rowLabel: basis_labels[r],
                            colLabel: basis_labels[c],
                          });

                        return (
                          <div
                            key={`cell-${r}-${c}`}
                            role="button"
                            tabIndex={0}
                            aria-label={`Row ${ketIndex(basis_labels[r])}, column ${ketIndex(basis_labels[c])}: real ${cell.real.toFixed(3)}, imaginary ${cell.imag.toFixed(3)}`}
                            onClick={select}
                            onKeyDown={(e) => {
                              if (e.key === "Enter" || e.key === " ") {
                                e.preventDefault();
                                select();
                              }
                            }}
                            style={cellStyle(cell, isDiag)}
                            className={`w-14 h-11 flex flex-col items-center justify-center rounded border font-mono text-[10px] cursor-pointer transition-all duration-150 select-none focus:outline-none focus-visible:ring-2 focus-visible:ring-accent ${
                              isCellSelected ? "ring-2 ring-accent scale-105 z-10" : ""
                            }`}
                            title={`${braket(basis_labels[r], basis_labels[c])} = ${cell.real >= 0 ? "+" : ""}${cell.real.toFixed(3)} ${cell.imag >= 0 ? "+" : ""}${cell.imag.toFixed(3)}i`}
                          >
                            <span className="font-bold leading-none">
                              {viewMode === "mag"
                                ? cell.mag.toFixed(3)
                                : viewMode === "real"
                                ? cell.real.toFixed(3)
                                : viewMode === "imag"
                                ? cell.imag.toFixed(3)
                                : `${fmtPhasePi(cell.phase, 2)}π`}
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

          {/* Colour legend — without it the heatmap is not readable */}
          {density_matrix && !result.density_matrix_truncated && (
            <MatrixLegend viewMode={viewMode} />
          )}

          {/* Cell Detail Card */}
          {selectedCell && (
            <div className="rounded-lg border border-accent/40 bg-accent/10 p-3 text-xs flex flex-wrap items-center justify-between gap-3 animate-in fade-in duration-150">
              <div className="space-y-0.5 font-mono">
                <span className="text-accent font-semibold">
                  {braket(selectedCell.rowLabel, selectedCell.colLabel)}:
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
                <span>Phase: <b>{fmtPhasePi(selectedCell.val.phase, 4)}π rad</b></span>
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

                    {/* Small Reduced Matrix Heatmap.

                        This grid used a single static `bg-card` for every
                        entry, so ρ_q0 was rendered as a colourless table while
                        the full matrix beside it was a heatmap — the same
                        defect that was fixed for the main grid, left behind
                        here. Reuse the magnitude ramp and label its scale, so
                        a student comparing ρ with ρ_q0 reads one visual
                        language rather than two. */}
                    <div className="flex flex-col items-center justify-center gap-2 p-2">
                      <div className="grid gap-1.5" style={{ gridTemplateColumns: `repeat(${dim}, minmax(0, 1fr))` }}>
                        {red.density_matrix.map((row, r) =>
                          row.map((cell, c) => (
                            <div
                              key={`red-${r}-${c}`}
                              style={magStyle(cell, r === c)}
                              title={`${braket(String(r), String(c))} = ${cell.real >= 0 ? "+" : ""}${cell.real.toFixed(3)} ${cell.imag >= 0 ? "+" : ""}${cell.imag.toFixed(3)}i`}
                              className="w-16 h-12 flex flex-col items-center justify-center rounded border p-1 text-center font-mono text-[11px]"
                            >
                              <span className="font-bold">
                                {cell.mag.toFixed(3)}
                              </span>
                              <span className="text-[9px] opacity-70">
                                |{r}⟩⟨{c}|
                              </span>
                            </div>
                          ))
                        )}
                      </div>
                      <div className="flex items-center gap-2 text-[10px] text-ink-3 font-mono">
                        <span>|ρ_ij| 0.0</span>
                        <span className="inline-flex overflow-hidden rounded border border-white/10">
                          {[0, 0.25, 0.5, 0.75, 1].map((a) => (
                            <span
                              key={a}
                              className="h-2.5 w-4"
                              style={{ backgroundColor: `rgba(99, 102, 241, ${(0.1 + 0.78 * a).toFixed(3)})` }}
                            />
                          ))}
                        </span>
                        <span>1.0 · diagonal entries in blue</span>
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

/**
 * Colour key for the density-matrix heatmap.
 *
 * The grid encodes a continuous value in cell colour; without a key the
 * reader cannot tell a large entry from a small one, or a positive real part
 * from a negative one. Swatches are generated from the same inline-style
 * scale the cells use, so the legend cannot drift from the grid.
 */
function MatrixLegend({ viewMode }: { viewMode: ViewMode }) {
  const ramp = (rgb: string) =>
    [0, 0.25, 0.5, 0.75, 1].map((a) => `rgba(${rgb}, ${(0.1 + 0.78 * a).toFixed(3)})`);

  const Swatches = ({ colors }: { colors: string[] }) => (
    <span className="inline-flex overflow-hidden rounded border border-white/10">
      {colors.map((c) => (
        <span key={c} className="h-3 w-5" style={{ backgroundColor: c }} />
      ))}
    </span>
  );

  return (
    <div className="flex flex-wrap items-center gap-x-5 gap-y-2 rounded-lg border border-line/60 bg-subtle/30 px-3 py-2 text-[11px] text-ink-3">
      <span className="font-semibold text-ink-2">Colour scale:</span>

      {viewMode === "mag" && (
        <>
          <span className="flex items-center gap-1.5">
            diagonal (populations) 0.0 <Swatches colors={ramp("59, 130, 246")} /> 1.0
          </span>
          <span className="flex items-center gap-1.5">
            off-diagonal (coherences) 0.0 <Swatches colors={ramp("99, 102, 241")} /> 1.0
          </span>
        </>
      )}

      {viewMode === "real" && (
        <span className="flex items-center gap-1.5">
          −1.0 <Swatches colors={[...ramp("244, 63, 94")].reverse()} /> 0
          <Swatches colors={ramp("16, 185, 129")} /> +1.0
        </span>
      )}

      {viewMode === "imag" && (
        <span className="flex items-center gap-1.5">
          −1.0 <Swatches colors={[...ramp("168, 85, 247")].reverse()} /> 0
          <Swatches colors={ramp("245, 158, 11")} /> +1.0
        </span>
      )}

      {viewMode === "phase" && (
        <span className="flex items-center gap-1.5">
          −π
          <span className="inline-flex overflow-hidden rounded border border-white/10">
            {[0, 60, 120, 180, 240, 300, 359].map((d) => (
              <span key={d} className="h-3 w-5" style={{ backgroundColor: `hsla(${d}, 70%, 50%, 0.7)` }} />
            ))}
          </span>
          +π
          <span className="ml-1 text-ink-4">(cells with |ρ| ≈ 0 are greyed: their phase is undefined)</span>
        </span>
      )}
    </div>
  );
}
