/**
 * The IBM-flavoured look, in one place.
 *
 * This file exists so that matching a reference image is a matter of editing
 * hex values here rather than hunting through Grid.tsx. Every colour and every
 * dimension the circuit canvas draws comes from this module, and nothing in
 * Grid.tsx hard-codes either.
 *
 * The gate palette is not arbitrary decoration. Gates are grouped the way a
 * quantum information theorist would group them:
 *
 *   - Clifford gates (H, X, Y, Z, S, SX, CX, SWAP) generate the stabilizer
 *     group. Circuits built only from these plus measurement are simulable in
 *     polynomial time on a classical computer (Gottesman-Knill).
 *   - Non-Clifford gates (T, TDG, P, RX, RY, RZ, U) take the state out of the
 *     stabilizer set, and that is precisely where classical simulation becomes
 *     exponential in the qubit count.
 *
 * So the colour split visible on the canvas is the same split that decides
 * whether a circuit is cheap or expensive to simulate classically. A learner
 * who notices "my circuit went purple" has noticed something true about it.
 *
 * If these hex values do not match the reference you are working from, this is
 * the only file that needs to change.
 */

import type { Op } from "./types";

/** Canvas geometry, in pixels. */
export const GEOMETRY = {
  /** Width (and row pitch) of one circuit column. */
  cell: 46,
  /** Left label gutter holding `q0`, `c1` and friends. */
  gutter: 62,
  /** Height reserved above the first wire for the column ruler. */
  header: 18,
  /** Corner radius of a gate tile. */
  radius: 6,
  /** Row pitch for classical bits. Tighter than the qubit pitch: a classical
   *  register carries no amplitude, so it does not need the room. */
  clbitCell: 22,
  /** Gap between the last qubit wire and the first classical bit line. */
  registerGap: 14,
  /** Half-gap between the two strokes of a classical double line. */
  doubleLineGap: 1.5,
} as const;

/**
 * Gate colours, by family.
 *
 * `clifford` and `nonClifford` are the two that carry meaning; the rest are
 * structural (measurement, flow control, barriers) and are chosen to sit back
 * visually so they never read as unitary gates.
 */
export const COLOURS = {
  /** H is the gate that creates superposition. Teal, and deliberately distinct
   *  from the other Cliffords: it is usually the first gate anyone places. */
  hadamard: "#0f9d8e",
  /** X / Y / Z / S / SX / SDG — stabilizer generators and their kin. */
  clifford: "#2f6fd0",
  /** T / TDG / P / RX / RY / RZ / U — the gates that break stabilizer
   *  simulation. Violet, so a circuit that leaves the stabilizer set changes
   *  colour as it does so. */
  nonClifford: "#8b5cf6",
  /** Control markers and the vertical line joining a gate to its controls. */
  control: "#14b8a6",
  /** SWAP, which is drawn as two ✕ joined by a line. */
  swap: "#e08a1e",
  /** Measurement. Muted slate: it is not a unitary gate and should not look
   *  like one. */
  measure: "#5b6b7f",
  /** Reset to |0>. */
  reset: "#475569",
  /** Barriers: a scheduling hint to the compiler, not an operation. */
  barrier: "#94a3b8",
  /** Classical flow control (if / for / while). Red, because these are the
   *  only constructs that can change the circuit at run time. */
  flow: "#d1495b",
  /** Named grouping box. */
  box: "#0f766e",
} as const;

/**
 * Per-qubit accent colours, used for the chip beside each `q0` label.
 *
 * Purely to make wires easy to follow by eye across a wide circuit -- they
 * carry no meaning about the qubit itself, which is why a qubit's wire is not
 * tinted with its accent.
 */
const QUBIT_ACCENTS = [
  "#8b5cf6",
  "#0ea5e9",
  "#14b8a6",
  "#f59e0b",
  "#ec4899",
  "#22c55e",
  "#ef4444",
  "#6366f1",
  "#0d9488",
  "#a855f7",
  "#eab308",
  "#3b82f6",
  "#f97316",
  "#10b981",
  "#d946ef",
];

export function qubitAccent(index: number): string {
  return QUBIT_ACCENTS[((index % QUBIT_ACCENTS.length) + QUBIT_ACCENTS.length) % QUBIT_ACCENTS.length];
}

const CLIFFORD = new Set(["x", "y", "z", "s", "sdg", "sx", "sxdg", "id", "i"]);
const NON_CLIFFORD = new Set(["t", "tdg", "p", "rx", "ry", "rz", "u", "u1", "u2", "u3"]);

/** The colour a gate tile is filled with. */
export function gateColour(op: Op): string {
  if (op.kind === "measure") return COLOURS.measure;
  if (op.kind === "reset") return COLOURS.reset;
  if (op.kind === "barrier") return COLOURS.barrier;
  if (op.kind === "if" || op.kind === "while") return COLOURS.flow;
  if (op.kind === "for") return COLOURS.flow;
  if (op.kind === "box") return COLOURS.box;

  const g = (op.gate ?? "").toLowerCase();
  if (g === "h") return COLOURS.hadamard;
  if (g === "swap") return COLOURS.swap;
  if (CLIFFORD.has(g)) return COLOURS.clifford;
  if (NON_CLIFFORD.has(g)) return COLOURS.nonClifford;
  // Anything unrecognised is treated as non-Clifford: the cautious default,
  // since assuming a gate is cheap to simulate is the expensive mistake.
  return COLOURS.nonClifford;
}

export type GateShape =
  /** A filled rounded tile bearing the gate's name. */
  | "tile"
  /** The ⊕ target marker of a controlled-X. */
  | "target"
  /** One half of a SWAP. */
  | "swap"
  /** A measurement meter, wired down to the classical register. */
  | "meter"
  /** A dashed vertical rule. */
  | "barrier"
  /** A classical flow-control block. */
  | "block";

/**
 * How an operation is drawn.
 *
 * Shape is kept separate from colour so that a CNOT can be teal-with-a-dot and
 * a measurement slate-with-a-meter without either one special-casing the other
 * in the renderer.
 */
export function gateShape(op: Op): GateShape {
  if (op.kind === "measure") return "meter";
  if (op.kind === "barrier") return "barrier";
  if (op.kind === "reset") return "tile";
  if (op.body.length > 0 || op.else_body.length > 0 || op.kind === "box") return "block";

  const g = (op.gate ?? "").toLowerCase();
  // A controlled X is drawn the way every textbook and every other composer
  // draws it: a ⊕ on the target, not a box saying "X". Rendering it as a plain
  // tile made a reversed control/target impossible to spot.
  if (g === "x" && op.controls.length > 0) return "target";
  if (g === "swap" && op.qubits.length === 2) return "swap";
  return "tile";
}

/** The short name printed on a tile. */
export function gateText(op: Op): string {
  switch (op.kind) {
    case "gate": {
      const g = (op.gate ?? "").toUpperCase();
      const names: Record<string, string> = { ID: "I", SDG: "S†", TDG: "T†", SX: "√X", SXDG: "√X†" };
      const base = names[g] ?? g;
      if (op.params.length) return `${base}(${op.params[0].expr})`;
      return base;
    }
    case "measure":
      return "M";
    case "reset":
      return "|0⟩";
    case "barrier":
      return "‖";
    default:
      return op.kind;
  }
}
