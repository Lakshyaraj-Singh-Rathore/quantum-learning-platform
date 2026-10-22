/* View C — Training dashboard.
 *
 * Polling is react-query's `refetchInterval`, exactly the idiom at
 * `ChallengesPage.tsx:965-975`. Not `setInterval`: react-query tears the
 * timer down on unmount and on every terminal state by itself, so there is
 * no cleanup to forget and no request left firing against an experiment
 * nobody is watching. The predicate returns `false` — not 0 — because 0 is
 * a legal interval that would spin.
 */
import { Badge, Button, Card, ConfirmModal, ErrorNote, Spinner } from "../ui";
import { CHART_TOKENS, LineChart, type Series } from "./charts";
import type { AlgorithmInfo, EpochRow, ExperimentStatus, KernelSummary } from "../../api/qml";
import { EPOCH_FIELD_LABELS, finiteSeries, isTerminal } from "../../api/qml";
import { useState } from "react";

const STATUS_TONE: Record<ExperimentStatus, "neutral" | "accent" | "ok" | "warn" | "danger"> = {
  queued: "neutral",
  running: "accent",
  completed: "ok",
  failed: "danger",
  cancelled: "warn",
  timed_out: "warn",
};

const STATUS_LABEL: Record<ExperimentStatus, string> = {
  queued: "Queued",
  running: "Running",
  completed: "Completed",
  failed: "Failed",
  cancelled: "Cancelled",
  timed_out: "Timed out",
};

/** R2 with an explicit sign. `-0.16` must never render as `0.16`, and a
 *  positive value is clearer with a leading `+` next to negative siblings. */
function formatR2(value: number): string {
  return `${value >= 0 ? "+" : ""}${value.toFixed(3)}`;
}

function Stat({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <div className="rounded-xl border border-line bg-subtle/50 px-3 py-2">
      <dt className="text-[10px] font-semibold uppercase tracking-wider text-ink-3">{label}</dt>
      <dd className="mt-0.5 text-sm font-semibold tabular-nums text-ink">{value}</dd>
      {hint && <p className="text-[10px] text-ink-3">{hint}</p>}
    </div>
  );
}

/** Canonical display order for epoch metrics: losses, then quality. */
const KNOWN_EPOCH_FIELDS = [
  "train_loss",
  "test_loss",
  "train_accuracy",
  "test_accuracy",
  "train_r2",
  "test_r2",
] as const;

