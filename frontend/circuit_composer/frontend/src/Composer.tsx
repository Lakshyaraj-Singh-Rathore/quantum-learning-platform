import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import {
  Streamlit,
  StreamlitComponentBase,
  withStreamlitConnection,
} from "streamlit-component-lib"
import type { ComponentProps } from "streamlit-component-lib"
import { BLOCKS, MULTI_PALETTE, PALETTE, STRUCTURAL, WHILE_CAP } from "./types"
import type { CircuitIR, Op, PaletteItem } from "./types"
import {
  circuitIsDynamic,
  compact,
  emptyCircuit,
  hasNestedMeasure,
  makeOp,
  makeParam,
  maxLayer,
  measureAllAppend,
  normalizeTerminalMeasurement,
  paramsFor,
  placeOp,
  requiredClbits,
} from "./ir"
import Grid from "./Grid"
import type { PendingSelection } from "./Grid"
import BlockEditor from "./BlockEditor"

/** Walk an index path (["body",0,"else_body",1]) down to a nested op. */
type PathStep = { branch: "body" | "else_body"; index: number }

function getAtPath(ops: Op[], rootIndex: number, path: PathStep[]): Op | null {
  let cur = ops[rootIndex]
  if (!cur) return null
  for (const step of path) {
    cur = cur[step.branch][step.index]
    if (!cur) return null
  }
  return cur
}

function setAtPath(ops: Op[], rootIndex: number, path: PathStep[], next: Op): Op[] {
  const clone = [...ops]
  if (path.length === 0) {
    clone[rootIndex] = next
    return clone
  }
  const rebuild = (op: Op, depth: number): Op => {
    const step = path[depth]
    const branch = [...op[step.branch]]
    branch[step.index] =
      depth === path.length - 1 ? next : rebuild(branch[step.index], depth + 1)
    return { ...op, [step.branch]: branch }
  }
  clone[rootIndex] = rebuild(clone[rootIndex], 0)
  return clone
}

