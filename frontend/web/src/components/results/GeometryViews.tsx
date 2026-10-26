/* Phase disk and Q-sphere, ported from viz.py::phase_disk and viz.py::qsphere.
 *
 * Both are drawn as SVG rather than plotly polar/surface traces. The geometry
 * is identical — same per-state rings, same Hamming-weight latitudes, same
 * relative-phase colour scale — but an orthographic projection of a sphere and
 * a polar plot are each a handful of circles and lines, so a megabyte of
 * plotting library to draw them would be a poor trade.
 */
import { useState, useRef } from "react";
import { RotateCcw, Move3d } from "lucide-react";
import { amplitudes, cabs, probabilities, qubitCount, relativePhases } from "../../lib/quantum";
import type { RunResult } from "../../api/jobs";
import { Notice } from "./ResultsViews";

/** The cyclic phase colour scale:
 *  0 rad (0°): Teal #3dd6c6
 *  +π/2 rad (+90°): Blue #5b9dff
 *  ±π rad (180°): Red #ff5d5d
 *  -π/2 rad (-90° / 270°): Purple #e17cff
 *  2π rad (360° / 0°): Teal #3dd6c6
 */
const PHASE_STOPS: [number, [number, number, number]][] = [
  [0.0, [61, 214, 198]],   // 0° (0 rad): Teal
  [0.25, [91, 157, 255]],  // 90° (+π/2 rad): Blue
  [0.5, [255, 93, 93]],    // 180° (±π rad): Red
  [0.75, [225, 124, 255]], // 270° / -90° (-π/2 rad): Purple
  [1.0, [61, 214, 198]],   // 360°: Teal
];

