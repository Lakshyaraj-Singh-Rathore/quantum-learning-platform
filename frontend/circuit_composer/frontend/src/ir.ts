import { GATE_PARAMS, WHILE_CAP } from "./types"
import type { CircuitIR, Condition, Op, OpKind, Param } from "./types"

export function uid(): string {
  return Math.random().toString(16).slice(2, 8) + Math.random().toString(16).slice(2, 8)
}

export function makeOp(kind: OpKind, patch: Partial<Op> = {}): Op {
  return {
    id: uid(),
    kind,
    gate: null,
    qubits: [],
    controls: [],
    params: [],
    clbits: [],
    layer: 0,
    condition: null,
    body: [],
    else_body: [],
    loop_n: null,
    loop_var: "i",
    loop_bit: null,
    loop_value: 1,
    box_name: null,
    ...patch,
  }
}

/** Every qubit row an op occupies, including nested block contents. */
export function involvedQubits(op: Op): number[] {
  const out = new Set<number>([...op.qubits, ...op.controls])
  for (const child of [...op.body, ...op.else_body]) {
    for (const q of involvedQubits(child)) out.add(q)
  }
  return [...out]
}

/** The contiguous row span a block/gate should be drawn across. */
export function rowSpan(op: Op, nQubits: number): [number, number] {
  const qs = involvedQubits(op)
  if (qs.length === 0) return [0, Math.max(0, nQubits - 1)]
  return [Math.min(...qs), Math.max(...qs)]
}

export function maxLayer(ops: Op[]): number {
  return ops.reduce((m, o) => Math.max(m, o.layer), -1)
}

/**
 * Global auto-insert column (IBM Composer behaviour): every op at layer >= t
 * shifts one column right. Never a local/partial shift.
 */
export function insertColumn(ops: Op[], t: number): Op[] {
  return ops.map((o) => (o.layer >= t ? { ...o, layer: o.layer + 1 } : o))
}

/** True when placing `qubits` at `layer` would overlap an existing op. */
export function hasCollision(
  ops: Op[],
  layer: number,
  qubits: number[],
  nQubits: number,
  ignoreId?: string,
): boolean {
  const want = new Set(qubits)
  return ops.some((o) => {
    if (o.layer !== layer || o.id === ignoreId) return false
    if (o.kind === "barrier" && o.qubits.length === 0) return true
    const [lo, hi] = rowSpan(o, nQubits)
    // blocks and barriers occupy their whole span, leaf gates only their rows
    const occupies =
      o.kind === "barrier" || o.body.length > 0 || o.else_body.length > 0
        ? range(lo, hi)
        : involvedQubits(o)
    return occupies.some((q) => want.has(q))
  })
}

export function range(lo: number, hi: number): number[] {
  const out: number[] = []
  for (let i = lo; i <= hi; i++) out.push(i)
  return out
}

/**
 * Place an op at a layer, auto-inserting a global column on collision.
 * Returns the new op list.
 */
export function placeOp(ir: CircuitIR, op: Op, layer: number): Op[] {
  const qubits = involvedQubits(op)
  let ops = ir.ops
  if (hasCollision(ops, layer, qubits, ir.n_qubits, op.id)) {
    ops = insertColumn(ops, layer)
  }
  return [...ops.filter((o) => o.id !== op.id), { ...op, layer }]
}

/** Remove empty columns, keeping relative order. */
export function compact(ops: Op[]): Op[] {
  const used = [...new Set(ops.map((o) => o.layer))].sort((a, b) => a - b)
  const remap = new Map(used.map((l, i) => [l, i]))
  return ops.map((o) => ({ ...o, layer: remap.get(o.layer) ?? o.layer }))
}

export function isDynamic(op: Op): boolean {
  if (op.kind === "if" || op.kind === "while") return true
  if (op.condition && op.condition.type !== "true") return true
  return [...op.body, ...op.else_body].some(isDynamic)
}

export function circuitIsDynamic(ir: CircuitIR): boolean {
  return ir.ops.some(isDynamic)
}

/** Number of classical bits the circuit needs. */
export function requiredClbits(ir: CircuitIR): number {
  let n = 0
  const walk = (op: Op) => {
    for (const c of op.clbits) n = Math.max(n, c + 1)
    const cond = op.condition
    if (cond) {
      if (cond.bit != null) n = Math.max(n, cond.bit + 1)
      if (cond.end != null) n = Math.max(n, cond.end)
    }
    ;[...op.body, ...op.else_body].forEach(walk)
  }
  ir.ops.forEach(walk)
  return Math.max(n, ir.n_clbits ?? 0)
}

