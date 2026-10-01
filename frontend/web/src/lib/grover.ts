/**
 * Grover's algorithm, ported from frontend/lib/grover_lab.py.
 *
 * Every number the module shows comes from this file, which simulates a real
 * 2ⁿ state vector. Nothing here invents a percentage, and every pure function
 * is pinned against numpy by `npm run golden:grover`.
 *
 * Two framings this module is deliberate about, both inherited from the
 * original:
 *
 * - Grover is never described as "trying all passwords at once". The pipeline
 *   is superposition → oracle → amplification → measurement.
 * - The optimal iteration count is ⌊π/4·√N⌋, not √N. The module lets the
 *   learner overshoot on purpose and watch the probability fall, which is the
 *   part that makes the distinction stick.
 */
import { mulberry32 } from "./demos";
import type { Complex } from "./quantum";

/** Deliberately small: 6 qubits is 64 states, which fits on screen. */
export const MAX_QUBITS = 6;
export const MIN_QUBITS = 1;

export function parsePassword(text: string, nQubits: number): { target: number | null; error: string } {
  const cleaned = text.replace(/\s+/g, "");
  if (!cleaned) return { target: null, error: "Enter a binary password, for example 101101." };
  if (/[^01]/.test(cleaned)) return { target: null, error: "Only the digits 0 and 1 are allowed." };
  if (cleaned.length !== nQubits) {
    return {
      target: null,
      error: `This is a ${nQubits}-qubit search, so the password needs exactly ${nQubits} bit${nQubits === 1 ? "" : "s"} (you gave ${cleaned.length}).`,
    };
  }
  return { target: parseInt(cleaned, 2), error: "" };
}

/**
 * ⌊π/4·√N⌋, the iteration count that maximises success.
 *
 * Not √N: overshooting rotates the state past the target and the success
 * probability falls again, which the module shows explicitly.
 */
export function optimalIterations(nQubits: number): number {
  const nStates = 2 ** nQubits;
  return Math.max(1, Math.floor((Math.PI / 4) * Math.sqrt(nStates)));
}

/** Hadamard on every qubit: equal amplitude 1/√N everywhere. */
export function uniformState(nQubits: number): Complex[] {
  const nStates = 2 ** nQubits;
  const amplitude = 1 / Math.sqrt(nStates);
  return Array.from({ length: nStates }, () => ({ re: amplitude, im: 0 }));
}

/** Flip the phase of the marked state, and nothing else. */
export function applyOracle(state: Complex[], target: number): Complex[] {
  const out = state.map((amplitude) => ({ ...amplitude }));
  out[target] = { re: -out[target].re, im: -out[target].im };
  return out;
}

/** Inversion about the mean: 2|s⟩⟨s| − I. */
export function applyDiffusion(state: Complex[]): Complex[] {
  const n = state.length;
  const meanRe = state.reduce((total, a) => total + a.re, 0) / n;
  const meanIm = state.reduce((total, a) => total + a.im, 0) / n;
  return state.map((a) => ({ re: 2 * meanRe - a.re, im: 2 * meanIm - a.im }));
}

export interface GroverFrame {
  iteration: number;
  stage: "superposition" | "amplified";
  probabilities: number[];
  targetProbability: number;
  amplitudes: Complex[];
}

/** Simulate step by step, recording the state after each stage. */
export function run(nQubits: number, target: number, iterations: number): GroverFrame[] {
  let state = uniformState(nQubits);
  const frames: GroverFrame[] = [
    {
      iteration: 0,
      stage: "superposition",
      probabilities: state.map((a) => a.re * a.re + a.im * a.im),
      targetProbability: state[target].re ** 2 + state[target].im ** 2,
      amplitudes: state.map((a) => ({ ...a })),
    },
  ];

  for (let step = 1; step <= iterations; step += 1) {
    state = applyDiffusion(applyOracle(state, target));
    frames.push({
      iteration: step,
      stage: "amplified",
      probabilities: state.map((a) => a.re * a.re + a.im * a.im),
      targetProbability: state[target].re ** 2 + state[target].im ** 2,
      amplitudes: state.map((a) => ({ ...a })),
    });
  }
  return frames;
}

/** sin²((2k+1)·asin(1/√N)) — the closed form, for cross-checking. */
export function analyticProbability(nQubits: number, iteration: number): number {
  const theta = Math.asin(1 / Math.sqrt(2 ** nQubits));
  return Math.sin((2 * iteration + 1) * theta) ** 2;
}

/**
 * Sample the state, so the learner sees a probabilistic result.
 *
 * Not pinned to numpy: drawing from a categorical distribution needs a
 * reproducible RNG, and numpy's PCG64 cannot be reproduced in JavaScript. The
 * lesson is the distribution, not the draw.
 */
export function measure(state: Complex[], shots: number, seed = 0): Record<number, number> {
  const weights = state.map((a) => a.re * a.re + a.im * a.im);
  const total = weights.reduce((sum, weight) => sum + weight, 0) || 1;
  const random = mulberry32(seed);
  const counts: Record<number, number> = {};
  for (let shot = 0; shot < shots; shot += 1) {
    let threshold = random() * total;
    let index = 0;
    while (index < weights.length - 1 && threshold > weights[index]) {
      threshold -= weights[index];
      index += 1;
    }
    counts[index] = (counts[index] ?? 0) + 1;
  }
  return counts;
}

/** What a sequential search costs, for the comparison panel. */
export function classicalAttempts(nQubits: number, target: number) {
  const nStates = 2 ** nQubits;
  return {
    checkedToFind: target + 1, // scanning 0, 1, 2, … in order
    worstCase: nStates,
    averageCase: Math.floor((nStates + 1) / 2),
  };
}

export const label = (index: number, nQubits: number): string =>
  index.toString(2).padStart(nQubits, "0");
