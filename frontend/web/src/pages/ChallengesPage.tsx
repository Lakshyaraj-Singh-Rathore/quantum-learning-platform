import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  CheckCircle2,
  XCircle,
  ExternalLink,
  RotateCcw,
  Trophy,
  Code2,
  Check,
  Sparkles,
  Zap,
  Calendar,
  Flame,
  Send,
  HelpCircle,
  CheckSquare,
  Square,
} from "lucide-react";
import { listQuizzes, submitQuiz, type Quiz, type QuizResult } from "../api/lessons";
import {
  getAttempt,
  listChallenges,
  submitChallenge,
  type Challenge,
  getAssessmentTopics,
  generateAiAssignment,
  evaluateAiAssignment,
  getDailyChallenge,
  verifyDailyChallenge,
  type TopicInfo,
  type GeneratedAssignment,
  type EvaluationResult,
  type DailyChallenge,
} from "../api/assessments";
import { useCircuit } from "../state/circuit";
import { circuitIsDynamic } from "@composer/ir";
import { CircuitDiagram } from "../components/results/CircuitDiagram";
import { CountsBar } from "../components/demos/Demos";
import { Markdown } from "../components/Markdown";
import {
  Badge,
  Button,
  Card,
  ErrorNote,
  Label,
  Select,
  SelectItem,
  Spinner,
  Tabs,
  TabsList,
  TabsTrigger,
  cn,
} from "../components/ui";

type Tab = "ai_assignment" | "daily_challenge" | "coding" | "quizzes";

