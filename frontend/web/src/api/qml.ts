/* Quantum ML Lab API client.
 *
 * Built on `./client`, like every other module here: it throws
 * `ApiError{status, detail}` and already formats FastAPI's three `detail`
 * shapes through `readableError()`, so a 422 from the config validator
 * arrives as readable text rather than `[object Object]`. No raw `fetch`, so
 * the token always comes from the session store and a 401 always means the
 * same thing.
 */
import { api } from "./client";

/* -------------------------------------------------------------------------- */
/* Config — mirrors backend QmlExperimentConfig exactly (extra="forbid")       */
/* -------------------------------------------------------------------------- */

export type DatasetName = "moons" | "circles" | "iris_binary";
export type Rotation = "X" | "Y" | "Z";
export type Entanglement = "ring" | "linear" | "none";
export type DiffMethod = "backprop" | "parameter-shift";

export interface DatasetConfig {
  name: DatasetName;
  n_samples: number;
  noise: number;
  test_fraction: number;
}

export interface CircuitConfig {
  n_qubits: number;
  n_layers: number;
  rotation: Rotation;
  entanglement: Entanglement;
}

export interface TrainingConfig {
  epochs: number;
  batch_size: number;
  learning_rate: number;
  diff_method: DiffMethod;
}

export interface QmlConfig {
  seed: number;
  dataset: DatasetConfig;
  circuit: CircuitConfig;
  training: TrainingConfig;
}

/* -------------------------------------------------------------------------- */
/* Server-described capabilities — the UI must not hardcode limits            */
/* -------------------------------------------------------------------------- */

export interface LimitRange {
  default: number;
  min: number;
  max: number;
}

export interface QmlDescribe {
  limits: Record<string, LimitRange>;
  datasets: { name: DatasetName; max_samples: number; n_features: number }[];
  diff_methods: DiffMethod[];
  rotations: Rotation[];
  entanglements: Entanglement[];
  device: string;
  max_concurrent_experiments: number;
  statuses: string[];
}

/* -------------------------------------------------------------------------- */
/* Experiments                                                                 */
/* -------------------------------------------------------------------------- */

export type ExperimentStatus =
  | "queued"
  | "running"
  | "completed"
  | "failed"
  | "cancelled"
  | "timed_out";

/** Nothing further will happen to an experiment in one of these states.
 *  This is the set the dashboard's poll stops on. */
export const TERMINAL_STATUSES: readonly ExperimentStatus[] = [
  "completed",
  "failed",
  "cancelled",
  "timed_out",
];

export function isTerminal(status: string | undefined): boolean {
  return status !== undefined && (TERMINAL_STATUSES as readonly string[]).includes(status);
}

export interface EpochRow {
  epoch: number;
  train_loss: number;
  train_accuracy: number;
  test_loss: number | null;
  test_accuracy: number | null;
  elapsed_seconds: number;
}

export interface Evaluation {
  accuracy: number;
  precision: number;
  recall: number;
  f1: number;
  confusion_matrix: number[][];
  n_samples: number;
}

export interface Baseline {
  model: string;
  train_accuracy: number;
  test_accuracy: number;
  n_parameters: number;
  converged: boolean;
}

export interface ExperimentResult {
  evaluation: Evaluation;
  baseline: Baseline;
  circuit: Record<string, unknown>;
  dataset: Record<string, unknown>;
  epochs_completed: number;
  duration_seconds: number;
  final_train_loss: number | null;
  final_train_accuracy: number | null;
  /** Present instead of the above when a run was cancelled or timed out. */
  interrupted?: boolean;
  reason?: string;
}

export interface Experiment {
  id: number;
  status: ExperimentStatus;
  config: QmlConfig;
  error: string | null;
  cached: boolean;
}

export interface ExperimentDetail extends Experiment {
  history: EpochRow[];
  result: ExperimentResult | null;
  epochs_recorded: number;
}

export interface ResultPayload {
  id: number;
  status: ExperimentStatus;
  result: ExperimentResult | null;
  history: EpochRow[];
  error: string | null;
}

export interface InferenceResult {
  predictions: number[];
  probabilities: number[];
  feature_names: string[];
  n_features: number;
}

/* -------------------------------------------------------------------------- */
/* Calls                                                                       */
/* -------------------------------------------------------------------------- */

export function describeQml(): Promise<QmlDescribe> {
  return api.get<QmlDescribe>("/qml/describe");
}

export function createExperiment(config: QmlConfig): Promise<Experiment> {
  return api.post<Experiment>("/qml/experiments", config);
}

export function listExperiments(limit = 20): Promise<Experiment[]> {
  return api.get<Experiment[]>(`/qml/experiments?limit=${limit}`);
}

/** Poll target for the training dashboard.
 *
 *  `afterEpoch` makes it incremental — the dashboard asks only for epochs it
 *  has not already drawn, instead of re-downloading the whole curve every
 *  tick.
 */
export function getExperiment(id: number, afterEpoch = 0): Promise<ExperimentDetail> {
  return api.get<ExperimentDetail>(`/qml/experiments/${id}?after_epoch=${afterEpoch}`);
}

export function getExperimentResult(id: number): Promise<ResultPayload> {
  return api.get<ResultPayload>(`/qml/experiments/${id}/result`);
}

export function cancelExperiment(id: number): Promise<Experiment> {
  return api.post<Experiment>(`/qml/experiments/${id}/cancel`);
}

export function runInference(id: number, features: number[][]): Promise<InferenceResult> {
  return api.post<InferenceResult>(`/qml/experiments/${id}/inference`, { features });
}

/* -------------------------------------------------------------------------- */
/* Defaults                                                                    */
/* -------------------------------------------------------------------------- */

/** Starting point for the config form.
 *
 *  Deliberately conservative and fast (2 qubits, 10 epochs, 200 samples) so a
 *  first run finishes in seconds rather than minutes. Real bounds come from
 *  `/qml/describe` at runtime; these are only the initial values.
 */
export const DEFAULT_CONFIG: QmlConfig = {
  seed: 42,
  dataset: { name: "moons", n_samples: 200, noise: 0.15, test_fraction: 0.3 },
  circuit: { n_qubits: 2, n_layers: 2, rotation: "Y", entanglement: "ring" },
  training: { epochs: 10, batch_size: 16, learning_rate: 0.1, diff_method: "backprop" },
};
