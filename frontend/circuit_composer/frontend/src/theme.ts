/**
 * The visual language of the canvas, in one place.
 *
 * Every colour and every dimension the composer draws comes from this module,
 * so retuning the look is an edit here rather than a hunt through Grid.tsx or
 * Composer.tsx.
 *
 * The palette follows the reference design: Hadamard is the one red gate, the
 * X family and multi-qubit gates are blue, the standard single-qubit gates are
 * pale blue, rotations and Y are pink, and everything that is not an operation
 * on amplitudes -- initialisation, barrier, measurement, control flow -- is
 * grey. That last grouping is worth keeping: it stops measurement and barriers
 * from reading as though they were unitary gates.
 *
 * Colours are held as CSS custom properties (see styles.css) so the existing
 * light theme still works; the dark values below are the reference.
 */

import type { Op } from "./types";

/** Canvas geometry, in pixels. */
export const GEOMETRY = {
  /** Row pitch between qubit wires, and the width of one circuit column. */
  cell: 50,
  /** Left gutter holding the `q[0]` and `c4` labels. */
  gutter: 84,
  /** Height reserved above the first wire for the column ruler. */
  header: 18,
  /** Corner radius of a gate tile. Near-square, per the reference. */
  radius: 3,
  /** A gate tile is 40x40 inside a 50px row. */
  tile: 40,
  /** Space between the last qubit wire and the classical register. */
  registerGap: 16,
  /** Separation of the two strokes of the classical double line. */
  doubleLineGap: 1.5,
  /** Diameter of the circular control at the right end of each wire. */
  endpoint: 40,
} as const;

/**
 * Gate families.
 *
 * `fg` is the ink used on the tile. Only Hadamard takes light ink; every other
 * family sits on a light enough fill to need dark ink for contrast.
 */
export const FAMILY = {
  /** Hadamard — the one red gate. Light ink. */
  hadamard: { bg: "#F84D63", fg: "#FFFFFF" },
  /** X, controlled-X, controlled-Y, SWAP, identity. */
  xFamily: { bg: "#4385F5", fg: "#14202B" },
  /** T, S, Z, T†, S†, P, RZ — the standard single-qubit gates. */
  single: { bg: "#B5E1F6", fg: "#14202B" },
  /** √X, Y, RX, RY — rotations and Y. */
  rotation: { bg: "#F66DB8", fg: "#14202B" },
  /** Initialisation, barrier, measurement, control flow. */
  structural: { bg: "#A2A9AE", fg: "#14202B" },
} as const;

const X_FAMILY = new Set(["x", "swap", "id", "i"]);
const SINGLE = new Set(["t", "s", "z", "tdg", "sdg", "p", "rz"]);
const ROTATION = new Set(["sx", "sxdg", "y", "rx", "ry"]);

/** Which family a placed op belongs to. */
export function familyOf(op: Op): (typeof FAMILY)[keyof typeof FAMILY] {
  if (op.kind === "measure" || op.kind === "reset" || op.kind === "barrier") return FAMILY.structural;
  if (op.kind === "if" || op.kind === "for" || op.kind === "while" || op.kind === "box") {
    return FAMILY.structural;
  }
  const g = (op.gate ?? "").toLowerCase();
  if (g === "h") return FAMILY.hadamard;
  // A controlled X or Y is drawn in the blue family like plain X: the control
  // dot is what marks it as controlled, not the colour of the target.
  if (X_FAMILY.has(g)) return FAMILY.xFamily;
  if (op.controls.length > 0 && (g === "y" || g === "z")) return FAMILY.xFamily;
  if (SINGLE.has(g)) return FAMILY.single;
  if (ROTATION.has(g)) return FAMILY.rotation;
  return FAMILY.single;
}

export function gateColour(op: Op): string {
  return familyOf(op).bg;
}

export function gateForeground(op: Op): string {
  return familyOf(op).fg;
}

export type GateShape =
  /** A filled rounded tile bearing the gate's name. */
  | "tile"
  /** The ⊕ target marker of a controlled gate. */
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
 * Shape is kept separate from colour so that a CNOT can be blue-with-a-⊕ and a
 * measurement grey-with-a-meter without either one special-casing the other in
 * the renderer.
 */
export function gateShape(op: Op): GateShape {
  if (op.kind === "measure") return "meter";
  if (op.kind === "barrier") return "barrier";
  if (op.body.length > 0 || op.else_body.length > 0 || op.kind === "box") return "block";

  const g = (op.gate ?? "").toLowerCase();
  // A controlled X or Y is drawn the way every textbook draws it: a circled
  // target, not a tile with a letter on it. Rendering it as a plain tile made
  // a reversed control/target impossible to spot.
  if (op.controls.length > 0 && (g === "x" || g === "y" || g === "z")) return "target";
  if (g === "swap" && op.qubits.length === 2) return "swap";
  return "tile";
}

/** The short name printed on a tile. */
export function gateText(op: Op): string {
  switch (op.kind) {
    case "gate": {
      const g = (op.gate ?? "").toUpperCase();
      const names: Record<string, string> = {
        ID: "I",
        SDG: "S†",
        TDG: "T†",
        SX: "√X",
        SXDG: "√X†",
      };
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

/**
 * Palette button styling, keyed by palette id.
 *
 * The palette buttons in the reference are coloured by the same family rules as
 * the gates they place, which is the point: the button is a preview of what
 * lands on the canvas.
 */
const PALETTE_FAMILY: Record<string, keyof typeof FAMILY> = {
  h: "hadamard",
  x: "xFamily",
  cx: "xFamily",
  cy: "xFamily",
  swap: "xFamily",
  id: "xFamily",
  t: "single",
  s: "single",
  z: "single",
  tdg: "single",
  sdg: "single",
  p: "single",
  rz: "single",
  sx: "rotation",
  y: "rotation",
  rx: "rotation",
  ry: "rotation",
  measure: "structural",
  reset: "structural",
  barrier: "structural",
  if: "structural",
  for: "structural",
  while: "structural",
  box: "structural",
  ctrl: "xFamily",
};

export function paletteStyle(id: string) {
  return FAMILY[PALETTE_FAMILY[id] ?? "structural"];
}
