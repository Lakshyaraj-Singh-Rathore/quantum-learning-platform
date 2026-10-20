/** API client and type definitions for Qudit Lab (Beta). */

import { api } from "./client";

export interface QuditWire {
  id: string;
  index: number;
  dimension: number;
  initial_state: number;
  label?: string | null;
}

export interface QuditOp {
  id: string;
  gate: string;
  targets: number[];
  controls: number[];
  params: Record<string, number>;
  dimension: number;
}

export interface DepolarizingNoiseConfig {
  enabled: boolean;
  p: number;
}

export interface DephasingNoiseConfig {
  enabled: boolean;
  gamma: number;
}

export interface RelaxationNoiseConfig {
  enabled: boolean;
  gamma: number;
}

export interface QuditNoiseConfig {
  depolarizing: DepolarizingNoiseConfig;
  dephasing: DephasingNoiseConfig;
  relaxation: RelaxationNoiseConfig;
}

export interface QuditCircuit {
  version: string;
  id: string;
  name: string;
  dimension: number;
  wires: QuditWire[];
  ops: QuditOp[];
}

export interface ResourceEstimate {
  dimensions: number[];
  total_dim: number;
  raw_density_matrix_bytes: number;
  estimated_peak_bytes: number;
  within_budget: boolean;
  budget_bytes: number;
  max_qudits_allowed: number;
  message: string;
}

export interface CircuitValidationReport {
  valid: boolean;
  errors: string[];
  warnings: string[];
  resource_estimate?: ResourceEstimate | null;
}

export interface ComplexVal {
  real: number;
  imag: number;
  mag: number;
  phase: number;
}

export interface StateValidation {
  is_valid: boolean;
  trace: number;
  trace_residual: number;
  hermiticity_residual: number;
  is_hermitian: boolean;
  min_eigenvalue: number;
  is_positive_semidefinite: boolean;
  purity: number;
  entropy?: number | null;
  diagnostics: string[];
}

export interface ReducedStateResult {
  wire_index: number;
  dimension: number;
  density_matrix: ComplexVal[][];
  purity: number;
  entropy?: number | null;
  populations: number[];
}

export interface SimulationRequest {
  circuit: QuditCircuit;
  noise?: QuditNoiseConfig | null;
  shots?: number | null;
  seed?: number | null;
  calculate_entropy?: boolean;
  density_matrix_max_dim?: number;
}

export interface SimulationResult {
  circuit_id: string;
  dimension: number;
  n_qudits: number;
  total_dim: number;
  basis_labels: string[];
  populations: Record<string, number>;
  coherences: Record<string, number>;
  probabilities: Record<string, number>;
  samples?: Record<string, number> | null;
  state_validation: StateValidation;
  density_matrix?: ComplexVal[][] | null;
  density_matrix_truncated: boolean;
  reduced_states: Record<string, ReducedStateResult>;
  execution_time_ms: number;
  memory_estimate_bytes: number;
  noisy: boolean;
  warnings: string[];
}

export interface GateParamDef {
  name: string;
  label: string;
  default: number;
  min: number;
  max: number;
  step: number;
}

export interface QuditGateCatalogueItem {
  id: string;
  name: string;
  symbol: string;
  description: string;
  latex: string;
  num_qudits: number;
  is_two_qudit: boolean;
  has_controls: boolean;
  parameters: GateParamDef[];
}

export interface EducationalPreset {
  id: string;
  title: string;
  category: string;
  dimension: number;
  description: string;
  circuit: QuditCircuit;
  noise?: QuditNoiseConfig | null;
}

export interface QuditLimits {
  safe_limits: Record<string, number>;
  expanded_limits: Record<string, number>;
  supported_dimensions: number[];
  default_budget_bytes: number;
  memory_formula: string;
  description: string;
}

export interface MatrixSliceRequest {
  circuit: QuditCircuit;
  noise?: QuditNoiseConfig | null;
  row_start: number;
  row_count: number;
  col_start: number;
  col_count: number;
}

export interface MatrixSliceResponse {
  total_dim: number;
  row_start: number;
  row_count: number;
  col_start: number;
  col_count: number;
  basis_rows: string[];
  basis_cols: string[];
  elements: ComplexVal[][];
}

export const quditLabApi = {
  getLimits: () => api.get<QuditLimits>("/qudit/limits"),
  getCatalogue: () => api.get<QuditGateCatalogueItem[]>("/qudit/catalogue"),
  getPresets: (dimension = 3) => api.get<EducationalPreset[]>(`/qudit/presets?dimension=${dimension}`),
  validateCircuit: (circuit: QuditCircuit) => api.post<CircuitValidationReport>("/qudit/validate", circuit),
  simulate: (payload: SimulationRequest) => api.post<SimulationResult>("/qudit/simulate", payload),
  getMatrixSlice: (payload: MatrixSliceRequest) => api.post<MatrixSliceResponse>("/qudit/slice", payload),
};