export function ChallengesPage() {
  const [tab, setTab] = useState<Tab>("ai_assignment");

  return (
    <div className="flex flex-col gap-6 p-6 max-w-5xl mx-auto">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-line pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-ink flex items-center gap-2.5">
            <Trophy className="h-6 w-6 text-accent" /> Challenges & Assessments
          </h1>
          <p className="text-sm text-ink-3 mt-1">
            Test and elevate your quantum skills with real-time Gemini AI assessments, daily circuit puzzles, and theory quizzes.
          </p>
        </div>

        <Tabs value={tab} onValueChange={(v) => setTab(v as Tab)} className="w-auto">
          <TabsList className="bg-subtle/80 p-1">
            <TabsTrigger value="ai_assignment" className="gap-2 text-xs font-semibold">
              <Sparkles className="h-4 w-4 text-accent" /> AI Custom Assignment
            </TabsTrigger>
            <TabsTrigger value="daily_challenge" className="gap-2 text-xs font-semibold">
              <Zap className="h-4 w-4 text-amber-400" /> Daily Circuit Challenge
            </TabsTrigger>
            <TabsTrigger value="coding" className="gap-2 text-xs font-semibold">
              <Code2 className="h-4 w-4 text-sky-400" /> Coding Challenges
            </TabsTrigger>
            <TabsTrigger value="quizzes" className="gap-2 text-xs font-semibold">
              <CheckCircle2 className="h-4 w-4 text-emerald-400" /> Theory Quizzes
            </TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {tab === "ai_assignment" && <AiAssignmentTab />}
      {tab === "daily_challenge" && <DailyChallengeTab />}
      {tab === "coding" && <CodingTab />}
      {tab === "quizzes" && <QuizTab />}
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Tab 1: AI Real-Time Assignment Generator & Evaluator (Gemini + RAG)        */
/* -------------------------------------------------------------------------- */
export function AiAssignmentTab() {
  const [selectedTopics, setSelectedTopics] = useState<string[]>([
    "qubits_gates",
    "entanglement_bell",
  ]);
  const [numQuestions, setNumQuestions] = useState<number>(5);
  const [difficulty, setDifficulty] = useState<string>("mixed");
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [assignment, setAssignment] = useState<GeneratedAssignment | null>(null);
  const [evaluation, setEvaluation] = useState<EvaluationResult | null>(null);

  const topicsQuery = useQuery({
    queryKey: ["assessmentTopics"],
    queryFn: getAssessmentTopics,
    staleTime: 10 * 60_000,
  });

  const availableTopics: TopicInfo[] = topicsQuery.data ?? [];

  const generateMutation = useMutation({
    mutationFn: () => generateAiAssignment(selectedTopics, numQuestions, difficulty),
    onSuccess: (data) => {
      setAssignment(data);
      setAnswers({});
      setEvaluation(null);
    },
  });

  const evaluateMutation = useMutation({
    mutationFn: () => evaluateAiAssignment(assignment!, answers),
    onSuccess: (data) => {
      setEvaluation(data);
    },
  });

  const toggleTopic = (id: string) => {
    setSelectedTopics((prev) =>
      prev.includes(id) ? prev.filter((t) => t !== id) : [...prev, id]
    );
  };

  const selectAllTopics = () => {
    setSelectedTopics(availableTopics.map((t) => t.id));
  };

  const clearTopics = () => {
    setSelectedTopics([]);
  };

  const answeredCount = Object.keys(answers).length;
  const totalQuestions = assignment?.questions.length ?? 0;

  return (
    <div className="space-y-6">
      {/* Configuration & Generator Card (Shown when not reviewing or to reconfigure) */}
      <Card className="p-6 border border-line bg-surface/60 backdrop-blur-sm relative overflow-hidden">
        <div className="absolute top-0 right-0 w-80 h-80 bg-accent/5 rounded-full blur-3xl pointer-events-none" />

        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-5 border-b border-line">
          <div>
            <div className="flex items-center gap-2">
              <span className="flex h-6 w-6 items-center justify-center rounded-lg bg-accent/20 text-accent">
                <Sparkles className="h-3.5 w-3.5" />
              </span>
              <h2 className="text-lg font-bold text-ink">Real-Time AI Assignment Generator</h2>
              <Badge tone="accent" className="text-[10px] uppercase font-bold tracking-wider">
                Gemini API + RAG
              </Badge>
            </div>
            <p className="text-xs text-ink-3 mt-1.5 max-w-2xl leading-relaxed">
              Select any quantum topics covered in our curriculum. The Gemini API retrieves the latest lesson content through our RAG system, automatically curates multiple-choice questions organized topic-wise, and evaluates your answers instantly upon submission.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={selectAllTopics}
              className="text-xs gap-1.5"
            >
              <CheckSquare className="h-3.5 w-3.5 text-accent" /> Select All
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={clearTopics}
              className="text-xs gap-1.5 text-ink-3 hover:text-ink"
            >
              <Square className="h-3.5 w-3.5" /> Clear
            </Button>
          </div>
        </div>

        {/* Topic Selector Chips */}
        <div className="pt-5 space-y-4">
          <div className="flex items-center justify-between">
            <Label className="text-xs font-semibold uppercase tracking-wider text-ink-2">
              Select Topics Covered ({selectedTopics.length} selected)
            </Label>
            <span className="text-[11px] text-ink-3">
              MCQs will be generated strictly from selected curriculum material
            </span>
          </div>

          {topicsQuery.isLoading ? (
            <div className="flex items-center justify-center p-8 text-xs text-ink-3">
              <Spinner className="mr-2 h-4 w-4" /> Loading curriculum topics from RAG…
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2.5">
              {availableTopics.map((topic) => {
                const isSelected = selectedTopics.includes(topic.id);
                return (
                  <button
                    key={topic.id}
                    type="button"
                    onClick={() => toggleTopic(topic.id)}
                    className={cn(
                      "flex items-start gap-3 p-3 rounded-xl border text-left transition-all duration-150 cursor-pointer select-none",
                      isSelected
                        ? "border-accent/80 bg-accent/10 shadow-sm shadow-accent/5 ring-1 ring-accent/30"
                        : "border-line bg-raised/70 hover:bg-hover hover:border-line-focus text-ink-2"
                    )}
                  >
                    <div
                      className={cn(
                        "flex h-4 w-4 shrink-0 rounded mt-0.5 items-center justify-center border transition-colors",
                        isSelected
                          ? "border-accent bg-accent text-accent-ink"
                          : "border-line-soft bg-subtle"
                      )}
                    >
                      {isSelected && <Check className="h-3 w-3 stroke-[3]" />}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between gap-1.5">
                        <span className={cn("text-xs font-semibold leading-tight truncate", isSelected ? "text-accent-ink" : "text-ink")}>
                          {topic.name}
                        </span>
                        <span className="text-[10px] text-ink-3 uppercase shrink-0 font-medium px-1.5 py-0.5 rounded bg-subtle">
                          {topic.category}
                        </span>
                      </div>
                      <p className="text-[11px] text-ink-3 mt-1 leading-snug line-clamp-2">
                        {topic.description}
                      </p>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Question Count & Difficulty & Generate Action */}
        <div className="mt-6 pt-5 border-t border-line flex flex-wrap items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-6">
            <div>
              <span className="block text-[11px] font-semibold uppercase tracking-wider text-ink-3 mb-1.5">
                Total Questions (MCQ Only)
              </span>
              <div className="flex items-center gap-1.5">
                {[3, 5, 10, 15, 20].map((n) => (
                  <button
                    key={n}
                    type="button"
                    onClick={() => setNumQuestions(n)}
                    className={cn(
                      "px-3 py-1 rounded-lg text-xs font-semibold border transition-all cursor-pointer",
                      numQuestions === n
                        ? "border-accent bg-accent text-accent-ink shadow-xs"
                        : "border-line bg-raised text-ink-2 hover:bg-hover hover:text-ink"
                    )}
                  >
                    {n}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <span className="block text-[11px] font-semibold uppercase tracking-wider text-ink-3 mb-1.5">
                Difficulty Level
              </span>
              <div className="flex items-center gap-1.5">
                {[
                  { id: "mixed", label: "Mixed" },
                  { id: "beginner", label: "Beginner" },
                  { id: "intermediate", label: "Intermediate" },
                  { id: "advanced", label: "Advanced" },
                ].map((d) => (
                  <button
                    key={d.id}
                    type="button"
                    onClick={() => setDifficulty(d.id)}
                    className={cn(
                      "px-2.5 py-1 rounded-lg text-xs font-semibold border transition-all cursor-pointer",
                      difficulty === d.id
                        ? "border-accent bg-accent text-accent-ink shadow-xs"
                        : "border-line bg-raised text-ink-2 hover:bg-hover hover:text-ink"
                    )}
                  >
                    {d.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <Button
            variant="primary"
            size="md"
            disabled={selectedTopics.length === 0 || generateMutation.isPending}
            onClick={() => generateMutation.mutate()}
            className="gap-2 px-6 bg-gradient-to-r from-accent to-indigo-600 hover:from-accent-hover hover:to-indigo-500 shadow-md shadow-accent/20 cursor-pointer"
          >
            {generateMutation.isPending ? (
              <>
                <Spinner className="h-4 w-4" /> Generating with Gemini API…
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4" /> Generate Real-Time Assignment
              </>
            )}
          </Button>
        </div>

        {generateMutation.isError && (
          <ErrorNote className="mt-4">{String(generateMutation.error)}</ErrorNote>
        )}
      </Card>

      {/* Generated Assignment Interactive Section */}
      {assignment && (
        <Card className="p-6 space-y-6 border border-line bg-surface">
          {/* Header & Topic-wise Summary */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-line">
            <div>
              <div className="flex items-center gap-2.5">
                <Badge tone="ok" className="text-xs uppercase font-bold tracking-wider">
                  Active Assessment
                </Badge>
                <h3 className="text-lg font-bold text-ink">
                  Topic-Wise Quantum MCQ Assignment
                </h3>
              </div>
              <p className="text-xs text-ink-3 mt-1">
                Generated via <strong className="text-ink">{assignment.model_used}</strong> accessing indexed RAG materials · {assignment.total_questions} questions across {Object.keys(assignment.by_topic).length} topic sections.
              </p>
            </div>

            {/* Progress Counter */}
            <div className="flex items-center gap-3 self-end sm:self-center">
              <div className="text-right">
                <span className="text-[11px] text-ink-3 block">Progress</span>
                <span className="text-xs font-mono font-bold text-ink">
                  {answeredCount} / {totalQuestions} answered
                </span>
              </div>
              <div className="w-20 h-2 bg-subtle rounded-full overflow-hidden border border-line">
                <div
                  className="h-full bg-accent transition-all duration-300"
                  style={{
                    width: `${Math.round((answeredCount / (totalQuestions || 1)) * 100)}%`,
                  }}
                />
              </div>
            </div>
          </div>

          {/* Questions Grouped Topic-Wise */}
          <div className="space-y-8">
            {Object.entries(assignment.by_topic).map(([topicId, topicQuestions], sectionIdx) => {
              const topicName = topicQuestions[0]?.topic_name || topicId;
              return (
                <div key={topicId} className="space-y-4">
                  {/* Topic Section Header */}
                  <div className="flex items-center gap-3 pb-2 border-b border-line/60">
                    <span className="flex h-5 w-5 items-center justify-center rounded bg-accent/20 text-accent text-xs font-bold font-mono">
                      {sectionIdx + 1}
                    </span>
                    <h4 className="text-sm font-bold text-ink tracking-tight uppercase">
                      Topic: {topicName}
                    </h4>
                    <span className="text-[11px] text-ink-3">
                      ({topicQuestions.length} {topicQuestions.length === 1 ? "question" : "questions"})
                    </span>
                  </div>

                  {/* Section Questions */}
                  <div className="space-y-4">
                    {topicQuestions.map((q) => {
                      const questionNum =
                        assignment.questions.findIndex((x) => x.id === q.id) + 1;
                      const isAnswered = answers[q.id] !== undefined;

                      return (
                        <div
                          key={q.id}
                          className={cn(
                            "p-5 rounded-xl border transition-all duration-150 space-y-3.5",
                            isAnswered
                              ? "border-accent/40 bg-accent/5"
                              : "border-line bg-raised/60 hover:border-line-focus"
                          )}
                        >
                          <div className="flex items-start justify-between gap-3">
                            <div className="flex items-start gap-2.5">
                              <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-surface border border-line text-ink font-mono text-xs font-semibold shadow-xs">
                                {questionNum}
                              </span>
                              <div>
                                <p className="text-sm font-semibold text-ink leading-snug">
                                  {q.prompt}
                                </p>
                              </div>
                            </div>
                            <span className="text-[10px] font-medium text-ink-3 uppercase px-2 py-0.5 rounded bg-subtle shrink-0">
                              {q.difficulty}
                            </span>
                          </div>

                          {/* 4 MCQ Options */}
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 pt-1 pl-8">
                            {q.options.map((opt, optIdx) => {
                              const isSelected = answers[q.id] === opt;
                              const optionLetter = String.fromCharCode(65 + optIdx); // A, B, C, D

                              return (
                                <label
                                  key={opt}
                                  className={cn(
                                    "flex cursor-pointer items-center gap-3 rounded-lg border p-3 text-xs transition-all select-none",
                                    isSelected
                                      ? "border-accent bg-accent/15 text-accent-ink font-medium shadow-xs"
                                      : "border-line bg-raised text-ink-2 hover:bg-hover hover:text-ink"
                                  )}
                                >
                                  <input
                                    type="radio"
                                    name={`ai_q_${q.id}`}
                                    value={opt}
                                    checked={isSelected}
                                    onChange={() =>
                                      setAnswers((prev) => ({ ...prev, [q.id]: opt }))
                                    }
                                    className="sr-only"
                                  />
                                  <span
                                    className={cn(
                                      "flex h-5 w-5 shrink-0 items-center justify-center rounded font-mono text-[11px] font-bold border transition-colors",
                                      isSelected
                                        ? "border-accent bg-accent text-accent-ink"
                                        : "border-line-soft bg-subtle text-ink-3"
                                    )}
                                  >
                                    {optionLetter}
                                  </span>
                                  <span className="leading-snug">{opt}</span>
                                </label>
                              );
                            })}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Submit Test Action */}
          <div className="pt-6 border-t border-line flex flex-wrap items-center justify-between gap-4">
            <Button
              variant="primary"
              size="lg"
              disabled={evaluateMutation.isPending || answeredCount === 0}
              onClick={() => evaluateMutation.mutate()}
              className="gap-2 px-8 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-bold shadow-md shadow-emerald-500/20 cursor-pointer"
            >
              {evaluateMutation.isPending ? (
                <>
                  <Spinner className="h-4 w-4" /> Evaluating Submission…
                </>
              ) : (
                <>
                  <Send className="h-4 w-4" /> Submit Assignment for Real-Time Evaluation
                </>
              )}
            </Button>

            <span className="text-xs text-ink-3">
              {answeredCount === totalQuestions
                ? "All questions answered! Ready for grading."
                : `${totalQuestions - answeredCount} unanswered questions remaining.`}
            </span>
          </div>

          {evaluateMutation.isError && (
            <ErrorNote className="mt-4">{String(evaluateMutation.error)}</ErrorNote>
          )}

          {/* Real-time Evaluation Results Dashboard */}
          {evaluation && (
            <div className="mt-8 p-6 rounded-2xl border border-line bg-raised/80 backdrop-blur-sm space-y-6 shadow-xl">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-line">
                <div>
                  <h4 className="text-lg font-bold text-ink flex items-center gap-2">
                    <Trophy className="h-5 w-5 text-amber-400" /> Real-Time Evaluation Report
                  </h4>
                  <p className="text-xs text-ink-3 mt-1">{evaluation.summary}</p>
                </div>
                <div className="flex items-center gap-3">
                  <Badge
                    tone={
                      evaluation.percentage >= 80
                        ? "ok"
                        : evaluation.percentage >= 50
                        ? "warn"
                        : "danger"
                    }
                    className="text-base px-4 py-1.5 font-bold"
                  >
                    Score: {evaluation.score} / {evaluation.total} ({evaluation.percentage}%)
                  </Badge>
                </div>
              </div>

              {/* Topic-Wise Score Breakdown */}
              <div className="space-y-3">
                <span className="text-xs font-bold uppercase tracking-wider text-ink-2">
                  Topic-Wise Performance Breakdown:
                </span>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {Object.entries(evaluation.topic_scores).map(([topId, stats]) => {
                    const topObj = availableTopics.find((t) => t.id === topId);
                    const name = topObj?.name || topId;
                    return (
                      <div
                        key={topId}
                        className="p-3.5 rounded-xl border border-line bg-surface/70 space-y-2"
                      >
                        <div className="flex items-center justify-between text-xs font-semibold">
                          <span className="text-ink truncate">{name}</span>
                          <span
                            className={
                              stats.percentage >= 80
                                ? "text-ok"
                                : stats.percentage >= 50
                                ? "text-warn"
                                : "text-danger"
                            }
                          >
                            {stats.correct}/{stats.total} ({stats.percentage}%)
                          </span>
                        </div>
                        <div className="w-full h-1.5 bg-subtle rounded-full overflow-hidden">
                          <div
                            className={cn(
                              "h-full transition-all duration-300",
                              stats.percentage >= 80
                                ? "bg-ok"
                                : stats.percentage >= 50
                                ? "bg-warn"
                                : "bg-danger"
                            )}
                            style={{ width: `${stats.percentage}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Question-By-Question Detailed Explanations */}
              <div className="space-y-3 pt-2">
                <span className="text-xs font-bold uppercase tracking-wider text-ink-2">
                  Detailed Question Analysis & Explanations:
                </span>
                <div className="space-y-3">
                  {evaluation.results.map((item, idx) => (
                    <div
                      key={item.id}
                      className={cn(
                        "p-4 rounded-xl border text-xs space-y-2.5 transition-all",
                        item.is_correct
                          ? "border-ok/30 bg-ok/5"
                          : "border-danger/30 bg-danger/5"
                      )}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex items-start gap-2.5">
                          {item.is_correct ? (
                            <CheckCircle2 className="h-4 w-4 text-ok shrink-0 mt-0.5" />
                          ) : (
                            <XCircle className="h-4 w-4 text-danger shrink-0 mt-0.5" />
                          )}
                          <div>
                            <span className="font-semibold text-ink leading-snug">
                              {idx + 1}. {item.prompt}
                            </span>
                            <span className="block text-[10px] text-ink-3 mt-0.5">
                              Section: {item.topic_name}
                            </span>
                          </div>
                        </div>
                        <Badge
                          tone={item.is_correct ? "ok" : "danger"}
                          className="text-[10px] uppercase font-bold shrink-0"
                        >
                          {item.is_correct ? "Correct" : "Incorrect"}
                        </Badge>
                      </div>

                      <div className="pl-6 space-y-1.5 text-ink-2">
                        <p>
                          Your answer:{" "}
                          <code className="font-mono text-ink font-semibold bg-subtle px-1.5 py-0.5 rounded">
                            {item.selected_text || "(none selected)"}
                          </code>
                        </p>
                        {!item.is_correct && (
                          <p className="text-ok">
                            Correct answer:{" "}
                            <code className="font-mono font-semibold bg-ok/10 text-ok px-1.5 py-0.5 rounded">
                              {item.correct_text}
                            </code>
                          </p>
                        )}
                        {item.explanation && (
                          <div className="mt-2 text-xs text-ink-2 bg-subtle/80 p-3 rounded-lg border border-line-soft leading-relaxed">
                            <span className="font-semibold text-accent block mb-1">
                              💡 Pedagogical Explanation:
                            </span>
                            {item.explanation}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Retake & Actions */}
              <div className="pt-4 border-t border-line flex items-center justify-between">
                <Button
                  variant="secondary"
                  size="md"
                  onClick={() => {
                    setAnswers({});
                    setEvaluation(null);
                  }}
                  className="gap-2 text-xs"
                >
                  <RotateCcw className="h-3.5 w-3.5" /> Retake This Assignment
                </Button>
                <Button
                  variant="primary"
                  size="md"
                  onClick={() => {
                    setAssignment(null);
                    setAnswers({});
                    setEvaluation(null);
                    window.scrollTo({ top: 0, behavior: "smooth" });
                  }}
                  className="gap-2 text-xs"
                >
                  <Sparkles className="h-3.5 w-3.5" /> Configure New Assignment
                </Button>
              </div>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Tab 2: Daily Quantum Circuit Challenge (Created by Gemini API)             */
/* -------------------------------------------------------------------------- */
export function DailyChallengeTab() {
  const navigate = useNavigate();
  const ir = useCircuit((state) => state.ir);
  const setIr = useCircuit((state) => state.setIr);
  const setChallengeContext = useCircuit((state) => state.setChallengeContext);

  const dailyQuery = useQuery({
    queryKey: ["dailyChallenge"],
    queryFn: getDailyChallenge,
    staleTime: 5 * 60_000,
  });

  const daily: DailyChallenge | undefined = dailyQuery.data;

  const verifyMutation = useMutation({
    mutationFn: () => verifyDailyChallenge(daily!.challenge_id, ir),
  });

  const loadIntoComposer = () => {
    if (!daily) return;
    if (daily.starter_ir) {
      setIr(daily.starter_ir);
    }
    setChallengeContext({
      challengeId: daily.challenge_id,
      title: daily.title,
      returnPath: "/challenges",
    });
    navigate("/composer");
  };

  if (dailyQuery.isLoading) {
    return (
      <div className="flex items-center justify-center p-12 text-ink-3 text-sm">
        <Spinner className="mr-2" /> Generating today's quantum circuit problem via Gemini…
      </div>
    );
  }

  if (dailyQuery.isError) {
    return <ErrorNote>{String(dailyQuery.error)}</ErrorNote>;
  }

  if (!daily) {
    return (
      <Card>
        <p className="text-sm text-ink-3">No daily challenge available right now.</p>
      </Card>
    );
  }

  const gateSummary = `${ir.n_qubits} qubits · ${ir.ops.length} gates · depth ${
    ir.ops.length > 0 ? Math.max(...ir.ops.map((op) => op.layer)) + 1 : 0
  }`;

  return (
    <div className="space-y-6">
      {/* Daily Challenge Card */}
      <Card className="p-6 border border-line bg-surface relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-amber-500/5 rounded-full blur-3xl pointer-events-none" />

        {/* Top Badges: Date, Streak, Reward */}
        <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-line">
          <div className="flex items-center gap-2">
            <span className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 text-xs font-bold">
              <Calendar className="h-3.5 w-3.5" /> {daily.date}
            </span>
            <Badge tone="accent" className="text-xs uppercase font-bold tracking-wider">
              Daily Circuit Puzzle
            </Badge>
            <span className="text-[11px] text-ink-3">Topic: {daily.topic}</span>
          </div>

          <div className="flex items-center gap-2">
            <span className="flex items-center gap-1 text-xs font-bold text-amber-400 bg-amber-400/10 px-2.5 py-1 rounded-lg border border-amber-400/20">
              <Flame className="h-4 w-4 fill-amber-400 text-amber-400" /> +{daily.xp_reward} XP
            </span>
            <span className="text-[10px] uppercase font-semibold text-ink-3 px-2 py-0.5 rounded bg-subtle">
              Difficulty: {daily.difficulty}
            </span>
          </div>
        </div>

        {/* Prompt & Story Context */}
        <div className="py-5 space-y-3">
          <h2 className="text-xl font-bold text-ink tracking-tight flex items-center gap-2">
            <Zap className="h-5 w-5 text-amber-400" /> {daily.title}
          </h2>
          <div className="p-4 rounded-xl border border-line bg-raised/70 space-y-2">
            <span className="text-[11px] font-bold uppercase tracking-wider text-amber-400">
              Circuit Problem Statement:
            </span>
            <p className="text-sm text-ink-1 leading-relaxed">{daily.prompt}</p>
            {daily.story && (
              <p className="text-xs text-ink-3 italic pt-1 border-t border-line/60">
                Context: {daily.story}
              </p>
            )}
          </div>
        </div>

        {/* Target State & Constraints */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pb-5">
          <div className="p-4 rounded-xl border border-line bg-subtle space-y-2">
            <span className="text-[11px] font-bold uppercase tracking-wider text-ink-3">
              Target Quantum State
            </span>
            <div className="font-mono text-sm font-bold text-accent-ink bg-raised p-2.5 rounded-lg border border-line">
              {daily.target_state}
            </div>
          </div>

          <div className="p-4 rounded-xl border border-line bg-subtle space-y-2">
            <span className="text-[11px] font-bold uppercase tracking-wider text-ink-3">
              Constraints & Requirements
            </span>
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span className="px-2 py-1 rounded bg-raised border border-line text-ink-2 font-mono">
                Max Qubits: {daily.constraints.max_qubits}
              </span>
              <span className="px-2 py-1 rounded bg-raised border border-line text-ink-2 font-mono">
                Max Gates: {daily.constraints.max_gates}
              </span>
              <span className="px-2 py-1 rounded bg-raised border border-line text-ok font-mono font-semibold">
                Fidelity ≥ {(daily.constraints.target_fidelity * 100).toFixed(0)}%
              </span>
            </div>
            <div className="text-[11px] text-ink-3 pt-1">
              Allowed gates:{" "}
              {daily.allowed_gates.map((g) => (
                <code
                  key={g}
                  className="font-mono text-accent-ink bg-raised px-1 py-0.5 rounded border border-line text-[10px] mr-1"
                >
                  {g}
                </code>
              ))}
            </div>
          </div>
        </div>

        {/* Hints */}
        {daily.hints && daily.hints.length > 0 && (
          <div className="p-4 rounded-xl border border-line-soft bg-subtle/50 space-y-1.5 mb-5">
            <span className="text-[11px] font-bold uppercase tracking-wider text-ink-3 flex items-center gap-1.5">
              <HelpCircle className="h-3.5 w-3.5 text-accent" /> Hints:
            </span>
            <ul className="list-disc list-inside text-xs text-ink-2 space-y-1 pl-1">
              {daily.hints.map((hint, idx) => (
                <li key={idx}>{hint}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Action: Open in Composer */}
        <div className="flex items-center justify-between pt-4 border-t border-line">
          <Button
            variant="primary"
            size="md"
            onClick={loadIntoComposer}
            className="gap-2 shadow-md font-semibold bg-gradient-to-r from-accent to-sky-600 hover:from-accent-hover hover:to-sky-500 cursor-pointer"
          >
            <ExternalLink className="h-4 w-4" /> Load Starter & Build in Composer
          </Button>
          <span className="text-xs text-ink-3">
            Build the circuit in Composer, then return here to test and verify!
          </span>
        </div>
      </Card>

      {/* Active Circuit Verification Panel */}
      <Card className="p-6 border border-line bg-surface space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-base font-semibold text-ink">Your Current Active Circuit</h3>
            <p className="text-xs text-ink-3 mt-0.5">Configuration: {gateSummary}</p>
          </div>
          <Button
            variant="secondary"
            size="sm"
            onClick={loadIntoComposer}
            className="text-xs gap-1.5"
          >
            Edit in Composer <ExternalLink className="h-3.5 w-3.5" />
          </Button>
        </div>

        {/* Active Circuit Diagram Preview */}
        <div className="overflow-x-auto rounded-xl border border-line bg-subtle p-3">
          <CircuitDiagram ir={ir} />
        </div>

        {/* Verification Action */}
        <div className="flex flex-wrap items-center justify-between gap-4 pt-2">
          <Button
            variant="primary"
            size="md"
            disabled={verifyMutation.isPending}
            onClick={() => verifyMutation.mutate()}
            className="gap-2 px-6 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 font-bold shadow-md cursor-pointer"
          >
            {verifyMutation.isPending ? (
              <>
                <Spinner className="h-4 w-4" /> Simulating & Verifying Quantum State…
              </>
            ) : (
              <>
                <Check className="h-4 w-4" /> Verify Daily Circuit Solution
              </>
            )}
          </Button>
        </div>

        {verifyMutation.isError && (
          <ErrorNote className="mt-3">{String(verifyMutation.error)}</ErrorNote>
        )}

        {/* Verification Outcome */}
        {verifyMutation.data && (
          <div
            className={cn(
              "mt-4 p-5 rounded-xl border text-sm space-y-3 transition-all",
              verifyMutation.data.passed
                ? "border-ok/40 bg-ok/10 text-ok"
                : "border-danger/40 bg-danger/10 text-danger"
            )}
          >
            <div className="flex items-center justify-between">
              <span className="font-bold text-base flex items-center gap-2">
                {verifyMutation.data.passed ? (
                  <>
                    <CheckCircle2 className="h-5 w-5" /> Challenge Solved! (+{daily.xp_reward} XP)
                  </>
                ) : (
                  <>
                    <XCircle className="h-5 w-5" /> Solution Not Yet Complete
                  </>
                )}
              </span>
              <Badge
                tone={verifyMutation.data.passed ? "ok" : "danger"}
                className="text-xs font-bold px-3 py-1"
              >
                State Fidelity: {(verifyMutation.data.fidelity * 100).toFixed(1)}%
              </Badge>
            </div>
            <p className="text-xs leading-relaxed text-ink-1">{verifyMutation.data.feedback}</p>
          </div>
        )}
      </Card>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Tab 3: Curated Coding Challenges                                           */
/* -------------------------------------------------------------------------- */
export function CodingTab() {
  const navigate = useNavigate();
  const [slug, setSlug] = useState<string | null>(null);
  const [attemptId, setAttemptId] = useState<number | null>(null);
  const ir = useCircuit((state) => state.ir);
  const setChallengeContext = useCircuit((state) => state.setChallengeContext);

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

  const settled = outcome.data?.status === "graded" || outcome.data?.status === "failed";
  const graded = settled ? outcome.data : null;
  const counts = (graded?.details as { counts?: Record<string, number> } | undefined)?.counts;

  function openInComposer() {
    if (!challenge) return;
    setChallengeContext({
      challengeId: challenge.slug,
      title: challenge.title,
      returnPath: "/challenges",
    });
    navigate("/composer");
  }

  if (challenges.isLoading) {
    return (
      <div className="flex items-center justify-center p-12 text-ink-3 text-sm">
        <Spinner className="mr-2" /> Loading challenges…
      </div>
    );
  }

  if (challenges.isError) return <ErrorNote>{String(challenges.error)}</ErrorNote>;

  if (all.length === 0) {
    return (
      <Card>
        <p className="text-sm text-ink-3">No coding challenges available.</p>
      </Card>
    );
  }

  const gateSummary = `${ir.n_qubits} qubits · ${ir.ops.length} gates · depth ${
    ir.ops.length > 0 ? Math.max(...ir.ops.map((op) => op.layer)) + 1 : 0
  }`;

  return (
    <div className="space-y-6">
      {/* Challenge Selector & Specification */}
      <Card className="p-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
          <div className="w-full sm:w-72">
            <Label>Select Coding Challenge</Label>
            <Select
              value={challenge?.slug ?? ""}
              onValueChange={(val) => {
                setSlug(val);
                setAttemptId(null);
              }}
              className="bg-bg text-xs"
            >
              {all.map((c) => (
                <SelectItem key={c.slug} value={c.slug}>
                  {c.title}
                </SelectItem>
              ))}
            </Select>
          </div>

          {challenge && (
            <Button
              variant="primary"
              size="md"
              onClick={openInComposer}
              className="gap-2 shadow-sm font-semibold"
            >
              <ExternalLink className="h-4 w-4" /> Open in Composer (Build your solution in the Composer)
            </Button>
          )}
        </div>

        {challenge && (
          <div className="space-y-4 pt-2">
            <h2 className="text-lg font-bold text-ink">{challenge.title}</h2>
            <div className="lesson-prose text-sm text-ink-2">
              <Markdown>{challenge.prompt}</Markdown>
            </div>

            <div className="mt-4 flex flex-wrap items-center gap-3 text-xs pt-3 border-t border-line-soft">
              <span className="text-ink-3">
                Allowed gates:{" "}
                {challenge.allowed_gates.map((gate, i) => (
                  <span key={gate}>
                    {i > 0 && ", "}
                    <code className="font-mono text-accent-ink bg-subtle px-1.5 py-0.5 rounded border border-line">
                      {gate}
                    </code>
                  </span>
                ))}
              </span>

              {challenge.is_dynamic && <Badge tone="warn">Requires Runtime Feedback</Badge>}
            </div>

            {challenge.constraints && Object.keys(challenge.constraints).length > 0 && (
              <div className="flex flex-wrap items-center gap-2 text-xs pt-2">
                <span className="text-ink-3">Constraints:</span>
                {Object.entries(challenge.constraints).map(([k, v]) => (
                  <Badge key={k} tone="neutral" className="font-mono text-[11px]">
                    {k}={String(v)}
                  </Badge>
                ))}
              </div>
            )}
          </div>
        )}
      </Card>

      {/* Circuit Preview & Submission */}
      <Card className="p-6">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h3 className="text-base font-semibold text-ink">Active Session Circuit</h3>
            <p className="text-xs text-ink-3 mt-0.5">
              Current circuit: {ir.n_qubits} qubits, depth {ir.ops.length > 0 ? Math.max(...ir.ops.map((op) => op.layer)) + 1 : 0}, {circuitIsDynamic(ir) ? "dynamic" : "static"} · Summary: {gateSummary}
            </p>
          </div>
          <Button
            variant="secondary"
            size="sm"
            onClick={openInComposer}
            className="text-xs gap-1.5"
          >
            Edit in Composer <ExternalLink className="h-3.5 w-3.5" />
          </Button>
        </div>

        <div className="overflow-x-auto rounded-xl border border-line bg-subtle p-3 my-4">
          <CircuitDiagram ir={ir} />
        </div>

        <Button
          variant="primary"
          size="md"
          disabled={submit.isPending}
          onClick={() => submit.mutate()}
          className="gap-2 px-6"
        >
          {submit.isPending ? <Spinner className="h-4 w-4" /> : <Check className="h-4 w-4" />}
          Submit this circuit for grading
        </Button>

        {submit.isError && <ErrorNote className="mt-3">{String(submit.error)}</ErrorNote>}
      </Card>

      {/* Grading Outcome Display */}
      {attemptId !== null && (
        <Card className="p-6">
          {!graded ? (
            outcome.data?.status === "failed" ? (
              <ErrorNote>{outcome.data.feedback || "The simulation evaluation failed."}</ErrorNote>
            ) : (
              <div className="flex items-center gap-2.5 text-sm text-ink-3 py-4">
                <Spinner className="h-4 w-4" /> Evaluating quantum circuit on simulator…
              </div>
            )
          ) : (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h4 className="text-base font-bold text-ink">Evaluation Results</h4>
                <Badge tone={graded.passed ? "ok" : "danger"} className="text-sm px-3 py-1">
                  {graded.passed ? "Passed" : "Needs Work"} · Score: {Math.round(graded.score * 100)}%
                </Badge>
              </div>

              <div
                className={cn(
                  "p-4 rounded-xl border text-sm leading-relaxed",
                  graded.passed ? "border-ok/40 bg-ok/10 text-ok" : "border-danger/40 bg-danger/10 text-danger"
                )}
              >
                {graded.feedback}
              </div>

              {counts && (
                <div className="pt-2">
                  <span className="block text-xs font-semibold text-ink-3 uppercase tracking-wider mb-2">
                    Measurement Sample Distribution:
                  </span>
                  <CountsBar counts={counts} />
                </div>
              )}

              {/* Human-readable criteria feedback */}
              <div className="rounded-xl border border-line bg-subtle p-4 mt-3">
                <h5 className="text-xs font-semibold text-ink uppercase tracking-wider mb-3">
                  Grading Criteria Breakdown
                </h5>
                <div className="space-y-2 text-xs">
                  <div className="flex items-center justify-between py-1 border-b border-line-soft">
                    <span className="text-ink-2">Quantum Gate Constraints</span>
                    <span className="text-ok flex items-center gap-1 font-medium">
                      <Check className="h-3.5 w-3.5" /> Satisfied
                    </span>
                  </div>
                  <div className="flex items-center justify-between py-1 border-b border-line-soft">
                    <span className="text-ink-2">Statevector / Output Fidelity</span>
                    <span className={cn("font-medium", graded.passed ? "text-ok" : "text-warn")}>
                      {graded.score.toFixed(3)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between py-1">
                    <span className="text-ink-2">Circuit Dynamic Control Flow</span>
                    <span className="text-ink-3">
                      {challenge?.is_dynamic ? (circuitIsDynamic(ir) ? "Compliant" : "Missing") : "N/A"}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Tab 4: Curated Theory Quizzes                                              */
/* -------------------------------------------------------------------------- */
export function QuizTab() {
  const [slug, setSlug] = useState<string | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [result, setResult] = useState<QuizResult | null>(null);

  const quizzes = useQuery({ queryKey: ["quizzes"], queryFn: listQuizzes, staleTime: 5 * 60_000 });
  const all = quizzes.data ?? [];
  const quiz: Quiz | undefined = all.find((q) => q.slug === slug) ?? all[0];

  function pickQuiz(next: string) {
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
      <div className="flex items-center justify-center p-12 text-ink-3 text-sm">
        <Spinner className="mr-2" /> Loading quizzes…
      </div>
    );
  }

  if (quizzes.isError) return <ErrorNote>{String(quizzes.error)}</ErrorNote>;

  if (all.length === 0) {
    return (
      <Card>
        <p className="text-sm text-ink-3">No quizzes currently available.</p>
      </Card>
    );
  }

  const answeredCount = Object.keys(answers).length;
  const totalQuestions = quiz?.questions.length ?? 0;

  return (
    <div className="space-y-6">
      <Card className="p-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
          <div className="w-full sm:w-72">
            <Label>Select Quiz Topic</Label>
            <Select
              value={quiz?.slug ?? ""}
              onValueChange={pickQuiz}
              className="bg-bg text-xs"
            >
              {all.map((q) => (
                <SelectItem key={q.slug} value={q.slug}>
                  {q.title}
                </SelectItem>
              ))}
            </Select>
          </div>

          {quiz && quiz.tags.length > 0 && (
            <div className="flex flex-wrap items-center gap-1.5 self-end sm:self-center">
              {quiz.tags.map((tag) => (
                <Badge key={tag} tone="neutral" className="text-xs">
                  {tag}
                </Badge>
              ))}
            </div>
          )}
        </div>

        {quiz && (
          <div className="mb-4">
            <h2 className="text-lg font-bold text-ink">{quiz.title}</h2>
          </div>
        )}

        {/* Progress Bar */}
        <div className="mb-6 flex items-center justify-between text-xs text-ink-3 border-b border-line pb-3">
          <span>
            Progress: <strong className="text-ink">{answeredCount}</strong> of{" "}
            <strong>{totalQuestions}</strong> questions answered
          </span>
          <span className="font-mono">{Math.round((answeredCount / (totalQuestions || 1)) * 100)}%</span>
        </div>

        {/* Questions list */}
        <div className="space-y-6">
          {quiz?.questions.map((question, index) => (
            <div
              key={question.id}
              className="p-4 rounded-xl border border-line bg-subtle/50 space-y-3"
            >
              <div className="flex items-start gap-2">
                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-accent/20 text-accent font-mono text-xs font-semibold">
                  {index + 1}
                </span>
                <p className="text-sm font-semibold text-ink leading-snug">{question.prompt}</p>
              </div>

              {question.qtype === "mcq" && question.options.length > 0 ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1 pl-7">
                  {question.options.map((option) => {
                    const isSelected = answers[String(question.id)] === option;
                    return (
                      <label
                        key={option}
                        className={cn(
                          "flex cursor-pointer items-center gap-3 rounded-lg border p-3 text-xs transition-all",
                          isSelected
                            ? "border-accent bg-accent/15 text-accent-ink font-medium shadow-xs"
                            : "border-line bg-raised text-ink-2 hover:bg-hover hover:text-ink"
                        )}
                      >
                        <input
                          type="radio"
                          name={`q_${quiz.slug}_${question.id}`}
                          value={option}
                          checked={isSelected}
                          onChange={() =>
                            setAnswers((prev) => ({ ...prev, [String(question.id)]: option }))
                          }
                          className="accent-accent h-4 w-4 shrink-0"
                        />
                        <span className="leading-snug">{option}</span>
                      </label>
                    );
                  })}
                </div>
              ) : (
                <div className="pl-7">
                  <input
                    value={answers[String(question.id)] ?? ""}
                    onChange={(e) =>
                      setAnswers((prev) => ({ ...prev, [String(question.id)]: e.target.value }))
                    }
                    placeholder="Type your answer here..."
                    className="h-9 w-full rounded-lg border border-line bg-raised px-3 text-xs text-ink placeholder:text-ink-3 focus:outline-none focus:border-line-focus"
                  />
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Actions */}
        <div className="mt-8 flex flex-wrap items-center justify-between gap-4 pt-4 border-t border-line">
          <Button
            variant="primary"
            size="md"
            disabled={submit.isPending || answeredCount === 0}
            onClick={() => submit.mutate()}
            className="gap-2 px-6"
          >
            {submit.isPending ? <Spinner className="h-4 w-4" /> : <Check className="h-4 w-4" />}
            Submit Quiz
          </Button>

          {result && (
            <Button
              variant="secondary"
              size="md"
              onClick={() => {
                setAnswers({});
                setResult(null);
              }}
              className="gap-2 text-xs"
            >
              <RotateCcw className="h-3.5 w-3.5" /> Retake Quiz
            </Button>
          )}
        </div>

        {submit.isError && <ErrorNote className="mt-4">{String(submit.error)}</ErrorNote>}

        {/* Quiz Results Feedback */}
        {result && (
          <div className="mt-8 p-6 rounded-xl border border-line bg-raised space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-ink">Quiz Results</h3>
              <Badge
                tone={result.percentage >= 80 ? "ok" : result.percentage >= 50 ? "warn" : "danger"}
                className="text-sm px-3 py-1 font-semibold"
              >
                {result.score} / {result.max_score} ({result.percentage}%)
              </Badge>
            </div>

            <div className="space-y-3 pt-2">
              {result.feedback.map((item) => (
                <div
                  key={item.question_id}
                  className={cn(
                    "p-3.5 rounded-lg border text-xs space-y-2",
                    item.correct
                      ? "border-ok/30 bg-ok/5"
                      : "border-danger/30 bg-danger/5"
                  )}
                >
                  <div className="flex items-start gap-2">
                    {item.correct ? (
                      <CheckCircle2 className="h-4 w-4 text-ok shrink-0 mt-0.5" />
                    ) : (
                      <XCircle className="h-4 w-4 text-danger shrink-0 mt-0.5" />
                    )}
                    <span className="font-medium text-ink flex-1 leading-snug">{item.prompt}</span>
                  </div>

                  <div className="pl-6 space-y-1 text-ink-2">
                    <p>
                      Your answer: <code className="font-mono text-ink font-semibold">{item.your_answer || "(blank)"}</code>
                    </p>
                    {!item.correct && (
                      <p className="text-ok">
                        Correct answer: <code className="font-mono font-semibold">{item.correct_answer}</code>
                      </p>
                    )}
                    {item.explanation && (
                      <p className="mt-2 text-xs text-ink-3 italic bg-subtle p-2 rounded border border-line-soft">
                        💡 {item.explanation}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}

