import React, { useState } from "react";
import {
  Activity,
  CheckCircle2,
  AlertTriangle,
  Layers,
  BarChart3,
  Split,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Maximize2,
  Minimize2,
} from "lucide-react";
import {
  type ComplexVal,
  type SimulationResult,
} from "../../api/quditLab";
import { Badge, cn } from "../ui";

interface DensityMatrixInspectorProps {
  result: SimulationResult | null;
  loading?: boolean;
  /** True when the circuit or noise config has changed since this result was produced. */
  stale?: boolean;
  /** Invoked by the staleness banner's re-run action. */
  onRerun?: () => void;
}

type ViewMode = "mag" | "real" | "imag" | "phase";

// -----------------------------------------------------------------------------
// Viridis Colormap (Screenshots A & normal Composer target)
// -----------------------------------------------------------------------------
const VIRIDIS_STOPS: [number, number, number][] = [
  [68, 1, 84],     // 0.00: #440154 (dark purple)
  [72, 40, 120],   // 0.10: #482878
  [62, 73, 137],   // 0.20: #3e4989 (deep blue)
  [49, 104, 142],  // 0.30: #31688e
  [38, 130, 142],  // 0.40: #26828e
  [31, 158, 137],  // 0.50: #1f9e89 (teal)
  [53, 183, 121],  // 0.60: #35b779
  [110, 206, 88],  // 0.70: #6ece58 (lime green)
  [181, 222, 43],  // 0.80: #b5de2b
  [229, 228, 25],  // 0.90: #e5e419
  [253, 231, 37],  // 1.00: #fde725 (yellow)
];

function viridisColor(t: number): string {
  const val = Math.max(0, Math.min(1, t));
  const pos = val * (VIRIDIS_STOPS.length - 1);
  const idx = Math.floor(pos);
  const frac = pos - idx;

  if (idx >= VIRIDIS_STOPS.length - 1) {
    const last = VIRIDIS_STOPS[VIRIDIS_STOPS.length - 1];
    return `rgb(${last[0]}, ${last[1]}, ${last[2]})`;
  }

  const c1 = VIRIDIS_STOPS[idx];
  const c2 = VIRIDIS_STOPS[idx + 1];
  const r = Math.round(c1[0] + frac * (c2[0] - c1[0]));
  const g = Math.round(c1[1] + frac * (c2[1] - c1[1]));
  const b = Math.round(c1[2] + frac * (c2[2] - c1[2]));

  return `rgb(${r}, ${g}, ${b})`;
}

// Signed diverging colormap for Real/Imag [-1, 1]
function signedColor(v: number): string {
  const clamped = Math.max(-1, Math.min(1, v));
  if (Math.abs(clamped) < 0.005) {
    return "#111827"; // neutral dark slate
  }
  if (clamped > 0) {
    // Green ramp
    const a = Math.min(1, clamped);
    const r = Math.round(17 + a * (16 - 17));
    const g = Math.round(24 + a * (185 - 24));
    const b = Math.round(39 + a * (129 - 39));
    return `rgb(${r}, ${g}, ${b})`;
  } else {
    // Rose ramp
    const a = Math.min(1, -clamped);
    const r = Math.round(17 + a * (225 - 17));
    const g = Math.round(24 + a * (29 - 24));
    const b = Math.round(39 + a * (72 - 39));
    return `rgb(${r}, ${g}, ${b})`;
  }
}

// Cyclic hue colormap for Phase [-pi, pi]
function phaseColor(phase: number, mag: number): { bg: string; undefinedPhase: boolean } {
  if (mag < 0.005) {
    return { bg: "#0d1322", undefinedPhase: true };
  }
  const deg = (((phase + Math.PI) / (2 * Math.PI)) * 360).toFixed(1);
  const opacity = Math.min(1, 0.4 + 0.6 * Math.min(1, mag)).toFixed(2);
  return {
    bg: `hsla(${deg}, 85%, 52%, ${opacity})`,
    undefinedPhase: false,
  };
}