export function QmlTrainingDashboard({
  experimentId,
  status,
  history,
  totalEpochs,
  error,
  cached,
  onCancel,
  cancelling,
  cancelError,
  onViewResults,
  algorithm,
  kernel,
}: {
  experimentId: number;
  status: ExperimentStatus;
  history: EpochRow[];
  totalEpochs: number;
  error: string | null;
  cached: boolean;
  onCancel: () => void;
  cancelling: boolean;
  cancelError: Error | null;
  onViewResults: () => void;
  /** Capability entry for the running algorithm. Drives which series exist
   *  and whether there is an epoch loop at all. */
  algorithm?: AlgorithmInfo;
  /** Present once a kernel run completes: its closed-form outcome. */
  kernel?: KernelSummary;
}) {
  const [confirmOpen, setConfirmOpen] = useState(false);

  const terminal = isTerminal(status);
  const last = history.length > 0 ? history[history.length - 1] : undefined;
  const done = last?.epoch ?? 0;
  const pct = totalEpochs > 0 ? Math.min(100, (done / totalEpochs) * 100) : 0;

  // `supports.epochs`, not `history.length` and not the algorithm's name.
  // The kernel is a single closed-form solve, so an empty history is its
  // correct and final state -- not a run that has yet to report.
  const hasEpochLoop = algorithm?.supports.epochs !== false;

  // Series come from the capability document, so a new metric needs no
  // change here. `finiteSeries` drops null points instead of coercing them:
  // a regression epoch has `train_accuracy = null`, and plotting that at 0
  // draws a flat line at 0% under a legend reading "accuracy" (D-033).
  // The capability document and the history endpoint disagree in BOTH
  // directions, so trusting either alone loses a curve:
  //   - every classification algorithm advertises
  //     ["train_loss", "train_accuracy", "test_accuracy"] yet `load_history`
  //     also serves `test_loss`. Driving purely off `epoch_fields` silently
  //     dropped the test-loss curve that Phase 3 drew.
  //   - `quantum_regression` advertises train_r2/test_r2, which
  //     `load_history` does not serialise at all, so those arrive as
  //     `undefined` and the series is empty.
  // Taking the union of what is advertised and what actually arrived keeps a
  // real curve whichever side is stale, and `buildSeries` drops any field
  // with no finite points so an advertised-but-absent metric draws nothing
  // rather than an empty axis.
  const advertised = algorithm?.epoch_fields ?? ["train_loss", "train_accuracy", "test_accuracy"];
  const present = KNOWN_EPOCH_FIELDS.filter((f) =>
    history.some((row) => typeof row[f as keyof EpochRow] === "number"),
  );
  const fields = KNOWN_EPOCH_FIELDS.filter(
    (f) => advertised.includes(f) || present.includes(f),
  );
  const colourFor = (field: string): string => {
    if (field.startsWith("test_")) return CHART_TOKENS.warn;
    if (field.includes("loss")) return CHART_TOKENS.accent;
    return CHART_TOKENS.ok;
  };
  const buildSeries = (keys: string[]): Series[] =>
    keys
      .map((field) => ({
        label: EPOCH_FIELD_LABELS[field] ?? field,
        color: colourFor(field),
        dashed: field.startsWith("test_"),
        points: finiteSeries(history, field as keyof EpochRow).map((pt) => ({
          x: pt.epoch,
          y: pt.value,
        })),
      }))
      .filter((series) => series.points.length > 0);

  const lossSeries = buildSeries(fields.filter((f) => f.includes("loss")));
  const qualityFields = fields.filter((f) => !f.includes("loss"));
  const qualitySeries = buildSeries(qualityFields);
  // R2 is unbounded below, so the accuracy chart's [0, 1] clamp would crop a
  // negative score out of view entirely. Phase 5 measured -2.060.
  const qualityIsR2 = qualityFields.some((f) => f.endsWith("_r2"));
  const qualityLabel = qualityIsR2 ? "R\u00b2" : "accuracy";

  return (
    <div className="space-y-4">
      <Card className="space-y-4">
        <header className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Badge tone={STATUS_TONE[status]}>{STATUS_LABEL[status]}</Badge>
            <span className="text-xs text-ink-3">experiment #{experimentId}</span>
            {cached && (
              <Badge tone="neutral" title="An identical configuration had already been run; its result was reused.">
                reused
              </Badge>
            )}
            {!terminal && <Spinner />}
          </div>

          <div className="flex items-center gap-2">
            {!terminal && (
              <Button
                variant="danger"
                size="sm"
                disabled={cancelling}
                onClick={() => setConfirmOpen(true)}
              >
                {cancelling ? "Cancelling…" : "Cancel"}
              </Button>
            )}
            {status === "completed" && (
              <Button size="sm" onClick={onViewResults}>
                View results
              </Button>
            )}
          </div>
        </header>

        <div>
          <div className="mb-1 flex items-baseline justify-between text-[11px] text-ink-3">
            <span>
              epoch {done} / {totalEpochs}
            </span>
            <span className="tabular-nums">
              {last ? `${last.elapsed_seconds.toFixed(1)}s elapsed` : "—"}
            </span>
          </div>
          <div
            className="h-1.5 w-full overflow-hidden rounded-full bg-subtle"
            role="progressbar"
            aria-valuenow={Math.round(pct)}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label="Training progress"
          >
            <div
              className="h-full rounded-full transition-all duration-300"
              style={{
                width: `${pct}%`,
                backgroundColor: terminal
                  ? status === "completed"
                    ? CHART_TOKENS.ok
                    : CHART_TOKENS.warn
                  : CHART_TOKENS.accent,
              }}
            />
          </div>
        </div>

        {error && <ErrorNote>{error}</ErrorNote>}
        {cancelError && <ErrorNote>Could not cancel: {cancelError.message}</ErrorNote>}

        {/* Only the metrics this task actually produces get a tile. A
            regression run has no accuracy, so no accuracy tile is rendered --
            an em dash under a heading that says "Train acc" still asserts the
            metric is meaningful here and merely missing. */}
        {hasEpochLoop && (
          <dl className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            <Stat label="Train loss" value={last ? last.train_loss.toFixed(4) : "—"} />
            <Stat
              label="Test loss"
              value={last?.test_loss != null ? last.test_loss.toFixed(4) : "—"}
            />
            {last?.train_accuracy != null && (
              <Stat label="Train acc" value={`${(last.train_accuracy * 100).toFixed(1)}%`} />
            )}
            {last?.test_accuracy != null && (
              <Stat label="Test acc" value={`${(last.test_accuracy * 100).toFixed(1)}%`} />
            )}
            {last?.train_r2 != null && (
              <Stat label="Train R\u00b2" value={formatR2(last.train_r2)} />
            )}
            {last?.test_r2 != null && <Stat label="Test R\u00b2" value={formatR2(last.test_r2)} />}
          </dl>
        )}
      </Card>

      {hasEpochLoop ? (
        <div className="grid gap-4 lg:grid-cols-2">
          <Card className="space-y-2">
            <h3 className="text-sm font-semibold text-ink">Loss</h3>
            <LineChart series={lossSeries} yMin={0} yLabel="loss" />
          </Card>
          {qualitySeries.length > 0 && (
            <Card className="space-y-2">
              <h3 className="text-sm font-semibold text-ink">
                {qualityIsR2 ? "R\u00b2" : "Accuracy"}
              </h3>
              <LineChart
                series={qualitySeries}
                {...(qualityIsR2 ? {} : { yMin: 0, yMax: 1 })}
                yLabel={qualityLabel}
              />
            </Card>
          )}
        </div>
      ) : (
        <ClosedFormPanel summary={kernel} status={status} />
      )}

      <ConfirmModal
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title="Cancel this experiment?"
        description="The worker stops at the end of the current batch. Epochs already recorded are kept, but no model is saved, so the run cannot be resumed or used for inference."
        confirmLabel="Cancel experiment"
        variant="danger"
        onConfirm={() => {
          setConfirmOpen(false);
          onCancel();
        }}
      />
    </div>
  );
}

