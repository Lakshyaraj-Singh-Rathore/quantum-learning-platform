import type { CircuitIR, Op } from "@composer/types";

export interface ExportTarget {
  id: string;
  name: string;
  framework: string;
  ext: string;
  mimeType: string;
  badge: string;
  iconType: "qasm" | "python" | "cpp" | "json";
  description: string;
}

export const EXPORT_TARGETS: ExportTarget[] = [
  {
    id: "qasm",
    name: "OpenQASM 3.0",
    framework: "OpenQASM 3",
    ext: ".qasm",
    mimeType: "text/plain",
    badge: "QASM",
    iconType: "qasm",
    description: "Industry-standard open quantum assembly specification",
  },
  {
    id: "qiskit",
    name: "Qiskit",
    framework: "Qiskit (Python)",
    ext: ".py",
    mimeType: "text/x-python",
    badge: "Python",
    iconType: "python",
    description: "IBM Quantum Python SDK with AerSimulator execution",
  },
  {
    id: "cirq",
    name: "Cirq",
    framework: "Cirq (Python)",
    ext: ".py",
    mimeType: "text/x-python",
    badge: "Python",
    iconType: "python",
    description: "Google Quantum AI Python simulation framework",
  },
  {
    id: "pennylane",
    name: "PennyLane",
    framework: "PennyLane (Python)",
    ext: ".py",
    mimeType: "text/x-python",
    badge: "Python",
    iconType: "python",
    description: "Xanadu differentiable quantum computing library",
  },
  {
    id: "qbraid",
    name: "qBraid SDK",
    framework: "qBraid (Python)",
    ext: ".py",
    mimeType: "text/x-python",
    badge: "Python",
    iconType: "python",
    description: "Unified cross-cloud quantum hardware submission script",
  },
  {
    id: "cudaq_cpp",
    name: "CUDA-Q (C++)",
    framework: "CUDA-Q (C++)",
    ext: ".cpp",
    mimeType: "text/x-c++src",
    badge: "C++",
    iconType: "cpp",
    description: "NVIDIA accelerated quantum-classical C++ kernel",
  },
  {
    id: "cudaq_py",
    name: "CUDA-Q (Python)",
    framework: "CUDA-Q (Python)",
    ext: ".py",
    mimeType: "text/x-python",
    badge: "Python",
    iconType: "python",
    description: "NVIDIA CUDA-Q Python kernel with GPU statevector",
  },
  {
    id: "json",
    name: "Circuit IR",
    framework: "Circuit IR (JSON)",
    ext: ".json",
    mimeType: "application/json",
    badge: "JSON",
    iconType: "json",
    description: "Platform JSON AST interchange representation",
  },
];

function sanitizeName(name: string): string {
  return name.trim().toLowerCase().replace(/[^a-z0-9_-]+/g, "_") || "circuit";
}

function sortOps(ops: Op[]): Op[] {
  return [...ops].sort((a, b) => {
    if (a.layer !== b.layer) return a.layer - b.layer;
    const aQ = a.qubits[0] ?? 0;
    const bQ = b.qubits[0] ?? 0;
    return aQ - bQ;
  });
}

function formatAngle(expr?: string): string {
  if (!expr) return "0";
  return expr.replace(/\s+/g, "");
}

