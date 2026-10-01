/**
 * The session circuit, shared across pages.
 *
 * Streamlit kept one circuit in st.session_state, so a circuit built inside a
 * lesson was still there when the learner opened the Composer, and the
 * Challenges page could submit "your current circuit". This store is that same
 * idea: one circuit, owned by whoever is editing it, visible to everyone who
 * needs to read it.
 *
 * It lives here rather than in ComposerPage because three places use it: the
 * Composer, the lesson demos (which embed the real grid), and the coding
 * challenges (which submit it).
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

export function emptyCircuit(n = 2): CircuitIR {
  return { name: "circuit", n_qubits: n, n_clbits: n, ops: [] };
}

interface CircuitState {
  ir: CircuitIR;
  /**
   * Bumped to remount the grid. It is uncontrolled once mounted — it owns its
   * own edit state — so a programmatic reset remounts it rather than fighting
   * it.
   */
  epoch: number;
  setIr: (ir: CircuitIR) => void;
  reset: (ir?: CircuitIR) => void;
}

export const useCircuit = create<CircuitState>()((set) => ({
  ir: bell(),
  epoch: 0,
  setIr: (ir) => set({ ir }),
  reset: (ir) => set((state) => ({ ir: ir ?? emptyCircuit(state.ir.n_qubits), epoch: state.epoch + 1 })),
}));

/**
 * Identity of a circuit, ignoring op ids.
 *
 * Op ids are regenerated every time the IR is rebuilt, so comparing raw
 * dictionaries would report a change on every keystroke and throw away results
 * that are still valid.
 */
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
