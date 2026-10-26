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
    ],
  };
}

export function ghz(n = 3): CircuitIR {
  const ops = [makeOp("gate", { gate: "h", qubits: [0], layer: 0 })];
  for (let i = 0; i < n - 1; i++) {
    ops.push(makeOp("gate", { gate: "x", qubits: [i + 1], controls: [i], layer: i + 1 }));
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
  reset: (ir?: CircuitIR, name?: string) => void;
  setQubits: (n: number) => void;
  setCircuitId: (id?: string) => void;
  setCircuitName: (name?: string) => void;
  setChallengeContext: (ctx?: ChallengeContext) => void;
}

export function normalizeCircuit(ir?: CircuitIR | null): CircuitIR {
  if (!ir) return emptyCircuit(2);
  return {
    ...ir,
    name: ir.name ?? "circuit",
    n_qubits: ir.n_qubits ?? 2,
    n_clbits: ir.n_clbits ?? ir.n_qubits ?? 2,
    ops: (ir.ops || []).map((op) => ({
      ...op,
      qubits: Array.isArray(op.qubits) ? [...op.qubits] : [],
      controls: Array.isArray(op.controls) ? [...op.controls] : [],
      neg_controls: Array.isArray(op.neg_controls) ? [...op.neg_controls] : [],
      params: Array.isArray(op.params) ? [...op.params] : [],
      clbits: Array.isArray(op.clbits) ? [...op.clbits] : [],
      body: Array.isArray(op.body) ? [...op.body] : [],
      else_body: Array.isArray(op.else_body) ? [...op.else_body] : [],
    })),
  };
}

export const useCircuit = create<CircuitState>()((set) => ({
  ir: bell(),
  epoch: 0,
  circuitId: undefined,
  circuitName: "Bell State",
  challengeContext: undefined,
  setIr: (ir) => set((state) => ({ ir: normalizeCircuit(ir), epoch: state.epoch + 1 })),
  reset: (ir, name) =>
    set((state) => {
      const nextIr = normalizeCircuit(ir ?? emptyCircuit(state.ir.n_qubits));
      let derivedName = name;
      if (!derivedName) {
        if (nextIr.name === "bell") derivedName = "Bell State";
        else if (nextIr.name?.startsWith("ghz")) derivedName = `${nextIr.n_qubits}-Qubit GHZ`;
        else if (nextIr.name === "w_state") derivedName = "W State";
        else if (nextIr.name?.startsWith("qft")) derivedName = `${nextIr.n_qubits}-Qubit QFT`;
        else derivedName = nextIr.ops.length > 0 ? `${nextIr.n_qubits}-Qubit Circuit` : "Untitled Circuit";
      }
      return {
        ir: nextIr,
        circuitName: derivedName,
        epoch: state.epoch + 1,
      };
    }),
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
