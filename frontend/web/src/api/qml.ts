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

/** All six datasets the server accepts. The first three are classification
 *  sets and the last three regression ones; `TASK_BY_DATASET` on the server
 *  is the single registry, and `/qml/describe` serves the split per algorithm
 *  so the client never has to hardcode which is which. */
export type ClassificationDataset = "moons" | "circles" | "iris_binary";
export type RegressionDataset = "sine" | "damped_cosine" | "linear_mix";
export type DatasetName = ClassificationDataset | RegressionDataset;

export type AlgorithmName = "vqc" | "hybrid_qnn" | "quantum_kernel" | "quantum_regression";

/** The discriminant for every task-shaped payload below. */
export type QmlTask = "classification" | "regression";
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
  /** Hybrid only. Gated by `supports.n_hidden`, never by an algorithm name. */
  n_hidden?: number;
}

export interface TrainingConfig {
  epochs: number;
  batch_size: number;
  learning_rate: number;
  diff_method: DiffMethod;
}

export interface QmlConfig {
  seed: number;
  algorithm: AlgorithmName;
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

export interface DatasetOption {
  name: DatasetName;
  max_samples: number;
  n_features: number;
  /** Regression only: the angle frequency the ansatz must reach to fit this
   *  target (D-034). `null` for classification sets. */
  required_angle_frequency: number | null;
}

/** What an algorithm's form can offer. Read these instead of branching on
 *  `name` — a new algorithm should need no client change (§2E.0). */
export interface AlgorithmSupports {
  n_hidden: boolean;
  /** False for the kernel: one closed-form solve, so there is no epoch
   *  slider and no training curve. */
  epochs: boolean;
  diff_method: boolean;
  data_reuploading: boolean;
}

export interface AlgorithmInfo {
  name: AlgorithmName;
  label: string;
  task: QmlTask;
  summary: string;
  /** Per-algorithm ceilings (§2C.3). D-032 guarantees every table has the
   *  same keys, so the form reads one shape. */
  limits: Record<string, LimitRange>;
  datasets: DatasetOption[];
  /** Which metrics the results panel should render, in order. */
  metrics: string[];
  /** Which per-epoch series the chart should plot. */
  epoch_fields: string[];
  supports: AlgorithmSupports;
  baseline: string;
}

export interface QmlDescribe {
  limits: Record<string, LimitRange>;
  /** Compatibility field: the datasets valid for `default_algorithm`.
   *  Prefer `algorithms[].datasets`, which is task-filtered. */
  datasets: DatasetOption[];
  diff_methods: DiffMethod[];
  rotations: Rotation[];
  entanglements: Entanglement[];
  device: string;
  max_concurrent_experiments: number;
  statuses: string[];
  default_algorithm: AlgorithmName;
  algorithms: AlgorithmInfo[];
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

/** One row of `qml_epoch_metrics`.
 *
 *  **Every metric except `train_loss` is nullable, and that is load-bearing.**
 *  A regression epoch stores `train_accuracy = NULL` because R2 is not an
 *  accuracy; a classification epoch stores `train_r2 = NULL` for the mirror
 *  reason. This type previously declared `train_accuracy: number`, which was
 *  simply false — the value arrives as `null` and any `* 100` or `.toFixed()`
 *  renders `0`, i.e. "the model scored zero" (D-033, third occurrence).
 *
 *  Treat `null` as *absent*, never as zero. `finiteSeries()` below is the
 *  supported way to get plottable points out of a history. */
export interface EpochRow {
  epoch: number;
  train_loss: number;
  train_accuracy: number | null;
  test_loss: number | null;
  test_accuracy: number | null;
  train_r2: number | null;
  test_r2: number | null;
  elapsed_seconds: number;
}

export interface ClassificationEvaluation {
  accuracy: number;
  precision: number;
  recall: number;
  f1: number;
  confusion_matrix: number[][];
  n_samples: number;
}

/** No accuracy field exists here, by construction. A results panel that
 *  renders `METRICS_BY_TASK[task]` therefore *cannot* show an accuracy for a
 *  regression run — §2C.4 enforced by the type system rather than by care. */
export interface RegressionEvaluation {
  mae: number;
  rmse: number;
  /** Can be negative: a model worse than predicting the mean. Phase 5
   *  measured -2.060 on epoch 1 of a sine fit. Always render the sign. */
  r2: number;
  n_samples: number;
}

export type Evaluation = ClassificationEvaluation | RegressionEvaluation;

export interface ClassificationBaseline {
  model: string;
  train_accuracy: number;
  test_accuracy: number;
  n_parameters: number;
  converged: boolean;
}

export interface RegressionBaseline {
  model: string;
  mae: number;
  rmse: number;
  r2: number;
  n_parameters: number;
}

export type Baseline = ClassificationBaseline | RegressionBaseline;

/** Present only for `quantum_kernel`. An LSSVM has no epochs, so this is
 *  where its single-solve outcome lives. */
export interface GramPreview {
  /** Full matrix dimension; `size` is what was actually sent. */
  n_total: number;
  size: number;
  symmetric: boolean;
  unit_diagonal: boolean;
  truncated: boolean;
  values: number[][];
}

export interface KernelSummary {
  classifier: string;
  n_support: number;
  gamma: number;
  train_accuracy: number;
  evaluations: {
    train_pairs: number;
    test_pairs: number;
    total: number;
    naive_full_matrix: number;
  };
  gram_preview: GramPreview;
}

interface ResultCommon {
  algorithm: AlgorithmName;
  circuit: Record<string, unknown>;
  dataset: Record<string, unknown>;
  epochs_completed: number;
  duration_seconds: number;
  final_train_loss: number | null;
  interrupted?: undefined;
}

export interface ClassificationResult extends ResultCommon {
  task: "classification";
  evaluation: ClassificationEvaluation;
  baseline: ClassificationBaseline;
  final_train_accuracy: number | null;
  /** `quantum_kernel` only. Its presence is how the Training view knows to
   *  show a closed-form summary instead of an empty curve. */
  kernel?: KernelSummary;
}

export interface RegressionResult extends ResultCommon {
  task: "regression";
  evaluation: RegressionEvaluation;
  baseline: RegressionBaseline;
  final_train_r2: number | null;
}

/** A cancelled or timed-out run.
 *
 *  **This shape has no `task` key**, because no task ever completed
 *  (`_finish_interrupted`, services:347). A `switch (result.task)` without
 *  this member falls through to `undefined` for every cancelled run, so the
 *  discriminant to test *first* is `interrupted`. No model is saved either,
 *  which is why there is no evaluation or baseline to render. */
export interface InterruptedResult {
  interrupted: true;
  reason: string;
  epochs_completed: number;
  stopped_at_epoch: number | null;
  stopped_at_batch: number | null;
  duration_seconds: number;
  task?: undefined;
}

export type ExperimentResult = ClassificationResult | RegressionResult | InterruptedResult;

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

interface InferenceCommon {
  algorithm: AlgorithmName;
  feature_names: string[];
  n_features: number;
}

export interface ClassificationInference extends InferenceCommon {
  task: "classification";
  predictions: number[];
  probabilities: number[];
  decision_values?: undefined;
}

/** The kernel is a classifier but reports a **signed margin**, not a
 *  probability. Labelling `decision_values` as a probability would be an
 *  overclaim: it is an unnormalised distance from the decision boundary and
 *  is routinely outside [0, 1]. */
export interface KernelInference extends InferenceCommon {
  task: "classification";
  predictions: number[];
  decision_values: number[];
  probabilities?: undefined;
}

export interface RegressionInference extends InferenceCommon {
  task: "regression";
  /** In the target's own units — the stored scaler is reloaded server-side
   *  and the endpoint raises rather than answering in scaled units. */
  values: number[];
  target_range: [number, number];
}

export type InferenceResult =
  | ClassificationInference
  | KernelInference
  | RegressionInference;

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
  algorithm: "vqc",
  dataset: { name: "moons", n_samples: 200, noise: 0.15, test_fraction: 0.3 },
  circuit: { n_qubits: 2, n_layers: 2, rotation: "Y", entanglement: "ring" },
  training: { epochs: 10, batch_size: 16, learning_rate: 0.1, diff_method: "backprop" },
};

/* -------------------------------------------------------------------------- */
/* Narrowing helpers — test `interrupted` before `task`                        */
/* -------------------------------------------------------------------------- */

export function isInterrupted(
  result: ExperimentResult | null | undefined,
): result is InterruptedResult {
  return result != null && result.interrupted === true;
}

export function isRegressionResult(
  result: ExperimentResult | null | undefined,
): result is RegressionResult {
  return result != null && !isInterrupted(result) && result.task === "regression";
}

export function isClassificationResult(
  result: ExperimentResult | null | undefined,
): result is ClassificationResult {
  return result != null && !isInterrupted(result) && result.task === "classification";
}

export function isRegressionInference(
  payload: InferenceResult,
): payload is RegressionInference {
  return payload.task === "regression";
}

/** The kernel branch of classification: a signed margin, not a probability. */
export function hasDecisionValues(
  payload: InferenceResult,
): payload is KernelInference {
  return payload.task === "classification" && Array.isArray(payload.decision_values);
}

export function hasProbabilities(
  payload: InferenceResult,
): payload is ClassificationInference {
  return payload.task === "classification" && Array.isArray(payload.probabilities);
}

/* -------------------------------------------------------------------------- */
/* Series extraction — the one supported way to turn history into points       */
/* -------------------------------------------------------------------------- */

/** A single plottable point. Null epochs never become one. */
export interface SeriesPoint {
  epoch: number;
  value: number;
}

/** Pull one series out of a history, **dropping null and non-finite points
 *  rather than coercing them to zero**.
 *
 *  This exists so that skipping is easier than not skipping. The failure it
 *  prevents is specific: a regression run stores `train_accuracy = null` on
 *  every epoch, and `rows.map(r => r.train_accuracy * 100)` yields a flat
 *  line at 0% under a legend that says "accuracy" — a measurement the model
 *  never produced, rendered as if it had scored zero.
 *
 *  A gap in the middle of a series is a gap, not a dip to the axis. */
export function finiteSeries(rows: EpochRow[], key: keyof EpochRow): SeriesPoint[] {
  const points: SeriesPoint[] = [];
  for (const row of rows) {
    const value = row[key];
    if (typeof value === "number" && Number.isFinite(value)) {
      points.push({ epoch: row.epoch, value });
    }
  }
  return points;
}

/** True when a series has no plottable point at all — e.g. accuracy on a
 *  regression run, or anything on a kernel run with no epoch rows. Callers
 *  should omit the series entirely rather than draw an empty axis. */
export function seriesIsEmpty(rows: EpochRow[], key: keyof EpochRow): boolean {
  return finiteSeries(rows, key).length === 0;
}

/** Human label for an epoch series key, used by the chart legend. */
export const EPOCH_FIELD_LABELS: Record<string, string> = {
  train_loss: "Train loss",
  test_loss: "Test loss",
  train_accuracy: "Train accuracy",
  test_accuracy: "Test accuracy",
  train_r2: "Train R\u00b2",
  test_r2: "Test R\u00b2",
};

/** Metric labels and formatting, keyed by the names `/qml/describe` serves.
 *
 *  `unit: "target"` means the number is in the target variable's own units
 *  and must not be rendered as a percentage (§2E.3, MT-006). */
export const METRIC_META: Record<
  string,
  { label: string; kind: "fraction" | "target" | "signed" }
> = {
  accuracy: { label: "Accuracy", kind: "fraction" },
  precision: { label: "Precision", kind: "fraction" },
  recall: { label: "Recall", kind: "fraction" },
  f1: { label: "F1", kind: "fraction" },
  mae: { label: "MAE", kind: "target" },
  rmse: { label: "RMSE", kind: "target" },
  r2: { label: "R\u00b2", kind: "signed" },
};

/* -------------------------------------------------------------------------- */
/* Phase 6 — AI explanation                                                   */
/* -------------------------------------------------------------------------- */

/** The facts the server handed to the model, returned so the UI can print
 *  them beside the prose. A fabricated number then sits directly above the
 *  real one instead of standing alone and authoritative (§2F.2). */
export interface ExplanationFacts {
  task: QmlTask | null;
  algorithm: string | null;
  dataset: {
    name: string | null;
    n_train: number | null;
    n_test: number | null;
    n_features: number | null;
  };
  circuit: {
    n_qubits: number | null;
    n_layers: number | null;
    n_parameters: number | null;
    encoding: string | null;
  };
  evaluation: Record<string, number | number[][] | null>;
  baseline: Record<string, number | string | boolean | null>;
  epochs_completed: number | null;
  n_epoch_rows: number;
}

/** `configured: false` is a first-class state, not an error: it is what
 *  CI and most checkouts return, and it still carries a useful body. */
export interface QmlExplanation {
  configured: boolean;
  explanation: string;
  grounded_on: ExplanationFacts;
}

export function explainExperiment(id: number): Promise<QmlExplanation> {
  return api.post<QmlExplanation>(`/qml/experiments/${id}/explain`, {});
}
