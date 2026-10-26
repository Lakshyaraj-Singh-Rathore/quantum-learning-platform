import React, { useState, useMemo } from "react";
import {
  RotateCcw,
  RotateCw,
  Search,
  Grid as GridIcon,
  Trash2,
  Copy,
  ArrowRightLeft,
  Sliders,
  SlidersHorizontal,
} from "lucide-react";
import {
  type QuditCircuit,
  type QuditOp,
  type QuditWire,
  type QuditGateCatalogueItem,
} from "../../api/quditLab";
import { cn } from "../ui";

interface QuditCircuitEditorProps {
  circuit: QuditCircuit;
  onChange?: (circuit: QuditCircuit) => void;
  onUpdateCircuit?: (circuit: QuditCircuit) => void;
  onRunSimulation?: () => void;
  onResetCircuit: () => void;
  dimension?: number;
  maxQudits: number;
  catalogue?: QuditGateCatalogueItem[];
}

interface PaletteGateDef {
  id: string;
  label: string;
  sublabel?: string;
  name: string;
  category: "shift" | "fourier" | "rotation" | "two_qudit" | "multi" | "control_flow";
  bg: string;
  fg: string;
  numQudits: number;
  hasControls?: boolean;
  isSwap?: boolean;
  defaultParams?: Record<string, any>;
}

function parseParamExpr(expr: string): number {
  if (!expr || !expr.trim()) return 0;
  const clean = expr.trim().toLowerCase().replace(/pi/g, String(Math.PI));
  if (!/^[-+*/0-9.()\s]+$/.test(clean)) return 0;
  try {
    const val = Function(`'use strict'; return (${clean})`)();
    return typeof val === "number" && !isNaN(val) ? val : 0;
  } catch {
    return 0;
  }
}

