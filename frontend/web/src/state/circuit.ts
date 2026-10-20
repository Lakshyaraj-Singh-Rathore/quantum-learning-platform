/**
 * The session circuit, shared across pages.
 *
 * Streamlit kept one circuit in st.session_state, so a circuit built inside a
 * lesson was still there when the learner opened the Composer, and the
 * Challenges page could submit "your current circuit". This store is that same
 * idea: one circuit, owned by whoever is editing it, visible to everyone who
 * needs to read it.
 *
 * Extended with Phase 2 presets and stubs for challengeContext and saved circuits.
 */
import { create } from "zustand";
import { makeOp } from "@composer/ir";
import type { CircuitIR } from "@composer/types";

export function bell(): CircuitIR {
  return {
    name: "bell",
    n_qubits: 2,
    n_clbits: 2,
    ops: [
      makeOp("gate", { gate: "h", qubits: [0], layer: 0 }),
      makeOp("gate", { gate: "x", qubits: [1], controls: [0], layer: 1 }),
      makeOp("measure", { qubits: [0], clbits: [0], layer: 2 }),
      makeOp("measure", { qubits: [1], clbits: [1], layer: 2 }),
    ],
  };
}

export function ghz(n = 3): CircuitIR {
  const ops = [makeOp("gate", { gate: "h", qubits: [0], layer: 0 })];
  for (let i = 0; i < n - 1; i++) {
    ops.push(makeOp("gate", { gate: "x", qubits: [i + 1], controls: [i], layer: i + 1 }));
  }
  for (let i = 0; i < n; i++) {
    ops.push(makeOp("measure", { qubits: [i], clbits: [i], layer: n }));
  }
  return { name: `ghz_${n}`, n_qubits: n, n_clbits: n, ops };
}

export function wState(): CircuitIR {
  return {
    name: "w_state",
    n_qubits: 3,
    n_clbits: 3,
    ops: [
      makeOp("gate", { gate: "ry", qubits: [0], params: [{ expr: "1.9106", value: 1.9106 }], layer: 0 }),
      makeOp("gate", { gate: "x", qubits: [1], controls: [0], layer: 1 }),
      makeOp("gate", { gate: "h", qubits: [0], layer: 2 }),
      makeOp("gate", { gate: "x", qubits: [2], controls: [1], layer: 3 }),
      makeOp("measure", { qubits: [0], clbits: [0], layer: 4 }),
      makeOp("measure", { qubits: [1], clbits: [1], layer: 4 }),
      makeOp("measure", { qubits: [2], clbits: [2], layer: 4 }),
    ],
  };
}

export function qft3(): CircuitIR {
  return {
    name: "qft_3",
    n_qubits: 3,
    n_clbits: 3,
    ops: [
      makeOp("gate", { gate: "h", qubits: [0], layer: 0 }),
      makeOp("gate", { gate: "s", qubits: [0], controls: [1], layer: 1 }),
      makeOp("gate", { gate: "t", qubits: [0], controls: [2], layer: 2 }),
      makeOp("gate", { gate: "h", qubits: [1], layer: 3 }),
      makeOp("gate", { gate: "s", qubits: [1], controls: [2], layer: 4 }),
      makeOp("gate", { gate: "h", qubits: [2], layer: 5 }),
      makeOp("measure", { qubits: [0], clbits: [0], layer: 6 }),
      makeOp("measure", { qubits: [1], clbits: [1], layer: 6 }),
      makeOp("measure", { qubits: [2], clbits: [2], layer: 6 }),
    ],
  };
}

export function emptyCircuit(n = 2): CircuitIR {
  return { name: "circuit", n_qubits: n, n_clbits: n, ops: [] };
}

export interface ChallengeContext {
  challengeId: string;
  title: string;
  returnPath: string;
}

export interface CircuitState {
  ir: CircuitIR;
  epoch: number;
  circuitId?: string;
  circuitName?: string;
  challengeContext?: ChallengeContext;
  setIr: (ir: CircuitIR) => void;
  reset: (ir?: CircuitIR) => void;
  setQubits: (n: number) => void;
  setCircuitId: (id?: string) => void;
  setCircuitName: (name?: string) => void;
  setChallengeContext: (ctx?: ChallengeContext) => void;
}

export const useCircuit = create<CircuitState>()((set) => ({
  ir: bell(),
  epoch: 0,
  circuitId: undefined,
  circuitName: "Bell State",
  challengeContext: undefined,
  setIr: (ir) => set({ ir }),
  reset: (ir) =>
    set((state) => ({
      ir: ir ?? emptyCircuit(state.ir.n_qubits),
      epoch: state.epoch + 1,
    })),
  setQubits: (n: number) =>
    set((state) => {
      const validN = Math.max(1, Math.min(20, n));
      // filter out operations on qubits >= validN
      const validOps = state.ir.ops.filter(
        (op) =>
          op.qubits.every((q) => q < validN) &&
          (!op.controls || op.controls.every((c) => c < validN))
      );
      return {
        ir: {
          ...state.ir,
          n_qubits: validN,
          n_clbits: validN,
          ops: validOps,
        },
        epoch: state.epoch + 1,
      };
    }),
  setCircuitId: (circuitId) => set({ circuitId }),
  setCircuitName: (circuitName) => set({ circuitName }),
  setChallengeContext: (challengeContext) => set({ challengeContext }),
}));

function stripIds(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(stripIds);
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>)
        .filter(([key]) => key !== "id")
        .map(([key, nested]) => [key, stripIds(nested)]),
    );
  }
  return value;
}

export function circuitStamp(ir: CircuitIR): string {
  return JSON.stringify(stripIds(ir));
}
