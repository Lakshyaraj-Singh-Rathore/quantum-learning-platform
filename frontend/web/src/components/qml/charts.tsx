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

/* -------------------------------------------------------------------------- */
/* Model response curve — regression (§2E.3)                                   */
/* -------------------------------------------------------------------------- */

/** The learned function, sampled across the input range.
 *
 *  ⚠ This is deliberately **not** the predicted-vs-actual scatter §2E.3 asks
 *  for. That chart needs the per-sample test predictions and their targets,
 *  and no endpoint serves them: a result payload carries only aggregates
 *  (`mae`, `rmse`, `r2`, `n_samples`). Rather than invent the actuals, this
 *  plots what the shipped API *can* answer for — the model's own prediction
 *  at each point of a swept input, obtained from the real inference endpoint
 *  — and labels itself as exactly that. See the phase report.
 *
 *  The dashed band is the training target range, which is the honest way to
 *  show saturation: a model whose response flattens against that band has
 *  stopped tracking the target rather than learned it.
 */
export function ModelResponseCurve({
  points,
  targetRange,
  unitLabel,
  height = 240,
  className,
}: {
  /** `x` is the swept input, `y` the model's prediction in target units. */
  points: { x: number; y: number }[];
  /** `[y_min, y_max]` the scaler was fitted on, drawn as a reference band. */
  targetRange?: [number, number];
  /** The target's own units. Never a percentage (MT-006). */
  unitLabel?: string;
  height?: number;
  className?: string;
}) {
  const pairs = points.filter((d) => Number.isFinite(d.x) && Number.isFinite(d.y));

  if (pairs.length === 0) {
    return (
      <div
        className={cn(
          "flex items-center justify-center rounded-xl border border-line-soft bg-subtle/40 text-xs text-ink-3",
          className,
        )}
        style={{ height }}
      >
        No predictions to plot
      </div>
    );
  }

  const xs = pairs.map((d) => d.x);
  const ys = pairs.map((d) => d.y);
  const yPool = targetRange ? [...ys, ...targetRange] : ys;
  const xLo = Math.min(...xs);
  const xHi = Math.max(...xs);
  const lo = Math.min(...yPool);
  const hi = Math.max(...yPool);
  // A degenerate range (every value identical) would divide by zero.
  const pad = hi - lo < 1e-9 ? 1 : (hi - lo) * 0.08;
  const min = lo - pad;
  const max = hi + pad;

  const padLeft = 44;
  const padBottom = 28;
  const padTop = 10;
  const padRight = 10;
  const width = 320;
  const plotW = width - padLeft - padRight;
  const plotH = height - padTop - padBottom;

  const xPad = xHi - xLo < 1e-9 ? 1 : (xHi - xLo) * 0.04;
  const xMin = xLo - xPad;
  const xMax = xHi + xPad;

  const sx = (v: number) => padLeft + ((v - xMin) / (xMax - xMin)) * plotW;
  const sy = (v: number) => padTop + plotH - ((v - min) / (max - min)) * plotH;

  const xTicks = [xMin, (xMin + xMax) / 2, xMax];
  const ticks = [min, (min + max) / 2, max];
  const path = pairs
    .slice()
    .sort((a, b) => a.x - b.x)
    .map((d, i) => `${i === 0 ? "M" : "L"}${sx(d.x).toFixed(2)},${sy(d.y).toFixed(2)}`)
    .join(" ");
  const fmt = (v: number) => (Math.abs(v) >= 100 ? v.toFixed(0) : v.toFixed(2));

  return (
    <figure className={cn("w-full", className)}>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="h-auto w-full"
        role="img"
        aria-label={`Predicted versus actual values for ${pairs.length} test samples, with the identity line`}
      >
        <rect
          x={padLeft}
          y={padTop}
          width={plotW}
          height={plotH}
          fill="none"
          stroke={TOKEN.line}
          strokeWidth={1}
        />

        {/* Training target range, drawn first so the curve sits on top. */}
        {targetRange?.map((bound) => (
          <line
            key={`band-${bound}`}
            x1={padLeft}
            y1={sy(bound)}
            x2={padLeft + plotW}
            y2={sy(bound)}
            stroke={TOKEN.ink3}
            strokeWidth={1}
            strokeDasharray="4 3"
          />
        ))}

        <path d={path} fill="none" stroke={TOKEN.accent} strokeWidth={1.75} />

        {pairs.map((d, i) => (
          <circle key={i} cx={sx(d.x)} cy={sy(d.y)} r={2} fill={TOKEN.accent} />
        ))}

        {xTicks.map((t) => (
          <g key={`x-${t}`}>
            <text
              x={sx(t)}
              y={height - 8}
              textAnchor="middle"
              fontSize={9}
              fill={TOKEN.ink3}
              className="tabular-nums"
            >
              {fmt(t)}
            </text>
          </g>
        ))}
        {ticks.map((t) => (
          <g key={`y-${t}`}>
            <text
              x={padLeft - 6}
              y={sy(t) + 3}
              textAnchor="end"
              fontSize={9}
              fill={TOKEN.ink3}
              className="tabular-nums"
            >
              {fmt(t)}
            </text>
          </g>
        ))}

        <text
          x={padLeft + plotW / 2}
          y={height - 19}
          textAnchor="middle"
          fontSize={9}
          fill={TOKEN.ink3}
        >
          input x
        </text>
        <text
          x={12}
          y={padTop + plotH / 2}
          textAnchor="middle"
          fontSize={9}
          fill={TOKEN.ink3}
          transform={`rotate(-90 12 ${padTop + plotH / 2})`}
        >
          predicted{unitLabel ? ` (${unitLabel})` : ""}
        </text>
      </svg>
      <figcaption className="mt-1 max-w-[22rem] text-[10px] leading-relaxed text-ink-3">
        The model&rsquo;s own prediction across the input range, from the inference endpoint — not
        a comparison against held-out targets, which the API does not expose.
        {targetRange ? " Dashed lines are the training target range." : ""}
      </figcaption>
    </figure>
  );
}

