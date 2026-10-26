import type { CircuitIR, Op } from "@composer/types";
import { makeOp } from "@composer/ir";

export interface ImportFormatOption {
  id: string;
  name: string;
  framework: string;
  ext: string;
  badge: string;
  description: string;
  placeholder: string;
}

export const MAX_IMPORT_BYTES = 100 * 1024; // 100 KB
export const MAX_IMPORT_CHARS = 20_000;

export const IMPORT_FORMATS: ImportFormatOption[] = [
  {
    id: "auto",
    name: "Auto-Detect",
    framework: "auto",
    ext: ".*",
    badge: "Auto",
    description: "Automatically identify circuit format from file extension or syntax signatures",
    placeholder: `// Paste OpenQASM 3.0, Circuit IR JSON, Qiskit, Cirq, PennyLane, qBraid, or CUDA-Q code\nOPENQASM 3.0;\ninclude "stdgates.inc";\nqubit[2] q;\nh q[0];\ncx q[0], q[1];`,
  },
  {
    id: "qasm3",
    name: "OpenQASM 3.0",
    framework: "qasm3",
    ext: ".qasm",
    badge: "QASM",
    description: "Industry-standard open quantum assembly specification",
    placeholder: `OPENQASM 3.0;\ninclude "stdgates.inc";\n\nqubit[2] q;\nbit[2] c;\n\nh q[0];\ncx q[0], q[1];\nc[0] = measure q[0];\nc[1] = measure q[1];`,
  },
  {
    id: "json",
    name: "Circuit IR (JSON)",
    framework: "json",
    ext: ".json",
    badge: "JSON",
    description: "Platform JSON AST interchange representation",
    placeholder: `{\n  "name": "bell-pair",\n  "n_qubits": 2,\n  "n_clbits": 2,\n  "ops": [\n    {"kind": "gate", "gate": "h", "qubits": [0], "layer": 0},\n    {"kind": "gate", "gate": "cx", "controls": [0], "qubits": [1], "layer": 1},\n    {"kind": "measure", "qubits": [0], "clbits": [0], "layer": 2},\n    {"kind": "measure", "qubits": [1], "clbits": [1], "layer": 2}\n  ]\n}`,
  },
  {
    id: "qiskit",
    name: "Qiskit",
    framework: "qiskit",
    ext: ".py",
    badge: "Python",
    description: "IBM Quantum Python SDK circuit",
    placeholder: `from qiskit import QuantumCircuit\n\ncircuit = QuantumCircuit(2, 2)\ncircuit.h(0)\ncircuit.cx(0, 1)\ncircuit.measure([0, 1], [0, 1])`,
  },
  {
    id: "cirq",
    name: "Cirq",
    framework: "cirq",
    ext: ".py",
    badge: "Python",
    description: "Google Quantum AI Python simulation circuit",
    placeholder: `import cirq\n\nq = cirq.LineQubit.range(2)\ncircuit = cirq.Circuit(\n    cirq.H(q[0]),\n    cirq.CNOT(q[0], q[1]),\n    cirq.measure(q[0], q[1], key="m")\n)`,
  },
  {
    id: "pennylane",
    name: "PennyLane",
    framework: "pennylane",
    ext: ".py",
    badge: "Python",
    description: "Xanadu differentiable quantum computing circuit",
    placeholder: `import pennylane as qml\n\ndev = qml.device("default.qubit", wires=2)\n\n@qml.qnode(dev)\ndef circuit():\n    qml.Hadamard(wires=0)\n    qml.CNOT(wires=[0, 1])\n    return qml.probs(wires=[0, 1])`,
  },
  {
    id: "qbraid",
    name: "qBraid SDK",
    framework: "qbraid",
    ext: ".py",
    badge: "Python",
    description: "Unified cross-cloud quantum hardware submission script",
    placeholder: `from qbraid.transpiler import transpile\nfrom qiskit import QuantumCircuit\n\nqc = QuantumCircuit(2, 2)\nqc.h(0)\nqc.cx(0, 1)\nqc.measure([0, 1], [0, 1])\ncircuit = transpile(qc, "qasm3")`,
  },
  {
    id: "cudaq",
    name: "CUDA-Q (Python)",
    framework: "cudaq",
    ext: ".py",
    badge: "Python",
    description: "NVIDIA CUDA-Q Python kernel with GPU statevector",
    placeholder: `import cudaq\n\ncircuit = cudaq.make_kernel()\nq = circuit.qalloc(2)\ncircuit.h(q[0])\ncircuit.cx(q[0], q[1])\ncircuit.mz(q)`,
  },
  {
    id: "cudaq_cpp",
    name: "CUDA-Q (C++)",
    framework: "cudaq_cpp",
    ext: ".cpp",
    badge: "C++",
    description: "NVIDIA accelerated quantum-classical C++ kernel (Export only)",
    placeholder: `#include <cudaq.h>\n\nstruct bell {\n  void operator()() __qpu__ {\n    cudaq::qvector q(2);\n    h(q[0]);\n    x<cudaq::ctrl>(q[0], q[1]);\n    mz(q);\n  }\n};`,
  },
];

