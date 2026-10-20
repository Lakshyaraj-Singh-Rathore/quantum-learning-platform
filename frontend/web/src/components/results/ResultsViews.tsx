/* The result views.
 *
 * Two deliberate choices:
 *
 * 1. Charts are plain SVG/CSS, not plotly. These are bars, arcs and grids —
 *    plotly would add ~1 MB of JavaScript for pictures that a handful of divs
 *    draw exactly. It also keeps every view verifiable without a browser.
 * 2. Every refusal message is carried over from Streamlit verbatim. When a view
 *    cannot be drawn (no statevector, too many qubits, no noisy run) the page
 *    says why in the same words, rather than showing an empty panel.
 *
 * The numbers come from the API unchanged; the maths behind the derived views
 * lives in src/lib/quantum.ts and is golden-tested against numpy.
 */
import { useState, useMemo } from "react";
import { ZoomIn, ZoomOut, RotateCcw, Maximize2, Minimize2 } from "lucide-react";
import { cn } from "../ui";
import {
  amplitudes,
  blochAngles,
  blochVector,
  cabs,
  formatAmplitude,
  ketExpression,
  probabilities,
  purity,
  qubitCount,
  reducedDensityMatrix,
  relativePhases,
  entanglementEntropy,
  type Complex,
} from "../../lib/quantum";
import type { RunResult } from "../../api/jobs";
import { InteractiveBlochSphere } from "./InteractiveBlochSphere";
import { phaseColour } from "./GeometryViews";

const MAX_HISTOGRAM_BARS = 32;
const DENSITY_QUBIT_LIMIT = 5;

export function Notice({ children }: { children: React.ReactNode }) {
  return (
    <p className="rounded-lg border border-line-soft bg-hover p-3 text-[13px] leading-relaxed text-ink-2">
      {children}
    </p>
  );
}

// ------------------------------------------------------------------ summary

export function ResultSummary({ result }: { result: RunResult }) {
  const meta = result.metadata;
  const rows: [string, string][] = [
    ["Backend", String(meta.engine ?? meta.backend ?? "-")],
    ["Shots", String(meta.shots ?? "-")],
    ["Qubits", String(meta.n_qubits ?? "-")],
    ["Runtime", `${Number(meta.runtime_seconds ?? 0).toFixed(3)}s`],
  ];
  return (
    <div className="flex flex-col gap-2">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {rows.map(([label, value]) => (
          <div key={label} className="rounded-lg border border-line-soft bg-hover/60 px-3 py-2">
            <p className="text-[11px] uppercase tracking-wide text-ink-3">{label}</p>
            <p className="text-sm font-medium text-ink">{value}</p>
          </div>
        ))}
      </div>
      <p className="text-xs text-ink-3">{meta.bit_order}</p>
      {(meta.warnings ?? []).map((w) => (
        <p key={w} className="text-[13px] text-warn">
          ⚠ {w}
        </p>
      ))}
    </div>
  );
}

// ------------------------------------------------------------------ gauges

function Gauge({
  value,
  title,
  subtitle,
  color,
  filterId,
}: {
  value: number;
  title: string;
  subtitle?: string;
  color: string;
  filterId: string;
}) {
  const radius = 75;
  const circumference = Math.PI * radius; // ~235.619
  const clamped = Math.max(0, Math.min(1, value));
  // Radial ticks at 0.2, 0.4, 0.6, 0.8 matching Screenshot 5
  const ticks = [0.2, 0.4, 0.6, 0.8];
  const cx = 140;
  const cy = 115;

  return (
    <div className="flex flex-col items-center justify-between rounded-xl border border-line-soft bg-raised/85 p-4 shadow-sm backdrop-blur-md transition-all hover:border-line relative group select-none">
      {/* Header */}
      <div className="text-center mb-1 w-full px-2">
        <h4 className="text-base font-semibold text-white tracking-tight">{title}</h4>
        {subtitle && (
          <p className="text-[11px] font-mono tracking-wider uppercase text-accent mt-0.5 opacity-90">
            {subtitle}
          </p>
        )}
      </div>

      <svg
        viewBox="0 0 280 135"
        className="w-full max-w-[260px] overflow-visible select-none"
        role="img"
        aria-label={`${title} ${value.toFixed(3)}`}
      >
        <defs>
          <filter id={filterId} x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="3.5" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* Outer Dark Track Groove */}
        <path
          d="M 65 115 A 75 75 0 0 1 215 115"
          fill="none"
          stroke="#090d16"
          strokeWidth="18"
          strokeLinecap="round"
        />
        <path
          d="M 65 115 A 75 75 0 0 1 215 115"
          fill="none"
          stroke="#131c2e"
          strokeWidth="14"
          strokeLinecap="round"
        />

        {/* Active Filled Arc */}
        <path
          d="M 65 115 A 75 75 0 0 1 215 115"
          fill="none"
          stroke={color}
          strokeWidth="13"
          strokeLinecap="round"
          strokeDasharray={`${clamped * circumference} ${circumference}`}
          filter={`url(#${filterId})`}
          className="transition-all duration-300 ease-out"
        />

        {/* Base 0 tick: notch & label "0 -" */}
        <text
          x="36"
          y="119"
          textAnchor="middle"
          fontSize="11"
          fontWeight="600"
          fill="#94a3b8"
          fontFamily="var(--font-mono), monospace"
        >
          0
        </text>
        <line x1="46" y1="115" x2="54" y2="115" stroke="#475569" strokeWidth="1.5" strokeLinecap="round" />

        {/* Radial ticks at 0.2, 0.4, 0.6, 0.8 matching Screenshot 5 */}
        {ticks.map((t) => {
          const theta = Math.PI * (1 - t);
          const cos = Math.cos(theta);
          const sin = Math.sin(theta);
          const x1 = cx + 83 * cos;
          const y1 = cy - 83 * sin;
          const x2 = cx + 90 * cos;
          const y2 = cy - 90 * sin;
          const xt = cx + 104 * cos;
          const yt = cy - 104 * sin + 3.5;

          return (
            <g key={t}>
              <line x1={x1} y1={y1} x2={x2} y2={y2} stroke="#475569" strokeWidth="1.5" strokeLinecap="round" />
              <text
                x={xt}
                y={yt}
                textAnchor="middle"
                fontSize="10.5"
                fontWeight="500"
                fill="#94a3b8"
                fontFamily="var(--font-mono), monospace"
              >
                {t.toFixed(1)}
              </text>
            </g>
          );
        })}

        {/* Base 1 tick: notch & label "- 1" */}
        <line x1="226" y1="115" x2="234" y2="115" stroke={clamped >= 0.99 ? color : "#475569"} strokeWidth="1.5" strokeLinecap="round" />
        <text
          x="244"
          y="119"
          textAnchor="middle"
          fontSize="11"
          fontWeight="600"
          fill="#94a3b8"
          fontFamily="var(--font-mono), monospace"
        >
          1
        </text>

        {/* Large Central Numeric Readout */}
        <text
          x={cx}
          y={cy - 6}
          textAnchor="middle"
          fontSize="36"
          fontWeight="700"
          fill="#ffffff"
          fontFamily="var(--font-mono), monospace"
          letterSpacing="-0.03em"
        >
          {value.toFixed(3)}
        </text>
      </svg>
    </div>
  );
}

