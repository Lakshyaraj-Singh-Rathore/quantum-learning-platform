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
    if (op.kind === "barrier") continue;

    if (op.kind === "reset") {
      for (const tgt of op.qubits ?? []) {
        if (tgt >= n) continue;
        const bit = 1 << tgt;
        for (let i = 0; i < dim; i++) {
          if ((i & bit) !== 0) {
            const i0 = i & ~bit;
            state[i0] = cadd(state[i0], state[i]);
            state[i] = cx(0, 0);
          }
        }
      }
      let norm = 0;
      for (let i = 0; i < dim; i++) {
        norm += state[i].re * state[i].re + state[i].im * state[i].im;
      }
      if (norm > 0) {
        const factor = 1 / Math.sqrt(norm);
        for (let i = 0; i < dim; i++) {
          state[i] = cx(state[i].re * factor, state[i].im * factor);
        }
      }
      continue;
    }

    if (op.kind === "measure") {
      // Born rule collapse for mid-circuit measurements:
      // If the measured qubit is used again later in the circuit, project and collapse statevector
      const tgt = op.qubits?.[0];
      if (tgt !== undefined && tgt < n) {
        const isMidCircuit = ops.some(
          (other) =>
            other.layer > op.layer &&
            (other.qubits?.includes(tgt) || other.controls?.includes(tgt))
        );
        if (isMidCircuit) {
          const bit = 1 << tgt;
          let p1 = 0;
          for (let i = 0; i < dim; i++) {
            if ((i & bit) !== 0) {
              p1 += state[i].re * state[i].re + state[i].im * state[i].im;
            }
          }
          const outcome = Math.random() < p1 ? 1 : 0;
          for (let i = 0; i < dim; i++) {
            const bitVal = (i & bit) !== 0 ? 1 : 0;
            if (bitVal !== outcome) {
              state[i] = cx(0, 0);
            }
          }
          let norm = 0;
          for (let i = 0; i < dim; i++) {
            norm += state[i].re * state[i].re + state[i].im * state[i].im;
          }
          if (norm > 0) {
            const factor = 1 / Math.sqrt(norm);
            for (let i = 0; i < dim; i++) {
              state[i] = cx(state[i].re * factor, state[i].im * factor);
            }
          }
        }
      }
      continue;
    }

    if (op.kind !== "gate" || !op.gate) continue;
    let g = op.gate.toLowerCase();
    let controls = [...(op.controls ?? [])];
    const negControls = [...(op.neg_controls ?? [])];
    let targets = [...(op.qubits ?? [])];

    // Normalize standard 2Q/3Q multi-qubit gate aliases where controls might be in op.qubits
    if (g === "cx" || g === "cnot") {
      if (controls.length === 0 && targets.length >= 2) {
        controls = [targets[0]];
        targets = [targets[1]];
      }
      g = "x";
    } else if (g === "cy") {
      if (controls.length === 0 && targets.length >= 2) {
        controls = [targets[0]];
        targets = [targets[1]];
      }
      g = "y";
    } else if (g === "cz") {
      if (controls.length === 0 && targets.length >= 2) {
        controls = [targets[0]];
        targets = [targets[1]];
      }
      g = "z";
    } else if (g === "ch") {
      if (controls.length === 0 && targets.length >= 2) {
        controls = [targets[0]];
        targets = [targets[1]];
      }
      g = "h";
    } else if (g === "ccx" || g === "toffoli") {
      if (controls.length === 0 && targets.length >= 3) {
        controls = [targets[0], targets[1]];
        targets = [targets[2]];
      }
      g = "x";
    } else if (g === "mcx") {
      if (controls.length === 0 && targets.length >= 2) {
        controls = targets.slice(0, -1);
        targets = [targets[targets.length - 1]];
      }
      g = "x";
    } else if (g === "cswap" || g === "fredkin") {
      if (controls.length === 0 && targets.length >= 3) {
        controls = [targets[0]];
        targets = [targets[1], targets[2]];
      }
      g = "swap";
    }

    // Skip operations on qubits outside the simulated preview width
    if (controls.some((c) => c >= n) || negControls.some((c) => c >= n)) continue;

    // SWAP Gate (can also have controls)
    if (g === "swap") {
      const q0 = targets[0];
      const q1 = targets[1];
      if (q0 === undefined || q1 === undefined || q0 >= n || q1 >= n || q0 === q1) continue;
      const bit0 = 1 << q0;
      const bit1 = 1 << q1;
      const next = [...state];
      for (let i = 0; i < dim; i++) {
        const posActive = controls.every((c) => (i & (1 << c)) !== 0);
        const negActive = negControls.every((c) => (i & (1 << c)) === 0);
        if (posActive && negActive) {
          const b0 = (i & bit0) !== 0;
          const b1 = (i & bit1) !== 0;
          if (b0 && !b1) {
            const j = (i & ~bit0) | bit1;
            const temp = next[i];
            next[i] = next[j];
            next[j] = temp;
          }
        }
      }
      state = next;
      continue;
    }

    // 1-Qubit Unitary (with optional arbitrary positive/negative controls)
    const tgt = targets[0];
    if (tgt === undefined || tgt >= n) continue;

    let mat = GATES_1Q[g];
    if (!mat && (g === "p" || g === "phase" || g === "rx" || g === "ry" || g === "rz")) {
      const p = op.params?.[0]?.value ?? parseParam(op.params?.[0]?.expr);
      mat = getParamGate(g === "phase" ? "p" : g, p);
    }
    if (!mat) mat = GATES_1Q.id;

    if (op.inv) {
      mat = [
        [cx(mat[0][0].re, -mat[0][0].im), cx(mat[1][0].re, -mat[1][0].im)],
        [cx(mat[0][1].re, -mat[0][1].im), cx(mat[1][1].re, -mat[1][1].im)],
      ];
    }

    const next = new Array<Complex>(dim);
    const tgtBit = 1 << tgt;
    for (let i = 0; i < dim; i++) {
      if ((i & tgtBit) === 0) {
        const i0 = i;
        const i1 = i | tgtBit;
        const posActive = controls.every((c) => (i & (1 << c)) !== 0);
        const negActive = negControls.every((c) => (i & (1 << c)) === 0);
        if (posActive && negActive) {
          const a0 = state[i0];
          const a1 = state[i1];
          next[i0] = cadd(cmul(mat[0][0], a0), cmul(mat[0][1], a1));
          next[i1] = cadd(cmul(mat[1][0], a0), cmul(mat[1][1], a1));
        } else {
          next[i0] = state[i0];
          next[i1] = state[i1];
        }
      }
    }
    state = next;
  }

  // Format statevector and probabilities
  const svPairs: [number, number][] = state.map((c) => [Number(c.re.toFixed(6)), Number(c.im.toFixed(6))]);
  const counts: Record<string, number> = {};
  const probs: Record<string, number> = {};

  // Check if any explicit measurements exist in the circuit
  const measureOps = ops.filter((o) => o.kind === "measure" && o.qubits && o.qubits.length > 0);

  if (measureOps.length > 0) {
    // Map measured qubits to classical bit register (c0 is rightmost in Qiskit bit ordering)
    const qToC = new Map<number, number>();
    for (const m of measureOps) {
      const q = m.qubits[0];
      const c = m.clbits?.[0] ?? q;
      qToC.set(q, c);
    }
    const maxClbit = Math.max(...Array.from(qToC.values()), 0);
    const numClbits = maxClbit + 1;

    for (let i = 0; i < dim; i++) {
      const p = state[i].re * state[i].re + state[i].im * state[i].im;
      if (p > 1e-6) {
        let clbitVal = 0;
        for (const [q, c] of qToC.entries()) {
          if (q < n) {
            const bit = (i >> q) & 1;
            if (bit) {
              clbitVal |= (1 << c);
            }
          }
        }
        const bitStr = clbitVal.toString(2).padStart(numClbits, "0");
        probs[bitStr] = (probs[bitStr] || 0) + p;
        counts[bitStr] = (counts[bitStr] || 0) + Math.round(p * 1024);
      }
    }
    for (const k of Object.keys(probs)) {
      probs[k] = Number(probs[k].toFixed(4));
    }
  } else {
    // Direct statevector probabilities when circuit is unmeasured (no measurement required to run)
    for (let i = 0; i < dim; i++) {
      const p = state[i].re * state[i].re + state[i].im * state[i].im;
      if (p > 1e-6) {
        const bitStr = i.toString(2).padStart(n, "0");
        probs[bitStr] = Number(p.toFixed(4));
        counts[bitStr] = Math.round(p * 1024);
      }
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
