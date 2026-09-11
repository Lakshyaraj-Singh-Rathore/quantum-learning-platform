import { useMemo } from "react"
import type { CircuitIR, Op, PaletteItem } from "./types"
import { describeCondition, involvedQubits, range, rowSpan } from "./ir"

const CELL = 46
const GUTTER = 62

export interface PendingSelection {
  op: Op
  need: number // -1 = arbitrary
  mode: "controls" | "target2"
}

interface Props {
  ir: CircuitIR
  nCols: number
  selectedId: string | null
  pending: PendingSelection | null
  dragging: PaletteItem | null
  onDropAt: (qubit: number, layer: number) => void
  onPick: (qubit: number) => void
  onSelect: (id: string | null) => void
  onDelete: (id: string) => void
  onOpenBlock: (id: string) => void
  onMoveOp: (id: string, qubit: number, layer: number) => void
}

function label(op: Op): string {
  switch (op.kind) {
    case "gate": {
      const g = (op.gate ?? "").toUpperCase()
      // A controlled X is drawn as the standard ⊕ target marker. Showing a
      // plain "X" box made a CNOT look identical whichever way round it was,
      // so a reversed control/target was impossible to spot on the grid.
      if (g === "X" && op.controls.length) return "⊕"
      const names: Record<string, string> = { ID: "I", SDG: "S†", TDG: "T†", SX: "√X" }
      const base = names[g] ?? g
      if (op.params.length) return `${base}(${op.params[0].expr})`
      return base
    }
    case "measure":
      return "M"
    case "reset":
      return "|0⟩"
    case "barrier":
      return "‖"
    case "if":
      return `if ${describeCondition(op.condition)}`
    case "for":
      return `for ${op.loop_var}<${op.loop_n}`
    case "while":
      return `while ${describeCondition(op.condition)}`
    case "box":
      return `box ${op.box_name ?? ""}`
    default:
      return op.kind
  }
}

function colorOf(op: Op): string {
  if (op.kind === "measure") return "#334155"
  if (op.kind === "reset") return "#475569"
  if (op.kind === "barrier") return "#64748b"
  if (op.kind === "if") return "#dc2626"
  if (op.kind === "for") return "#ea580c"
  if (op.kind === "while") return "#b91c1c"
  if (op.kind === "box") return "#0f766e"
  const g = op.gate ?? ""
  if (g === "h") return "#6366f1"
  if (["x", "y", "z"].includes(g)) return op.controls.length ? "#14b8a6" : "#0ea5e9"
  if (g === "swap") return "#f59e0b"
  if (g === "id") return "#94a3b8"
  if (["p", "rx", "ry", "rz"].includes(g)) return "#a855f7"
  return "#8b5cf6"
}