export function MetricGauges({ result }: { result: RunResult }) {
  const meta = result.metadata;
  const metrics = (meta.metrics ?? {}) as Record<string, unknown>;
  if (Object.keys(metrics).length === 0) return null;

  const noisy = Boolean((meta.noise as { enabled?: boolean } | undefined)?.enabled);
  const entropy = Number(metrics.entanglement_entropy ?? 0);
  const concurrence = metrics.concurrence as number | undefined;
  const entangled = Boolean(metrics.entangled);

  // Fidelity and purity are rendered only when the backend reports them.
  const fidelity = metrics.fidelity as number | undefined;
  const purityValue = metrics.purity as number | undefined;

  return (
    <div className="flex flex-col gap-3 select-none">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Gauge
          value={entropy}
          title="Entanglement S"
          subtitle={`${entangled ? "ENTANGLED" : "SEPARABLE"}${
            concurrence !== undefined ? ` · C=${Number(concurrence).toFixed(2)}` : ""
          }`}
          color="#fbbf24"
          filterId="entropyGlow"
        />
        {fidelity !== undefined && (
          <Gauge
            value={Number(fidelity)}
            title="Fidelity"
            subtitle={noisy ? "F(ideal, noisy ρ)" : "F(ideal, noisy ρ)"}
            color="#2dd4bf"
            filterId="fidelityGlow"
          />
        )}
        {purityValue !== undefined && (
          <Gauge
            value={Number(purityValue)}
            title="Purity"
            subtitle="Tr(ρ²) · pure state"
            color="#a855f7"
            filterId="purityGlow"
          />
        )}
      </div>
      {noisy && (
        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-lg border border-line-soft bg-hover/60 px-3 py-2">
            <p className="text-[11px] uppercase tracking-wide text-ink-3">TV distance (ideal vs noisy)</p>
            <p className="text-sm font-medium text-ink">
              {Number(metrics.total_variation ?? 0).toFixed(3)}
            </p>
          </div>
          <div className="rounded-lg border border-line-soft bg-hover/60 px-3 py-2">
            <p className="text-[11px] uppercase tracking-wide text-ink-3">Shot leakage</p>
            <p className="text-sm font-medium text-ink">
              {(Number(metrics.shot_leakage ?? 0) * 100).toFixed(1)}%
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

// --------------------------------------------------------------- histogram

// --------------------------------------------------------------- histogram

export function Histogram({
  result,
  title = "Probability distribution",
  subtitle = "Bar color = relative phase. Z / S / T / RZ often change color, not height.",
  circuitLabel,
}: {
  result: RunResult;
  title?: string;
  subtitle?: string;
  circuitLabel?: string;
}) {
  const [asProbability, setAsProbability] = useState(true);
  const [colourByPhase, setColourByPhase] = useState(true);

  const counts = result.counts ?? {};
  const amps = amplitudes(result.statevector);
  const phases = amps ? relativePhases(amps) : null;
  const nQubits = amps ? qubitCount(amps) : ((result.metadata?.n_qubits as number | undefined) ?? 1);

  // If counts exist, use entries; if pure statevector simulation with 0 counts, populate from statevector
  let entries: [string, number][] = Object.entries(counts);
  if (entries.length === 0 && amps) {
    const probs = probabilities(amps);
    entries = probs
      .map((p, i) => [i.toString(2).padStart(nQubits, "0"), p * (result.metadata?.shots ? Number(result.metadata.shots) : 1024)] as [string, number])
      .filter(([, c]) => c > 1e-4);
  }
  entries.sort((a, b) => a[0].localeCompare(b[0])); // Canonical computational basis order

  const truncated = entries.length > MAX_HISTOGRAM_BARS;
  if (truncated) entries = entries.slice(0, MAX_HISTOGRAM_BARS);

  if (entries.length === 0) return <Notice>No counts or statevector in this result.</Notice>;

  const effectiveTotal = Object.values(counts).reduce((a, b) => a + b, 0) || (result.metadata?.shots ? Number(result.metadata.shots) : 1024);
  const yMax = asProbability ? 1.0 : Math.max(...entries.map(([, n]) => n), 1);

  // Derive Entanglement & Fidelity metrics for footer banner
  const meta = result.metadata ?? {};
  const metrics = (meta.metrics ?? {}) as Record<string, unknown>;
  const entropy = metrics.entanglement_entropy !== undefined ? Number(metrics.entanglement_entropy) : null;
  const fidelity = metrics.fidelity !== undefined ? Number(metrics.fidelity) : 1.0;
  const noisy = Boolean((meta.noise as { enabled?: boolean } | undefined)?.enabled);

  return (
    <div className="flex flex-col gap-4 font-sans select-none">
      {/* Title & Subtitle matching User Screenshot 2 */}
      <div className="border-b border-line-soft pb-2.5">
        <h3 className="text-base sm:text-lg font-bold tracking-tight text-white flex items-center justify-between">
          <span>{title}</span>
          <span className="text-xs font-mono font-medium text-ink-3">
            {entries.length} active basis state{entries.length === 1 ? "" : "s"}
          </span>
        </h3>
        <p className="text-xs text-ink-3 mt-0.5">
          {subtitle}
        </p>
        <div className="flex flex-wrap items-center justify-between gap-3 mt-2">
          {circuitLabel ? (
            <div className="text-xs font-semibold text-accent font-mono flex items-center gap-1.5">
              <span>Probabilities · {circuitLabel}</span>
            </div>
          ) : <div />}
          <div className="flex items-center gap-4 text-xs font-mono text-ink-3">
            <label className="flex items-center gap-1.5 cursor-pointer hover:text-ink">
              <input
                type="checkbox"
                checked={asProbability}
                onChange={(e) => setAsProbability(e.target.checked)}
                className="rounded accent-accent h-3.5 w-3.5"
              />
              Probability (%)
            </label>
            <label className="flex items-center gap-1.5 cursor-pointer hover:text-ink">
              <input
                type="checkbox"
                checked={colourByPhase}
                onChange={(e) => setColourByPhase(e.target.checked)}
                className="rounded accent-accent h-3.5 w-3.5"
              />
              Phase colors
            </label>
          </div>
        </div>
      </div>

      {/* Main Chart + Phase Colorbar Container */}
      <div className="flex items-stretch gap-4 sm:gap-6 bg-raised/40 p-4 rounded-xl border border-line-soft">
        {/* Left Side: Y-Axis + Bars + X-Axis */}
        <div className="flex-1 flex flex-col min-w-0">
          <div className="flex items-stretch h-[220px]">
            {/* Y-Axis Column */}
            <div className="flex flex-col justify-between items-end pr-2.5 text-[11px] font-mono text-ink-3 select-none w-10 shrink-0">
              <span className="text-[10px] text-ink-3 font-semibold mb-auto -mt-1">P(|x⟩)</span>
              <span>1.0</span>
              <span>0.8</span>
              <span>0.6</span>
              <span>0.4</span>
              <span>0.2</span>
              <span>0</span>
            </div>

            {/* Grid & Bars Container */}
            <div className="relative flex-1 flex items-end border-l border-b border-line-soft px-3 pt-4 pb-0 h-full">
              {/* Horizontal Reference Lines */}
              <div className="absolute inset-0 pointer-events-none flex flex-col justify-between opacity-15">
                <div className="border-b border-dashed border-white w-full" />
                <div className="border-b border-dashed border-white w-full" />
                <div className="border-b border-dashed border-white w-full" />
                <div className="border-b border-dashed border-white w-full" />
                <div className="border-b border-dashed border-white w-full" />
                <div className="border-b border-white w-full opacity-60" />
              </div>

              {/* Bars Row */}
              <div className="relative z-10 w-full flex items-end justify-around gap-2 sm:gap-4 h-full">
                {entries.map(([bits, n]) => {
                  const prob = n / effectiveTotal;
                  const ratio = Math.max(0, Math.min(1, prob / (asProbability ? 1.0 : yMax)));
                  const barHeightPct = Math.max(4, ratio * 100);
                  const index = parseInt(bits, 2);
                  const phaseRad = phases && index < phases.length ? phases[index] : 0;
                  const phaseDeg = (phaseRad * 180) / Math.PI;
                  const barBg = colourByPhase ? phaseColour(phaseDeg) : "var(--accent, #3b82f6)";

                  return (
                    <div
                      key={bits}
                      className="group relative flex-1 flex flex-col items-center justify-end h-full max-w-[120px]"
                    >
                      {/* Probability percentage label on top of bar */}
                      <span className="mb-1 text-[11px] sm:text-xs font-bold font-mono text-ink-2 tabular-nums">
                        {(prob * 100).toFixed(1)}%
                      </span>

                      {/* The Bar */}
                      <div
                        className="w-full rounded-t-sm shadow-md transition-all duration-200 hover:brightness-110 cursor-pointer relative"
                        style={{
                          height: `${barHeightPct}%`,
                          backgroundColor: barBg,
                          boxShadow: `0 0 16px -2px ${barBg}44`,
                        }}
                      >
                        {/* Hover Tooltip */}
                        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:flex flex-col items-center pointer-events-none z-30">
                          <div className="bg-[#0f172a] border border-line-soft text-white text-[11px] font-mono px-2.5 py-1.5 rounded-lg shadow-xl whitespace-nowrap">
                            <span className="font-bold text-accent">|{bits}⟩</span>: P = {prob.toFixed(4)} ({n} shots)
                            <div className="text-[10px] text-ink-3">
                              rel. phase: {phaseDeg >= 0 ? "+" : ""}{phaseDeg.toFixed(1)}° ({phaseRad >= 0 ? "+" : ""}{phaseRad.toFixed(3)} rad)
                            </div>
                          </div>
                          <div className="w-2 h-2 bg-[#0f172a] border-r border-b border-line-soft rotate-45 -mt-1" />
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* X-Axis Labels */}
          <div className="flex ml-10 pl-3 pt-2">
            <div className="w-full flex justify-around gap-2 sm:gap-4">
              {entries.map(([bits]) => (
                <span
                  key={bits}
                  className="flex-1 max-w-[120px] text-center font-mono text-xs font-bold text-ink hover:text-accent transition-colors"
                >
                  |{bits}⟩
                </span>
              ))}
            </div>
          </div>
          <span className="text-[11px] font-mono text-ink-3 text-center mt-1">
            basis state (q0 rightmost)
          </span>
        </div>

        {/* Right Side: Vertical Relative Phase Color Scale Bar */}
        <div className="flex items-center gap-2 select-none shrink-0 py-2">
          {/* Color Gradient Strip */}
          <div className="relative w-5 sm:w-6 h-[190px] rounded-sm overflow-hidden border border-white/20 shadow-inner">
            <div
              className="w-full h-full"
              style={{
                background: "linear-gradient(to bottom, #3dd6c6 0%, #ff5d5d 25%, #e17cff 50%, #5b9dff 75%, #3dd6c6 100%)",
              }}
            />
          </div>

          {/* Tick Labels */}
          <div className="h-[190px] flex flex-col justify-between text-[10px] sm:text-[11px] font-mono text-ink-3">
            <span>+π</span>
            <span>+π/2</span>
            <span className="font-semibold text-white">0</span>
            <span>-π/2</span>
            <span>-π</span>
          </div>

          {/* Rotated Axis Label */}
          <div
            className="text-[11px] font-mono font-medium text-ink-3 uppercase tracking-wider select-none pl-1"
            style={{ writingMode: "vertical-rl", transform: "rotate(180deg)" }}
          >
            rel. phase
          </div>
        </div>
      </div>

      {/* Footer Metrics Banner matching Screenshot 2 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 pt-1">
        <div className="flex flex-col p-3 rounded-xl border border-line-soft bg-raised/30">
          <span className="text-[11px] font-semibold text-ink-3 uppercase tracking-wider">Entanglement</span>
          <span className="text-xs font-mono font-bold text-ink mt-0.5">
            {nQubits < 2
              ? "need 2+ qubits · N/A"
              : entropy !== null && entropy > 0.05
              ? `Entangled (S = ${entropy.toFixed(3)})`
              : "Separable (S = 0.000)"}
          </span>
        </div>

        <div className="flex flex-col p-3 rounded-xl border border-line-soft bg-raised/30">
          <span className="text-[11px] font-semibold text-ink-3 uppercase tracking-wider">Fidelity</span>
          <span className="text-xs font-mono font-bold text-ink mt-0.5">
            F(ideal, noisy ρ) = {Number(fidelity).toFixed(3)}
          </span>
        </div>

        <div className="flex flex-col p-3 rounded-xl border border-line-soft bg-raised/30 justify-center">
          <span className="text-[10px] text-ink-3 leading-relaxed">
            {noisy
              ? "Noise active: shot leakage and thermal decay computed."
              : "Enable noise to see purity of the mixed state and shot leakage."}
          </span>
        </div>
      </div>
    </div>
  );
}

// ------------------------------------------------------------------ tables

export function ProbabilityTable({ result }: { result: RunResult }) {
  const counts = result.counts ?? {};
  const total = Object.values(counts).reduce((a, b) => a + b, 0) || 1;
  const rows = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  if (rows.length === 0) return <Notice>No counts in this result.</Notice>;
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b border-line text-left text-[11px] uppercase tracking-wide text-ink-3">
          <th className="py-2 pr-3 font-medium">State</th>
          <th className="py-2 pr-3 text-right font-medium">Count</th>
          <th className="py-2 pr-3 text-right font-medium">Probability</th>
          <th className="py-2 text-right font-medium">Percent</th>
        </tr>
      </thead>
      <tbody>
        {rows.map(([bits, n]) => (
          <tr key={bits} className="border-b border-line-soft/60">
            <td className="py-1.5 pr-3 font-mono text-[13px]">{bits}</td>
            <td className="py-1.5 pr-3 text-right tabular-nums">{n}</td>
            <td className="py-1.5 pr-3 text-right tabular-nums">{(n / total).toFixed(6)}</td>
            <td className="py-1.5 text-right tabular-nums">{((n / total) * 100).toFixed(3)}%</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function StatevectorTable({ result }: { result: RunResult }) {
  const amps = amplitudes(result.statevector);
  if (!amps) return <Notice>Phase table needs a statevector.</Notice>;
  const n = qubitCount(amps);
  const probs = probabilities(amps);
  const phases = relativePhases(amps);
  const ket = ketExpression(amps);

  const rows = amps
    .map((a, i) => ({ i, a, p: probs[i], phase: phases[i] }))
    .filter((row) => row.p > 1e-10);

  return (
    <div className="flex flex-col gap-3">
      {ket && (
        <div className="rounded-lg border border-line-soft bg-hover/60 p-3">
          <p className="font-mono text-[13px] leading-relaxed text-ink">
            |ψ⟩ = {ket.expression}
          </p>
          {ket.hidden > 0 && (
            <p className="mt-1 text-xs text-ink-3">
              {ket.hidden} further term(s) with smaller amplitudes are not shown.
            </p>
          )}
          <p className="mt-1 text-xs text-ink-3">
            Amplitudes are complex numbers; each squared magnitude is the probability of
            measuring that basis state.
          </p>
        </div>
      )}
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-line text-left text-[11px] uppercase tracking-wide text-ink-3">
            <th className="py-2 pr-3 font-medium">State</th>
            <th className="py-2 pr-3 font-medium">Amplitude</th>
            <th className="py-2 pr-3 text-right font-medium">Probability</th>
            <th className="py-2 pr-3 text-right font-medium">Rel. phase (rad)</th>
            <th className="py-2 text-right font-medium">Rel. phase (deg)</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(({ i, a, p, phase }) => (
            <tr key={i} className="border-b border-line-soft/60">
              <td className="py-1.5 pr-3 font-mono text-[13px]">
                |{i.toString(2).padStart(n, "0")}⟩
              </td>
              <td className="py-1.5 pr-3 font-mono text-[13px]">{formatAmplitude(a)}</td>
              <td className="py-1.5 pr-3 text-right tabular-nums">{p.toFixed(6)}</td>
              <td className="py-1.5 pr-3 text-right tabular-nums">{phase.toFixed(6)}</td>
              <td className="py-1.5 text-right tabular-nums">
                {((phase * 180) / Math.PI).toFixed(2)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="text-xs text-ink-3">
        Phases are <strong className="text-ink-2">relative</strong> to the first populated
        state; a global phase is physically unobservable.
      </p>
    </div>
  );
}

// ------------------------------------------------------- comparison charts

// ------------------------------------------------------- comparison charts

function GroupedBars({
  labels,
  series,
  yLabel = "probability",
  height = 240,
}: {
  labels: string[];
  series: { name: string; values: number[]; color: string }[];
  yLabel?: string;
  height?: number;
}) {
  const yTicks = [1.0, 0.8, 0.6, 0.4, 0.2, 0];

  return (
    <div className="flex flex-col gap-3 font-sans select-none">
      {/* Top Legend */}
      <div className="flex flex-wrap items-center gap-6 text-xs font-mono font-semibold">
        {series.map((s) => (
          <span key={s.name} className="flex items-center gap-2 text-ink hover:text-white transition-colors">
            <span
              className="h-3 w-3 rounded-xs shadow-sm"
              style={{ backgroundColor: s.color, boxShadow: `0 0 10px ${s.color}66` }}
            />
            {s.name}
          </span>
        ))}
      </div>

      {/* Main Chart Area */}
      <div className="flex items-stretch pt-4" style={{ height: `${height}px` }}>
        {/* Y-Axis Column */}
        <div className="flex flex-col justify-between items-end pr-2.5 text-[11px] font-mono text-ink-3 select-none w-12 shrink-0">
          <span className="text-[10px] text-ink-3 font-semibold mb-auto -mt-2">{yLabel}</span>
          {yTicks.map((t) => (
            <span key={t}>{t === 0 ? "0" : t.toFixed(1)}</span>
          ))}
        </div>

        {/* Grid & Grouped Bars Container */}
        <div className="relative flex-1 flex items-end border-l border-b border-line-soft px-4 pt-4 pb-0 h-full">
          {/* Horizontal Reference Lines */}
          <div className="absolute inset-0 pointer-events-none flex flex-col justify-between opacity-15">
            <div className="border-b border-dashed border-white w-full" />
            <div className="border-b border-dashed border-white w-full" />
            <div className="border-b border-dashed border-white w-full" />
            <div className="border-b border-dashed border-white w-full" />
            <div className="border-b border-dashed border-white w-full" />
            <div className="border-b border-white w-full opacity-60" />
          </div>

          {/* Grouped Bars per Label */}
          <div className="relative z-10 w-full flex items-end justify-around gap-4 sm:gap-8 h-full">
            {labels.map((label, i) => (
              <div
                key={label}
                className="flex-1 flex items-end justify-center gap-1 sm:gap-2 h-full max-w-[140px]"
              >
                {series.map((s) => {
                  const val = Math.max(0, s.values[i]);
                  const ratio = Math.max(0, Math.min(1, val / 1.0));
                  const barHeightPct = Math.max(3, ratio * 100);

                  return (
                    <div
                      key={s.name}
                      className="group relative flex-1 flex flex-col items-center justify-end h-full"
                    >
                      <div
                        className="w-full rounded-t-sm shadow-md transition-all duration-200 hover:brightness-125 cursor-pointer"
                        style={{
                          height: `${barHeightPct}%`,
                          backgroundColor: s.color,
                          boxShadow: `0 0 12px ${s.color}44`,
                        }}
                      >
                        {/* Hover Tooltip */}
                        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:flex flex-col items-center pointer-events-none z-30">
                          <div className="bg-[#0f172a] border border-line-soft text-white text-[11px] font-mono px-2.5 py-1.5 rounded-lg shadow-xl whitespace-nowrap">
                            <span className="font-bold text-accent">{label}</span>: {val.toFixed(4)} ({s.name})
                          </div>
                          <div className="w-2 h-2 bg-[#0f172a] border-r border-b border-line-soft rotate-45 -mt-1" />
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* X-Axis Labels */}
      <div className="flex ml-12 pl-4 pt-2">
        <div className="w-full flex justify-around gap-4 sm:gap-8">
          {labels.map((label) => (
            <span
              key={label}
              className="flex-1 max-w-[140px] text-center font-mono text-xs font-bold text-ink hover:text-accent transition-colors"
            >
              |{label}⟩
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

interface BornVsShotsEntry {
  bitstring: string;
  bornProb: number;
  sampledProb: number;
  count: number;
  delta: number;
}

export function BornVsShots({ result }: { result: RunResult }) {
  const [hoveredBitstring, setHoveredBitstring] = useState<string | null>(null);
  const [showAllStates, setShowAllStates] = useState<boolean>(false);

  const amps = amplitudes(result.statevector);
  const counts = result.counts ?? {};
  const totalShots =
    Object.values(counts).reduce((acc, c) => acc + c, 0) ||
    Number(result.metadata?.shots || 0);

  const nQubits = amps
    ? qubitCount(amps)
    : Number(result.metadata?.n_qubits || 0) ||
      Object.keys(counts)[0]?.length ||
      2;

  // Compute exact Born probabilities from statevector or fallback to result.probabilities
  const exactMap = useMemo(() => {
    const map: Record<string, number> = {};
    if (amps && amps.length > 0) {
      const probs = probabilities(amps);
      const width = qubitCount(amps);
      probs.forEach((p, idx) => {
        const bs = idx.toString(2).padStart(width, "0");
        map[bs] = p;
      });
    } else if (result.probabilities) {
      Object.entries(result.probabilities).forEach(([bs, p]) => {
        map[bs] = Number(p) || 0;
      });
    }
    return map;
  }, [result.statevector, result.probabilities, amps]);

  const hasExactBorn = Object.keys(exactMap).length > 0;
  const hasCounts = totalShots > 0 && Object.keys(counts).length > 0;

  // Build unified comparison entries
  const { entries, tvd, maxError, classicalFidelity } = useMemo(() => {
    const allKeys = new Set<string>([
      ...Object.keys(exactMap),
      ...Object.keys(counts),
    ]);

    // Ensure full basis representation for small qubit counts (<= 4 qubits)
    if (nQubits > 0 && nQubits <= 4 && allKeys.size < (1 << nQubits)) {
      for (let i = 0; i < (1 << nQubits); i++) {
        allKeys.add(i.toString(2).padStart(nQubits, "0"));
      }
    }

    const rawEntries: BornVsShotsEntry[] = Array.from(allKeys)
      .sort()
      .map((bs) => {
        const bornProb = exactMap[bs] ?? 0;
        const count = counts[bs] ?? 0;
        const sampledProb = totalShots > 0 ? count / totalShots : 0;
        return {
          bitstring: bs,
          bornProb,
          sampledProb,
          count,
          delta: sampledProb - bornProb,
        };
      });

    // Statistical metrics across the entire distribution
    let l1Sum = 0;
    let maxErr = 0;
    let bhattacharyya = 0;

    for (const item of rawEntries) {
      const absDiff = Math.abs(item.bornProb - item.sampledProb);
      l1Sum += absDiff;
      if (absDiff > maxErr) maxErr = absDiff;
      bhattacharyya += Math.sqrt(Math.max(0, item.bornProb * item.sampledProb));
    }

    const computedTvd = 0.5 * l1Sum;
    const computedFidelity = Math.min(1, bhattacharyya * bhattacharyya);

    // Filter non-trivial states if basis is large
    const filtered = showAllStates
      ? rawEntries.slice(0, 32)
      : rawEntries.filter((e) => e.bornProb > 1e-4 || e.sampledProb > 1e-4);

    const displayList =
      filtered.length > 0 ? filtered.slice(0, 24) : rawEntries.slice(0, 16);

    return {
      entries: displayList,
      tvd: computedTvd,
      maxError: maxErr,
      classicalFidelity: computedFidelity,
    };
  }, [exactMap, counts, totalShots, nQubits, showAllStates]);

  if (!hasExactBorn && !hasCounts) {
    return (
      <Notice>
        Needs both a statevector and measurement counts to compare Born rule probabilities against finite sampling.
      </Notice>
    );
  }

  const maxProb = Math.max(
    0.05,
    ...entries.map((e) => Math.max(e.bornProb, e.sampledProb))
  );
  const yMax = Math.min(1.0, Math.ceil(maxProb * 10) / 10 + 0.05);
  const expectedShotNoise = totalShots > 0 ? 1 / Math.sqrt(totalShots) : 0;
  const activeEntry =
    entries.find((e) => e.bitstring === hoveredBitstring) || null;

  return (
    <div className="flex flex-col gap-4 font-sans select-none">
      {/* Header & Legend */}
      <div className="border-b border-line-soft pb-2.5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-accent font-mono">
                Measurement Statistics
              </span>
              <span className="rounded-full border border-accent/30 bg-accent-soft px-2 py-0.5 font-mono text-[10px] text-accent-ink">
                {totalShots > 0 ? `${totalShots.toLocaleString()} shots` : "Analytical Only"}
              </span>
            </div>
            <h3 className="text-base sm:text-lg font-bold tracking-tight text-white mt-0.5">
              Born Rule vs. Finite Shot Sampling
            </h3>
          </div>

          <div className="flex flex-wrap items-center gap-4 text-xs font-mono">
            <div className="flex items-center gap-2">
              <span
                className="inline-block h-3 w-3 rounded-xs shadow-sm"
                style={{
                  background: "linear-gradient(180deg, #5eead4 0%, #14b8a6 100%)",
                  boxShadow: "0 0 8px rgba(45,212,191,0.45)",
                }}
              />
              <span className="text-ink">
                Exact Born <span className="text-ink-3">P(x) = |ψₓ|²</span>
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span
                className="inline-block h-3 w-3 rounded-xs shadow-sm"
                style={{
                  background: "linear-gradient(180deg, #c4b5fd 0%, #8b5cf6 100%)",
                  boxShadow: "0 0 8px rgba(167,139,250,0.45)",
                }}
              />
              <span className="text-ink">
                Sampled <span className="text-ink-3">cₓ / N</span>
              </span>
            </div>
            {nQubits <= 5 && (
              <button
                type="button"
                onClick={() => setShowAllStates((v) => !v)}
                className="rounded-md border border-line-soft bg-raised/60 px-2.5 py-1 text-[11px] font-medium text-ink-2 hover:text-white hover:border-line-focus transition-colors cursor-pointer"
              >
                {showAllStates ? "Hide Zero States" : "Show All Basis States"}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Main Chart Viewport */}
      <div className="relative rounded-xl border border-line-soft bg-raised/40 p-4 pt-6">
        {/* Horizontal Grid Lines */}
        <div className="pointer-events-none absolute inset-x-12 top-6 bottom-12 flex flex-col justify-between opacity-15">
          {[1, 0.75, 0.5, 0.25, 0].map((frac) => (
            <div key={frac} className="border-b border-dashed border-white w-full" />
          ))}
        </div>

        {/* Grouped Bars Track */}
        <div
          className="relative z-10 ml-8 flex items-end justify-around gap-2 sm:gap-4 overflow-x-auto pb-2"
          style={{ minHeight: "240px" }}
        >
          {entries.map((entry) => {
            const bornHeightPx = Math.max(
              entry.bornProb > 0 ? 6 : 2,
              Math.round((entry.bornProb / yMax) * 180)
            );
            const sampledHeightPx = Math.max(
              entry.sampledProb > 0 ? 6 : 2,
              Math.round((entry.sampledProb / yMax) * 180)
            );
            const isHovered = hoveredBitstring === entry.bitstring;
            const deltaPct = entry.delta * 100;

            return (
              <div
                key={entry.bitstring}
                onMouseEnter={() => setHoveredBitstring(entry.bitstring)}
                onMouseLeave={() => setHoveredBitstring(null)}
                className={`group flex min-w-[64px] flex-1 max-w-[120px] flex-col items-center rounded-lg px-2 pt-2 pb-1 transition-colors ${
                  isHovered ? "bg-white/[0.05]" : "hover:bg-white/[0.02]"
                }`}
              >
                {/* Delta pill on hover or significant gap */}
                <div className="mb-1.5 h-4 flex items-center justify-center">
                  {hasExactBorn && hasCounts && (entry.bornProb > 0.001 || entry.sampledProb > 0.001) && (
                    <span
                      className={`rounded px-1.5 py-0.5 font-mono text-[9px] font-semibold transition-opacity ${
                        Math.abs(deltaPct) < 0.05
                          ? "bg-ok/10 text-ok"
                          : deltaPct > 0
                          ? "bg-purple-500/15 text-purple-300"
                          : "bg-amber-500/15 text-amber-300"
                      }`}
                    >
                      {deltaPct >= 0 ? `+${deltaPct.toFixed(1)}%` : `${deltaPct.toFixed(1)}%`}
                    </span>
                  )}
                </div>

                {/* Paired Bar Columns */}
                <div
                  className="flex w-full items-end justify-center gap-1.5 sm:gap-2 border-b border-line-soft px-1"
                  style={{ height: "190px" }}
                >
                  {/* Exact Born Bar */}
                  <div className="flex flex-col items-center">
                    <span className="mb-1 font-mono text-[10px] font-bold text-teal-300 tabular-nums">
                      {(entry.bornProb * 100).toFixed(1)}%
                    </span>
                    <div
                      className="w-4 sm:w-5 rounded-t-sm transition-all duration-300 cursor-pointer hover:brightness-110"
                      style={{
                        height: `${bornHeightPx}px`,
                        background:
                          entry.bornProb > 0
                            ? "linear-gradient(180deg, #5eead4 0%, #14b8a6 55%, #0f766e 100%)"
                            : "rgba(255,255,255,0.06)",
                        boxShadow:
                          entry.bornProb > 0.01
                            ? "0 0 12px rgba(45, 212, 191, 0.35), inset 0 1px 0 rgba(255,255,255,0.4)"
                            : "none",
                      }}
                    />
                  </div>

                  {/* Sampled Shots Bar */}
                  <div className="flex flex-col items-center">
                    <span className="mb-1 font-mono text-[10px] font-bold text-violet-300 tabular-nums">
                      {(entry.sampledProb * 100).toFixed(1)}%
                    </span>
                    <div
                      className="w-4 sm:w-5 rounded-t-sm transition-all duration-300 cursor-pointer hover:brightness-110"
                      style={{
                        height: `${sampledHeightPx}px`,
                        background:
                          entry.sampledProb > 0
                            ? "linear-gradient(180deg, #c4b5fd 0%, #8b5cf6 55%, #5b21b6 100%)"
                            : "rgba(255,255,255,0.06)",
                        boxShadow:
                          entry.sampledProb > 0.01
                            ? "0 0 12px rgba(167, 139, 250, 0.35), inset 0 1px 0 rgba(255,255,255,0.4)"
                            : "none",
                      }}
                    />
                  </div>
                </div>

                {/* Basis State Label */}
                <div className="mt-2 flex flex-col items-center">
                  <span className="rounded border border-line-soft bg-subtle px-2 py-0.5 font-mono text-xs font-semibold text-ink">
                    |{entry.bitstring}⟩
                  </span>
                  {hasCounts && (
                    <span className="mt-0.5 font-mono text-[10px] text-ink-3">
                      {entry.count} {entry.count === 1 ? "shot" : "shots"}
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Statistical Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
        <div className="rounded-xl border border-line-soft bg-raised/30 p-3">
          <div className="text-[10px] font-semibold uppercase tracking-wider text-ink-3">
            Total Variation Distance
          </div>
          <div className="mt-1 flex items-baseline gap-2">
            <span className="font-mono text-base font-bold text-ink">
              {(tvd * 100).toFixed(2)}%
            </span>
            <span className="text-[11px] text-ink-3">
              {tvd < 0.03 ? "High convergence" : tvd < 0.08 ? "Moderate variance" : "Shot-limited"}
            </span>
          </div>
        </div>

        <div
          className="rounded-xl border border-line-soft bg-raised/30 p-3"
          title="Classical distribution fidelity between sampled shots and theoretical Born probabilities: F = (Σ √(P_exact · P_sample))² (Bhattacharyya coefficient)"
        >
          <div className="text-[10px] font-semibold uppercase tracking-wider text-ink-3">
            Distribution Fidelity
          </div>
          <div className="mt-1 flex items-baseline gap-2">
            <span className="font-mono text-base font-bold text-ok">
              {(classicalFidelity * 100).toFixed(2)}%
            </span>
            <span className="text-[11px] text-ink-3">
              {classicalFidelity > 0.99 ? "Exact agreement" : classicalFidelity > 0.95 ? "High overlap" : "Sampling variance"}
            </span>
          </div>
        </div>

        <div className="rounded-xl border border-line-soft bg-raised/30 p-3">
          <div className="text-[10px] font-semibold uppercase tracking-wider text-ink-3">
            Max Basis Error |ΔP|
          </div>
          <div className="mt-1 flex items-baseline gap-2">
            <span className="font-mono text-base font-bold text-violet-300">
              {(maxError * 100).toFixed(2)}%
            </span>
            <span className="text-[11px] text-ink-3">
              1/√N ≈ {(expectedShotNoise * 100).toFixed(1)}%
            </span>
          </div>
        </div>

        <div className="rounded-xl border border-line-soft bg-raised/30 p-3">
          <div className="text-[10px] font-semibold uppercase tracking-wider text-ink-3">
            {activeEntry ? `Inspecting |${activeEntry.bitstring}⟩` : "Physical Takeaway"}
          </div>
          {activeEntry ? (
            <div className="mt-1 font-mono text-xs text-ink">
              Born {(activeEntry.bornProb * 100).toFixed(2)}% · Sampled{" "}
              {(activeEntry.sampledProb * 100).toFixed(2)}% ({activeEntry.count})
            </div>
          ) : (
            <div className="mt-1 text-[11px] leading-snug text-ink-2">
              Finite shots cause <span className="font-mono text-teal-300">~1/√N</span> projection noise, distinct from T₁/T₂ decoherence.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export function IdealVsNoisy({ result }: { result: RunResult }) {
  const idealCounts = result.metadata.ideal_counts as Record<string, number> | undefined;
  if (!idealCounts) {
    return (
      <Notice>
        Enable the noise model on the Qiskit Aer or CUDA-Q backend to compare an ideal run
        against a noisy one.
      </Notice>
    );
  }
  const noisyCounts = result.counts ?? {};
  const totalIdeal = Object.values(idealCounts).reduce((a, b) => a + b, 0) || 1;
  const totalNoisy = Object.values(noisyCounts).reduce((a, b) => a + b, 0) || 1;
  const labels = [...new Set([...Object.keys(idealCounts), ...Object.keys(noisyCounts)])].sort();
  const ideal = labels.map((k) => (idealCounts[k] ?? 0) / totalIdeal);
  const noisy = labels.map((k) => (noisyCounts[k] ?? 0) / totalNoisy);

  return (
    <div className="flex flex-col gap-4">
      <GroupedBars
        labels={labels}
        series={[
          { name: "Ideal", values: ideal, color: "var(--accent)" },
          { name: "Noisy", values: noisy, color: "var(--danger)" },
        ]}
      />
      <div>
        <p className="mb-2 text-[13px] font-medium text-ink">
          Noisy minus ideal (positive = noise added weight here)
        </p>
        <GroupedBars
          labels={labels}
          height={180}
          series={[
            {
              name: "difference",
              values: noisy.map((v, i) => v - ideal[i]),
              color: "#f59e0b",
            },
          ]}
        />
      </div>
    </div>
  );
}

// -------------------------------------------------------- density matrix

// -------------------------------------------------------- viridis colormap

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

// -------------------------------------------------------- density matrix

export function DensityMatrix({ result }: { result: RunResult }) {
  const amps = amplitudes(result.statevector);
  if (!amps) return <Notice>Density matrix needs a statevector.</Notice>;
  const n = qubitCount(amps);
  if (n > DENSITY_QUBIT_LIMIT) {
    return <Notice>Density matrix view is limited to {DENSITY_QUBIT_LIMIT} qubits.</Notice>;
  }
  const size = amps.length;
  const rawLabels = Array.from({ length: size }, (_, i) => i.toString(2).padStart(n, "0"));

  const [zoom, setZoom] = useState(1);
  const [fullscreen, setFullscreen] = useState(false);
  const [hoveredCell, setHoveredCell] = useState<{
    r: number;
    c: number;
    val: number;
    real: number;
    imag: number;
  } | null>(null);

  // Responsive cell size matching Screenshot 4
  const baseCellSize = n <= 2 ? 64 : n === 3 ? 42 : n === 4 ? 24 : 14;
  const cellSize = Math.round(baseCellSize * zoom);

  const meta = result.metadata || {};
  const circuitTitle = (meta.circuit_name as string) || (meta.title as string) || (meta.label as string) || "";
  const displayTitle = circuitTitle ? `Ideal |ρ| · ${circuitTitle}` : "Ideal |ρ|";

  // Colorbar ticks matching Screenshot 4: 1, 0.8, 0.6, 0.4, 0.2, 0
  const colorbarTicks = [1, 0.8, 0.6, 0.4, 0.2, 0];

  return (
    <div
      className={cn(
        "flex flex-col gap-4 rounded-xl border border-line-soft bg-raised/85 p-5 shadow-sm backdrop-blur-md select-none relative transition-all",
        fullscreen && "fixed inset-6 z-50 bg-[#090d16]/95 border-accent/40 shadow-2xl overflow-auto"
      )}
    >
      {/* Top Header & Toolbar matching Screenshot 4 */}
      <div className="flex items-center justify-between border-b border-line-soft/60 pb-3">
        <h3 className="text-sm font-semibold text-white tracking-wide font-mono">
          {displayTitle}
        </h3>
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => setZoom((z) => Math.min(2, +(z + 0.25).toFixed(2)))}
            title="Zoom In"
            className="p-1.5 rounded hover:bg-hover text-ink-3 hover:text-white transition-colors"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <button
            type="button"
            onClick={() => setZoom((z) => Math.max(0.75, +(z - 0.25).toFixed(2)))}
            title="Zoom Out"
            className="p-1.5 rounded hover:bg-hover text-ink-3 hover:text-white transition-colors"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <button
            type="button"
            onClick={() => setZoom(1)}
            title="Reset View"
            className="p-1.5 rounded hover:bg-hover text-ink-3 hover:text-white transition-colors"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
          <button
            type="button"
            onClick={() => setFullscreen((f) => !f)}
            title={fullscreen ? "Exit Fullscreen" : "Fullscreen"}
            className="p-1.5 rounded hover:bg-hover text-ink-3 hover:text-white transition-colors"
          >
            {fullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Main Heatmap Area with Centered Grid and Right Colorbar matching Screenshot 4 */}
      <div className="flex flex-col md:flex-row items-center justify-center gap-8 py-2 overflow-x-auto">
        {/* Heatmap Section */}
        <div className="flex flex-col items-center">
          {/* "ket" axis label centered on top */}
          <div className="text-xs font-mono font-medium text-slate-400 tracking-wider mb-2">
            ket
          </div>

          <div className="flex items-center">
            {/* "bra" axis label on the left */}
            <div className="text-xs font-mono font-medium text-slate-400 tracking-wider -rotate-90 pr-2 select-none">
              bra
            </div>

            {/* Matrix Table with Row & Col Headers */}
            <div className="flex flex-col">
              {/* Column Kets Header */}
              <div className="flex" style={{ marginLeft: n <= 2 ? 48 : 36 }}>
                {rawLabels.map((l) => (
                  <div
                    key={l}
                    style={{ width: cellSize }}
                    className="text-center font-mono text-[11px] font-medium text-slate-300 pb-2 truncate"
                    title={`|${l}⟩`}
                  >
                    |{l}⟩
                  </div>
                ))}
              </div>

              {/* Matrix Rows */}
              {rawLabels.map((rowLabel, r) => (
                <div key={rowLabel} className="flex items-center">
                  {/* Row Bra Label */}
                  <div
                    style={{ width: n <= 2 ? 48 : 36 }}
                    className="text-right font-mono text-[11px] font-medium text-slate-300 pr-2 truncate"
                    title={`|${rowLabel}⟩`}
                  >
                    |{rowLabel}⟩
                  </div>

                  {/* Row Cells */}
                  <div className="flex">
                    {rawLabels.map((colLabel, c) => {
                      const aR = amps[r];
                      const aC = amps[c];
                      const real = aR.re * aC.re + aR.im * aC.im;
                      const imag = aR.im * aC.re - aR.re * aC.im;
                      const val = cabs({ re: real, im: imag });
                      const bg = viridisColor(val);

                      const isHovered = hoveredCell?.r === r && hoveredCell?.c === c;

                      return (
                        <div
                          key={colLabel}
                          onMouseEnter={() => setHoveredCell({ r, c, val, real, imag })}
                          onMouseLeave={() => setHoveredCell(null)}
                          style={{
                            width: cellSize,
                            height: cellSize,
                            backgroundColor: bg,
                          }}
                          className={cn(
                            "cursor-pointer transition-transform border border-[#0d1527]/70 relative",
                            isHovered && "ring-2 ring-white/90 scale-105 z-20 shadow-lg"
                          )}
                        />
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Colorbar Section matching Screenshot 4 */}
        <div className="flex flex-col items-center">
          <span className="text-xs font-mono font-bold text-slate-300 mb-1.5">|ρ|</span>
          <div className="flex items-stretch gap-2">
            {/* Color gradient bar */}
            <div
              style={{
                height: cellSize * size,
                width: 16,
                background: "linear-gradient(to top, #440154 0%, #3e4989 20%, #26828e 40%, #1f9e89 50%, #35b779 60%, #b5de2b 80%, #fde725 100%)",
              }}
              className="rounded-sm border border-slate-700/80 shadow-inner"
            />
            {/* Colorbar ticks and numbers */}
            <div
              style={{ height: cellSize * size }}
              className="flex flex-col justify-between text-[11px] font-mono text-slate-400 select-none py-0.5"
            >
              {colorbarTicks.map((tickVal) => (
                <div key={tickVal} className="flex items-center gap-1 leading-none">
                  <span className="w-1.5 h-[1px] bg-slate-600 inline-block" />
                  <span>{tickVal === 1 ? "1" : tickVal === 0 ? "0" : tickVal.toFixed(1)}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Hover Information Readout */}
      {hoveredCell ? (
        <div className="text-center font-mono text-xs text-slate-300 py-1 bg-surface/80 rounded border border-line-soft/40">
          <span className="text-accent font-semibold">⟨{rawLabels[hoveredCell.r]}|ρ|{rawLabels[hoveredCell.c]}⟩</span>:
          {" "}|ρ| = <strong className="text-white">{hoveredCell.val.toFixed(4)}</strong>
          {Math.abs(hoveredCell.imag) > 1e-4 ? (
            <span className="text-slate-400 ml-2">
              (Re: {hoveredCell.real.toFixed(4)}, Im: {hoveredCell.imag.toFixed(4)})
            </span>
          ) : (
            <span className="text-slate-400 ml-2">(Real: {hoveredCell.real.toFixed(4)})</span>
          )}
        </div>
      ) : (
        <div className="text-center font-mono text-xs text-slate-500 py-1">
          Hover over any matrix cell to inspect quantum amplitude & phase
        </div>
      )}

      {/* Explanatory Caption */}
      <p className="text-xs leading-relaxed text-ink-3">
        Ideal |rho|. A Bell state lights up the off-diagonal |00⟩⟨11| corners — those corners{" "}
        <strong className="text-ink-2">are</strong> the entanglement. A classical mixture
        would show only the diagonal.
      </p>
    </div>
  );
}

// ------------------------------------------------------------------ bloch

export function BlochView({ result }: { result: RunResult }) {
  const amps = amplitudes(result.statevector);
  if (!amps) return <Notice>Bloch view needs a statevector.</Notice>;
  const n = qubitCount(amps);
  const rows = Array.from({ length: n }, (_, q) => {
    const rho = reducedDensityMatrix(amps, n, q);
    const [x, y, z] = blochVector(rho);
    const { theta, phi } = blochAngles(x, y, z);
    return { q, x, y, z, theta, phi, entropy: entanglementEntropy(rho), purity: purity(rho) };
  });

  return (
    <div className="flex flex-col gap-3">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3">
        {rows.map((row) => (
          <InteractiveBlochSphere key={row.q} {...row} />
        ))}
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-line text-left text-[11px] uppercase tracking-wide text-ink-3">
            <th className="py-2 pr-3 font-medium">Qubit</th>
            <th className="py-2 pr-3 text-right font-medium">x</th>
            <th className="py-2 pr-3 text-right font-medium">y</th>
            <th className="py-2 pr-3 text-right font-medium">z</th>
            <th className="py-2 pr-3 text-right font-medium">θ (deg)</th>
            <th className="py-2 pr-3 text-right font-medium">φ (deg)</th>
            <th className="py-2 text-right font-medium">S</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.q} className="border-b border-line-soft/60">
              <td className="py-1.5 pr-3 font-mono">q{row.q}</td>
              <td className="py-1.5 pr-3 text-right tabular-nums">{row.x.toFixed(4)}</td>
              <td className="py-1.5 pr-3 text-right tabular-nums">{row.y.toFixed(4)}</td>
              <td className="py-1.5 pr-3 text-right tabular-nums">{row.z.toFixed(4)}</td>
              <td className="py-1.5 pr-3 text-right tabular-nums">
                {Number.isNaN(row.theta) ? "–" : row.theta.toFixed(2)}
              </td>
              <td className="py-1.5 pr-3 text-right tabular-nums">
                {Number.isNaN(row.phi) ? "–" : row.phi.toFixed(2)}
              </td>
              <td className="py-1.5 text-right tabular-nums">{row.entropy.toFixed(4)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** A single 3D interactive Bloch sphere with Euler rotation, state vector, and coordinate axes. */
/** Exported so lesson demos, gate sandboxes, and playground draw the verified 3D sphere. */
export function BlochCircle({ q, x, y, z, size = 180 }: { q: number; x: number; y: number; z: number; size?: number }) {
  const r = Math.sqrt(x * x + y * y + z * z);
  const theta = r > 1e-6 ? (Math.acos(Math.max(-1, Math.min(1, z / r))) * 180) / Math.PI : 0;
  const phi = ((Math.atan2(y, x) * 180) / Math.PI + 360) % 360;
  const entropy = Math.max(0, 1 - r * r);

  return (
    <div className="flex flex-col items-center">
      <InteractiveBlochSphere
        q={q}
        x={x}
        y={y}
        z={z}
        theta={theta}
        phi={phi}
        entropy={entropy}
        size={size}
      />
    </div>
  );
}

export type { Complex };
