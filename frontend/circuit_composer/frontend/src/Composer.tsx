import { useCallback, useEffect, useMemo, useRef, useState } from "react"
// NOTE: this file is deliberately host-agnostic.
//
// It is the single implementation of the drag-and-drop grid. It is built into
// the React SPA (frontend/web) through the `@composer` alias, and it knows
// nothing about how any host mounts it: state comes in as props and changes go
// out as callbacks. That is what keeps the physics and the layout in one place
// while the surrounding app is free to change.
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
  paramsFor,
  placeOp,
  requiredClbits,
  describeOp,
  involvedQubits,
  sortOps,
} from "./ir"
import Grid from "./Grid"
import type { PendingSelection } from "./Grid"
import BlockEditor from "./BlockEditor"
import { paletteStyle } from "./theme"
import { EditGatePanel } from "./EditGatePanel"

/** Walk an index path (["body",0,"else_body",1]) down to a nested op. */
/** Floor for the reported iframe height, so a 0 measurement can never
 *  collapse the component into an invisible strip. */
const MIN_FRAME_HEIGHT = 560

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

export interface ComposerProps {
  /** The circuit to show; null/empty starts from `nQubits` empty rows. */
  value?: CircuitIR | null
  nQubits?: number
  /** Called (debounced) whenever the circuit changes. Omit for a read-only grid. */
  onChange?: (ir: CircuitIR) => void
  /** Called with the height the host should reserve. Optional: a host that
     *  lays the grid out itself can ignore it and let the grid size normally. */
  onHeight?: (height: number) => void
  theme?: { base?: string }
}

const ALL_PALETTE_ITEMS: Record<string, PaletteItem> = (() => {
  const m: Record<string, PaletteItem> = {}
  for (const item of [...PALETTE, ...MULTI_PALETTE, ...STRUCTURAL, ...BLOCKS]) m[item.id] = item
  return m
})()

const normalizeOp = (o: Op): Op => {
  return {
    ...makeOp(o.kind || "gate", o),
    qubits: Array.isArray(o.qubits) ? [...o.qubits] : [],
    controls: Array.isArray(o.controls) ? [...o.controls] : [],
    neg_controls: Array.isArray(o.neg_controls) ? [...o.neg_controls] : [],
    params: Array.isArray(o.params) ? [...o.params] : [],
    clbits: Array.isArray(o.clbits) ? [...o.clbits] : [],
    body: Array.isArray(o.body) ? o.body.map(normalizeOp) : [],
    else_body: Array.isArray(o.else_body) ? o.else_body.map(normalizeOp) : [],
  }
}

const sanitizeOps = (ops: Op[], nQubits: number): Op[] => {
  if (!Array.isArray(ops)) return []
  const normalized = ops.map((raw) => {
    const o = normalizeOp(raw)
    if (o.gate === "swap") {
      let q0 = o.qubits[0] ?? 0
      let q1 = o.qubits[1] ?? (nQubits === 2 ? (q0 === 0 ? 1 : 0) : (q0 < nQubits - 1 ? q0 + 1 : q0 - 1))
      if (q0 === q1) {
        q1 = q0 === 0 ? 1 : 0
      }
      return { ...o, qubits: [q0, q1], controls: [] }
    }
    return o
  })

  // Deduplicate exact collisions at the same layer and qubits
  const seen = new Set<string>()
  const deduped: Op[] = []
  for (const op of normalized) {
    const key = `${op.kind}:${op.gate}:${op.layer}:${[...(op.qubits || [])].sort().join(",")}:${[...(op.controls || [])].sort().join(",")}`
    if (!seen.has(key)) {
      seen.add(key)
      deduped.push(op)
    }
  }
  return deduped
}