export const QuditCircuitEditor: React.FC<QuditCircuitEditorProps> = ({
  circuit,
  onChange,
  onUpdateCircuit,
  onResetCircuit,
  dimension: propDim,
  maxQudits,
}) => {
  const dimension = propDim ?? circuit.dimension;
  const { wires, ops } = circuit;

  // History for Undo / Redo
  const [history, setHistory] = useState<QuditCircuit[]>([]);
  const [future, setFuture] = useState<QuditCircuit[]>([]);

  // Selection & drag states
  const [selectedPaletteGate, setSelectedPaletteGate] = useState<string>("f");
  const [selectedOpId, setSelectedOpId] = useState<string | null>(null);
  const [draggingGate, setDraggingGate] = useState<PaletteGateDef | null>(null);
  const [dragOverCell, setDragOverCell] = useState<{ wire: number; col: number } | null>(null);

  // Toolbar & inspection states
  const [alignment, setAlignment] = useState<"preserve" | "left">("preserve");
  const [inspect, setInspect] = useState<boolean>(true);
  const [showCode, setShowCode] = useState<boolean>(true);
  const [search, setSearch] = useState<string>("");
  const [showSearch, setShowSearch] = useState<boolean>(false);
  const [categoryFilter, setCategoryFilter] = useState<string>("all");
  const [paramExpr, setParamExpr] = useState<string>("pi/2");

  const commitUpdate = (newCircuit: QuditCircuit) => {
    setHistory((prev) => [...prev.slice(-30), circuit]);
    if (onUpdateCircuit) onUpdateCircuit(newCircuit);
    if (onChange) onChange(newCircuit);
  };

  const handleUndo = () => {
    if (history.length === 0) return;
    const prev = history[history.length - 1];
    setHistory((h) => h.slice(0, -1));
    setFuture((f) => [circuit, ...f]);
    if (onUpdateCircuit) onUpdateCircuit(prev);
    if (onChange) onChange(prev);
    setSelectedOpId(null);
  };

  const handleRedo = () => {
    if (future.length === 0) return;
    const next = future[0];
    setFuture((f) => f.slice(1));
    setHistory((h) => [...h, circuit]);
    if (onUpdateCircuit) onUpdateCircuit(next);
    if (onChange) onChange(next);
    setSelectedOpId(null);
  };

  // ---------------------------------------------------------------------------
  // Qudit-Specific Operations Palette (d in {3, 4, 5})
  // ---------------------------------------------------------------------------
  const QUDIT_PALETTE: PaletteGateDef[] = useMemo(
    () => [
      // 1. Single Qudit: Shift, Phase & Fourier
      {
        id: "x",
        label: `X${dimension}`,
        sublabel: "Shift",
        name: `Cyclic Shift X_${dimension}`,
        category: "shift",
        bg: "#2563eb",
        fg: "#ffffff",
        numQudits: 1,
        defaultParams: { power: 1 },
      },
      {
        id: "z",
        label: `Z${dimension}`,
        sublabel: "Phase",
        name: `Clock Phase Z_${dimension}`,
        category: "shift",
        bg: "#1d4ed8",
        fg: "#ffffff",
        numQudits: 1,
        defaultParams: { power: 1 },
      },
      {
        id: "f",
        label: `F${dimension}`,
        sublabel: "Fourier",
        name: `Generalized Fourier F_${dimension}`,
        category: "fourier",
        bg: "#ea580c",
        fg: "#ffffff",
        numQudits: 1,
        defaultParams: {},
      },
      {
        id: "f_dag",
        label: `F${dimension}†`,
        sublabel: "Inv F",
        name: `Inverse Fourier F_${dimension}†`,
        category: "fourier",
        bg: "#c2410c",
        fg: "#ffffff",
        numQudits: 1,
        defaultParams: {},
      },
      {
        id: "id",
        label: `I${dimension}`,
        sublabel: "Id",
        name: `Identity I_${dimension}`,
        category: "fourier",
        bg: "#0891b2",
        fg: "#ffffff",
        numQudits: 1,
        defaultParams: {},
      },
      {
        id: "p_j",
        label: "P(θ)",
        sublabel: "Lvl Ph",
        name: `Level Phase P_j(θ)`,
        category: "rotation",
        bg: "#db2777",
        fg: "#ffffff",
        numQudits: 1,
        defaultParams: { j: 1, theta: Math.PI / 2 },
      },
      {
        id: "r_jk",
        label: "R_jk",
        sublabel: "Givens",
        name: `Pairwise Givens Rotation R_jk(θ, φ)`,
        category: "rotation",
        bg: "#be185d",
        fg: "#ffffff",
        numQudits: 1,
        defaultParams: { j: 0, k: 1, theta: Math.PI / 2, phi: 0 },
      },
      {
        id: "diag",
        label: `D${dimension}`,
        sublabel: "Diag",
        name: `Diagonal Unitary D_${dimension}`,
        category: "rotation",
        bg: "#9333ea",
        fg: "#ffffff",
        numQudits: 1,
        defaultParams: { phi_0: 0.0, phi_1: Math.PI / 2 },
      },

      // 2. Two-Qudit Entangling & Exchange
      {
        id: "sum",
        label: `SUM${dimension}`,
        sublabel: "Add",
        name: `Controlled Modular Add SUM_${dimension}`,
        category: "two_qudit",
        bg: "#7c3aed",
        fg: "#ffffff",
        hasControls: true,
        numQudits: 2,
        defaultParams: {},
      },
      {
        id: "sum_dag",
        label: `SUM†`,
        sublabel: "InvAdd",
        name: `Inverse Add SUM_${dimension}†`,
        category: "two_qudit",
        bg: "#6d28d9",
        fg: "#ffffff",
        hasControls: true,
        numQudits: 2,
        defaultParams: {},
      },
      {
        id: "csx",
        label: "CSX",
        sublabel: "CtrlX",
        name: `Controlled Shift CSX_${dimension}`,
        category: "two_qudit",
        bg: "#8b5cf6",
        fg: "#ffffff",
        hasControls: true,
        numQudits: 2,
        defaultParams: { c: 1, a: 1 },
      },
      {
        id: "cp",
        label: `CP${dimension}`,
        sublabel: "CtrlPh",
        name: `Generalized Controlled Phase GCP_${dimension}`,
        category: "two_qudit",
        bg: "#6366f1",
        fg: "#ffffff",
        hasControls: true,
        numQudits: 2,
        defaultParams: {},
      },
      {
        id: "scp",
        label: "SCP",
        sublabel: "SelPh",
        name: `Selective Controlled Phase SCP_${dimension}`,
        category: "two_qudit",
        bg: "#4f46e5",
        fg: "#ffffff",
        hasControls: true,
        numQudits: 2,
        defaultParams: { c: 1, t: 1, theta: Math.PI / 2 },
      },
      {
        id: "swap",
        label: "SWAP",
        sublabel: "Swap",
        name: `Qudit SWAP_${dimension}`,
        category: "two_qudit",
        bg: "#06b6d4",
        fg: "#ffffff",
        hasControls: false,
        isSwap: true,
        numQudits: 2,
        defaultParams: {},
      },

      // 3. Multi-Qudit & Controlled
      {
        id: "ccx",
        label: "CCX",
        sublabel: "Toffoli",
        name: `Double-Controlled Shift CCX_${dimension}`,
        category: "multi",
        bg: "#0d9488",
        fg: "#ffffff",
        hasControls: true,
        numQudits: 3,
        defaultParams: { c1: 1, c2: 1, a: 1 },
      },
      {
        id: "cswap",
        label: "CSWAP",
        sublabel: "Fredkin",
        name: `Controlled SWAP (Fredkin_${dimension})`,
        category: "multi",
        bg: "#0284c7",
        fg: "#ffffff",
        hasControls: true,
        isSwap: true,
        numQudits: 3,
        defaultParams: { c: 1 },
      },
      {
        id: "mcp",
        label: "MCP",
        sublabel: "MC-Phase",
        name: `Multi-Controlled Phase MCP_${dimension}`,
        category: "multi",
        bg: "#059669",
        fg: "#ffffff",
        hasControls: true,
        numQudits: 3,
        defaultParams: { theta: Math.PI / 2 },
      },

      // 4. Circuit Directives
      {
        id: "measure",
        label: "M",
        sublabel: "Meter",
        name: "Measure Qudit",
        category: "control_flow",
        bg: "#475569",
        fg: "#ffffff",
        numQudits: 1,
        defaultParams: {},
      },
      {
        id: "reset",
        label: "|0⟩",
        sublabel: "Reset",
        name: "Reset to |0⟩",
        category: "control_flow",
        bg: "#334155",
        fg: "#ffffff",
        numQudits: 1,
        defaultParams: {},
      },
      {
        id: "barrier",
        label: "||",
        sublabel: "Barrier",
        name: "Visual Barrier",
        category: "control_flow",
        bg: "#1e293b",
        fg: "#ffffff",
        numQudits: 1,
        defaultParams: {},
      },
    ],
    [dimension]
  );

  const visiblePalette = useMemo(() => {
    let list = QUDIT_PALETTE;
    if (categoryFilter !== "all") {
      if (categoryFilter === "1q") {
        list = list.filter((g) => g.numQudits === 1 && g.category !== "control_flow");
      } else if (categoryFilter === "2q") {
        list = list.filter((g) => g.numQudits === 2);
      } else if (categoryFilter === "multi") {
        list = list.filter((g) => g.numQudits >= 3);
      } else if (categoryFilter === "directives") {
        list = list.filter((g) => g.category === "control_flow");
      }
    }
    if (!search.trim()) return list;
    const needle = search.trim().toLowerCase();
    return list.filter(
      (g) =>
        g.name.toLowerCase().includes(needle) ||
        g.id.toLowerCase().includes(needle) ||
        g.label.toLowerCase().includes(needle) ||
        (g.sublabel && g.sublabel.toLowerCase().includes(needle))
    );
  }, [search, categoryFilter, QUDIT_PALETTE]);

  // Circuit display column count
  const nCols = Math.max(8, ops.length + 3);

  // Map wire index to DOM row index
  const wireRowIndexMap = useMemo(() => {
    const map = new Map<number, number>();
    wires.forEach((w, idx) => {
      map.set(w.index, idx);
    });
    return map;
  }, [wires]);

  // Visual appearance helper for placed gates
  const getGateVisual = (op: QuditOp) => {
    const gateDef = QUDIT_PALETTE.find((g) => g.id === op.gate);
    const bg = gateDef?.bg || "#2563eb";
    const fg = gateDef?.fg || "#ffffff";
    let symbol = gateDef?.label || op.gate.toUpperCase();
    let isRound = false;
    let showDim = true;

    if (op.gate === "sum") {
      symbol = "⊕";
      isRound = true;
      showDim = false;
    } else if (op.gate === "sum_dag") {
      symbol = "⊕†";
      isRound = true;
      showDim = false;
    } else if (op.gate === "swap" || op.gate === "cswap") {
      symbol = "✕";
      showDim = false;
    } else if (op.gate === "measure") {
      symbol = "M";
      showDim = false;
    } else if (op.gate === "barrier") {
      symbol = "║";
      showDim = false;
    } else if (op.gate === "reset") {
      symbol = "|0⟩";
      showDim = false;
    } else if (op.gate === "f" || op.gate === "f_dag") {
      symbol = op.gate === "f_dag" ? `F${op.dimension}†` : `F${op.dimension}`;
      showDim = false;
    } else if (op.gate === "x" || op.gate === "z") {
      symbol = `${op.gate.toUpperCase()}${op.dimension}`;
      showDim = false;
    } else if (op.gate === "csx") {
      symbol = `X⁺${op.params.a ?? 1}`;
      showDim = true;
    }

    return { bg, fg, symbol, isRound, showDim };
  };

  // Continuous unbroken vertical connector lines for multi-qudit gates
  const multiQuditConnectors = useMemo(() => {
    const list: Array<{
      col: number;
      vMin: number;
      vMax: number;
      isSelected: boolean;
    }> = [];

    ops.forEach((op, col) => {
      if (!op) return;
      const allWires = [...(op.controls || []), ...(op.targets || [])];
      if (allWires.length > 1) {
        const rowIndices = allWires.map((w) => wireRowIndexMap.get(w) ?? w);
        const vMin = Math.min(...rowIndices);
        const vMax = Math.max(...rowIndices);
        list.push({
          col,
          vMin,
          vMax,
          isSelected: selectedOpId === op.id,
        });
      }
    });

    return list;
  }, [ops, wireRowIndexMap, selectedOpId]);

  // Wire operations
  const handleAddWire = () => {
    if (wires.length >= maxQudits) return;
    const newIdx = wires.length;
    const newWire: QuditWire = {
      id: `q${newIdx}`,
      index: newIdx,
      dimension: dimension,
      initial_state: 0,
      label: `q${newIdx}`,
    };
    commitUpdate({
      ...circuit,
      wires: [...wires, newWire],
    });
  };

  const handleRemoveWire = (wireIdx: number) => {
    if (wires.length <= 1) return;
    const remainingWires = wires
      .filter((w) => w.index !== wireIdx)
      .map((w, idx) => ({ ...w, index: idx, id: `q${idx}` }));

    const remainingOps = ops
      .filter((op) => !op.targets.includes(wireIdx) && !op.controls.includes(wireIdx))
      .map((op) => ({
        ...op,
        targets: op.targets.map((t) => (t > wireIdx ? t - 1 : t)),
        controls: op.controls.map((c) => (c > wireIdx ? c - 1 : c)),
      }));

    commitUpdate({
      ...circuit,
      wires: remainingWires,
      ops: remainingOps,
    });
    if (selectedOpId) setSelectedOpId(null);
  };

  const handleCycleInitialState = (wireIdx: number) => {
    const updatedWires = wires.map((w) => {
      if (w.index !== wireIdx) return w;
      const nextState = (w.initial_state + 1) % dimension;
      return { ...w, initial_state: nextState };
    });
    commitUpdate({ ...circuit, wires: updatedWires });
  };

  // ---------------------------------------------------------------------------
  // Gate Placement & Drop Handler
  // ---------------------------------------------------------------------------
  const handlePlaceGateAt = (gateId: string, targetWire: number, atCol?: number) => {
    const gateDef = QUDIT_PALETTE.find((g) => g.id === gateId);
    if (!gateDef) return;

    let targets = [targetWire];
    let controls: number[] = [];
    const params: Record<string, any> = { ...(gateDef.defaultParams || {}) };

    // Apply parsed param expression
    const parsedVal = parseParamExpr(paramExpr);
    if (gateDef.id === "p_j" || gateDef.id === "scp" || gateDef.id === "mcp" || gateDef.id === "r_jk") {
      params.theta = parsedVal || Math.PI / 2;
    } else if (gateDef.id === "x" || gateDef.id === "z") {
      params.power = Math.max(1, Math.min(dimension - 1, Math.round(parsedVal || 1)));
    }

    if (gateDef.isSwap) {
      if (gateDef.numQudits === 2) {
        if (wires.length < 2) return;
        const otherWire = targetWire === 0 ? 1 : targetWire - 1;
        targets = [targetWire, otherWire];
        controls = [];
      } else if (gateDef.numQudits === 3) {
        if (wires.length < 3) return;
        controls = [0];
        targets = [1, Math.min(2, wires.length - 1)];
      }
    } else if (gateDef.numQudits === 2) {
      if (wires.length < 2) return;
      const ctrlWire = targetWire === 0 ? 0 : 0;
      const tgtWire = targetWire === 0 ? 1 : targetWire;
      controls = [ctrlWire];
      targets = [tgtWire];
    } else if (gateDef.numQudits === 3) {
      if (wires.length < 3) return;
      controls = [0, 1];
      targets = [Math.max(2, targetWire)];
    }

    const newOp: QuditOp = {
      id: `op-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
      gate: gateDef.id,
      targets,
      controls,
      params,
      dimension,
    };

    let nextOps = [...ops];
    if (atCol !== undefined && atCol < nextOps.length) {
      // Insert at column
      nextOps.splice(atCol, 0, newOp);
    } else {
      nextOps.push(newOp);
    }

    commitUpdate({
      ...circuit,
      ops: nextOps,
    });
    setSelectedOpId(newOp.id);
  };

  const handleDeleteOp = (opId: string) => {
    commitUpdate({
      ...circuit,
      ops: ops.filter((o) => o.id !== opId),
    });
    if (selectedOpId === opId) setSelectedOpId(null);
  };

  const handleDuplicateOp = (opId: string) => {
    const orig = ops.find((o) => o.id === opId);
    if (!orig) return;
    const dup: QuditOp = {
      ...orig,
      id: `op-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
    };
    commitUpdate({
      ...circuit,
      ops: [...ops, dup],
    });
    setSelectedOpId(dup.id);
  };

  // Modify currently selected gate
  const handleUpdateSelectedOp = (updater: (prev: QuditOp) => QuditOp) => {
    if (!selectedOpId) return;
    const updatedOps = ops.map((op) => (op.id === selectedOpId ? updater(op) : op));
    commitUpdate({ ...circuit, ops: updatedOps });
  };

  // Invert Control & Target for 2-qudit gates
  const handleInvertControlTarget = () => {
    if (!selectedOpId) return;
    handleUpdateSelectedOp((op) => {
      if (op.controls.length >= 1 && op.targets.length >= 1) {
        return {
          ...op,
          controls: [op.targets[0]],
          targets: [op.controls[0]],
        };
      }
      return op;
    });
  };

  // Flip targets for SWAP
  const handleFlipSwapTargets = () => {
    if (!selectedOpId) return;
    handleUpdateSelectedOp((op) => {
      if (op.targets.length >= 2) {
        return {
          ...op,
          targets: [op.targets[1], op.targets[0]],
        };
      }
      return op;
    });
  };

  // Clear circuit
  const handleClear = () => {
    commitUpdate({
      ...circuit,
      ops: [],
    });
    setSelectedOpId(null);
  };

  const selectedOp = ops.find((o) => o.id === selectedOpId) || null;

  // Describe op line for Right panel
  const describeOp = (op: QuditOp): string => {
    const g = op.gate.toUpperCase();
    if (op.gate === "swap") {
      const wA = op.targets[0] ?? 0;
      const wB = op.targets[1] ?? 1;
      return `SWAP_${op.dimension} q${wA} ↔ q${wB}`;
    }
    if (op.controls.length > 0) {
      const cStr = op.controls.map((c) => `q${c}`).join(",");
      const tStr = op.targets.map((t) => `q${t}`).join(",");
      return `${g}_${op.dimension} ctrl(${cStr}) → ${tStr}`;
    }
    if (op.gate === "r_jk") {
      const j = op.params.j ?? 0;
      const k = op.params.k ?? 1;
      const th = Number(op.params.theta ?? Math.PI / 2).toFixed(2);
      return `R_${j}${k}(${th}) q${op.targets[0]}`;
    }
    if (op.gate === "p_j") {
      const j = op.params.j ?? 1;
      const th = Number(op.params.theta ?? Math.PI / 2).toFixed(2);
      return `P_${j}(${th}) q${op.targets[0]}`;
    }
    if (op.gate === "x" && op.params.power && op.params.power > 1) {
      return `X_${op.dimension}^${op.params.power} q${op.targets[0]}`;
    }
    if (op.gate === "z" && op.params.power && op.params.power > 1) {
      return `Z_${op.dimension}^${op.params.power} q${op.targets[0]}`;
    }
    if (op.gate === "measure") {
      return `measure q${op.targets[0]} → c${op.targets[0]}`;
    }
    return `${g}_${op.dimension} q${op.targets.join(",q")}`;
  };

  return (
    <div className="rounded-xl border border-line bg-[#07090e] shadow-xl select-none overflow-hidden flex flex-col">
      {/* ------------------------------------------------------------- 3-COLUMN COMPOSER BODY */}
      <div className="flex flex-col lg:flex-row items-stretch">
        {/* ------------------------------------------------ LEFT: OPERATIONS SIDEBAR */}
        <aside className="w-full lg:w-[285px] shrink-0 border-b lg:border-b-0 lg:border-r border-line/60 bg-[#0c101c]/95 p-3.5 flex flex-col gap-3">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <SlidersHorizontal className="w-3.5 h-3.5 text-accent" />
              <span className="text-xs font-bold text-white tracking-wider uppercase font-mono">
                Operations
              </span>
            </div>
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={() => setShowSearch((v) => !v)}
                title="Search operations"
                className="p-1 rounded text-slate-400 hover:text-white hover:bg-hover transition-colors text-xs"
              >
                <Search className="w-3.5 h-3.5" />
              </button>
              <button
                type="button"
                onClick={() => setSearch("")}
                title="Reset search"
                className="p-1 rounded text-slate-400 hover:text-white hover:bg-hover transition-colors text-xs"
              >
                <GridIcon className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Search Field */}
          {showSearch && (
            <input
              type="text"
              value={search}
              placeholder="filter qudit gates..."
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-[#080c16] border border-line rounded px-2.5 py-1 text-xs text-white placeholder-slate-500 font-mono focus:outline-none focus:border-accent"
            />
          )}

          {/* Category Filter Pills */}
          <div className="flex items-center gap-1 overflow-x-auto pb-1 scrollbar-none text-[11px] font-mono">
            {[
              { id: "all", label: "All" },
              { id: "1q", label: "1-Qudit" },
              { id: "2q", label: "2-Qudit" },
              { id: "multi", label: "Multi" },
              { id: "directives", label: "Directives" },
            ].map((cat) => (
              <button
                key={cat.id}
                type="button"
                onClick={() => setCategoryFilter(cat.id)}
                className={cn(
                  "px-2 py-0.5 rounded-full whitespace-nowrap transition-all border text-[10px]",
                  categoryFilter === cat.id
                    ? "bg-accent/20 border-accent text-accent font-semibold shadow-sm"
                    : "bg-[#090d18] border-line/60 text-slate-400 hover:text-white hover:border-line"
                )}
              >
                {cat.label}
              </button>
            ))}
          </div>

          {/* Palette Grid with HTML5 Drag & Drop - Spacious 3-Column Layout */}
          <div className="grid grid-cols-3 gap-2 py-1 max-h-[420px] overflow-y-auto pr-0.5">
            {visiblePalette.map((gate) => {
              const isSelected = selectedPaletteGate === gate.id;
              const wireBadge = gate.numQudits > 1 ? `${gate.numQudits}Q` : "1Q";
              return (
                <div
                  key={gate.id}
                  role="button"
                  tabIndex={0}
                  draggable
                  onDragStart={(e) => {
                    setDraggingGate(gate);
                    try {
                      e.dataTransfer.setData("palette-id", gate.id);
                      e.dataTransfer.setData("text/plain", gate.id);
                      e.dataTransfer.effectAllowed = "copyMove";
                    } catch (_) {}
                  }}
                  onDragEnd={() => {
                    setDraggingGate(null);
                    setDragOverCell(null);
                  }}
                  onClick={() => {
                    setSelectedPaletteGate(gate.id);
                    handlePlaceGateAt(gate.id, 0);
                  }}
                  style={{
                    backgroundColor: gate.bg,
                    color: gate.fg,
                  }}
                  className={cn(
                    "h-[52px] rounded-lg flex flex-col justify-between p-1.5 shadow-md hover:brightness-115 hover:shadow-lg active:scale-95 transition-all relative overflow-hidden cursor-grab active:cursor-grabbing border border-white/10 group",
                    isSelected
                      ? "ring-2 ring-white ring-offset-2 ring-offset-[#0c101c] shadow-cyan-500/30"
                      : "hover:border-white/30"
                  )}
                  title={`${gate.name} (${wireBadge}) — Drag onto circuit wire or click to append`}
                >
                  {/* Subtle top gloss highlight */}
                  <div className="absolute inset-x-0 top-0 h-[40%] bg-gradient-to-b from-white/20 to-transparent pointer-events-none" />

                  {/* Top row: Label & Wire Badge */}
                  <div className="flex items-center justify-between w-full relative z-10">
                    <span className="font-mono font-bold text-[13px] leading-none tracking-tight drop-shadow-sm truncate">
                      {gate.label}
                    </span>
                    <span className="text-[8.5px] font-mono px-1 py-0.2 rounded bg-black/35 text-white/90 font-semibold border border-white/10">
                      {wireBadge}
                    </span>
                  </div>

                  {/* Bottom row: Sublabel */}
                  <div className="flex items-center justify-between w-full relative z-10">
                    <span className="text-[9px] font-medium tracking-wide uppercase opacity-85 truncate">
                      {gate.sublabel || gate.category}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Parameter Box matching Screenshot C */}
          <div className="mt-auto pt-3 border-t border-line/60 space-y-1.5 font-mono text-xs">
            <div className="text-[11px] font-bold text-slate-400 tracking-wider">
              PARAM
            </div>
            <input
              type="text"
              value={paramExpr}
              onChange={(e) => setParamExpr(e.target.value)}
              placeholder="pi/2"
              className="w-full bg-[#080c16] border border-line rounded px-2.5 py-1.5 text-xs text-white font-mono focus:outline-none focus:border-accent"
              title="Parameter expression for P/R_jk/CSX/X/Z. Accepts pi, numbers, + - * / ( )"
            />
            <div className="text-[10px] text-slate-500">
              only <code className="text-slate-400 font-bold">pi</code>, numbers and{" "}
              <code className="text-slate-400">+ - * / ( )</code>
            </div>
          </div>
        </aside>

        {/* ------------------------------------------------ CENTER: WORKSPACE */}
        <section className="flex-1 min-w-0 flex flex-col bg-[#07090e]">
          {/* Top Toolbar matching Screenshot C */}
          <div className="min-h-[44px] flex flex-wrap items-center justify-between gap-3 px-4 py-2 border-b border-line/60 bg-[#090d18]">
            <div className="flex items-center gap-3">
              {/* Undo / Redo */}
              <div className="flex items-center gap-1">
                <button
                  type="button"
                  onClick={handleUndo}
                  disabled={history.length === 0}
                  className="p-1 rounded text-slate-400 hover:text-white disabled:opacity-30 disabled:pointer-events-none transition-colors"
                  title="Undo"
                >
                  <RotateCcw className="w-4 h-4" />
                </button>
                <button
                  type="button"
                  onClick={handleRedo}
                  disabled={future.length === 0}
                  className="p-1 rounded text-slate-400 hover:text-white disabled:opacity-30 disabled:pointer-events-none transition-colors"
                  title="Redo"
                >
                  <RotateCw className="w-4 h-4" />
                </button>
              </div>

              {/* Spacing Selector */}
              <select
                value={alignment}
                onChange={(e) => setAlignment(e.target.value as any)}
                className="bg-transparent border border-line/60 rounded px-2 py-0.5 text-xs text-slate-300 font-sans focus:outline-none"
              >
                <option value="preserve" className="bg-[#0f131f] text-white">Preserve spacing</option>
                <option value="left" className="bg-[#0f131f] text-white">Left alignment</option>
              </select>

              {/* Inspect Toggle Switch */}
              <button
                type="button"
                onClick={() => setInspect((v) => !v)}
                className={cn(
                  "flex items-center gap-2 text-xs font-medium px-2 py-1 rounded transition-colors",
                  inspect ? "text-accent" : "text-slate-400 hover:text-slate-200"
                )}
                title="Toggle Gate Inspection"
              >
                <div
                  className={cn(
                    "w-8 h-4 rounded-full relative transition-colors",
                    inspect ? "bg-accent" : "bg-slate-700"
                  )}
                >
                  <div
                    className={cn(
                      "w-3.5 h-3.5 rounded-full bg-white absolute top-0.5 transition-transform",
                      inspect ? "left-4" : "left-0.5"
                    )}
                  />
                </div>
                <span>Inspect</span>
              </button>
            </div>

            {/* Hide / Show Code Toggle */}
            <button
              type="button"
              onClick={() => setShowCode((v) => !v)}
              className="text-xs text-slate-400 hover:text-white transition-colors"
            >
              {showCode ? "Hide code" : "Show code"}
            </button>
          </div>

          {/* Action Bar matching Screenshot C */}
          <div className="flex flex-wrap items-center gap-2 px-4 py-2 border-b border-line/60 bg-[#0a0f1d] text-xs">
            <button
              type="button"
              onClick={handleAddWire}
              disabled={wires.length >= maxQudits}
              className="px-2.5 py-1 rounded border border-line bg-subtle/50 text-white font-medium hover:bg-hover disabled:opacity-40 transition-colors"
            >
              + Qudit
            </button>
            <button
              type="button"
              onClick={() => handleRemoveWire(wires.length - 1)}
              disabled={wires.length <= 1}
              className="px-2.5 py-1 rounded border border-line bg-subtle/50 text-white font-medium hover:bg-hover disabled:opacity-40 transition-colors"
            >
              − Qudit
            </button>
            <span className="text-slate-400 font-mono text-[11px] px-1">
              {wires.length} {wires.length === 1 ? "qudit" : "qudits"} (d={dimension})
            </span>

            <div className="flex-1" />
            <button
              type="button"
              onClick={() => {
                commitUpdate({ ...circuit, ops: [...ops] });
              }}
              className="px-2.5 py-1 rounded border border-line bg-subtle/40 text-slate-300 hover:text-white hover:bg-hover transition-colors"
            >
              Compact
            </button>
            <button
              type="button"
              onClick={() => {
                handleClear();
                onResetCircuit();
              }}
              className="px-2.5 py-1 rounded border border-rose-500/40 text-rose-300 hover:bg-rose-500/20 transition-colors"
            >
              Clear
            </button>
          </div>

          {/* Circuit Canvas Grid with Horizontal Tracks & HTML5 Drop Targets */}
          <div className="p-4 overflow-x-auto flex-1">
            <div className="inline-block min-w-full">
              {/* Column Indices */}
              <div className="flex items-center gap-2 mb-2 select-none">
                <div className="w-20 shrink-0" />
                <div className="flex items-center gap-4 text-[11px] font-mono text-slate-500">
                  {Array.from({ length: nCols }).map((_, c) => (
                    <div key={c} className="w-12 text-center">
                      {c}
                    </div>
                  ))}
                </div>
              </div>

              {/* Wire Tracks */}
              <div className="space-y-4 relative">
                {/* SVG Continuous Vertical Connector Lines Layer */}
                <svg
                  className="absolute inset-0 pointer-events-none z-0"
                  style={{ width: "100%", height: "100%", overflow: "visible" }}
                >
                  {multiQuditConnectors.map(({ col, vMin, vMax, isSelected }) => {
                    const x = 112 + col * 64;
                    const y1 = vMin * 64 + 24;
                    const y2 = vMax * 64 + 24;
                    return (
                      <g key={`connector-${col}`}>
                        {isSelected && (
                          <line
                            x1={x}
                            y1={y1}
                            x2={x}
                            y2={y2}
                            stroke="#38bdf8"
                            strokeWidth={5}
                            strokeLinecap="round"
                            opacity={0.4}
                          />
                        )}
                        <line
                          x1={x}
                          y1={y1}
                          x2={x}
                          y2={y2}
                          stroke={isSelected ? "#38bdf8" : "#22d3ee"}
                          strokeWidth={2.5}
                          strokeLinecap="round"
                        />
                      </g>
                    );
                  })}
                </svg>

                {wires.map((wire) => {
                  const wireIdx = wire.index;
                  const isWireEmpty = !ops.some(
                    (o) => o.targets.includes(wireIdx) || o.controls.includes(wireIdx)
                  );

                  return (
                    <div key={wire.id} className="flex items-center gap-2 relative h-12">
                      {/* Wire Label & Initial State */}
                      <div className="w-20 shrink-0 flex items-center justify-between pr-2">
                        <span className="font-mono text-xs font-semibold text-slate-300">
                          q[{wireIdx}]
                        </span>
                        <button
                          type="button"
                          onClick={() => handleCycleInitialState(wireIdx)}
                          title={`Click to cycle initial state |0⟩..|${dimension - 1}⟩`}
                          className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-subtle/80 text-accent font-bold border border-line hover:border-accent"
                        >
                          |{wire.initial_state}⟩
                        </button>
                      </div>

                      {/* Wire Canvas with Track Line */}
                      <div className="relative flex items-center gap-4 flex-1">
                        {/* Horizontal track line */}
                        <div className="absolute inset-x-0 h-[2px] bg-[#6366f1]/40 top-1/2 -translate-y-1/2 pointer-events-none" />

                        {/* Column Cells with Drag & Drop */}
                        {Array.from({ length: nCols }).map((_, col) => {
                          const op = ops[col];
                          const isTarget = op?.targets.includes(wireIdx);
                          const isControl = op?.controls.includes(wireIdx);
                          const isSelected = op && selectedOpId === op.id;
                          const isDragOver =
                            dragOverCell?.wire === wireIdx && dragOverCell?.col === col;

                          return (
                            <div
                              key={col}
                              onDragOver={(e) => {
                                e.preventDefault();
                                e.dataTransfer.dropEffect = "copy";
                                if (
                                  dragOverCell?.wire !== wireIdx ||
                                  dragOverCell?.col !== col
                                ) {
                                  setDragOverCell({ wire: wireIdx, col });
                                }
                              }}
                              onDragLeave={() => {
                                if (
                                  dragOverCell?.wire === wireIdx &&
                                  dragOverCell?.col === col
                                ) {
                                  setDragOverCell(null);
                                }
                              }}
                              onDrop={(e) => {
                                e.preventDefault();
                                setDragOverCell(null);
                                const gid =
                                  e.dataTransfer.getData("palette-id") ||
                                  e.dataTransfer.getData("text/plain") ||
                                  draggingGate?.id;
                                if (gid) {
                                  handlePlaceGateAt(gid, wireIdx, col);
                                }
                              }}
                              onClick={() => {
                                if (op) {
                                  setSelectedOpId(op.id);
                                } else {
                                  handlePlaceGateAt(selectedPaletteGate, wireIdx, col);
                                }
                              }}
                              className={cn(
                                "w-12 h-12 rounded relative z-10 flex items-center justify-center cursor-pointer transition-all",
                                !op &&
                                  "hover:bg-accent/10 border border-transparent hover:border-accent/40",
                                isDragOver &&
                                  "ring-2 ring-accent bg-accent/25 border border-accent animate-pulse"
                              )}
                            >
                              {/* 1. Target Gate Rendering */}
                              {isTarget && (() => {
                                const visual = getGateVisual(op);
                                return (
                                  <div
                                    style={{ backgroundColor: visual.bg, color: visual.fg }}
                                    className={cn(
                                      "w-10 h-10 flex flex-col items-center justify-center font-bold shadow-md border border-white/20 relative transition-transform select-none z-10",
                                      visual.isRound ? "rounded-full" : "rounded-md",
                                      isSelected && "ring-2 ring-white scale-105 z-30"
                                    )}
                                  >
                                    <span
                                      className={cn(
                                        "font-mono leading-tight",
                                        visual.symbol.length <= 2
                                          ? "text-[13px]"
                                          : visual.symbol.length <= 4
                                          ? "text-[11px]"
                                          : "text-[9.5px] tracking-tight"
                                      )}
                                    >
                                      {visual.symbol}
                                    </span>
                                    {visual.showDim && (
                                      <span className="text-[7.5px] font-mono leading-none opacity-80">
                                        d={op.dimension}
                                      </span>
                                    )}
                                    {/* Delete on click when selected */}
                                    {isSelected && (
                                      <button
                                        type="button"
                                        onClick={(e) => {
                                          e.stopPropagation();
                                          handleDeleteOp(op.id);
                                        }}
                                        className="absolute -top-1.5 -right-1.5 w-4 h-4 rounded-full bg-rose-600 text-white flex items-center justify-center text-[10px] hover:bg-rose-500 shadow z-40"
                                        title="Delete operation"
                                      >
                                        ✕
                                      </button>
                                    )}
                                  </div>
                                );
                              })()}

                              {/* 2. Control Dot Rendering */}
                              {isControl && (
                                <div className="relative flex items-center justify-center z-20">
                                  <div className="w-4 h-4 rounded-full bg-cyan-400 border-2 border-[#07090e] shadow-md flex items-center justify-center" />
                                  {op.params.c !== undefined && (
                                    <span className="absolute -top-3 text-[9px] font-mono text-cyan-300 font-bold bg-[#07090e]/90 px-1 rounded shadow">
                                      c={op.params.c}
                                    </span>
                                  )}
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>

                      {/* Wire End Control: Minus circle at end of wire */}
                      <button
                        type="button"
                        onClick={() => handleRemoveWire(wireIdx)}
                        disabled={!isWireEmpty || wires.length <= 1}
                        title={
                          isWireEmpty
                            ? "Remove empty wire"
                            : "Wire has placed gates — remove gates first"
                        }
                        className={cn(
                          "w-6 h-6 rounded-full border border-slate-700 flex items-center justify-center text-slate-500 font-bold transition-all",
                          isWireEmpty && wires.length > 1
                            ? "hover:border-rose-500 hover:text-rose-400 cursor-pointer"
                            : "opacity-30 cursor-not-allowed"
                        )}
                      >
                        ⊖
                      </button>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Instruction Text matching Screenshot C */}
            <div className="mt-6 text-xs text-slate-500 leading-relaxed max-w-2xl font-sans">
              Drag a gate onto the grid (or click it, then click a cell). Dropping onto an occupied column inserts a new column globally, shifting everything to the right. Click a block to inspect and customize its control, target, and parameter values. The ⊖ at the end of a wire removes it once it is empty.
            </div>

            {/* ------------------------------------------------------------- GATE INSPECT & EDIT CONTROLS */}
            {inspect && (
              <div className="mt-4 p-4 rounded-xl bg-[#0c101c] border border-line/60 max-w-2xl shadow-lg">
                {selectedOp ? (
                  <div className="space-y-4 text-xs font-mono">
                    {/* Header */}
                    <div className="flex items-center justify-between pb-2 border-b border-line/50">
                      <div className="flex items-center gap-2">
                        <Sliders className="w-4 h-4 text-accent" />
                        <span className="font-bold text-white text-sm">
                          {selectedOp.gate.toUpperCase()}_{selectedOp.dimension} Gate Properties
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => handleDuplicateOp(selectedOp.id)}
                          className="px-2 py-1 rounded border border-line/60 bg-subtle/50 text-slate-300 hover:text-white flex items-center gap-1.5 transition-colors"
                        >
                          <Copy className="w-3.5 h-3.5" /> Duplicate
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDeleteOp(selectedOp.id)}
                          className="px-2 py-1 rounded border border-rose-500/40 bg-rose-500/10 text-rose-300 hover:bg-rose-500/20 flex items-center gap-1.5 transition-colors"
                        >
                          <Trash2 className="w-3.5 h-3.5" /> Delete
                        </button>
                      </div>
                    </div>

                    {/* Interactive Wires & Roles Assignment */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 bg-[#080c16] p-3 rounded-lg border border-line/40">
                      {/* SWAP Gate Wires */}
                      {selectedOp.gate === "swap" ? (
                        <>
                          <div className="flex flex-col gap-1.5">
                            <label className="text-slate-400 font-semibold text-[11px]">
                              First Qudit Wire:
                            </label>
                            <select
                              value={selectedOp.targets[0] ?? 0}
                              onChange={(e) => {
                                const newW0 = Number(e.target.value);
                                handleUpdateSelectedOp((op) => ({
                                  ...op,
                                  targets: [newW0, op.targets[1] === newW0 ? (newW0 === 0 ? 1 : 0) : op.targets[1]],
                                }));
                              }}
                              className="bg-[#0f1424] border border-line rounded px-2 py-1 text-white font-mono text-xs focus:border-accent outline-none"
                            >
                              {wires.map((w) => (
                                <option key={w.index} value={w.index}>
                                  q[{w.index}] {w.label ? `(${w.label})` : ""}
                                </option>
                              ))}
                            </select>
                          </div>

                          <div className="flex flex-col gap-1.5">
                            <label className="text-slate-400 font-semibold text-[11px]">
                              Second Qudit Wire:
                            </label>
                            <select
                              value={selectedOp.targets[1] ?? (wires.length > 1 ? 1 : 0)}
                              onChange={(e) => {
                                const newW1 = Number(e.target.value);
                                handleUpdateSelectedOp((op) => ({
                                  ...op,
                                  targets: [op.targets[0] === newW1 ? (newW1 === 0 ? 1 : 0) : op.targets[0], newW1],
                                }));
                              }}
                              className="bg-[#0f1424] border border-line rounded px-2 py-1 text-white font-mono text-xs focus:border-accent outline-none"
                            >
                              {wires.map((w) => (
                                <option key={w.index} value={w.index}>
                                  q[{w.index}] {w.label ? `(${w.label})` : ""}
                                </option>
                              ))}
                            </select>
                          </div>

                          <div className="sm:col-span-2">
                            <button
                              type="button"
                              onClick={handleFlipSwapTargets}
                              className="px-2.5 py-1 rounded border border-line bg-subtle text-accent text-xs flex items-center gap-1.5 hover:bg-hover transition-colors"
                            >
                              <ArrowRightLeft className="w-3.5 h-3.5" /> Flip Swap Target Order
                            </button>
                          </div>
                        </>
                      ) : (
                        <>
                          {/* Controlled Gates: Control Wire */}
                          {selectedOp.controls.length > 0 && (
                            <div className="flex flex-col gap-1.5">
                              <label className="text-slate-400 font-semibold text-[11px] flex items-center gap-1">
                                <span className="w-2 h-2 rounded-full bg-cyan-400 inline-block" />
                                Control Qudit:
                              </label>
                              <select
                                value={selectedOp.controls[0] ?? 0}
                                onChange={(e) => {
                                  const newC = Number(e.target.value);
                                  handleUpdateSelectedOp((op) => ({
                                    ...op,
                                    controls: [newC],
                                    targets: op.targets[0] === newC ? [newC === 0 ? (wires.length > 1 ? 1 : 0) : 0] : op.targets,
                                  }));
                                }}
                                className="bg-[#0f1424] border border-line rounded px-2 py-1 text-white font-mono text-xs focus:border-accent outline-none"
                              >
                                {wires.map((w) => (
                                  <option key={w.index} value={w.index}>
                                    q[{w.index}] {w.label ? `(${w.label})` : ""}
                                  </option>
                                ))}
                              </select>
                            </div>
                          )}

                          {/* Target Wire */}
                          <div className="flex flex-col gap-1.5">
                            <label className="text-slate-400 font-semibold text-[11px] flex items-center gap-1">
                              <span className="w-2 h-2 rounded bg-accent inline-block" />
                              Target Qudit:
                            </label>
                            <select
                              value={selectedOp.targets[0] ?? 0}
                              onChange={(e) => {
                                const newT = Number(e.target.value);
                                handleUpdateSelectedOp((op) => ({
                                  ...op,
                                  targets: [newT],
                                  controls: op.controls[0] === newT ? [newT === 0 ? (wires.length > 1 ? 1 : 0) : 0] : op.controls,
                                }));
                              }}
                              className="bg-[#0f1424] border border-line rounded px-2 py-1 text-white font-mono text-xs focus:border-accent outline-none"
                            >
                              {wires.map((w) => (
                                <option key={w.index} value={w.index}>
                                  q[{w.index}] {w.label ? `(${w.label})` : ""}
                                </option>
                              ))}
                            </select>
                          </div>

                          {/* Invert Roles Button for 2-Qudit Controlled Gates */}
                          {selectedOp.controls.length === 1 && selectedOp.targets.length === 1 && (
                            <div className="sm:col-span-2 pt-1">
                              <button
                                type="button"
                                onClick={handleInvertControlTarget}
                                className="px-2.5 py-1 rounded border border-line bg-subtle text-accent text-xs flex items-center gap-1.5 hover:bg-hover transition-colors"
                              >
                                <ArrowRightLeft className="w-3.5 h-3.5" /> Invert Control ↔ Target Roles
                              </button>
                            </div>
                          )}
                        </>
                      )}
                    </div>

                    {/* Parameters Configuration */}
                    <div className="space-y-3 bg-[#080c16] p-3 rounded-lg border border-line/40">
                      <span className="text-slate-400 font-semibold text-[11px] block">
                        Gate Parameters:
                      </span>

                      {/* Control Level 'c' for CSX, SCP, CU, CSWAP */}
                      {(selectedOp.params.c !== undefined || selectedOp.gate === "csx" || selectedOp.gate === "scp") && (
                        <div className="flex items-center gap-3">
                          <span className="text-slate-300 w-32">Activating Level c:</span>
                          <div className="flex gap-1.5">
                            {Array.from({ length: dimension }).map((_, lvl) => (
                              <button
                                key={lvl}
                                type="button"
                                onClick={() =>
                                  handleUpdateSelectedOp((op) => ({
                                    ...op,
                                    params: { ...op.params, c: lvl },
                                  }))
                                }
                                className={cn(
                                  "w-7 h-7 rounded font-mono text-xs font-bold border transition-colors",
                                  (selectedOp.params.c ?? 1) === lvl
                                    ? "bg-accent text-accent-ink border-accent shadow"
                                    : "bg-subtle text-slate-300 border-line hover:border-slate-400"
                                )}
                              >
                                {lvl}
                              </button>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Power 'a' for X^a, Z^b, CSX */}
                      {(selectedOp.gate === "x" || selectedOp.gate === "z" || selectedOp.gate === "csx") && (
                        <div className="flex items-center gap-3">
                          <span className="text-slate-300 w-32">Shift Power a:</span>
                          <div className="flex gap-1.5">
                            {Array.from({ length: dimension - 1 }).map((_, idx) => {
                              const pow = idx + 1;
                              const curPow = selectedOp.params.power ?? selectedOp.params.a ?? 1;
                              return (
                                <button
                                  key={pow}
                                  type="button"
                                  onClick={() =>
                                    handleUpdateSelectedOp((op) => ({
                                      ...op,
                                      params: {
                                        ...op.params,
                                        power: pow,
                                        a: pow,
                                      },
                                    }))
                                  }
                                  className={cn(
                                    "w-7 h-7 rounded font-mono text-xs font-bold border transition-colors",
                                    curPow === pow
                                      ? "bg-accent text-accent-ink border-accent shadow"
                                      : "bg-subtle text-slate-300 border-line hover:border-slate-400"
                                  )}
                                >
                                  {pow}
                                </button>
                              );
                            })}
                          </div>
                        </div>
                      )}

                      {/* Angle θ for P_j, R_jk, SCP, MCP */}
                      {(selectedOp.gate === "p_j" ||
                        selectedOp.gate === "r_jk" ||
                        selectedOp.gate === "scp" ||
                        selectedOp.gate === "mcp") && (
                        <div className="flex flex-col gap-2">
                          <div className="flex items-center gap-3">
                            <span className="text-slate-300 w-32">Phase Angle θ:</span>
                            <input
                              type="text"
                              value={
                                selectedOp.params.theta !== undefined
                                  ? String(selectedOp.params.theta)
                                  : "1.570796"
                              }
                              onChange={(e) => {
                                const val = parseParamExpr(e.target.value);
                                handleUpdateSelectedOp((op) => ({
                                  ...op,
                                  params: { ...op.params, theta: val },
                                }));
                              }}
                              className="bg-[#0f1424] border border-line rounded px-2.5 py-1 text-white font-mono text-xs w-36 focus:border-accent outline-none"
                            />
                          </div>
                          {/* Quick Angle Chips */}
                          <div className="flex items-center gap-1.5 pl-32 text-[10px]">
                            <span className="text-slate-500">Presets:</span>
                            {[
                              { label: "π/4", val: Math.PI / 4 },
                              { label: "π/2", val: Math.PI / 2 },
                              { label: "π", val: Math.PI },
                              { label: "2π/3", val: (2 * Math.PI) / 3 },
                            ].map((preset) => (
                              <button
                                key={preset.label}
                                type="button"
                                onClick={() =>
                                  handleUpdateSelectedOp((op) => ({
                                    ...op,
                                    params: { ...op.params, theta: preset.val },
                                  }))
                                }
                                className="px-1.5 py-0.5 rounded bg-subtle border border-line hover:border-accent text-slate-300 hover:text-white"
                              >
                                {preset.label}
                              </button>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Level selection for P_j and R_jk */}
                      {selectedOp.gate === "p_j" && (
                        <div className="flex items-center gap-3">
                          <span className="text-slate-300 w-32">Target Level j:</span>
                          <div className="flex gap-1.5">
                            {Array.from({ length: dimension }).map((_, lvl) => (
                              <button
                                key={lvl}
                                type="button"
                                onClick={() =>
                                  handleUpdateSelectedOp((op) => ({
                                    ...op,
                                    params: { ...op.params, j: lvl },
                                  }))
                                }
                                className={cn(
                                  "w-7 h-7 rounded font-mono text-xs font-bold border transition-colors",
                                  (selectedOp.params.j ?? 1) === lvl
                                    ? "bg-accent text-accent-ink border-accent shadow"
                                    : "bg-subtle text-slate-300 border-line hover:border-slate-400"
                                )}
                              >
                                |{lvl}⟩
                              </button>
                            ))}
                          </div>
                        </div>
                      )}

                      {selectedOp.gate === "r_jk" && (
                        <div className="grid grid-cols-2 gap-3">
                          <div className="flex flex-col gap-1">
                            <span className="text-slate-300">Level j:</span>
                            <select
                              value={selectedOp.params.j ?? 0}
                              onChange={(e) => {
                                const newJ = Number(e.target.value);
                                handleUpdateSelectedOp((op) => ({
                                  ...op,
                                  params: {
                                    ...op.params,
                                    j: newJ,
                                    k: op.params.k === newJ ? (newJ === 0 ? 1 : 0) : op.params.k,
                                  },
                                }));
                              }}
                              className="bg-[#0f1424] border border-line rounded px-2 py-1 text-white font-mono text-xs"
                            >
                              {Array.from({ length: dimension }).map((_, lvl) => (
                                <option key={lvl} value={lvl}>
                                  |{lvl}⟩
                                </option>
                              ))}
                            </select>
                          </div>
                          <div className="flex flex-col gap-1">
                            <span className="text-slate-300">Level k:</span>
                            <select
                              value={selectedOp.params.k ?? 1}
                              onChange={(e) => {
                                const newK = Number(e.target.value);
                                handleUpdateSelectedOp((op) => ({
                                  ...op,
                                  params: {
                                    ...op.params,
                                    k: newK,
                                    j: op.params.j === newK ? (newK === 0 ? 1 : 0) : op.params.j,
                                  },
                                }));
                              }}
                              className="bg-[#0f1424] border border-line rounded px-2 py-1 text-white font-mono text-xs"
                            >
                              {Array.from({ length: dimension }).map((_, lvl) => (
                                <option key={lvl} value={lvl}>
                                  |{lvl}⟩
                                </option>
                              ))}
                            </select>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="text-xs text-slate-500 font-mono text-center py-2">
                    Inspect is ON — click any placed gate to adjust controls, targets, angles, and levels.
                  </div>
                )}
              </div>
            )}
          </div>
        </section>

        {/* ------------------------------------------------ RIGHT: CIRCUIT OPS PANEL */}
        {showCode && (
          <aside className="w-full lg:w-[230px] shrink-0 border-t lg:border-t-0 lg:border-l border-line/60 bg-[#07090e] flex flex-col font-mono text-xs">
            {/* Header */}
            <div className="flex items-center justify-between px-3 py-2.5 border-b border-line/60 text-slate-400">
              <span className="font-semibold text-slate-300">Circuit</span>
              <span className="text-[11px] text-slate-500">{ops.length} ops</span>
            </div>

            {/* Ops Lines */}
            <div className="flex-1 p-2 space-y-1 overflow-y-auto max-h-[320px] lg:max-h-none">
              {ops.length === 0 ? (
                <div className="text-slate-600 text-xs py-2 px-1">empty circuit</div>
              ) : (
                ops.map((op, i) => (
                  <div
                    key={op.id}
                    onClick={() => setSelectedOpId(op.id)}
                    className={cn(
                      "flex items-center gap-2 px-2 py-1 rounded cursor-pointer transition-colors leading-tight",
                      selectedOpId === op.id
                        ? "bg-accent/20 text-white font-bold"
                        : "text-slate-300 hover:bg-hover"
                    )}
                  >
                    <span className="text-slate-500 w-4 text-right select-none">{i + 1}</span>
                    <span className="truncate">{describeOp(op)}</span>
                  </div>
                ))
              )}
            </div>
          </aside>
        )}
      </div>
    </div>
  );
};
