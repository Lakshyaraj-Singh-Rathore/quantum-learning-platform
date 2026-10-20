import { useState, useRef, useCallback } from "react";
import { RotateCcw } from "lucide-react";

export interface BlochQubitData {
  q: number;
  x: number;
  y: number;
  z: number;
  theta: number;
  phi: number;
  entropy: number;
}

interface Props extends BlochQubitData {
  size?: number;
  interactive?: boolean;
}

/**
 * Interactive 3D Bloch Sphere Component.
 * Supports mouse drag to rotate in 3D (Euler yaw and pitch),
 * keyboard arrow controls, 3D great circles, coordinate axes,
 * state vector arrow, and real-time projection.
 */
export function InteractiveBlochSphere({
  q,
  x,
  y,
  z,
  theta,
  phi,
  entropy,
  size = 220,
  interactive = true,
}: Props) {
  // Initial viewpoint: slight elevation and rotation for natural 3D depth
  const [yaw, setYaw] = useState(-35); // rotation around Z axis in deg
  const [pitch, setPitch] = useState(25); // tilt angle in deg

  const isDragging = useRef(false);
  const lastMousePos = useRef<{ x: number; y: number }>({ x: 0, y: 0 });

  const radius = size * 0.38;
  const center = size / 2;

  // 3D rotation and projection: (x, y, z) -> (px, py, depth)
  // Standard quantum Bloch convention: Z is up, X is right/forward, Y is into page/right.
  const project = useCallback(
    (vx: number, vy: number, vz: number) => {
      const radYaw = (yaw * Math.PI) / 180;
      const radPitch = (pitch * Math.PI) / 180;

      // Rotate around Z axis (yaw)
      const x1 = vx * Math.cos(radYaw) - vy * Math.sin(radYaw);
      const y1 = vx * Math.sin(radYaw) + vy * Math.cos(radYaw);
      const z1 = vz;

      // Rotate around X' axis (pitch/tilt)
      const x2 = x1;
      const y2 = y1 * Math.cos(radPitch) - z1 * Math.sin(radPitch);
      const z2 = y1 * Math.sin(radPitch) + z1 * Math.cos(radPitch);

      // Orthographic projection to 2D screen coordinates
      const px = center + x2 * radius;
      const py = center - z2 * radius;
      const depth = y2; // for z-sorting if needed

      return { px, py, depth };
    },
    [yaw, pitch, radius, center],
  );

  // Mouse drag handlers
  const handleMouseDown = (e: React.MouseEvent) => {
    if (!interactive) return;
    isDragging.current = true;
    lastMousePos.current = { x: e.clientX, y: e.clientY };
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging.current || !interactive) return;
    const dx = e.clientX - lastMousePos.current.x;
    const dy = e.clientY - lastMousePos.current.y;
    lastMousePos.current = { x: e.clientX, y: e.clientY };

    setYaw((prev) => (prev + dx * 0.8) % 360);
    setPitch((prev) => Math.max(-80, Math.min(80, prev + dy * 0.8)));
  };

  const handleMouseUp = () => {
    isDragging.current = false;
  };

  // Keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!interactive) return;
    if (e.key === "ArrowLeft") setYaw((prev) => prev - 10);
    if (e.key === "ArrowRight") setYaw((prev) => prev + 10);
    if (e.key === "ArrowUp") setPitch((prev) => Math.min(80, prev + 10));
    if (e.key === "ArrowDown") setPitch((prev) => Math.max(-80, prev - 10));
  };

  const resetView = () => {
    setYaw(-35);
    setPitch(25);
  };

  // Generate 3D circle paths for equator and meridians
  const generateCirclePath = (plane: "XY" | "XZ" | "YZ", steps = 48) => {
    const points: string[] = [];
    for (let i = 0; i <= steps; i++) {
      const angle = (i / steps) * 2 * Math.PI;
      const cosA = Math.cos(angle);
      const sinA = Math.sin(angle);
      let pt;
      if (plane === "XY") pt = project(cosA, sinA, 0);
      else if (plane === "XZ") pt = project(cosA, 0, sinA);
      else pt = project(0, cosA, sinA);

      points.push(`${i === 0 ? "M" : "L"} ${pt.px.toFixed(1)} ${pt.py.toFixed(1)}`);
    }
    return points.join(" ");
  };

  // Project axes
  const origin = project(0, 0, 0);
  const xPos = project(1.18, 0, 0);
  const xNeg = project(-1.18, 0, 0);
  const yPos = project(0, 1.18, 0);
  const yNeg = project(0, -1.18, 0);
  const zPos = project(0, 0, 1.18);
  const zNeg = project(0, 0, -1.18);

  // Project state vector
  const tip = project(x, y, z);
  const vectorLength = Math.sqrt(x * x + y * y + z * z);
  const isMixed = vectorLength < 0.15;

  return (
    <div className="flex flex-col items-center rounded-xl border border-line-soft bg-raised/70 p-3 shadow-sm transition-all hover:border-line">
      {/* Header with Qubit Label and Reset View */}
      <div className="flex w-full items-center justify-between px-1 pb-1">
        <span className="font-mono text-xs font-semibold text-ink">
          Qubit q[{q}]
        </span>
        {interactive && (
          <button
            onClick={resetView}
            title="Reset 3D View"
            className="rounded p-1 text-ink-3 transition-colors hover:bg-hover hover:text-ink"
          >
            <RotateCcw className="h-3 w-3" />
          </button>
        )}
      </div>

      {/* 3D Canvas SVG */}
      <div
        className="relative touch-none select-none"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onKeyDown={handleKeyDown}
        tabIndex={interactive ? 0 : undefined}
        role="region"
        aria-label={`Interactive 3D Bloch sphere for qubit ${q}. Drag with mouse or use arrow keys to rotate.`}
        style={{ cursor: interactive ? (isDragging.current ? "grabbing" : "grab") : "default" }}
      >
        <svg
          width={size}
          height={size}
          viewBox={`0 0 ${size} ${size}`}
          className="overflow-visible"
        >
          <defs>
            <radialGradient id={`blochBg-${q}`} cx="45%" cy="40%" r="65%">
              <stop offset="0%" stopColor="var(--bg)" stopOpacity="0.8" />
              <stop offset="100%" stopColor="var(--panel, var(--hover))" stopOpacity="0.4" />
            </radialGradient>
            <filter id={`arrowGlow-${q}`} x="-30%" y="-30%" width="160%" height="160%">
              <feGaussianBlur stdDeviation="2.5" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* Sphere Silhouette */}
          <circle
            cx={center}
            cy={center}
            r={radius}
            fill={`url(#blochBg-${q})`}
            stroke="var(--line-soft)"
            strokeWidth="1.2"
          />

          {/* 3D Great Circles */}
          {/* XY Equatorial Plane (Dashed) */}
          <path
            d={generateCirclePath("XY")}
            fill="none"
            stroke="var(--accent)"
            strokeWidth="1"
            strokeDasharray="3 3"
            strokeOpacity="0.6"
          />
          {/* XZ Meridian */}
          <path
            d={generateCirclePath("XZ")}
            fill="none"
            stroke="var(--line)"
            strokeWidth="0.8"
            strokeOpacity="0.5"
          />
          {/* YZ Meridian */}
          <path
            d={generateCirclePath("YZ")}
            fill="none"
            stroke="var(--line)"
            strokeWidth="0.8"
            strokeOpacity="0.5"
          />

          {/* Coordinate Axes */}
          {/* X Axis */}
          <line
            x1={xNeg.px}
            y1={xNeg.py}
            x2={xPos.px}
            y2={xPos.py}
            stroke="var(--line)"
            strokeWidth="1"
            strokeDasharray="2 2"
          />
          {/* Y Axis */}
          <line
            x1={yNeg.px}
            y1={yNeg.py}
            x2={yPos.px}
            y2={yPos.py}
            stroke="var(--line)"
            strokeWidth="1"
            strokeDasharray="2 2"
          />
          {/* Z Axis (Vertical) */}
          <line
            x1={zNeg.px}
            y1={zNeg.py}
            x2={zPos.px}
            y2={zPos.py}
            stroke="var(--line)"
            strokeWidth="1.2"
          />

          {/* Axis Labels */}
          {/* |0> at +Z */}
          <text
            x={zPos.px}
            y={zPos.py - 6}
            textAnchor="middle"
            dominantBaseline="middle"
            fontSize="10"
            fontWeight="bold"
            fill="var(--ink)"
          >
            |0⟩
          </text>
          {/* |1> at -Z */}
          <text
            x={zNeg.px}
            y={zNeg.py + 7}
            textAnchor="middle"
            dominantBaseline="middle"
            fontSize="10"
            fontWeight="bold"
            fill="var(--ink)"
          >
            |1⟩
          </text>
          {/* +X Label */}
          <text
            x={xPos.px + 6}
            y={xPos.py}
            textAnchor="start"
            dominantBaseline="middle"
            fontSize="9"
            fill="var(--accent)"
          >
            +X
          </text>
          {/* +Y Label */}
          <text
            x={yPos.px}
            y={yPos.py + 6}
            textAnchor="middle"
            dominantBaseline="hanging"
            fontSize="9"
            fill="var(--accent-2, #38bdf8)"
          >
            +Y
          </text>

          {/* Center Origin Dot */}
          <circle cx={origin.px} cy={origin.py} r={2} fill="var(--ink-3)" />

          {/* Equatorial Projection Shadow (if not pure Z) */}
          {!isMixed && Math.abs(z) < 0.98 && (
            <line
              x1={origin.px}
              y1={origin.py}
              x2={project(x, y, 0).px}
              y2={project(x, y, 0).py}
              stroke="var(--ink-3)"
              strokeWidth="1"
              strokeDasharray="2 2"
              strokeOpacity="0.4"
            />
          )}

          {/* 3D State Vector Arrow */}
          <line
            x1={origin.px}
            y1={origin.py}
            x2={tip.px}
            y2={tip.py}
            stroke={isMixed ? "var(--warn)" : "var(--accent)"}
            strokeWidth={isMixed ? 2 : 2.8}
            strokeDasharray={isMixed ? "3 3" : undefined}
            strokeLinecap="round"
            filter={`url(#arrowGlow-${q})`}
          />

          {/* State Vector Tip */}
          <circle
            cx={tip.px}
            cy={tip.py}
            r={isMixed ? 4 : 5.5}
            fill={isMixed ? "var(--warn)" : "var(--accent)"}
            stroke="var(--bg)"
            strokeWidth="1.5"
          />
        </svg>

        {interactive && (
          <div className="pointer-events-none absolute bottom-1 right-1 text-[9px] text-ink-3">
            drag to rotate
          </div>
        )}
      </div>

      {/* State Status Badge */}
      <div className="mt-2 flex w-full flex-col items-center gap-1 border-t border-line-soft pt-1.5">
        {isMixed ? (
          <span className="rounded bg-warn/15 px-2 py-0.5 text-[10px] font-medium text-warn">
            Mixed State (Entangled · S={entropy.toFixed(3)})
          </span>
        ) : (
          <div className="grid grid-cols-3 gap-2 text-center text-[11px] tabular-nums text-ink-2">
            <span>x: {x.toFixed(2)}</span>
            <span>y: {y.toFixed(2)}</span>
            <span>z: {z.toFixed(2)}</span>
          </div>
        )}
        <div className="text-[10px] tabular-nums text-ink-3">
          q{q} · θ: {Number.isNaN(theta) ? "–" : `${theta.toFixed(1)}°`} · φ:{" "}
          {Number.isNaN(phi) ? "–" : `${phi.toFixed(1)}°`} · |r| = {vectorLength.toFixed(3)}
        </div>
      </div>
    </div>
  );
}
