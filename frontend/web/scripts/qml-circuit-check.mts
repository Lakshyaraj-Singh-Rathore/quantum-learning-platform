/* Checks the circuit *preview* against the circuit that actually trains.
 *
 * The Circuit view builds its IR in TypeScript; the model it depicts is built
 * in Python. The fixture is captured off a real PennyLane tape by
 * scripts/qml-circuit-fixtures.py, so this is a genuine cross-language
 * comparison rather than two restatements of the same guess.
 *
 * It does NOT compare the two op lists index by index. PennyLane emits
 * Z-encoding as H(0),RZ(0),H(1),RZ(1) while the builder groups the Hadamards
 * first; single-qubit gates on different wires commute, so that difference is
 * not a defect and a positional diff would fail on it forever. What *is*
 * meaningful, and what is compared here:
 *
 *   1. the ordered sequence of operations on each individual wire, with
 *      control and target roles distinguished;
 *   2. the ordered list of two-qubit pairings;
 *   3. the parameter and entangler counts the backend reports.
 *
 * Two circuits agreeing on all three differ at most by reordering gates that
 * act on disjoint wires.
 *
 *   npx tsx scripts/qml-circuit-check.mts
 */
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { buildQmlCircuitIr, entanglerPairs, parameterCount } from "../src/components/qml/circuitIr.ts";
import type { Entanglement, Rotation } from "../src/api/qml.ts";

interface FixtureOp {
  gate: string;
  qubits: number[];
  controls: number[];
}

interface FixtureCase {
  n_qubits: number;
  n_layers: number;
  rotation: Rotation;
  entanglement: Entanglement;
  n_features: number;
  ops: FixtureOp[];
  describe: {
    n_parameters: number;
    entanglers_per_layer: number;
    rotations_per_layer: number;
  };
}

const fixturePath = fileURLToPath(
  new URL("../test-fixtures/qml-circuit-golden.json", import.meta.url),
);
const fixture = JSON.parse(readFileSync(fixturePath, "utf-8")) as { cases: FixtureCase[] };

/** PennyLane's operation names to the IR's gate names. */
const ALIAS: Record<string, string> = {
  hadamard: "h",
  paulix: "x",
  pauliy: "y",
  pauliz: "z",
  cnot: "x",
};

const norm = (gate: string | null | undefined) => {
  const g = (gate ?? "").toLowerCase();
  return ALIAS[g] ?? g;
};

let failures = 0;
let checks = 0;

function eq(name: string, actual: unknown, expected: unknown) {
  checks += 1;
  const a = JSON.stringify(actual);
  const e = JSON.stringify(expected);
  if (a !== e) {
    failures += 1;
    console.log(`FAIL  ${name}\n        got      ${a}\n        expected ${e}`);
  }
}

/** Per-wire op sequence: what this wire sees, in order, as target or control. */
function perWire(
  ops: { gate: string; qubits: number[]; controls: number[] }[],
  nQubits: number,
): string[][] {
  const wires: string[][] = Array.from({ length: nQubits }, () => []);
  for (const op of ops) {
    for (const q of op.qubits) wires[q]?.push(norm(op.gate));
    for (const c of op.controls) wires[c]?.push(`ctrl:${norm(op.gate)}`);
  }
  return wires;
}

function pairings(ops: { gate: string; qubits: number[]; controls: number[] }[]) {
  return ops
    .filter((o) => o.controls.length > 0)
    .map((o) => [o.controls[0], o.qubits[0]]);
}

for (const c of fixture.cases) {
  const label = `${c.n_qubits}q x ${c.n_layers}L R${c.rotation} ${c.entanglement} (${c.n_features}f)`;

  const ir = buildQmlCircuitIr(
    {
      n_qubits: c.n_qubits,
      n_layers: c.n_layers,
      rotation: c.rotation,
      entanglement: c.entanglement,
    },
    c.n_features,
  );

  // The measure op has no counterpart on the operations tape (it is the
  // expval), so it is excluded from the gate comparison and asserted on its
  // own below.
  const irGates = ir.ops
    .filter((o) => o.kind === "gate")
    .sort((a, b) => a.layer - b.layer)
    .map((o) => ({ gate: norm(o.gate), qubits: o.qubits, controls: o.controls }));

  eq(`${label} :: wire sequences`, perWire(irGates, c.n_qubits), perWire(c.ops, c.n_qubits));
  eq(`${label} :: entangler pairings`, pairings(irGates), pairings(c.ops));
  eq(`${label} :: gate count`, irGates.length, c.ops.length);

  eq(
    `${label} :: n_parameters`,
    parameterCount(c.n_qubits, c.n_layers),
    c.describe.n_parameters,
  );
  eq(
    `${label} :: entanglers per layer`,
    entanglerPairs(c.n_qubits, c.entanglement).length,
    c.describe.entanglers_per_layer,
  );

  // Readout is a single Z measurement on wire 0 — the model's only observable.
  const measures = ir.ops.filter((o) => o.kind === "measure");
  eq(`${label} :: one readout on wire 0`, measures.map((m) => m.qubits), [[0]]);
  eq(`${label} :: IR declares the right width`, [ir.n_qubits, ir.n_clbits], [c.n_qubits, 1]);
}

console.log(
  failures === 0
    ? `ALL CHECKS PASSED — ${checks} assertions across ${fixture.cases.length} circuits agree with the PennyLane tape`
    : `${failures} of ${checks} ASSERTIONS FAILED`,
);
process.exit(failures === 0 ? 0 : 1);