/** What the Training view shows for an algorithm with no epoch loop.
 *
 *  The kernel solves once in closed form, so there is no curve to draw. The
 *  failure modes this replaces are all forms of implying otherwise: an empty
 *  axis (suggests the data is missing), a spinner (suggests work in
 *  progress), or a synthetic single-point "curve" (suggests one epoch
 *  happened). It reports the actual cost instead -- how many kernel entries
 *  were evaluated, and how many a naive implementation would have needed.
 */
function ClosedFormPanel({
  summary,
  status,
}: {
  summary?: KernelSummary;
  status: ExperimentStatus;
}) {
  if (!isTerminal(status)) {
    return (
      <Card className="space-y-2">
        <h3 className="text-sm font-semibold text-ink">Closed-form solve</h3>
        <p className="text-xs leading-relaxed text-ink-3">
          This algorithm has no training loop: it builds the kernel matrix, then solves a single
          linear system. There are no epochs to report, so no curve is drawn — progress is the
          kernel build itself.
        </p>
        <div className="flex items-center gap-2 text-xs text-ink-3">
          <Spinner />
          <span>Evaluating kernel entries…</span>
        </div>
      </Card>
    );
  }

  if (!summary) {
    return (
      <Card className="space-y-2">
        <h3 className="text-sm font-semibold text-ink">Closed-form solve</h3>
        <p className="text-xs leading-relaxed text-ink-3">
          This run recorded no epochs, which is correct for a closed-form fit. Open the Results
          view for its metrics.
        </p>
      </Card>
    );
  }

  const { evaluations } = summary;
  const saved = evaluations.naive_full_matrix - evaluations.total;

  return (
    <Card className="space-y-3">
      <div className="flex items-baseline justify-between gap-2">
        <h3 className="text-sm font-semibold text-ink">Closed-form solve</h3>
        <Badge tone="neutral">{summary.classifier}</Badge>
      </div>
      <p className="text-xs leading-relaxed text-ink-3">
        No epochs: the kernel matrix is built once and a single linear system is solved. A training
        curve would be a fabrication, so none is drawn.
      </p>
      <dl className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <Stat label="Support vectors" value={String(summary.n_support)} />
        <Stat label="Gamma" value={summary.gamma.toFixed(3)} />
        <Stat
          label="Train acc"
          value={`${(summary.train_accuracy * 100).toFixed(1)}%`}
        />
        <Stat
          label="Kernel evals"
          value={evaluations.total.toLocaleString()}
          hint={`${saved.toLocaleString()} fewer than a naive full matrix`}
        />
      </dl>
    </Card>
  );
}
