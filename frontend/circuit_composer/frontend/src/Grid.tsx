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
import { useMemo } from "react";
import type { CircuitIR, Op, PaletteItem } from "./types";
import { involvedQubits, range, rowSpan } from "./ir";
import { GEOMETRY, gateColour, gateForeground, gateShape, gateText } from "./theme";

export interface PendingSelection {
  op: Op;
  need: number; // -1 = arbitrary
  mode: "controls" | "target2";
}

interface Props {
  ir: CircuitIR;
  nCols: number;
  selectedId: string | null;
  pending: PendingSelection | null;
  dragging: PaletteItem | null;
  onDropAt: (qubit: number, layer: number) => void;
  onPick: (qubit: number) => void;
  onSelect: (id: string | null) => void;
  onDelete: (id: string) => void;
  onOpenBlock: (id: string) => void;
  onMoveOp: (id: string, qubit: number, layer: number) => void;
  /** Remove the given qubit wire. Refused (with a notice) if gates sit on it. */
  onRemoveWire?: (qubit: number) => void;
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

export default function Grid(props: Props) {
  const { ir, nCols, selectedId, pending, dragging } = props;
  const rows = ir.n_qubits;
  const nClbits = Math.max(1, ir.n_clbits ?? 0);

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
    if (!pending) return new Set<number>();
    const used = new Set(involvedQubits(pending.op));
    return new Set(range(0, rows - 1).filter((q) => !used.has(q)));
  }, [pending, rows]);

  /** True when nothing has been placed on this wire, so it can be removed. */
  const wireEmpty = (q: number) => !ir.ops.some((o) => [...o.qubits, ...o.controls].includes(q));

  return (
    <div className="grid-scroll">
      <div className="grid" style={{ width, height, position: "relative" }}>
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

        {/* drop / pick cells — qubit rows only; the register is not a target */}
        {range(0, rows - 1).map((q) =>
          range(0, nCols - 1).map((c) => {
            const canPick = pending != null && pickable.has(q);
            return (
              <div
                key={`c${q}-${c}`}
                className={`cell${dragging ? " drop" : ""}${canPick ? " pickable" : ""}`}
                style={{ position: "absolute", left: colX(c), top: TOP + q * CELL }}
                onDragOver={(e) => {
                  if (dragging) e.preventDefault();
                }}
                onDrop={(e) => {
                  e.preventDefault();
                  const moving = e.dataTransfer.getData("op-id");
                  if (moving) props.onMoveOp(moving, q, c);
                  else props.onDropAt(q, c);
                }}
                onClick={() => {
                  if (canPick) props.onPick(q);
                  else if (!pending) props.onSelect(null);
                }}
              />
            );
          }),
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
          if (!op.controls.length || isBlock(op)) return null;
          const all = [...op.controls, ...op.qubits];
          const lo = Math.min(...all);
          const hi = Math.max(...all);
          return (
            <div key={`ctl${op.id}`}>
              <div
                className="ctrl-line"
                style={{ left: colX(op.layer) + CELL / 2 - 1, top: wireY(lo), height: (hi - lo) * CELL }}
              />
              {op.controls.map((q) => (
                <div
                  key={`d${op.id}-${q}`}
                  className="ctrl-dot"
                  style={{ left: colX(op.layer) + CELL / 2 - 6.5, top: wireY(q) - 6.5 }}
                  title={`control q[${q}]`}
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
                style={{
                  left: colX(op.layer) + CELL / 2 - 1,
                  top: TOP + 2,
                  height: rows * CELL - 4,
                }}
                title="Barrier — the compiler may not reorder across this line"
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
          if (shape === "swap" && op.qubits.length === 2) {
            return (
              <div key={op.id}>
                <div
                  className="ctrl-line swap-line"
                  style={{
                    left: colX(op.layer) + CELL / 2 - 1,
                    top: wireY(Math.min(...op.qubits)),
                    height: Math.abs(op.qubits[0] - op.qubits[1]) * CELL,
                  }}
                />
                {op.qubits.map((q, i) => (
                  <div
                    key={`${op.id}-${i}`}
                    className={`gate swap${selectedId === op.id ? " selected" : ""}`}
                    draggable
                    onDragStart={(e) => e.dataTransfer.setData("op-id", op.id)}
                    style={{
                      left: colX(op.layer) + pad,
                      top: TOP + q * CELL + pad,
                      width: TILE,
                      height: TILE,
                      background: colour,
                      color: ink,
                    }}
                    onClick={(e) => {
                      e.stopPropagation();
                      props.onSelect(op.id);
                    }}
                    title="SWAP"
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
            return (
              <div
                key={op.id}
                className={`gate target${selectedId === op.id ? " selected" : ""}`}
                draggable
                onDragStart={(e) => e.dataTransfer.setData("op-id", op.id)}
                style={{
                  left: colX(op.layer) + pad,
                  top: TOP + q * CELL + pad,
                  width: TILE,
                  height: TILE,
                  background: colour,
                  color: ink,
                }}
                onClick={(e) => {
                  e.stopPropagation();
                  props.onSelect(op.id);
                }}
                title={`controlled ${(op.gate ?? "").toUpperCase()} target`}
              >
                <span className="del" onClick={(e) => { e.stopPropagation(); props.onDelete(op.id); }}>
                  ×
                </span>
              </div>
            );
          }

          // Measurement: a meter, wired to the register by the line drawn above.
          if (shape === "meter") {
            return (
              <div
                key={op.id}
                className={`gate meter${selectedId === op.id ? " selected" : ""}`}
                draggable
                onDragStart={(e) => e.dataTransfer.setData("op-id", op.id)}
                style={{
                  left: colX(op.layer) + pad,
                  top: TOP + q * CELL + pad,
                  width: TILE,
                  height: TILE,
                  background: colour,
                  color: ink,
                }}
                onClick={(e) => {
                  e.stopPropagation();
                  props.onSelect(op.id);
                }}
                title={`measure q[${q}] → c${op.clbits[0] ?? q}`}
              >
                <MeterDial />
                <span className="del" onClick={(e) => { e.stopPropagation(); props.onDelete(op.id); }}>
                  ×
                </span>
              </div>
            );
          }

          // Everything else: a filled tile bearing the gate's name.
          return (
            <div
              key={op.id}
              className={`gate${selectedId === op.id ? " selected" : ""}`}
              draggable
              onDragStart={(e) => e.dataTransfer.setData("op-id", op.id)}
              style={{
                left: colX(op.layer) + pad,
                top: TOP + q * CELL + pad,
                width: TILE,
                height: TILE,
                background: colour,
                color: ink,
                fontSize: text.length > 4 ? 9 : text.length > 2 ? 11 : 15,
              }}
              title={text}
              onClick={(e) => {
                e.stopPropagation();
                props.onSelect(op.id);
              }}
            >
              {text}
              <span className="del" onClick={(e) => { e.stopPropagation(); props.onDelete(op.id); }}>
                ×
              </span>
            </div>
          );
        })}

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