/**
 * "Measure All (Append)" — dynamic-safe. Appends a measurement layer for every
 * qubit at the end of the circuit. Never deletes an existing measurement.
 */
export function measureAllAppend(ir: CircuitIR): CircuitIR {
  const layer = maxLayer(ir.ops) + 1
  const added: Op[] = []
  for (let q = 0; q < ir.n_qubits; q++) {
    added.push(makeOp("measure", { qubits: [q], clbits: [q], layer }))
  }
  return {
    ...ir,
    n_clbits: Math.max(requiredClbits(ir), ir.n_qubits),
    ops: [...ir.ops, ...added],
  }
}

/**
 * "Normalize Terminal Measurement" — TOP LEVEL ONLY. Strips top-level measures
 * and appends exactly one terminal measurement layer. Measurements nested
 * inside if/for/while/box bodies are never touched.
 */
export function normalizeTerminalMeasurement(ir: CircuitIR): CircuitIR {
  const kept = ir.ops.filter((o) => o.kind !== "measure")
  const layer = maxLayer(kept) + 1
  const added: Op[] = []
  for (let q = 0; q < ir.n_qubits; q++) {
    added.push(makeOp("measure", { qubits: [q], clbits: [q], layer }))
  }
  return {
    ...ir,
    n_clbits: Math.max(requiredClbits({ ...ir, ops: kept }), ir.n_qubits),
    ops: compact([...kept, ...added]),
  }
}

/** True when a nested (non-top-level) measurement exists. */
export function hasNestedMeasure(ops: Op[]): boolean {
  const walk = (op: Op): boolean =>
    [...op.body, ...op.else_body].some((c) => c.kind === "measure" || walk(c))
  return ops.some(walk)
}

// --------------------------------------------------------------- parameters

const PARAM_TOKEN = /^[0-9+\-*/().\s]|pi/

/**
 * Restricted grammar: only `pi`, numbers and + - * / ( ). Variables such as
 * `theta` are rejected, matching backend/app/quantum/params.py.
 */
export function evalParamExpr(expr: string): number {
  const src = expr.trim()
  if (!src) throw new Error("empty expression")
  if (!PARAM_TOKEN.test(src)) throw new Error(`invalid expression: ${expr}`)
  const cleaned = src.toLowerCase().replace(/\bpi\b/g, "PI")
  if (/[a-z_]/.test(cleaned.replace(/PI/g, ""))) {
    throw new Error("only 'pi', numbers and + - * / ( ) are allowed")
  }
  if (!/^[0-9PI+\-*/().\s]+$/.test(cleaned)) {
    throw new Error("only 'pi', numbers and + - * / ( ) are allowed")
  }
  const js = cleaned.replace(/PI/g, String(Math.PI))
  // eslint-disable-next-line no-new-func
  const out = Function(`"use strict";return (${js})`)()
  if (typeof out !== "number" || !isFinite(out)) throw new Error("expression is not finite")
  return out
}

export function makeParam(expr: string): Param {
  return { expr, value: evalParamExpr(expr) }
}

export function paramsFor(gate: string): number {
  return GATE_PARAMS[gate] ?? 0
}

// --------------------------------------------------------------- conditions

export function describeCondition(c?: Condition | null): string {
  if (!c || c.type === "true") return "true"
  if (c.type === "bit_eq") return `c[${c.bit ?? 0}] == ${c.value ?? 1}`
  const start = c.start ?? 0
  const end = c.end ?? start + 1
  return `c[${start}:${end}] == ${c.value}`
}

export function describeOp(op: Op): string {
  switch (op.kind) {
    case "gate": {
      const p = op.params.length ? `(${op.params.map((x) => x.expr).join(", ")})` : ""
      const ctrl = op.controls.length ? `ctrl${op.controls.join(",")}→` : ""
      return `${ctrl}${(op.gate ?? "").toUpperCase()}${p} q${op.qubits.join(",")}`
    }
    case "measure":
      return `measure q${op.qubits[0]} → c${op.clbits[0]}`
    case "reset":
      return `reset q${op.qubits[0]}`
    case "barrier":
      return "barrier"
    case "if":
      return `if (${describeCondition(op.condition)})${op.else_body.length ? " / else" : ""}`
    case "for":
      return `for ${op.loop_var} in [0..${op.loop_n})`
    case "while":
      return `while (${describeCondition(op.condition)}) [cap ${WHILE_CAP}]`
    case "box":
      return `box ${op.box_name ?? ""}`
    default:
      return op.kind
  }
}

export function emptyCircuit(nQubits = 2): CircuitIR {
  return { name: "circuit", n_qubits: nQubits, n_clbits: nQubits, ops: [] }
}
