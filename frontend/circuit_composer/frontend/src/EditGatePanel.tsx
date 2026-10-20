import React, { useState } from "react";
import type { Op, Param } from "./types";
import { makeParam } from "./ir";
import { gateColour, gateForeground } from "./theme";

interface EditGatePanelProps {
  op: Op;
  nQubits: number;
  onUpdateOp: (updated: Op) => void;
  onClose: () => void;
  onAddQubit?: () => number;
  onDuplicate?: () => void;
  onDelete?: () => void;
}

interface GateSpec {
  name: string;
  matrix: string[][];
  matrixPrefix?: string;
  dirac: string[];
  properties: string[];
  desc: string;
}

const GATE_SPECS: Record<string, GateSpec> = {
  Y: {
    name: "Pauli-Y",
    matrix: [
      ["0", "-i"],
      ["i", "0"],
    ],
    dirac: ["|0⟩ →  i |1⟩", "|1⟩ → -i |0⟩"],
    properties: ["Clifford", "Hermitian", "Self-Inverse (Y²=I)", "Pauli-Y"],
    desc: "Bit and phase flip gate. Equivalent to a π rotation about the Y axis on the Bloch sphere.",
  },
  X: {
    name: "Pauli-X (NOT)",
    matrix: [
      ["0", "1"],
      ["1", "0"],
    ],
    dirac: ["|0⟩ → |1⟩", "|1⟩ → |0⟩"],
    properties: ["Clifford", "Hermitian", "Self-Inverse (X²=I)", "NOT Gate"],
    desc: "Quantum NOT / bit-flip gate. Inverts the computational basis state |0⟩ ↔ |1⟩.",
  },
  Z: {
    name: "Pauli-Z",
    matrix: [
      ["1", "0"],
      ["0", "-1"],
    ],
    dirac: ["|0⟩ → |0⟩", "|1⟩ → -|1⟩"],
    properties: ["Clifford", "Hermitian", "Self-Inverse (Z²=I)", "Phase-Flip"],
    desc: "Phase-flip gate. Imparts a π phase shift on |1⟩ while leaving |0⟩ unchanged.",
  },
  H: {
    name: "Hadamard (H)",
    matrixPrefix: "1/√2",
    matrix: [
      ["1", "1"],
      ["1", "-1"],
    ],
    dirac: ["|0⟩ → (|0⟩ + |1⟩)/√2  (|+⟩)", "|1⟩ → (|0⟩ - |1⟩)/√2  (|-⟩)"],
    properties: ["Clifford", "Hermitian", "Self-Inverse (H²=I)", "Superposition"],
    desc: "Creates equal superposition from computational basis states; maps between X and Z bases.",
  },
  S: {
    name: "Phase Gate (S / √Z)",
    matrix: [
      ["1", "0"],
      ["0", "i"],
    ],
    dirac: ["|0⟩ → |0⟩", "|1⟩ → i |1⟩"],
    properties: ["Clifford", "Phase (π/2)", "S² = Z", "Unitary"],
    desc: "Single-qubit π/2 phase gate around the Z axis. The square root of Pauli-Z.",
  },
  SDG: {
    name: "S-Dagger (S†)",
    matrix: [
      ["1", "0"],
      ["0", "-i"],
    ],
    dirac: ["|0⟩ → |0⟩", "|1⟩ → -i |1⟩"],
    properties: ["Clifford", "Phase (-π/2)", "S†S = I", "Adjoint"],
    desc: "Adjoint / conjugate transpose of S gate. Applies a -π/2 rotation around the Z axis.",
  },
  T: {
    name: "T Gate (π/8 / ⁴√Z)",
    matrix: [
      ["1", "0"],
      ["0", "e^(iπ/4)"],
    ],
    dirac: ["|0⟩ → |0⟩", "|1⟩ → e^(iπ/4) |1⟩"],
    properties: ["Non-Clifford", "Phase (π/4)", "T⁴ = Z", "Universal"],
    desc: "Fourth root of Z gate. Crucial non-Clifford resource for universal quantum computation.",
  },
  TDG: {
    name: "T-Dagger (T†)",
    matrix: [
      ["1", "0"],
      ["0", "e^(-iπ/4)"],
    ],
    dirac: ["|0⟩ → |0⟩", "|1⟩ → e^(-iπ/4) |1⟩"],
    properties: ["Non-Clifford", "Phase (-π/4)", "T†T = I", "Adjoint"],
    desc: "Adjoint of the T gate. Rotates state by -π/4 around the Z axis.",
  },
  SX: {
    name: "Square Root of X (√X)",
    matrixPrefix: "½",
    matrix: [
      ["1+i", "1-i"],
      ["1-i", "1+i"],
    ],
    dirac: ["|0⟩ → [(1+i)|0⟩ + (1-i)|1⟩]/2", "|1⟩ → [(1-i)|0⟩ + (1+i)|1⟩]/2"],
    properties: ["Clifford", "√X Gate", "(SX)² = X", "Native Gate"],
    desc: "Square root of X gate. Often the native single-qubit microwave drive pulse on transmon QPUs.",
  },
  SXDG: {
    name: "SX-Dagger (SX†)",
    matrixPrefix: "½",
    matrix: [
      ["1-i", "1+i"],
      ["1+i", "1-i"],
    ],
    dirac: ["|0⟩ → [(1-i)|0⟩ + (1+i)|1⟩]/2", "|1⟩ → [(1+i)|0⟩ + (1-i)|1⟩]/2"],
    properties: ["Clifford", "Adjoint √X", "SX†SX = I"],
    desc: "Adjoint of square root of X gate.",
  },
  RX: {
    name: "Rotation X (Rx)",
    matrix: [
      ["cos(θ/2)", "-i·sin(θ/2)"],
      ["-i·sin(θ/2)", "cos(θ/2)"],
    ],
    dirac: ["|ψ⟩ → exp(-i θ X / 2) |ψ⟩"],
    properties: ["Parametric", "Continuous", "X-Axis Rotation"],
    desc: "Continuous arbitrary rotation of angle θ around the Bloch sphere X axis.",
  },
  RY: {
    name: "Rotation Y (Ry)",
    matrix: [
      ["cos(θ/2)", "-sin(θ/2)"],
      ["sin(θ/2)", "cos(θ/2)"],
    ],
    dirac: ["|ψ⟩ → exp(-i θ Y / 2) |ψ⟩"],
    properties: ["Parametric", "Continuous", "Real Matrix", "Y-Axis Rotation"],
    desc: "Continuous arbitrary rotation of angle θ around the Bloch sphere Y axis.",
  },
  RZ: {
    name: "Rotation Z (Rz)",
    matrix: [
      ["e^(-iθ/2)", "0"],
      ["0", "e^(iθ/2)"],
    ],
    dirac: ["|0⟩ → e^(-iθ/2)|0⟩", "|1⟩ → e^(iθ/2)|1⟩"],
    properties: ["Parametric", "Virtual Z", "Diagonal", "Z-Axis Rotation"],
    desc: "Continuous rotation of angle θ around the Bloch sphere Z axis (zero-duration frame change on IBM hardware).",
  },
  P: {
    name: "Phase Shift (P)",
    matrix: [
      ["1", "0"],
      ["0", "e^(iλ)"],
    ],
    dirac: ["|0⟩ → |0⟩", "|1⟩ → e^(iλ) |1⟩"],
    properties: ["Parametric", "Phase Shift", "Diagonal"],
    desc: "Arbitrary phase gate applying a relative phase angle λ to state |1⟩.",
  },
  CX: {
    name: "Controlled-NOT (CX / CNOT)",
    matrix: [
      ["1", "0", "0", "0"],
      ["0", "1", "0", "0"],
      ["0", "0", "0", "1"],
      ["0", "0", "1", "0"],
    ],
    dirac: ["|00⟩ → |00⟩", "|01⟩ → |01⟩", "|10⟩ → |11⟩", "|11⟩ → |10⟩"],
    properties: ["Clifford", "Hermitian", "Entangling", "2-Qubit"],
    desc: "Controlled-NOT gate. Flips target qubit if and only if the control qubit is in state |1⟩.",
  },
  CY: {
    name: "Controlled-Y (CY)",
    matrix: [
      ["1", "0", "0", "0"],
      ["0", "1", "0", "0"],
      ["0", "0", "0", "-i"],
      ["0", "0", "i", "0"],
    ],
    dirac: ["|10⟩ →  i |11⟩", "|11⟩ → -i |10⟩"],
    properties: ["Clifford", "Hermitian", "Entangling", "2-Qubit"],
    desc: "Controlled-Y gate. Applies Pauli-Y to the target qubit when the control is |1⟩.",
  },
  CZ: {
    name: "Controlled-Z (CZ)",
    matrix: [
      ["1", "0", "0", "0"],
      ["0", "1", "0", "0"],
      ["0", "0", "1", "0"],
      ["0", "0", "0", "-1"],
    ],
    dirac: ["|11⟩ → -|11⟩", "Symmetric: control ↔ target interchangeable"],
    properties: ["Clifford", "Hermitian", "Entangling", "Symmetric"],
    desc: "Controlled-Z gate. Imparts a phase of -1 if both qubits are in state |1⟩.",
  },
  CH: {
    name: "Controlled-Hadamard (CH)",
    matrixPrefix: "CH",
    matrix: [
      ["1", "0", "0", "0"],
      ["0", "1", "0", "0"],
      ["0", "0", "1/√2", "1/√2"],
      ["0", "0", "1/√2", "-1/√2"],
    ],
    dirac: ["|10⟩ → |1+⟩", "|11⟩ → |1-⟩"],
    properties: ["Entangling", "2-Qubit", "Unitary"],
    desc: "Controlled-Hadamard gate. Applies Hadamard to target qubit if control is |1⟩.",
  },
  SWAP: {
    name: "SWAP Gate",
    matrix: [
      ["1", "0", "0", "0"],
      ["0", "0", "1", "0"],
      ["0", "1", "0", "0"],
      ["0", "0", "0", "1"],
    ],
    dirac: ["|ab⟩ → |ba⟩", "|01⟩ ↔ |10⟩"],
    properties: ["Clifford", "Hermitian", "Self-Inverse", "2-Qubit"],
    desc: "Swaps the quantum state of two qubits. Can be decomposed into 3 alternating CNOT gates.",
  },
  CCX: {
    name: "Toffoli Gate (CCX)",
    matrix: [
      ["1", "0", "0", "0", "0", "0", "0", "0"],
      ["0", "1", "0", "0", "0", "0", "0", "0"],
      ["0", "0", "1", "0", "0", "0", "0", "0"],
      ["0", "0", "0", "1", "0", "0", "0", "0"],
      ["0", "0", "0", "0", "1", "0", "0", "0"],
      ["0", "0", "0", "0", "0", "1", "0", "0"],
      ["0", "0", "0", "0", "0", "0", "0", "1"],
      ["0", "0", "0", "0", "0", "0", "1", "0"],
    ],
    dirac: ["|110⟩ → |111⟩", "|111⟩ → |110⟩"],
    properties: ["Universal Classical", "Reversible Logic", "3-Qubit"],
    desc: "Toffoli gate (Controlled-Controlled-NOT). Flips the third qubit if both controls are |1⟩.",
  },
  MEASURE: {
    name: "Measurement",
    matrix: [
      ["1", "0"],
      ["0", "0"],
    ],
    dirac: ["|ψ⟩ = α|0⟩ + β|1⟩", "P(0) = |α|², P(1) = |β|²"],
    properties: ["Projective", "Non-Unitary", "POVM / Readout"],
    desc: "Collapses quantum superposition into classical bit register 0 or 1 according to the Born rule.",
  },
  RESET: {
    name: "State Reset (|0⟩)",
    matrix: [
      ["1", "0"],
      ["0", "0"],
    ],
    dirac: ["|ψ⟩ → |0⟩  (Unconditional)"],
    properties: ["Non-Unitary", "State Initialization", "Active Reset"],
    desc: "Forces a qubit into ground state |0⟩ regardless of its prior quantum state.",
  },
  BARRIER: {
    name: "Circuit Barrier",
    matrix: [
      ["1", "0"],
      ["0", "1"],
    ],
    dirac: ["Identity operation with compiler fence"],
    properties: ["Compiler Directive", "Prevents Optimization", "Visual Marker"],
    desc: "Compiler fence preventing transpile optimization passes from reordering or merging gates across the barrier.",
  },
};

