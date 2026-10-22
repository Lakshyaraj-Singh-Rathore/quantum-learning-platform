/* Build a CircuitIR from a QML config so view B can reuse the existing
 * `components/results/CircuitDiagram.tsx` rather than drawing a second,
 * slightly-different circuit renderer.
 *
 * The layout mirrors the backend ansatz in `app/quantum/qml_lab/circuit.py`:
 *
 *   encoding layer   : one rotation per wire carrying the feature angle
 *   per variational layer:
 *       RY then RZ on every wire   (2 trainable params per wire per layer)
 *       entangler                  (ring | linear | none)
 *
 * so `n_params = n_layers * n_qubits * 2`. The trainable bias is counted
 * separately by the backend (`limits.py:106-113`) because it is classical and
 * has no gate, so it is neither drawn nor counted here. The ring entangler
 * deliberately skips the wrap-around CNOT at n_qubits == 2, where it would
 * duplicate the chain's only link (`circuit.py:38-40`).
 *
 * This is a *preview*: it shows structure, not the trained angles. It must
 * stay in step with the backend builder, which is why the parameter count it
 * implies is asserted against the server's own figure in the results view.
 */
import type { CircuitIR, Op, Param } from "@composer/types";
import type { CircuitConfig } from "../../api/qml";

let seq = 0;
const nextId = () => `qml-${(seq += 1)}`;

/** The fields every Op carries regardless of kind.
 *
 *  `body`/`else_body`/`loop_var`/`loop_value` are required by the composer's
 *  `Op` even for a plain gate, because the same type also describes `if`,
 *  `for` and `while` blocks. They are filled with their empty values rather
 *  than cast away: a `Partial<Op>` cast here would mean the next field the
 *  composer adds compiles silently and renders wrong. */
const EMPTY_OP = {
  neg_controls: [] as number[],
  inv: false,
  params: [] as Param[],
  body: [] as Op[],
  else_body: [] as Op[],
  loop_var: "",
  loop_value: 0,
  condition: null,
} as const;

function gate(name: string, qubits: number[], layer: number, controls: number[] = []): Op {
  return {
    ...EMPTY_OP,
    id: nextId(),
    kind: "gate",
    gate: name,
    qubits,
    controls,
    clbits: [],
    layer,
  };
}

/** Entangler pairs for one layer, matching the backend's topology exactly. */
export function entanglerPairs(nQubits: number, topology: string): [number, number][] {
  if (topology === "none" || nQubits < 2) return [];
  const pairs: [number, number][] = [];
  for (let q = 0; q < nQubits - 1; q += 1) pairs.push([q, q + 1]);
  // The wrap-around closes the ring, but at n=2 it is the same pair again.
  if (topology === "ring" && nQubits > 2) pairs.push([nQubits - 1, 0]);
  return pairs;
}

/** Circuit parameter count, excluding the classical bias — the exact
 *  definition used by `limits.n_parameters` (`limits.py:113`). The results
 *  view asserts this against the server's own figure so the preview cannot
 *  drift away from the ansatz without something going visibly red. */
export function parameterCount(nQubits: number, nLayers: number): number {
  return nLayers * nQubits * 2;
}

export function buildQmlCircuitIr(circuit: CircuitConfig, nFeatures: number): CircuitIR {
  seq = 0;
  const { n_qubits: nQubits, n_layers: nLayers, rotation, entanglement } = circuit;
  const ops: Op[] = [];
  let layer = 0;

  // --- feature encoding -----------------------------------------------------
  // Z-encoding needs a Hadamard first: RZ on |0> only changes a global phase,
  // which is unobservable, so the feature would be silently discarded.
  const encodeGate = `r${rotation.toLowerCase()}`;
  if (rotation === "Z") {
    for (let q = 0; q < Math.min(nFeatures, nQubits); q += 1) ops.push(gate("h", [q], layer));
    layer += 1;
  }
  for (let q = 0; q < Math.min(nFeatures, nQubits); q += 1) {
    ops.push(gate(encodeGate, [q], layer));
  }
  layer += 1;

  // --- variational layers ---------------------------------------------------
  for (let l = 0; l < nLayers; l += 1) {
    for (let q = 0; q < nQubits; q += 1) ops.push(gate("ry", [q], layer));
    layer += 1;
    for (let q = 0; q < nQubits; q += 1) ops.push(gate("rz", [q], layer));
    layer += 1;

    for (const [control, target] of entanglerPairs(nQubits, entanglement)) {
      // CNOT in this IR is an X with a control, which is how the composer's
      // grid and CircuitDiagram's GateGlyph both expect it.
      ops.push(gate("x", [target], layer, [control]));
      layer += 1;
    }
  }

  // --- readout --------------------------------------------------------------
  // The model reads <Z> on wire 0; the measure op makes that explicit.
  ops.push({
    ...EMPTY_OP,
    id: nextId(),
    kind: "measure",
    gate: null,
    qubits: [0],
    controls: [],
    clbits: [0],
    layer,
  });

  return {
    name: "qml-ansatz",
    n_qubits: nQubits,
    n_clbits: 1,
    ops,
  };
}
