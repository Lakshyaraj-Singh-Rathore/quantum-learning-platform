import { useState } from "react"
import type { CircuitIR, Condition, Op } from "./types"
import { GATE_SET, PALETTE, WHILE_CAP } from "./types"
import { describeOp, makeOp, makeParam, paramsFor } from "./ir"

interface Props {
  ir: CircuitIR
  op: Op
  /** breadcrumb of ancestor labels, outermost first */
  trail: string[]
  onChange: (next: Op) => void
  onClose: () => void
  /** descend into a nested block (index path within body/else_body) */
  onDescend: (branch: "body" | "else_body", index: number) => void
}

function BranchEditor({
  ir,
  ops,
  onChange,
  onDescend,
  title,
}: {
  ir: CircuitIR
  ops: Op[]
  onChange: (ops: Op[]) => void
  onDescend: (index: number) => void
  title: string
}) {
  const [gate, setGate] = useState("x")
  const [qubit, setQubit] = useState(0)
  const [param, setParam] = useState("pi/2")
  const [err, setErr] = useState("")

  const nParams = paramsFor(gate)

  const add = () => {
    try {
      const params = nParams ? [makeParam(param)] : []
      const layer = ops.reduce((m, o) => Math.max(m, o.layer), -1) + 1
      onChange([...ops, makeOp("gate", { gate, qubits: [qubit], params, layer })])
      setErr("")
    } catch (e) {
      setErr(String((e as Error).message))
    }
  }

  const addStructural = (kind: "measure" | "reset" | "barrier") => {
    const layer = ops.reduce((m, o) => Math.max(m, o.layer), -1) + 1
    const patch =
      kind === "barrier" ? { layer } : { qubits: [qubit], clbits: [qubit], layer }
    onChange([...ops, makeOp(kind, patch)])
  }

  const addBlock = (kind: "if" | "for" | "while" | "box") => {
    const layer = ops.reduce((m, o) => Math.max(m, o.layer), -1) + 1
    const patch: Partial<Op> = { layer }
    if (kind === "if") patch.condition = { type: "bit_eq", bit: 0, value: 1 }
    if (kind === "for") patch.loop_n = 2
    if (kind === "while") {
      patch.loop_bit = 0
      patch.loop_value = 1
      patch.condition = { type: "bit_eq", bit: 0, value: 1 }
    }
    if (kind === "box") patch.box_name = "box"
    onChange([...ops, makeOp(kind, patch)])
  }

  return (
    <div style={{ marginBottom: 14 }}>
      <div className="field">
        <label>{title}</label>
      </div>
      <div className="row" style={{ alignItems: "flex-end" }}>
        <div className="field">
          <label>Gate</label>
          <select value={gate} onChange={(e) => setGate(e.target.value)}>
            {GATE_SET.map((g) => (
              <option key={g} value={g}>
                {PALETTE.find((p) => p.gate === g)?.label ?? g.toUpperCase()}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label>Qubit</label>
          <select value={qubit} onChange={(e) => setQubit(Number(e.target.value))}>
            {Array.from({ length: ir.n_qubits }, (_, i) => (
              <option key={i} value={i}>
                q[{i}]
              </option>
            ))}
          </select>
        </div>
        {nParams > 0 && (
          <div className="field">
            <label>Param (pi, numbers, + - * / )</label>
            <input value={param} onChange={(e) => setParam(e.target.value)} />
          </div>
        )}
        <div className="field">
          <label>&nbsp;</label>
          <button className="tb primary" onClick={add}>
            Add gate
          </button>
        </div>
      </div>

      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 8 }}>
        <button className="tb" onClick={() => addStructural("measure")}>
          + Measure
        </button>
        <button className="tb" onClick={() => addStructural("reset")}>
          + Reset
        </button>
        <button className="tb" onClick={() => addStructural("barrier")}>
          + Barrier
        </button>
        <button className="tb" onClick={() => addBlock("if")}>
          + If
        </button>
        <button className="tb" onClick={() => addBlock("for")}>
          + For
        </button>
        <button className="tb" onClick={() => addBlock("while")}>
          + While
        </button>
        <button className="tb" onClick={() => addBlock("box")}>
          + Box
        </button>
      </div>

      {err && <div className="banner err">{err}</div>}

      <ul className="oplist">
        {ops.length === 0 && (
          <li>
            <span className="hint">empty</span>
          </li>
        )}
        {ops.map((o, i) => (
          <li key={o.id}>
            <span className="grow">{describeOp(o)}</span>
            {(o.body.length > 0 || o.else_body.length > 0 || ["if", "for", "while", "box"].includes(o.kind)) && (
              <button className="tb" onClick={() => onDescend(i)}>
                Edit inside
              </button>
            )}
            <button
              className="tb danger"
              onClick={() => onChange(ops.filter((x) => x.id !== o.id))}
            >
              Delete
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}

export default function BlockEditor(props: Props) {
  const { ir, op, trail } = props
  const cond: Condition = op.condition ?? { type: "bit_eq", bit: 0, value: 1 }

  const setCond = (patch: Partial<Condition>) =>
    props.onChange({ ...op, condition: { ...cond, ...patch } })

  return (
    <div className="modal-backdrop" onClick={props.onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3>
          Edit block — {trail.join(" › ")}
        </h3>

        {op.kind === "if" && (
          <>
            <div className="row">
              <div className="field">
                <label>Condition type</label>
                <select
                  value={cond.type}
                  onChange={(e) =>
                    setCond({
                      type: e.target.value as Condition["type"],
                      ...(e.target.value === "bit_eq"
                        ? { bit: 0, value: 1, start: null, end: null }
                        : { bit: null, start: 0, end: 2, value: "01" }),
                    })
                  }
                >
                  <option value="bit_eq">single bit — c[i] == v</option>
                  <option value="bitstring_eq">bitstring — c[start:end] == value</option>
                </select>
              </div>
            </div>
            {cond.type === "bit_eq" ? (
              <div className="row">
                <div className="field">
                  <label>Classical bit i</label>
                  <input
                    type="number"
                    min={0}
                    value={cond.bit ?? 0}
                    onChange={(e) => setCond({ bit: Number(e.target.value) })}
                  />
                </div>
                <div className="field">
                  <label>Equals</label>
                  <select
                    value={String(cond.value ?? 1)}
                    onChange={(e) => setCond({ value: Number(e.target.value) })}
                  >
                    <option value="0">0</option>
                    <option value="1">1</option>
                  </select>
                </div>
              </div>
            ) : (
              <div className="row">
                <div className="field">
                  <label>start</label>
                  <input
                    type="number"
                    min={0}
                    value={cond.start ?? 0}
                    onChange={(e) => setCond({ start: Number(e.target.value) })}
                  />
                </div>
                <div className="field">
                  <label>end (exclusive)</label>
                  <input
                    type="number"
                    min={1}
                    value={cond.end ?? 1}
                    onChange={(e) => setCond({ end: Number(e.target.value) })}
                  />
                </div>
                <div className="field">
                  <label>bitstring value</label>
                  <input
                    value={String(cond.value ?? "")}
                    onChange={(e) => setCond({ value: e.target.value })}
                  />
                </div>
              </div>
            )}
          </>
        )}

        {op.kind === "for" && (
          <div className="row">
            <div className="field">
              <label>Loop variable</label>
              <input
                value={op.loop_var}
                onChange={(e) => props.onChange({ ...op, loop_var: e.target.value })}
              />
            </div>
            <div className="field">
              <label>N (compile-time constant)</label>
              <input
                type="number"
                min={0}
                value={op.loop_n ?? 0}
                onChange={(e) => props.onChange({ ...op, loop_n: Number(e.target.value) })}
              />
            </div>
          </div>
        )}

        {op.kind === "while" && (
          <>
            <div className="row">
              <div className="field">
                <label>Watch classical bit</label>
                <input
                  type="number"
                  min={0}
                  value={op.loop_bit ?? 0}
                  onChange={(e) => {
                    const bit = Number(e.target.value)
                    props.onChange({
                      ...op,
                      loop_bit: bit,
                      condition: { type: "bit_eq", bit, value: op.loop_value },
                    })
                  }}
                />
              </div>
              <div className="field">
                <label>Loop while it equals</label>
                <select
                  value={String(op.loop_value)}
                  onChange={(e) => {
                    const v = Number(e.target.value)
                    props.onChange({
                      ...op,
                      loop_value: v,
                      condition: { type: "bit_eq", bit: op.loop_bit ?? 0, value: v },
                    })
                  }}
                >
                  <option value="0">0</option>
                  <option value="1">1</option>
                </select>
              </div>
            </div>
            <div className="banner warn">
              While loops are hard-capped at {WHILE_CAP} iterations at execution time.
            </div>
          </>
        )}

        {op.kind === "box" && (
          <div className="field">
            <label>Box name</label>
            <input
              value={op.box_name ?? ""}
              onChange={(e) => props.onChange({ ...op, box_name: e.target.value })}
            />
          </div>
        )}

        <hr style={{ border: 0, borderTop: "1px solid var(--line)", margin: "12px 0" }} />

        <BranchEditor
          ir={ir}
          ops={op.body}
          title={op.kind === "if" ? "Then branch" : "Body"}
          onChange={(body) => props.onChange({ ...op, body })}
          onDescend={(i) => props.onDescend("body", i)}
        />

        {op.kind === "if" && (
          <BranchEditor
            ir={ir}
            ops={op.else_body}
            title="Else branch"
            onChange={(else_body) => props.onChange({ ...op, else_body })}
            onDescend={(i) => props.onDescend("else_body", i)}
          />
        )}

        <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
          <button className="tb primary" onClick={props.onClose}>
            Done
          </button>
        </div>
      </div>
    </div>
  )
}
