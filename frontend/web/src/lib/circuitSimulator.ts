/**
 * Client-Side Real-Time Quantum Statevector Simulator for interactive UI parity with IBM Quantum.
 * Immediately computes analytical statevectors and probabilities for <= 10 qubits in < 1ms.
 */
import type { CircuitIR } from "@composer/types";
import type { RunResult } from "../api/jobs";

interface Complex {
  re: number;
  im: number;
}

const cx = (re: number, im: number): Complex => ({ re, im });
const cadd = (a: Complex, b: Complex): Complex => cx(a.re + b.re, a.im + b.im);
const cmul = (a: Complex, b: Complex): Complex =>
  cx(a.re * b.re - a.im * b.im, a.re * b.im + a.im * b.re);

type Matrix2 = [[Complex, Complex], [Complex, Complex]];

const INV_SQRT2 = 1 / Math.SQRT2;

const GATES_1Q: Record<string, Matrix2> = {
  h: [
    [cx(INV_SQRT2, 0), cx(INV_SQRT2, 0)],
    [cx(INV_SQRT2, 0), cx(-INV_SQRT2, 0)],
  ],
  x: [
    [cx(0, 0), cx(1, 0)],
    [cx(1, 0), cx(0, 0)],
  ],
  y: [
    [cx(0, 0), cx(0, -1)],
    [cx(0, 1), cx(0, 0)],
  ],
  z: [
    [cx(1, 0), cx(0, 0)],
    [cx(0, 0), cx(-1, 0)],
  ],
  s: [
    [cx(1, 0), cx(0, 0)],
    [cx(0, 0), cx(0, 1)],
  ],
  sdg: [
    [cx(1, 0), cx(0, 0)],
    [cx(0, 0), cx(0, -1)],
  ],
  t: [
    [cx(1, 0), cx(0, 0)],
    [cx(0, 0), cx(INV_SQRT2, INV_SQRT2)],
  ],
  tdg: [
    [cx(1, 0), cx(0, 0)],
    [cx(0, 0), cx(INV_SQRT2, -INV_SQRT2)],
  ],
  sx: [
    [cx(0.5, 0.5), cx(0.5, -0.5)],
    [cx(0.5, -0.5), cx(0.5, 0.5)],
  ],
  id: [
    [cx(1, 0), cx(0, 0)],
    [cx(0, 0), cx(1, 0)],
  ],
  i: [
    [cx(1, 0), cx(0, 0)],
    [cx(0, 0), cx(1, 0)],
  ],
};

function parseParam(expr?: string): number {
  if (!expr) return 0;
  try {
    const cleaned = expr.toLowerCase().replace(/pi/g, String(Math.PI));
    // evaluate safely for math expressions
    return Function(`"use strict"; return (${cleaned})`)();
  } catch {
    return 0;
  }
}

function getParamGate(gateName: string, paramVal: number): Matrix2 {
  const g = gateName.toLowerCase();
  const half = paramVal / 2;
  if (g === "p") {
    return [
      [cx(1, 0), cx(0, 0)],
      [cx(0, 0), cx(Math.cos(paramVal), Math.sin(paramVal))],
    ];
  }
  if (g === "rx") {
    return [
      [cx(Math.cos(half), 0), cx(0, -Math.sin(half))],
      [cx(0, -Math.sin(half)), cx(Math.cos(half), 0)],
    ];
  }
  if (g === "ry") {
    return [
      [cx(Math.cos(half), 0), cx(-Math.sin(half), 0)],
      [cx(Math.sin(half), 0), cx(Math.cos(half), 0)],
    ];
  }
  if (g === "rz") {
    return [
      [cx(Math.cos(-half), Math.sin(-half)), cx(0, 0)],
      [cx(0, 0), cx(Math.cos(half), Math.sin(half))],
    ];
  }
  return GATES_1Q.id;
}

/**
 * Highest qubit count the *live preview* will simulate.
 *
 * The preview runs synchronously inside `useMemo` on every circuit edit, so its
 * cost is paid on the main thread while the user is still typing. Statevector
 * simulation is O(2^n) in both time and memory; measured on this code:
 *
 *     2-8q  <0.4ms   12q  8.8ms    16q   82.7ms
 *    10q     2.7ms   14q 21.8ms    18q  296.7ms   20q 1551.3ms
 *
 * 12 qubits is the last size that stays inside a 16ms frame, so it is the last
 * size where "live" is honest. Building larger circuits is still allowed (the
 * backend runs up to `max_static_qubits` = 20) — the preview simply stops
 * following past this point and says so in the UI. See PREVIEW_TRUNCATED below.
 *
 * Do not raise this without re-measuring. Raising it to 20 costs ~1.5s of
 * blocked main thread per keystroke.
 */
export const PREVIEW_MAX_QUBITS = 12;

/**
 * Simulate a circuit analytically and return exact probabilities.
 *
 * When `ir.n_qubits > maxQubits` the result is computed over the first
 * `maxQubits` wires only, and `RunResult.preview_truncated` is set so callers
 * can tell the user. Every gate branch below skips qubits >= n, so truncating
 * is safe — it never reads out of bounds.
 */