export const EditGatePanel: React.FC<EditGatePanelProps> = ({
  op,
  nQubits,
  onUpdateOp,
  onClose,
  onAddQubit,
  onDuplicate,
  onDelete,
}) => {
  const [showAddMenu, setShowAddMenu] = useState(false);
  const allWires = Array.from({ length: nQubits }, (_: unknown, i: number) => i);
  const rawGateName = (op.gate ?? op.kind ?? "").toUpperCase();
  const gateName = rawGateName;

  const controls = op.controls || [];
  const negControls = op.neg_controls || [];

  // Change target wire (Connections)
  const handleTargetChange = (targetIdx: number, newWire: number) => {
    const nextQubits = [...op.qubits];
    const oldWire = nextQubits[targetIdx];

    const existingTargetIdx = nextQubits.indexOf(newWire);
    const existingCtrlIdx = controls.indexOf(newWire);
    const existingNegCtrlIdx = negControls.indexOf(newWire);

    let nextControls = [...controls];
    let nextNegControls = [...negControls];

    if (existingTargetIdx !== -1 && existingTargetIdx !== targetIdx) {
      nextQubits[existingTargetIdx] = oldWire;
    } else if (existingCtrlIdx !== -1) {
      nextControls[existingCtrlIdx] = oldWire;
    } else if (existingNegCtrlIdx !== -1) {
      nextNegControls[existingNegCtrlIdx] = oldWire;
    }
    nextQubits[targetIdx] = newWire;

    onUpdateOp({ ...op, qubits: nextQubits, controls: nextControls, neg_controls: nextNegControls });
  };

  // Change wire of a control (positive or negative)
  const handleControlWireChange = (oldWire: number, isNeg: boolean, newWire: number) => {
    let nextQubits = [...op.qubits];
    let nextControls = [...controls];
    let nextNegControls = [...negControls];

    const existingTargetIdx = nextQubits.indexOf(newWire);
    const existingCtrlIdx = nextControls.indexOf(newWire);
    const existingNegCtrlIdx = nextNegControls.indexOf(newWire);

    if (existingTargetIdx !== -1) {
      nextQubits[existingTargetIdx] = oldWire;
    } else if (existingCtrlIdx !== -1) {
      nextControls[existingCtrlIdx] = oldWire;
    } else if (existingNegCtrlIdx !== -1) {
      nextNegControls[existingNegCtrlIdx] = oldWire;
    }

    if (isNeg) {
      const idx = nextNegControls.indexOf(oldWire);
      if (idx !== -1) nextNegControls[idx] = newWire;
    } else {
      const idx = nextControls.indexOf(oldWire);
      if (idx !== -1) nextControls[idx] = newWire;
    }

    onUpdateOp({ ...op, qubits: nextQubits, controls: nextControls, neg_controls: nextNegControls });
  };

  // Toggle polarity of a control (from positive to negative or vice versa)
  const handleToggleControlPolarity = (wire: number, currentlyNeg: boolean) => {
    let nextControls = [...controls];
    let nextNegControls = [...negControls];

    if (currentlyNeg) {
      nextNegControls = nextNegControls.filter((w) => w !== wire);
      if (!nextControls.includes(wire)) {
        nextControls.push(wire);
      }
    } else {
      nextControls = nextControls.filter((w) => w !== wire);
      if (!nextNegControls.includes(wire)) {
        nextNegControls.push(wire);
      }
    }

    onUpdateOp({ ...op, controls: nextControls, neg_controls: nextNegControls });
  };

  // Remove a control wire
  const handleRemoveControlWire = (wire: number, isNeg: boolean) => {
    if (isNeg) {
      const nextNegControls = negControls.filter((w) => w !== wire);
      onUpdateOp({ ...op, neg_controls: nextNegControls });
    } else {
      const nextControls = controls.filter((w) => w !== wire);
      onUpdateOp({ ...op, controls: nextControls });
    }
  };

  // Add modifier handler
  const handleAddModifier = (type: "ctrl" | "negctrl" | "inv" | "pow") => {
    setShowAddMenu(false);
    const used = new Set([...op.qubits, ...controls, ...negControls]);
    let freeWire = allWires.find((w) => !used.has(w));

    if (freeWire === undefined && (type === "ctrl" || type === "negctrl")) {
      if (onAddQubit) {
        freeWire = onAddQubit();
      } else {
        freeWire = allWires.length > 0 ? Math.max(...allWires) + 1 : 1;
      }
    }

    if (type === "ctrl") {
      if (freeWire !== undefined) {
        onUpdateOp({ ...op, controls: [...controls, freeWire] });
      }
    } else if (type === "negctrl") {
      if (freeWire !== undefined) {
        onUpdateOp({ ...op, neg_controls: [...negControls, freeWire] });
      }
    } else if (type === "inv") {
      onUpdateOp({ ...op, inv: true });
    } else if (type === "pow") {
      onUpdateOp({ ...op, power: op.power !== undefined ? op.power : 2 });
    }
  };

  // Update gate parameter
  const handleParamChange = (paramIdx: number, expr: string) => {
    const nextParams = [...(op.params || [])];
    nextParams[paramIdx] = makeParam(expr);
    onUpdateOp({ ...op, params: nextParams });
  };

  const colour = gateColour(op);
  const ink = gateForeground(op);

  // Combine controls for unified, polarity-switchable rendering
  const allControls = [
    ...controls.map((w) => ({ wire: w, isNeg: false })),
    ...negControls.map((w) => ({ wire: w, isNeg: true })),
  ];

  const spec = GATE_SPECS[gateName] || {
    name: `${gateName} Gate`,
    matrix: [
      ["1", "0"],
      ["0", "1"],
    ],
    dirac: [`|ψ⟩ → ${gateName} |ψ⟩`],
    properties: ["Quantum Gate", "Unitary"],
    desc: `Unitary quantum operation ${gateName} applied on target wire(s).`,
  };

  return (
    <div className="ibm-edit-panel">
      {/* Header */}
      <div className="ibm-edit-header">
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span
            className="ibm-edit-badge"
            style={{ background: colour, color: ink }}
          >
            {gateName}
          </span>
          <span className="ibm-edit-title">Edit {gateName} gate</span>
        </div>
        <div className="ibm-edit-header-actions">
          <button
            type="button"
            className="ibm-icon-btn"
            title={`Gate: ${gateName} at Column ${op.layer} — ${spec.desc}`}
          >
            ⓘ
          </button>
          <button
            type="button"
            className="ibm-icon-btn"
            onClick={onClose}
            title="Close editor and return to Operations"
          >
            ✕
          </button>
        </div>
      </div>

      <div className="ibm-edit-body">
        {/* Section 1: Connections */}
        <div className="ibm-edit-section">
          <div className="ibm-section-title">Connections</div>
          {op.qubits.map((qWire: number, idx: number) => (
            <div key={`target-${idx}`} className="ibm-field-group">
              <label className="ibm-field-label">
                Target {op.qubits.length > 1 ? `q${idx + 1}` : "Qubit"}
              </label>
              <div className="ibm-select-row">
                <select
                  className="ibm-select"
                  value={qWire}
                  onChange={(e) => handleTargetChange(idx, Number(e.target.value))}
                >
                  {allWires.map((w: number) => (
                    <option key={`target-opt-${w}`} value={w}>
                      q[{w}]
                    </option>
                  ))}
                </select>
              </div>
            </div>
          ))}
        </div>

        {/* Section 2: Parameters (for Rx, Ry, Rz, P, U) */}
        {op.params && op.params.length > 0 && (
          <div className="ibm-edit-section">
            <div className="ibm-section-title">Parameters</div>
            {op.params.map((param: Param, idx: number) => (
              <div key={`param-${idx}`} className="ibm-field-group">
                <label className="ibm-field-label">θ{idx + 1} (expression)</label>
                <input
                  type="text"
                  className="ibm-input"
                  value={param.expr}
                  onChange={(e) => handleParamChange(idx, e.target.value)}
                  placeholder="e.g. pi/2, 1.57, 0"
                />
              </div>
            ))}
          </div>
        )}

        {/* Section 3: Modifiers */}
        {op.kind === "gate" && op.gate !== "barrier" && (
          <div className="ibm-edit-section">
            <div className="ibm-section-title">Modifiers</div>

            {/* Controls (Positive & Negative Controls) */}
            {allControls.map((item) => (
              <div key={`ctrl-mod-${item.wire}`} className="ibm-field-group">
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "3px" }}>
                  <select
                    className="ibm-polarity-select"
                    value={item.isNeg ? "negctrl" : "ctrl"}
                    onChange={(e) => handleToggleControlPolarity(item.wire, e.target.value !== "negctrl")}
                    title="Toggle control polarity (Solid • positive vs Hollow ○ negative control)"
                  >
                    <option value="ctrl">• Control (ctrl)</option>
                    <option value="negctrl">○ Negative control (negctrl)</option>
                  </select>
                </div>
                <div className="ibm-select-row">
                  <select
                    className="ibm-select"
                    value={item.wire}
                    onChange={(e) => handleControlWireChange(item.wire, item.isNeg, Number(e.target.value))}
                  >
                    {allWires.map((w: number) => (
                      <option key={`ctrl-opt-${w}`} value={w}>
                        q[{w}]
                      </option>
                    ))}
                  </select>
                  <button
                    type="button"
                    className="ibm-trash-btn"
                    onClick={() => handleRemoveControlWire(item.wire, item.isNeg)}
                    title="Remove control modifier"
                  >
                    🗑️
                  </button>
                </div>
              </div>
            ))}

            {/* Power (pow) */}
            {op.power !== undefined && (
              <div className="ibm-field-group">
                <label className="ibm-field-label">Power (pow)</label>
                <div className="ibm-select-row">
                  <input
                    type="number"
                    step="any"
                    className="ibm-input font-mono"
                    value={op.power}
                    onChange={(e) => {
                      const val = e.target.value;
                      onUpdateOp({ ...op, power: val === "" ? 1 : Number(val) });
                    }}
                  />
                  <button
                    type="button"
                    className="ibm-trash-btn"
                    onClick={() => {
                      const next = { ...op };
                      delete next.power;
                      onUpdateOp(next);
                    }}
                    title="Remove power modifier"
                  >
                    🗑️
                  </button>
                </div>
              </div>
            )}

            {/* Inverse (inv) */}
            {op.inv && (
              <div className="ibm-field-group">
                <label className="ibm-field-label">Inverse (inv)</label>
                <div className="ibm-select-row">
                  <div className="ibm-input font-mono" style={{ display: "flex", alignItems: "center" }}>
                    † (Adjoint / Inverse)
                  </div>
                  <button
                    type="button"
                    className="ibm-trash-btn"
                    onClick={() => onUpdateOp({ ...op, inv: false })}
                    title="Remove inverse modifier"
                  >
                    🗑️
                  </button>
                </div>
              </div>
            )}

            {/* Add modifier dropdown - fixed width and no truncation */}
            <div style={{ position: "relative", marginTop: "4px" }}>
              <button
                type="button"
                className="ibm-add-modifier-btn"
                onClick={() => setShowAddMenu(!showAddMenu)}
              >
                <span>Add modifier</span>
                <span className="ibm-caret">⌵</span>
              </button>
              {showAddMenu && (
                <div className="ibm-modifier-dropdown">
                  <button
                    type="button"
                    className="ibm-modifier-item"
                    onClick={() => handleAddModifier("ctrl")}
                  >
                    <span className="ibm-ctrl-dot-icon">•</span>
                    Control (ctrl)
                  </button>
                  <button
                    type="button"
                    className="ibm-modifier-item"
                    onClick={() => handleAddModifier("negctrl")}
                  >
                    <span className="ibm-ctrl-dot-icon" style={{ fontSize: "14px" }}>○</span>
                    Negative control (negctrl)
                  </button>
                  {!op.inv && (
                    <button
                      type="button"
                      className="ibm-modifier-item"
                      onClick={() => handleAddModifier("inv")}
                    >
                      <span className="ibm-ctrl-dot-icon">†</span>
                      Inverse (inv)
                    </button>
                  )}
                  {op.power === undefined && (
                    <button
                      type="button"
                      className="ibm-modifier-item"
                      onClick={() => handleAddModifier("pow")}
                    >
                      <span className="ibm-ctrl-dot-icon" style={{ fontSize: "11px" }}>xⁿ</span>
                      Power (pow)
                    </button>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Section 4: Gate Inspector & Quantum Unitary (Fills wasted space with rich quantum mechanics info) */}
        <div className="ibm-edit-section ibm-inspector-section">
          <div className="ibm-section-title">Quantum Operator Matrix</div>
          <div className="ibm-matrix-card">
            <div className="ibm-matrix-header">
              <span className="ibm-matrix-name">{spec.name}</span>
              <span className="ibm-matrix-dim">
                {spec.matrix.length}×{spec.matrix[0]?.length || spec.matrix.length} Unitary
              </span>
            </div>

            <div className="ibm-matrix-display">
              {spec.matrixPrefix && (
                <span className="ibm-matrix-prefix">{spec.matrixPrefix}</span>
              )}
              <div className="ibm-matrix-brackets">
                <div
                  className="ibm-matrix-grid"
                  style={{
                    gridTemplateColumns: `repeat(${Math.min(spec.matrix[0]?.length || 2, 4)}, minmax(0, 1fr))`,
                  }}
                >
                  {spec.matrix.slice(0, 4).map((row, rIdx) =>
                    row.slice(0, 4).map((cell, cIdx) => (
                      <span
                        key={`cell-${rIdx}-${cIdx}`}
                        className={`ibm-matrix-cell ${cell === "0" ? "zero" : cell.includes("i") ? "imaginary" : "active"}`}
                      >
                        {cell}
                      </span>
                    ))
                  )}
                </div>
              </div>
            </div>

            {/* Dirac state transformation */}
            <div className="ibm-dirac-box">
              <span className="ibm-dirac-label">Dirac Effect:</span>
              {spec.dirac.map((d, i) => (
                <div key={`dirac-${i}`} className="ibm-dirac-line font-mono">
                  {d}
                </div>
              ))}
            </div>

            {/* Quantum properties tags */}
            <div className="ibm-prop-tags">
              {spec.properties.map((prop, i) => (
                <span key={`prop-${i}`} className="ibm-prop-tag">
                  {prop}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* Section 5: Quick Gate Actions */}
        <div className="ibm-edit-section ibm-actions-section">
          <div className="ibm-section-title">Actions</div>
          <div className="ibm-action-buttons-grid">
            {onDuplicate && (
              <button
                type="button"
                className="ibm-panel-action-btn"
                onClick={onDuplicate}
                title="Duplicate this gate to the next available column"
              >
                <span>📋</span> Duplicate
              </button>
            )}
            <button
              type="button"
              className={`ibm-panel-action-btn ${op.inv ? "active" : ""}`}
              onClick={() => onUpdateOp({ ...op, inv: !op.inv })}
              title="Toggle gate adjoint / inverse (†)"
            >
              <span>†</span> {op.inv ? "Remove Inv" : "Invert (†)"}
            </button>
            {onDelete && (
              <button
                type="button"
                className="ibm-panel-action-btn danger"
                onClick={onDelete}
                title="Remove gate from circuit"
              >
                <span>🗑️</span> Delete
              </button>
            )}
            <button
              type="button"
              className="ibm-panel-action-btn primary"
              onClick={onClose}
              title="Apply edits and return to Operations"
            >
              <span>✓</span> Done
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

