import React, { useState } from "react";
import {
  Plus,
  Trash2,
  ChevronLeft,
  ChevronRight,
  Settings2,
  Sliders,
  RotateCcw,
} from "lucide-react";
import { type QuditCircuit, type QuditWire } from "../../api/quditLab";
import { Badge, Button } from "../ui";

interface QuditCircuitEditorProps {
  circuit: QuditCircuit;
  maxQudits: number;
  onUpdateCircuit: (updated: QuditCircuit) => void;
  onResetCircuit: () => void;
}

export const QuditCircuitEditor: React.FC<QuditCircuitEditorProps> = ({
  circuit,
  maxQudits,
  onUpdateCircuit,
  onResetCircuit,
}) => {
  const [selectedOpId, setSelectedOpId] = useState<string | null>(null);

  const dimension = circuit.dimension;
  const wires = circuit.wires;
  const ops = circuit.ops;

  const handleAddWire = () => {
    if (wires.length >= maxQudits) return;
    const newIndex = wires.length;
    const newWire: QuditWire = {
      id: `q${newIndex}`,
      index: newIndex,
      dimension: dimension,
      initial_state: 0,
      label: `q${newIndex}`,
    };
    onUpdateCircuit({
      ...circuit,
      wires: [...wires, newWire],
    });
  };

  const handleRemoveWire = (wireIdx: number) => {
    if (wires.length <= 1) return;
    // Remove wire and re-index
    const remainingWires = wires
      .filter((w) => w.index !== wireIdx)
      .map((w, idx) => ({ ...w, index: idx, id: `q${idx}` }));

    // Filter out operations referencing the removed wire or update indices
    const updatedOps = ops
      .filter((op) => !op.targets.includes(wireIdx) && !op.controls.includes(wireIdx))
      .map((op) => ({
        ...op,
        targets: op.targets.map((t) => (t > wireIdx ? t - 1 : t)),
        controls: op.controls.map((c) => (c > wireIdx ? c - 1 : c)),
      }));

    onUpdateCircuit({
      ...circuit,
      wires: remainingWires,
      ops: updatedOps,
    });
    if (selectedOpId) setSelectedOpId(null);
  };

  const handleInitialStateChange = (wireIdx: number, state: number) => {
    const updatedWires = wires.map((w) =>
      w.index === wireIdx ? { ...w, initial_state: state } : w
    );
    onUpdateCircuit({ ...circuit, wires: updatedWires });
  };

  const handleRemoveOp = (opId: string) => {
    const updatedOps = ops.filter((o) => o.id !== opId);
    onUpdateCircuit({ ...circuit, ops: updatedOps });
    if (selectedOpId === opId) setSelectedOpId(null);
  };

  const handleMoveOp = (index: number, direction: "left" | "right") => {
    const targetIdx = direction === "left" ? index - 1 : index + 1;
    if (targetIdx < 0 || targetIdx >= ops.length) return;
    const newOps = [...ops];
    const temp = newOps[index];
    newOps[index] = newOps[targetIdx];
    newOps[targetIdx] = temp;
    onUpdateCircuit({ ...circuit, ops: newOps });
  };

  const handleUpdateOpParams = (opId: string, newParams: Record<string, number>) => {
    const updatedOps = ops.map((op) =>
      op.id === opId ? { ...op, params: { ...op.params, ...newParams } } : op
    );
    onUpdateCircuit({ ...circuit, ops: updatedOps });
  };

  const handleUpdateOpWires = (
    opId: string,
    targets: number[],
    controls: number[] = []
  ) => {
    const updatedOps = ops.map((op) =>
      op.id === opId ? { ...op, targets, controls } : op
    );
    onUpdateCircuit({ ...circuit, ops: updatedOps });
  };

  const selectedOp = ops.find((o) => o.id === selectedOpId);

  return (
    <div className="rounded-xl border border-line bg-card/60 backdrop-blur-md p-4 shadow-sm space-y-4">
      {/* Editor Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line/60 pb-3">
        <div className="flex items-center gap-2">
          <Sliders className="h-4 w-4 text-accent" />
          <h2 className="text-sm font-semibold tracking-wide text-ink">Qudit Circuit Canvas</h2>
          <Badge tone="neutral">
            {wires.length} / {maxQudits} Qudits
          </Badge>
          <Badge tone="neutral">
            {ops.length} Gates
          </Badge>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleAddWire}
            disabled={wires.length >= maxQudits}
            className="text-xs"
            aria-label="Add qudit wire"
          >
            <Plus className="h-3.5 w-3.5 mr-1 text-accent" />
            Add Qudit
          </Button>

          <Button
            variant="ghost"
            size="sm"
            onClick={onResetCircuit}
            className="text-xs text-ink-3 hover:text-red-400"
            aria-label="Reset circuit"
          >
            <RotateCcw className="h-3.5 w-3.5 mr-1" />
            Reset
          </Button>
        </div>
      </div>

      {/* Circuit Grid Canvas */}
      <div className="overflow-x-auto min-h-[160px] pb-2 scrollbar-thin">
        <div className="min-w-[600px] flex flex-col gap-2 relative">
          {wires.map((wire) => (
            <div key={wire.id} className="flex items-center gap-3 relative group h-14">
              {/* Wire Label & Basis Level Selector */}
              <div className="flex items-center gap-2 w-48 shrink-0 bg-subtle/40 rounded-lg p-1.5 border border-line/60">
                <span className="text-xs font-mono font-bold text-accent px-1.5 py-0.5 rounded bg-accent/10">
                  {wire.id}
                </span>

                <div className="flex items-center gap-1">
                  <span className="text-[11px] text-ink-3">|</span>
                  <select
                    value={wire.initial_state}
                    onChange={(e) => handleInitialStateChange(wire.index, Number(e.target.value))}
                    className="bg-bg border border-line rounded px-1.5 py-0.5 text-xs font-mono font-bold text-ink focus:outline-none focus:border-accent cursor-pointer"
                    aria-label={`Initial state for ${wire.id}`}
                  >
                    {Array.from({ length: wire.dimension }, (_, i) => (
                      <option key={i} value={i}>
                        {i}
                      </option>
                    ))}
                  </select>
                  <span className="text-[11px] text-ink-3">⟩</span>
                </div>

                <Badge tone="neutral" className="ml-auto text-[10px]">
                  d={wire.dimension}
                </Badge>

                {wires.length > 1 && (
                  <button
                    type="button"
                    onClick={() => handleRemoveWire(wire.index)}
                    className="text-ink-3 hover:text-red-400 p-1 rounded hover:bg-red-500/10 transition-colors ml-1"
                    aria-label={`Remove wire ${wire.id}`}
                  >
                    <Trash2 className="h-3 w-3" />
                  </button>
                )}
              </div>

              {/* Wire Line with Gate Slots */}
              <div className="relative flex-1 flex items-center h-full">
                {/* Continuous wire line */}
                <div className="absolute left-0 right-0 top-1/2 -translate-y-1/2 h-[2px] bg-line/80 z-0" />

                {/* Operations on this wire */}
                <div className="flex items-center gap-4 z-10 pl-2">
                  {ops.map((op) => {
                    const isTarget = op.targets.includes(wire.index);
                    const isControl = op.controls.includes(wire.index);
                    const isSelected = selectedOpId === op.id;

                    if (!isTarget && !isControl) {
                      // Empty wire pass-through spacer
                      return (
                        <div
                          key={`${op.id}-${wire.index}`}
                          className="w-12 h-10 flex items-center justify-center shrink-0"
                        />
                      );
                    }

                    return (
                      <div
                        key={`${op.id}-${wire.index}`}
                        onClick={() => setSelectedOpId(isSelected ? null : op.id)}
                        className={`relative w-12 h-10 flex items-center justify-center rounded-lg border text-xs font-mono font-bold cursor-pointer transition-all duration-150 select-none shrink-0 ${
                          isSelected
                            ? "border-accent bg-accent/20 text-accent shadow-[0_0_12px_rgba(59,130,246,0.5)] scale-105"
                            : isControl
                            ? "border-line bg-subtle text-ink hover:border-accent/40"
                            : "border-line bg-subtle text-ink hover:border-accent/40 hover:bg-accent/10"
                        }`}
                        title={`Click to configure ${op.gate.toUpperCase()} gate`}
                      >
                        {isControl ? (
                          <div className="h-3 w-3 rounded-full bg-accent shadow-sm" />
                        ) : op.gate === "sum" ? (
                          <span className="text-base text-accent font-bold">⊕</span>
                        ) : op.gate === "swap" ? (
                          <span className="text-sm font-bold text-amber-400">✕</span>
                        ) : (
                          <span>
                            {op.gate.toUpperCase()}_{dimension}
                          </span>
                        )}

                        {/* Connector dot indicator for 2-qudit gates */}
                        {(op.controls.length > 0 || op.targets.length > 1) && (
                          <div className="absolute -top-1 right-1 h-1.5 w-1.5 rounded-full bg-amber-400" />
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Selected Operation Parameter Inspector Panel */}
      {selectedOp && (
        <div className="rounded-lg border border-accent/30 bg-accent/5 p-3 text-xs space-y-2 animate-in fade-in duration-150">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Settings2 className="h-4 w-4 text-accent" />
              <span className="font-semibold text-ink">
                Configure Operation: {selectedOp.gate.toUpperCase()} (ID: {selectedOp.id})
              </span>
            </div>

            <div className="flex items-center gap-1.5">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleMoveOp(ops.findIndex((o) => o.id === selectedOp.id), "left")}
                disabled={ops.findIndex((o) => o.id === selectedOp.id) === 0}
                className="h-6 px-1.5 text-xs"
                aria-label="Move gate left"
              >
                <ChevronLeft className="h-3 w-3" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleMoveOp(ops.findIndex((o) => o.id === selectedOp.id), "right")}
                disabled={ops.findIndex((o) => o.id === selectedOp.id) === ops.length - 1}
                className="h-6 px-1.5 text-xs"
                aria-label="Move gate right"
              >
                <ChevronRight className="h-3 w-3" />
              </Button>
              <Button
                variant="danger"
                size="sm"
                onClick={() => handleRemoveOp(selectedOp.id)}
                className="h-6 px-2 text-xs"
                aria-label="Delete gate"
              >
                <Trash2 className="h-3 w-3 mr-1" />
                Remove
              </Button>
            </div>
          </div>

          {/* Wire operands mapping */}
          <div className="flex flex-wrap items-center gap-4 pt-1">
            {selectedOp.controls.length > 0 && (
              <div className="flex items-center gap-2">
                <span className="text-ink-3">Control Wire:</span>
                <select
                  value={selectedOp.controls[0]}
                  onChange={(e) => {
                    const newCtrl = Number(e.target.value);
                    if (newCtrl === selectedOp.targets[0]) return;
                    handleUpdateOpWires(selectedOp.id, selectedOp.targets, [newCtrl]);
                  }}
                  className="bg-bg border border-line rounded px-2 py-1 font-mono text-xs text-ink"
                  aria-label="Control wire"
                >
                  {wires.map((w) => (
                    <option key={w.id} value={w.index} disabled={w.index === selectedOp.targets[0]}>
                      {w.id}
                    </option>
                  ))}
                </select>
              </div>
            )}

            <div className="flex items-center gap-2">
              <span className="text-ink-3">Target Wire:</span>
              <select
                value={selectedOp.targets[0]}
                onChange={(e) => {
                  const newTgt = Number(e.target.value);
                  if (selectedOp.controls.includes(newTgt)) return;
                  handleUpdateOpWires(selectedOp.id, [newTgt], selectedOp.controls);
                }}
                className="bg-bg border border-line rounded px-2 py-1 font-mono text-xs text-ink"
                aria-label="Target wire"
              >
                {wires.map((w) => (
                  <option
                    key={w.id}
                    value={w.index}
                    disabled={selectedOp.controls.includes(w.index)}
                  >
                    {w.id}
                  </option>
                ))}
              </select>
            </div>

            {/* 2nd target for SWAP */}
            {selectedOp.gate === "swap" && (
              <div className="flex items-center gap-2">
                <span className="text-ink-3">Swap With:</span>
                <select
                  value={selectedOp.targets[1] ?? (selectedOp.targets[0] === 0 ? 1 : 0)}
                  onChange={(e) => {
                    const newTgt2 = Number(e.target.value);
                    handleUpdateOpWires(selectedOp.id, [selectedOp.targets[0], newTgt2], []);
                  }}
                  className="bg-bg border border-line rounded px-2 py-1 font-mono text-xs text-ink"
                  aria-label="Second swap wire"
                >
                  {wires.map((w) => (
                    <option
                      key={w.id}
                      value={w.index}
                      disabled={w.index === selectedOp.targets[0]}
                    >
                      {w.id}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* Subspace rotation parameters */}
            {selectedOp.gate === "r_jk" && (
              <div className="flex flex-wrap items-center gap-3 w-full pt-1 border-t border-line/40">
                <div className="flex items-center gap-1.5">
                  <span className="text-ink-3">Level j:</span>
                  <select
                    value={selectedOp.params.j ?? 0}
                    onChange={(e) => handleUpdateOpParams(selectedOp.id, { j: Number(e.target.value) })}
                    className="bg-bg border border-line rounded px-2 py-0.5 font-mono text-xs"
                    aria-label="Rotation level j"
                  >
                    {Array.from({ length: dimension - 1 }, (_, i) => (
                      <option key={i} value={i}>
                        |{i}⟩
                      </option>
                    ))}
                  </select>
                </div>

                <div className="flex items-center gap-1.5">
                  <span className="text-ink-3">Level k:</span>
                  <select
                    value={selectedOp.params.k ?? 1}
                    onChange={(e) => handleUpdateOpParams(selectedOp.id, { k: Number(e.target.value) })}
                    className="bg-bg border border-line rounded px-2 py-0.5 font-mono text-xs"
                    aria-label="Rotation level k"
                  >
                    {Array.from({ length: dimension }, (_, i) => i)
                      .filter((i) => i > (selectedOp.params.j ?? 0))
                      .map((i) => (
                        <option key={i} value={i}>
                          |{i}⟩
                        </option>
                      ))}
                  </select>
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-ink-3">Angle θ (rad):</span>
                  <input
                    type="range"
                    min={-3.14}
                    max={3.14}
                    step={0.05}
                    value={selectedOp.params.theta ?? 1.57}
                    onChange={(e) => handleUpdateOpParams(selectedOp.id, { theta: Number(e.target.value) })}
                    className="w-24 accent-accent"
                    aria-label="Rotation angle theta"
                  />
                  <span className="font-mono text-ink">
                    {(selectedOp.params.theta ?? 1.57).toFixed(2)}
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-ink-3">Phase φ (rad):</span>
                  <input
                    type="range"
                    min={-3.14}
                    max={3.14}
                    step={0.05}
                    value={selectedOp.params.phi ?? 0.0}
                    onChange={(e) => handleUpdateOpParams(selectedOp.id, { phi: Number(e.target.value) })}
                    className="w-24 accent-accent"
                    aria-label="Rotation phase phi"
                  />
                  <span className="font-mono text-ink">
                    {(selectedOp.params.phi ?? 0.0).toFixed(2)}
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
