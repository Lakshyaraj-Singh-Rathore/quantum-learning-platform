/* Phase disk and Q-sphere, ported from viz.py::phase_disk and viz.py::qsphere.
 *
 * Both are drawn as SVG rather than plotly polar/surface traces. The geometry
 * is identical — same per-state rings, same Hamming-weight latitudes, same
 * relative-phase colour scale — but an orthographic projection of a sphere and
 * a polar plot are each a handful of circles and lines, so a megabyte of
 * plotting library to draw them would be a poor trade.
 */
import { amplitudes, cabs, probabilities, qubitCount, relativePhases } from "../../lib/quantum";
import type { RunResult } from "../../api/jobs";
import { Notice } from "./ResultsViews";

/** The cyclic phase colour scale from viz.py (teal -> blue -> pink -> red -> teal). */
const PHASE_STOPS: [number, [number, number, number]][] = [
  [0.0, [61, 214, 198]],
  [0.25, [91, 157, 255]],
  [0.5, [225, 124, 255]],
  [0.75, [255, 93, 93]],
  [1.0, [61, 214, 198]],
];

export function phaseColour(degrees: number): string {
  // Plotly maps the scale across [cmin, cmax] = [-180, 180].
  const t = (((degrees + 180) % 360) + 360) % 360 / 360;
  for (let i = 0; i < PHASE_STOPS.length - 1; i += 1) {
    const [t0, c0] = PHASE_STOPS[i];
    const [t1, c1] = PHASE_STOPS[i + 1];
    if (t <= t1) {
      const f = (t - t0) / (t1 - t0);
      const rgb = c0.map((v, k) => Math.round(v + (c1[k] - v) * f));
      return `rgb(${rgb.join(",")})`;
    }
  }
  return "rgb(61,214,198)";
}

const MAX_DISK_STATES = 32;

/** Polar -> screen, with 0 deg at north and angles counterclockwise (plotly's
 *  default angular axis). */
function polar(cx: number, cy: number, radius: number, degrees: number): [number, number] {
  const rad = (degrees * Math.PI) / 180;
  return [cx + radius * Math.sin(rad), cy - radius * Math.cos(rad)];
}

export function PhaseDisk({ result }: { result: RunResult }) {
  const amps = amplitudes(result.statevector);
  if (!amps) {
    return (
      <Notice>
        Phase disk unavailable: this run has no statevector (mid-circuit measurement,
        reset or remote execution).
      </Notice>
    );
  }

  const n = qubitCount(amps);
  const probs = probabilities(amps);
  const phases = relativePhases(amps);

  let indices = amps.map((_, i) => i).filter((i) => probs[i] > 1e-10);
  if (indices.length === 0) return <Notice>Statevector is empty.</Notice>;
  if (indices.length > MAX_DISK_STATES) {
    indices = indices
      .slice()
      .sort((a, b) => probs[b] - probs[a])
      .slice(0, MAX_DISK_STATES)
      .sort((a, b) => a - b);
  }

  const size = 420;
  const centre = size / 2;
  const scale = centre - 42;
  const total = indices.length;

  const ticks = [0, 45, 90, 135, 180, 225, 270, 315];
  const tickLabels = ["0", "45", "90", "135", "180", "-135", "-90", "-45"];

  return (
    <div className="flex flex-col gap-3">
      <svg
        viewBox={`0 0 ${size} ${size}`}
        className="mx-auto w-full max-w-[420px]"
        role="img"
        aria-label="Phase disk: one ring per basis state, angle is relative phase"
      >
        {ticks.map((tick) => {
          const [x1, y1] = polar(centre, centre, scale * 0.94, tick);
          const [x2, y2] = polar(centre, centre, scale, tick);
          const [lx, ly] = polar(centre, centre, scale + 16, tick);
          return (
            <g key={tick}>
              <line x1={x1} y1={y1} x2={x2} y2={y2} stroke="var(--line)" />
              <text
                x={lx}
                y={ly + 4}
                textAnchor="middle"
                fontSize="11"
                fill="var(--ink-3)"
              >
                {tickLabels[ticks.indexOf(tick)]}
              </text>
            </g>
          );
        })}

        {indices.map((index, slot) => {
          const ring = (slot + 1) / total;
          const angle = (phases[index] * 180) / Math.PI;
          const magnitude = cabs(amps[index]);
          const probability = probs[index];
          const inner = ring - (1 / total) * 0.92 * (1 - magnitude);
          const [ox, oy] = polar(centre, centre, ring * scale, angle);
          const [sx, sy] = polar(centre, centre, Math.max(0, inner) * scale, angle);
          const [mx, my] = polar(centre, centre, ring * scale, angle);
          const radius = (10 + 26 * Math.sqrt(probability)) / 3.2;
          return (
            <g key={index}>
              <circle
                cx={centre}
                cy={centre}
                r={ring * scale}
                fill="none"
                stroke="var(--line-soft)"
                strokeWidth="1"
              />
              <line x1={sx} y1={sy} x2={ox} y2={oy} stroke="var(--ink-3)" strokeWidth="2" />
              <circle
                cx={mx}
                cy={my}
                r={radius}
                fill={phaseColour(angle)}
                stroke="var(--line)"
                strokeWidth="1"
              />
              {(() => {
                const [lx, ly] = polar(centre, centre, ring * scale + 14, angle);
                return (
                  <text
                    x={lx}
                    y={ly + 4}
                    textAnchor="middle"
                    fontSize="10"
                    fill="var(--ink-3)"
                  >
                    |{index.toString(2).padStart(n, "0")}⟩
                  </text>
                );
              })()}
            </g>
          );
        })}
      </svg>

      <p className="text-xs leading-relaxed text-ink-3">
        Each basis state sits on its <strong className="text-ink-2">own ring</strong>, so
        states that share a phase no longer overlap. The angle is the phase{" "}
        <strong className="text-ink-2">relative</strong> to the first populated state
        (global phase is unobservable); marker size grows with probability.
      </p>
    </div>
  );
}

