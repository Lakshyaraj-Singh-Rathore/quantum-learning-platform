/**
 * Which single-qubit gates a playground circuit applies to qubit 0.
 *
 * The playground models ONE qubit, so anything the composer allows that does
 * not act on qubit 0 alone -- two-qubit gates, measurements, control-flow
 * blocks -- is reported as skipped rather than silently ignored. A learner who
 * drops a CNOT and sees nothing happen would reasonably conclude the demo is
 * broken.
 *
 * Ported from frontend/lib/playground.py::gates_from_ir.
 */
import { GATES } from "./demos";
import type { CircuitIR } from "@composer/types";

export function gatesFromIr(ir: CircuitIR, qubit = 0): { applied: string[]; skipped: string[] } {
  const applied: string[] = [];
  const skipped: string[] = [];

  for (const op of ir.ops ?? []) {
    if (op.kind !== "gate") {
      skipped.push(op.kind || "?");
      continue;
    }
    const name = (op.gate || "").toUpperCase();
    const qubits = op.qubits ?? [];
    const controls = op.controls ?? [];
    if (controls.length > 0 || qubits.length !== 1 || qubits[0] !== qubit) {
      skipped.push(name ? name.toLowerCase() : "?");
      continue;
    }
    if (!(name in GATES)) {
      skipped.push(name.toLowerCase());
      continue;
    }
    applied.push(name);
  }
  return { applied, skipped };
}
