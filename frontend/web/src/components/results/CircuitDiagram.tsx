/* Circuit diagram, ported from viz.py::circuit_diagram.
 *
 * The geometry (cell size, wire positions, control dots, CNOT target, swap
 * crosses, block outlines) is unchanged; the only deliberate difference is
 * colour: viz.py hardcodes a light palette (#FFFFFF background, #2D3436
 * strokes) because Streamlit rendered it inside a white card. Here it uses the
 * app's tokens so it reads correctly in dark mode, which is the default.
 *
 * It is drawn as React elements rather than an SVG string, so no
 * dangerouslySetInnerHTML is needed and the app's CSP can stay strict.
 */
import type { CircuitIR, Op } from "@composer/types";
import { Notice } from "./ResultsViews";

const GATE_COLORS: Record<string, string> = {
  h: "#6C5CE7",
  x: "#E17055",
  y: "#E84393",
  z: "#0984E3",
  s: "#00B894",
  sdg: "#00B894",
  t: "#00CEC9",
  tdg: "#00CEC9",
  sx: "#FDCB6E",
  p: "#0984E3",
  rx: "#D63031",
  ry: "#E84393",
  rz: "#0984E3",
  id: "#B2BEC3",
  swap: "#FD79A8",
};

const CELL = 58;
const LEFT = 56;
const TOP = 26;

const BLOCK_LABELS: Record<string, string> = {
  if: "IF",
  for: "FOR",
  while: "WHILE",
  box: "BOX",
};

export function CircuitDiagram({ ir }: { ir: CircuitIR }) {
  const nQubits = ir.n_qubits;
  const ops = [...ir.ops].sort((a, b) => a.layer - b.layer);
  const nLayers = ops.reduce((max, o) => Math.max(max, o.layer), -1) + 1;

  if (nLayers === 0) {
    return <Notice>Circuit is empty - drag gates from the palette to begin.</Notice>;
  }

  const width = LEFT + nLayers * CELL + 24;
  const height = TOP + nQubits * CELL + 16;
  const wireY = (qubit: number) => TOP + qubit * CELL + CELL / 2;

  return (
    <div className="overflow-auto">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        width={width}
        height={height}
        role="img"
        aria-label={`Circuit diagram: ${nQubits} qubits, ${nLayers} layers`}
        className="max-w-full"
      >
        {Array.from({ length: nQubits }, (_, qubit) => (
          <g key={`wire-${qubit}`}>
            <line
              x1={LEFT}
              y1={wireY(qubit)}
              x2={width - 16}
              y2={wireY(qubit)}
              stroke="var(--ink-3)"
              strokeWidth="1.4"
            />
            <text x="12" y={wireY(qubit) + 5} fontFamily="monospace" fontSize="14" fill="var(--ink-2)">
              q[{qubit}]
            </text>
          </g>
        ))}

        {ops.map((op) => (
          <OpGlyph key={op.id} op={op} nQubits={nQubits} wireY={wireY} />
        ))}
      </svg>
    </div>
  );
}

