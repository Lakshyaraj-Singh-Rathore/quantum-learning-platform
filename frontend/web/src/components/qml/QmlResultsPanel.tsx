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
import { ConfusionMatrix, KernelHeatmap, ModelResponseCurve, ProbabilityBar } from "./charts";
import type {
  ClassificationResult,
  ExperimentResult,
  InferenceResult,
  RegressionResult,
} from "../../api/qml";
import {
  METRIC_META,
  hasDecisionValues,
  hasProbabilities,
  isInterrupted,
  isRegressionResult,
} from "../../api/qml";

type MetricKind = "fraction" | "target" | "signed";

/** Render a metric in its own units.
 *
 *  `fraction` is a proportion and reads as a percentage. `target` is in the
 *  target variable's units -- MAE of 0.59 is 0.59 *of y*, and showing "59%"
 *  would be meaningless. `signed` always carries its sign, because R2 can be
 *  negative and "0.16" versus "-0.16" is the difference between a weak model
 *  and one worse than predicting the mean.
 */
function formatMetric(value: number, kind: MetricKind, unitLabel?: string): string {
  if (kind === "fraction") return `${(value * 100).toFixed(1)}%`;
  if (kind === "signed") return `${value >= 0 ? "+" : ""}${value.toFixed(3)}`;
  return `${value.toFixed(3)}${unitLabel ? ` ${unitLabel}` : ""}`;
}

function Metric({
  label,
  value,
  compare,
  kind = "fraction",
  unitLabel,
  lowerIsBetter = false,
}: {
  label: string;
  value: number;
  compare?: number;
  kind?: MetricKind;
  unitLabel?: string;
  /** MAE and RMSE improve downwards, so the delta's colour must flip. */
  lowerIsBetter?: boolean;
}) {
  const delta = compare === undefined ? undefined : value - compare;
  const better = delta === undefined ? false : lowerIsBetter ? delta < 0 : delta > 0;
  const threshold = kind === "fraction" ? 0.0005 : 0.0005;
  return (
    <div className="rounded-xl border border-line bg-subtle/50 px-3 py-2">
      <dt className="text-[10px] font-semibold uppercase tracking-wider text-ink-3">{label}</dt>
      <dd className="mt-0.5 flex items-baseline gap-1.5">
        <span className="text-base font-semibold tabular-nums text-ink">
          {formatMetric(value, kind, unitLabel)}
        </span>
        {delta !== undefined && Math.abs(delta) >= threshold && (
          <span
            className="text-[11px] font-medium tabular-nums"
            style={{ color: better ? "var(--color-ok)" : "var(--color-warn)" }}
          >
            {delta > 0 ? "+" : ""}
            {kind === "fraction" ? (delta * 100).toFixed(1) : delta.toFixed(3)}
          </span>
        )}
      </dd>
    </div>
  );
}

/** Metric tiles for whichever task ran, ordered as the server listed them.
 *
 *  Reading `metrics` from the payload is what makes §2C.4 structural: the
 *  server never offers an accuracy for a regression run, so this cannot
 *  render one. There is no placeholder row for a metric a task does not
 *  have -- an em dash under "Accuracy" would still assert the metric applies
 *  here and is merely missing. */
function MetricGrid({
  metrics,
  values,
  compare,
  unitLabel,
}: {
  metrics: string[];
  values: Record<string, number | undefined>;
  compare?: Record<string, number | undefined>;
  unitLabel?: string;
}) {
  const present = metrics.filter((m) => typeof values[m] === "number");
  return (
    <dl className="grid grid-cols-2 gap-2 sm:grid-cols-4">
      {present.map((name) => {
        const meta = METRIC_META[name] ?? { label: name, kind: "fraction" as const };
        return (
          <Metric
            key={name}
            label={meta.label}
            value={values[name] as number}
            compare={compare?.[name]}
            kind={meta.kind}
            unitLabel={meta.kind === "target" ? unitLabel : undefined}
            lowerIsBetter={name === "mae" || name === "rmse"}
          />
        );
      })}
    </dl>
  );
}

/* -------------------------------------------------------------------------- */
/* Inference                                                                   */
/* -------------------------------------------------------------------------- */

interface InferenceRow {
  index: number;
  prediction: number | null;
  probability: number | null;
  margin: number | null;
  value: number | null;
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

  // One row shape, three populations. A column only exists when the task
  // actually produced that quantity -- a regression row has no class and no
  // probability, and the kernel has a margin rather than a probability.
  // ⚠ `ColumnDef.render` is `(value, row)` -- the cell value first, not the
  // row (`ui.tsx:743`). The shipped Phase 3 table wrote `(r) => r.prediction`
  // and so rendered the string "undefined" in every Class badge; `tsc` could
  // not catch it because `render`'s parameters are typed `any`. Always take
  // the second argument.
  let rows: InferenceRow[] = [];
  const columns: ColumnDef<InferenceRow>[] = [
    { key: "index", label: "#", className: "w-10 tabular-nums" },
  ];

