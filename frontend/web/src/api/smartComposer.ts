import { api } from "./client";

export interface TransformationRule {
  id: string;
  name: string;
  category: string;
  mathematical_formula: string;
  description: string;
  preconditions: string[];
  applicable_gates: string[];
  verified: boolean;
}

export interface CircuitMetrics {
  n_qubits: number;
  total_gates: number;
  depth: number;
  two_qubit_gates: number;
  gate_counts: Record<string, number>;
  estimated_fidelity: number;
  circuit_hash: string;
}

export interface VerificationReport {
  status:
    | "verified"
    | "state_prep_verified"
    | "distribution_match"
    | "equivalence_failed"
    | "unverified"
    | "timeout"
    | "unsupported_dynamic";
  tier: "tier_a_unitary" | "tier_b_state" | "tier_c_measurement" | "tier_d_certified";
  tolerance: number;
  global_phase_difference_rad?: number | null;
  fidelity?: number | null;
  tvd?: number | null;
  details: string;
  is_equivalent: boolean;
  is_universal_proof?: boolean;
  evidential_strength?: string;
}

export interface SimplificationResult {
  job_id: string;
  original_circuit: any;
  simplified_circuit: any;
  original_metrics: CircuitMetrics;
  simplified_metrics: CircuitMetrics;
  applied_rules: TransformationRule[];
  verification: VerificationReport;
  improvements: {
    gate_reduction_count?: number;
    gate_reduction_pct?: number;
    depth_reduction_count?: number;
    depth_reduction_pct?: number;
    two_qubit_reduction_count?: number;
    two_qubit_reduction_pct?: number;
    fidelity_gain?: number;
  };
  accepted: boolean;
  explanation: string;
  repair_attempts: number;
  warnings: string[];
}

export interface GenerationTaskSpec {
  prompt: string;
  target_qubits?: number | null;
  allowed_gates?: string[] | null;
  max_depth?: number | null;
  desired_state?: string | null;
}

export interface GenerationResult {
  circuit: any;
  metrics: CircuitMetrics;
  task_spec: GenerationTaskSpec;
  passed_tests: string[];
  assumptions: string[];
  repair_attempts: number;
  explanation: string;
}

export const smartComposerApi = {
  getRules: () => api.get<TransformationRule[]>("/smart-composer/rules"),
  generate: (spec: GenerationTaskSpec) =>
    api.post<GenerationResult>("/smart-composer/generate", spec),
  simplify: (ir: any, objective = "min_gates") =>
    api.post<SimplificationResult>("/smart-composer/simplify", {
      circuit_ir: ir,
      objective,
    }),
  getJobStatus: (jobId: string) =>
    api.get<any>(`/smart-composer/jobs/${jobId}`),
};