export function phaseColour(degrees: number): string {
  // Normalize angle to [0, 360)
  const norm = ((degrees % 360) + 360) % 360;
  const t = norm / 360;
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

  const size = 440;
  const centre = size / 2;
  const scale = centre - 56;
  const total = indices.length;

  const ticks = [0, 45, 90, 135, 180, 225, 270, 315];
  const tickLabels = ["0°", "45°", "90°", "135°", "180°", "-135°", "-90°", "-45°"];

  return (
    <div className="flex flex-col items-center gap-4">
      <div className="relative rounded-2xl border border-line-soft bg-raised/50 p-4 shadow-sm">
        <svg
          viewBox={`0 0 ${size} ${size}`}
          width={size}
          height={size}
          className="mx-auto max-w-full overflow-visible"
          role="img"
          aria-label="Phase disk: one ring per basis state, angle is relative phase"
        >
          <defs>
            <radialGradient id="phaseDiskGrad" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="var(--bg)" stopOpacity="0.9" />
              <stop offset="70%" stopColor="var(--raised)" stopOpacity="0.7" />
              <stop offset="100%" stopColor="var(--panel, var(--hover))" stopOpacity="0.5" />
            </radialGradient>
            <filter id="phaseGlow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* Background Tinted Disc */}
          <circle
            cx={centre}
            cy={centre}
            r={scale + 8}
            fill="url(#phaseDiskGrad)"
            stroke="var(--line)"
            strokeWidth="1.5"
          />

          {/* Radial Spokes & Degree Labels */}
          {ticks.map((tick, i) => {
            const [x1, y1] = polar(centre, centre, 12, tick);
            const [x2, y2] = polar(centre, centre, scale + 8, tick);
            const [lx, ly] = polar(centre, centre, scale + 24, tick);
            return (
              <g key={tick}>
                <line
                  x1={x1}
                  y1={y1}
                  x2={x2}
                  y2={y2}
                  stroke="var(--line-soft)"
                  strokeWidth="1"
                  strokeDasharray="3 3"
                />
                <text
                  x={lx}
                  y={ly}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fontSize="11"
                  fontWeight="500"
                  fill="var(--ink-3)"
                  className="font-mono select-none"
                >
                  {tickLabels[i]}
                </text>
              </g>
            );
          })}

          {/* State Rings and Markers */}
          {indices.map((index, slot) => {
            const ring = total === 1 ? 0.65 : 0.3 + (slot / Math.max(1, total - 1)) * 0.62;
            const angle = (phases[index] * 180) / Math.PI;
            const magnitude = cabs(amps[index]);
            const probability = probs[index];
            const [mx, my] = polar(centre, centre, ring * scale, angle);
            const markerRadius = Math.max(6, Math.min(22, 5 + 32 * Math.sqrt(probability)));
            const color = phaseColour(angle);

            // Avoid collision with outer 0° / 12 o'clock degree mark
            const isNearTop = Math.abs(angle) < 25;
            const labelDistance = isNearTop
              ? ring * scale - markerRadius - 12
              : ring * scale + markerRadius + 12;
            const [lx, ly] = polar(centre, centre, Math.max(16, labelDistance), angle);

            return (
              <g key={index}>
                {/* Concentric Ring */}
                <circle
                  cx={centre}
                  cy={centre}
                  r={ring * scale}
                  fill="none"
                  stroke="var(--line)"
                  strokeWidth="1"
                  strokeDasharray="4 4"
                  strokeOpacity="0.7"
                />

                {/* Vector Stem from Center to Marker */}
                <line
                  x1={centre}
                  y1={centre}
                  x2={mx}
                  y2={my}
                  stroke={color}
                  strokeWidth="2.5"
                  strokeOpacity="0.6"
                />

                {/* State Marker Dot */}
                <circle
                  cx={mx}
                  cy={my}
                  r={markerRadius}
                  fill={color}
                  stroke="var(--bg)"
                  strokeWidth="2"
                  filter="url(#phaseGlow)"
                  className="cursor-pointer transition-colors duration-150 hover:stroke-white hover:stroke-[2.5px]"
                >
                  <title>{`|${index.toString(2).padStart(n, "0")}⟩: prob=${(probability * 100).toFixed(2)}%, phase=${angle.toFixed(1)}°, mag=${magnitude.toFixed(3)}`}</title>
                </circle>

                {/* Non-Colliding State Ket Label */}
                <text
                  x={lx}
                  y={ly}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fontSize="11"
                  fontWeight="600"
                  fill="var(--ink)"
                  className="font-mono select-none"
                >
                  |{index.toString(2).padStart(n, "0")}⟩
                </text>
              </g>
            );
          })}
        </svg>

        {/* Phase Color Wheel Legend Bar */}
        <div className="mt-4 flex flex-col items-center gap-1.5 border-t border-line-soft pt-3">
          <div className="flex w-full max-w-[280px] items-center justify-between text-[10px] font-mono text-ink-3">
            <span>-180° (-π)</span>
            <span>0°</span>
            <span>+180° (+π)</span>
          </div>
          <div
            className="h-3 w-full max-w-[280px] rounded-full shadow-inner"
            style={{
              background:
                "linear-gradient(to right, rgb(225,124,255), rgb(255,93,93), rgb(61,214,198), rgb(91,157,255), rgb(225,124,255))",
            }}
          />
          <span className="text-[11px] text-ink-3">Relative Phase Hue Spectrum</span>
        </div>
      </div>

      <p className="max-w-md text-center text-xs leading-relaxed text-ink-3">
        Each basis state gets its <strong className="text-ink-2">own ring</strong>.
        Angle represents <strong className="text-ink-2">relative phase</strong> with respect to the first populated state,
        and marker radius is proportional to <strong className="text-ink-2">amplitude magnitude</strong>.
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

  const [yaw, setYaw] = useState(-30);
  const [pitch, setPitch] = useState(20);
  const [showStateLabels, setShowStateLabels] = useState(true);
  const [showPhaseLabels, setShowPhaseLabels] = useState(true);
  const [isDragging, setIsDragging] = useState(false);
  const dragRef = useRef<{ startX: number; startY: number; startYaw: number; startPitch: number } | null>(null);

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

  const size = 340;
  const centre = size / 2;
  const radius = centre - 40;

  // 3D Euler rotation: Yaw (around Z) then Pitch (around X)
  const radYaw = (yaw * Math.PI) / 180;
  const radPitch = (pitch * Math.PI) / 180;
  const cosY = Math.cos(radYaw);
  const sinY = Math.sin(radYaw);
  const cosP = Math.cos(radPitch);
  const sinP = Math.sin(radPitch);

  const project3D = (x: number, y: number, z: number) => {
    // 1. Rotate by yaw around Z
    const x1 = x * cosY - y * sinY;
    const y1 = x * sinY + y * cosY;
    // 2. Rotate by pitch around X
    const y2 = y1 * cosP - z * sinP;
    const z2 = y1 * sinP + z * cosP;
    return {
      sx: centre + x1 * radius,
      sy: centre - z2 * radius,
      depth: y2, // Positive depth is towards viewer
    };
  };

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
      const proj = project3D(x, y, z);
      markers.push({
        index,
        sx: proj.sx,
        sy: proj.sy,
        depth: proj.depth,
        probability: probs[index],
        degrees: (phases[index] * 180) / Math.PI,
        label: index.toString(2).padStart(n, "0"),
      });
    });
  }

  // Rotate North and South poles
  const northProj = project3D(0, 0, 1);
  const southProj = project3D(0, 0, -1);

  // Far markers first so the near ones sit on top
  const ordered = markers.slice().sort((a, b) => a.depth - b.depth);

  // Generate 3D latitude rings for each weight level
  const latitudeRings: { weight: number; path: string; depth: number }[] = [];
  if (n > 1) {
    for (let w = 1; w < n; w += 1) {
      const theta = (Math.PI * w) / n;
      const r_w = Math.sin(theta);
      const z_w = Math.cos(theta);
      const points: string[] = [];
      let avgDepth = 0;
      const steps = 36;
      for (let s = 0; s <= steps; s += 1) {
        const phi = (2 * Math.PI * s) / steps;
        const x = r_w * Math.cos(phi);
        const y = r_w * Math.sin(phi);
        const proj = project3D(x, y, z_w);
        points.push(`${proj.sx.toFixed(1)},${proj.sy.toFixed(1)}`);
        avgDepth += proj.depth;
      }
      latitudeRings.push({
        weight: w,
        path: `M ${points.join(" L ")}`,
        depth: avgDepth / (steps + 1),
      });
    }
  }

  const handlePointerDown = (e: React.PointerEvent<SVGSVGElement>) => {
    (e.target as Element).setPointerCapture?.(e.pointerId);
    dragRef.current = {
      startX: e.clientX,
      startY: e.clientY,
      startYaw: yaw,
      startPitch: pitch,
    };
    setIsDragging(true);
  };

  const handlePointerMove = (e: React.PointerEvent<SVGSVGElement>) => {
    if (!dragRef.current) return;
    const dx = e.clientX - dragRef.current.startX;
    const dy = e.clientY - dragRef.current.startY;
    setYaw(((dragRef.current.startYaw + dx * 0.6 + 180) % 360) - 180);
    setPitch(Math.max(-85, Math.min(85, dragRef.current.startPitch - dy * 0.6)));
  };

  const handlePointerUp = () => {
    dragRef.current = null;
    setIsDragging(false);
  };

  return (
    <div className="flex flex-col gap-3">
      {/* 3D Orbit Controls Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-line-soft bg-raised px-3 py-2 text-xs text-ink-2">
        <span className="flex items-center gap-1.5 font-medium text-ink">
          <Move3d className="h-4 w-4 text-accent" />
          3D Interactive Q-Sphere
          <span className="ml-1 text-[11px] font-normal text-ink-3">
            (click &amp; drag to rotate)
          </span>
        </span>
        <div className="flex items-center gap-3">
          <span className="font-mono text-[11px] text-ink-3">
            yaw {Math.round(yaw)}° · pitch {Math.round(pitch)}°
          </span>
          <button
            onClick={() => {
              setYaw(-30);
              setPitch(20);
            }}
            title="Reset rotation angles"
            className="flex items-center gap-1 rounded border border-line px-2 py-0.5 text-[11px] text-ink-2 hover:bg-hover hover:text-ink"
          >
            <RotateCcw className="h-3 w-3" /> Reset view
          </button>
        </div>
      </div>

      <svg
        viewBox={`0 0 ${size} ${size}`}
        className={`mx-auto w-full max-w-[340px] max-h-[280px] touch-none select-none ${
          isDragging ? "cursor-grabbing" : "cursor-grab"
        }`}
        role="img"
        aria-label="3D Interactive Q-sphere: click and drag to rotate, latitude is Hamming weight, colour is relative phase"
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerUp}
      >
        <defs>
          <radialGradient id="qsphereShading" cx="35%" cy="30%" r="70%">
            <stop offset="0%" stopColor="#1e293b" stopOpacity="0.4" />
            <stop offset="65%" stopColor="#0f172a" stopOpacity="0.75" />
            <stop offset="100%" stopColor="#020617" stopOpacity="0.95" />
          </radialGradient>
          <filter id="qGlow" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>

        {/* Outer Sphere Silhouette & Shading */}
        <circle
          cx={centre}
          cy={centre}
          r={radius}
          fill="url(#qsphereShading)"
          stroke="rgba(255, 255, 255, 0.2)"
          strokeWidth="1.2"
        />

        {/* 3D Latitude Parallels */}
        {latitudeRings.map((ring) => (
          <path
            key={ring.weight}
            d={ring.path}
            fill="none"
            stroke="var(--line-soft)"
            strokeWidth="1"
            strokeDasharray="3 3"
            strokeOpacity={ring.depth < 0 ? 0.35 : 0.75}
          />
        ))}

        {/* Central Axis connecting Poles */}
        <line
          x1={northProj.sx}
          y1={northProj.sy}
          x2={southProj.sx}
          y2={southProj.sy}
          stroke="var(--line-soft)"
          strokeWidth="1.2"
          strokeDasharray="4 3"
        />

        {/* Subtle North/South Pole Reference Points */}
        <circle
          cx={northProj.sx}
          cy={northProj.sy}
          r="2.5"
          fill="rgba(255,255,255,0.4)"
          opacity={northProj.depth < 0 ? 0.3 : 0.7}
        />
        <circle
          cx={southProj.sx}
          cy={southProj.sy}
          r="2.5"
          fill="rgba(255,255,255,0.4)"
          opacity={southProj.depth < 0 ? 0.3 : 0.7}
        />

        {/* State Stems from Center */}
        {ordered.map((m) => {
          const color = phaseColour(m.degrees);
          return (
            <line
              key={`stem-${m.index}`}
              x1={centre}
              y1={centre}
              x2={m.sx}
              y2={m.sy}
              stroke={color}
              strokeWidth={m.depth < 0 ? 1.5 : 2.5}
              strokeOpacity={m.depth < 0 ? 0.45 : 0.9}
            />
          );
        })}

        {/* State Nodes */}
        {ordered.map((m) => {
          const r = Math.max(7, Math.min(22, 6 + 26 * Math.sqrt(m.probability)));
          const isFront = m.depth >= 0;
          const color = phaseColour(m.degrees);
          const phaseStr = Math.abs(m.degrees) < 0.5 ? "0" : `${m.degrees >= 0 ? "+" : ""}${Math.round(m.degrees)}°`;
          
          let badgeText = `|${m.label}⟩`;
          if (showPhaseLabels && showStateLabels) {
            badgeText = `|${m.label}⟩  ${phaseStr}`;
          } else if (showPhaseLabels) {
            badgeText = phaseStr;
          }

          const badgeWidth = badgeText.length * 7.5 + 16;

          return (
            <g key={`marker-${m.index}`}>
              {/* Outer Glow Halo for Front Nodes */}
              {isFront && (
                <circle
                  cx={m.sx}
                  cy={m.sy}
                  r={r + 3}
                  fill="none"
                  stroke={color}
                  strokeWidth={1.5}
                  strokeOpacity={0.6}
                  filter="url(#qGlow)"
                />
              )}

              {/* Nodal Cap Marker with dynamic phase color */}
              <circle
                cx={m.sx}
                cy={m.sy}
                r={r}
                fill={color}
                stroke="#0b101d"
                strokeWidth={isFront ? 2 : 1.2}
                opacity={isFront ? 1 : 0.55}
                filter={isFront ? "url(#qGlow)" : undefined}
                className="cursor-pointer transition-colors duration-150 hover:stroke-white hover:stroke-[2.5px]"
              />

              {/* Specular 3D Highlight for depth */}
              {isFront && r > 9 && (
                <circle
                  cx={m.sx - r * 0.28}
                  cy={m.sy - r * 0.28}
                  r={r * 0.32}
                  fill="#ffffff"
                  fillOpacity={0.4}
                  className="pointer-events-none"
                />
              )}

              <title>
                {`|${m.label}⟩ · p=${m.probability.toFixed(4)} (${(m.probability * 100).toFixed(1)}%) · phase ${m.degrees >= 0 ? "+" : ""}${m.degrees.toFixed(1)}°`}
              </title>

              {/* Dark Rounded Badge Card */}
              {(showStateLabels || showPhaseLabels) && (
                <g className="pointer-events-none select-none">
                  <rect
                    x={m.sx - badgeWidth / 2}
                    y={m.sy - r - 23}
                    width={badgeWidth}
                    height={19}
                    rx={4}
                    ry={4}
                    fill="#0b101d"
                    stroke={color}
                    strokeWidth={1}
                    strokeOpacity={0.7}
                    opacity={isFront ? 0.95 : 0.6}
                  />
                  <text
                    x={m.sx}
                    y={m.sy - r - 10}
                    textAnchor="middle"
                    fontSize="10"
                    fontFamily="var(--font-mono), monospace"
                    fontWeight="600"
                    fill={isFront ? "#f8fafc" : "#94a3b8"}
                  >
                    {badgeText}
                  </text>
                </g>
              )}
            </g>
          );
        })}
        </svg>

        {/*
         * effdc6b replaced this caption with the interactive header above and
         * kept only an aria-label, so sighted readers lost both the key to the
         * diagram and the warning that bounds it. The Q-sphere still renders,
         * so the explanation belongs with it: a reader who takes this for a
         * Bloch sphere will read a mixed state off a picture that cannot show
         * one.
         */}
        <p className="text-xs leading-relaxed text-ink-3">
          Latitude is Hamming weight: north pole is all-zeros, south pole is all-ones. Blob
          size is probability, colour is relative phase. This shows the{" "}
          <strong className="text-ink-2">ideal statevector</strong> — it is not a Bloch
          sphere and cannot show a mixed state.
        </p>

        {/* Prominent, Highly Readable Quantum Phase Spectrum & Wheel Reference */}
      <div className="flex flex-col gap-3 rounded-2xl border border-line-soft bg-raised/90 p-4 backdrop-blur-md shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-4">
          {/* Large Cyclic Phase Color Wheel Reference */}
          <div className="flex items-center gap-4">
            <svg
              width="90"
              height="90"
              viewBox="-48 -48 96 96"
              className="select-none overflow-visible shrink-0"
              role="img"
              aria-label="Quantum phase cyclic hue wheel"
            >
              {Array.from({ length: 36 }).map((_, i) => {
                const a1 = (i * 10 * Math.PI) / 180;
                const a2 = ((i + 1) * 10 * Math.PI) / 180;
                const r1 = 20;
                const r2 = 32;
                const x1 = r1 * Math.cos(a1);
                const y1 = -r1 * Math.sin(a1);
                const x2 = r2 * Math.cos(a1);
                const y2 = -r2 * Math.sin(a1);
                const x3 = r2 * Math.cos(a2);
                const y3 = -r2 * Math.sin(a2);
                const x4 = r1 * Math.cos(a2);
                const y4 = -r1 * Math.sin(a2);
                const deg = i * 10;
                return (
                  <path
                    key={i}
                    d={`M ${x1} ${y1} L ${x2} ${y2} A ${r2} ${r2} 0 0 0 ${x3} ${y3} L ${x4} ${y4} A ${r1} ${r1} 0 0 1 ${x1} ${y1} Z`}
                    fill={phaseColour(deg)}
                  />
                );
              })}
              <circle cx="0" cy="0" r="18" fill="#090d16" stroke="rgba(255,255,255,0.08)" strokeWidth="1" />
              <text x="0" y="3" textAnchor="middle" fontSize="8" fontWeight="bold" fill="#f8fafc" fontFamily="var(--font-mono)">
                Phase
              </text>
              {/* Prominent Radian Labels around Wheel */}
              <text x="36" y="3" fontSize="9" fontWeight="bold" fill="#3dd6c6" fontFamily="var(--font-mono)">
                0
              </text>
              <text x="0" y="-35" textAnchor="middle" fontSize="9" fontWeight="bold" fill="#5b9dff" fontFamily="var(--font-mono)">
                +π/2
              </text>
              <text x="-36" y="3" textAnchor="end" fontSize="9" fontWeight="bold" fill="#ff5d5d" fontFamily="var(--font-mono)">
                ±π
              </text>
              <text x="0" y="42" textAnchor="middle" fontSize="9" fontWeight="bold" fill="#e17cff" fontFamily="var(--font-mono)">
                -π/2
              </text>
            </svg>

            <div className="space-y-1">
              <span className="block text-sm font-bold text-white tracking-tight">Quantum Phase Spectrum</span>
              <span className="block text-xs text-ink-3">
                Complex argument <code className="text-accent font-mono font-medium">arg(ψ)</code> mapped to continuous hue wheel
              </span>
              <div className="flex flex-wrap items-center gap-2 pt-1 text-[11px] font-mono">
                <span className="inline-flex items-center gap-1 rounded bg-[#3dd6c6]/15 px-2 py-0.5 font-medium text-[#3dd6c6] border border-[#3dd6c6]/30">
                  <span className="h-1.5 w-1.5 rounded-full bg-[#3dd6c6]" /> 0 rad (0°)
                </span>
                <span className="inline-flex items-center gap-1 rounded bg-[#5b9dff]/15 px-2 py-0.5 font-medium text-[#5b9dff] border border-[#5b9dff]/30">
                  <span className="h-1.5 w-1.5 rounded-full bg-[#5b9dff]" /> +π/2 rad (+90°)
                </span>
                <span className="inline-flex items-center gap-1 rounded bg-[#ff5d5d]/15 px-2 py-0.5 font-medium text-[#ff5d5d] border border-[#ff5d5d]/30">
                  <span className="h-1.5 w-1.5 rounded-full bg-[#ff5d5d]" /> ±π rad (180°)
                </span>
                <span className="inline-flex items-center gap-1 rounded bg-[#e17cff]/15 px-2 py-0.5 font-medium text-[#e17cff] border border-[#e17cff]/30">
                  <span className="h-1.5 w-1.5 rounded-full bg-[#e17cff]" /> -π/2 rad (-90°)
                </span>
              </div>
            </div>
          </div>

          {/* Labels & Overlay Controls */}
          <div className="flex items-center gap-3 rounded-xl border border-line bg-subtle p-2 text-xs">
            <span className="text-[11px] font-bold text-ink-3 uppercase tracking-wider font-mono">Display:</span>
            <label className="flex items-center gap-1.5 cursor-pointer font-medium text-ink hover:text-white select-none">
              <input
                type="checkbox"
                checked={showStateLabels}
                onChange={(e) => setShowStateLabels(e.target.checked)}
                className="rounded accent-accent h-4 w-4"
              />
              State (|x⟩)
            </label>
            <label className="flex items-center gap-1.5 cursor-pointer font-medium text-ink hover:text-white select-none">
              <input
                type="checkbox"
                checked={showPhaseLabels}
                onChange={(e) => setShowPhaseLabels(e.target.checked)}
                className="rounded accent-accent h-4 w-4"
              />
              Phase angle (deg)
            </label>
          </div>
        </div>
      </div>

      <p className="text-xs leading-relaxed text-ink-3">
        Latitude represents Hamming weight (|00…0⟩ at north pole, |11…1⟩ at south pole). Marker radius scales with probability P(x), and node/stem color shows quantum phase arg(ψ). Click and drag to orbit in 3D.
      </p>
    </div>
  );
}