  if (result !== undefined) {
    if (result.task === "regression") {
      rows = result.values.map((v, i) => ({
        index: i,
        prediction: null,
        probability: null,
        margin: null,
        value: v,
      }));
      columns.push({
        key: "value",
        label: "Predicted value",
        render: (_value, row) => (
          <span className="tabular-nums text-ink">{(row.value as number).toFixed(4)}</span>
        ),
      });
    } else {
      rows = result.predictions.map((p, i) => ({
        index: i,
        prediction: p,
        probability: hasProbabilities(result) ? result.probabilities[i] : null,
        margin: hasDecisionValues(result) ? result.decision_values[i] : null,
        value: null,
      }));
      columns.push({
        key: "prediction",
        label: "Class",
        render: (_value, row) => (
          <Badge tone={row.prediction === 1 ? "accent" : "neutral"}>{row.prediction}</Badge>
        ),
      });
      if (hasProbabilities(result)) {
        columns.push({
          key: "probability",
          label: "P(class 1)",
          render: (_value, row) => <ProbabilityBar value={row.probability as number} />,
        });
      }
      if (hasDecisionValues(result)) {
        // Named for what it is. An LSSVM decision value is an unnormalised
        // signed distance from the boundary and is routinely outside [0, 1];
        // rendering it in a bar labelled "probability" would be an overclaim.
        columns.push({
          key: "margin",
          label: "Margin",
          render: (_value, row) => (
            <span className="tabular-nums text-ink">
              {(row.margin as number) >= 0 ? "+" : ""}
              {(row.margin as number).toFixed(4)}
            </span>
          ),
        });
      }
    }
  }

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
        <>
          <DataTable columns={columns} rows={rows} emptyMessage="No predictions yet." />
          {result !== undefined && result.task === "regression" && (
            <p className="text-[11px] leading-relaxed text-ink-3">
              Predictions are in the target&rsquo;s own units, produced with the scaler fitted on
              this experiment&rsquo;s training split and stored alongside the model — not refitted
              on what you typed. Training targets ranged{" "}
              <span className="tabular-nums">{result.target_range[0].toFixed(3)}</span> to{" "}
              <span className="tabular-nums">{result.target_range[1].toFixed(3)}</span>.
            </p>
          )}
          {result !== undefined && hasDecisionValues(result) && (
            <p className="text-[11px] leading-relaxed text-ink-3">
              Margin is the LSSVM decision value: a signed distance from the boundary, not a
              probability. Its sign gives the class; its magnitude is confidence in unnormalised
              units.
            </p>
          )}
        </>
      )}
    </Card>
  );
}

/* -------------------------------------------------------------------------- */
/* Results                                                                     */
/* -------------------------------------------------------------------------- */

/** Points for the regression response curve, plus the reason there are none
 *  when that is the case. A missing curve with no explanation reads as a
 *  rendering bug. */
export interface ResponseCurve {
  points: { x: number; y: number }[];
  unavailableReason?: string;
}