/* -------------------------------------------------------------------------- */
/* 1. OpenQASM 3.0 Generator                                                  */
/* -------------------------------------------------------------------------- */
export function generateQasm3(ir: CircuitIR): string {
  let out = `OPENQASM 3.0;\ninclude "stdgates.inc";\n\n`;
  out += `qubit[${ir.n_qubits}] q;\n`;
  out += `bit[${ir.n_clbits}] c;\n\n`;

  function emitOp(op: Op, indent = ""): string {
    let res = "";
    const pad = indent;
    if (op.kind === "gate") {
      const g = (op.gate || "x").toLowerCase();
      const posCtrls = op.controls || [];
      const negCtrls = op.neg_controls || [];
      const targets = op.qubits || [0];
      const hasNeg = negCtrls.length > 0;

      // Handle negative control wrapping via X gates
      if (hasNeg) {
        for (const nc of negCtrls) {
          res += `${pad}x q[${nc}];\n`;
        }
      }

      const allCtrls = [...posCtrls, ...negCtrls];

      if (g === "swap") {
        const q0 = targets[0] ?? 0;
        const q1 = targets[1] ?? (q0 === 0 ? 1 : 0);
        if (allCtrls.length > 0) {
          res += `${pad}cswap q[${allCtrls[0]}], q[${q0}], q[${q1}];\n`;
        } else {
          res += `${pad}swap q[${q0}], q[${q1}];\n`;
        }
      } else if (allCtrls.length > 0) {
        if (allCtrls.length === 1) {
          if (g === "x" || g === "cx" || g === "cnot") {
            res += `${pad}cx q[${allCtrls[0]}], q[${targets[0]}];\n`;
          } else if (g === "z" || g === "cz") {
            res += `${pad}cz q[${allCtrls[0]}], q[${targets[0]}];\n`;
          } else if (g === "y" || g === "cy") {
            res += `${pad}cy q[${allCtrls[0]}], q[${targets[0]}];\n`;
          } else if (g === "h" || g === "ch") {
            res += `${pad}ch q[${allCtrls[0]}], q[${targets[0]}];\n`;
          } else if (g === "p" || g === "cp") {
            const angle = formatAngle(op.params?.[0]?.expr || "pi");
            res += `${pad}cp(${angle}) q[${allCtrls[0]}], q[${targets[0]}];\n`;
          } else if (g === "rx" || g === "crx") {
            const angle = formatAngle(op.params?.[0]?.expr || "pi");
            res += `${pad}crx(${angle}) q[${allCtrls[0]}], q[${targets[0]}];\n`;
          } else if (g === "ry" || g === "cry") {
            const angle = formatAngle(op.params?.[0]?.expr || "pi");
            res += `${pad}cry(${angle}) q[${allCtrls[0]}], q[${targets[0]}];\n`;
          } else if (g === "rz" || g === "crz") {
            const angle = formatAngle(op.params?.[0]?.expr || "pi");
            res += `${pad}crz(${angle}) q[${allCtrls[0]}], q[${targets[0]}];\n`;
          } else {
            res += `${pad}c${g} q[${allCtrls[0]}], q[${targets[0]}];\n`;
          }
        } else if (allCtrls.length === 2 && (g === "x" || g === "cx" || g === "ccx")) {
          res += `${pad}ccx q[${allCtrls[0]}], q[${allCtrls[1]}], q[${targets[0]}];\n`;
        } else {
          res += `${pad}mcx q[${allCtrls.join("], q[")}], q[${targets[0]}];\n`;
        }
      } else if (op.params && op.params.length > 0) {
        const angle = formatAngle(op.params[0].expr);
        res += `${pad}${g}(${angle}) q[${targets[0]}];\n`;
      } else {
        res += `${pad}${g} q[${targets[0]}];\n`;
      }

      // Restore negative control qubits
      if (hasNeg) {
        for (const nc of negCtrls) {
          res += `${pad}x q[${nc}];\n`;
        }
      }
    } else if (op.kind === "measure") {
      const q = op.qubits[0] ?? 0;
      const c = op.clbits?.[0] ?? q;
      res += `${pad}c[${c}] = measure q[${q}];\n`;
    } else if (op.kind === "reset") {
      res += `${pad}reset q[${op.qubits[0] ?? 0}];\n`;
    } else if (op.kind === "barrier") {
      res += `${pad}barrier q;\n`;
    } else if (op.kind === "if") {
      const bit = op.condition?.bit ?? 0;
      const val = op.condition?.value ?? 1;
      res += `${pad}if (c[${bit}] == ${val}) {\n`;
      for (const child of op.body || []) {
        res += emitOp(child, pad + "  ");
      }
      if (op.else_body && op.else_body.length > 0) {
        res += `${pad}} else {\n`;
        for (const child of op.else_body) {
          res += emitOp(child, pad + "  ");
        }
      }
      res += `${pad}}\n`;
    } else if (op.kind === "for") {
      const n = op.loop_n || 1;
      res += `${pad}for uint i in [0:${n - 1}] {\n`;
      for (const child of op.body || []) {
        res += emitOp(child, pad + "  ");
      }
      res += `${pad}}\n`;
    } else if (op.kind === "while") {
      const bit = op.condition?.bit ?? 0;
      const val = op.condition?.value ?? 1;
      res += `${pad}while (c[${bit}] == ${val}) {\n`;
      for (const child of op.body || []) {
        res += emitOp(child, pad + "  ");
      }
      res += `${pad}}\n`;
    }
    return res;
  }

  for (const op of sortOps(ir.ops)) {
    out += emitOp(op);
  }

  return out;
}

