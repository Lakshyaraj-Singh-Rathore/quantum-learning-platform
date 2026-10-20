import { api } from "./client";

export interface DecoherenceParams {
  enabled: boolean;
  t1_us: number;
  t2_us: number;
  t_phi_us?: number | null;
  gate_time_1q_us: number;
  gate_time_2q_us: number;
  gate_time_3q_us: number;
  excited_state_pop: number;
}

export interface StochasticParams {
  enabled: boolean;
  depolarizing_1q: number;
  depolarizing_2q: number;
  bit_flip: number;
  phase_flip: number;
  bit_phase_flip: number;
  reset_error: number;
}

export interface CoherentParams {
  enabled: boolean;
  over_rotation_1q_rad: number;
  over_rotation_2q_rad: number;
  phase_offset_rad: number;
}

export interface ReadoutParams {
  enabled: boolean;
  prob_1_given_0: number;
  prob_0_given_1: number;
}

export interface CorrelatedParams {
  enabled: boolean;
  zz_crosstalk_strength: number;
  correlated_depolarizing_2q: number;
}

export interface NoiseConfig {
  name: string;
  description: string;
  decoherence: DecoherenceParams;
  stochastic: StochasticParams;
  coherent: CoherentParams;
  readout: ReadoutParams;
  correlated: CorrelatedParams;
  simulation_method: string;
}

export interface NoiseCatalogueItem {
  id: string;
  category: string;
  name: string;
  parameter: string;
  unit: string;
  valid_range: string;
  formula: string;
  support_level: string;
  physical_origin: string;
  student_hint: string;
}

export interface NoiseMetrics {
  fidelity?: number | null;
  purity?: number | null;
  trace_distance?: number | null;
  total_variation_distance: number;
  entropy_bits?: number | null;
  is_exact_density_matrix: boolean;
}

export interface NoiseSimulationResult {
  circuit_name: string;
  n_qubits: number;
  shots: number;
  ideal_counts: Record<string, number>;
  noisy_counts: Record<string, number>;
  ideal_probabilities: Record<string, number>;
  noisy_probabilities: Record<string, number>;
  metrics: NoiseMetrics;
  applied_channels: string[];
  warnings: string[];
  method_used: string;
  density_matrix_sample?: { real: number; imag: number }[][] | null;
}

export interface ValidationReport {
  valid: boolean;
  errors: string[];
  warnings: string[];
  physical_checks: Record<string, any>;
}

export interface SweepPoint {
  value: number;
  fidelity?: number | null;
  purity?: number | null;
  tvd?: number | null;
  trace_distance?: number | null;
  error?: string;
}

export const noiseLabApi = {
  getCatalogue: () => api.get<NoiseCatalogueItem[]>("/noise/catalogue"),
  getPresets: () => api.get<Record<string, NoiseConfig>>("/noise/presets"),
  validate: (config: NoiseConfig, qubits?: number) =>
    api.post<ValidationReport>("/noise/validate", { noise_config: config, circuit_qubits: qubits }),
  simulate: (ir: any, config: NoiseConfig, shots = 1024, seed = 42) =>
    api.post<NoiseSimulationResult>("/noise/simulate", {
      circuit_ir: ir,
      noise_config: config,
      shots,
      seed,
    }),
  sweep: (ir: any, config: NoiseConfig, paramPath: string, startVal: number, endVal: number, steps = 6, shots = 512) =>
    api.post<SweepPoint[]>("/noise/sweep", {
      circuit_ir: ir,
      noise_config: config,
      param_path: paramPath,
      start_val: startVal,
      end_val: endVal,
      steps,
      shots,
    }),
};