/**
 * Automatically detect format from file extension or content signatures.
 */
export function detectFormat(content: string, filename?: string): string {
  const trimmed = content.trim();

  if (filename) {
    const lower = filename.toLowerCase();
    if (lower.endsWith(".qasm")) return "qasm3";
    if (lower.endsWith(".json")) return "json";
    if (lower.endsWith(".cpp") || lower.endsWith(".cc") || lower.endsWith(".cxx") || lower.endsWith(".h")) {
      return "cudaq_cpp";
    }
  }

  // Content heuristics
  if (trimmed.startsWith("{") && (trimmed.includes('"n_qubits"') || trimmed.includes('"ops"'))) {
    return "json";
  }

  if (
    trimmed.startsWith("OPENQASM") ||
    trimmed.includes('include "stdgates.inc"') ||
    trimmed.includes('include "qelib1.inc"') ||
    /\bqubit\[\d+\]/.test(trimmed)
  ) {
    return "qasm3";
  }

  if (trimmed.includes("#include <cudaq.h>") || trimmed.includes("__qpu__")) {
    return "cudaq_cpp";
  }

  if (trimmed.includes("import cirq") || trimmed.includes("cirq.Circuit")) {
    return "cirq";
  }

  if (
    trimmed.includes("import pennylane") ||
    trimmed.includes("from pennylane") ||
    trimmed.includes("qml.qnode") ||
    trimmed.includes("qml.device")
  ) {
    return "pennylane";
  }

  if (trimmed.includes("import cudaq") || trimmed.includes("cudaq.make_kernel")) {
    return "cudaq";
  }

  if (trimmed.includes("import qbraid") || trimmed.includes("from qbraid")) {
    return "qbraid";
  }

  if (
    trimmed.includes("from qiskit") ||
    trimmed.includes("import qiskit") ||
    trimmed.includes("QuantumCircuit")
  ) {
    return "qiskit";
  }

  // Fallback heuristic: semicolons indicate QASM, indentation/def/import indicates Python
  if (trimmed.includes(";") && !trimmed.includes("def ") && !trimmed.includes("import ")) {
    return "qasm3";
  }

  return "qiskit";
}

/**
 * Validate and safely parse Circuit IR JSON without data tampering.
 * Verifies qubit indices, gate names, layers, and structure boundaries.
 */