/* -------------------------------------------------------------------------- */
/* 2. IBM Qiskit Generator                                                    */
/* -------------------------------------------------------------------------- */
export function generateQiskit(ir: CircuitIR, shots = 1024): string {
  let out = `"""Generated by QuantumLearn - IBM Qiskit."""\n\n`;
  out += `from qiskit import QuantumCircuit, transpile\n`;
  out += `from qiskit_aer import AerSimulator\n`;
  out += `from numpy import pi\n\n`;
  out += `qc = QuantumCircuit(${ir.n_qubits}, ${ir.n_clbits})\n\n`;

  function emitOp(op: Op, indent = ""): string {
    let res = "";
    const pad = indent;
    if (op.kind === "gate") {
      const g = (op.gate || "x").toLowerCase();
      const posCtrls = op.controls || [];
      const negCtrls = op.neg_controls || [];
      const targets = op.qubits || [0];
      const hasNeg = negCtrls.length > 0;

      if (hasNeg) {
        for (const nc of negCtrls) {
          res += `${pad}qc.x(${nc})\n`;
        }
      }

      const allCtrls = [...posCtrls, ...negCtrls];

      if (g === "swap") {
        const q0 = targets[0] ?? 0;
        const q1 = targets[1] ?? (q0 === 0 ? 1 : 0);
        if (allCtrls.length > 0) {
          res += `${pad}qc.cswap(${allCtrls[0]}, ${q0}, ${q1})\n`;
        } else {
          res += `${pad}qc.swap(${q0}, ${q1})\n`;
        }
      } else if (allCtrls.length > 0) {
        if (allCtrls.length === 1) {
          if (g === "x" || g === "cx" || g === "cnot") {
            res += `${pad}qc.cx(${allCtrls[0]}, ${targets[0]})\n`;
          } else if (g === "z" || g === "cz") {
            res += `${pad}qc.cz(${allCtrls[0]}, ${targets[0]})\n`;
          } else if (g === "y" || g === "cy") {
            res += `${pad}qc.cy(${allCtrls[0]}, ${targets[0]})\n`;
          } else if (g === "h" || g === "ch") {
            res += `${pad}qc.ch(${allCtrls[0]}, ${targets[0]})\n`;
          } else if (g === "p" || g === "cp") {
            const angle = formatAngle(op.params?.[0]?.expr || "pi");
            res += `${pad}qc.cp(${angle}, ${allCtrls[0]}, ${targets[0]})\n`;
          } else if (g === "rx" || g === "crx") {
            const angle = formatAngle(op.params?.[0]?.expr || "pi");
            res += `${pad}qc.crx(${angle}, ${allCtrls[0]}, ${targets[0]})\n`;
          } else if (g === "ry" || g === "cry") {
            const angle = formatAngle(op.params?.[0]?.expr || "pi");
            res += `${pad}qc.cry(${angle}, ${allCtrls[0]}, ${targets[0]})\n`;
          } else if (g === "rz" || g === "crz") {
            const angle = formatAngle(op.params?.[0]?.expr || "pi");
            res += `${pad}qc.crz(${angle}, ${allCtrls[0]}, ${targets[0]})\n`;
          } else {
            res += `${pad}qc.c${g}(${allCtrls[0]}, ${targets[0]})\n`;
          }
        } else if (allCtrls.length === 2 && (g === "x" || g === "cx" || g === "ccx")) {
          res += `${pad}qc.ccx(${allCtrls[0]}, ${allCtrls[1]}, ${targets[0]})\n`;
        } else {
          res += `${pad}qc.mcx([${allCtrls.join(", ")}], ${targets[0]})\n`;
        }
      } else if (op.params && op.params.length > 0) {
        const angle = formatAngle(op.params[0].expr);
        res += `${pad}qc.${g}(${angle}, ${targets[0]})\n`;
      } else {
        res += `${pad}qc.${g}(${targets[0]})\n`;
      }

      if (hasNeg) {
        for (const nc of negCtrls) {
          res += `${pad}qc.x(${nc})\n`;
        }
      }
    } else if (op.kind === "measure") {
      const q = op.qubits[0] ?? 0;
      const c = op.clbits?.[0] ?? q;
      res += `${pad}qc.measure(${q}, ${c})\n`;
    } else if (op.kind === "reset") {
      res += `${pad}qc.reset(${op.qubits[0] ?? 0})\n`;
    } else if (op.kind === "barrier") {
      res += `${pad}qc.barrier()\n`;
    } else if (op.kind === "if") {
      const bit = op.condition?.bit ?? 0;
      const val = op.condition?.value ?? 1;
      res += `${pad}with qc.if_test((qc.clbits[${bit}], ${val})):\n`;
      for (const child of op.body || []) {
        res += emitOp(child, pad + "    ");
      }
      if (op.else_body && op.else_body.length > 0) {
        res += `${pad}# else branch\n`;
        for (const child of op.else_body) {
          res += emitOp(child, pad + "    ");
        }
      }
    }
    return res;
  }

  for (const op of sortOps(ir.ops)) {
    out += emitOp(op);
  }

  out += `\n# Simulate circuit with Aer\n`;
  out += `simulator = AerSimulator()\n`;
  out += `compiled_circuit = transpile(qc, simulator)\n`;
  out += `job = simulator.run(compiled_circuit, shots=${shots})\n`;
  out += `result = job.result()\n`;
  out += `counts = result.get_counts()\n`;
  out += `print("Measurement Counts:", counts)\n`;

  return out;
}