/* -------------------------------------------------------------------------- */
/* Kernel Gram matrix heatmap (§2E.3)                                          */
/* -------------------------------------------------------------------------- */

/** Heatmap of the quantum kernel's Gram matrix.
 *
 *  Built the way `DensityMatrixInspector` builds its cells: a computed inline
 *  `style`, never an interpolated Tailwind class. `bg-opacity-${x}` would
 *  produce a class name that exists in the markup and in no stylesheet — the
 *  QL-001 failure that shipped the density-matrix heatmap invisible.
 *
 *  The matrix is symmetric with a unit diagonal, and the full square is drawn
 *  rather than a triangle, because showing half of a symmetric matrix invites
 *  the reader to wonder what is in the other half. The caption says so.
 */
export function KernelHeatmap({
  values,
  nTotal,
  truncated,
  className,
}: {
  values: number[][];
  /** Dimension of the full matrix; `values` may be a top-left corner of it. */
  nTotal: number;
  truncated: boolean;
  className?: string;
}) {
  const size = values.length;
  if (size === 0) {
    return (
      <div className={cn("text-xs text-ink-3", className)}>No kernel matrix available</div>
    );
  }

  // A quantum kernel from a normalised state overlap is already in [0, 1],
  // but the scale is computed rather than assumed so a different kernel does
  // not silently render as a single flat colour.
  const flat = values.flat().filter((v) => Number.isFinite(v));
  const lo = Math.min(...flat);
  const hi = Math.max(...flat);
  const span = hi - lo < 1e-12 ? 1 : hi - lo;

  const cell = size <= 20 ? 12 : size <= 40 ? 8 : 5;

  return (
    <figure className={cn("inline-block", className)}>
      <div
        className="grid gap-px rounded-md border border-line-soft p-1"
        style={{ gridTemplateColumns: `repeat(${size}, ${cell}px)` }}
        role="img"
        aria-label={
          `Quantum kernel Gram matrix, ${size} by ${size}` +
          (truncated ? `, the top-left corner of a ${nTotal} by ${nTotal} matrix` : "") +
          ". Symmetric with a unit diagonal."
        }
      >
        {values.map((row, r) =>
          row.map((v, c) => {
            const t = (v - lo) / span;
            return (
              <div
                key={`${r}-${c}`}
                style={{
                  width: cell,
                  height: cell,
                  // Inline style, computed. Never `bg-accent/${n}`.
                  backgroundColor: TOKEN.accent,
                  opacity: 0.12 + t * 0.88,
                }}
              />
            );
          }),
        )}
      </div>
      <figcaption className="mt-1 max-w-[22rem] text-[10px] leading-relaxed text-ink-3">
        {truncated
          ? `Top-left ${size}x${size} corner of the full ${nTotal}x${nTotal} matrix.`
          : `Full ${size}x${size} matrix.`}{" "}
        Symmetric, unit diagonal; the whole square is drawn rather than a triangle. Darker is a
        higher kernel value, scaled over {lo.toFixed(2)}-{hi.toFixed(2)}.
      </figcaption>
    </figure>
  );
}

export { TOKEN as CHART_TOKENS };
