/**
 * The maths behind the lesson demos, ported from frontend/lib/playground.py.
 *
 * Every pure function here is pinned against numpy by `npm run golden:quantum`
 * (see scripts/golden-quantum.py), so a demo cannot quietly start showing a
 * different number than Streamlit does today.
 *
 * The one deliberate exception is `sample`, which draws random shots. numpy's
 * PCG64 is not reproducible in JavaScript, so the counts differ between the
 * two apps — but that is the point of the demo: at 1024 shots you get roughly
 * 512, not exactly 512. The distribution is what is being taught, and both
 * apps draw from the same binomial.
 */
import {
  blochAngles,
  blochVector,
  cmul,
  cx,
  probabilities,
  reducedDensityMatrix,
  type Complex,
  type Matrix2,
  type Statevector,
} from "./quantum";

export const SQRT1_2 = 1 / Math.sqrt(2);

/** Single-qubit gates the playground offers, matching playground.py exactly. */
export const GATES: Record<string, Matrix2> = {
  H: [
    [cx(SQRT1_2, 0), cx(SQRT1_2, 0)],
    [cx(SQRT1_2, 0), cx(-SQRT1_2, 0)],
  ],
  X: [
    [cx(0, 0), cx(1, 0)],
    [cx(1, 0), cx(0, 0)],
  ],
  Y: [
    [cx(0, 0), cx(0, -1)],
    [cx(0, 1), cx(0, 0)],
  ],
  Z: [
    [cx(1, 0), cx(0, 0)],
    [cx(0, 0), cx(-1, 0)],
  ],
  S: [
    [cx(1, 0), cx(0, 0)],
    [cx(0, 0), cx(0, 1)],
  ],
  T: [
    [cx(1, 0), cx(0, 0)],
    [cx(0, 0), cx(Math.cos(Math.PI / 4), Math.sin(Math.PI / 4))],
  ],
};

export const GATE_HELP: Record<string, string> = {
  H: "Hadamard — turns |0⟩ into an equal superposition",
  X: "Pauli-X — the quantum NOT, flips |0⟩ and |1⟩",
  Y: "Pauli-Y — a flip plus a phase",
  Z: "Pauli-Z — leaves |0⟩ alone, negates |1⟩",
  S: "Phase — a quarter turn about Z",
  T: "T — an eighth turn about Z",
};

/** The six cardinal states, as (theta, phi) in degrees. */
export const LANDMARKS: Record<string, [number, number]> = {
  "|0⟩": [0, 0],
  "|1⟩": [180, 0],
  "|+⟩": [90, 0],
  "|−⟩": [90, 180],
  "|+i⟩": [90, 90],
  "|−i⟩": [90, 270],
};

export function stateFromAngles(thetaDeg: number, phiDeg: number): Statevector {
  const theta = (thetaDeg * Math.PI) / 180;
  const phi = (phiDeg * Math.PI) / 180;
  const alpha = cx(Math.cos(theta / 2), 0);
  const beta = cx(Math.cos(phi) * Math.sin(theta / 2), Math.sin(phi) * Math.sin(theta / 2));
  return [
    [alpha.re, alpha.im],
    [beta.re, beta.im],
  ];
}

/**
 * Normalise a pair of real amplitudes into a valid state. Renormalising
 * quietly is the honest move: the learner's ratio survives and the state stays
 * physical.
 */
export function stateFromAmplitudes(alpha: number, beta: number): Statevector {
  const norm = Math.hypot(alpha, beta);
  if (norm < 1e-12) return [[1, 0], [0, 0]];
  return [
    [alpha / norm, 0],
    [beta / norm, 0],
  ];
}

/** Apply gates left to right, the order they appear on a circuit wire. */
export function applyGates(state: Statevector, gates: string[]): Statevector {
  let [a, b] = state.map(([re, im]) => cx(re, im)) as [Complex, Complex];
  for (const name of gates) {
    const matrix = GATES[name.toUpperCase()];
    if (!matrix) throw new Error(`unknown gate ${name}`);
    const a2 = add(mul(matrix[0][0], a), mul(matrix[0][1], b));
    const b2 = add(mul(matrix[1][0], a), mul(matrix[1][1], b));
    a = a2;
    b = b2;
  }
  return [
    [a.re, a.im],
    [b.re, b.im],
  ];
}

const add = (p: Complex, q: Complex): Complex => cx(p.re + q.re, p.im + q.im);
const mul = (p: Complex, q: Complex): Complex => cmul(p, q);

export function probs(state: Statevector): [number, number] {
  const p = probabilities(state.map(([re, im]) => cx(re, im)));
  return [p[0], p[1]];
}

/** Recover (theta, phi) in degrees from a state vector. blochAngles already
 *  returns degrees, and wraps phi into [0, 360). */
export function blochAnglesOf(state: Statevector): [number, number] {
  const amps = state.map(([re, im]) => cx(re, im));
  const rho = reducedDensityMatrix(amps, 1, 0);
  const [x, y, z] = blochVector(rho);
  const { theta, phi } = blochAngles(x, y, z);
  return [theta, phi];
}

export function blochXYZ(state: Statevector): [number, number, number] {
  const amps = state.map(([re, im]) => cx(re, im));
  return blochVector(reducedDensityMatrix(amps, 1, 0));
}

/** Small deterministic PRNG, so a demo can be re-rolled rather than reloaded. */
export function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/**
 * Measure once. Measurement is destructive: the state left behind is the basis
 * state that was observed, so measuring again gives the same answer forever.
 */
export function collapse(state: Statevector, random: () => number = Math.random): number {
  const [p0] = probs(state);
  return random() < p0 ? 0 : 1;
}

/** Sample `shots` measurements; binomial in P(1), like playground.sample. */
export function sample(state: Statevector, shots: number, seed = 0): { "0": number; "1": number } {
  const [p0] = probs(state);
  const random = mulberry32(seed);
  let ones = 0;
  for (let i = 0; i < shots; i += 1) {
    if (random() >= p0) ones += 1;
  }
  return { "0": shots - ones, "1": ones };
}

/** Two paths meeting at one outcome: amplitudes add, then are squared. */
export function interference(ampA: number, ampB: number) {
  const total = ampA + ampB;
  return {
    amplitude: total,
    probability: total * total,
    classical: ampA * ampA + ampB * ampB,
  };
}

/** Rows for the 2ⁿ growth demo. 16 bytes per complex128 amplitude. */
export function stateSpaceRows(maxQubits = 10) {
  return Array.from({ length: maxQubits }, (_, i) => {
    const n = i + 1;
    const states = 2 ** n;
    return { qubits: n, states, megabytes: (states * 16) / 1e6 };
  });
}

/** Explain Qiskit bit ordering, where qubit 0 is the RIGHTMOST character. */
export function bitstringTable(value: number, nQubits: number) {
  const bits = value.toString(2).padStart(nQubits, "0");
  return bits.split("").map((char, position) => {
    const qubit = nQubits - 1 - position;
    return {
      qubit: `q${qubit}`,
      value: Number(char),
      position: `char ${position} (from the left)`,
      rightmost: qubit === 0,
    };
  });
}

export type { Complex, Statevector, Matrix2 };