/* -------------------------------------------------------------------------- */
/* 3. Google Cirq Generator                                                   */
/* -------------------------------------------------------------------------- */
export function generateCirq(ir: CircuitIR, shots = 1024): string {
  let out = `"""Generated by QuantumLearn - Google Cirq."""\n\n`;
  out += `import cirq\n`;
  out += `from numpy import pi\n\n`;
  out += `q = cirq.LineQubit.range(${ir.n_qubits})\n`;
  out += `circuit = cirq.Circuit([\n`;

  for (const op of sortOps(ir.ops)) {
    if (op.kind === "gate") {
      const g = (op.gate || "x").toLowerCase();
      const posCtrls = op.controls || [];
      const negCtrls = op.neg_controls || [];
      const targets = op.qubits || [0];
      const allCtrls = [...posCtrls, ...negCtrls];

      if (g === "swap") {
        const q0 = targets[0] ?? 0;
        const q1 = targets[1] ?? (q0 === 0 ? 1 : 0);
        out += `    cirq.SWAP(q[${q0}], q[${q1}]),\n`;
      } else if (allCtrls.length > 0) {
        const ctrlValues = [
          ...posCtrls.map(() => 1),
          ...negCtrls.map(() => 0),
        ];
        const ctrlStr = allCtrls.map((c) => `q[${c}]`).join(", ");
        const valStr = ctrlValues.join(", ");

        if (g === "x" && allCtrls.length === 1 && ctrlValues[0] === 1) {
          out += `    cirq.CNOT(q[${allCtrls[0]}], q[${targets[0]}]),\n`;
        } else if (g === "z" && allCtrls.length === 1 && ctrlValues[0] === 1) {
          out += `    cirq.CZ(q[${allCtrls[0]}], q[${targets[0]}]),\n`;
        } else if (g === "x" && allCtrls.length === 2 && ctrlValues[0] === 1 && ctrlValues[1] === 1) {
          out += `    cirq.TOFFOLI(q[${allCtrls[0]}], q[${allCtrls[1]}], q[${targets[0]}]),\n`;
        } else {
          // Native Cirq controlled_by with control_values for negative controls
          const baseGate = g === "x" ? "cirq.X" : g === "z" ? "cirq.Z" : g === "y" ? "cirq.Y" : g === "h" ? "cirq.H" : `cirq.${g.toUpperCase()}`;
          out += `    ${baseGate}(q[${targets[0]}]).controlled_by(${ctrlStr}, control_values=[${valStr}]),\n`;
        }
      } else if (op.params && op.params.length > 0) {
        const angle = formatAngle(op.params[0].expr);
        out += `    cirq.${g}(rads=${angle})(q[${targets[0]}]),\n`;
      } else {
        out += `    cirq.${g.toUpperCase()}(q[${targets[0]}]),\n`;
      }
    } else if (op.kind === "measure") {
      const q = op.qubits[0] ?? 0;
      out += `    cirq.measure(q[${q}], key='m${q}'),\n`;
    }
  }

  out += `])\n\n`;
  out += `# Execute on Cirq local simulator\n`;
  out += `simulator = cirq.Simulator()\n`;
  out += `result = simulator.run(circuit, repetitions=${shots})\n`;
  out += `print("Circuit execution results:")\n`;
  out += `print(result)\n`;

  return out;
}

