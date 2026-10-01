import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ComposerInner } from "@composer/Composer";
import { maxLayer } from "@composer/ir";
import type { CircuitIR } from "@composer/types";
import { listGames, type GameLevel } from "../api/games";
import { getAttempt, submitChallenge, type ChallengeAttempt } from "../api/assessments";
import { circuitStamp, emptyCircuit, useCircuit } from "../state/circuit";
import { useTheme } from "../state/theme";
import { CountsBar } from "../components/demos/Demos";
import { Badge, Button, Card, ErrorNote, Spinner, cn } from "../components/ui";

/** A result describes the circuit that was graded — see the note in LevelPlay. */
interface ScoredRun {
  outcome: ChallengeAttempt;
  stamp: string;
  slug: string;
}

export function GamesPage() {
  const [slug, setSlug] = useState<string | null>(null);

  const games = useQuery({ queryKey: ["games"], queryFn: listGames, staleTime: 30_000 });
  const all = games.data?.games ?? [];

  const level = useMemo(() => {
    for (const game of all) {
      const found = game.levels.find((candidate) => candidate.slug === slug);
      if (found) return found;
    }
    return null;
  }, [all, slug]);

  if (games.isLoading) {
    return (
      <p className="flex items-center gap-2 p-6 text-sm text-ink-3">
        <Spinner /> loading games…
      </p>
    );
  }
  if (games.isError) return <ErrorNote className="m-6">{String(games.error)}</ErrorNote>;
  if (all.length === 0) {
    return (
      <Card className="m-6">
        <p className="text-[13px] text-ink-3">No games are seeded yet.</p>
      </Card>
    );
  }

  return (
    <div className="flex flex-col gap-5 p-6">
      {level ? (
        <LevelPlay level={level} onBack={() => setSlug(null)} />
      ) : (
        <Catalogue games={all} onPlay={setSlug} />
      )}
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Catalogue                                                                  */
/* -------------------------------------------------------------------------- */

export function Catalogue({
  games,
  onPlay,
}: {
  games: { game_id: string; title: string; blurb: string; icon: string; completed: number; total: number; levels: GameLevel[] }[];
  onPlay: (slug: string) => void;
}) {
  return (
    <>
      <p className="text-[13px] text-ink-3">
        Each level is a real circuit puzzle, graded by the same engine as the coding challenges.
        Pick one to start.
      </p>
      {games.map((game) => (
        <Card key={game.game_id}>
          <div className="mb-4 flex flex-wrap items-start gap-3">
            <div className="min-w-0 flex-1">
              <h3 className="text-base font-semibold text-ink">
                {game.icon} {game.title}
              </h3>
              <p className="text-[13px] text-ink-3">{game.blurb}</p>
            </div>
            <div className="w-40">
              <p className="text-[11px] uppercase tracking-wide text-ink-3">Progress</p>
              <p className="text-sm font-semibold text-ink">
                {game.completed}/{game.total}
              </p>
              {game.total > 0 && (
                <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-hover">
                  <div
                    className="h-full bg-accent"
                    style={{ width: `${(game.completed / game.total) * 100}%` }}
                  />
                </div>
              )}
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {game.levels.map((entry) => (
              <div key={entry.slug} className="rounded-lg border border-line p-3">
                <p className="text-[13px] font-semibold text-ink">
                  {entry.passed ? "✅" : "•"} Level {entry.level}
                </p>
                <p className="text-[12px] text-ink-3">{entry.title.split(":").slice(-1)[0].trim()}</p>
                {entry.attempts > 0 && (
                  <p className="text-[11px] text-ink-3">
                    best {entry.best_score.toFixed(2)} · {entry.attempts} tries
                  </p>
                )}
                <Button size="sm" variant="primary" className="mt-2 w-full" onClick={() => onPlay(entry.slug)}>
                  Play
                </Button>
              </div>
            ))}
          </div>
        </Card>
      ))}
    </>
  );
}

/* -------------------------------------------------------------------------- */
/* Playing a level                                                            */
/* -------------------------------------------------------------------------- */

export function LevelPlay({ level, onBack }: { level: GameLevel; onBack: () => void }) {
  const ir = useCircuit((state) => state.ir);
  const setIr = useCircuit((state) => state.setIr);
  const epoch = useCircuit((state) => state.epoch);
  const resetCircuit = useCircuit((state) => state.reset);
  const { theme } = useTheme();

  const [shots, setShots] = useState(1024);
  const [scored, setScored] = useState<ScoredRun | null>(null);

  const submit = useMutation({
    mutationFn: () => submitChallenge(level.slug, ir, shots),
    onSuccess: (attempt) =>
      setScored({ outcome: attempt, stamp: circuitStamp(ir), slug: level.slug }),
  });

  const attemptId = submit.data?.attempt_id ?? null;
  const outcome = useQuery({
    queryKey: ["attempt", attemptId],
    queryFn: () => getAttempt(attemptId as number),
    enabled: attemptId !== null,
    refetchInterval: (query) =>
      query.state.data?.status === "graded" || query.state.data?.status === "failed" ? false : 500,
    staleTime: 0,
  });

  const graded = outcome.data?.status === "graded" ? outcome.data : null;

  // A result describes the circuit that was graded, not whatever is on the
  // grid now. Showing a stale "Level complete" beside an edited circuit reads
  // as the game accepting a wrong answer.
  const stale =
    scored !== null && (scored.slug !== level.slug || scored.stamp !== circuitStamp(ir));

  const rules: string[] = [];
  if (level.allowed_gates.length > 0) {
    rules.push(`**Allowed gates:** ${level.allowed_gates.map((g) => g.toUpperCase()).join(", ")}`);
  }
  const constraints = level.constraints ?? {};
  if (constraints.max_qubits) rules.push(`**Max qubits:** ${String(constraints.max_qubits)}`);
  if (constraints.max_depth) rules.push(`**Max depth:** ${String(constraints.max_depth)}`);
  if (level.max_edits !== null && level.max_edits !== undefined) {
    rules.push(`**Edit budget:** ${level.max_edits}`);
  }
  if (level.epsilon !== null && level.epsilon !== undefined) {
    rules.push(`**Tolerance:** ${level.epsilon}`);
  }
  if (level.n_controls) {
    rules.push(`**Checked over all ${2 ** (level.n_controls + 1)} basis inputs**`);
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="text-lg font-semibold tracking-tight">{level.title}</h2>
        <Button size="sm" className="ml-auto" onClick={onBack}>
          ← All games
        </Button>
      </div>

      <Card>
        <h3 className="mb-2 text-sm font-semibold">🎯 Objective</h3>
        <p className="whitespace-pre-line text-[13px] leading-relaxed text-ink-2">{level.prompt}</p>
        {rules.length > 0 && (
          <p className="mt-2 text-[12px] text-ink-3">
            {rules.map((rule, index) => (
              <span key={rule}>
                {index > 0 && " • "}
                {rule.replace(/\*\*/g, "")}
              </span>
            ))}
          </p>
        )}
        {level.attempts > 0 && (
          <p className="mt-2 text-[12px] text-ink-3">
            Your best: <strong className="text-ink-2">{level.best_score.toFixed(2)}</strong> (
            {level.passed ? "passed" : "not passed yet"}) over {level.attempts} attempt(s).
          </p>
        )}
      </Card>

      <Card>
        <h3 className="mb-2 text-sm font-semibold">🛠 Build your circuit</h3>
        <p className="mb-3 text-[13px] text-ink-3">
          Drag a gate from the palette onto the grid, or click a gate then click a cell. For
          controlled gates, drop on the target first, then click the control qubits in the same
          column.
        </p>
        <div className={cn("composer-host", theme === "dark" && "dark")}>
          <ComposerInner key={epoch} value={ir} nQubits={ir.n_qubits} onChange={setIr} />
        </div>
        <p className="mt-2 text-[12px] text-ink-3">
          {ir.n_qubits} qubits · depth {maxLayer(ir.ops) + 1} · {ir.ops.length} ops
        </p>

        {level.grader === "shot_detective" && (
          <label className="mt-3 block text-[13px] text-ink-2">
            Shots — fewer scores higher, but you must stay within tolerance
            <select
              value={shots}
              onChange={(e) => setShots(Number(e.target.value))}
              className="mt-1 h-9 w-full max-w-xs rounded-lg border border-line bg-raised px-2 text-sm text-ink"
            >
              {[128, 256, 512, 1024, 2048, 4096].map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
        )}

        <div className="mt-3 flex flex-wrap gap-2">
          <Button variant="primary" disabled={submit.isPending} onClick={() => submit.mutate()}>
            {submit.isPending ? <Spinner /> : null}
            ▶ Run &amp; score
          </Button>
          <Button onClick={() => { resetCircuit(emptyCircuit(2)); setScored(null); }}>
            ↺ Clear circuit
          </Button>
          {level.starter_ir && (
            <Button
              onClick={() => {
                setIr(level.starter_ir as unknown as CircuitIR);
                setScored(null);
              }}
            >
              ⟲ Reset to broken
            </Button>
          )}
        </div>
        {submit.isError && <ErrorNote className="mt-3">{String(submit.error)}</ErrorNote>}

        {stale && scored && (
          <p className="mt-3 rounded-lg border border-line bg-raised px-3 py-2 text-[13px] text-ink-2">
            You have changed the circuit since the last run. Press <strong>Run &amp; score</strong>{" "}
            to grade what is on the grid now.
          </p>
        )}

        {attemptId !== null && !graded && !stale && (
          <p className="mt-3 flex items-center gap-2 text-[13px] text-ink-3">
            <Spinner /> Simulating and grading… ({outcome.data?.status ?? "queued"})
          </p>
        )}

        {graded && !stale && <LevelResult outcome={graded} />}
      </Card>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Results                                                                    */
/* -------------------------------------------------------------------------- */

interface GameDetails {
  testcases_total?: number;
  testcases_passed?: number;
  superposed?: number;
  table?: {
    passed: boolean;
    input: string;
    output?: string;
    expected_target: string;
    got_target: string;
    controls_intact: boolean;
    certainty?: number;
  }[];
  failures?: { passed: boolean; input: string; output?: string; expected_target: string; got_target: string; controls_intact: boolean; certainty?: number }[];
  curve?: { shots: number; tvd: number }[];
  edits?: { total: number; modified: number; added: number; removed: number };
  max_edits?: number;
}

/** Exported so the render harness can check each grader's result panel
 *  against real grader output. */
export function LevelResult({ outcome }: { outcome: ChallengeAttempt }) {
  const details = (outcome.details ?? {}) as Record<string, unknown>;
  const extra = (details.game ?? {}) as GameDetails;
  const note = String(details.behaviour_note ?? "");
  const counts = details.counts as Record<string, number> | undefined;

  return (
    <div className="mt-4 flex flex-col gap-4 border-t border-line-soft pt-4">
      {outcome.passed ? (
        <p className="rounded-lg border border-ok/40 bg-ok/10 px-3 py-2 text-[13px] font-semibold text-ink">
          Level complete — score {outcome.score.toFixed(2)}
        </p>
      ) : (
        <p className="rounded-lg border border-warn/40 bg-warn/10 px-3 py-2 text-[13px] font-semibold text-ink">
          Not yet — score {outcome.score.toFixed(2)}
        </p>
      )}
      {outcome.feedback && <p className="text-[13px] text-ink-2">{outcome.feedback}</p>}

      {/* Truth table. Always shown, pass or fail: on a win it is the proof the
          logic is right, which is exactly when a learner wants to read it. */}
      {extra.testcases_total !== undefined && (
        <div>
          <div className="mb-2 flex gap-3">
            <Badge tone={extra.testcases_passed === extra.testcases_total ? "accent" : "warn"}>
              Test cases passed {extra.testcases_passed}/{extra.testcases_total}
            </Badge>
            {Boolean(extra.superposed) && <Badge tone="warn">Superposed outputs {extra.superposed}</Badge>}
          </div>
          {Boolean(extra.superposed) && (
            <p className="mb-2 rounded-lg border border-warn/40 bg-warn/10 px-3 py-2 text-[12px] text-ink">
              Some inputs left the register in a <strong>superposition</strong>, so there is no
              single output bitstring to check. This level is about classical logic — build it from
              X and controlled-X gates only.
            </p>
          )}
          {(() => {
            const rows = extra.table ?? extra.failures ?? [];
            if (rows.length === 0) return null;
            return (
              <div>
                {!extra.table && (
                  <p className="mb-1 text-[12px] text-ink-3">
                    Showing the failing inputs from this older attempt.
                  </p>
                )}
                <div className="overflow-auto rounded-lg border border-line-soft">
                  <table className="w-full text-[12px]">
                    <thead>
                      <tr className="border-b border-line bg-hover/40 text-left text-[11px] uppercase tracking-wide text-ink-3">
                        <th className="px-2 py-1.5" />
                        <th className="px-2 py-1.5 font-medium">Input |c…t⟩</th>
                        <th className="px-2 py-1.5 font-medium">Output</th>
                        <th className="px-2 py-1.5 font-medium">Target should be</th>
                        <th className="px-2 py-1.5 font-medium">Target was</th>
                        <th className="px-2 py-1.5 font-medium">Controls preserved</th>
                        <th className="px-2 py-1.5 font-medium">Certainty</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rows.map((row) => (
                        <tr key={row.input} className="border-b border-line-soft/60 last:border-0">
                          <td className="px-2 py-1">{row.passed ? "✅" : "❌"}</td>
                          <td className="px-2 py-1 font-mono">{row.input}</td>
                          <td className="px-2 py-1 font-mono">{row.output ?? "—"}</td>
                          <td className="px-2 py-1 font-mono">{row.expected_target}</td>
                          <td className="px-2 py-1 font-mono">{row.got_target}</td>
                          <td className="px-2 py-1">{row.controls_intact ? "yes" : "no"}</td>
                          <td className="px-2 py-1 font-mono">
                            {row.certainty === undefined ? "—" : `${Math.round(row.certainty * 100)}%`}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <p className="mt-1 text-[11px] text-ink-3">
                  Controls are the left characters, the target is the rightmost. A correct vault
                  flips the target only when every control is 1, and leaves the controls untouched.
                </p>
              </div>
            );
          })()}
        </div>
      )}

      {/* Shot Detective: the convergence curve is the whole lesson. */}
      {extra.curve && extra.curve.length > 0 && (
        <div>
          <p className="mb-1 text-[13px] font-semibold">How the error shrinks with more shots</p>
          <p className="mb-2 text-[12px] text-ink-3">
            Measured by subsampling one run, so this whole curve costs a single simulation.
          </p>
          <CurveChart points={extra.curve} />
          <div className="overflow-auto rounded-lg border border-line-soft">
            <table className="w-full text-[12px]">
              <thead>
                <tr className="border-b border-line bg-hover/40 text-left text-[11px] uppercase tracking-wide text-ink-3">
                  <th className="px-2 py-1.5 font-medium">Shots</th>
                  <th className="px-2 py-1.5 font-medium">Error (TVD)</th>
                </tr>
              </thead>
              <tbody>
                {extra.curve.map((point) => (
                  <tr key={point.shots} className="border-b border-line-soft/60 last:border-0">
                    <td className="px-2 py-1 font-mono">{point.shots}</td>
                    <td className="px-2 py-1 font-mono">{point.tvd.toFixed(4)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Find the Bug: the edit budget. */}
      {extra.edits && (
        <div className="grid grid-cols-2 gap-2 lg:grid-cols-4">
          <MetricCard label="Edits used" value={String(extra.edits.total)} delta={`budget ${extra.max_edits}`} />
          <MetricCard label="Modified" value={String(extra.edits.modified)} />
          <MetricCard label="Added" value={String(extra.edits.added)} />
          <MetricCard label="Removed" value={String(extra.edits.removed)} />
        </div>
      )}

      {/* State-graded levels: the histogram alone cannot tell |Φ+⟩ from |Φ−⟩,
          so surface the fidelity that actually decided the result. */}
      {note.toLowerCase().includes("fidelity") && (
        <p className="text-[12px] text-ink-3">Graded on state fidelity — {note}</p>
      )}

      {counts && (
        <div>
          <p className="mb-2 text-[13px] font-semibold">Measurement outcomes</p>
          <CountsBar counts={counts} />
          {note.toLowerCase().includes("fidelity") && (
            <p className="mt-2 text-[12px] text-ink-3">
              Two different states can produce this same histogram. That is why these levels are
              graded on the state, not the counts.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function MetricCard({ label, value, delta }: { label: string; value: string; delta?: string }) {
  return (
    <div className="rounded-lg border border-line bg-raised px-3 py-2">
      <p className="text-[11px] uppercase tracking-wide text-ink-3">{label}</p>
      <p className="font-mono text-sm text-ink">{value}</p>
      {delta && <p className="text-[11px] text-ink-3">{delta}</p>}
    </div>
  );
}

/** The convergence curve, drawn rather than charted — it is one polyline. */
function CurveChart({ points }: { points: { shots: number; tvd: number }[] }) {
  const width = 480;
  const height = 140;
  const padding = 24;
  const peak = Math.max(...points.map((p) => p.tvd), 1e-9);
  const xs = points.map((p) => Math.log2(p.shots));
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const spanX = maxX - minX || 1;

  const coordinates = points.map((point, index) => {
    const x = padding + ((xs[index] - minX) / spanX) * (width - padding * 2);
    const y = height - padding - (point.tvd / peak) * (height - padding * 2);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className="mb-2 h-36 w-full rounded-lg border border-line-soft bg-raised"
      role="img"
      aria-label="Sampling error against shots"
    >
      <line
        x1={padding}
        y1={height - padding}
        x2={width - padding}
        y2={height - padding}
        stroke="var(--line)"
      />
      <line x1={padding} y1={padding} x2={padding} y2={height - padding} stroke="var(--line)" />
      <polyline
        points={coordinates.join(" ")}
        fill="none"
        stroke="var(--accent)"
        strokeWidth="2"
      />
      {points.map((point, index) => {
        const [x, y] = coordinates[index].split(",").map(Number);
        return <circle key={point.shots} cx={x} cy={y} r="2.5" fill="var(--accent)" />;
      })}
    </svg>
  );
}