function OpGlyph({
  op,
  nQubits,
  wireY,
}: {
  op: Op;
  nQubits: number;
  wireY: (q: number) => number;
}) {
  const cx = LEFT + op.layer * CELL + CELL / 2;
  const targets = op.qubits ?? [];
  const controls = op.controls ?? [];

  if (op.kind === "if" || op.kind === "for" || op.kind === "while" || op.kind === "box") {
    return (
      <g>
        <rect
          x={cx - 24}
          y={TOP + 4}
          width="48"
          height={nQubits * CELL - 8}
          rx="8"
          fill="var(--bg-hover)"
          stroke="var(--ink-3)"
          strokeDasharray="5,3"
        />
        <text
          x={cx}
          y={TOP + 22}
          textAnchor="middle"
          fontFamily="sans-serif"
          fontSize="11"
          fontWeight="bold"
          fill="var(--ink-2)"
        >
          {BLOCK_LABELS[op.kind]}
        </text>
      </g>
    );
  }

  const involved = [...new Set([...targets, ...controls])].sort((a, b) => a - b);

  return (
    <g>
      {involved.length > 1 && (
        <line
          x1={cx}
          y1={wireY(involved[0])}
          x2={cx}
          y2={wireY(involved[involved.length - 1])}
          stroke="var(--ink-3)"
          strokeWidth="2"
        />
      )}

      {controls.map((control) => (
        <circle key={`c-${control}`} cx={cx} cy={wireY(control)} r="6" fill="var(--ink-2)" />
      ))}

      {op.kind === "measure" &&
        targets.map((qubit) => (
          <g key={`m-${qubit}`}>
            <rect
              x={cx - 17}
              y={wireY(qubit) - 17}
              width="34"
              height="34"
              rx="5"
              fill="var(--ink-2)"
            />
            <text
              x={cx}
              y={wireY(qubit) + 6}
              textAnchor="middle"
              fill="var(--bg)"
              fontFamily="sans-serif"
              fontSize="15"
            >
              M
            </text>
          </g>
        ))}

      {op.kind === "reset" &&
        targets.map((qubit) => (
          <g key={`r-${qubit}`}>
            <rect
              x={cx - 17}
              y={wireY(qubit) - 17}
              width="34"
              height="34"
              rx="5"
              fill="var(--ink-3)"
            />
            <text
              x={cx}
              y={wireY(qubit) + 6}
              textAnchor="middle"
              fill="var(--bg)"
              fontFamily="sans-serif"
              fontSize="12"
            >
              |0⟩
            </text>
          </g>
        ))}

      {op.kind === "barrier" &&
        (targets.length > 0 ? targets : Array.from({ length: nQubits }, (_, i) => i)).map(
          (qubit) => (
            <line
              key={`b-${qubit}`}
              x1={cx}
              y1={TOP + qubit * CELL + 4}
              x2={cx}
              y2={TOP + qubit * CELL + CELL - 4}
              stroke="var(--ink-3)"
              strokeWidth="3"
              strokeDasharray="4,3"
            />
          ),
        )}

      {op.kind === "gate" && <GateGlyph op={op} cx={cx} wireY={wireY} />}
    </g>
  );
}

function GateGlyph({
  op,
  cx,
  wireY,
}: {
  op: Op;
  cx: number;
  wireY: (q: number) => number;
}) {
  const gate = (op.gate ?? "").toLowerCase();
  const targets = op.qubits ?? [];
  const controls = op.controls ?? [];

  // Controlled X draws the CNOT target, not an X box.
  if (gate === "x" && controls.length > 0) {
    return (
      <g>
        {targets.map((qubit) => (
          <g key={`cx-${qubit}`}>
            <circle
              cx={cx}
              cy={wireY(qubit)}
              r="14"
              fill="var(--bg-raised)"
              stroke="var(--ink-2)"
              strokeWidth="2"
            />
            <line
              x1={cx - 14}
              y1={wireY(qubit)}
              x2={cx + 14}
              y2={wireY(qubit)}
              stroke="var(--ink-2)"
              strokeWidth="2"
            />
            <line
              x1={cx}
              y1={wireY(qubit) - 14}
              x2={cx}
              y2={wireY(qubit) + 14}
              stroke="var(--ink-2)"
              strokeWidth="2"
            />
          </g>
        ))}
      </g>
    );
  }

  if (gate === "swap") {
    return (
      <g>
        {targets.map((qubit) => (
          <g key={`sw-${qubit}`}>
            <line
              x1={cx - 9}
              y1={wireY(qubit) - 9}
              x2={cx + 9}
              y2={wireY(qubit) + 9}
              stroke="var(--ink-2)"
              strokeWidth="2.5"
            />
            <line
              x1={cx - 9}
              y1={wireY(qubit) + 9}
              x2={cx + 9}
              y2={wireY(qubit) - 9}
              stroke="var(--ink-2)"
              strokeWidth="2.5"
            />
          </g>
        ))}
      </g>
    );
  }

  const label =
    op.params.length > 0 ? `${gate.toUpperCase()}(${op.params[0].expr})` : gate.toUpperCase();
  const boxWidth = Math.max(34, 9 * label.length);
  const color = GATE_COLORS[gate] ?? "#6C5CE7";

  return (
    <g>
      {targets.map((qubit) => (
        <g key={`g-${qubit}`}>
          <rect
            x={cx - boxWidth / 2}
            y={wireY(qubit) - 17}
            width={boxWidth}
            height="34"
            rx="5"
            fill={color}
          />
          <text
            x={cx}
            y={wireY(qubit) + 6}
            textAnchor="middle"
            fill="#FFFFFF"
            fontFamily="sans-serif"
            fontSize="13"
            fontWeight="600"
          >
            {label}
          </text>
        </g>
      ))}
    </g>
  );
}
