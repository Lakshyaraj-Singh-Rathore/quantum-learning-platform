/**
 * The circuit canvas: qubit wires, gate tiles, and the classical register that
 * measurement collapses into.
 *
 * Time runs left to right, one horizontal wire per qubit, gates are tiles on a
 * wire, and multi-qubit gates are joined by a vertical line with a filled dot
 * on each control.
 *
 * Two things are drawn differently from an ordinary "letter in a box" diagram,
 * and both because the ordinary version teaches the wrong thing:
 *
 * - A controlled X is a ⊕ on the target, not a tile saying "X". As a plain tile
 *   it is indistinguishable whichever way round the control and target are.
 * - Measurement is a meter dial, not a grey tile. A measurement is not a
 *   unitary gate; it is where amplitude collapses into a bit, and it is wired
 *   down to the classical register to show that.
 *
 * The register itself is a double line, which is the usual notation for "this
 * carries bits, not amplitudes".
 *
 * Every colour and size comes from ./theme.
 */
import { useMemo, useState, useRef } from "react";
import type { CircuitIR, Op, PaletteItem } from "./types";
import { involvedQubits, range, rowSpan } from "./ir";
import { GEOMETRY, gateColour, gateForeground, gateShape, gateText } from "./theme";

export interface PendingSelection {
  op: Op;
  need: number; // -1 = arbitrary
  mode: "controls" | "target" | "target2" | "mcx_config";
}

interface Props {
  ir: CircuitIR;
  nCols: number;
  selectedId: string | null;
  selectedTool?: PaletteItem | null;
  pending: PendingSelection | null;
  dragging: PaletteItem | null;
  onDropAt: (qubit: number, layer: number, paletteId?: string) => void;
  onPick: (qubit: number) => void;
  onSelect: (id: string | null) => void;
  onDelete: (id: string) => void;
  onOpenBlock: (id: string) => void;
  onMoveOp: (id: string, qubit: number, layer: number, handleType?: string) => void;
  /** Remove the given qubit wire. Refused (with a notice) if gates sit on it. */
  onRemoveWire?: (qubit: number) => void;
  onOpenEditPanel?: (id: string) => void;
  onFlipGate?: (id: string) => void;
  onDuplicateGate?: (id: string) => void;
}

/** A measurement meter: a dial in a rounded box. Not a letter in a square. */
function MeterDial() {
  return (
    <svg viewBox="0 0 24 16" className="meter-dial" aria-hidden="true">
      <path d="M3 13 A 9 9 0 0 1 21 13" fill="none" stroke="currentColor" strokeWidth="1.7" />
      <line x1="12" y1="13" x2="17.5" y2="7" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
    </svg>
  );
}

/** Formats parameterized gates into two distinct tiers (name + param) to prevent overflow. */
function formatParamBadge(op: Op): { name: string; param: string; fullTitle: string } | null {
  if (op.kind !== "gate" || !op.params?.length) return null;
  const rawGate = (op.gate ?? "").toUpperCase();
  const nameMap: Record<string, string> = {
    ID: "I",
    SDG: "S†",
    TDG: "T†",
    SX: "√X",
    SXDG: "√X†",
  };
  const name = nameMap[rawGate] ?? rawGate;
  const p = op.params[0];
  const fullTitle = `${name}(${p.expr})`;

  const exprStr = (p.expr ?? "").trim();
  if (exprStr && exprStr.length <= 5 && !/[0-9]+\.[0-9]{3,}/.test(exprStr)) {
    return { name, param: exprStr, fullTitle };
  }

  const numVal = typeof p.value === "number" ? p.value : parseFloat(exprStr);
  if (Number.isNaN(numVal)) {
    return { name, param: exprStr.slice(0, 5), fullTitle };
  }

  // Snap to common pi fractions
  const ratios: [number, string][] = [
    [Math.PI, "π"], [-Math.PI, "-π"],
    [Math.PI / 2, "π/2"], [-Math.PI / 2, "-π/2"],
    [Math.PI / 4, "π/4"], [-Math.PI / 4, "-π/4"],
    [(2 * Math.PI) / 3, "2π/3"], [-(2 * Math.PI) / 3, "-2π/3"],
    [(3 * Math.PI) / 4, "3π/4"], [-(3 * Math.PI) / 4, "-3π/4"],
  ];
  for (const [target, label] of ratios) {
    if (Math.abs(numVal - target) < 1e-3) {
      return { name, param: label, fullTitle };
    }
  }

  const compactNum = Number(numVal.toFixed(2)).toString();
  return { name, param: compactNum, fullTitle };
}