/* -------------------------------------------------------------------------- */
/* 4. Xanadu PennyLane Generator                                              */
/* -------------------------------------------------------------------------- */
export function generatePennyLane(ir: CircuitIR, shots = 1024): string {
  let out = `"""Generated by QuantumLearn - Xanadu PennyLane."""\n\n`;
  out += `import pennylane as qml\n`;
  out += `from numpy import pi\n\n`;
  out += `dev = qml.device("default.qubit", wires=${ir.n_qubits}, shots=${shots})\n\n`;
  out += `@qml.qnode(dev)\n`;
  out += `def circuit():\n`;

  let hasGate = false;
  for (const op of sortOps(ir.ops)) {
    if (op.kind === "gate") {
      hasGate = true;
      const g = (op.gate || "x").toLowerCase();
      const posCtrls = op.controls || [];
      const negCtrls = op.neg_controls || [];
      const targets = op.qubits || [0];
      const allCtrls = [...posCtrls, ...negCtrls];

      if (g === "swap") {
        const q0 = targets[0] ?? 0;
        const q1 = targets[1] ?? (q0 === 0 ? 1 : 0);
        out += `    qml.SWAP(wires=[${q0}, ${q1}])\n`;
      } else if (allCtrls.length > 0) {
        const ctrlValues = [
          ...posCtrls.map(() => 1),
          ...negCtrls.map(() => 0),
        ];
        if (allCtrls.length === 1 && ctrlValues[0] === 1 && g === "x") {
          out += `    qml.CNOT(wires=[${allCtrls[0]}, ${targets[0]}])\n`;
        } else if (allCtrls.length === 1 && ctrlValues[0] === 1 && g === "z") {
          out += `    qml.CZ(wires=[${allCtrls[0]}, ${targets[0]}])\n`;
        } else if (allCtrls.length === 1 && ctrlValues[0] === 1 && g === "y") {
          out += `    qml.CY(wires=[${allCtrls[0]}, ${targets[0]}])\n`;
        } else if (allCtrls.length === 2 && ctrlValues[0] === 1 && ctrlValues[1] === 1 && g === "x") {
          out += `    qml.Toffoli(wires=[${allCtrls[0]}, ${allCtrls[1]}, ${targets[0]}])\n`;
        } else {
          const baseOp = g === "x" ? `qml.PauliX(wires=${targets[0]})` : g === "z" ? `qml.PauliZ(wires=${targets[0]})` : `qml.Hadamard(wires=${targets[0]})`;
          out += `    qml.ctrl(${baseOp}, control=[${allCtrls.join(", ")}], control_values=[${ctrlValues.join(", ")}])\n`;
        }
      } else if (op.params && op.params.length > 0) {
        const angle = formatAngle(op.params[0].expr);
        if (g === "rx") out += `    qml.RX(${angle}, wires=${targets[0]})\n`;
        else if (g === "ry") out += `    qml.RY(${angle}, wires=${targets[0]})\n`;
        else if (g === "rz") out += `    qml.RZ(${angle}, wires=${targets[0]})\n`;
        else if (g === "p") out += `    qml.PhaseShift(${angle}, wires=${targets[0]})\n`;
        else out += `    qml.${g.toUpperCase()}(${angle}, wires=${targets[0]})\n`;
      } else {
        if (g === "h") out += `    qml.Hadamard(wires=${targets[0]})\n`;
        else if (g === "x") out += `    qml.PauliX(wires=${targets[0]})\n`;
        else if (g === "y") out += `    qml.PauliY(wires=${targets[0]})\n`;
        else if (g === "z") out += `    qml.PauliZ(wires=${targets[0]})\n`;
        else if (g === "s") out += `    qml.S(wires=${targets[0]})\n`;
        else if (g === "t") out += `    qml.T(wires=${targets[0]})\n`;
        else if (g === "sx") out += `    qml.SX(wires=${targets[0]})\n`;
        else out += `    qml.${g.toUpperCase()}(wires=${targets[0]})\n`;
      }
    }
  }

  if (!hasGate) {
    out += `    pass\n`;
  }

  out += `    return qml.counts()\n\n`;
  out += `if __name__ == "__main__":\n`;
  out += `    print("PennyLane Sampled Counts:")\n`;
  out += `    print(circuit())\n`;

  return out;
}

