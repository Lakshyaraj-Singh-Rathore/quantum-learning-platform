/**
 * Single-qubit state maths, mirroring frontend/lib/playground.py.
 *
 * This is a deliberate second implementation: the Python version is verified
 * against analytic physics in test_playground.py, and a test compares the two
 * numerically so they cannot drift apart. The duplication buys continuous
 * 60fps interaction, which a Streamlit rerun per drag cannot give.
 *
 * Convention matches the platform:
 *   |psi> = cos(theta/2)|0> + e^(i*phi) sin(theta/2)|1>
 * with theta from +Z (|0> at theta = 0) and phi anticlockwise from +X.
 */

export type Complex = { re: number; im: number }
export type State = [Complex, Complex]

export const SQRT1_2 = Math.SQRT1_2

const c = (re: number, im = 0): Complex => ({ re, im })
const mul = (a: Complex, b: Complex): Complex => ({
  re: a.re * b.re - a.im * b.im,
  im: a.re * b.im + a.im * b.re,
})
const add = (a: Complex, b: Complex): Complex => ({ re: a.re + b.re, im: a.im + b.im })
const abs2 = (a: Complex): number => a.re * a.re + a.im * a.im

/** Gate matrices, in the same order as the Python GATES dict. */
export const GATES: Record<string, [Complex, Complex, Complex, Complex]> = {
  H: [c(SQRT1_2), c(SQRT1_2), c(SQRT1_2), c(-SQRT1_2)],
  X: [c(0), c(1), c(1), c(0)],
  Y: [c(0), c(0, -1), c(0, 1), c(0)],
  Z: [c(1), c(0), c(0), c(-1)],
  S: [c(1), c(0), c(0), c(0, 1)],
  T: [c(1), c(0), c(0), c(Math.SQRT1_2, Math.SQRT1_2)],
}

export const GATE_HELP: Record<string, string> = {
  H: "Hadamard — creates superposition",
  X: "Pauli-X — the quantum NOT",
  Y: "Pauli-Y — flip plus phase",
  Z: "Pauli-Z — negates |1⟩",
  S: "Phase — quarter turn about Z",
  T: "T — eighth turn about Z",
}

export const LANDMARKS: Record<string, [number, number]> = {
  "|0⟩": [0, 0],
  "|1⟩": [180, 0],
  "|+⟩": [90, 0],
  "|−⟩": [90, 180],
  "|+i⟩": [90, 90],
  "|−i⟩": [90, 270],
}

export function stateFromAngles(thetaDeg: number, phiDeg: number): State {
  const theta = (thetaDeg * Math.PI) / 180
  const phi = (phiDeg * Math.PI) / 180
  return [
    c(Math.cos(theta / 2)),
    mul(c(Math.cos(phi), Math.sin(phi)), c(Math.sin(theta / 2))),
  ]
}

export function applyGates(state: State, gates: string[]): State {
  let out = state
  for (const name of gates) {
    const m = GATES[name]
    if (!m) continue
    out = [add(mul(m[0], out[0]), mul(m[1], out[1])),
           add(mul(m[2], out[0]), mul(m[3], out[1]))]
  }
  return out
}

export function probabilities(state: State): [number, number] {
  return [abs2(state[0]), abs2(state[1])]
}

/** Bloch vector r = (Tr(rho X), Tr(rho Y), Tr(rho Z)) for a pure state. */
export function blochVector(state: State): [number, number, number] {
  const [a, b] = state
  // rho = |psi><psi|, so rho01 = a * conj(b).
  const r01 = mul(a, { re: b.re, im: -b.im })
  return [2 * r01.re, -2 * r01.im, abs2(a) - abs2(b)]
}

/** Angles in degrees, with the unobservable global phase divided out. */
export function blochAngles(state: State): [number, number] {
  let [a, b] = state
  const mag = Math.hypot(a.re, a.im)
  if (mag > 1e-12) {
    const inv = { re: a.re / mag, im: -a.im / mag }
    a = mul(a, inv)
    b = mul(b, inv)
  }
  const theta = 2 * Math.acos(Math.min(1, Math.max(-1, Math.hypot(a.re, a.im))))
  const phi = Math.hypot(b.re, b.im) > 1e-12 ? Math.atan2(b.im, b.re) : 0
  return [(theta * 180) / Math.PI, ((phi * 180) / Math.PI + 360) % 360]
}

export function ketString(state: State, places = 3): string {
  const fmt = (z: Complex): string => {
    if (Math.abs(z.im) < 1e-9) return z.re.toFixed(places)
    if (Math.abs(z.re) < 1e-9) return `${z.im.toFixed(places)}i`
    const sign = z.im >= 0 ? "+" : "−"
    return `(${z.re.toFixed(places)} ${sign} ${Math.abs(z.im).toFixed(places)}i)`
  }
  return `${fmt(state[0])}|0⟩ + ${fmt(state[1])}|1⟩`
}
