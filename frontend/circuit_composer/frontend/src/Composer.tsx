import { useCallback, useEffect, useMemo, useRef, useState } from "react"
// NOTE: this file is deliberately free of `streamlit-component-lib`.
//
// It is the single implementation of the drag-and-drop grid, and it is used by
// two hosts: Streamlit (via ./streamlit.tsx, which wires the callbacks to
// setComponentValue / setFrameHeight) and the new React SPA (via
// frontend/web, which wires them to props and React state). Keeping the
// Streamlit import out of here means the SPA bundles no Streamlit code, and
// Streamlit's iframe behaviour is decided in exactly one file.
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
  describeOp,
} from "./ir"
import Grid from "./Grid"
import type { PendingSelection } from "./Grid"
import BlockEditor from "./BlockEditor"
import { paletteStyle } from "./theme"

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
  /** Called with the height the host should reserve. Streamlit needs this; a
   *  plain React host can ignore it and let the grid size itself. */
  onHeight?: (height: number) => void
  theme?: { base?: string }
}

export function ComposerInner({ value, nQubits, onChange, onHeight, theme }: ComposerProps) {
  const incoming = value ?? null
  const initial = useMemo<CircuitIR>(
    () => (incoming && incoming.ops ? incoming : emptyCircuit(nQubits ?? 2)),
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
  const rootRef = useRef<HTMLDivElement>(null)

  // theme -> css variables
  useEffect(() => {
    document.body.classList.toggle("dark", theme?.base === "dark")
  }, [theme])

  // Streamlit sizes the iframe from document.body.scrollHeight at the moment
  // we call this. If layout is not settled yet (web font still loading, grid
  // not measured) the reported height can be 0 and the component shows as a
  // blank area. Re-measure after paint and whenever the body resizes.
  const resize = useCallback(() => {
    // Never report 0: Streamlit would collapse the iframe to nothing and the
    // component looks like a blank white box with no error anywhere.
    const measured = Math.max(
      document.body.scrollHeight,
      document.documentElement?.scrollHeight ?? 0,
      rootRef.current?.scrollHeight ?? 0,
    )
    // Streamlit needs the height pushed to the parent frame; a plain React
    // host usually just lets the grid size itself, hence the optional hook.
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

  /** Push the circuit back to Python (only when it actually changed). */
  const commit = useCallback((next: CircuitIR) => {
    // Floor at n_qubits so "Measure All" always has somewhere to write, but
    // never carry a stale larger width forward: that is what made a shrunk
    // circuit keep producing over-wide bitstrings.
    const payload = {
      ...next,
      n_clbits: Math.max(requiredClbits(next), next.n_qubits, 1),
    }
    const json = JSON.stringify(payload)
    if (json !== lastSent.current) {
      lastSent.current = json
      onChange?.(payload)
    }
  }, [onChange])

  // Every setComponentValue triggers a full Python rerun of the page, and the
  // whole Composer (timeline, analysis, export tabs) re-renders. Committing
  // synchronously on each keystroke/click made the +/- Qubit buttons feel
  // laggy and unresponsive. The React state is authoritative and updates
  // instantly; debounce the trip back to Python so a burst of clicks costs one
  // rerun instead of one per click.
  useEffect(() => {
    const id = window.setTimeout(() => commit(ir), 250)
    return () => window.clearTimeout(id)
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
        // Name the target explicitly. "Click 1 control qubit" gave no clue
        // which qubit had just become the target, so it was very easy to end
        // up with the control and target the wrong way round -- an H on q0
        // plus a reversed CNOT yields a separable |00>+|01>, not a Bell pair.
        setNotice(
          item.controls < 0
            ? `Target is q[${qubit}]. Click control qubits in the same column, then press Done.`
            : `Target is q[${qubit}] (it flips). Now click ${item.controls} control qubit${
                item.controls > 1 ? "s" : ""
              } in the same column.`,
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
        qubits: o.qubits.map((x) => (x > qubit ? x - 1 : x)),
        controls: o.controls.map((x) => (x > qubit ? x - 1 : x)),
      })),
    }));
  };

  const selectedOp = ir.ops.find((o) => o.id === selectedId) ?? null;

  /* -------------------------------------------------------------- palette */

  const byId = useMemo(() => {
    const m: Record<string, PaletteItem> = {};
    for (const item of [...PALETTE, ...MULTI_PALETTE, ...STRUCTURAL, ...BLOCKS]) m[item.id] = item;
    return m;
  }, []);

  // The reference layout is a six-column grid. The grouping is by colour:
  // red Hadamard, blue X-family and multi-qubit, pale blue single-qubit,
  // pink rotations, grey everything-that-is-not-an-operation.
  const GRID: string[][] = [
    ["h", "x", "cx", "cy", "swap", "id"],
    ["t", "s", "z", "tdg", "sdg", "p"],
    ["rz", "p", "reset", "barrier", "measure", "if"],
    ["for", "while", "box", "sx", "y", "rx"],
    ["ry"],
  ];

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
        className={`gate-btn${selectedTool?.id === item.id ? " selected" : ""}`}
        style={{ background: style.bg, color: style.fg }}
        draggable
        title={item.hint}
        onDragStart={() => setDragging(item)}
        onDragEnd={() => setDragging(null)}
        onClick={() => setSelectedTool(selectedTool?.id === item.id ? null : item)}
      >
        {item.label}
      </div>
    );
  };

  return (
    <div className="composer" ref={rootRef}>
      <div className="composer-columns">
        {/* ------------------------------------------------ left: operations */}
        <aside className="ops-sidebar">
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
              onChange={(e) => setParamExpr(e.target.value)}
              title="Used for P/RX/RY/RZ. Only pi, numbers and + - * / ( )"
            />
            <span className="hint">
              only <code>pi</code>, numbers and <code>+ - * / ( )</code>
            </span>
          </div>
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
                  const last = prev.n_qubits - 1;
                  return {
                    ...prev,
                    n_qubits: Math.max(1, last),
                    ops: prev.ops.filter((o) => ![...o.qubits, ...o.controls].includes(last)),
                  };
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
                update((prev) => normalizeTerminalMeasurement(prev));
                if (dynamic)
                  setNotice(
                    "Normalized to a single terminal measurement layer. Note: this changes the semantics of a dynamic circuit, whose mid-circuit measurements drive control flow.",
                  );
              }}
            >
              Normalize Terminal Measurement
            </button>
            <button className="tb" onClick={() => update((prev) => ({ ...prev, ops: compact(prev.ops) }))}>
              Compact
            </button>
            <button className="tb danger" onClick={() => update((prev) => ({ ...prev, ops: [] }))}>
              Clear
            </button>
          </div>

          <div className="canvas-col">
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
                const idx = ir.ops.findIndex((o) => o.id === id);
                if (idx >= 0) setEditing({ rootIndex: idx, path: [] });
              }}
              onRemoveWire={removeWire}
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
              {ir.ops.map((op, i) => (
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

// No default export on purpose: hosts import { ComposerInner } explicitly.
// The Streamlit adapter lives in ./streamlit.tsx so that this file stays free
// of streamlit-component-lib (see the note at the top).
