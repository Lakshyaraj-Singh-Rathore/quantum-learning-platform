import { api } from "./client";
import type { CircuitIR } from "@composer/types";

/** Mirrors the /codelab endpoints in backend/app/api/jobs.py. */

export interface Finding {
  line: number;
  column: number;
  message: string;
}

export interface CheckResult {
  findings: Finding[];
  /** The source with `# ^^^ message` markers under each offending line. */
  annotated: string;
}

export interface StartersResponse {
  frameworks: string[];
  starters: Record<string, string>;
}

export interface BuildResult {
  circuit_ir: CircuitIR;
  qasm3: string;
  stdout: string;
  is_dynamic: boolean;
  n_qubits: number;
  depth: number;
}

export const FRAMEWORK_LABELS: Record<string, string> = {
  qiskit: "Qiskit",
  cirq: "Cirq",
  pennylane: "PennyLane",
  qasm3: "OpenQASM 3",
  qbraid: "qBraid",
  cudaq: "CUDA-Q",
};

/** Which CodeMirror language to load; QASM has no grammar of its own yet. */
export const FRAMEWORK_LANGUAGE: Record<string, "python" | "text"> = {
  qasm3: "text",
};

/**
 * Static checks, run server-side so the rules live in exactly one place.
 * Nothing here executes the learner's program — it is a syntax/import pass
 * meant to run while they type.
 */
export function checkCode(code: string, framework: string): Promise<CheckResult> {
  return api.post<CheckResult>("/codelab/check", { code, framework });
}

export function starters(): Promise<StartersResponse> {
  return api.get<StartersResponse>("/codelab/starters");
}

export function buildCircuit(code: string, framework: string): Promise<BuildResult> {
  return api.post<BuildResult>("/codelab/build", { code, framework });
}

/** Gemini drafts source; it never runs it. See the note on the page. */
export function generateCode(prompt: string, framework: string): Promise<{ code: string }> {
  return api.post<{ code: string }>("/codelab/generate", { prompt, framework });
}