function ComposerInner({ args, theme }: ComponentProps) {
  const incoming = (args["value"] ?? null) as CircuitIR | null
  const initial = useMemo<CircuitIR>(
    () => (incoming && incoming.ops ? incoming : emptyCircuit(args["nQubits"] ?? 2)),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  )

  const [ir, setIr] = useState<CircuitIR>(initial)
  const [dragging, setDragging] = useState<PaletteItem | null>(null)
  const [selectedTool, setSelectedTool] = useState<PaletteItem | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [pending, setPending] = useState<PendingSelection | null>(null)
  const [paramExpr, setParamExpr] = useState("pi/2")
  const [error, setError] = useState("")
  const [notice, setNotice] = useState("")
  const [editing, setEditing] = useState<{ rootIndex: number; path: PathStep[] } | null>(null)

  const lastSent = useRef<string>("")

  // theme -> css variables
  useEffect(() => {
    document.body.classList.toggle("dark", theme?.base === "dark")
  }, [theme])

  useEffect(() => {
    Streamlit.setFrameHeight()
  })

  /** Push the circuit back to Python (only when it actually changed). */
  const commit = useCallback((next: CircuitIR) => {
    const payload = { ...next, n_clbits: Math.max(requiredClbits(next), 1) }
    const json = JSON.stringify(payload)
    if (json !== lastSent.current) {
      lastSent.current = json
      Streamlit.setComponentValue(payload)
    }
  }, [])

  useEffect(() => {
    commit(ir)
  }, [ir, commit])

  const nCols = Math.max(maxLayer(ir.ops) + 2, 8) // auto-grow right

  const update = (fn: (prev: CircuitIR) => CircuitIR) => {
    setError("")
    setIr((prev) => {
      try {
        return fn(prev)
      } catch (e) {
        setError(String((e as Error).message))
        return prev
      }
    })
  }

  /** Build the op for a palette item dropped on (qubit, layer). */
  const buildOp = (item: PaletteItem, qubit: number): Op | null => {
    if (item.kind === "gate" && item.gate) {
      const n = paramsFor(item.gate)
      const params = n ? [makeParam(paramExpr)] : []
      return makeOp("gate", { gate: item.gate, qubits: [qubit], params })
    }
    if (item.kind === "measure") return makeOp("measure", { qubits: [qubit], clbits: [qubit] })
    if (item.kind === "reset") return makeOp("reset", { qubits: [qubit] })
    if (item.kind === "barrier") return makeOp("barrier", {})
    if (item.kind === "if")
      return makeOp("if", {
        condition: { type: "bit_eq", bit: 0, value: 1 },
        body: [makeOp("gate", { gate: "x", qubits: [qubit] })],
      })
    if (item.kind === "for")
      return makeOp("for", {
        loop_n: 2,
        body: [makeOp("gate", { gate: "x", qubits: [qubit] })],
      })
    if (item.kind === "while")
      return makeOp("while", {
        loop_bit: 0,
        loop_value: 1,
        condition: { type: "bit_eq", bit: 0, value: 1 },
        body: [makeOp("gate", { gate: "x", qubits: [qubit] })],
      })
    if (item.kind === "box")
      return makeOp("box", {
        box_name: "box",
        body: [makeOp("gate", { gate: "x", qubits: [qubit] })],
      })
    return null
  }

  const handleDrop = (qubit: number, layer: number) => {
    const item = dragging ?? selectedTool
    setDragging(null)
    if (!item) return

    // "Control+" adds a control to the currently selected gate.
    if (item.id === "ctrl") {
      if (!selectedId) {
        setError("Select a gate first, then use Control+ and click a control qubit.")
        return
      }
      update((prev) => {
        const ops = prev.ops.map((o) => {
          if (o.id !== selectedId) return o
          if (o.qubits.includes(qubit) || o.controls.includes(qubit)) return o
          return { ...o, controls: [...o.controls, qubit] }
        })
        return { ...prev, ops }
      })
      return
    }

    try {
      const op = buildOp(item, qubit)
      if (!op) return

      // multi-qubit palette items enter a click-to-pick phase
      if (item.controls && item.controls !== 0) {
        update((prev) => ({ ...prev, ops: placeOp(prev, { ...op, layer }, layer) }))
        setPending({ op: { ...op, layer }, need: item.controls, mode: "controls" })
        setNotice(
          item.controls < 0
            ? "Click control qubits in the same column, then press Done."
            : `Click ${item.controls} control qubit${item.controls > 1 ? "s" : ""} in the same column.`,
        )
        return
      }
      if (item.targets === 2) {
        update((prev) => ({ ...prev, ops: placeOp(prev, { ...op, layer }, layer) }))
        setPending({ op: { ...op, layer }, need: 1, mode: "target2" })
        setNotice("Click the second SWAP qubit.")
        return
      }

      update((prev) => ({ ...prev, ops: placeOp(prev, { ...op, layer }, layer) }))
    } catch (e) {
      setError(String((e as Error).message))
    }
  }

  /** Click during a pending control/target selection. */
  const handlePick = (qubit: number) => {
    if (!pending) return
    const next: Op =
      pending.mode === "controls"
        ? { ...pending.op, controls: [...pending.op.controls, qubit] }
        : { ...pending.op, qubits: [...pending.op.qubits, qubit] }

    update((prev) => ({
      ...prev,
      ops: prev.ops.map((o) => (o.id === next.id ? next : o)),
    }))

    const got = pending.mode === "controls" ? next.controls.length : next.qubits.length - 1
    if (pending.need > 0 && got >= pending.need) {
      setPending(null)
      setNotice("")
    } else {
      setPending({ ...pending, op: next })
    }
  }

  const finishPick = () => {
    if (pending && pending.mode === "controls" && pending.op.controls.length === 0) {
      // no controls picked -> leave the bare gate in place
      setNotice("No controls added; the gate was left uncontrolled.")
    }
    setPending(null)
    setNotice("")
  }

  const moveOp = (id: string, qubit: number, layer: number) => {
    update((prev) => {
      const op = prev.ops.find((o) => o.id === id)
      if (!op) return prev
      const delta = qubit - (op.qubits[0] ?? 0)
      const moved: Op = {
        ...op,
        qubits: op.qubits.map((q) => q + delta),
        controls: op.controls.map((q) => q + delta),
      }
      const all = [...moved.qubits, ...moved.controls]
      if (all.some((q) => q < 0 || q >= prev.n_qubits)) return prev
      return { ...prev, ops: placeOp({ ...prev, ops: prev.ops }, moved, layer) }
    })
  }

  const deleteOp = (id: string) => {
    update((prev) => ({ ...prev, ops: prev.ops.filter((o) => o.id !== id) }))
    if (selectedId === id) setSelectedId(null)
  }

  const dynamic = circuitIsDynamic(ir)
  const nested = hasNestedMeasure(ir.ops)

  const editingOp = editing ? getAtPath(ir.ops, editing.rootIndex, editing.path) : null

  const paletteChip = (item: PaletteItem) => (
    <div
      key={item.id}
      className={`chip${selectedTool?.id === item.id ? " selected" : ""}`}
      style={{ background: item.color }}
      draggable
      title={item.hint}
      onDragStart={() => setDragging(item)}
      onDragEnd={() => setDragging(null)}
      onClick={() => setSelectedTool(selectedTool?.id === item.id ? null : item)}
    >
      {item.label}
    </div>
  )

  return (
    <div className="composer">
      {/* toolbar */}
      <div className="toolbar">
        <button
          className="tb"
          onClick={() =>
            update((prev) => ({
              ...prev,
              n_qubits: Math.min(prev.n_qubits + 1, 15),
              n_clbits: Math.max(prev.n_clbits, Math.min(prev.n_qubits + 1, 15)),
            }))
          }
        >
          + Qubit
        </button>
        <button
          className="tb"
          disabled={ir.n_qubits <= 1}
          onClick={() =>
            update((prev) => {
              const last = prev.n_qubits - 1
              return {
                ...prev,
                n_qubits: Math.max(1, last),
                ops: prev.ops.filter(
                  (o) => ![...o.qubits, ...o.controls].includes(last),
                ),
              }
            })
          }
        >
          − Qubit
        </button>
        <span className="hint">{ir.n_qubits} qubits</span>

        <div className="spacer" />

        <button className="tb" onClick={() => update((prev) => measureAllAppend(prev))}>
          Measure All (Append)
        </button>
        <button
          className="tb"
          title="Top-level only — never touches measurements inside blocks"
          onClick={() => {
            update((prev) => normalizeTerminalMeasurement(prev))
            if (dynamic)
              setNotice(
                "Normalized to a single terminal measurement layer. Note: this changes the semantics of a dynamic circuit, whose mid-circuit measurements drive control flow.",
              )
          }}
        >
          Normalize Terminal Measurement
        </button>
        <button className="tb" onClick={() => update((prev) => ({ ...prev, ops: compact(prev.ops) }))}>
          Compact
        </button>
        <button
          className="tb danger"
          onClick={() => update((prev) => ({ ...prev, ops: [] }))}
        >
          Clear
        </button>
      </div>

      {/* palette */}
      <div>
        <div className="palette-group">
          <span className="palette-label">Gates</span>
          {PALETTE.map(paletteChip)}
        </div>
        <div className="palette-group">
          <span className="palette-label">Multi-qubit</span>
          {MULTI_PALETTE.map(paletteChip)}
        </div>
        <div className="palette-group">
          <span className="palette-label">Ops</span>
          {STRUCTURAL.map(paletteChip)}
          {BLOCKS.map(paletteChip)}
        </div>
        <div className="palette-group">
          <span className="palette-label">Param</span>
          <input
            className="field"
            style={{
              padding: "5px 8px",
              border: "1px solid var(--line)",
              borderRadius: 6,
              background: "var(--bg)",
              color: "var(--fg)",
              width: 160,
            }}
            value={paramExpr}
            onChange={(e) => setParamExpr(e.target.value)}
            title="Used for P/RX/RY/RZ. Only pi, numbers and + - * / ( )"
          />
          <span className="hint">
            used by P/RX/RY/RZ — only <code>pi</code>, numbers and <code>+ - * / ( )</code>
          </span>
        </div>
      </div>

      {pending && (
        <div className="banner info">
          {notice}{" "}
          <button className="tb" onClick={finishPick} style={{ marginLeft: 8 }}>
            Done
          </button>
        </div>
      )}
      {!pending && notice && <div className="banner warn">{notice}</div>}
      {error && <div className="banner err">{error}</div>}
      {dynamic && (
        <div className="banner info">
          <strong>Dynamic circuit</strong> — executes on the Qiskit dynamic engine (max 15
          qubits, while loops capped at {WHILE_CAP} iterations).
        </div>
      )}
      {nested && (
        <div className="banner warn">
          This circuit has measurements inside blocks. “Normalize Terminal Measurement” only
          affects top-level measurements and will leave those untouched.
        </div>
      )}

      <Grid
        ir={ir}
        nCols={nCols}
        selectedId={selectedId}
        pending={pending}
        dragging={dragging}
        onDropAt={handleDrop}
        onPick={handlePick}
        onSelect={setSelectedId}
        onDelete={deleteOp}
        onMoveOp={moveOp}
        onOpenBlock={(id) => {
          const idx = ir.ops.findIndex((o) => o.id === id)
          if (idx >= 0) setEditing({ rootIndex: idx, path: [] })
        }}
      />

      <div className="hint">
        Drag a gate onto the grid (or click it, then click a cell). Dropping onto an occupied
        column inserts a new column globally, shifting everything to the right. Drag a placed
        gate to move it. Click a block to edit its contents.
      </div>

      {editing && editingOp && (
        <BlockEditor
          ir={ir}
          op={editingOp}
          trail={[
            "circuit",
            ...editing.path.map((s) => (s.branch === "body" ? "then" : "else")),
            editingOp.kind,
          ]}
          onChange={(next) =>
            update((prev) => ({
              ...prev,
              ops: setAtPath(prev.ops, editing.rootIndex, editing.path, next),
            }))
          }
          onDescend={(branch, index) =>
            setEditing({ ...editing, path: [...editing.path, { branch, index }] })
          }
          onClose={() => {
            if (editing.path.length > 0)
              setEditing({ ...editing, path: editing.path.slice(0, -1) })
            else setEditing(null)
          }}
        />
      )}
    </div>
  )
}

/** Class wrapper required by withStreamlitConnection. */
class Composer extends StreamlitComponentBase {
  public render() {
    return <ComposerInner {...(this.props as ComponentProps)} />
  }
}

export default withStreamlitConnection(Composer)
