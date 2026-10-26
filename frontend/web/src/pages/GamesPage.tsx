import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Gamepad2,
  Lock,
  Play,
  RotateCcw,
  Target,
  Wrench,
  CheckCircle2,
  XCircle,
  Circle,
  ChevronRight,
  ArrowLeft,
  Maximize2,
  Minimize2,
  ExternalLink,
  Sparkles,
  X,
} from "lucide-react";
import { ComposerInner } from "@composer/Composer";
import { maxLayer } from "@composer/ir";
import type { CircuitIR } from "@composer/types";
import { listGames, type GameLevel } from "../api/games";
import { getAttempt, submitChallenge, type ChallengeAttempt } from "../api/assessments";
import { circuitStamp, emptyCircuit, useCircuit } from "../state/circuit";
import { CountsBar } from "../components/demos/Demos";
import { GroverLab } from "../components/grover/GroverLab";
import { Badge, Button, Card, ErrorNote, Label, Select, SelectItem, Spinner, cn } from "../components/ui";
import { simulateCircuit } from "../lib/circuitSimulator";
import { Histogram } from "../components/results/ResultsViews";

const GROVER_SLUG = "grover-lab";

interface ScoredRun {
  outcome: ChallengeAttempt;
  stamp: string;
  slug: string;
}