/* -------------------------------------------------------------------------- */
/* 5. qBraid SDK Generator                                                    */
/* -------------------------------------------------------------------------- */
export function generateQBraid(ir: CircuitIR, shots = 1024): string {
  const qasm3 = generateQasm3(ir);
  let out = `"""Generated by QuantumLearn - qBraid SDK Submission."""\n\n`;
  out += `import os\n`;
  out += `from qbraid.runtime import QbraidProvider\n\n`;
  out += `QASM_CODE = """\\\n${qasm3}"""\n\n`;
  out += `SHOTS = ${shots}\n`;
  out += `DEVICE_ID = os.environ.get("QBRAID_DEVICE_ID", "qbraid_qir_simulator")\n\n`;
  out += `def main():\n`;
  out += `    api_key = os.environ.get("QBRAID_API_KEY")\n`;
  out += `    if not api_key:\n`;
  out += `        print("Please set your QBRAID_API_KEY environment variable to submit to cloud hardware.")\n`;
  out += `        print("Printing generated OpenQASM 3.0 circuit instead:")\n`;
  out += `        print(QASM_CODE)\n`;
  out += `        return\n\n`;
  out += `    provider = QbraidProvider(api_key=api_key)\n`;
  out += `    device = provider.get_device(DEVICE_ID)\n`;
  out += `    print(f"Submitting circuit to {DEVICE_ID} ({SHOTS} shots)...")\n`;
  out += `    job = device.run(QASM_CODE, shots=SHOTS)\n`;
  out += `    print(f"Job ID: {job.id}")\n`;
  out += `    job.wait_for_final_state()\n`;
  out += `    result = job.result()\n`;
  out += `    print("Results:", result.data.get_counts())\n\n`;
  out += `if __name__ == "__main__":\n`;
  out += `    main()\n`;

  return out;
}

