import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { listQuizzes, submitQuiz, type Quiz, type QuizResult } from "../api/lessons";
import {
  getAttempt,
  listChallenges,
  submitChallenge,
  type Challenge,
} from "../api/assessments";
import { useCircuit } from "../state/circuit";
import { useTheme } from "../state/theme";
import { circuitIsDynamic } from "@composer/ir";
import { CircuitDiagram } from "../components/results/CircuitDiagram";
import { CountsBar } from "../components/demos/Demos";
import { Markdown } from "../components/Markdown";
import { Badge, Button, Card, ErrorNote, Spinner, cn } from "../components/ui";

type Tab = "quizzes" | "coding";

/** Streamlit colours the score by band; the bands are part of the feedback. */
function scoreTone(percentage: number): { tone: string; label: string } {
  if (percentage >= 80) return { tone: "border-ok/40 bg-ok/10 text-ink", label: "Score" };
  if (percentage >= 50) return { tone: "border-warn/40 bg-warn/10 text-ink", label: "Score" };
  return { tone: "border-danger/40 bg-danger/10 text-ink", label: "Score" };
}

export function ChallengesPage() {
  const [tab, setTab] = useState<Tab>("quizzes");

  return (
    <div className="flex flex-col gap-5 p-6">
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="text-xl font-semibold tracking-tight">Challenges</h2>
        <div className="ml-auto flex gap-1 rounded-lg border border-line bg-raised p-1">
          {(["quizzes", "coding"] as Tab[]).map((value) => (
            <button
              key={value}
              onClick={() => setTab(value)}
              className={cn(
                "rounded-md px-3 py-1 text-[13px] transition-colors",
                tab === value ? "bg-accent text-white" : "text-ink-2 hover:bg-hover",
              )}
            >
              {value === "quizzes" ? "Quizzes" : "Coding challenges"}
            </button>
          ))}
        </div>
      </div>
      {tab === "quizzes" ? <QuizTab /> : <CodingTab />}
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Quizzes                                                                    */
/* -------------------------------------------------------------------------- */

export function QuizTab() {
  const [slug, setSlug] = useState<string | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [result, setResult] = useState<QuizResult | null>(null);

  const quizzes = useQuery({ queryKey: ["quizzes"], queryFn: listQuizzes, staleTime: 5 * 60_000 });
  const all = quizzes.data ?? [];
  const quiz: Quiz | undefined = all.find((q) => q.slug === slug) ?? all[0];

  // Switching quizzes must clear both the draft answers and any score from the
  // previous one: a score left on screen next to someone else's questions is
  // worse than a blank form.
  function pick(next: string) {
    setSlug(next);
    setAnswers({});
    setResult(null);
  }

  const submit = useMutation({
    mutationFn: () => submitQuiz(quiz!.slug, answers),
    onSuccess: setResult,
  });

  if (quizzes.isLoading) {
    return (
      <p className="flex items-center gap-2 text-sm text-ink-3">
        <Spinner /> loading quizzes…
      </p>
    );
  }
  if (quizzes.isError) return <ErrorNote>{String(quizzes.error)}</ErrorNote>;
  if (all.length === 0) {
    return (
      <Card>
        <p className="text-[13px] text-ink-3">No quizzes available.</p>
      </Card>
    );
  }

  return (
    <Card>
      <label className="mb-3 block text-[13px] text-ink-2">
        Quiz
        <select
          value={quiz?.slug ?? ""}
          onChange={(e) => pick(e.target.value)}
          className="mt-1 h-9 w-full rounded-lg border border-line bg-raised px-2 text-sm text-ink"
        >
          {all.map((q) => (
            <option key={q.slug} value={q.slug}>
              {q.title}
            </option>
          ))}
        </select>
      </label>
      {quiz && quiz.tags.length > 0 && (
        <p className="mb-4 text-[13px] text-ink-3">
          Concepts:{" "}
          {quiz.tags.map((tag, i) => (
            <span key={tag}>
              {i > 0 && ", "}
              <code className="font-mono">{tag}</code>
            </span>
          ))}
        </p>
      )}

      {quiz?.questions.map((question, index) => (
        <div key={question.id} className="mb-5">
          <p className="mb-2 text-sm font-semibold text-ink">
            {index + 1}. {question.prompt}
          </p>
          {question.qtype === "mcq" && question.options.length > 0 ? (
            <div className="flex flex-col gap-1">
              {question.options.map((option) => (
                <label
                  key={option}
                  className={cn(
                    "flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-1.5 text-[13px]",
                    answers[String(question.id)] === option
                      ? "border-accent bg-accent/10 text-ink"
                      : "border-line text-ink-2 hover:bg-hover",
                  )}
                >
                  <input
                    type="radio"
                    name={`q_${quiz.slug}_${question.id}`}
                    value={option}
                    checked={answers[String(question.id)] === option}
                    onChange={() =>
                      setAnswers((prev) => ({ ...prev, [String(question.id)]: option }))
                    }
                    className="accent-accent"
                  />
                  {option}
                </label>
              ))}
            </div>
          ) : (
            <input
              value={answers[String(question.id)] ?? ""}
              onChange={(e) =>
                setAnswers((prev) => ({ ...prev, [String(question.id)]: e.target.value }))
              }
              className="h-9 w-full rounded-lg border border-line bg-raised px-3 text-sm text-ink"
            />
          )}
        </div>
      ))}

      <Button
        variant="primary"
        disabled={submit.isPending}
        onClick={() => submit.mutate()}
      >
        {submit.isPending ? <Spinner /> : null}
        Submit answers
      </Button>
      {submit.isError && <ErrorNote className="mt-3">{String(submit.error)}</ErrorNote>}

      {result && (
        <div className="mt-5 flex flex-col gap-3">
          <p
            className={cn(
              "rounded-lg border px-3 py-2 text-sm font-medium",
              scoreTone(result.percentage).tone,
            )}
          >
            Score: {result.score}/{result.max_score} ({result.percentage}%)
          </p>
          {result.feedback.map((item) => (
            <details
              key={item.question_id}
              className="rounded-lg border border-line-soft [&_summary]:cursor-pointer"
            >
              <summary className="px-3 py-2 text-[13px] font-medium text-ink">
                {item.correct ? "✅" : "❌"} {item.prompt}
              </summary>
              <div className="flex flex-col gap-1 border-t border-line-soft p-3 text-[13px] text-ink-2">
                <p>
                  Your answer:{" "}
                  <code className="font-mono">{item.your_answer || "(blank)"}</code>
                </p>
                {!item.correct && (
                  <p>
                    Correct answer:{" "}
                    <code className="font-mono">{item.correct_answer}</code>
                  </p>
                )}
                {item.explanation && (
                  <p className="rounded-md border border-line bg-raised px-2 py-1.5">
                    {item.explanation}
                  </p>
                )}
              </div>
            </details>
          ))}
        </div>
      )}
    </Card>
  );
}

/* -------------------------------------------------------------------------- */
/* Coding challenges                                                          */
/* -------------------------------------------------------------------------- */

export function CodingTab() {
  const [slug, setSlug] = useState<string | null>(null);
  const [attemptId, setAttemptId] = useState<number | null>(null);
  const ir = useCircuit((state) => state.ir);
  const { theme } = useTheme();

  const challenges = useQuery({
    queryKey: ["challenges"],
    queryFn: listChallenges,
    staleTime: 5 * 60_000,
  });
  const all = challenges.data ?? [];
  const challenge: Challenge | undefined = all.find((c) => c.slug === slug) ?? all[0];

  const submit = useMutation({
    mutationFn: () => submitChallenge(challenge!.slug, ir),
    onSuccess: (attempt) => setAttemptId(attempt.attempt_id),
  });

  // Grading runs in Celery, so the attempt is polled the way Streamlit polled
  // it: every half second until it settles.
  const outcome = useQuery({
    queryKey: ["attempt", attemptId],
    queryFn: () => getAttempt(attemptId as number),
    enabled: attemptId !== null,
    refetchInterval: (query) =>
      query.state.data?.status === "graded" || query.state.data?.status === "failed"
        ? false
        : 500,
    staleTime: 0,
  });
  // A job that never ran (no worker, or an invalid circuit) settles as failed
  // or as graded-with-a-failure-message. Neither is a pass, and neither should
  // sit there saying "Grading…" forever.
  const settled = outcome.data?.status === "graded" || outcome.data?.status === "failed";
  const graded = settled ? outcome.data : null;
  const counts = (graded?.details as { counts?: Record<string, number> } | undefined)?.counts;

  if (challenges.isLoading) {
    return (
      <p className="flex items-center gap-2 text-sm text-ink-3">
        <Spinner /> loading challenges…
      </p>
    );
  }
  if (challenges.isError) return <ErrorNote>{String(challenges.error)}</ErrorNote>;
  if (all.length === 0) {
    return (
      <Card>
        <p className="text-[13px] text-ink-3">No coding challenges available.</p>
      </Card>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <label className="mb-3 block text-[13px] text-ink-2">
          Challenge
          <select
            value={challenge?.slug ?? ""}
            onChange={(e) => {
              setSlug(e.target.value);
              setAttemptId(null);
            }}
            className="mt-1 h-9 w-full rounded-lg border border-line bg-raised px-2 text-sm text-ink"
          >
            {all.map((c) => (
              <option key={c.slug} value={c.slug}>
                {c.title}
              </option>
            ))}
          </select>
        </label>

        {challenge && (
          <>
            <h3 className="mb-2 text-base font-semibold text-ink">{challenge.title}</h3>
            <Markdown>{challenge.prompt}</Markdown>

            <div className="mt-3 flex flex-wrap items-center gap-3 text-[13px] text-ink-3">
              <span>
                Allowed gates:{" "}
                {challenge.allowed_gates.map((gate, i) => (
                  <span key={gate}>
                    {i > 0 && ", "}
                    <code className="font-mono">{gate}</code>
                  </span>
                ))}
              </span>
              {Object.entries(challenge.constraints ?? {}).length > 0 && (
                <span>
                  Constraints:{" "}
                  {Object.entries(challenge.constraints).map(([key, value], i) => (
                    <span key={key}>
                      {i > 0 && ", "}
                      <code className="font-mono">
                        {key}={String(value)}
                      </code>
                    </span>
                  ))}
                </span>
              )}
              {challenge.is_dynamic && <Badge tone="accent">Requires runtime control flow</Badge>}
            </div>
          </>
        )}
      </Card>

      <Card>
        <h3 className="mb-2 text-sm font-semibold">Your circuit</h3>
        <p className="mb-3 text-[13px] text-ink-2">
          Build your solution in the <strong className="text-ink">Composer</strong> page, then
          submit it here. Your current circuit is shown below.
        </p>
        <div
          className={cn(
            "overflow-auto rounded-lg border border-line-soft bg-raised p-2",
            theme === "dark" && "composer-host dark",
          )}
        >
          <CircuitDiagram ir={ir} />
        </div>
        <p className="mt-2 text-[13px] text-ink-3">
          Current circuit: {ir.n_qubits} qubits, depth{" "}
          {ir.ops.length > 0 ? Math.max(...ir.ops.map((op) => op.layer)) + 1 : 0},{" "}
          {circuitIsDynamic(ir) ? "dynamic" : "static"}
        </p>
        <Button
          variant="primary"
          className="mt-3"
          disabled={submit.isPending}
          onClick={() => submit.mutate()}
        >
          {submit.isPending ? <Spinner /> : null}
          Submit this circuit
        </Button>
        {submit.isError && <ErrorNote className="mt-3">{String(submit.error)}</ErrorNote>}
      </Card>

      {attemptId !== null && (
        <Card>
          {!graded ? (
            outcome.data?.status === "failed" ? (
              <ErrorNote>{outcome.data.feedback || "The simulation failed."}</ErrorNote>
            ) : (
              <p className="flex items-center gap-2 text-[13px] text-ink-3">
                <Spinner /> Grading… ({outcome.data?.status ?? "queued"})
              </p>
            )
          ) : (
            <div className="flex flex-col gap-3">
              <p
                className={cn(
                  "rounded-lg border px-3 py-2 text-[13px]",
                  graded.passed
                    ? "border-ok/40 bg-ok/10 text-ink"
                    : "border-danger/40 bg-danger/10 text-ink",
                )}
              >
                {graded.feedback}
              </p>
              <div>
                <div className="mb-1 flex justify-between text-[12px] text-ink-3">
                  <span>Score {graded.score.toFixed(2)}</span>
                  <span>{Math.round(Math.min(1, graded.score) * 100)}%</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-hover">
                  <div
                    className="h-full bg-accent"
                    style={{ width: `${Math.min(100, Math.max(0, graded.score * 100))}%` }}
                  />
                </div>
              </div>
              {counts && <CountsBar counts={counts} />}
              <details className="rounded-lg border border-line-soft [&_summary]:cursor-pointer">
                <summary className="px-3 py-2 text-[13px] font-medium text-ink-2">
                  Grading details
                </summary>
                <pre className="max-h-64 overflow-auto border-t border-line-soft bg-hover/60 p-3 font-mono text-[11px] text-ink-2">
                  {JSON.stringify(graded.details, null, 2)}
                </pre>
              </details>
            </div>
          )}
          {outcome.isError && <ErrorNote>{String(outcome.error)}</ErrorNote>}
        </Card>
      )}
    </div>
  );
}