export function ComposerInner({ value, nQubits, onChange, onHeight, theme }: ComposerProps) {
  const incoming = value ?? null
  const initial = useMemo<CircuitIR>(
    () => {
      const raw = incoming && incoming.ops ? incoming : emptyCircuit(nQubits ?? 2)
      return {
        ...raw,
        ops: sanitizeOps(raw.ops, raw.n_qubits),
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  )

  const [ir, setIr] = useState<CircuitIR>(initial)
  const [dragging, setDragging] = useState<PaletteItem | null>(null)
  const [selectedTool, setSelectedTool] = useState<PaletteItem | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [isEditPanelOpen, setIsEditPanelOpen] = useState(false)
  const [pending, setPending] = useState<PendingSelection | null>(null)
  const [paramExpr, setParamExpr] = useState("pi/2")
  const [error, setError] = useState("")
  const [notice, setNotice] = useState("")
  const [editing, setEditing] = useState<{ rootIndex: number; path: PathStep[] } | null>(null)
  const [mcxCountInput, setMcxCountInput] = useState<number>(2)

  const lastSent = useRef<string>("")
  const rootRef = useRef<HTMLDivElement>(null)
  const lastDropTimeRef = useRef<number>(0)
  const lastMoveTimeRef = useRef<number>(0)

  const handleSelect = (id: string | null) => {
    setSelectedId(id)
    if (!id) {
      setIsEditPanelOpen(false)
    } else {
      const op = ir.ops.find((o) => o.id === id)
      if (op && op.params && op.params.length > 0 && op.params[0]?.expr) {
        setParamExpr(op.params[0].expr)
      }
    }
  }

  const handleUpdateOp = (updated: Op) => {
    update((prev) => ({
      ...prev,
      ops: prev.ops.map((o) => (o.id === updated.id ? updated : o)),
    }))
  }

  const handleParamChange = (newExpr: string) => {
    setParamExpr(newExpr)
    if (selectedId) {
      update((prev) => {
        const op = prev.ops.find((o) => o.id === selectedId)
        if (!op || !op.params || op.params.length === 0) return prev
        const updatedOp: Op = {
          ...op,
          params: [makeParam(newExpr)],
        }
        return {
          ...prev,
          ops: prev.ops.map((o) => (o.id === selectedId ? updatedOp : o)),
        }
      })
    }
  }

  const cancelPending = () => {
    if (!pending) return
    const pendingOp = pending.op
    setPending(null)
    setNotice("")
    update((prev) => ({
      ...prev,
      ops: prev.ops.filter((o) => o.id !== pendingOp.id),
    }))
    if (selectedId === pendingOp.id) setSelectedId(null)
  }

  // theme -> css variables
  useEffect(() => {
    document.body.classList.toggle("dark", theme?.base === "dark")
  }, [theme])

  // The height is measured from document.body.scrollHeight at the moment we
    // call this. If layout is not settled yet (web font still loading, grid not
    // measured) the reported height can be 0 and the host reserves no space at
    // all. Re-measure after paint and whenever the body resizes.
  const resize = useCallback(() => {
    // Never report 0: a host that trusts this number would reserve no space
      // and the grid looks like a blank box with no error anywhere.
    const measured = Math.max(
      document.body.scrollHeight,
      document.documentElement?.scrollHeight ?? 0,
      rootRef.current?.scrollHeight ?? 0,
    )
    // Only hosts that need the height pushed upwards pass the hook; others
      // let the grid size itself, which is why it is optional.
    onHeight?.(Math.max(measured, MIN_FRAME_HEIGHT))
  }, [onHeight])

  useEffect(() => {
    resize()
    const raf = window.requestAnimationFrame(resize)
    const later = window.setTimeout(resize, 250)
    return () => {
      window.cancelAnimationFrame(raf)
      window.clearTimeout(later)
    }
  })

  useEffect(() => {
    if (typeof ResizeObserver === "undefined") return
    const ro = new ResizeObserver(resize)
    ro.observe(document.body)
    if (rootRef.current) ro.observe(rootRef.current)
    return () => ro.disconnect()
  }, [resize])

  // Synchronize internal state when an external actor updates value
  // (e.g. Smart Composer adopting a circuit, Presets like Bell/GHZ, or Import)
  useEffect(() => {
    if (!value) return
    const incomingJson = JSON.stringify(value)
    if (incomingJson !== lastSent.current) {
      lastSent.current = incomingJson
      setIr({
        ...value,
        ops: sanitizeOps(value.ops, value.n_qubits),
      })
      setPending(null)
      setSelectedId(null)
      setError("")
      setNotice("")
    }
  }, [value])

  /** Push the circuit back to host (only when fully formed and actually changed). */
  const commit = useCallback((next: CircuitIR) => {
    // Do not commit incomplete operations (e.g. CNOT control placed, target pending)
    const validOps = next.ops.filter((o) => {
      if (o.kind === "barrier") return true
      return o.qubits && o.qubits.length > 0
    })
    const payload = {
      ...next,
      ops: validOps,
      n_clbits: Math.max(requiredClbits(next), next.n_qubits, 1),
    }
    const json = JSON.stringify(payload)
    if (json !== lastSent.current) {
      lastSent.current = json
      onChange?.(payload)
    }
  }, [onChange])

  // Debounce the trip back to host so bursts of clicks cost one update.
  // CRITICAL: Do not commit while a multi-qubit placement is pending target selection!
  useEffect(() => {
    if (pending) return
    const id = window.setTimeout(() => commit(ir), 250)
    return () => window.clearTimeout(id)
  }, [ir, commit, pending])


  const nCols = Math.max(maxLayer(ir.ops) + 2, 8) // auto-grow right

  const update = (fn: (prev: CircuitIR) => CircuitIR) => {
    setError("")
    setIr((prev) => {
      try {
        const next = fn(prev)
        return {
          ...next,
          ops: sanitizeOps(next.ops, next.n_qubits),
        }
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


  const handleDrop = (qubit: number, layer: number, paletteId?: string) => {
    // Prevent duplicate drop invocations from browser event bubbling / re-render
    const now = Date.now()
    if (now - lastDropTimeRef.current < 350) {
      return
    }
    lastDropTimeRef.current = now

    const item = dragging ?? (paletteId ? ALL_PALETTE_ITEMS[paletteId] : null)
    setDragging(null)
    setSelectedTool(null)
    if (!item) return

    // "Control+" or "NegCtrl+" adds a control modifier to the targeted or selected gate (IBM Quantum Composer behavior)
    if (item.id === "ctrl" || item.id === "negctrl") {
      const isNeg = item.id === "negctrl"
      // Find a gate directly at (qubit, layer), or in the same column (layer), or currently selected
      const exactOp = ir.ops.find(
        (o) => o.layer === layer && ((o.qubits || []).includes(qubit) || (o.controls || []).includes(qubit) || (o.neg_controls || []).includes(qubit))
      )
      const columnOps = ir.ops.filter((o) => o.layer === layer && o.kind === "gate" && o.gate !== "barrier")
      const currentSelected = ir.ops.find((o) => o.id === selectedId)

      const targetOp =
        exactOp ||
        (currentSelected && currentSelected.layer === layer ? currentSelected : columnOps[0]) ||
        currentSelected

      if (!targetOp || targetOp.kind !== "gate" || targetOp.gate === "barrier") {
        setError(`Drag ${item.label} onto an existing gate on the circuit to add a control.`)
        return
      }

      // Determine which wire gets the new control dot
      const usedWires = new Set([...(targetOp.qubits || []), ...(targetOp.controls || []), ...(targetOp.neg_controls || [])])
      let newCtrlWire: number | null = null

      if (!usedWires.has(qubit)) {
        // User dropped Control on a free wire in the gate's column
        newCtrlWire = qubit
      } else {
        // User dropped Control directly ON the gate tile -> pick nearest available wire
        const candidates: number[] = []
        for (let offset = 1; offset < ir.n_qubits; offset++) {
          if (qubit + offset < ir.n_qubits) candidates.push(qubit + offset)
          if (qubit - offset >= 0) candidates.push(qubit - offset)
        }
        newCtrlWire = candidates.find((w) => !usedWires.has(w)) ?? null
      }

      let nextNq = ir.n_qubits
      if (newCtrlWire === null) {
        newCtrlWire = ir.n_qubits
        nextNq = Math.min(ir.n_qubits + 1, 16)
      }

      // Update operation, select it, and open the Edit Gate panel
      update((prev) => {
        const ops = prev.ops.map((o) => {
          if (o.id !== targetOp.id) return o
          if (isNeg) {
            return { ...o, neg_controls: [...(o.neg_controls || []), newCtrlWire!] }
          } else {
            return { ...o, controls: [...o.controls, newCtrlWire!] }
          }
        })
        return {
          ...prev,
          n_qubits: Math.max(prev.n_qubits, nextNq),
          n_clbits: Math.max(prev.n_clbits, nextNq),
          ops,
        }
      })

      setSelectedId(targetOp.id)
      setIsEditPanelOpen(true)
      setError("")
      setNotice(`Added ${isNeg ? "negative control (○)" : "control (•)"} on q[${newCtrlWire}] to ${(targetOp.gate ?? "").toUpperCase()} gate.`)
      return
    }

    // If an incomplete pending gate was active, clean it up before placing a new one
    if (pending) {
      const staleId = pending.op.id
      update((prev) => ({
        ...prev,
        ops: prev.ops.filter((o) => o.id !== staleId),
      }))
      setPending(null)
      setNotice("")
    }

    try {
      const op = buildOp(item, qubit)
      if (!op) return

      // SWAP gate: drop first qubit, then prompt user to click target qubit
      if (item.targets === 2 || item.id === "swap" || item.gate === "swap") {
        const swapOp: Op = { ...op, gate: "swap", qubits: [qubit], controls: [], layer }
        update((prev) => {
          const nq = Math.max(prev.n_qubits, qubit + 1, 2)
          return {
            ...prev,
            n_qubits: nq,
            n_clbits: Math.max(prev.n_clbits, nq),
            ops: placeOp({ ...prev, n_qubits: nq }, swapOp, layer),
          }
        })
        setSelectedId(swapOp.id)
        setPending({ op: swapOp, need: 1, mode: "target2" })
        setNotice("Select target qubit for SWAP — click a wire on the circuit")
        return
      }

      // CNOT (CX): drop control, then prompt user to click target qubit
      if (item.id === "cx" || (item.controls === 1 && (item.gate === "x" || item.id === "cnot"))) {
        const cOp: Op = { ...op, gate: "x", qubits: [], controls: [qubit], layer }
        update((prev) => {
          const nq = Math.max(prev.n_qubits, qubit + 1, 2)
          return {
            ...prev,
            n_qubits: nq,
            n_clbits: Math.max(prev.n_clbits, nq),
            ops: placeOp({ ...prev, n_qubits: nq }, cOp, layer),
          }
        })
        setSelectedId(cOp.id)
        setPending({ op: cOp, need: 1, mode: "target" })
        setNotice("Select target qubit for CNOT — click a wire on the circuit")
        return
      }

      // CY: drop control, then prompt user to click target qubit
      if (item.id === "cy" || (item.controls === 1 && item.gate === "y")) {
        const cyOp: Op = { ...op, gate: "y", qubits: [], controls: [qubit], layer }
        update((prev) => {
          const nq = Math.max(prev.n_qubits, qubit + 1, 2)
          return {
            ...prev,
            n_qubits: nq,
            n_clbits: Math.max(prev.n_clbits, nq),
            ops: placeOp({ ...prev, n_qubits: nq }, cyOp, layer),
          }
        })
        setSelectedId(cyOp.id)
        setPending({ op: cyOp, need: 1, mode: "target" })
        setNotice("Select target qubit for CY — click a wire on the circuit")
        return
      }

      // CZ: drop control, then prompt user to click target qubit
      if (item.id === "cz" || (item.controls === 1 && item.gate === "z")) {
        const czOp: Op = { ...op, gate: "z", qubits: [], controls: [qubit], layer }
        update((prev) => {
          const nq = Math.max(prev.n_qubits, qubit + 1, 2)
          return {
            ...prev,
            n_qubits: nq,
            n_clbits: Math.max(prev.n_clbits, nq),
            ops: placeOp({ ...prev, n_qubits: nq }, czOp, layer),
          }
        })
        setSelectedId(czOp.id)
        setPending({ op: czOp, need: 1, mode: "target" })
        setNotice("Select target qubit for CZ — click a wire on the circuit")
        return
      }

      // CH: drop control, then prompt user to click target qubit
      if (item.id === "ch" || (item.controls === 1 && item.gate === "h")) {
        const chOp: Op = { ...op, gate: "h", qubits: [], controls: [qubit], layer }
        update((prev) => {
          const nq = Math.max(prev.n_qubits, qubit + 1, 2)
          return {
            ...prev,
            n_qubits: nq,
            n_clbits: Math.max(prev.n_clbits, nq),
            ops: placeOp({ ...prev, n_qubits: nq }, chOp, layer),
          }
        })
        setSelectedId(chOp.id)
        setPending({ op: chOp, need: 1, mode: "target" })
        setNotice("Select target qubit for CH — click a wire on the circuit")
        return
      }

      // General 1-control gate
      if (item.controls === 1) {
        const cOp: Op = { ...op, qubits: [], controls: [qubit], layer }
        update((prev) => {
          const nq = Math.max(prev.n_qubits, qubit + 1, 2)
          return {
            ...prev,
            n_qubits: nq,
            n_clbits: Math.max(prev.n_clbits, nq),
            ops: placeOp({ ...prev, n_qubits: nq }, cOp, layer),
          }
        })
        setSelectedId(cOp.id)
        setPending({ op: cOp, need: 1, mode: "target" })
        setNotice(`Select target qubit for ${item.label} — click a wire on the circuit`)
        return
      }

      // Toffoli (CCX): 2 controls, 1 target (drop target first, then select 2 controls)
      if (item.id === "ccx" || item.controls === 2) {
        const ccxOp: Op = { ...op, gate: "x", qubits: [qubit], controls: [], layer }
        update((prev) => {
          const nq = Math.max(prev.n_qubits, qubit + 1, 3)
          return {
            ...prev,
            n_qubits: nq,
            n_clbits: Math.max(prev.n_clbits, nq),
            ops: placeOp({ ...prev, n_qubits: nq }, ccxOp, layer),
          }
        })
        setSelectedId(ccxOp.id)
        setPending({ op: ccxOp, need: 2, mode: "controls" })
        setNotice("Select 2 control qubits for CCX — click two wires on the circuit")
        return
      }

      // MCX
      if (item.id === "mcx" || (item.controls && item.controls < 0)) {
        const mcxOp: Op = { ...op, gate: "x", qubits: [qubit], controls: [], layer }
        update((prev) => {
          const nq = Math.max(prev.n_qubits, qubit + 1, 2)
          return {
            ...prev,
            n_qubits: nq,
            n_clbits: Math.max(prev.n_clbits, nq),
            ops: placeOp({ ...prev, n_qubits: nq }, mcxOp, layer),
          }
        })
        setSelectedId(mcxOp.id)
        setPending({ op: mcxOp, need: -1, mode: "mcx_config" })
        setNotice("Configure MCX Gate: Select or enter the number of control qubits.")
        return
      }

      // Single-qubit gates, measurement, reset, barrier, flow control blocks
      update((prev) => ({ ...prev, ops: placeOp(prev, { ...op, layer }, layer) }))
      setNotice("")
      setPending(null)
    } catch (e) {
      setError(String((e as Error).message))
    }
  }

  const handleConfirmMcxControls = (k: number) => {
    if (!pending || pending.mode !== "mcx_config") return
    const validCount = Math.max(1, Math.min(19, k))
    const targetQ = pending.op.qubits[0] ?? 0
    const needed = Math.max(validCount + 1, targetQ + 1)
    update((prev) => {
      const nq = Math.max(prev.n_qubits, needed)
      return {
        ...prev,
        n_qubits: nq,
        n_clbits: Math.max(prev.n_clbits, nq),
      }
    })
    setPending({ op: pending.op, need: validCount, mode: "controls" })
    setNotice(
      `Select ${validCount} control qubit(s) for MCX — click ${validCount === 1 ? "1 wire" : `${validCount} wires`} on circuit (${validCount} remaining)`
    )
  }

  /** Click during a pending control/target selection. */
  const handlePick = (qubit: number) => {
    if (!pending || pending.mode === "mcx_config") return
    const used = involvedQubits(pending.op)
    if (used.includes(qubit)) return

    let next: Op
    if (pending.mode === "target") {
      next = { ...pending.op, qubits: [qubit] }
    } else if (pending.mode === "target2") {
      next = { ...pending.op, qubits: [...pending.op.qubits, qubit] }
    } else {
      next = { ...pending.op, controls: [...(pending.op.controls || []), qubit] }
    }

    update((prev) => {
      const nq = Math.max(prev.n_qubits, qubit + 1)
      return {
        ...prev,
        n_qubits: nq,
        n_clbits: Math.max(prev.n_clbits, nq),
        ops: prev.ops.map((o) => (o.id === next.id ? next : o)),
      }
    })

    if (pending.mode === "target" || pending.mode === "target2") {
      setPending(null)
      setNotice("")
      return
    }

    const got =
      pending.mode === "controls"
        ? next.controls.length
        : next.qubits.length - 1
    if (pending.need > 0 && got >= pending.need) {
      setPending(null)
      setNotice("")
    } else {
      setPending({ ...pending, op: next })
      if (pending.mode === "controls") {
        if (pending.need > 0) {
          const remaining = pending.need - got
          setNotice(`Select ${remaining} more control qubit(s) — click wire on circuit (${remaining} remaining)`)
        } else {
          setNotice(`Click wires to add controls for MCX, then click Done`)
        }
      }
    }
  }

  const finishPick = () => {
    if (pending && pending.mode === "controls" && (pending.op.controls?.length || 0) === 0) {
      // no controls picked -> leave the bare gate in place
      setNotice("No controls added; the gate was left uncontrolled.")
    }
    setPending(null)
    setNotice("")
  }

  const moveOp = (id: string, qubit: number, layer: number, handleType?: string) => {
    const now = Date.now()
    if (now - lastMoveTimeRef.current < 150) {
      return
    }
    lastMoveTimeRef.current = now

    update((prev) => {
      const op = prev.ops.find((o) => o.id === id)
      if (!op) return prev

      let moved: Op
      if (handleType === "swap-0") {
        const other = op.qubits[1] ?? (qubit === 0 ? 1 : 0)
        if (qubit === other) return prev // cannot swap qubit with itself
        moved = { ...op, qubits: [qubit, other], layer }
      } else if (handleType === "swap-1") {
        const other = op.qubits[0] ?? (qubit === 0 ? 1 : 0)
        if (qubit === other) return prev
        moved = { ...op, qubits: [other, qubit], layer }
      } else if (handleType === "control" || handleType?.startsWith("control-")) {
        const cIdx = handleType.includes("-") ? parseInt(handleType.split("-")[1] ?? "0", 10) : 0
        if (op.qubits.includes(qubit)) return prev // control cannot overlap target
        const newControls = [...(op.controls || [])]
        if (newControls.length === 0) newControls.push(qubit)
        else newControls[cIdx] = qubit
        moved = { ...op, controls: newControls, layer }
      } else if (handleType?.startsWith("neg-control-")) {
        const cIdx = parseInt(handleType.split("-")[2] ?? "0", 10)
        if (op.qubits.includes(qubit)) return prev // control cannot overlap target
        const newNegControls = [...(op.neg_controls || [])]
        if (newNegControls.length === 0) newNegControls.push(qubit)
        else newNegControls[cIdx] = qubit
        moved = { ...op, neg_controls: newNegControls, layer }
      } else if (handleType === "target") {
        if ((op.controls || []).includes(qubit) || (op.neg_controls || []).includes(qubit)) return prev // target cannot overlap control
        moved = { ...op, qubits: [qubit], layer }
      } else {
        // Move entire gate: delta applies across all involved qubits
        const refQ = (op.qubits || [])[0] ?? (op.controls || [])[0] ?? (op.neg_controls && op.neg_controls[0]) ?? 0
        const delta = qubit - refQ
        const nextQubits = (op.qubits || []).map((q) => q + delta)
        const nextControls = (op.controls || []).map((q) => q + delta)
        const nextNegControls = (op.neg_controls || []).map((q) => q + delta)
        const all = [...nextQubits, ...nextControls, ...nextNegControls]
        if (all.some((q) => q < 0 || q >= prev.n_qubits)) {
          // If vertical shift would put any wire out of bounds, keep wires and only change column
          moved = { ...op, layer }
        } else {
          moved = { ...op, qubits: nextQubits, controls: nextControls, neg_controls: nextNegControls, layer }
        }
      }

      const remainingOps = prev.ops.filter((o) => o.id !== id)
      return {
        ...prev,
        ops: placeOp({ ...prev, ops: remainingOps }, moved, layer),
      }
    })
  }

  const deleteOp = (id: string) => {
    update((prev) => ({ ...prev, ops: prev.ops.filter((o) => o.id !== id) }))
    if (selectedId === id) setSelectedId(null)
  }

  const handleFlipGate = (id: string) => {
    update((prev) => {
      const ops = prev.ops.map((o) => {
        if (o.id !== id) return o
        const allControls = [...(o.controls || []), ...(o.neg_controls || [])]
        if (allControls.length > 0 && (o.qubits?.length || 0) > 0) {
          const nextQubits = [...(o.qubits || [])]
          if ((o.controls?.length || 0) > 0) {
            const nextControls = [...(o.controls || [])]
            const temp = nextQubits[0]
            nextQubits[0] = nextControls[0]
            nextControls[0] = temp
            return { ...o, qubits: nextQubits, controls: nextControls }
          } else {
            const nextNegControls = [...(o.neg_controls || [])]
            const temp = nextQubits[0]
            nextQubits[0] = nextNegControls[0]
            nextNegControls[0] = temp
            return { ...o, qubits: nextQubits, neg_controls: nextNegControls }
          }
        } else if (o.qubits.length > 1) {
          return { ...o, qubits: [...o.qubits].reverse() }
        }
        return o
      })
      return { ...prev, ops }
    })
  }

  const handleDuplicateGate = (id: string) => {
    let duplicatedId = ""
    update((prev) => {
      const op = prev.ops.find((o) => o.id === id)
      if (!op) return prev
      const nextLayer = op.layer + 1
      duplicatedId = `op-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`
      const duplicated: Op = {
        ...op,
        id: duplicatedId,
        layer: nextLayer,
      }
      return { ...prev, ops: placeOp(prev, duplicated, nextLayer) }
    })
    if (duplicatedId) {
      setSelectedId(duplicatedId)
    }
  }

  // Keyboard shortcut: Escape cancels pending gate; Delete/Backspace deletes selected gate
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const activeTag = (document.activeElement?.tagName ?? "").toLowerCase()
      if (activeTag === "input" || activeTag === "textarea" || activeTag === "select") {
        return
      }
      if (e.key === "Escape") {
        if (pending) {
          e.preventDefault()
          cancelPending()
        }
        return
      }
      if (e.key === "Delete" || e.key === "Backspace") {
        if (selectedId) {
          e.preventDefault()
          deleteOp(selectedId)
        }
      }
    }
    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [selectedId, pending])

  const dynamic = circuitIsDynamic(ir)
  const nested = hasNestedMeasure(ir.ops)

  const editingOp = editing ? getAtPath(ir.ops, editing.rootIndex, editing.path) : null

  /* ------------------------------------------------------------ history */

  // Undo/redo. Recorded in an effect rather than inside the state updater so
  // that React's double-invocation in development cannot push the same entry
  // twice, and so that an undo does not immediately re-record itself.
  const [past, setPast] = useState<CircuitIR[]>([]);
  const [future, setFuture] = useState<CircuitIR[]>([]);
  const prevIr = useRef<CircuitIR>(ir);
  const restoring = useRef(false);

  useEffect(() => {
    if (prevIr.current === ir) return;
    if (restoring.current) {
      restoring.current = false;
      prevIr.current = ir;
      return;
    }
    setPast((p) => [...p.slice(-49), prevIr.current]);
    setFuture([]);
    prevIr.current = ir;
  }, [ir]);

  const undo = () => {
    if (!past.length) return;
    const previous = past[past.length - 1];
    setPast((p) => p.slice(0, -1));
    setFuture((f) => [ir, ...f].slice(0, 50));
    restoring.current = true;
    setIr(previous);
  };

  const redo = () => {
    if (!future.length) return;
    const next = future[0];
    setFuture((f) => f.slice(1));
    setPast((p) => [...p.slice(-49), ir]);
    restoring.current = true;
    setIr(next);
  };

  /* ------------------------------------------------------- view controls */

  // "Left alignment" packs every gate into the earliest column it can.
  // "Preserve spacing" leaves the columns you chose alone. Both are real
  // transformations; centre and right alignment have no meaning for a circuit,
  // so they are deliberately absent rather than shipped as dead controls.
  const [alignment, setAlignment] = useState<"left" | "preserve">("preserve");
  const applyAlignment = (value: string) => {
    const next = value as "left" | "preserve";
    setAlignment(next);
    if (next === "left") update((prev) => ({ ...prev, ops: compact(prev.ops) }));
  };

  const [inspect, setInspect] = useState(false);
  const [search, setSearch] = useState("");
  const [showSearch, setShowSearch] = useState(false);
  const [showCode, setShowCode] = useState(true);

  /** Remove a qubit wire. Refused while gates still sit on it. */
  const removeWire = (qubit: number) => {
    const occupied = ir.ops.some((o) => [...o.qubits, ...o.controls].includes(qubit));
    if (occupied) {
      setNotice(`q[${qubit}] still has gates on it — remove them first.`);
      return;
    }
    if (ir.n_qubits <= 1) {
      setNotice("A circuit needs at least one qubit.");
      return;
    }
    update((prev) => ({
      ...prev,
      n_qubits: prev.n_qubits - 1,
      ops: prev.ops.map((o) => ({
        ...o,
        qubits: (o.qubits || []).map((x) => (x > qubit ? x - 1 : x)),
        controls: (o.controls || []).map((x) => (x > qubit ? x - 1 : x)),
      })),
    }));
  };

  const selectedOp = ir.ops.find((o) => o.id === selectedId) ?? null;

  /* -------------------------------------------------------------- palette */

  const byId = ALL_PALETTE_ITEMS;

  // The reference layout is a six-column grid with full multi-qubit gate support:
  // red Hadamard, blue X-family and multi-qubit, pale blue single-qubit,
  // pink rotations, grey structural/control flow.
  const GRID: string[][] = [
    ["h", "x", "cx", "cy", "cz", "ch"],
    ["swap", "ccx", "mcx", "id", "ctrl", "barrier"],
    ["t", "s", "z", "tdg", "sdg", "p"],
    ["rz", "rx", "ry", "sx", "y", "measure"],
    ["reset", "if", "for", "while", "box", "negctrl"],
  ];

function renderPaletteLabel(label: string) {
  if (label === "Control+") {
    return (
      <span className="gate-btn-stack">
        <span style={{ fontSize: 13, fontWeight: 800, lineHeight: 1 }}>•</span>
        <span style={{ fontSize: 8.5, fontWeight: 700, lineHeight: 1 }}>Ctrl+</span>
      </span>
    );
  }
  if (label === "NegCtrl+") {
    return (
      <span className="gate-btn-stack">
        <span style={{ fontSize: 13, fontWeight: 800, lineHeight: 1 }}>○</span>
        <span style={{ fontSize: 8.5, fontWeight: 700, lineHeight: 1 }}>Ctrl-</span>
      </span>
    );
  }
  const paramMatch = label.match(/^([A-Za-z]+)\((.+)\)$/);
  if (paramMatch) {
    return (
      <span className="gate-btn-stack">
        <span style={{ fontSize: 11, fontWeight: 800, lineHeight: 1.05 }}>{paramMatch[1]}</span>
        <span style={{ fontSize: 8.5, fontWeight: 600, lineHeight: 1, opacity: 0.92 }}>({paramMatch[2]})</span>
      </span>
    );
  }
  if (label === "If / Else") {
    return (
      <span className="gate-btn-stack">
        <span style={{ fontSize: 8.5, fontWeight: 700, lineHeight: 1.05 }}>If /</span>
        <span style={{ fontSize: 8.5, fontWeight: 700, lineHeight: 1.05 }}>Else</span>
      </span>
    );
  }
  const len = label.length;
  const fontSize =
    len === 1 ? 14 :
    len <= 3 ? 11.5 :
    len <= 5 ? 9 :
    8;
  return (
    <span
      style={{
        fontSize,
        fontWeight: 700,
        letterSpacing: len >= 6 ? "-0.035em" : len >= 4 ? "-0.02em" : "0",
        lineHeight: 1.05,
        maxWidth: "38px",
        overflow: "hidden",
        textOverflow: "ellipsis",
        whiteSpace: "nowrap",
        display: "block",
        textAlign: "center",
      }}
    >
      {label}
    </span>
  );
}

  const paletteButton = (id: string, key: string) => {
    const item = byId[id];
    if (!item) return null;
    const needle = search.trim().toLowerCase();
    if (needle && !item.label.toLowerCase().includes(needle) && !item.id.includes(needle)) {
      return null;
    }
    const style = paletteStyle(item.id);
    return (
      <div
        key={key}
        role="button"
        tabIndex={0}
        aria-label={`Drag ${item.label} gate: ${item.hint}`}
        className="gate-btn"
        style={{ background: style.bg, color: style.fg, cursor: "grab" }}
        draggable
        title={`${item.hint} — drag onto circuit wire`}
        onDragStart={(e) => {
          setDragging(item);
          try {
            e.dataTransfer.setData("text/plain", item.id);
            e.dataTransfer.setData("palette-id", item.id);
            e.dataTransfer.effectAllowed = "copyMove";
          } catch (_) {}
        }}
        onDragEnd={() => setDragging(null)}
        onClick={() => {
          setNotice(`Drag the ${item.label} gate onto a circuit wire to place it.`);
          setTimeout(() => setNotice((n) => (n.includes("Drag") ? "" : n)), 4000);
        }}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            setNotice(`Drag the ${item.label} gate onto a circuit wire to place it.`);
          }
        }}
      >
        {renderPaletteLabel(item.label)}
      </div>
    );
  };


  return (
    <div className="composer" ref={rootRef}>
      <div className="composer-columns">
        {/* ------------------------------------------------ left: operations */}
        <aside className="ops-sidebar">
          {isEditPanelOpen && selectedOp ? (
            <EditGatePanel
              op={selectedOp}
              nQubits={ir.n_qubits}
              nClbits={ir.n_clbits ?? ir.n_qubits}
              onUpdateOp={handleUpdateOp}
              onClose={() => setIsEditPanelOpen(false)}
              onDuplicate={() => handleDuplicateGate(selectedOp.id)}
              onDelete={() => {
                deleteOp(selectedOp.id);
                setIsEditPanelOpen(false);
              }}
              onAddQubit={() => {
                let nextIdx = ir.n_qubits;
                update((prev) => {
                  nextIdx = prev.n_qubits;
                  const nq = Math.min(prev.n_qubits + 1, 20);
                  return {
                    ...prev,
                    n_qubits: nq,
                    n_clbits: Math.max(prev.n_clbits, nq),
                  };
                });
                return nextIdx;
              }}
            />
          ) : (
            <>
              <div className="ops-header">
                <span className="ops-title">Operations</span>
                <div className="ops-header-icons">
                  <button
                    className="ops-icon"
                    title="Search operations"
                    onClick={() => setShowSearch((v) => !v)}
                  >
                    &#8983;
                  </button>
                  <button className="ops-icon" title="Palette view" onClick={() => setSearch("")}>
                    &#9638;
                  </button>
                </div>
              </div>

              {showSearch && (
                <input
                  className="ops-search"
                  value={search}
                  placeholder="filter gates…"
                  onChange={(e) => setSearch(e.target.value)}
                />
              )}

              <div className="gate-grid">
                {GRID.map((row, r) =>
                  row.map((id, c) => paletteButton(id, `${id}-${r}-${c}`)),
                )}
              </div>

              <div className="palette-param">
                <span className="palette-label">Param</span>
                <input
                  className="field"
                  value={paramExpr}
                  onChange={(e) => handleParamChange(e.target.value)}
                  title="Used for P/RX/RY/RZ. Only pi, numbers and + - * / ( )"
                />
                <span className="hint">
                  only <code>pi</code>, numbers and <code>+ - * / ( )</code>
                </span>
              </div>
            </>
          )}
        </aside>

        {/* ------------------------------------------------ centre: workspace */}
        <section className="workspace">
          <div className="circuit-toolbar">
            <button
              className="tb icon"
              onClick={undo}
              disabled={!past.length}
              title={past.length ? "Undo" : "Nothing to undo"}
            >
              &#8630;
            </button>
            <button
              className="tb icon"
              onClick={redo}
              disabled={!future.length}
              title={future.length ? "Redo" : "Nothing to redo"}
            >
              &#8631;
            </button>

            <select
              className="align-select"
              value={alignment}
              onChange={(e) => applyAlignment(e.target.value)}
              title="How gates are packed into columns"
            >
              <option value="preserve">Preserve spacing</option>
              <option value="left">Left alignment</option>
            </select>

            <button
              className={`inspect-toggle${inspect ? " on" : ""}`}
              onClick={() => setInspect((v) => !v)}
              title="Show the selected gate's properties"
            >
              <span className="switch">
                <span className="knob" />
              </span>
              Inspect
            </button>

            <div className="spacer" />
            <button className="tb ghost" onClick={() => setShowCode((v) => !v)}>
              {showCode ? "Hide code" : "Show code"}
            </button>
          </div>

          <div className="circuit-actions">
            <button
              className="tb"
              onClick={() =>
                update((prev) => ({
                  ...prev,
                  n_qubits: Math.min(prev.n_qubits + 1, 20),
                  n_clbits: Math.max(prev.n_clbits, Math.min(prev.n_qubits + 1, 20)),
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
                  const last = prev.n_qubits - 1;
                  return {
                    ...prev,
                    n_qubits: Math.max(1, last),
                    ops: prev.ops.filter((o) => ![...(o.qubits || []), ...(o.controls || [])].includes(last)),
                  };
                })
              }
            >
              − Qubit
            </button>
            <span className="hint">{ir.n_qubits} qubits</span>
            <div className="spacer" />
            <button className="tb" onClick={() => update((prev) => ({ ...prev, ops: compact(prev.ops) }))}>
              Compact
            </button>
            <button className="tb danger" onClick={() => update((prev) => ({ ...prev, ops: [] }))}>
              Clear
            </button>
          </div>

          <div className="canvas-col">
            {pending && pending.mode === "mcx_config" ? (
              <div className="banner info pending-banner mcx-config-banner">
                <div className="mcx-config-content">
                  <span className="pending-msg">
                    <strong>Configure MCX:</strong> Number of control qubits:
                  </span>
                  <div className="mcx-buttons-group">
                    {[1, 2, 3, 4].map((count) => (
                      <button
                        key={count}
                        type="button"
                        className="tb mcx-count-btn"
                        onClick={() => handleConfirmMcxControls(count)}
                        title={`Select ${count} control qubit${count > 1 ? "s" : ""}`}
                      >
                        {count}
                      </button>
                    ))}
                    <span className="mcx-or-label">or custom:</span>
                    <input
                      type="number"
                      min={1}
                      max={19}
                      className="mcx-count-input"
                      value={mcxCountInput}
                      onChange={(e) => {
                        const val = parseInt(e.target.value, 10);
                        setMcxCountInput(isNaN(val) ? 1 : Math.max(1, Math.min(19, val)));
                      }}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") {
                          handleConfirmMcxControls(mcxCountInput);
                        }
                      }}
                    />
                    <button
                      type="button"
                      className="tb mcx-confirm-btn"
                      onClick={() => handleConfirmMcxControls(mcxCountInput)}
                    >
                      Confirm
                    </button>
                  </div>
                </div>
                <button type="button" className="tb tb-cancel" onClick={cancelPending}>
                  ✕ Cancel
                </button>
              </div>
            ) : pending ? (
              <div className="banner info pending-banner">
                <span>{notice}</span>
                <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                  {pending.mode === "controls" && (
                    <button className="tb" onClick={finishPick}>
                      Done
                    </button>
                  )}
                  <button className="tb tb-cancel" onClick={cancelPending}>
                    ✕ Cancel
                  </button>
                </div>
              </div>
            ) : null}
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
              selectedTool={selectedTool}
              pending={pending}
              dragging={dragging}
              onDropAt={handleDrop}
              onPick={handlePick}
              onSelect={handleSelect}
              onDelete={deleteOp}
              onMoveOp={moveOp}
              onOpenBlock={(id) => {
                const idx = ir.ops.findIndex((o) => o.id === id);
                if (idx >= 0) setEditing({ rootIndex: idx, path: [] });
              }}
              onRemoveWire={removeWire}
              onOpenEditPanel={(id) => {
                setSelectedId(id);
                setIsEditPanelOpen(true);
              }}
              onFlipGate={handleFlipGate}
              onDuplicateGate={handleDuplicateGate}
            />

            {inspect && (
              <div className="inspect-panel">
                {selectedOp ? (
                  <table>
                    <tbody>
                      {(
                        [
                          ["kind", selectedOp.kind],
                          ["gate", selectedOp.gate ?? "—"],
                          [
                            "qubits",
                            selectedOp.qubits.length
                              ? selectedOp.qubits.map((q) => `q[${q}]`).join(", ")
                              : "—",
                          ],
                          [
                            "controls",
                            selectedOp.controls.length
                              ? selectedOp.controls.map((q) => `q[${q}]`).join(", ")
                              : "—",
                          ],
                          ["clbits", selectedOp.clbits.length ? selectedOp.clbits.join(", ") : "—"],
                          [
                            "params",
                            selectedOp.params.length
                              ? selectedOp.params.map((p) => p.expr).join(", ")
                              : "—",
                          ],
                          ["column", String(selectedOp.layer)],
                        ] as [string, string][]
                      ).map(([k, v]) => (
                        <tr key={k}>
                          <th>{k}</th>
                          <td>{v}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <span className="hint">Inspect is on — select a gate to see its properties.</span>
                )}
              </div>
            )}

            <div className="hint">
              Drag a gate onto the grid (or click it, then click a cell). Dropping onto an occupied
              column inserts a new column globally, shifting everything to the right. Drag a placed
              gate to move it. Click a block to edit its contents. The ⊖ at the end of a wire
              removes it once it is empty.
            </div>
          </div>
        </section>

        {/* -------------------------------------------------- right: code */}
        {showCode && (
          <aside className="code-panel">
            <div className="code-header">
              Circuit <span className="code-count">{ir.ops.length} ops</span>
            </div>
            <div className="code-body">
              {ir.ops.length === 0 && <div className="code-empty">empty circuit</div>}
              {sortOps(ir.ops).map((op, i) => (
                <div className="code-line" key={op.id}>
                  <span className="ln">{i + 1}</span>
                  <span className="src">{describeOp(op)}</span>
                </div>
              ))}
            </div>
          </aside>
        )}
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
              setEditing({ ...editing, path: editing.path.slice(0, -1) });
            else setEditing(null);
          }}
        />
      )}
    </div>
  );
}

// No default export on purpose: hosts import { ComposerInner } explicitly, so
// it is always obvious which grid a page is rendering (see the note at the top).