/* -------------------------------------------------------------------------- */
/* 6. NVIDIA CUDA-Q C++ Generator                                             */
/* -------------------------------------------------------------------------- */
export function generateCudaQCpp(ir: CircuitIR): string {
  let out = `// Generated by QuantumLearn - NVIDIA CUDA-Q (C++)\n`;
  out += `#include <cudaq.h>\n`;
  out += `#include <iostream>\n\n`;
  out += `struct quantum_circuit {\n`;
  out += `    void operator()() __qpu__ {\n`;
  out += `        cudaq::qvector q(${ir.n_qubits});\n\n`;

  for (const op of sortOps(ir.ops)) {
    if (op.kind === "gate") {
      const g = (op.gate || "x").toLowerCase();
      const posCtrls = op.controls || [];
      const negCtrls = op.neg_controls || [];
      const targets = op.qubits || [0];
      const hasNeg = negCtrls.length > 0;

      if (hasNeg) {
        for (const nc of negCtrls) {
          out += `        x(q[${nc}]);\n`;
        }
      }

      const allCtrls = [...posCtrls, ...negCtrls];

      if (g === "swap") {
        const q0 = targets[0] ?? 0;
        const q1 = targets[1] ?? (q0 === 0 ? 1 : 0);
        out += `        swap(q[${q0}], q[${q1}]);\n`;
      } else if (allCtrls.length === 1) {
        if (g === "x" || g === "cx") {
          out += `        cx(q[${allCtrls[0]}], q[${targets[0]}]);\n`;
        } else if (g === "z" || g === "cz") {
          out += `        cz(q[${allCtrls[0]}], q[${targets[0]}]);\n`;
        } else if (g === "y" || g === "cy") {
          out += `        cy(q[${allCtrls[0]}], q[${targets[0]}]);\n`;
        } else if (g === "h" || g === "ch") {
          out += `        ch(q[${allCtrls[0]}], q[${targets[0]}]);\n`;
        } else {
          out += `        cudaq::control(q[${allCtrls[0]}], [&]() { ${g}(q[${targets[0]}]); });\n`;
        }
      } else if (allCtrls.length > 1) {
        out += `        cudaq::control({${allCtrls.map((c) => `q[${c}]`).join(", ")}}, [&]() { ${g}(q[${targets[0]}]); });\n`;
      } else if (op.params && op.params.length > 0) {
        const angle = formatAngle(op.params[0].expr);
        out += `        ${g}(${angle}, q[${targets[0]}]);\n`;
      } else {
        out += `        ${g}(q[${targets[0]}]);\n`;
      }

      if (hasNeg) {
        for (const nc of negCtrls) {
          out += `        x(q[${nc}]);\n`;
        }
      }
    } else if (op.kind === "measure") {
      out += `        mz(q[${op.qubits[0] ?? 0}]);\n`;
    } else if (op.kind === "reset") {
      out += `        reset(q[${op.qubits[0] ?? 0}]);\n`;
    }
  }

  out += `    }\n`;
  out += `};\n\n`;
  out += `int main() {\n`;
  out += `    auto counts = cudaq::sample(quantum_circuit{});\n`;
  out += `    std::cout << "Measurement Distribution:\\n";\n`;
  out += `    counts.dump();\n`;
  out += `    return 0;\n`;
  out += `}\n`;

  return out;
}

/* -------------------------------------------------------------------------- */
/* 7. NVIDIA CUDA-Q Python Generator                                          */
/* -------------------------------------------------------------------------- */
export function generateCudaQPy(ir: CircuitIR, shots = 1024): string {
  let out = `"""Generated by QuantumLearn - NVIDIA CUDA-Q (Python)."""\n\n`;
  out += `import cudaq\n\n`;
  out += `kernel = cudaq.make_kernel()\n`;
  out += `q = kernel.qalloc(${ir.n_qubits})\n\n`;

  for (const op of sortOps(ir.ops)) {
    if (op.kind === "gate") {
      const g = (op.gate || "x").toLowerCase();
      const posCtrls = op.controls || [];
      const negCtrls = op.neg_controls || [];
      const targets = op.qubits || [0];
      const hasNeg = negCtrls.length > 0;

      if (hasNeg) {
        for (const nc of negCtrls) {
          out += `kernel.x(q[${nc}])\n`;
        }
      }

      const allCtrls = [...posCtrls, ...negCtrls];

      if (g === "swap") {
        const q0 = targets[0] ?? 0;
        const q1 = targets[1] ?? (q0 === 0 ? 1 : 0);
        out += `kernel.swap(q[${q0}], q[${q1}])\n`;
      } else if (allCtrls.length === 1) {
        if (g === "x" || g === "cx") {
          out += `kernel.cx(q[${allCtrls[0]}], q[${targets[0]}])\n`;
        } else if (g === "z" || g === "cz") {
          out += `kernel.cz(q[${allCtrls[0]}], q[${targets[0]}])\n`;
        } else if (g === "y" || g === "cy") {
          out += `kernel.cy(q[${allCtrls[0]}], q[${targets[0]}])\n`;
        } else if (g === "h" || g === "ch") {
          out += `kernel.ch(q[${allCtrls[0]}], q[${targets[0]}])\n`;
        } else {
          out += `kernel.cx(q[${allCtrls[0]}], q[${targets[0]}])\n`;
        }
      } else if (allCtrls.length > 1) {
        out += `kernel.mcx([${allCtrls.map((c) => `q[${c}]`).join(", ")}], q[${targets[0]}])\n`;
      } else if (op.params && op.params.length > 0) {
        const angle = formatAngle(op.params[0].expr);
        out += `kernel.${g}(${angle}, q[${targets[0]}])\n`;
      } else {
        out += `kernel.${g}(q[${targets[0]}])\n`;
      }

      if (hasNeg) {
        for (const nc of negCtrls) {
          out += `kernel.x(q[${nc}])\n`;
        }
      }
    } else if (op.kind === "measure") {
      out += `kernel.mz(q[${op.qubits[0] ?? 0}])\n`;
    }
  }

  out += `\n# Sample on GPU\n`;
  out += `result = cudaq.sample(kernel, shots_count=${shots})\n`;
  out += `print("CUDA-Q Results:")\n`;
  out += `print(result)\n`;

  return out;
}