export function GamesPage() {
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const slug = searchParams.get("slug");

  const setSlug = (newSlug: string | null) => {
    if (newSlug) {
      setSearchParams({ slug: newSlug });
    } else {
      setSearchParams({});
    }
  };

  const handleBack = () => {
    void queryClient.invalidateQueries({ queryKey: ["games"] });
    setSlug(null);
  };

  const games = useQuery({ queryKey: ["games"], queryFn: listGames, staleTime: 0 });
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
      <div className="flex items-center justify-center p-12 text-ink-3 text-sm">
        <Spinner className="mr-2" /> Loading interactive quantum games…
      </div>
    );
  }
  if (games.isError) return <ErrorNote className="m-6">{String(games.error)}</ErrorNote>;

  if (slug === GROVER_SLUG) {
    return (
      <div className="flex flex-col gap-5 p-6 max-w-5xl mx-auto">
        <div className="flex items-center justify-between border-b border-line pb-4">
          <nav aria-label="Breadcrumb" className="flex items-center gap-2 text-sm text-ink-3">
            <button onClick={handleBack} className="hover:text-ink transition-colors">
              Games
            </button>
            <ChevronRight className="h-3.5 w-3.5" />
            <span className="font-semibold text-ink">Quantum Password Search (Grover)</span>
          </nav>
          <Button size="sm" variant="secondary" onClick={handleBack} className="gap-1.5 text-xs">
            <ArrowLeft className="h-3.5 w-3.5" /> All games
          </Button>
        </div>
        <GroverLab />
      </div>
    );
  }

  if (all.length === 0) {
    return (
      <Card className="m-6">
        <p className="text-sm text-ink-3">No games are seeded yet.</p>
      </Card>
    );
  }

  return (
    <div
      className={cn(
        "flex flex-col gap-6 p-4 md:p-6 mx-auto transition-all duration-200",
        level ? "max-w-[1600px] w-full" : "max-w-5xl"
      )}
    >
      {level ? (
        <LevelPlay level={level} onBack={handleBack} />
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
  games: {
    game_id: string;
    title: string;
    blurb: string;
    icon: string;
    completed: number;
    total: number;
    levels: GameLevel[];
  }[];
  onPlay: (slug: string) => void;
}) {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-ink flex items-center gap-2.5">
          <Gamepad2 className="h-6 w-6 text-accent" /> Quantum Games & Puzzles
        </h1>
        <p className="text-sm text-ink-3 mt-1">
          Solve circuit puzzles through interactive gamified levels graded by our quantum state engine.
        </p>
      </div>

      {/* Featured Grover's Algorithm Card */}
      <Card className="border-accent/40 bg-accent/5 p-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-start gap-3.5 min-w-0 flex-1">
            <div className="grid h-10 w-10 place-items-center rounded-xl bg-accent/20 text-accent shrink-0">
              <Lock className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-ink">Quantum Password Search</h3>
              <p className="text-xs text-ink-2 mt-1 max-w-2xl leading-relaxed">
                Watch Grover&apos;s quantum search algorithm amplify the correct target state with geometric rotations instead of checking items one by one.
              </p>
            </div>
          </div>
          <Button size="md" variant="primary" onClick={() => onPlay(GROVER_SLUG)} className="px-5">
            Launch Simulation
          </Button>
        </div>
      </Card>

      {/* Game Categories */}
      {games.map((game) => (
        <Card key={game.game_id} className="p-6">
          <div className="mb-5 flex flex-wrap items-start justify-between gap-4 border-b border-line pb-4">
            <div className="min-w-0 flex-1">
              <h3 className="text-lg font-bold text-ink flex items-center gap-2">
                <span>{game.icon}</span> {game.title}
              </h3>
              <p className="text-xs text-ink-3 mt-1">{game.blurb}</p>
            </div>

            <div className="w-36 text-right">
              <span className="text-[11px] uppercase tracking-wider text-ink-3 font-semibold">
                Progress: {game.completed}/{game.total}
              </span>
              {game.total > 0 && (
                <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-subtle">
                  <div
                    className="h-full bg-ok transition-all duration-300"
                    style={{ width: `${(game.completed / game.total) * 100}%` }}
                  />
                </div>
              )}
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {game.levels.map((entry) => {
              const isPassed = entry.passed;
              return (
                <div
                  key={entry.slug}
                  className={cn(
                    "rounded-xl border p-4 flex flex-col justify-between transition-all",
                    isPassed
                      ? "border-ok/40 bg-ok/5"
                      : "border-line bg-subtle/40 hover:border-line-focus/40",
                  )}
                >
                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-xs font-bold text-ink flex items-center gap-1.5">
                        {isPassed ? (
                          <CheckCircle2 className="h-4 w-4 text-ok" />
                        ) : (
                          <Circle className="h-3 w-3 text-ink-3" />
                        )}
                        Level {entry.level}
                      </span>
                      {entry.attempts > 0 && (
                        <span className="text-[10px] text-ink-3 font-mono">
                          {entry.attempts} {entry.attempts === 1 ? "try" : "tries"}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-ink-2 font-medium line-clamp-2">
                      {entry.title.split(":").slice(-1)[0].trim()}
                    </p>
                  </div>

                  <Button
                    size="sm"
                    variant={isPassed ? "secondary" : "primary"}
                    className="mt-4 w-full text-xs"
                    onClick={() => onPlay(entry.slug)}
                  >
                    {isPassed ? "Replay" : "Play"}
                  </Button>
                </div>
              );
            })}
          </div>
        </Card>
      ))}
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Playing a Level                                                            */
/* -------------------------------------------------------------------------- */
export function LevelPlay({ level, onBack }: { level: GameLevel; onBack: () => void }) {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const ir = useCircuit((state) => state.ir);
  const setIr = useCircuit((state) => state.setIr);
  const resetCircuit = useCircuit((state) => state.reset);

  const [shots, setShots] = useState(1024);
  const [scored, setScored] = useState<ScoredRun | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showLiveSim, setShowLiveSim] = useState(false);

  // Client-side live analytical preview. Capped at PREVIEW_MAX_QUBITS (12);
  // game levels are 2-6 qubits so the cap is never hit in practice.
  const liveResult = useMemo(() => simulateCircuit(ir), [ir]);

  useEffect(() => {
    if (level.starter_ir) {
      setIr(level.starter_ir as unknown as CircuitIR);
    } else {
      const maxQ = Number(level.constraints?.max_qubits);
      if (Number.isFinite(maxQ) && maxQ > 0 && ir.n_qubits !== maxQ) {
        resetCircuit(emptyCircuit(maxQ));
      }
    }
    setScored(null);
  }, [level.slug, level.starter_ir]);

  const submit = useMutation({
    mutationFn: () => submitChallenge(level.slug, ir, shots),
    onSuccess: (attempt) => {
      setScored({ outcome: attempt, stamp: circuitStamp(ir), slug: level.slug });
      void queryClient.invalidateQueries({ queryKey: ["games"] });
      void queryClient.invalidateQueries({ queryKey: ["progress", "me"] });
      void queryClient.invalidateQueries({ queryKey: ["challenges"] });
    },
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

  useEffect(() => {
    if (outcome.data?.status === "graded") {
      void queryClient.invalidateQueries({ queryKey: ["games"] });
      void queryClient.invalidateQueries({ queryKey: ["progress", "me"] });
      void queryClient.invalidateQueries({ queryKey: ["challenges"] });
    }
  }, [outcome.data?.status, queryClient]);

  const graded = outcome.data?.status === "graded" ? outcome.data : null;

  const stale =
    scored !== null && (scored.slug !== level.slug || scored.stamp !== circuitStamp(ir));

  const rules: string[] = [];
  if (level.allowed_gates.length > 0) {
    rules.push(`Allowed gates: ${level.allowed_gates.map((g) => g.toUpperCase()).join(", ")}`);
  }
  const constraints = level.constraints ?? {};
  if (constraints.max_qubits) rules.push(`Max qubits: ${String(constraints.max_qubits)}`);
  if (constraints.max_depth) rules.push(`Max depth: ${String(constraints.max_depth)}`);
  if (level.max_edits !== null && level.max_edits !== undefined) {
    rules.push(`Edit budget: ${level.max_edits}`);
  }
  if (level.epsilon !== null && level.epsilon !== undefined) {
    rules.push(`Tolerance: ${level.epsilon}`);
  }
  if (level.n_controls) {
    rules.push(`Checked over all ${2 ** (level.n_controls + 1)} basis inputs`);
  }

  const handleOpenInStudio = () => {
    useCircuit.getState().setChallengeContext({
      challengeId: level.slug,
      title: level.title,
      returnPath: `/games?slug=${level.slug}`,
    });
    navigate("/composer");
  };

  return (
    <div className="space-y-6">
      {/* Fullscreen Overlay Mode */}
      {isFullscreen && (
        <div className="fixed inset-0 z-50 flex flex-col bg-[#070b14] overflow-hidden">
          <div className="flex items-center justify-between border-b border-line bg-subtle px-6 py-3 shrink-0">
            <div className="flex items-center gap-4">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setIsFullscreen(false)}
                className="gap-1.5 text-xs font-medium"
              >
                <Minimize2 className="h-3.5 w-3.5" /> Exit Fullscreen
              </Button>
              <div className="flex items-center gap-2">
                <span className="font-bold text-sm text-ink">{level.title}</span>
                <span className="text-xs text-ink-3 font-mono">
                  {ir.n_qubits} qubits · depth {maxLayer(ir.ops) + 1} · {ir.ops.length} ops
                </span>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <Button
                variant="primary"
                size="sm"
                disabled={submit.isPending}
                onClick={() => submit.mutate()}
                className="gap-1.5 text-xs font-semibold px-4"
              >
                {submit.isPending ? <Spinner className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}
                Run & score
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsFullscreen(false)}
                className="text-xs text-ink-3 hover:text-ink"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </div>

          <div className="flex-1 composer-host dark bg-[#090d18] p-4 overflow-auto">
            <ComposerInner
              value={ir}
              nQubits={ir.n_qubits}
              onChange={setIr}
              theme={{ base: "dark" }}
            />
          </div>
        </div>
      )}

      {/* Top Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line pb-3">
        <div className="flex items-center gap-3">
          <Button
            size="sm"
            variant="secondary"
            onClick={() => {
              void queryClient.invalidateQueries({ queryKey: ["games"] });
              onBack();
            }}
            className="gap-1.5 text-xs"
          >
            <ArrowLeft className="h-3.5 w-3.5" /> All games
          </Button>
          <h2 className="text-xl font-bold tracking-tight text-ink">{level.title}</h2>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsFullscreen(true)}
            className="gap-1.5 text-xs text-ink-2 hover:text-ink"
            title="Open Fullscreen Focus Mode"
          >
            <Maximize2 className="h-3.5 w-3.5" /> Fullscreen
          </Button>

          <Button
            variant="secondary"
            size="sm"
            onClick={handleOpenInStudio}
            className="gap-1.5 text-xs text-accent hover:text-accent font-medium"
            title="Open in dedicated Studio Composer with Q-Sphere and full analysis"
          >
            <ExternalLink className="h-3.5 w-3.5" /> Open in Studio
          </Button>

          <Button
            variant="primary"
            size="sm"
            disabled={submit.isPending}
            onClick={() => submit.mutate()}
            className="gap-1.5 text-xs font-semibold px-4"
          >
            {submit.isPending ? <Spinner className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}
            Run & score
          </Button>
        </div>
      </div>

      {/* Objective Card */}
      <Card className="p-5">
        <div className="flex items-center gap-2 mb-2 text-ink">
          <Target className="h-5 w-5 text-accent" />
          <h3 className="text-sm font-bold uppercase tracking-wider">🎯 Objective</h3>
        </div>
        <p className="whitespace-pre-line text-sm leading-relaxed text-ink-2">{level.prompt}</p>

        {rules.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-2 text-xs text-ink-3 pt-3 border-t border-line-soft">
            {rules.map((rule) => (
              <span key={rule} className="bg-subtle px-2.5 py-1 rounded-md border border-line">
                {rule}
              </span>
            ))}
          </div>
        )}

        {level.attempts > 0 && (
          <p className="mt-3 text-xs text-ink-3">
            Your best: <strong className="text-ink">{level.best_score.toFixed(2)}</strong> (
            {level.passed ? "passed" : "not passed yet"}) over {level.attempts} attempt(s).
          </p>
        )}
      </Card>

      {/* Build Circuit Card - Spacious Workbench */}
      <div className="rounded-2xl border border-line bg-raised shadow-xl overflow-hidden">
        {/* Studio Workbench Header Bar */}
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line bg-subtle px-4 py-3">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <Wrench className="h-4 w-4 text-accent" />
              <span className="text-xs sm:text-sm font-bold uppercase tracking-wider text-ink">
                Quantum Circuit Composer
              </span>
            </div>
            <span className="text-xs font-mono text-ink-3">
              {ir.n_qubits} qubits · depth {maxLayer(ir.ops) + 1} · {ir.ops.length} ops
            </span>
            {stale && scored && (
              <Badge tone="warn" className="text-[11px] animate-pulse">
                Unsaved Changes
              </Badge>
            )}
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowLiveSim((prev) => !prev)}
              className="gap-1.5 text-xs text-ink-2 hover:text-ink"
            >
              <Sparkles className="h-3.5 w-3.5 text-accent" />
              {showLiveSim ? "Hide Live State" : "Live State Preview"}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsFullscreen(true)}
              className="gap-1.5 text-xs text-ink-2 hover:text-ink"
              title="Maximize Composer Canvas to full screen"
            >
              <Maximize2 className="h-3.5 w-3.5" /> Maximize
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={handleOpenInStudio}
              className="gap-1.5 text-xs text-accent hover:text-accent font-medium"
              title="Open in dedicated Studio Composer with Q-Sphere and full analysis"
            >
              <ExternalLink className="h-3.5 w-3.5" /> Open in Studio
            </Button>
          </div>
        </div>

        {/* How the grid is operated. Without this the composer is a puzzle
            before the level is. */}
        <p className="border-b border-line bg-subtle/50 px-4 py-2.5 text-xs text-ink-3">
          Drag a gate from the palette onto the grid, or click a gate then click a cell. For
          controlled gates, drop on the target first, then click the control qubits in the same
          column.
        </p>

        {/* Composer Canvas */}
        <div className="composer-host dark bg-[#090d18] p-3 md:p-5 min-h-[440px] overflow-x-auto">
          <ComposerInner
            value={ir}
            nQubits={ir.n_qubits}
            onChange={setIr}
            theme={{ base: "dark" }}
          />
        </div>

        {/* Live Simulation Collapsible Panel */}
        {showLiveSim && (
          <div className="border-t border-line bg-subtle/70 p-4 animate-in fade-in duration-200">
            <Histogram
              result={liveResult}
              title="Live Quantum State (Simulation Preview)"
              subtitle="Instant analytical probability distribution before submitting"
              circuitLabel={`${ir.n_qubits}Q Statevector`}
            />
          </div>
        )}

        {/* Studio Bottom Toolbar */}
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line bg-subtle/80 px-4 py-3">
          <div className="flex flex-wrap items-center gap-3">
            <Button
              variant="primary"
              size="md"
              disabled={submit.isPending}
              onClick={() => submit.mutate()}
              className="gap-2 px-5 font-semibold shadow-md"
            >
              {submit.isPending ? <Spinner className="h-4 w-4" /> : <Play className="h-4 w-4" />}
              Run & score
            </Button>

            <Button
              size="md"
              variant="secondary"
              onClick={() => {
                resetCircuit(emptyCircuit(level.constraints?.max_qubits ? Number(level.constraints.max_qubits) : 2));
                setScored(null);
              }}
              className="gap-1.5 text-xs"
            >
              <RotateCcw className="h-3.5 w-3.5" /> Clear circuit
            </Button>

            {level.starter_ir && (
              <Button
                size="md"
                variant="secondary"
                onClick={() => {
                  setIr(level.starter_ir as unknown as CircuitIR);
                  setScored(null);
                }}
                className="gap-1.5 text-xs"
              >
                Reset to broken
              </Button>
            )}
          </div>

          {level.grader === "shot_detective" && (
            <div className="flex items-center gap-2">
              <Label className="text-xs text-ink-3">
                Shots — fewer scores higher, but you must stay within tolerance
              </Label>
              <Select
                value={String(shots)}
                onValueChange={(val) => setShots(Number(val))}
                className="h-8 w-28 text-xs bg-bg"
              >
                {[128, 256, 512, 1024, 2048, 4096].map((s) => (
                  <SelectItem key={s} value={String(s)}>
                    {s} shots
                  </SelectItem>
                ))}
              </Select>
            </div>
          )}
        </div>

        {submit.isError && <ErrorNote className="m-4">{String(submit.error)}</ErrorNote>}

        {stale && scored && (
          <p className="m-4 rounded-lg border border-warn/30 bg-warn/10 px-3 py-2 text-xs text-ink-2">
            You modified the circuit since the last evaluation. Click <strong>Run & score</strong> to grade what is currently on the grid.
          </p>
        )}

        {attemptId !== null && !graded && !stale && (
          <div className="m-4 flex items-center gap-2 text-xs text-ink-3">
            <Spinner className="h-4 w-4" /> Simulating and evaluating… ({outcome.data?.status ?? "queued"})
          </div>
        )}

        {graded && !stale && (
          <div className="p-4 border-t border-line">
            <LevelResult outcome={graded} />
          </div>
        )}
      </div>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Level Result Details                                                       */
/* -------------------------------------------------------------------------- */
export function LevelResult({ outcome }: { outcome: ChallengeAttempt }) {
  const details = (outcome.details ?? {}) as Record<string, unknown>;
  const extra = (details.game ?? {}) as any;
  const note = String(details.behaviour_note ?? "");
  const counts = details.counts as Record<string, number> | undefined;

  return (
    <div className="mt-6 rounded-xl border border-line bg-raised p-5 space-y-4">
      <div className="flex items-center justify-between">
        <h4 className="text-base font-bold text-ink">Evaluation Summary</h4>
        <Badge
          tone={outcome.passed ? "ok" : "warn"}
          className="text-sm px-3 py-1 font-semibold"
        >
          {outcome.passed
            ? `Level complete — score ${outcome.score.toFixed(2)}`
            : `Not yet — score ${outcome.score.toFixed(2)}`}
        </Badge>
      </div>

      {outcome.feedback && (
        <p className="text-xs text-ink-2 leading-relaxed">{outcome.feedback}</p>
      )}

      {/* Truth table. Always shown, pass or fail: on a win it is the proof the
          logic is right, which is exactly when a learner wants to read it. */}
      {extra.testcases_total !== undefined && (
        <div className="space-y-3 pt-2">
          <div className="flex gap-2">
            <Badge tone={extra.testcases_passed === extra.testcases_total ? "ok" : "warn"}>
              Test cases passed {extra.testcases_passed}/{extra.testcases_total}
            </Badge>
            {Boolean(extra.superposed) && (
              <Badge tone="warn">Superposed outputs {extra.superposed}</Badge>
            )}
          </div>

          {Boolean(extra.superposed) && (
            <p className="rounded-lg border border-warn/40 bg-warn/10 px-3 py-2 text-xs text-ink">
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
                  <p className="mb-1 text-xs text-ink-3">
                    Showing the failing inputs from this older attempt.
                  </p>
                )}
                <div className="overflow-x-auto rounded-lg border border-line">
                  <table className="w-full text-xs">
                    <thead className="bg-subtle text-ink-3 uppercase text-[10px] tracking-wider border-b border-line">
                      <tr>
                        <th className="px-3 py-2 text-left">Status</th>
                        <th className="px-3 py-2 text-left font-mono">Input |c…t⟩</th>
                        <th className="px-3 py-2 text-left font-mono">Output</th>
                        <th className="px-3 py-2 text-left font-mono">Target should be</th>
                        <th className="px-3 py-2 text-left font-mono">Target was</th>
                        <th className="px-3 py-2 text-left">Controls preserved</th>
                        <th className="px-3 py-2 text-left">Certainty</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-line-soft font-mono">
                      {rows.map((row: any) => (
                        <tr key={row.input} className="hover:bg-hover/50">
                          <td className="px-3 py-1.5">
                            {row.passed ? (
                              <CheckCircle2 className="h-4 w-4 text-ok" />
                            ) : (
                              <XCircle className="h-4 w-4 text-danger" />
                            )}
                          </td>
                          <td className="px-3 py-1.5">{row.input}</td>
                          <td className="px-3 py-1.5">{row.output ?? "—"}</td>
                          <td className="px-3 py-1.5">{row.expected_target}</td>
                          <td className="px-3 py-1.5">{row.got_target}</td>
                          <td className="px-3 py-1.5">{row.controls_intact ? "yes" : "no"}</td>
                          <td className="px-3 py-1.5">
                            {row.certainty === undefined
                              ? "—"
                              : `${Math.round(row.certainty * 100)}%`}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {/* How to read the table. Without this a learner cannot tell
                    which character is the target. */}
                <p className="mt-2 text-[11px] text-ink-3">
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
        <div className="pt-2">
          <p className="mb-1 text-sm font-semibold text-ink">How the error shrinks with more shots</p>
          <p className="mb-2 text-xs text-ink-3">
            Measured by subsampling one run, so this whole curve costs a single simulation.
          </p>
          <CurveChart points={extra.curve} />
          <div className="overflow-x-auto rounded-lg border border-line">
            <table className="w-full text-xs">
              <thead className="bg-subtle text-ink-3 uppercase text-[10px] tracking-wider border-b border-line">
                <tr>
                  <th className="px-3 py-2 text-left font-mono">Shots</th>
                  <th className="px-3 py-2 text-left font-mono">Error (TVD)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line-soft font-mono">
                {extra.curve.map((point: { shots: number; tvd: number }) => (
                  <tr key={point.shots} className="hover:bg-hover/50">
                    <td className="px-3 py-1.5">{point.shots}</td>
                    <td className="px-3 py-1.5">{point.tvd.toFixed(4)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Find the Bug: the edit budget. */}
      {extra.edits && (
        <div className="grid grid-cols-2 gap-2 pt-2 lg:grid-cols-4">
          <MetricCard
            label="Edits used"
            value={String(extra.edits.total)}
            delta={`budget ${extra.max_edits}`}
          />
          <MetricCard label="Modified" value={String(extra.edits.modified)} />
          <MetricCard label="Added" value={String(extra.edits.added)} />
          <MetricCard label="Removed" value={String(extra.edits.removed)} />
        </div>
      )}

      {/* State-graded levels: the histogram alone cannot tell |Φ+⟩ from |Φ−⟩,
          so surface the fidelity that actually decided the result. */}
      {note.toLowerCase().includes("fidelity") && (
        <p className="text-xs text-ink-3">Graded on state fidelity — {note}</p>
      )}

      {counts && (
        <div className="pt-2">
          <p className="text-xs font-semibold text-ink-3 uppercase tracking-wider mb-2">
            Measurement outcomes
          </p>
          <CountsBar counts={counts} />
          {note.toLowerCase().includes("fidelity") && (
            <p className="mt-2 text-xs text-ink-3">
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
      <polyline
        points={coordinates.join(" ")}
        fill="none"
        stroke="var(--color-accent)"
        strokeWidth={2}
      />
      {coordinates.map((coordinate) => {
        const [cx, cy] = coordinate.split(",");
        return <circle key={coordinate} cx={cx} cy={cy} r={3} fill="var(--color-accent)" />;
      })}
    </svg>
  );
}
