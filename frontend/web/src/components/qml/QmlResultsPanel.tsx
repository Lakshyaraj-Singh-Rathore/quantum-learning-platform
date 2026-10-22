/* View D — Results and inference.
 *
 * Two things this must get right and does not guess at:
 *  - the confusion matrix orientation is the backend's (rows = true labels),
 *    so precision and recall read correctly off it;
 *  - the quantum model is shown *against* the classical baseline. A QNN at
 *    82% means nothing until you know logistic regression got 88% on the
 *    same split. Hiding that comparison is how a toy gets presented as a
 *    result.
 */
import { useState } from "react";
import { Badge, Button, Card, DataTable, EmptyState, ErrorNote, Input, Label } from "../ui";
import type { ColumnDef } from "../ui";
import { ConfusionMatrix, ProbabilityBar } from "./charts";
import type { ExperimentResult, InferenceResult } from "../../api/qml";

function Metric({
  label,
  value,
  compare,
}: {
  label: string;
  value: number;
  compare?: number;
}) {
  const delta = compare === undefined ? undefined : value - compare;
  return (
    <div className="rounded-xl border border-line bg-subtle/50 px-3 py-2">
      <dt className="text-[10px] font-semibold uppercase tracking-wider text-ink-3">{label}</dt>
      <dd className="mt-0.5 flex items-baseline gap-1.5">
        <span className="text-base font-semibold tabular-nums text-ink">
          {(value * 100).toFixed(1)}%
        </span>
        {delta !== undefined && Math.abs(delta) >= 0.0005 && (
          <span
            className="text-[11px] font-medium tabular-nums"
            style={{
              color: delta > 0 ? "var(--color-ok)" : "var(--color-warn)",
            }}
          >
            {delta > 0 ? "+" : ""}
            {(delta * 100).toFixed(1)}
          </span>
        )}
      </dd>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Inference                                                                   */
/* -------------------------------------------------------------------------- */

interface InferenceRow {
  index: number;
  features: string;
  prediction: number;
  probability: number;
}

function InferencePanel({
  nFeatures,
  featureNames,
  onRun,
  result,
  running,
  error,
}: {
  nFeatures: number;
  featureNames: string[];
  onRun: (features: number[][]) => void;
  result: InferenceResult | undefined;
  running: boolean;
  error: Error | null;
}) {
  const [values, setValues] = useState<string[]>(() => Array(nFeatures).fill("0"));

  // Keep the row the same width as the model expects if the config changes
  // under us, rather than posting a short vector the server will 422.
  if (values.length !== nFeatures) {
    setValues(Array(nFeatures).fill("0"));
  }

  const parsed = values.map((v) => Number(v));
  const invalid = parsed.some((v) => !Number.isFinite(v));

  const rows: InferenceRow[] =
    result === undefined
      ? []
      : result.predictions.map((p, i) => ({
          index: i,
          features: "submitted",
          prediction: p,
          probability: result.probabilities[i],
        }));

  const columns: ColumnDef<InferenceRow>[] = [
    { key: "index", label: "#", className: "w-10 tabular-nums" },
    {
      key: "prediction",
      label: "Class",
      render: (r) => <Badge tone={r.prediction === 1 ? "accent" : "neutral"}>{r.prediction}</Badge>,
    },
    {
      key: "probability",
      label: "P(class 1)",
      render: (r) => <ProbabilityBar value={r.probability} />,
    },
  ];

  return (
    <Card className="space-y-4">
      <header>
        <h3 className="text-sm font-semibold text-ink">Inference</h3>
        <p className="text-[11px] text-ink-3">
          Runs against the saved model, reloaded from disk — the same weights the
          evaluation above measured.
        </p>
      </header>

      <div className="grid gap-3 sm:grid-cols-2">
        {values.map((v, i) => (
          <div key={i} className="space-y-1">
            <Label htmlFor={`qml-feature-${i}`}>{featureNames[i] ?? `feature ${i}`}</Label>
            <Input
              id={`qml-feature-${i}`}
              type="number"
              step="0.1"
              value={v}
              onChange={(e) => {
                const next = [...values];
                next[i] = e.target.value;
                setValues(next);
              }}
            />
          </div>
        ))}
      </div>

      <p className="text-[11px] text-ink-3">
        Raw feature values. The server applies the scaler that was fitted on this
        experiment&rsquo;s training split, so values near that range behave best.
      </p>

      {error && <ErrorNote>{error.message}</ErrorNote>}

      <Button disabled={running || invalid} onClick={() => onRun([parsed])}>
        {running ? "Predicting…" : "Predict"}
      </Button>

      {rows.length > 0 && (
        <DataTable columns={columns} rows={rows} emptyMessage="No predictions yet." />
      )}
    </Card>
  );
}

/* -------------------------------------------------------------------------- */
/* Results                                                                     */
/* -------------------------------------------------------------------------- */

export function QmlResultsPanel({
  result,
  status,
  error,
  inference,
  onRunInference,
  inferenceRunning,
  inferenceError,
}: {
  result: ExperimentResult | null;
  status: string;
  error: string | null;
  inference: InferenceResult | undefined;
  onRunInference: (features: number[][]) => void;
  inferenceRunning: boolean;
  inferenceError: Error | null;
}) {
  if (status === "failed") {
    return (
      <EmptyState
        title="This experiment failed"
        description={error ?? "No error detail was recorded."}
      />
    );
  }

  if (result === null) {
    return (
      <EmptyState
        title="No results yet"
        description={
          status === "cancelled" || status === "timed_out"
            ? "The run stopped before it finished, so no model was saved."
            : "Results appear here once training completes."
        }
      />
    );
  }

  if (result.interrupted) {
    return (
      <EmptyState
        title={status === "timed_out" ? "Run timed out" : "Run cancelled"}
        description={
          result.reason ??
          "Training stopped early. Epochs recorded up to that point are on the dashboard, but no model was saved."
        }
      />
    );
  }

  const { evaluation, baseline } = result;
  const beatsBaseline = evaluation.accuracy >= baseline.test_accuracy;
  const nFeatures = Number(result.dataset?.n_features ?? 2);
  const featureNames = Array.isArray(result.dataset?.feature_names)
    ? (result.dataset.feature_names as string[])
    : [];

  return (
    <div className="space-y-4">
      <Card className="space-y-4">
        <header className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-sm font-semibold text-ink">Test-set performance</h3>
          <span className="text-[11px] tabular-nums text-ink-3">
            {evaluation.n_samples} held-out samples · {result.epochs_completed} epochs ·{" "}
            {result.duration_seconds.toFixed(1)}s
          </span>
        </header>

        <dl className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          <Metric label="Accuracy" value={evaluation.accuracy} compare={baseline.test_accuracy} />
          <Metric label="Precision" value={evaluation.precision} />
          <Metric label="Recall" value={evaluation.recall} />
          <Metric label="F1" value={evaluation.f1} />
        </dl>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="space-y-3">
          <h3 className="text-sm font-semibold text-ink">Confusion matrix</h3>
          <ConfusionMatrix matrix={evaluation.confusion_matrix} />
          <p className="text-[11px] text-ink-3">
            Rows are true labels, columns predicted. The diagonal is correct.
          </p>
        </Card>

        <Card className="space-y-3">
          <header className="flex items-center justify-between gap-2">
            <h3 className="text-sm font-semibold text-ink">Classical baseline</h3>
            <Badge tone={beatsBaseline ? "ok" : "warn"}>
              {beatsBaseline ? "quantum ≥ baseline" : "baseline ahead"}
            </Badge>
          </header>

          <dl className="grid grid-cols-2 gap-2">
            <Metric label="Quantum (test)" value={evaluation.accuracy} />
            <Metric label={baseline.model} value={baseline.test_accuracy} />
          </dl>

          <p className="text-[11px] leading-relaxed text-ink-3">
            {baseline.model} trained on the same split, {baseline.n_parameters} parameters,{" "}
            {baseline.converged ? "converged" : "did not converge"}.{" "}
            {beatsBaseline
              ? "The quantum model matches or beats it here — on a small, seeded, synthetic set, which is not evidence of quantum advantage."
              : "The classical model is ahead, which is the expected outcome on these datasets; the point of the lab is the mechanism, not a win."}
          </p>
        </Card>
      </div>

      <InferencePanel
        nFeatures={nFeatures}
        featureNames={featureNames}
        onRun={onRunInference}
        result={inference}
        running={inferenceRunning}
        error={inferenceError}
      />
    </div>
  );
}