export default function Grid(props: Props) {
  const { ir, nCols, selectedId, pending, dragging } = props
  const rows = ir.n_qubits
  const width = GUTTER + nCols * CELL + 20
  const height = 18 + rows * CELL + 6

  const isBlock = (op: Op) => op.body.length > 0 || op.else_body.length > 0 || op.kind === "box"

  /** Rows that are legal control/target picks for the pending selection. */
  const pickable = useMemo(() => {
    if (!pending) return new Set<number>()
    const used = new Set(involvedQubits(pending.op))
    return new Set(range(0, rows - 1).filter((q) => !used.has(q)))
  }, [pending, rows])

  return (
    <div className="grid-scroll">
      <div className="grid" style={{ width, height, position: "relative" }}>
        {/* column headers */}
        {range(0, nCols - 1).map((c) => (
          <div
            key={`h${c}`}
            className="colhead"
            style={{ position: "absolute", left: GUTTER + c * CELL, top: 0, width: CELL }}
          >
            {c}
          </div>
        ))}

        {/* qubit labels + wires */}
        {range(0, rows - 1).map((q) => (
          <div key={`w${q}`}>
            <div
              className="qlabel"
              style={{ position: "absolute", left: 0, top: 18 + q * CELL, width: GUTTER }}
            >
              q[{q}]
            </div>
            <div
              className="wire"
              style={{ left: GUTTER, top: 18 + q * CELL + CELL / 2 - 1, width: nCols * CELL }}
            />
          </div>
        ))}

        {/* drop / pick cells */}
        {range(0, rows - 1).map((q) =>
          range(0, nCols - 1).map((c) => {
            const canPick = pending != null && pickable.has(q)
            return (
              <div
                key={`c${q}-${c}`}
                className={`cell${dragging ? " drop" : ""}${canPick ? " pickable" : ""}`}
                style={{ position: "absolute", left: GUTTER + c * CELL, top: 18 + q * CELL }}
                onDragOver={(e) => {
                  if (dragging) e.preventDefault()
                }}
                onDrop={(e) => {
                  e.preventDefault()
                  const moving = e.dataTransfer.getData("op-id")
                  if (moving) props.onMoveOp(moving, q, c)
                  else props.onDropAt(q, c)
                }}
                onClick={() => {
                  if (canPick) props.onPick(q)
                  else if (!pending) props.onSelect(null)
                }}
              />
            )
          }),
        )}

        {/* control connector lines + dots */}
        {ir.ops.map((op) => {
          if (!op.controls.length || isBlock(op)) return null
          const all = [...op.controls, ...op.qubits]
          const lo = Math.min(...all)
          const hi = Math.max(...all)
          return (
            <div key={`ctl${op.id}`}>
              <div
                className="ctrl-line"
                style={{
                  left: GUTTER + op.layer * CELL + CELL / 2 - 1,
                  top: 18 + lo * CELL + CELL / 2,
                  height: (hi - lo) * CELL,
                }}
              />
              {op.controls.map((q) => (
                <div
                  key={`d${op.id}-${q}`}
                  className="ctrl-dot"
                  style={{
                    left: GUTTER + op.layer * CELL + CELL / 2 - 6.5,
                    top: 18 + q * CELL + CELL / 2 - 6.5,
                  }}
                  title={`control q[${q}]`}
                />
              ))}
            </div>
          )
        })}

        {/* ops */}
        {ir.ops.map((op) => {
          const block = isBlock(op)
          const [lo, hi] = rowSpan(op, rows)
          const top = 18 + lo * CELL
          const h = (hi - lo + 1) * CELL

          if (block) {
            return (
              <div
                key={op.id}
                className="block-box"
                style={{
                  left: GUTTER + op.layer * CELL + 2,
                  top: top + 3,
                  width: CELL - 4,
                  height: h - 6,
                  borderColor: colorOf(op),
                }}
                title={`${label(op)} — click to edit contents`}
                onClick={(e) => {
                  e.stopPropagation()
                  props.onOpenBlock(op.id)
                }}
              >
                <span className="block-label" style={{ background: colorOf(op) }}>
                  {op.kind}
                </span>
              </div>
            )
          }

          // SWAP: draw an × on both target rows
          if (op.gate === "swap" && op.qubits.length === 2) {
            return (
              <div key={op.id}>
                <div
                  className="ctrl-line"
                  style={{
                    left: GUTTER + op.layer * CELL + CELL / 2 - 1,
                    top: 18 + Math.min(...op.qubits) * CELL + CELL / 2,
                    height: Math.abs(op.qubits[0] - op.qubits[1]) * CELL,
                    background: "#f59e0b",
                  }}
                />
                {op.qubits.map((q, i) => (
                  <div
                    key={`${op.id}-${i}`}
                    className={`gate${selectedId === op.id ? " selected" : ""}`}
                    draggable
                    onDragStart={(e) => e.dataTransfer.setData("op-id", op.id)}
                    style={{
                      left: GUTTER + op.layer * CELL + 8,
                      top: 18 + q * CELL + 8,
                      width: CELL - 16,
                      height: CELL - 16,
                      background: "#f59e0b",
                      fontSize: 16,
                    }}
                    onClick={(e) => {
                      e.stopPropagation()
                      props.onSelect(op.id)
                    }}
                    title="SWAP"
                  >
                    ✕
                    {i === 0 && (
                      <span
                        className="del"
                        onClick={(e) => {
                          e.stopPropagation()
                          props.onDelete(op.id)
                        }}
                      >
                        ×
                      </span>
                    )}
                  </div>
                ))}
              </div>
            )
          }

          const q = op.qubits[0] ?? lo
          const text = label(op)
          return (
            <div
              key={op.id}
              className={`gate${selectedId === op.id ? " selected" : ""}`}
              draggable
              onDragStart={(e) => e.dataTransfer.setData("op-id", op.id)}
              style={{
                left: GUTTER + op.layer * CELL + 3,
                top: 18 + q * CELL + 5,
                width: CELL - 6,
                height: CELL - 10,
                background: colorOf(op),
                fontSize: text.length > 4 ? 9 : text.length > 2 ? 10 : 13,
              }}
              title={text}
              onClick={(e) => {
                e.stopPropagation()
                props.onSelect(op.id)
              }}
            >
              {text}
              <span
                className="del"
                onClick={(e) => {
                  e.stopPropagation()
                  props.onDelete(op.id)
                }}
              >
                ×
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