export const DensityMatrixInspector: React.FC<DensityMatrixInspectorProps> = ({
  result,
  loading = false,
  stale = false,
  onRerun,
}) => {
  const [viewMode, setViewMode] = useState<ViewMode>("mag");
  const [zoom, setZoom] = useState<number>(1);
  const [fullscreen, setFullscreen] = useState<boolean>(false);
  const [hoveredCell, setHoveredCell] = useState<{
    r: number;
    c: number;
    val: ComplexVal;
    rowLabel: string;
    colLabel: string;
  } | null>(null);
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
      <div className="rounded-xl border border-line bg-raised/60 backdrop-blur-md p-8 flex flex-col items-center justify-center min-h-[350px] space-y-3">
        <div className="h-8 w-8 rounded-full border-2 border-accent border-t-transparent animate-spin" />
        <span className="text-sm text-ink-3 font-mono">Simulating genuine qudit density matrix evolution (Cirq)...</span>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="rounded-xl border border-line bg-raised/60 backdrop-blur-md p-8 flex flex-col items-center justify-center min-h-[350px] text-center space-y-2">
        <Activity className="h-10 w-10 text-ink-3/40" />
        <h3 className="text-sm font-semibold text-ink">No Simulation Data Yet</h3>
        <p className="text-xs text-ink-3 max-w-sm">
          Run your qudit circuit to compute and inspect the exact density matrix, physical invariants, and subsystem reduced states.
        </p>
      </div>
    );
  }

  const {
    state_validation: sv,
    total_dim,
    basis_labels,
    density_matrix,
    probabilities,
    samples,
    reduced_states,
  } = result;

  const isPure = sv.purity >= 0.999;

  // Clean basis labels without brackets for raw bra-ket construction
  const rawIndex = (label: string) => label.replace(/[|⟩⟨]/g, "").trim();
  const formatBraket = (rLab: string, cLab: string) => `⟨${rawIndex(rLab)}|ρ|${rawIndex(cLab)}⟩`;

  // Format phase as multiple of pi
  const formatPhasePi = (phase: number) => {
    const s = (phase / Math.PI).toFixed(4);
    return /^-0(\.0+)?$/.test(s) ? s.slice(1) : s;
  };

  // Base cell size adapted to matrix dimension
  const baseCellSize =
    total_dim <= 4 ? 64 : total_dim <= 9 ? 44 : total_dim <= 16 ? 32 : total_dim <= 25 ? 26 : 20;
  const cellSize = Math.round(baseCellSize * zoom);

  // Active cell being inspected (hover takes precedence, then selected)
  const activeInspected = hoveredCell || selectedCell;

  // Colorbar config based on view mode
  const colorbarTicks =
    viewMode === "mag"
      ? [1.0, 0.8, 0.6, 0.4, 0.2, 0.0]
      : viewMode === "phase"
      ? [1.0, 0.5, 0.0, -0.5, -1.0]
      : [1.0, 0.5, 0.0, -0.5, -1.0];

  const colorbarGradient =
    viewMode === "mag"
      ? "linear-gradient(to top, #440154 0%, #3e4989 20%, #26828e 40%, #1f9e89 50%, #35b779 60%, #b5de2b 80%, #fde725 100%)"
      : viewMode === "phase"
      ? "linear-gradient(to top, hsl(360, 85%, 52%) 0%, hsl(270, 85%, 52%) 25%, hsl(180, 85%, 52%) 50%, hsl(90, 85%, 52%) 75%, hsl(0, 85%, 52%) 100%)"
      : "linear-gradient(to top, #e11d48 0%, #111827 50%, #10b981 100%)";

  const colorbarLabel =
    viewMode === "mag" ? "|ρ|" : viewMode === "real" ? "Re(ρ)" : viewMode === "imag" ? "Im(ρ)" : "∠ρ";

  return (
    <div
      className={cn(
        "rounded-xl border bg-[#080c16]/95 border-line shadow-sm backdrop-blur-md p-5 space-y-4 select-none relative transition-all",
        stale && "border-warn/50",
        fullscreen && "fixed inset-4 z-50 bg-[#070a12]/98 border-accent/40 shadow-2xl overflow-auto p-6"
      )}
    >
      {/* Staleness banner if circuit was edited */}
      {stale && (
        <div
          role="status"
          className="flex flex-wrap items-center gap-x-3 gap-y-2 rounded-lg border border-warn/40 bg-warn/10 px-3 py-2 text-xs text-warn"
        >
          <AlertTriangle className="h-4 w-4 shrink-0" />
          <span>
            <strong className="font-semibold">Results out of sync:</strong> The circuit or noise configuration was modified after this simulation run.
          </span>
          {onRerun && (
            <button
              type="button"
              onClick={onRerun}
              className="ml-auto rounded-md border border-warn/50 px-2.5 py-0.5 font-semibold text-warn hover:bg-warn/20 transition-colors"
            >
              Re-run simulation
            </button>
          )}
        </div>
      )}

      {/* Top Header & Tab Switcher matching IBM Composer / Normal Composer */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line/60 pb-3">
        {/* Navigation Tabs */}
        <div className="flex items-center gap-1.5 bg-subtle/40 p-1 rounded-lg border border-line/60">
          <button
            type="button"
            onClick={() => setActiveTab("matrix")}
            className={`px-3 py-1 rounded-md text-xs font-mono font-medium transition-all ${
              activeTab === "matrix"
                ? "bg-accent text-accent-ink shadow-sm"
                : "text-ink-3 hover:text-ink"
            }`}
          >
            <Layers className="h-3.5 w-3.5 inline mr-1.5" />
            Density Matrix (ρ)
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("probabilities")}
            className={`px-3 py-1 rounded-md text-xs font-mono font-medium transition-all ${
              activeTab === "probabilities"
                ? "bg-accent text-accent-ink shadow-sm"
                : "text-ink-3 hover:text-ink"
            }`}
          >
            <BarChart3 className="h-3.5 w-3.5 inline mr-1.5" />
            Measurement Distribution
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("reduced")}
            className={`px-3 py-1 rounded-md text-xs font-mono font-medium transition-all ${
              activeTab === "reduced"
                ? "bg-accent text-accent-ink shadow-sm"
                : "text-ink-3 hover:text-ink"
            }`}
          >
            <Split className="h-3.5 w-3.5 inline mr-1.5" />
            Reduced Subsystems
          </button>
        </div>

        {/* View Mode & Zoom Toolbar */}
        {activeTab === "matrix" && (
          <div className="flex items-center gap-3">
            {/* Display Modes */}
            <div className="flex items-center gap-1 text-xs bg-subtle/30 p-0.5 rounded border border-line/40">
              <span className="text-ink-3 px-1.5 text-[11px] font-mono">Display:</span>
              {(["mag", "real", "imag", "phase"] as ViewMode[]).map((mode) => (
                <button
                  key={mode}
                  type="button"
                  onClick={() => setViewMode(mode)}
                  className={`px-2.5 py-0.5 rounded text-[11px] font-mono transition-colors ${
                    viewMode === mode
                      ? "bg-accent text-accent-ink font-bold shadow-sm"
                      : "text-ink-3 hover:text-ink hover:bg-hover"
                  }`}
                >
                  {mode === "mag" ? "|ρ|" : mode === "real" ? "Re(ρ)" : mode === "imag" ? "Im(ρ)" : "∠ρ"}
                </button>
              ))}
            </div>

            {/* Zoom & Fullscreen Toolbar Controls matching Screenshot A */}
            <div className="flex items-center gap-1 border-l border-line/50 pl-2">
              <button
                type="button"
                onClick={() => setZoom((z) => Math.min(2.0, +(z + 0.25).toFixed(2)))}
                title="Zoom In"
                className="p-1.5 rounded hover:bg-hover text-ink-3 hover:text-white transition-colors"
                aria-label="Zoom in"
              >
                <ZoomIn className="w-4 h-4" />
              </button>
              <button
                type="button"
                onClick={() => setZoom((z) => Math.max(0.75, +(z - 0.25).toFixed(2)))}
                title="Zoom Out"
                className="p-1.5 rounded hover:bg-hover text-ink-3 hover:text-white transition-colors"
                aria-label="Zoom out"
              >
                <ZoomOut className="w-4 h-4" />
              </button>
              <button
                type="button"
                onClick={() => setZoom(1.0)}
                title="Reset View"
                className="p-1.5 rounded hover:bg-hover text-ink-3 hover:text-white transition-colors"
                aria-label="Reset zoom"
              >
                <RotateCcw className="w-4 h-4" />
              </button>
              <button
                type="button"
                onClick={() => setFullscreen((f) => !f)}
                title={fullscreen ? "Exit Fullscreen" : "Fullscreen"}
                className="p-1.5 rounded hover:bg-hover text-ink-3 hover:text-white transition-colors"
                aria-label="Toggle fullscreen"
              >
                {fullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Quantum Physical Invariants Card (Scientific Validation) */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 p-3.5 rounded-lg bg-[#0c1220]/80 border border-line/60 text-xs">
        {/* Trace */}
        <div className="space-y-0.5">
          <div className="text-ink-3 text-[11px] font-mono flex items-center gap-1.5">
            <span>Trace Tr(ρ)</span>
            {Math.abs(sv.trace - 1.0) < 1e-4 ? (
              <CheckCircle2 className="h-3 w-3 text-emerald-400" />
            ) : (
              <AlertTriangle className="h-3 w-3 text-rose-400" />
            )}
          </div>
          <div className="font-mono font-bold text-ink text-sm">
            {sv.trace.toFixed(4)}
          </div>
        </div>

        {/* Hermiticity */}
        <div className="space-y-0.5">
          <div className="text-ink-3 text-[11px] font-mono">Hermiticity</div>
          <div className="font-mono font-bold flex items-center gap-1">
            {sv.is_hermitian ? (
              <Badge tone="ok">ρ = ρ†</Badge>
            ) : (
              <Badge tone="danger">Non-Hermitian</Badge>
            )}
          </div>
        </div>

        {/* Positivity */}
        <div className="space-y-0.5">
          <div className="text-ink-3 text-[11px] font-mono">Positivity</div>
          <div className="font-mono font-bold">
            {sv.is_positive_semidefinite ? (
              <Badge tone="ok">λ_min ≥ 0</Badge>
            ) : (
              <Badge tone="danger">λ_min &lt; 0</Badge>
            )}
          </div>
        </div>

        {/* Purity */}
        <div className="space-y-0.5">
          <div className="text-ink-3 text-[11px] font-mono">Purity γ = Tr(ρ²)</div>
          <div className="font-mono font-bold flex items-center gap-1.5">
            <span className={isPure ? "text-emerald-400" : "text-amber-400"}>
              {sv.purity.toFixed(4)}
            </span>
            <Badge tone={isPure ? "accent" : "warn"}>
              {isPure ? "Pure" : "Mixed"}
            </Badge>
          </div>
        </div>

        {/* Entropy */}
        <div className="space-y-0.5">
          <div className="text-ink-3 text-[11px] font-mono">Entropy S(ρ)</div>
          <div className="font-mono font-bold text-ink text-sm">
            {sv.entropy !== null && sv.entropy !== undefined ? `${sv.entropy.toFixed(4)} bits` : "—"}
          </div>
        </div>
      </div>

      {/* Main Tab Content */}
      {activeTab === "matrix" && (
        <div className="space-y-4">
          {result.density_matrix_truncated ? (
            <div className="p-4 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs">
              Density matrix dimension (D = {total_dim}) exceeds interactive full browser threshold (D &gt; 64). Reduced subsystem matrices and compact measurement distribution are active below.
            </div>
          ) : density_matrix ? (
            /* Centered Heatmap Surface with Top 'ket' and Left 'bra' matching Screenshot A */
            <div className="flex flex-col md:flex-row items-center justify-center gap-8 py-4 overflow-x-auto">
              {/* Matrix Core */}
              <div className="flex flex-col items-center">
                {/* 'ket' axis label centered at top */}
                <div className="text-xs font-mono font-semibold text-slate-400 tracking-widest mb-2 select-none">
                  ket
                </div>

                <div className="flex items-center">
                  {/* 'bra' axis label on the left rotated -90deg */}
                  <div className="text-xs font-mono font-semibold text-slate-400 tracking-widest -rotate-90 pr-3 select-none">
                    bra
                  </div>

                  {/* Grid Container */}
                  <div className="flex flex-col">
                    {/* Top Column Kets */}
                    <div className="flex" style={{ marginLeft: total_dim <= 4 ? 48 : 36 }}>
                      {basis_labels.map((colLabel, c) => (
                        <div
                          key={`col-${c}`}
                          style={{ width: cellSize }}
                          className="text-center font-mono text-[11px] font-medium text-slate-300 pb-2 truncate select-none"
                          title={colLabel}
                        >
                          {colLabel}
                        </div>
                      ))}
                    </div>

                    {/* Matrix Rows */}
                    {density_matrix.map((row, r) => (
                      <div key={`row-${r}`} className="flex items-center">
                        {/* Row Bra Label */}
                        <div
                          style={{ width: total_dim <= 4 ? 48 : 36 }}
                          className="text-right font-mono text-[11px] font-medium text-slate-300 pr-2 truncate select-none"
                          title={basis_labels[r]}
                        >
                          {basis_labels[r]}
                        </div>

                        {/* Row Cells */}
                        <div className="flex">
                          {row.map((cell, c) => {
                            const isHovered = hoveredCell?.r === r && hoveredCell?.c === c;
                            const isSelected = selectedCell?.r === r && selectedCell?.c === c;

                            // Calculate cell color based on mode
                            let bg = "";
                            let cellTitle = "";

                            if (viewMode === "mag") {
                              bg = viridisColor(cell.mag);
                              cellTitle = `|ρ| = ${cell.mag.toFixed(4)}`;
                            } else if (viewMode === "real") {
                              bg = signedColor(cell.real);
                              cellTitle = `Re(ρ) = ${cell.real.toFixed(4)}`;
                            } else if (viewMode === "imag") {
                              bg = signedColor(cell.imag);
                              cellTitle = `Im(ρ) = ${cell.imag.toFixed(4)}`;
                            } else {
                              const pInfo = phaseColor(cell.phase, cell.mag);
                              bg = pInfo.bg;
                              cellTitle = pInfo.undefinedPhase
                                ? "Phase undefined (|ρ| ≈ 0)"
                                : `∠ρ = ${formatPhasePi(cell.phase)}π rad`;
                            }

                            return (
                              <div
                                key={`cell-${r}-${c}`}
                                onMouseEnter={() =>
                                  setHoveredCell({
                                    r,
                                    c,
                                    val: cell,
                                    rowLabel: basis_labels[r],
                                    colLabel: basis_labels[c],
                                  })
                                }
                                onMouseLeave={() => setHoveredCell(null)}
                                onClick={() =>
                                  setSelectedCell({
                                    r,
                                    c,
                                    val: cell,
                                    rowLabel: basis_labels[r],
                                    colLabel: basis_labels[c],
                                  })
                                }
                                style={{
                                  width: cellSize,
                                  height: cellSize,
                                  backgroundColor: bg,
                                }}
                                className={cn(
                                  "cursor-pointer transition-transform border border-[#0d1527]/80 relative flex items-center justify-center",
                                  isHovered && "ring-2 ring-white/95 scale-105 z-20 shadow-lg",
                                  isSelected && !isHovered && "ring-2 ring-accent scale-105 z-10 shadow"
                                )}
                                title={`${formatBraket(basis_labels[r], basis_labels[c])}: ${cellTitle}`}
                              />
                            );
                          })}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Vertical Colorbar Section matching Screenshot A */}
              <div className="flex flex-col items-center">
                <span className="text-xs font-mono font-bold text-slate-300 mb-1.5">{colorbarLabel}</span>
                <div className="flex items-stretch gap-2">
                  {/* Color Gradient Bar */}
                  <div
                    style={{
                      height: Math.min(320, Math.max(160, cellSize * total_dim)),
                      width: 16,
                      background: colorbarGradient,
                    }}
                    className="rounded-sm border border-slate-700/80 shadow-inner"
                  />
                  {/* Numeric Ticks */}
                  <div
                    style={{ height: Math.min(320, Math.max(160, cellSize * total_dim)) }}
                    className="flex flex-col justify-between text-[11px] font-mono text-slate-400 select-none py-0.5"
                  >
                    {colorbarTicks.map((tickVal) => (
                      <div key={tickVal} className="flex items-center gap-1 leading-none">
                        <span className="w-1.5 h-[1px] bg-slate-600 inline-block" />
                        <span>
                          {viewMode === "phase"
                            ? tickVal === 1
                              ? "+π"
                              : tickVal === 0.5
                              ? "+π/2"
                              : tickVal === 0
                              ? "0"
                              : tickVal === -0.5
                              ? "-π/2"
                              : "-π"
                            : tickVal === 1
                            ? "1"
                            : tickVal === 0
                            ? "0"
                            : tickVal.toFixed(1)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          ) : null}

          {/* Interactive Matrix-Cell Inspection Card matching Screenshot A */}
          {activeInspected ? (
            <div className="flex flex-wrap items-center justify-between gap-3 text-xs font-mono text-slate-300 py-2.5 px-4 bg-[#0a0f1d] rounded-lg border border-accent/30 shadow-sm">
              <div className="flex items-center gap-2">
                <span className="text-accent font-bold text-sm">
                  {formatBraket(activeInspected.rowLabel, activeInspected.colLabel)}
                </span>
                <span className="text-slate-400">
                  : Re: <strong className="text-white">{activeInspected.val.real.toFixed(5)}</strong>, Im:{" "}
                  <strong className="text-white">{activeInspected.val.imag.toFixed(5)}</strong>
                </span>
              </div>
              <div className="flex items-center gap-4 text-slate-300">
                <span>
                  Magnitude: <strong className="text-amber-300">{activeInspected.val.mag.toFixed(5)}</strong>
                </span>
                <span>
                  Phase:{" "}
                  <strong className="text-cyan-300">
                    {activeInspected.val.mag < 0.005 ? "undefined" : `${formatPhasePi(activeInspected.val.phase)}π rad`}
                  </strong>
                </span>
                <Badge tone={activeInspected.r === activeInspected.c ? "accent" : "warn"}>
                  {activeInspected.r === activeInspected.c ? "Diagonal (Population)" : "Off-Diagonal (Coherence)"}
                </Badge>
              </div>
            </div>
          ) : (
            <div className="text-center font-mono text-xs text-slate-500 py-2 bg-[#090d18] rounded-lg border border-line/30">
              Hover over any matrix cell to inspect quantum amplitude & phase
            </div>
          )}

          {/* Educational Bell-State Coherence Annotation matching Screenshot A */}
          <div className="p-3.5 rounded-lg bg-[#0b101f]/70 border border-line/50 text-xs text-slate-400 leading-relaxed font-sans">
            <span className="font-semibold text-slate-300 font-mono mr-1">Scientific Note:</span>
            A Bell state lights up the off-diagonal |00⟩⟨11| (or |0,0⟩⟨d-1,d-1⟩) corners — those coherences are the direct signature of quantum superposition and entanglement. A classical statistical mixture exhibits only diagonal entries (populations) without off-diagonal coherences.
          </div>
        </div>
      )}

      {/* Measurement Distribution Tab */}
      {activeTab === "probabilities" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between text-xs text-ink-3">
            <span>Theoretical Born-rule state populations vs Sample counts ({samples ? Object.values(samples).reduce((a, b) => a + b, 0) : 0} shots)</span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 gap-2.5">
            {basis_labels.map((label, idx) => {
              const prob = probabilities ? (probabilities[label] ?? (probabilities as any)[idx] ?? 0.0) : 0.0;
              const count = samples ? samples[label] ?? 0 : 0;
              return (
                <div
                  key={label}
                  className="p-2.5 rounded-lg bg-[#0c1220] border border-line/50 flex flex-col items-center justify-center text-center space-y-1"
                >
                  <div className="font-mono text-xs font-bold text-accent">{label}</div>
                  <div className="text-sm font-mono font-semibold text-white">{(prob * 100).toFixed(1)}%</div>
                  <div className="text-[10px] text-ink-3 font-mono">{count} shots</div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Reduced Subsystems Tab */}
      {activeTab === "reduced" && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
            <div className="flex items-center gap-2">
              <span className="text-ink-3 font-mono">Select Subsystem Wire:</span>
              <div className="flex items-center gap-1">
                {Object.keys(reduced_states || {}).map((wireId) => (
                  <button
                    key={wireId}
                    type="button"
                    onClick={() => setSelectedReducedWire(wireId)}
                    className={`px-2.5 py-1 rounded text-xs font-mono transition-colors ${
                      selectedReducedWire === wireId
                        ? "bg-accent text-accent-ink font-bold shadow-sm"
                        : "bg-subtle text-ink-3 hover:text-ink"
                    }`}
                  >
                    {wireId}
                  </button>
                ))}
              </div>
            </div>

            {reduced_states && reduced_states[selectedReducedWire] && (
              <div className="flex items-center gap-3 text-ink-3 font-mono">
                <span>Purity: <strong className="text-white">{reduced_states[selectedReducedWire].purity.toFixed(4)}</strong></span>
                <span>Entropy: <strong className="text-white">{reduced_states[selectedReducedWire].entropy != null ? `${reduced_states[selectedReducedWire].entropy!.toFixed(4)} bits` : "—"}</strong></span>
              </div>
            )}
          </div>

          {reduced_states && reduced_states[selectedReducedWire] ? (
            <div className="flex flex-col items-center justify-center p-6 bg-[#090d18] rounded-xl border border-line/40">
              <div className="text-xs font-mono text-slate-400 mb-3">
                Reduced Density Matrix ρ_{selectedReducedWire} (Dimension d={reduced_states[selectedReducedWire].dimension})
              </div>
              <div className="flex flex-col gap-1">
                {reduced_states[selectedReducedWire].density_matrix.map((row, r) => (
                  <div key={r} className="flex gap-1">
                    {row.map((cell, c) => {
                      const isHighLuminance = cell.mag > 0.55;
                      return (
                        <div
                          key={c}
                          style={{
                            width: 52,
                            height: 52,
                            backgroundColor: viridisColor(cell.mag),
                            color: isHighLuminance ? "#070b14" : "#ffffff",
                          }}
                          className={cn(
                            "border border-[#0d1527] rounded-sm flex items-center justify-center font-mono text-[11px] shadow-sm transition-transform hover:scale-105",
                            isHighLuminance ? "font-extrabold" : "font-semibold text-white/95"
                          )}
                          title={`|ρ| = ${cell.mag.toFixed(4)} (Re: ${cell.real.toFixed(4)}, Im: ${cell.imag.toFixed(4)})`}
                        >
                          {cell.mag.toFixed(2)}
                        </div>
                      );
                    })}
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="p-6 text-center text-xs text-ink-3">No reduced subsystem data available.</div>
          )}
        </div>
      )}
    </div>
  );
};
