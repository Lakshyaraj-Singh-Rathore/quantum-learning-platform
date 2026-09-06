/** Mirrors backend/app/quantum/ir.py so the JSON round-trips unchanged. */

export interface Param {
  expr: string
  value: number
}

export type ConditionType = "bit_eq" | "bitstring_eq" | "true"

export interface Condition {
  type: ConditionType
  bit?: number | null
  start?: number | null
  end?: number | null
  value?: string | number | null
}

export type OpKind =
  | "gate"
  | "measure"
  | "reset"
  | "barrier"
  | "if"
  | "for"
  | "while"
  | "box"

export interface Op {
  id: string
  kind: OpKind
  gate?: string | null
  qubits: number[]
  controls: number[]
  params: Param[]
  clbits: number[]
  layer: number
  condition?: Condition | null
  body: Op[]
  else_body: Op[]
  loop_n?: number | null
  loop_var: string
  loop_bit?: number | null
  loop_value: number
  box_name?: string | null
}

export interface CircuitIR {
  name: string
  n_qubits: number
  n_clbits: number
  ops: Op[]
  [key: string]: unknown
}

/** Base gates accepted by the backend GATE_SET. */
export const GATE_SET = [
  "h",
  "x",
  "y",
  "z",
  "id",
  "swap",
  "s",
  "sdg",
  "t",
  "tdg",
  "sx",
  "p",
  "rx",
  "ry",
  "rz",
] as const

/** How many params each gate takes (GATE_PARAMS). */
export const GATE_PARAMS: Record<string, number> = {
  p: 1,
  rx: 1,
  ry: 1,
  rz: 1,
}

export interface PaletteItem {
  id: string
  label: string
  /** base gate name, or undefined for non-gate ops */
  gate?: string
  kind: OpKind
  /** number of control qubits the palette entry implies (-1 = arbitrary/MCX) */
  controls?: number
  /** number of target qubits */
  targets?: number
  hint: string
  color: string
}

export const PALETTE: PaletteItem[] = [
  { id: "h", label: "H", gate: "h", kind: "gate", hint: "Hadamard", color: "#6366f1" },
  { id: "x", label: "X", gate: "x", kind: "gate", hint: "Pauli-X / NOT", color: "#0ea5e9" },
  { id: "y", label: "Y", gate: "y", kind: "gate", hint: "Pauli-Y", color: "#0ea5e9" },
  { id: "z", label: "Z", gate: "z", kind: "gate", hint: "Pauli-Z", color: "#0ea5e9" },
  { id: "id", label: "I", gate: "id", kind: "gate", hint: "Identity", color: "#94a3b8" },
  { id: "s", label: "S", gate: "s", kind: "gate", hint: "Phase S", color: "#8b5cf6" },
  { id: "sdg", label: "S†", gate: "sdg", kind: "gate", hint: "S dagger", color: "#8b5cf6" },
  { id: "t", label: "T", gate: "t", kind: "gate", hint: "T gate", color: "#8b5cf6" },
  { id: "tdg", label: "T†", gate: "tdg", kind: "gate", hint: "T dagger", color: "#8b5cf6" },
  { id: "sx", label: "√X", gate: "sx", kind: "gate", hint: "Sqrt-X", color: "#8b5cf6" },
  { id: "p", label: "P(λ)", gate: "p", kind: "gate", hint: "Phase(λ)", color: "#a855f7" },
  { id: "rx", label: "RX(θ)", gate: "rx", kind: "gate", hint: "Rotation X", color: "#a855f7" },
  { id: "ry", label: "RY(θ)", gate: "ry", kind: "gate", hint: "Rotation Y", color: "#a855f7" },
  { id: "rz", label: "RZ(θ)", gate: "rz", kind: "gate", hint: "Rotation Z", color: "#a855f7" },
]

export const MULTI_PALETTE: PaletteItem[] = [
  {
    id: "cx",
    label: "CNOT",
    gate: "x",
    kind: "gate",
    controls: 1,
    hint: "Drop on target, then click 1 control",
    color: "#14b8a6",
  },
  {
    id: "ccx",
    label: "Toffoli",
    gate: "x",
    kind: "gate",
    controls: 2,
    hint: "Drop on target, then click 2 controls",
    color: "#14b8a6",
  },
  {
    id: "mcx",
    label: "MCX",
    gate: "x",
    kind: "gate",
    controls: -1,
    hint: "Drop on target, then click any controls, then Done",
    color: "#14b8a6",
  },
  {
    id: "swap",
    label: "SWAP",
    gate: "swap",
    kind: "gate",
    targets: 2,
    hint: "Drop on first qubit, then click the second",
    color: "#f59e0b",
  },
  {
    id: "ctrl",
    label: "Control+",
    kind: "gate",
    controls: -1,
    hint: "Add a control to an existing gate",
    color: "#14b8a6",
  },
]

export const STRUCTURAL: PaletteItem[] = [
  { id: "measure", label: "Measure", kind: "measure", hint: "Measure qubit → clbit", color: "#334155" },
  { id: "reset", label: "Reset", kind: "reset", hint: "Reset to |0>", color: "#475569" },
  { id: "barrier", label: "Barrier", kind: "barrier", hint: "Barrier", color: "#64748b" },
]

export const BLOCKS: PaletteItem[] = [
  { id: "if", label: "If / Else", kind: "if", hint: "Classically conditioned block", color: "#dc2626" },
  { id: "for", label: "For", kind: "for", hint: "for i in [0..N)", color: "#ea580c" },
  { id: "while", label: "While", kind: "while", hint: "while (c[i]==v), capped at 32", color: "#b91c1c" },
  { id: "box", label: "Box", kind: "box", hint: "Named grouping box", color: "#0f766e" },
]

export const WHILE_CAP = 32