export default function Grid(props: Props) {
  const { ir, nCols, selectedId, pending, dragging } = props;
  const rows = ir.n_qubits;
  const nClbits = Math.max(1, ir.n_clbits ?? 0);
  const gridRef = useRef<HTMLDivElement>(null);
  const lastDropHandledRef = useRef<number>(0);
  const [dragHover, setDragHover] = useState<{ q: number; c: number } | null>(null);
  const [movingOp, setMovingOp] = useState<{ id: string; handleType?: string } | null>(null);

  const {
    cell: CELL,
    gutter: GUTTER,
    header: TOP,
    tile: TILE,
    registerGap: REG_GAP,
    endpoint: ENDPOINT,
  } = GEOMETRY;

  const pad = (CELL - TILE) / 2;
  const width = GUTTER + nCols * CELL + ENDPOINT + 18;
  const regY = TOP + rows * CELL + REG_GAP;
  const height = regY + 26;

  /** Vertical centre of qubit row `q`. */
  const wireY = (q: number) => TOP + q * CELL + CELL / 2;
  /** Left edge of column `layer`. */
  const colX = (layer: number) => GUTTER + layer * CELL;

  const isBlock = (op: Op) => op.body.length > 0 || op.else_body.length > 0 || op.kind === "box";

  /** Rows that are legal control/target picks for the pending selection. */
  const pickable = useMemo(() => {
    if (!pending || pending.mode === "mcx_config") return new Set<number>();
    const used = new Set(involvedQubits(pending.op));
    return new Set(range(0, rows - 1).filter((q) => !used.has(q)));
  }, [pending, rows]);

  const wireEmpty = (q: number) => !ir.ops.some((o) => [...(o.qubits || []), ...(o.controls || [])].includes(q));

  const coordsFromEvent = (e: React.DragEvent) => {
    const rect = gridRef.current?.getBoundingClientRect();
    if (!rect) return null;
    const x = e.clientX - rect.left - GUTTER;
    const y = e.clientY - rect.top - TOP;
    if (x < 0 || y < 0) return null;
    if (y > rows * CELL + 10 || x > nCols * CELL + 24) return null;
    const c = Math.max(0, Math.min(nCols - 1, Math.floor(x / CELL)));
    const q = Math.max(0, Math.min(rows - 1, Math.floor(y / CELL)));
    return { q, c };
  };

  const activeMovingOp = movingOp ? ir.ops.find((o) => o.id === movingOp.id) : null;

  return (
    <div className="grid-scroll">
      <div
        ref={gridRef}
        className="grid"
        style={{ width, height, position: "relative" }}
        onDragOver={(e) => {
          e.preventDefault();
          e.dataTransfer.dropEffect = "copy";
          const coords = coordsFromEvent(e);
          if (coords) {
            setDragHover((prev) => (prev?.q === coords.q && prev?.c === coords.c ? prev : coords));
          } else {
            setDragHover(null);
          }
        }}
        onDragLeave={(e) => {
          if (e.currentTarget === e.target) {
            setDragHover(null);
          }
        }}
        onDrop={(e) => {
          e.preventDefault();
          e.stopPropagation();
          setDragHover(null);

          const now = Date.now();
          if (now - lastDropHandledRef.current < 350) {
            return;
          }
          lastDropHandledRef.current = now;

          const handleType = e.dataTransfer.getData("handle-type");
          const moving = e.dataTransfer.getData("op-id");
          const paletteId = e.dataTransfer.getData("palette-id") || e.dataTransfer.getData("text/plain");
          const coords = coordsFromEvent(e);
          setMovingOp(null);
          if (!coords) return;
          const { q, c } = coords;
          if (moving) {
            props.onMoveOp(moving, q, c, handleType || undefined);
          } else if (dragging || paletteId) {
            props.onDropAt(q, c, paletteId || undefined);
          }
        }}
      >
        {/* column ruler */}
        {range(0, nCols - 1).map((c) => (
          <div
            key={`h${c}`}
            className="colhead"
            style={{ position: "absolute", left: colX(c), top: 0, width: CELL }}
          >
            {c}
          </div>
        ))}

        {/* qubit labels + wires */}
        {range(0, rows - 1).map((q) => (
          <div key={`w${q}`}>
            <div
              className="qlabel"
              style={{ position: "absolute", left: 0, top: TOP + q * CELL, width: GUTTER, height: CELL }}
            >
              q[{q}]
            </div>
            <div className="wire" style={{ left: GUTTER, top: wireY(q) - 1, width: nCols * CELL }} />
          </div>
        ))}

        {/* drop cells — qubit rows only; the register is not a target */}
        {range(0, rows - 1).map((q) =>
          range(0, nCols - 1).map((c) => {
            const isHovered = dragHover?.q === q && dragHover?.c === c;
            const isPendingCol = pending != null && pending.op.layer === c;
            const canPick = pending != null && pickable.has(q);
            const isPickCell = isPendingCol && canPick;
            return (
              <div
                key={`c${q}-${c}`}
                className={`cell${(dragging || movingOp) ? " drop" : ""}${isHovered ? " drag-hover" : ""}${isPickCell ? " pickable" : ""}`}
                style={{
                  position: "absolute",
                  left: colX(c),
                  top: TOP + q * CELL,
                  width: CELL,
                  height: CELL,
                  zIndex: isPickCell ? 12 : 1,
                  pointerEvents: (dragging || movingOp) ? "none" : "auto",
                }}
                onClick={() => {
                  if (canPick) {
                    props.onPick(q);
                  } else {
                    props.onSelect(null);
                  }
                }}
              >
                {isPickCell && (
                  <div className="pending-target-badge">
                    {pending?.mode === "target2"
                      ? "✕"
                      : pending?.mode === "target"
                      ? (pending.op.gate === "x" ? "⊕" : (pending.op.gate ?? "").toUpperCase())
                      : "•"}
                  </div>
                )}
              </div>
            );
          }),
        )}

        {/* Live Drag & Drop Preview (IBM Quantum Composer Style) */}
        {dragHover && (
          <div className="drag-preview-container" style={{ pointerEvents: "none" }}>
            {activeMovingOp ? (() => {
              // Moving an existing placed gate or handle
              if (activeMovingOp.gate === "swap") {
                const opQubits = activeMovingOp.qubits;
                let q0 = opQubits[0] ?? 0;
                let q1 = opQubits[1] ?? (q0 === 0 ? 1 : 0);
                if (movingOp?.handleType === "swap-0") {
                  q0 = dragHover.q;
                } else if (movingOp?.handleType === "swap-1") {
                  q1 = dragHover.q;
                } else {
                  const delta = dragHover.q - q0;
                  q0 += delta;
                  q1 += delta;
                }
                return (
                  <div key="preview-move-swap">
                    <div
                      className="ctrl-line swap-line preview-line"
                      style={{
                        left: colX(dragHover.c) + CELL / 2 - 1,
                        top: wireY(Math.min(q0, q1)),
                        height: Math.abs(q0 - q1) * CELL,
                      }}
                    />
                    {[q0, q1].map((pq) => (
                      <div
                        key={`preview-move-swap-${pq}`}
                        className="gate swap drag-preview-cross"
                        style={{
                          left: colX(dragHover.c) + pad,
                          top: TOP + pq * CELL + pad,
                          width: TILE,
                          height: TILE,
                          zIndex: 20,
                        }}
                      >
                        ✕
                      </div>
                    ))}
                  </div>
                );
              }
              if ((activeMovingOp.controls?.length || 0) > 0) {
                let targetQ = activeMovingOp.qubits[0] ?? 0;
                let controls = [...(activeMovingOp.controls || [])];
                if (movingOp?.handleType === "control") {
                  controls[0] = dragHover.q;
                } else if (movingOp?.handleType?.startsWith("control-")) {
                  const cIdx = parseInt(movingOp.handleType.split("-")[1] ?? "0", 10);
                  if (cIdx >= 0 && cIdx < controls.length) {
                    controls[cIdx] = dragHover.q;
                  }
                } else if (movingOp?.handleType === "target") {
                  targetQ = dragHover.q;
                } else {
                  const delta = dragHover.q - targetQ;
                  targetQ += delta;
                  controls = controls.map((c) => c + delta);
                }
                const allQ = [...controls, targetQ];
                const lo = Math.min(...allQ);
                const hi = Math.max(...allQ);
                const isTargetShape = gateShape(activeMovingOp) === "target";
                return (
                  <div key="preview-move-controlled">
                    <div
                      className="ctrl-line preview-line"
                      style={{
                        left: colX(dragHover.c) + CELL / 2 - 1,
                        top: wireY(lo),
                        height: (hi - lo) * CELL,
                      }}
                    />
                    {controls.map((cQ, i) => (
                      <div
                        key={`preview-move-dot-${i}-${cQ}`}
                        className="ctrl-dot preview-dot"
                        style={{
                          left: colX(dragHover.c) + CELL / 2 - 6.5,
                          top: wireY(cQ) - 6.5,
                          zIndex: 20,
                        }}
                      />
                    ))}
                    {isTargetShape ? (
                      <div
                        className="gate target drag-preview-target"
                        style={{
                          left: colX(dragHover.c) + pad,
                          top: TOP + targetQ * CELL + pad,
                          width: TILE,
                          height: TILE,
                          zIndex: 20,
                        }}
                      />
                    ) : (
                      <div
                        className="gate drag-preview-tile"
                        style={{
                          left: colX(dragHover.c) + pad,
                          top: TOP + targetQ * CELL + pad,
                          width: TILE,
                          height: TILE,
                          background: gateColour(activeMovingOp),
                          color: gateForeground(activeMovingOp),
                          zIndex: 20,
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          fontWeight: 600,
                        }}
                      >
                        {gateText(activeMovingOp)}
                      </div>
                    )}
                  </div>
                );
              }
              return (
                <div
                  className="drag-preview-tile"
                  style={{
                    left: colX(dragHover.c) + pad,
                    top: TOP + dragHover.q * CELL + pad,
                    width: TILE,
                    height: TILE,
                    zIndex: 20,
                  }}
                >
                  {gateText(activeMovingOp)}
                </div>
              );
            })() : dragging?.kind === "measure" ? (
              <div key="preview-measure">
                <div
                  className="m-wire preview-line"
                  style={{
                    left: colX(dragHover.c) + CELL / 2 - 1,
                    top: wireY(dragHover.q),
                    height: Math.max(0, regY - wireY(dragHover.q)),
                    borderLeft: "2px dashed #38bdf8",
                  }}
                />
                <div
                  className="drag-preview-tile"
                  style={{
                    left: colX(dragHover.c) + pad,
                    top: TOP + dragHover.q * CELL + pad,
                    width: TILE,
                    height: TILE,
                    zIndex: 20,
                  }}
                >
                  <MeterDial />
                </div>
              </div>
            ) : dragging?.kind === "barrier" ? (
              <div
                className="barrier"
                style={{
                  left: colX(dragHover.c) + CELL / 2 - 1,
                  top: TOP + 2,
                  height: rows * CELL - 4,
                  borderColor: "#38bdf8",
                  boxShadow: "0 0 10px #38bdf8",
                  zIndex: 20,
                }}
              />
            ) : (
              <div
                className="drag-preview-tile"
                style={{
                  left: colX(dragHover.c) + pad,
                  top: TOP + dragHover.q * CELL + pad,
                  width: TILE,
                  height: TILE,
                  background: dragging?.color ? `${dragging.color}44` : "rgba(56, 189, 248, 0.28)",
                  borderColor: dragging?.color || "#38bdf8",
                  color: "#fff",
                  zIndex: 20,
                }}
              >
                {dragging?.label || "Gate"}
              </div>
            )}
          </div>
        )}

        {/* the classical register: one double line, labelled with its width */}
        <div
          className="reg-label"
          style={{ position: "absolute", left: 0, top: regY - CELL / 2, width: GUTTER, height: CELL }}
        >
          c{nClbits}
        </div>
        <div className="clbit" style={{ left: GUTTER, top: regY - 2, width: nCols * CELL }} />
        <div className="clbit" style={{ left: GUTTER, top: regY + 1, width: nCols * CELL }} />

        {/* measurement: the wire from the meter down to the register */}
        {ir.ops.map((op) => {
          if (op.kind !== "measure") return null;
          const q = op.qubits[0];
          if (q == null) return null;
          return (
            <div
              key={`m${op.id}`}
              className="m-wire"
              style={{
                left: colX(op.layer) + CELL / 2 - 1,
                top: wireY(q),
                height: Math.max(0, regY - wireY(q)),
              }}
            />
          );
        })}

        {/* control connector lines + dots */}
        {ir.ops.map((op) => {
          const controls = op.controls || [];
          const negControls = op.neg_controls || [];
          const totalControls = controls.length + negControls.length;
          if (!totalControls || isBlock(op)) return null;
          const all = [...controls, ...negControls, ...(op.qubits || [])];
          const hasTarget = (op.qubits?.length || 0) > 0;
          const lo = Math.min(...all);
          const hi = Math.max(...all);
          return (
            <div key={`ctl${op.id}`}>
              {hasTarget && all.length >= 2 && (
                <div
                  className="ctrl-line"
                  draggable
                  onDragStart={(e) => {
                    e.stopPropagation();
                    setMovingOp({ id: op.id, handleType: "whole" });
                    e.dataTransfer.setData("op-id", op.id);
                    e.dataTransfer.setData("handle-type", "whole");
                    e.dataTransfer.effectAllowed = "move";
                  }}
                  onDragEnd={() => {
                    setMovingOp(null);
                    setDragHover(null);
                  }}
                  style={{
                    left: colX(op.layer) + CELL / 2 - 1,
                    top: wireY(lo),
                    height: (hi - lo) * CELL,
                    cursor: "grab",
                  }}
                  title="Controlled gate — drag to move entire gate"
                />
              )}
              {/* Positive control dots (solid) */}
              {controls.map((q, cIdx) => (
                <div
                  key={`d${op.id}-${q}`}
                  className={`ctrl-dot${!hasTarget ? " pending-ctrl-dot" : ""}`}
                  draggable={hasTarget}
                  onDragStart={(e) => {
                    e.stopPropagation();
                    setMovingOp({ id: op.id, handleType: `control-${cIdx}` });
                    e.dataTransfer.setData("op-id", op.id);
                    e.dataTransfer.setData("handle-type", `control-${cIdx}`);
                    e.dataTransfer.effectAllowed = "move";
                  }}
                  onDragEnd={() => {
                    setMovingOp(null);
                    setDragHover(null);
                  }}
                  style={{
                    left: colX(op.layer) + CELL / 2 - 6.5,
                    top: wireY(q) - 6.5,
                    cursor: hasTarget ? "grab" : "default",
                    zIndex: 10,
                  }}
                  title={`control q[${q}]`}
                />
              ))}
              {/* Negative control dots (open circle ○) */}
              {negControls.map((q, cIdx) => (
                <div
                  key={`neg-d${op.id}-${q}`}
                  className="ctrl-dot neg-ctrl-dot"
                  draggable={hasTarget}
                  onDragStart={(e) => {
                    e.stopPropagation();
                    setMovingOp({ id: op.id, handleType: `neg-control-${cIdx}` });
                    e.dataTransfer.setData("op-id", op.id);
                    e.dataTransfer.setData("handle-type", `neg-control-${cIdx}`);
                    e.dataTransfer.effectAllowed = "move";
                  }}
                  onDragEnd={() => {
                    setMovingOp(null);
                    setDragHover(null);
                  }}
                  style={{
                    left: colX(op.layer) + CELL / 2 - 6.5,
                    top: wireY(q) - 6.5,
                    cursor: hasTarget ? "grab" : "default",
                    zIndex: 10,
                  }}
                  title={`negative control q[${q}] (|0⟩)`}
                />
              ))}
            </div>
          );
        })}

        {/* ops */}
        {ir.ops.map((op) => {
          const shape = gateShape(op);
          const colour = gateColour(op);
          const ink = gateForeground(op);
          const text = gateText(op);
          const paramBadge = formatParamBadge(op);
          const fullTitle = paramBadge ? paramBadge.fullTitle : text;

          // Classical flow control spans rows and opens an editor on click.
          if (shape === "block") {
            const [lo, hi] = rowSpan(op, rows);
            const top = TOP + lo * CELL;
            const h = (hi - lo + 1) * CELL;
            return (
              <div
                key={op.id}
                className="block-box"
                style={{
                  left: colX(op.layer) + 2,
                  top: top + 3,
                  width: CELL - 4,
                  height: h - 6,
                  borderColor: colour,
                }}
                title={`${op.kind} — click to edit contents`}
                onClick={(e) => {
                  e.stopPropagation();
                  props.onOpenBlock(op.id);
                }}
              >
                <span className="block-label" style={{ background: colour, color: ink }}>
                  {op.kind}
                </span>
              </div>
            );
          }

          // A barrier is a scheduling hint, drawn as a dashed rule across every
          // wire rather than as a tile on one.
          if (shape === "barrier") {
            return (
              <div
                key={op.id}
                className="barrier"
                draggable
                onDragStart={(e) => {
                  e.stopPropagation();
                  setMovingOp({ id: op.id, handleType: "whole" });
                  e.dataTransfer.setData("op-id", op.id);
                  e.dataTransfer.setData("handle-type", "whole");
                  e.dataTransfer.effectAllowed = "move";
                }}
                onDragEnd={() => {
                  setMovingOp(null);
                  setDragHover(null);
                }}
                style={{
                  left: colX(op.layer) + CELL / 2 - 1,
                  top: TOP + 2,
                  height: rows * CELL - 4,
                  cursor: "grab",
                }}
                title="Barrier — drag to move"
                onClick={(e) => {
                  e.stopPropagation();
                  props.onSelect(op.id);
                }}
              >
                <span className="del" onClick={(e) => { e.stopPropagation(); props.onDelete(op.id); }}>
                  ×
                </span>
              </div>
            );
          }

          // SWAP: two ✕ joined by a line, one on each wire.
          const isSwap = shape === "swap" || op.gate === "swap";
          if (isSwap) {
            // Incomplete pending SWAP with only 1 endpoint:
            if (op.qubits.length < 2) {
              const q0 = op.qubits[0] ?? 0;
              return (
                <div
                  key={op.id}
                  className={`gate swap pending-swap${selectedId === op.id ? " selected" : ""}`}
                  style={{
                    left: colX(op.layer) + pad,
                    top: TOP + q0 * CELL + pad,
                    width: TILE,
                    height: TILE,
                    zIndex: 3,
                  }}
                  title="SWAP endpoint 1 — click target wire on circuit"
                >
                  ✕
                  <span className="del" onClick={(e) => { e.stopPropagation(); props.onDelete(op.id); }}>
                    ×
                  </span>
                </div>
              );
            }
            const opQubits = op.qubits;
            return (
              <div key={op.id}>
                <div
                  className="ctrl-line swap-line"
                  draggable
                  onDragStart={(e) => {
                    e.stopPropagation();
                    setMovingOp({ id: op.id, handleType: "whole" });
                    e.dataTransfer.setData("op-id", op.id);
                    e.dataTransfer.setData("handle-type", "whole");
                    e.dataTransfer.effectAllowed = "move";
                  }}
                  onDragEnd={() => {
                    setMovingOp(null);
                    setDragHover(null);
                  }}
                  style={{
                    left: colX(op.layer) + CELL / 2 - 1,
                    top: wireY(Math.min(...opQubits)),
                    height: Math.abs(opQubits[0] - opQubits[1]) * CELL,
                    cursor: "grab",
                  }}
                  title="SWAP connection — drag to move entire SWAP gate"
                />
                {opQubits.map((q, i) => (
                  <div
                    key={`${op.id}-${i}`}
                    className={`gate swap${selectedId === op.id ? " selected" : ""}`}
                    draggable
                    onDragStart={(e) => {
                      e.stopPropagation();
                      setMovingOp({ id: op.id, handleType: `swap-${i}` });
                      e.dataTransfer.setData("op-id", op.id);
                      e.dataTransfer.setData("handle-type", `swap-${i}`);
                      e.dataTransfer.effectAllowed = "move";
                    }}
                    onDragEnd={() => {
                      setMovingOp(null);
                      setDragHover(null);
                    }}
                    style={{
                      left: colX(op.layer) + pad,
                      top: TOP + q * CELL + pad,
                      width: TILE,
                      height: TILE,
                      zIndex: 3,
                      cursor: "grab",
                      pointerEvents: (dragging || movingOp) ? "none" : "auto",
                    }}
                    onClick={(e) => {
                      e.stopPropagation();
                      props.onSelect(op.id);
                    }}
                    title={`SWAP endpoint ${i + 1} on q[${q}] — drag to change wire`}
                  >
                    ✕
                    {i === 0 && (
                      <span className="del" onClick={(e) => { e.stopPropagation(); props.onDelete(op.id); }}>
                        ×
                      </span>
                    )}
                  </div>
                ))}
              </div>
            );
          }

          const q = op.qubits[0] ?? 0;

          // The circled target of a controlled gate: the shape is what tells
          // you which end of a CNOT is which.
          if (shape === "target") {
            if (op.qubits.length === 0) return null; // waiting for target wire pick
            return (
              <div
                key={op.id}
                className={`gate target${selectedId === op.id ? " selected" : ""}`}
                draggable
                onDragStart={(e) => {
                  e.stopPropagation();
                  setMovingOp({ id: op.id, handleType: "target" });
                  e.dataTransfer.setData("op-id", op.id);
                  e.dataTransfer.setData("handle-type", "target");
                  e.dataTransfer.effectAllowed = "move";
                }}
                onDragEnd={() => {
                  setMovingOp(null);
                  setDragHover(null);
                }}
                style={{
                  left: colX(op.layer) + pad,
                  top: TOP + q * CELL + pad,
                  width: TILE,
                  height: TILE,
                  background: colour,
                  color: ink,
                  zIndex: 3,
                  cursor: "grab",
                  pointerEvents: (dragging || movingOp) ? "none" : "auto",
                }}
                onClick={(e) => {
                  e.stopPropagation();
                  props.onSelect(op.id);
                }}
                title={`controlled ${(op.gate ?? "").toUpperCase()} target on q[${q}] — drag to change target wire`}
              >
                <span className="del" onClick={(e) => { e.stopPropagation(); props.onDelete(op.id); }}>
                  ×
                </span>
              </div>
            );
          }

          if (((op.controls?.length || 0) > 0 || (op.neg_controls && op.neg_controls.length > 0)) && (op.qubits?.length || 0) === 0) return null;

          // Measurement: a meter, wired to the register by the line drawn above.
          if (shape === "meter") {
            return (
              <div
                key={op.id}
                className={`gate meter${selectedId === op.id ? " selected" : ""}`}
                draggable
                onDragStart={(e) => {
                  e.stopPropagation();
                  setMovingOp({ id: op.id, handleType: "whole" });
                  e.dataTransfer.setData("op-id", op.id);
                  e.dataTransfer.setData("handle-type", "whole");
                  e.dataTransfer.effectAllowed = "move";
                }}
                onDragEnd={() => {
                  setMovingOp(null);
                  setDragHover(null);
                }}
                style={{
                  left: colX(op.layer) + pad,
                  top: TOP + q * CELL + pad,
                  width: TILE,
                  height: TILE,
                  background: colour,
                  color: ink,
                  zIndex: 3,
                  cursor: "grab",
                  pointerEvents: (dragging || movingOp) ? "none" : "auto",
                }}
                onClick={(e) => {
                  e.stopPropagation();
                  props.onSelect(op.id);
                }}
                title={`measure q[${q}] → c${op.clbits?.[0] ?? q} — drag to move`}
              >
                <MeterDial />
                <span className="del" onClick={(e) => { e.stopPropagation(); props.onDelete(op.id); }}>
                  ×
                </span>
              </div>
            );
          }

          // Everything else: a filled tile bearing the gate's name.
          const isControlledTile = (op.controls?.length || 0) > 0 || (op.neg_controls && op.neg_controls.length > 0);
          return (
            <div
              key={op.id}
              className={`gate${selectedId === op.id ? " selected" : ""}${paramBadge ? " gate-parametric" : ""}`}
              draggable
              onDragStart={(e) => {
                e.stopPropagation();
                const handleType = isControlledTile ? "target" : "whole";
                setMovingOp({ id: op.id, handleType });
                e.dataTransfer.setData("op-id", op.id);
                e.dataTransfer.setData("handle-type", handleType);
                e.dataTransfer.effectAllowed = "move";
              }}
              onDragEnd={() => {
                setMovingOp(null);
                setDragHover(null);
              }}
              style={{
                left: colX(op.layer) + pad,
                top: TOP + q * CELL + pad,
                width: TILE,
                height: TILE,
                background: colour,
                color: ink,
                fontSize: paramBadge
                  ? undefined
                  : text.length >= 6
                  ? 7.5
                  : text.length === 5
                  ? 8.5
                  : text.length === 4
                  ? 9.5
                  : text.length === 3
                  ? 11.5
                  : 14.5,
                letterSpacing: text.length >= 4 ? "-0.025em" : undefined,
                zIndex: 3,
                cursor: "grab",
                pointerEvents: (dragging || movingOp) ? "none" : "auto",
              }}
              title={`${fullTitle} — drag to move`}
              onClick={(e) => {
                e.stopPropagation();
                props.onSelect(op.id);
              }}
            >
              {paramBadge ? (
                <div className="gate-param-stack">
                  <span className="gate-param-name">{paramBadge.name}{op.inv ? "†" : ""}</span>
                  <span className="gate-param-val">{paramBadge.param}</span>
                </div>
              ) : (
                <span className="gate-label-single">
                  {text}{op.inv ? "†" : ""}
                  {op.power !== undefined && op.power !== "" && op.power !== 1 && (
                    <sup className="gate-power-sup">^{op.power}</sup>
                  )}
                </span>
              )}
              <span className="del" onClick={(e) => { e.stopPropagation(); props.onDelete(op.id); }}>
                ×
              </span>
            </div>
          );
        })}

        {/* IBM Selection Bounding Box & Floating Action Toolbar */}
        {selectedId && (() => {
          const selectedOp = ir.ops.find((o) => o.id === selectedId);
          if (!selectedOp || isBlock(selectedOp)) return null;
          const allWires = [...selectedOp.qubits, ...(selectedOp.controls || []), ...(selectedOp.neg_controls || [])];
          if (allWires.length === 0) return null;
          const minW = Math.min(...allWires);
          const maxW = Math.max(...allWires);
          const boxLeft = colX(selectedOp.layer) + pad - 3;
          const boxTop = TOP + minW * CELL + pad - 3;
          const boxWidth = TILE + 6;
          const boxHeight = (maxW - minW) * CELL + TILE + 6;
          const toolbarLeft = Math.max(GUTTER, colX(selectedOp.layer) + CELL / 2 - 64);
          const toolbarTop = Math.min(boxTop + boxHeight + 8, height - 36);

          return (
            <div key="selected-assembly">
              <div
                className="ibm-selection-box"
                style={{
                  left: boxLeft,
                  top: boxTop,
                  width: boxWidth,
                  height: boxHeight,
                }}
              />
              <div
                className="ibm-floating-toolbar"
                style={{
                  left: toolbarLeft,
                  top: toolbarTop,
                }}
                onClick={(e) => e.stopPropagation()}
              >
                <button
                  type="button"
                  className="ibm-toolbar-btn"
                  title="Edit gate connections & modifiers"
                  onClick={() => props.onOpenEditPanel?.(selectedOp.id)}
                >
                  ✏️
                </button>
                {((selectedOp.controls?.length || 0) > 0 || (selectedOp.neg_controls && selectedOp.neg_controls.length > 0) || (selectedOp.qubits?.length || 0) > 1) && (
                  <button
                    type="button"
                    className="ibm-toolbar-btn"
                    title="Flip control and target"
                    onClick={() => props.onFlipGate?.(selectedOp.id)}
                  >
                    ⇄
                  </button>
                )}
                <button
                  type="button"
                  className="ibm-toolbar-btn"
                  title="Duplicate gate"
                  onClick={() => props.onDuplicateGate?.(selectedOp.id)}
                >
                  📋
                </button>
                <div className="ibm-toolbar-divider" />
                <button
                  type="button"
                  className="ibm-toolbar-btn danger"
                  title="Delete gate"
                  onClick={() => props.onDelete(selectedOp.id)}
                >
                  🗑️
                </button>
              </div>
            </div>
          );
        })()}

        {/* circular endpoint controls at the right end of each wire */}
        {range(0, rows - 1).map((q) => {
          const empty = wireEmpty(q);
          return (
            <div
              key={`e${q}`}
              className={`endpoint${empty ? "" : " blocked"}`}
              style={{
                left: GUTTER + nCols * CELL + 8,
                top: wireY(q) - ENDPOINT / 2,
                width: ENDPOINT,
                height: ENDPOINT,
              }}
              title={
                empty
                  ? `Remove q[${q}]`
                  : `q[${q}] still has gates on it — remove them first`
              }
              onClick={() => props.onRemoveWire?.(q)}
            >
              −
            </div>
          );
        })}
      </div>
    </div>
  );
}