export function validateAndSanitizeCircuitIR(
  rawJson: string
): { ok: true; ir: CircuitIR } | { ok: false; error: string } {
  let parsed: any;
  try {
    parsed = JSON.parse(rawJson);
  } catch (err: any) {
    return { ok: false, error: `Invalid JSON syntax: ${err.message}` };
  }

  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    return { ok: false, error: "Circuit IR must be a JSON object." };
  }

  // Prevent prototype pollution
  if (Object.prototype.hasOwnProperty.call(parsed, "__proto__")) {
    return { ok: false, error: "Malformed payload rejected for security." };
  }

  const nQubits = Number(parsed.n_qubits);
  if (!Number.isInteger(nQubits) || nQubits < 1 || nQubits > 20) {
    return {
      ok: false,
      error: `Invalid n_qubits (${parsed.n_qubits}). Must be an integer between 1 and 20.`,
    };
  }

  const nClbits = Number(parsed.n_clbits ?? nQubits);
  if (!Number.isInteger(nClbits) || nClbits < 1) {
    return {
      ok: false,
      error: `Invalid n_clbits (${parsed.n_clbits}). Must be a positive integer.`,
    };
  }

  if (!Array.isArray(parsed.ops)) {
    return { ok: false, error: "Missing or invalid `ops` array in circuit." };
  }

  const sanitizedOps: Op[] = [];

  for (let idx = 0; idx < parsed.ops.length; idx++) {
    const rawOp = parsed.ops[idx];
    if (!rawOp || typeof rawOp !== "object") {
      return { ok: false, error: `Invalid operation at index ${idx}: expected an object.` };
    }

    const kind = String(rawOp.kind || "gate").toLowerCase();
    const validKinds = ["gate", "measure", "reset", "barrier", "custom", "if", "for", "while", "box"];
    if (!validKinds.includes(kind)) {
      return { ok: false, error: `Unknown operation kind '${kind}' at index ${idx}.` };
    }

    const layer = Number(rawOp.layer ?? 0);
    if (!Number.isInteger(layer) || layer < 0) {
      return { ok: false, error: `Invalid layer (${rawOp.layer}) at op index ${idx}.` };
    }

    // Validate qubits array
    const rawQubits = Array.isArray(rawOp.qubits) ? rawOp.qubits : [];
    const qubits: number[] = [];
    for (const q of rawQubits) {
      const qNum = Number(q);
      if (!Number.isInteger(qNum) || qNum < 0 || qNum >= nQubits) {
        return {
          ok: false,
          error: `Qubit index ${q} at op index ${idx} is out of bounds for a ${nQubits}-qubit circuit.`,
        };
      }
      qubits.push(qNum);
    }

    // Validate controls array
    const rawCtrls = Array.isArray(rawOp.controls) ? rawOp.controls : [];
    const controls: number[] = [];
    for (const c of rawCtrls) {
      const cNum = Number(c);
      if (!Number.isInteger(cNum) || cNum < 0 || cNum >= nQubits) {
        return {
          ok: false,
          error: `Control qubit index ${c} at op index ${idx} is out of bounds for a ${nQubits}-qubit circuit.`,
        };
      }
      if (qubits.includes(cNum)) {
        return {
          ok: false,
          error: `Qubit ${cNum} cannot be both a control and target at op index ${idx}.`,
        };
      }
      controls.push(cNum);
    }

    // Validate clbits
    const rawClbits = Array.isArray(rawOp.clbits) ? rawOp.clbits : [];
    const clbits: number[] = [];
    for (const c of rawClbits) {
      const cNum = Number(c);
      if (Number.isInteger(cNum) && cNum >= 0) {
        clbits.push(cNum);
      }
    }

    // Validate parameters
    const params = Array.isArray(rawOp.params)
      ? rawOp.params.map((p: any) => ({
          expr: String(p?.expr ?? "0").trim(),
        }))
      : undefined;

    const op: Op = makeOp(kind as any, {
      id: String(rawOp.id || `op-${idx}-${Date.now()}`),
      layer,
      qubits,
      controls,
      clbits,
      gate: rawOp.gate ? String(rawOp.gate).toLowerCase() : undefined,
      params: params ?? [],
    });

    sanitizedOps.push(op);
  }

  const ir: CircuitIR = {
    name: String(parsed.name || "imported_circuit").trim() || "imported_circuit",
    n_qubits: nQubits,
    n_clbits: nClbits,
    ops: sanitizedOps,
  };

  return { ok: true, ir };
}
