/**
 * The circuit canvas: qubit wires, gate tiles, and the classical register that
 * measurement collapses into.
 *
 * Layout follows the convention every quantum composer shares and that IBM's
 * made familiar: time runs left to right, one horizontal wire per qubit, gates
 * are tiles on a wire, and multi-qubit gates are joined by a vertical line with
 * a filled dot on each control.
 *
 * Measurement is drawn the way IBM draws it, because the square "M" tile this
 * used to render was actively misleading: a measurement is not a unitary gate,
 * it is the point where a qubit's amplitude collapses into a classical bit.
 * So it gets a meter glyph, and a line running down to the register below. That
 * register is drawn as a double line -- the usual notation for "this carries
 * bits, not amplitudes".
 *
 * Every colour and size here comes from ./theme, so the look can be retuned
 * without touching this file.
 */
import { useMemo } from "react";
import type { CircuitIR, Op, PaletteItem } from "./types";
import { describeCondition, involvedQubits, range, rowSpan } from "./ir";
import { COLOURS, GEOMETRY, gateColour, gateShape, gateText, qubitAccent } from "./theme";

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
  // The register is always at least one bit wide: a zero-width register would
  // make the canvas jump as circuits are edited.
  const nClbits = Math.max(1, ir.n_clbits ?? 0);

  const { cell: CELL, gutter: GUTTER, header: TOP, clbitCell: CL_CELL, registerGap: REG_GAP } =
    GEOMETRY;

  const width = GUTTER + nCols * CELL + 20;
  const regTop = TOP + rows * CELL + REG_GAP;
  const height = regTop + nClbits * CL_CELL + 6;

  /** Vertical centre of qubit row `q`. */
  const wireY = (q: number) => TOP + q * CELL + CELL / 2;
  /** Vertical centre of classical bit `c`. */
  const clbitY = (c: number) => regTop + c * CL_CELL + CL_CELL / 2;
  /** Left edge of column `layer`. */
  const colX = (layer: number) => GUTTER + layer * CELL;

  const isBlock = (op: Op) => op.body.length > 0 || op.else_body.length > 0 || op.kind === "box";

  /** Rows that are legal control/target picks for the pending selection. */
  const pickable = useMemo(() => {
    if (!pending) return new Set<number>();
    const used = new Set(involvedQubits(pending.op));
    return new Set(range(0, rows - 1).filter((q) => !used.has(q)));
  }, [pending, rows]);

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
              <span className="qchip" style={{ background: qubitAccent(q) }} />
              q{q}
            </div>
            <div className="wire" style={{ left: GUTTER, top: wireY(q) - 1, width: nCols * CELL }} />
          </div>
        ))}

        {/* drop / pick cells — qubit rows only; classical bits are not targets */}
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

        {/* the classical register, below the last wire */}
        {range(0, nClbits - 1).map((c) => (
          <div key={`cl${c}`}>
            {/* Two strokes, three pixels apart: the standard notation for a wire
                that carries classical bits rather than amplitudes. */}
            <div className="clbit" style={{ left: GUTTER, top: clbitY(c) - 2, width: nCols * CELL }} />
            <div className="clbit" style={{ left: GUTTER, top: clbitY(c) + 1, width: nCols * CELL }} />
            <div
              className="clabel"
              style={{ position: "absolute", left: 0, top: regTop + c * CL_CELL, width: GUTTER, height: CL_CELL }}
            >
              c{c}
            </div>
          </div>
        ))}

        {/* measurement: the wire from the meter down to its classical bit */}
        {ir.ops.map((op) => {
          if (op.kind !== "measure") return null;
          const q = op.qubits[0];
          const c = op.clbits[0] ?? q;
          if (q == null) return null;
          return (
            <div
              key={`m${op.id}`}
              className="m-wire"
              style={{
                left: colX(op.layer) + CELL / 2 - 1,
                top: wireY(q),
                height: Math.max(0, clbitY(c) - wireY(q)),
                background: COLOURS.measure,
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
                style={{
                  left: colX(op.layer) + CELL / 2 - 1,
                  top: wireY(lo),
                  height: (hi - lo) * CELL,
                  background: COLOURS.control,
                }}
              />
              {op.controls.map((q) => (
                <div
                  key={`d${op.id}-${q}`}
                  className="ctrl-dot"
                  style={{
                    left: colX(op.layer) + CELL / 2 - 6.5,
                    top: wireY(q) - 6.5,
                    background: COLOURS.control,
                  }}
                  title={`control q${q}`}
                />
              ))}
            </div>
          );
        })}

        {/* ops */}
        {ir.ops.map((op) => {
          const shape = gateShape(op);
          const colour = gateColour(op);
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
                <span className="block-label" style={{ background: colour }}>
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
                  borderColor: COLOURS.barrier,
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
                  className="ctrl-line"
                  style={{
                    left: colX(op.layer) + CELL / 2 - 1,
                    top: wireY(Math.min(...op.qubits)),
                    height: Math.abs(op.qubits[0] - op.qubits[1]) * CELL,
                    background: COLOURS.swap,
                  }}
                />
                {op.qubits.map((q, i) => (
                  <div
                    key={`${op.id}-${i}`}
                    className={`gate swap${selectedId === op.id ? " selected" : ""}`}
                    draggable
                    onDragStart={(e) => e.dataTransfer.setData("op-id", op.id)}
                    style={{
                      left: colX(op.layer) + 8,
                      top: TOP + q * CELL + 8,
                      width: CELL - 16,
                      height: CELL - 16,
                      color: COLOURS.swap,
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

          // The ⊕ target of a controlled-X. A circle, not a tile: the shape is
          // what tells you which end of a CNOT is which.
          if (shape === "target") {
            return (
              <div
                key={op.id}
                className={`gate target${selectedId === op.id ? " selected" : ""}`}
                draggable
                onDragStart={(e) => e.dataTransfer.setData("op-id", op.id)}
                style={{
                  left: colX(op.layer) + 6,
                  top: TOP + q * CELL + 6,
                  width: CELL - 12,
                  height: CELL - 12,
                  borderColor: COLOURS.control,
                  color: COLOURS.control,
                }}
                onClick={(e) => {
                  e.stopPropagation();
                  props.onSelect(op.id);
                }}
                title="CNOT target"
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
                  left: colX(op.layer) + 3,
                  top: TOP + q * CELL + 5,
                  width: CELL - 6,
                  height: CELL - 10,
                  background: COLOURS.measure,
                }}
                onClick={(e) => {
                  e.stopPropagation();
                  props.onSelect(op.id);
                }}
                title={`measure q${q} → c${op.clbits[0] ?? q}`}
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
                left: colX(op.layer) + 3,
                top: TOP + q * CELL + 5,
                width: CELL - 6,
                height: CELL - 10,
                background: colour,
                fontSize: text.length > 4 ? 9 : text.length > 2 ? 10 : 13,
              }}
              title={op.kind === "if" || op.kind === "while" ? `if ${describeCondition(op.condition)}` : text}
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
      </div>
    </div>
  );
}