export function QmlResultsPanel({
  result,
  status,
  error,
  inference,
  onRunInference,
  inferenceRunning,
  inferenceError,
  responseCurve,
}: {
  result: ExperimentResult | null;
  status: string;
  error: string | null;
  inference: InferenceResult | undefined;
  onRunInference: (features: number[][]) => void;
  inferenceRunning: boolean;
  inferenceError: Error | null;
  responseCurve?: ResponseCurve;
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

  if (isInterrupted(result)) {
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

  const nFeatures = Number(result.dataset?.n_features ?? 2);
  const featureNames = Array.isArray(result.dataset?.feature_names)
    ? (result.dataset.feature_names as string[])
    : [];

  return (
    <div className="space-y-4">
      {isRegressionResult(result) ? (
        <RegressionResults result={result} responseCurve={responseCurve} />
      ) : (
        <ClassificationResults result={result} />
      )}

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

/* -------------------------------------------------------------------------- */
/* Per-task result bodies                                                      */
/* -------------------------------------------------------------------------- */

function RunSummary({ result }: { result: ClassificationResult | RegressionResult }) {
  return (
    <span className="text-[11px] tabular-nums text-ink-3">
      {result.evaluation.n_samples} held-out samples ·{" "}
      {/* A closed-form fit ran no epochs; saying "0 epochs" is accurate but
          reads as a failure, so name the mechanism instead. */}
      {result.epochs_completed > 0 ? `${result.epochs_completed} epochs` : "closed form"} ·{" "}
      {result.duration_seconds.toFixed(1)}s
    </span>
  );
}

function ClassificationResults({ result }: { result: ClassificationResult }) {
  const { evaluation, baseline, kernel } = result;
  const beatsBaseline = evaluation.accuracy >= baseline.test_accuracy;

  return (
    <>
      <Card className="space-y-4">
        <header className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-sm font-semibold text-ink">Test-set performance</h3>
          <RunSummary result={result} />
        </header>

        <MetricGrid
          metrics={["accuracy", "precision", "recall", "f1"]}
          values={{
            accuracy: evaluation.accuracy,
            precision: evaluation.precision,
            recall: evaluation.recall,
            f1: evaluation.f1,
          }}
          compare={{ accuracy: baseline.test_accuracy }}
        />
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

      {kernel && (
        <Card className="space-y-3">
          <header className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-sm font-semibold text-ink">Quantum kernel matrix</h3>
            <Badge tone="neutral">{kernel.classifier}</Badge>
          </header>
          <KernelHeatmap
            values={kernel.gram_preview.values}
            nTotal={kernel.gram_preview.n_total}
            truncated={kernel.gram_preview.truncated}
          />
          <p className="text-[11px] leading-relaxed text-ink-3">
            Entry (i, j) is the fidelity between the encoded states of samples i and j, so the
            diagonal is 1 by construction. {kernel.evaluations.total.toLocaleString()} entries were
            evaluated against {kernel.evaluations.naive_full_matrix.toLocaleString()} for a naive
            full matrix, because the matrix is symmetric and only its strict upper triangle needs
            computing.
          </p>
        </Card>
      )}
    </>
  );
}

function RegressionResults({
  result,
  responseCurve,
}: {
  result: RegressionResult;
  responseCurve?: ResponseCurve;
}) {
  const { evaluation, baseline } = result;
  // R2 is the comparable headline: MAE and RMSE are in target units and the
  // ridge baseline is measured on the same split.
  const beatsBaseline = evaluation.r2 >= baseline.r2;
  const targetRange = Array.isArray(result.dataset?.target_range_test)
    ? (result.dataset.target_range_test as [number, number])
    : undefined;

  return (
    <>
      <Card className="space-y-4">
        <header className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-sm font-semibold text-ink">Test-set performance</h3>
          <RunSummary result={result} />
        </header>

        <MetricGrid
          metrics={["mae", "rmse", "r2"]}
          values={{ mae: evaluation.mae, rmse: evaluation.rmse, r2: evaluation.r2 }}
          compare={{ mae: baseline.mae, rmse: baseline.rmse, r2: baseline.r2 }}
          unitLabel="y"
        />

        <p className="text-[11px] leading-relaxed text-ink-3">
          MAE and RMSE are in the target&rsquo;s own units, not percentages. R² is signed: 0 means
          no better than predicting the mean and a negative value means worse than that, which is a
          real outcome on a hard target rather than an error.
        </p>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="space-y-3">
          <h3 className="text-sm font-semibold text-ink">Model response</h3>
          {responseCurve?.points.length ? (
            <ModelResponseCurve
              points={responseCurve.points}
              targetRange={targetRange}
              unitLabel="y"
            />
          ) : (
            <p className="text-[11px] leading-relaxed text-ink-3">
              {responseCurve?.unavailableReason ??
                "A response curve is drawn for single-feature targets only."}
            </p>
          )}
        </Card>

        <Card className="space-y-3">
          <header className="flex items-center justify-between gap-2">
            <h3 className="text-sm font-semibold text-ink">Classical baseline</h3>
            <Badge tone={beatsBaseline ? "ok" : "warn"}>
              {beatsBaseline ? "quantum ≥ baseline" : "baseline ahead"}
            </Badge>
          </header>

          <dl className="grid grid-cols-2 gap-2">
            <Metric label="Quantum R²" value={evaluation.r2} kind="signed" />
            <Metric label={`${baseline.model} R²`} value={baseline.r2} kind="signed" />
          </dl>

          <p className="text-[11px] leading-relaxed text-ink-3">
            {baseline.model} regression on the same split, {baseline.n_parameters} parameters, MAE{" "}
            <span className="tabular-nums">{baseline.mae.toFixed(3)}</span> y.{" "}
            {beatsBaseline
              ? "The quantum model matches or beats it here — on a small, seeded, synthetic target, which is not evidence of quantum advantage."
              : "The classical model is ahead, which is the expected outcome on these targets; the point of the lab is the mechanism, not a win."}
          </p>
        </Card>
      </div>
    </>
  );
}
