/* Hand-rolled SVG charts for the QML Lab.
 *
 * No chart library: none is installed and §1.4 forbids adding one. These are
 * drawn as React elements rather than an SVG string, matching
 * `components/results/CircuitDiagram.tsx`, so no `dangerouslySetInnerHTML` is
 * needed and the CSP stays strict.
 *
 * ⚠ QL-001: a Tailwind class is NEVER interpolated. Tailwind v4 scans source
 * text for complete class names at build time, so `text-${tone}` produces a
 * class that exists in the markup and in no stylesheet — which is exactly how
 * the density-matrix heatmap shipped invisible. Every data-driven colour here
 * goes through an inline `style` holding a `var(--token)`.
 */
import { useId } from "react";
import { cn } from "../ui";

/** Token names, not Tailwind classes. Read at paint time via `var()`. */
const TOKEN = {
  accent: "var(--color-accent)",
  ok: "var(--color-ok)",
  warn: "var(--color-warn)",
  danger: "var(--color-danger)",
  line: "var(--color-line)",
  ink3: "var(--color-ink-3)",
} as const;

export interface Series {
  label: string;
  /** Token colour, e.g. TOKEN.accent — never a Tailwind class. */
  color: string;
  points: { x: number; y: number }[];
  dashed?: boolean;
}

/* -------------------------------------------------------------------------- */
/* Line chart — loss and accuracy curves                                      */
/* -------------------------------------------------------------------------- */

export function LineChart({
  series,
  yMin,
  yMax,
  xLabel = "epoch",
  yLabel,
  height = 180,
  className,
}: {
  series: Series[];
  yMin?: number;
  yMax?: number;
  xLabel?: string;
  yLabel?: string;
  height?: number;
  className?: string;
}) {
  const gradientId = useId();
  const populated = series.filter((s) => s.points.length > 0);

  if (populated.length === 0) {
    return (
      <div
        className={cn(
          "flex items-center justify-center rounded-xl border border-line bg-raised/40 text-xs text-ink-3",
          className,
        )}
        style={{ height }}
      >
        Waiting for the first epoch…
      </div>
    );
  }

  // viewBox units; the SVG scales to its container so there is no resize
  // listener and nothing to clean up.
  const W = 480;
  const H = height;
  const PAD = { top: 10, right: 10, bottom: 26, left: 38 };
  const plotW = W - PAD.left - PAD.right;
  const plotH = H - PAD.top - PAD.bottom;

  const allX = populated.flatMap((s) => s.points.map((p) => p.x));
  const allY = populated.flatMap((s) => s.points.map((p) => p.y));
  const x0 = Math.min(...allX);
  const x1 = Math.max(...allX);
  const lo = yMin ?? Math.min(...allY);
  const hiRaw = yMax ?? Math.max(...allY);
  // A flat series (every y identical) would divide by zero; give it headroom.
  const hi = hiRaw - lo < 1e-9 ? lo + 1 : hiRaw;

  const sx = (x: number) => PAD.left + (x1 === x0 ? plotW / 2 : ((x - x0) / (x1 - x0)) * plotW);
  const sy = (y: number) => PAD.top + plotH - ((y - lo) / (hi - lo)) * plotH;

  const ticks = [0, 0.25, 0.5, 0.75, 1].map((t) => lo + t * (hi - lo));

  return (
    <figure className={cn("w-full", className)}>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full"
        style={{ height }}
        role="img"
        aria-label={`${yLabel ?? "value"} against ${xLabel}`}
        preserveAspectRatio="none"
      >
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={populated[0].color} stopOpacity="0.22" />
            <stop offset="100%" stopColor={populated[0].color} stopOpacity="0" />
          </linearGradient>
        </defs>

        {ticks.map((t) => (
          <g key={t}>
            <line
              x1={PAD.left}
              x2={W - PAD.right}
              y1={sy(t)}
              y2={sy(t)}
              stroke={TOKEN.line}
              strokeWidth={1}
              strokeDasharray="3 4"
            />
            <text
              x={PAD.left - 6}
              y={sy(t) + 3}
              textAnchor="end"
              fontSize={9}
              fill={TOKEN.ink3}
              fontFamily="var(--font-mono, monospace)"
            >
              {t.toFixed(2)}
            </text>
          </g>
        ))}

        <line
          x1={PAD.left}
          x2={W - PAD.right}
          y1={PAD.top + plotH}
          y2={PAD.top + plotH}
          stroke={TOKEN.line}
          strokeWidth={1}
        />

        {populated.map((s) => {
          const d = s.points.map((p, i) => `${i === 0 ? "M" : "L"}${sx(p.x)},${sy(p.y)}`).join(" ");
          const area =
            `M${sx(s.points[0].x)},${PAD.top + plotH} ` +
            s.points.map((p) => `L${sx(p.x)},${sy(p.y)}`).join(" ") +
            ` L${sx(s.points[s.points.length - 1].x)},${PAD.top + plotH} Z`;
          return (
            <g key={s.label}>
              {s === populated[0] && !s.dashed && <path d={area} fill={`url(#${gradientId})`} />}
              <path
                d={d}
                fill="none"
                stroke={s.color}
                strokeWidth={1.8}
                strokeDasharray={s.dashed ? "4 3" : undefined}
                strokeLinejoin="round"
                strokeLinecap="round"
              />
              {s.points.length === 1 && (
                <circle cx={sx(s.points[0].x)} cy={sy(s.points[0].y)} r={2.5} fill={s.color} />
              )}
            </g>
          );
        })}

        <text
          x={PAD.left + plotW / 2}
          y={H - 6}
          textAnchor="middle"
          fontSize={9}
          fill={TOKEN.ink3}
        >
          {xLabel}
        </text>
      </svg>

      <figcaption className="mt-1.5 flex flex-wrap items-center gap-x-4 gap-y-1">
        {populated.map((s) => (
          <span key={s.label} className="inline-flex items-center gap-1.5 text-[11px] text-ink-3">
            <span
              aria-hidden="true"
              className="inline-block h-0.5 w-4 rounded-full"
              style={{
                backgroundColor: s.color,
                opacity: s.dashed ? 0.65 : 1,
              }}
            />
            {s.label}
          </span>
        ))}
      </figcaption>
    </figure>
  );
}