export function QSphere({ result }: { result: RunResult }) {
  const amps = amplitudes(result.statevector);
  if (!amps) return <Notice>Q-sphere unavailable: this run has no statevector.</Notice>;

  const n = qubitCount(amps);
  const probs = probabilities(amps);
  const phases = relativePhases(amps);

  // Bucket by Hamming weight: latitude. North pole is all-zeros.
  const byWeight = new Map<number, number[]>();
  amps.forEach((_, index) => {
    if (probs[index] > 1e-10) {
      const weight = index.toString(2).split("").filter((b) => b === "1").length;
      const bucket = byWeight.get(weight) ?? [];
      bucket.push(index);
      byWeight.set(weight, bucket);
    }
  });
  if (byWeight.size === 0) return <Notice>Statevector is empty.</Notice>;

  const size = 420;
  const centre = size / 2;
  const radius = centre - 46;

  type Marker = {
    index: number;
    sx: number;
    sy: number;
    depth: number;
    probability: number;
    degrees: number;
    label: string;
  };
  const markers: Marker[] = [];

  for (const [weight, members] of [...byWeight.entries()].sort((a, b) => a[0] - b[0])) {
    const theta = (Math.PI * weight) / Math.max(n, 1);
    members.sort((a, b) => a - b);
    members.forEach((index, slot) => {
      const phi = members.length <= 1 ? 0 : (2 * Math.PI * slot) / members.length;
      const x = Math.sin(theta) * Math.cos(phi);
      const y = Math.sin(theta) * Math.sin(phi);
      const z = Math.cos(theta);
      markers.push({
        index,
        sx: centre + x * radius,
        sy: centre - z * radius,
        // y is depth: positive is towards the viewer.
        depth: y,
        probability: probs[index],
        degrees: (phases[index] * 180) / Math.PI,
        label: index.toString(2).padStart(n, "0"),
      });
    });
  }

  // Far markers first so the near ones sit on top.
  const ordered = markers.slice().sort((a, b) => a.depth - b.depth);

  return (
    <div className="flex flex-col gap-3">
      <svg
        viewBox={`0 0 ${size} ${size}`}
        className="mx-auto w-full max-w-[420px]"
        role="img"
        aria-label="Q-sphere: latitude is Hamming weight, colour is relative phase"
      >
        <circle
          cx={centre}
          cy={centre}
          r={radius}
          fill="none"
          stroke="var(--line)"
          strokeWidth="1.5"
        />
        <ellipse
          cx={centre}
          cy={centre}
          rx={radius}
          ry={radius * 0.28}
          fill="none"
          stroke="var(--line-soft)"
        />
        <line
          x1={centre}
          y1={centre - radius}
          x2={centre}
          y2={centre + radius}
          stroke="var(--line-soft)"
        />
        <text x={centre} y={centre - radius - 8} textAnchor="middle" fontSize="10" fill="var(--ink-3)">
          |{"0".repeat(n)}⟩
        </text>
        <text x={centre} y={centre + radius + 16} textAnchor="middle" fontSize="10" fill="var(--ink-3)">
          |{"1".repeat(n)}⟩
        </text>

        {ordered.map((m) => (
          <g key={m.index}>
            <line
              x1={centre}
              y1={centre}
              x2={m.sx}
              y2={m.sy}
              stroke="var(--line)"
              strokeWidth="2"
            />
          </g>
        ))}
        {ordered.map((m) => {
          const r = (8 + 26 * Math.sqrt(m.probability)) / 4.6;
          return (
            <g key={m.index}>
              <circle
                cx={m.sx}
                cy={m.sy}
                r={r}
                fill={phaseColour(m.degrees)}
                stroke="var(--line)"
                strokeWidth="1"
                opacity={m.depth < 0 ? 0.75 : 1}
              />
              <title>
                {`|${m.label}⟩ · p=${m.probability.toFixed(4)} · rel. phase ${m.degrees >= 0 ? "+" : ""}${m.degrees.toFixed(1)}°`}
              </title>
              <text
                x={m.sx}
                y={m.sy - r - 4}
                textAnchor="middle"
                fontSize="9"
                fill="var(--ink-2)"
              >
                {m.label}
              </text>
            </g>
          );
        })}
      </svg>

      <p className="text-xs leading-relaxed text-ink-3">
        Latitude is Hamming weight: north pole is all-zeros, south pole is all-ones. Blob
        size is probability, colour is relative phase. This shows the{" "}
        <strong className="text-ink-2">ideal statevector</strong> — it is not a Bloch
        sphere and cannot show a mixed state.
      </p>
    </div>
  );
}