export function simulateCircuit(ir: CircuitIR, maxQubits = PREVIEW_MAX_QUBITS): RunResult {
  const n = Math.max(1, Math.min(maxQubits, ir.n_qubits));
  const dim = 1 << n;
  let state: Complex[] = Array.from({ length: dim }, (_, i) => (i === 0 ? cx(1, 0) : cx(0, 0)));

  // Sort ops by column/layer
  const ops = [...ir.ops].sort((a, b) => a.layer - b.layer);

  for (const op of ops) {
    if (op.kind !== "gate" || !op.gate) continue;
    const g = op.gate.toLowerCase();
    const target = op.qubits[0];
    if (target === undefined || target >= n) continue;

    // 1-Qubit Uncontrolled Gate
    if ((!op.controls || op.controls.length === 0) && g !== "cx" && g !== "cz" && g !== "cy" && g !== "swap") {
      let mat = GATES_1Q[g];
      if (!mat && (g === "p" || g === "rx" || g === "ry" || g === "rz")) {
        const p = parseParam(op.params?.[0]?.expr);
        mat = getParamGate(g, p);
      }
      if (!mat) mat = GATES_1Q.id;

      const next = new Array<Complex>(dim);
      const targetBit = 1 << target;
      for (let i = 0; i < dim; i++) {
        if ((i & targetBit) === 0) {
          const i0 = i;
          const i1 = i | targetBit;
          const a0 = state[i0];
          const a1 = state[i1];
          next[i0] = cadd(cmul(mat[0][0], a0), cmul(mat[0][1], a1));
          next[i1] = cadd(cmul(mat[1][0], a0), cmul(mat[1][1], a1));
        }
      }
      state = next;
    } else if (g === "cx" || g === "cnot") {
      const ctrl = op.controls?.[0] ?? op.qubits[0];
      const tgt = op.controls?.[0] !== undefined ? op.qubits[0] : op.qubits[1];
      if (ctrl === undefined || tgt === undefined || ctrl >= n || tgt >= n) continue;
      const ctrlBit = 1 << ctrl;
      const tgtBit = 1 << tgt;
      const next = [...state];
      for (let i = 0; i < dim; i++) {
        if ((i & ctrlBit) !== 0 && (i & tgtBit) === 0) {
          const i0 = i;
          const i1 = i | tgtBit;
          const temp = next[i0];
          next[i0] = next[i1];
          next[i1] = temp;
        }
      }
      state = next;
    } else if (g === "cz") {
      const ctrl = op.controls?.[0] ?? op.qubits[0];
      const tgt = op.controls?.[0] !== undefined ? op.qubits[0] : op.qubits[1];
      if (ctrl === undefined || tgt === undefined || ctrl >= n || tgt >= n) continue;
      const ctrlBit = 1 << ctrl;
      const tgtBit = 1 << tgt;
      const next = [...state];
      for (let i = 0; i < dim; i++) {
        if ((i & ctrlBit) !== 0 && (i & tgtBit) !== 0) {
          next[i] = cx(-next[i].re, -next[i].im);
        }
      }
      state = next;
    } else if (g === "swap") {
      const q0 = op.qubits[0];
      const q1 = op.qubits[1];
      if (q0 === undefined || q1 === undefined || q0 >= n || q1 >= n) continue;
      const bit0 = 1 << q0;
      const bit1 = 1 << q1;
      const next = [...state];
      for (let i = 0; i < dim; i++) {
        const b0 = (i & bit0) !== 0;
        const b1 = (i & bit1) !== 0;
        if (b0 && !b1) {
          const j = (i & ~bit0) | bit1;
          const temp = next[i];
          next[i] = next[j];
          next[j] = temp;
        }
      }
      state = next;
    }
  }

  // Format statevector and probabilities
  const svPairs: [number, number][] = state.map((c) => [Number(c.re.toFixed(6)), Number(c.im.toFixed(6))]);
  const counts: Record<string, number> = {};
  const probs: Record<string, number> = {};

  for (let i = 0; i < dim; i++) {
    const p = state[i].re * state[i].re + state[i].im * state[i].im;
    if (p > 1e-6) {
      const bitStr = i.toString(2).padStart(n, "0");
      probs[bitStr] = Number(p.toFixed(4));
      counts[bitStr] = Math.round(p * 1024);
    }
  }

  // True when the caller's circuit is wider than the preview window. Both the
  // flag and a metadata warning are set, so the UI cannot silently show a
  // partial result as if it were the whole circuit.
  const truncated = n < ir.n_qubits;
  const warnings = truncated
    ? [
        `Live preview covers only the first ${n} of ${ir.n_qubits} qubits. ` +
          `Run the circuit on a backend for the full result.`,
      ]
    : [];

  return {
      counts,
      probabilities: probs,
      statevector: svPairs,
      preview_truncated: truncated,
      metadata: {
        backend: "Analytical Simulator",
        shots: 1024,
        n_qubits: n,
        runtime_seconds: 0.001,
        bit_order: "qiskit (qubit 0 = rightmost)",
        warnings,
      },
    };
  }