/* -------------------------------------------------------------------------- */
/* Confusion matrix                                                            */
/* -------------------------------------------------------------------------- */

/** Rows are TRUE labels, columns are PREDICTED: [[TN, FP], [FN, TP]].
 *  That orientation is fixed by the backend evaluator, which documents it at
 *  `evaluator.py:7`. Transposing it here would silently swap precision and
 *  recall in the reader's head. */
export function ConfusionMatrix({
  matrix,
  className,
}: {
  matrix: number[][];
  className?: string;
}) {
  const flat = matrix.flat();
  const max = Math.max(1, ...flat);
  const labels = ["0", "1"];

  return (
    <div className={cn("inline-block", className)}>
      <table className="border-separate border-spacing-1" aria-label="Confusion matrix">
        <caption className="sr-only">
          Confusion matrix: rows are true labels, columns are predicted labels
        </caption>
        <thead>
          <tr>
            <th scope="col" className="w-14" />
            {labels.map((l) => (
              <th
                key={l}
                scope="col"
                className="w-16 pb-1 text-center text-[10px] font-semibold uppercase tracking-wider text-ink-3"
              >
                pred {l}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {matrix.map((row, r) => (
            <tr key={r}>
              <th
                scope="row"
                className="pr-1 text-right text-[10px] font-semibold uppercase tracking-wider text-ink-3"
              >
                true {labels[r]}
              </th>
              {row.map((value, c) => {
                const correct = r === c;
                // Data-driven colour as an inline style, never an
                // interpolated class (QL-001).
                const intensity = value / max;
                return (
                  <td key={c} className="p-0">
                    <div
                      className="flex h-14 w-16 items-center justify-center rounded-lg border text-sm font-bold tabular-nums"
                      style={{
                        backgroundColor: correct
                          ? `color-mix(in srgb, ${TOKEN.ok} ${8 + intensity * 46}%, transparent)`
                          : `color-mix(in srgb, ${TOKEN.danger} ${8 + intensity * 46}%, transparent)`,
                        borderColor: correct
                          ? `color-mix(in srgb, ${TOKEN.ok} 45%, transparent)`
                          : `color-mix(in srgb, ${TOKEN.danger} 45%, transparent)`,
                        color: "var(--color-ink)",
                      }}
                      title={`${correct ? "Correct" : "Incorrect"}: true ${labels[r]}, predicted ${labels[c]} — ${value}`}
                    >
                      {value}
                    </div>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Probability bar — one inference row                                        */
/* -------------------------------------------------------------------------- */

export function ProbabilityBar({ value, className }: { value: number; className?: string }) {
  const pct = Math.max(0, Math.min(1, value)) * 100;
  // Confidence is distance from the 0.5 decision boundary, so an uncertain
  // prediction reads as warn regardless of which class it leans toward.
  const confident = Math.abs(value - 0.5) > 0.15;
  const colour = confident ? (value >= 0.5 ? TOKEN.accent : TOKEN.ok) : TOKEN.warn;

  return (
    <div className={cn("flex items-center gap-2", className)}>
      <div
        className="relative h-2 w-24 shrink-0 overflow-hidden rounded-full border border-line bg-subtle"
        role="meter"
        aria-valuenow={Number(value.toFixed(3))}
        aria-valuemin={0}
        aria-valuemax={1}
        aria-label="Probability of class 1"
      >
        <div
          className="absolute inset-y-0 left-0 rounded-full"
          style={{ width: `${pct}%`, backgroundColor: colour }}
        />
        <div
          aria-hidden="true"
          className="absolute inset-y-0 w-px"
          style={{ left: "50%", backgroundColor: TOKEN.line }}
        />
      </div>
      <span className="tabular-nums text-xs text-ink-2">{value.toFixed(3)}</span>
    </div>
  );
}

export { TOKEN as CHART_TOKENS };
