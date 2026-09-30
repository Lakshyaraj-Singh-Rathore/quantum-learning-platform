import { api } from "./client";
import type { CircuitIR } from "@composer/types";

/** Mirrors backend/app/schemas/job.py and app/quantum/backends/base.py. */

export interface NoiseIn {
  enabled: boolean;
  t1_us: number;
  t2_us: number;
  readout_error: number;
  gate_time_1q_us: number;
  gate_time_2q_us: number;
  gate_time_3q_us: number;
}

export interface JobOut {
  id: number;
  status: string;
  backend: string;
  mode: string;
  shots: number;
  error: string | null;
}

export interface RunMetadata {
  backend: string;
  shots: number;
  n_qubits: number;
  runtime_seconds: number;
  bit_order: string;
  warnings: string[];
  [key: string]: unknown;
}

export interface RunResult {
  counts: Record<string, number>;
  probabilities: Record<string, number>;
  statevector: [number, number][] | null;
  metadata: RunMetadata;
}

export interface JobResultOut {
  id: number;
  status: string;
  result: RunResult | null;
  error: string | null;
}

export interface InspectReport {
  ok: boolean;
  errors: string[];
  warnings: string[];
  summary: Record<string, unknown>;
}

export function inspectCircuit(
  circuit_ir: CircuitIR,
  backend?: string,
  shots?: number,
): Promise<InspectReport> {
  return api.post<InspectReport>("/inspect", { circuit_ir, backend, shots });
}

export function submitJob(args: {
  circuit_ir: CircuitIR;
  backend: string;
  shots: number;
  mode?: string;
  noise?: NoiseIn | null;
}): Promise<JobOut> {
  const { circuit_ir, backend, shots, mode = "auto", noise = null } = args;
  return api.post<JobOut>("/jobs", { circuit_ir, backend, shots, mode, noise });
}

export function jobStatus(id: number): Promise<JobOut> {
  return api.get<JobOut>(`/jobs/${id}`);
}

export function jobResult(id: number): Promise<JobResultOut> {
  return api.get<JobResultOut>(`/jobs/${id}/result`);
}
