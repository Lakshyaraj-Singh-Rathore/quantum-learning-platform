/* The result views, ported from frontend/lib/viz.py.
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
import { useState } from "react";
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
import { cn } from "../ui";

/** Matches viz.py's palette; the accents are the app's own tokens. */
const SERIES_ALT = "#6C5CE7";
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
}: {
  value: number;
  title: string;
  subtitle?: string;
  color: string;
}) {
  // Semicircular dial: 180 degrees of sweep, drawn as an SVG arc.
  const radius = 52;
  const circumference = Math.PI * radius;
  const clamped = Math.max(0, Math.min(1, value));
  return (
    <div className="flex flex-col items-center rounded-lg border border-line-soft bg-hover/60 p-3">
      <svg viewBox="0 0 140 84" className="w-full max-w-[170px]" role="img" aria-label={`${title} ${value.toFixed(3)}`}>
        <path
          d={`M 18 70 A ${radius} ${radius} 0 0 1 122 70`}
          fill="none"
          stroke="var(--line)"
          strokeWidth="10"
          strokeLinecap="round"
        />
        <path
          d={`M 18 70 A ${radius} ${radius} 0 0 1 122 70`}
          fill="none"
          stroke={color}
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={`${clamped * circumference} ${circumference}`}
        />
        <text x="70" y="64" textAnchor="middle" fontSize="26" fill="var(--ink)">
          {value.toFixed(3)}
        </text>
      </svg>
      <p className="mt-1 text-[13px] font-medium text-ink">{title}</p>
      {subtitle && <p className="text-[11px] text-ink-3">{subtitle}</p>}
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
  // CUDA-Q does not, and inventing a stand-in would be a lie on the page.
  const fidelity = metrics.fidelity as number | undefined;
  const purityValue = metrics.purity as number | undefined;

  const grade = (v: number) => (v > 0.97 ? "var(--accent)" : v > 0.85 ? "var(--warn)" : "var(--danger)");

  return (
    <div className="flex flex-col gap-3">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Gauge
          value={entropy}
          title="Entanglement S"
          subtitle={`${entangled ? "ENTANGLED" : "separable"}${
            concurrence !== undefined ? `  |  C=${Number(concurrence).toFixed(2)}` : ""
          }`}
          color={entangled ? "var(--warn)" : "var(--accent)"}
        />
        {fidelity !== undefined && (
          <Gauge
            value={Number(fidelity)}
            title="Fidelity"
            subtitle={noisy ? "F(ideal, noisy rho)" : "no noise applied"}
            color={grade(Number(fidelity))}
          />
        )}
        {purityValue !== undefined && (
          <Gauge
            value={Number(purityValue)}
            title="Purity"
            subtitle="Tr(rho^2)  |  1 = still pure"
            color={grade(Number(purityValue))}
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

export function Histogram({ result }: { result: RunResult }) {
  const [asProbability, setAsProbability] = useState(false);
  const [colourByPhase, setColourByPhase] = useState(false);

  const counts = result.counts ?? {};
  const total = Object.values(counts).reduce((a, b) => a + b, 0) || 1;
  let entries = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  const truncated = entries.length > MAX_HISTOGRAM_BARS;
  if (truncated) entries = entries.slice(0, MAX_HISTOGRAM_BARS);

  const amps = amplitudes(result.statevector);
  const phases = amps ? relativePhases(amps) : null;
  const max = Math.max(...entries.map(([, n]) => n), 1);

  if (entries.length === 0) return <Notice>No counts in this result.</Notice>;

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap gap-4">
        <label className="flex items-center gap-2 text-[13px] text-ink-2">
          <input
            type="checkbox"
            checked={asProbability}
            onChange={(e) => setAsProbability(e.target.checked)}
            className="h-4 w-4 accent-[var(--accent)]"
          />
          Show probability instead of counts
        </label>
        <label
          className={cn(
            "flex items-center gap-2 text-[13px] text-ink-2",
            !phases && "opacity-50",
          )}
          title={
            phases
              ? "Z, S, T and RZ change the phase without moving any counts, so the bars stay the same height and only the colour changes."
              : "Needs a statevector"
          }
        >
          <input
            type="checkbox"
            checked={colourByPhase && phases !== null}
            disabled={!phases}
            onChange={(e) => setColourByPhase(e.target.checked)}
            className="h-4 w-4 accent-[var(--accent)]"
          />
          Colour bars by relative phase
        </label>
      </div>

      <div className="flex items-end gap-1.5" style={{ height: 260 }}>
        {entries.map(([bits, n]) => {
          const value = asProbability ? n / total : n;
          const height = ((asProbability ? n / total : n / max) * 100).toFixed(2);
          const index = parseInt(bits, 2);
          const phase = phases ? phases[index] : null;
          const hue = phase === null ? 0 : (phase * 180) / Math.PI;
          return (
            <div key={bits} className="flex min-w-0 flex-1 flex-col items-center justify-end gap-1">
              <span className="text-[10px] tabular-nums text-ink-3">
                {asProbability ? `${(value * 100).toFixed(1)}%` : n}
              </span>
              <div
                className="w-full rounded-t"
                style={{
                  height: `${height}%`,
                  background:
                    colourByPhase && phase !== null
                      ? `hsl(${hue}, 65%, 55%)`
                      : "var(--accent)",
                }}
                title={`${bits}: ${n} (${((n / total) * 100).toFixed(2)}%)`}
              />
              <span className="w-full truncate text-center font-mono text-[10px] text-ink-3">
                {bits}
              </span>
            </div>
          );
        })}
      </div>

      {truncated && (
        <p className="text-xs text-ink-3">
          Showing the {MAX_HISTOGRAM_BARS} most frequent of {Object.keys(counts).length} outcomes.
        </p>
      )}
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

function GroupedBars({
  labels,
  series,
  height = 260,
}: {
  labels: string[];
  series: { name: string; values: number[]; color: string }[];
  height?: number;
}) {
  const max = Math.max(...series.flatMap((s) => s.values), 1e-9);
  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap gap-4">
        {series.map((s) => (
          <span key={s.name} className="flex items-center gap-1.5 text-xs text-ink-2">
            <span className="h-2.5 w-2.5 rounded-sm" style={{ background: s.color }} />
            {s.name}
          </span>
        ))}
      </div>
      <div className="flex items-end gap-2" style={{ height }}>
        {labels.map((label, i) => (
          <div key={label} className="flex min-w-0 flex-1 items-end justify-center gap-0.5">
            {series.map((s) => (
              <div
                key={s.name}
                className="w-full rounded-t"
                style={{
                  height: `${(Math.max(0, s.values[i]) / max) * 100}%`,
                  background: s.color,
                }}
                title={`${label} · ${s.name}: ${s.values[i].toFixed(4)}`}
              />
            ))}
          </div>
        ))}
      </div>
      <div className="flex gap-2">
        {labels.map((label) => (
          <span
            key={label}
            className="min-w-0 flex-1 truncate text-center font-mono text-[10px] text-ink-3"
          >
            {label}
          </span>
        ))}
      </div>
    </div>
  );
}

export function BornVsShots({ result }: { result: RunResult }) {
  const amps = amplitudes(result.statevector);
  const counts = result.counts ?? {};
  if (!amps || Object.keys(counts).length === 0) {
    return <Notice>Needs both a statevector and measurement counts.</Notice>;
  }
  const n = qubitCount(amps);
  const probs = probabilities(amps);
  const total = Object.values(counts).reduce((a, b) => a + b, 0) || 1;

  const exact = new Map<string, number>();
  probs.forEach((p, i) => {
    if (p > 1e-12) exact.set(i.toString(2).padStart(n, "0"), p);
  });
  const sampled = new Map(Object.entries(counts).map(([k, v]) => [k, v / total]));
  const labels = [...new Set([...exact.keys(), ...sampled.keys()])].sort();

  return (
    <div className="flex flex-col gap-3">
      <GroupedBars
        labels={labels}
        series={[
          { name: "exact |psi|²", values: labels.map((l) => exact.get(l) ?? 0), color: "var(--accent)" },
          { name: `${total} shots`, values: labels.map((l) => sampled.get(l) ?? 0), color: SERIES_ALT },
        ]}
      />
      <p className="text-xs leading-relaxed text-ink-3">
        Gaps here are <strong className="text-ink-2">sampling error</strong> from a finite
        shot count, not hardware noise. Raise the shots and the two bars converge.
      </p>
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
              color: "var(--danger)",
            },
          ]}
        />
      </div>
    </div>
  );
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
  const labels = Array.from({ length: size }, (_, i) => i.toString(2).padStart(n, "0"));
  const max = Math.max(...amps.map(cabs), 1e-9);

  return (
    <div className="flex flex-col gap-3">
      <div className="overflow-auto">
        <table className="border-separate border-spacing-0 text-[10px]">
          <thead>
            <tr>
              <th className="sticky left-0 bg-bg" />
              {labels.map((l) => (
                <th key={l} className="px-1 pb-1 font-mono font-normal text-ink-3">
                  {l}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {labels.map((rowLabel, r) => (
              <tr key={rowLabel}>
                <th className="sticky left-0 bg-bg pr-1 text-right font-mono font-normal text-ink-3">
                  {rowLabel}
                </th>
                {labels.map((colLabel, c) => {
                  // |rho_rc| = |a_r * conj(a_c)| = |a_r| * |a_c|
                  const value = cabs(amps[r]) * cabs(amps[c]);
                  return (
                    <td
                      key={colLabel}
                      title={`⟨${rowLabel}|rho|${colLabel}⟩ = ${value.toFixed(4)}`}
                      className="h-6 w-6"
                      style={{
                        background: `color-mix(in oklab, var(--accent) ${(value / max) * 100}%, transparent)`,
                      }}
                    />
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
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
      <div className="flex flex-wrap gap-4">
        {rows.map((row) => (
          <BlochCircle key={row.q} {...row} />
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

/** A single sphere drawn as an orthographic disk with the state vector on it. */
function BlochCircle({ q, x, y, z }: { q: number; x: number; y: number; z: number }) {
  // Screen projection: x right, z up, y towards the viewer (drawn as depth).
  const size = 120;
  const centre = size / 2;
  const radius = 44;
  const px = centre + x * radius * 0.7;
  const py = centre - z * radius * 0.7;
  const length = Math.sqrt(x * x + y * y + z * z);
  return (
    <div className="flex flex-col items-center gap-1">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} role="img" aria-label={`Bloch sphere for qubit ${q}`}>
        <circle cx={centre} cy={centre} r={radius} fill="none" stroke="var(--line)" />
        <ellipse
          cx={centre}
          cy={centre}
          rx={radius}
          ry={radius * 0.32}
          fill="none"
          stroke="var(--line-soft)"
        />
        <line
          x1={centre}
          y1={centre}
          x2={centre}
          y2={centre - radius}
          stroke="var(--line-soft)"
        />
        <line x1={centre} y1={centre} x2={px} y2={py} stroke="var(--accent)" strokeWidth="2.5" />
        <circle cx={px} cy={py} r="4" fill="var(--accent)" />
        <text x={centre} y={12} textAnchor="middle" fontSize="9" fill="var(--ink-3)">
          |0⟩
        </text>
        <text x={centre} y={size - 4} textAnchor="middle" fontSize="9" fill="var(--ink-3)">
          |1⟩
        </text>
      </svg>
      <p className="text-[11px] text-ink-3">
        q{q} · |r| = {length.toFixed(3)}
      </p>
    </div>
  );
}

export type { Complex };