/* -------------------------------------------------------------------------- */
/* 8. Circuit IR (JSON) Generator                                             */
/* -------------------------------------------------------------------------- */
export function generateCircuitIRJson(ir: CircuitIR): string {
  return JSON.stringify(ir, null, 2);
}

/* -------------------------------------------------------------------------- */
/* Dispatcher & Actions                                                       */
/* -------------------------------------------------------------------------- */
export function generateCircuitCode(
  targetId: string,
  ir: CircuitIR,
  circuitName = "circuit",
  shots = 1024
): { code: string; filename: string; mimeType: string } {
  const baseName = sanitizeName(circuitName || ir.name);
  const target = EXPORT_TARGETS.find((t) => t.id === targetId) || EXPORT_TARGETS[0];

  let code = "";
  let filename = `${baseName}${target.ext}`;

  switch (target.id) {
    case "qasm":
      code = generateQasm3(ir);
      filename = `${baseName}.qasm`;
      break;
    case "qiskit":
      code = generateQiskit(ir, shots);
      filename = `${baseName}_qiskit.py`;
      break;
    case "cirq":
      code = generateCirq(ir, shots);
      filename = `${baseName}_cirq.py`;
      break;
    case "pennylane":
      code = generatePennyLane(ir, shots);
      filename = `${baseName}_pennylane.py`;
      break;
    case "qbraid":
      code = generateQBraid(ir, shots);
      filename = `${baseName}_qbraid.py`;
      break;
    case "cudaq_cpp":
      code = generateCudaQCpp(ir);
      filename = `${baseName}_cudaq.cpp`;
      break;
    case "cudaq_py":
      code = generateCudaQPy(ir, shots);
      filename = `${baseName}_cudaq.py`;
      break;
    case "json":
      code = generateCircuitIRJson(ir);
      filename = `${baseName}_ir.json`;
      break;
    default:
      code = generateQasm3(ir);
      filename = `${baseName}.qasm`;
  }

  return { code, filename, mimeType: target.mimeType };
}

/**
 * Triggers a real browser file download with the circuit code.
 */
export function downloadCircuitFile(
  targetId: string,
  ir: CircuitIR,
  circuitName = "circuit",
  shots = 1024
): string {
  const { code, filename, mimeType } = generateCircuitCode(targetId, ir, circuitName, shots);
  const blob = new Blob([code], { type: `${mimeType};charset=utf-8` });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  return filename;
}

/**
 * Copies the generated circuit code to clipboard.
 */
export async function copyCircuitCode(
  targetId: string,
  ir: CircuitIR,
  circuitName = "circuit",
  shots = 1024
): Promise<string> {
  const { code } = generateCircuitCode(targetId, ir, circuitName, shots);
  await navigator.clipboard.writeText(code);
  const target = EXPORT_TARGETS.find((t) => t.id === targetId);
  return target?.framework || "Circuit";
}
