/* AI explanation of a finished run, shown beside the numbers it describes.
 *
 * Three rules from §2F.2, all visible in the markup below:
 *
 *  1. The prose is rendered as prose. It never goes in a `Stat`, never gets
 *     a metric label, and never sits where a measured value sits. A
 *     sentence that says "accuracy was 0.95" must not be able to pass for
 *     the accuracy readout.
 *  2. The real figures are printed next to it, from `grounded_on` — the
 *     same values the server handed the model. If the model invents a
 *     number, the true one is directly above it rather than absent.
 *  3. `configured: false` is a first-class state with its own `EmptyState`,
 *     not an error. It is what CI and most checkouts return, so it has to
 *     be useful rather than look broken.
 */
import { useMutation } from "@tanstack/react-query";
import { Sparkles } from "lucide-react";

import { explainExperiment, type QmlExplanation, type ExplanationFacts } from "../../api/qml";
import { Button, Card, EmptyState, ErrorNote, Spinner } from "../ui";

/** Metric names the backend may return, rendered in a stable order. */
const METRIC_ORDER = [
  "accuracy",
  "precision",
  "recall",
  "f1",
  "mae",
  "rmse",
  "r2",
] as const;

function formatValue(value: unknown): string {
  if (typeof value === "number") {
    return Number.isInteger(value) ? String(value) : value.toFixed(4);
  }
  if (typeof value === "boolean") return value ? "yes" : "no";
  return String(value);
}

/** The measured numbers, printed as data — this is the control the prose is
 *  checked against, so it is deliberately plain and complete. */
export function GroundingTable({ facts }: { facts: ExplanationFacts }) {
  const metrics = METRIC_ORDER.filter(
    (name) => typeof facts.evaluation?.[name] === "number",
  );
  const baselineEntries = Object.entries(facts.baseline ?? {}).filter(
    ([key]) => key !== "model",
  );

  return (
    <div className="rounded-xl border border-line bg-subtle/40 p-3 space-y-3">
      <p className="text-[10px] font-bold uppercase tracking-wider text-ink-3">
        Measured — what the model was given
      </p>

      {metrics.length > 0 && (
        <dl className="grid grid-cols-2 gap-x-4 gap-y-1 sm:grid-cols-3">
          {metrics.map((name) => (
            <div key={name} className="flex items-baseline justify-between gap-2">
              <dt className="text-xs text-ink-3">{name}</dt>
              <dd className="text-xs tabular-nums text-ink">
                {formatValue(facts.evaluation[name])}
              </dd>
            </div>
          ))}
        </dl>
      )}

      {baselineEntries.length > 0 && (
        <div className="border-t border-line-soft pt-2">
          <p className="text-[10px] uppercase tracking-wider text-ink-3 mb-1">
            Classical baseline
            {typeof facts.baseline?.model === "string" ? ` — ${facts.baseline.model}` : ""}
          </p>
          <dl className="grid grid-cols-2 gap-x-4 gap-y-1 sm:grid-cols-3">
            {baselineEntries.map(([key, value]) => (
              <div key={key} className="flex items-baseline justify-between gap-2">
                <dt className="text-xs text-ink-3">{key}</dt>
                <dd className="text-xs tabular-nums text-ink">{formatValue(value)}</dd>
              </div>
            ))}
          </dl>
        </div>
      )}
    </div>
  );
}

/** Prose. Rendered as paragraphs with no metric affordance whatsoever. */
export function Commentary({ text }: { text: string }) {
  const paragraphs = text.split(/\n{2,}/).filter((p) => p.trim());
  return (
    <div className="space-y-2">
      {paragraphs.map((paragraph, index) => (
        <p
          key={index}
          className="whitespace-pre-line text-xs leading-relaxed text-ink-2 sm:text-sm"
        >
          {paragraph.trim()}
        </p>
      ))}
    </div>
  );
}

export function QmlExplanationPanel({
  experimentId,
  disabled = false,
}: {
  experimentId: number | null;
  disabled?: boolean;
}) {
  const mutation = useMutation<QmlExplanation, Error, number>({
    mutationFn: (id: number) => explainExperiment(id),
  });

  const data = mutation.data;

  return (
    <Card className="space-y-3">
      <header className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-accent" />
          <h3 className="text-sm font-semibold text-ink">Explain this result</h3>
        </div>
        <Button
          variant="secondary"
          onClick={() => experimentId != null && mutation.mutate(experimentId)}
          disabled={disabled || experimentId == null || mutation.isPending}
        >
          {mutation.isPending ? (
            <span className="flex items-center gap-2">
              <Spinner className="h-3.5 w-3.5" />
              Explaining…
            </span>
          ) : data ? (
            "Explain again"
          ) : (
            "Explain"
          )}
        </Button>
      </header>

      {!data && !mutation.isPending && !mutation.error && (
        <p className="text-xs text-ink-3">
          Generates a plain-language reading of the metrics below, grounded on the
          numbers this run actually produced.
        </p>
      )}

      {mutation.error && <ErrorNote>{mutation.error.message}</ErrorNote>}

      {data && !data.configured && (
        <EmptyState
          /* No icon: the only lucide glyph already in the shared chunk is
             Sparkles, which the header uses. Importing a second one (Info)
             made the shared bundle export one more binding and grew it by
             9 bytes -- measured, not guessed. An optional icon is not worth
             moving a byte of the shared bundle. */
          title="AI explanation is not configured"
          description="No GEMINI_API_KEY is set on the server. The measured comparison below is unaffected and is what the explanation would have been based on."
        />
      )}

      {data && (
        <div className="space-y-3">
          {data.configured && <Commentary text={data.explanation} />}
          {!data.configured && (
            <pre className="whitespace-pre-wrap rounded-xl border border-line bg-subtle/40 p-3 text-[11px] leading-relaxed text-ink-2">
              {data.explanation}
            </pre>
          )}

          <GroundingTable facts={data.grounded_on} />

          {data.configured && (
            <p className="text-[10px] leading-relaxed text-ink-3">
              Written by Gemini from the measured values shown above. It is commentary,
              not a measurement — if a number in the prose disagrees with the table, the
              table is correct.
            </p>
          )}
        </div>
      )}
    </Card>
  );
}
