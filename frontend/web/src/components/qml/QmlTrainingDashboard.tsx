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
import { CHART_TOKENS, LineChart } from "./charts";
import type { EpochRow, ExperimentStatus } from "../../api/qml";
import { isTerminal } from "../../api/qml";
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
}) {
  const [confirmOpen, setConfirmOpen] = useState(false);

  const terminal = isTerminal(status);
  const last = history.length > 0 ? history[history.length - 1] : undefined;
  const done = last?.epoch ?? 0;
  const pct = totalEpochs > 0 ? Math.min(100, (done / totalEpochs) * 100) : 0;
  const hasTest = history.some((h) => h.test_loss !== null);

  const lossSeries = [
    {
      label: "train loss",
      color: CHART_TOKENS.accent,
      points: history.map((h) => ({ x: h.epoch, y: h.train_loss })),
    },
    ...(hasTest
      ? [
          {
            label: "test loss",
            color: CHART_TOKENS.warn,
            dashed: true,
            points: history
              .filter((h) => h.test_loss !== null)
              .map((h) => ({ x: h.epoch, y: h.test_loss as number })),
          },
        ]
      : []),
  ];

  const accSeries = [
    {
      label: "train accuracy",
      color: CHART_TOKENS.ok,
      points: history.map((h) => ({ x: h.epoch, y: h.train_accuracy })),
    },
    ...(hasTest
      ? [
          {
            label: "test accuracy",
            color: CHART_TOKENS.accent,
            dashed: true,
            points: history
              .filter((h) => h.test_accuracy !== null)
              .map((h) => ({ x: h.epoch, y: h.test_accuracy as number })),
          },
        ]
      : []),
  ];

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

        <dl className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          <Stat label="Train loss" value={last ? last.train_loss.toFixed(4) : "—"} />
          <Stat
            label="Train acc"
            value={last ? `${(last.train_accuracy * 100).toFixed(1)}%` : "—"}
          />
          <Stat
            label="Test loss"
            value={last?.test_loss != null ? last.test_loss.toFixed(4) : "—"}
          />
          <Stat
            label="Test acc"
            value={
              last?.test_accuracy != null ? `${(last.test_accuracy * 100).toFixed(1)}%` : "—"
            }
          />
        </dl>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="space-y-2">
          <h3 className="text-sm font-semibold text-ink">Loss</h3>
          <LineChart series={lossSeries} yMin={0} yLabel="loss" />
        </Card>
        <Card className="space-y-2">
          <h3 className="text-sm font-semibold text-ink">Accuracy</h3>
          <LineChart series={accSeries} yMin={0} yMax={1} yLabel="accuracy" />
        </Card>
      </div>

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
