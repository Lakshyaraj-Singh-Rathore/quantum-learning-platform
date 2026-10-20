import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  LayoutDashboard,
  GraduationCap,
  TrendingUp,
  BookOpen,
  Puzzle,
  Clock,
  Sparkles,
  Trophy,
} from "lucide-react";
import {
  instructorOverview,
  listStudents,
  myProgress,
  studentDetail,
  type LearnerProgress,
  type MasteryRow,
} from "../api/dashboard";
import { listJobs } from "../api/jobs";
import { useSession } from "../state/session";
import {
  Badge,
  Card,
  DataTable,
  EmptyState,
  ErrorNote,
  Label,
  Select,
  SelectItem,
  Spinner,
  Tabs,
  TabsList,
  TabsTrigger,
  type ColumnDef,
} from "../components/ui";
import { NoSimulationsIllustration } from "../components/illustrations/NoSimulationsIllustration";

export function DashboardPage() {
  const user = useSession((state) => state.user);
  const isInstructor = user?.role === "instructor" || user?.role === "admin";
  const [tab, setTab] = useState<"mine" | "instructor">("mine");

  return (
    <div className="flex flex-col gap-6 p-6 max-w-6xl mx-auto">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-line pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-ink flex items-center gap-2.5">
            <LayoutDashboard className="h-6 w-6 text-accent" /> Learning Analytics & Dashboard
          </h1>
          <p className="text-sm text-ink-3 mt-1">
            Track concept mastery across quantum mechanics, algorithm comprehension, and simulation benchmarks.
          </p>
        </div>

        {isInstructor && (
          <Tabs value={tab} onValueChange={(val) => setTab(val as "mine" | "instructor")} className="w-auto">
            <TabsList>
              <TabsTrigger value="mine">My Progress</TabsTrigger>
              <TabsTrigger value="instructor" className="gap-1.5">
                <GraduationCap className="h-4 w-4" /> Instructor Cohort
              </TabsTrigger>
            </TabsList>
          </Tabs>
        )}
      </div>

      {tab === "mine" || !isInstructor ? <ProgressPanel /> : <InstructorPanel />}
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Metric Card                                                                */
/* -------------------------------------------------------------------------- */
function MetricCard({
  label,
  value,
  subtitle,
  icon: Icon,
}: {
  label: string;
  value: string | number;
  subtitle?: string;
  icon?: any;
}) {
  return (
    <div className="glass-card rounded-2xl p-5 border border-white/10 hover:border-accent/40 shadow-lg relative overflow-hidden group">
      <div className="flex items-center justify-between mb-2">
        <p className="text-[11px] font-bold uppercase tracking-wider text-ink-3 font-mono">{label}</p>
        {Icon && (
          <div className="p-2 rounded-xl bg-accent/10 text-accent group-hover:scale-110 group-hover:bg-accent/20 transition-all">
            <Icon className="h-4 w-4" />
          </div>
        )}
      </div>
      <p className="text-3xl font-extrabold text-white tracking-tight tabular-nums font-display">{value}</p>
      {subtitle && <p className="text-xs text-ink-3 mt-1.5 font-medium">{subtitle}</p>}
      <div className="absolute -bottom-6 -right-6 w-20 h-20 rounded-full bg-accent/5 blur-xl group-hover:bg-accent/10 transition-colors pointer-events-none" />
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Mastery Chart                                                              */
/* -------------------------------------------------------------------------- */
function MasteryChart({ rows, valueKey = "score" }: { rows: MasteryRow[]; valueKey?: string }) {
  const peak = Math.max(...rows.map((row) => Number(row[valueKey] ?? 0)), 1);

  return (
    <div className="space-y-2.5">
      {rows.map((row) => {
        const val = Number(row[valueKey] ?? 0);
        const percent = Math.min(100, Math.max(0, (val / peak) * 100));

        return (
          <div key={String(row.tag)} className="flex items-center gap-3 text-xs">
            <span className="w-28 truncate font-medium text-ink-2" title={String(row.tag)}>
              {String(row.tag)}
            </span>
            <div className="h-3 flex-1 overflow-hidden rounded-full bg-subtle border border-line-soft">
              <div
                className="h-full bg-gradient-to-r from-accent to-accent-2 transition-all duration-300"
                style={{ width: `${percent}%` }}
              />
            </div>
            <span className="w-12 text-right font-mono text-ink-3 font-medium tabular-nums">
              {val.toFixed(2)}
            </span>
          </div>
        );
      })}
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Quiz Score Progression SVG Line Chart                                      */
/* -------------------------------------------------------------------------- */
function QuizProgressionChart({ progress }: { progress: LearnerProgress }) {
  const history = (progress as any).quiz_history ?? [];

  if (history.length === 0) {
    return (
      <div className="p-4 text-center text-xs text-ink-3 bg-subtle/50 rounded-xl border border-line-soft">
        Take quizzes to view your score progression timeline.
      </div>
    );
  }

  const width = 500;
  const height = 140;
  const padding = 28;
  const scores = history.map((h: any) => h.percentage ?? (h.score / h.max_score) * 100);

  const points = scores.map((val: number, idx: number) => {
    const x = padding + (idx / Math.max(1, scores.length - 1)) * (width - padding * 2);
    const y = height - padding - (val / 100) * (height - padding * 2);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-xs text-ink-3">
        <span>Score Progression Over Time</span>
        <span className="font-mono text-ok">Avg: {progress.average_quiz_percentage}%</span>
      </div>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="w-full h-36 rounded-xl border border-line bg-subtle p-2"
        role="img"
        aria-label="Quiz scores progression"
      >
        {/* Grid lines */}
        <line x1={padding} y1={padding} x2={width - padding} y2={padding} stroke="var(--line-soft)" strokeDasharray="3 3" />
        <line x1={padding} y1={height / 2} x2={width - padding} y2={height / 2} stroke="var(--line-soft)" strokeDasharray="3 3" />
        <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="var(--line)" />

        {/* 100% and 50% labels */}
        <text x="8" y={padding + 4} fill="var(--ink-3)" fontSize="10" fontFamily="var(--font-mono)">100%</text>
        <text x="14" y={height / 2 + 4} fill="var(--ink-3)" fontSize="10" fontFamily="var(--font-mono)">50%</text>

        {/* Polyline */}
        <polyline
          points={points.join(" ")}
          fill="none"
          stroke="var(--accent)"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* Data points */}
        {scores.map((_val: number, idx: number) => {
          const [cx, cy] = points[idx].split(",").map(Number);
          return (
            <circle
              key={idx}
              cx={cx}
              cy={cy}
              r="4"
              fill="var(--bg-raised)"
              stroke="var(--accent)"
              strokeWidth="2"
            />
          );
        })}
      </svg>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Recommendations                                                            */
/* -------------------------------------------------------------------------- */
function Recommendations({ progress }: { progress: LearnerProgress }) {
  const items = progress.recommendations ?? [];
  if (items.length === 0) {
    return <p className="text-xs text-ink-3">No pending recommendations. You are fully up to date!</p>;
  }

  return (
    <div className="space-y-2.5">
      {items.map((item) => (
        <div
          key={`${item.kind}-${item.slug}`}
          className="flex items-start gap-3 p-3 rounded-lg border border-line bg-subtle hover:bg-hover transition-colors"
        >
          <div className="mt-0.5 text-accent">
            {item.kind === "lesson" ? (
              <BookOpen className="h-4 w-4" />
            ) : (
              <Puzzle className="h-4 w-4" />
            )}
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-xs font-semibold text-ink leading-snug">
              {item.title ?? item.slug}
            </p>
            <p className="text-[11px] text-ink-3 mt-0.5 leading-relaxed">{item.reason}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Learner Panel                                                              */
/* -------------------------------------------------------------------------- */
export function ProgressPanel() {
  const progress = useQuery({ queryKey: ["progress", "me"], queryFn: myProgress });
  const jobs = useQuery({ queryKey: ["jobs", "recent"], queryFn: () => listJobs(15) });

  if (progress.isError) return <ErrorNote>{String(progress.error)}</ErrorNote>;
  if (progress.isLoading || !progress.data) {
    return (
      <div className="flex items-center justify-center p-12 text-ink-3 text-sm">
        <Spinner className="mr-2" /> Loading learner metrics…
      </div>
    );
  }

  const p = progress.data;

  // Job columns definition
  const jobColumns: ColumnDef[] = [
    {
      key: "id",
      label: "Job ID",
      render: (val) => <span className="font-mono text-xs text-accent">#{val}</span>,
    },
    {
      key: "backend",
      label: "Backend",
      render: (val) => <Badge tone="neutral">{String(val)}</Badge>,
    },
    {
      key: "status",
      label: "Status",
      render: (val) => (
        <Badge tone={val === "completed" ? "ok" : val === "failed" ? "danger" : "warn"}>
          {String(val)}
        </Badge>
      ),
    },
    {
      key: "shots",
      label: "Shots",
      render: (val) => <span className="font-mono text-xs text-ink-2">{val ?? "—"}</span>,
    },
    {
      key: "created_at",
      label: "Timestamp",
      render: (val) => (
        <span className="text-xs text-ink-3">
          {val ? new Date(val).toLocaleTimeString() : "—"}
        </span>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* 4 Overview Metrics */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard label="Quizzes Completed" value={p.quizzes_taken} icon={GraduationCap} />
        <MetricCard label="Average Quiz Score" value={`${p.average_quiz_percentage}%`} icon={TrendingUp} />
        <MetricCard label="Challenges Attempted" value={p.challenges_attempted} icon={Puzzle} />
        <MetricCard
          label="Challenges Passed"
          value={p.challenges_passed}
          icon={Trophy}
          subtitle={`${Math.round((p.challenges_passed / Math.max(1, p.challenges_attempted)) * 100)}% success rate`}
        />
      </div>

      {/* Charts & Recommendations Grid */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Concept Mastery Chart */}
        <Card className="p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-line pb-3">
            <h3 className="text-sm font-bold uppercase tracking-wider text-ink flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-accent" /> Concept Mastery Breakdown
            </h3>
          </div>

          {(p.mastery ?? []).length > 0 ? (
            <MasteryChart rows={p.mastery} />
          ) : (
            <p className="text-xs text-ink-3 py-6 text-center">
              Complete lessons and challenges to populate concept mastery tracking.
            </p>
          )}
        </Card>

        {/* Quiz Progression SVG Chart */}
        <Card className="p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-line pb-3">
            <h3 className="text-sm font-bold uppercase tracking-wider text-ink flex items-center gap-2">
              <Clock className="h-4 w-4 text-accent" /> Quiz Performance Timeline
            </h3>
          </div>
          <QuizProgressionChart progress={p} />
        </Card>
      </div>

      {/* Recommended Next Actions */}
      <Card className="p-6">
        <div className="flex items-center gap-2 mb-4">
          <Sparkles className="h-4 w-4 text-accent" />
          <h3 className="text-sm font-bold uppercase tracking-wider text-ink">
            Recommended Next Learning Objectives
          </h3>
        </div>
        <Recommendations progress={p} />
      </Card>

      {/* Recent Simulation Jobs */}
      <Card className="p-6">
        <h3 className="text-base font-bold text-ink mb-4">Recent Quantum Simulator Jobs</h3>
        {jobs.isError ? (
          <ErrorNote>{String(jobs.error)}</ErrorNote>
        ) : jobs.isLoading ? (
          <div className="flex items-center gap-2 text-xs text-ink-3 py-6">
            <Spinner className="h-4 w-4" /> Fetching simulation history…
          </div>
        ) : (jobs.data ?? []).length === 0 ? (
          <EmptyState
            illustration={<NoSimulationsIllustration />}
            title="No simulations yet"
            description="Run your first quantum circuit from the Composer or Code Lab to generate execution data."
          />
        ) : (
          <DataTable columns={jobColumns} rows={jobs.data ?? []} />
        )}
      </Card>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Instructor Panel                                                           */
/* -------------------------------------------------------------------------- */
export function InstructorPanel() {
  const overview = useQuery({ queryKey: ["instructor-overview"], queryFn: instructorOverview });
  const students = useQuery({ queryKey: ["students"], queryFn: listStudents });
  const [pickedStudentId, setPickedStudentId] = useState<number | null>(null);

  const detail = useQuery({
    queryKey: ["student", pickedStudentId],
    queryFn: () => studentDetail(pickedStudentId as number),
    enabled: pickedStudentId !== null,
  });

  if (overview.isError) return <ErrorNote>{String(overview.error)}</ErrorNote>;
  if (overview.isLoading || !overview.data) {
    return (
      <div className="flex items-center justify-center p-12 text-ink-3 text-sm">
        <Spinner className="mr-2" /> Loading cohort analytics…
      </div>
    );
  }

  const data = overview.data;

  // Cohort Quiz completion table columns
  const quizCols: ColumnDef[] = [
    { key: "quiz_slug", label: "Quiz Topic", render: (v) => <span className="font-semibold text-xs">{v}</span> },
    { key: "attempts", label: "Total Attempts", render: (v) => <span className="font-mono text-xs">{v}</span> },
    { key: "best_score", label: "Avg / Best Score", render: (v) => <span className="font-mono text-xs text-ok">{v}%</span> },
  ];

  // Challenge completion table columns
  const challengeCols: ColumnDef[] = [
    { key: "challenge_slug", label: "Challenge", render: (v) => <span className="font-semibold text-xs">{v}</span> },
    { key: "attempts", label: "Attempts", render: (v) => <span className="font-mono text-xs">{v}</span> },
    { key: "best_score", label: "Best Score", render: (v) => <span className="font-mono text-xs text-ok">{v}</span> },
  ];

  // Leaderboard table columns
  const leaderboardCols: ColumnDef[] = [
    { key: "user_id", label: "Student ID", render: (v) => <span className="font-mono text-xs text-accent">#{v}</span> },
    { key: "challenges_passed", label: "Passed Challenges", render: (v) => <span className="font-mono text-xs font-bold text-ok">{v}</span> },
    { key: "score", label: "Total Score", render: (v) => <span className="font-mono text-xs">{v}</span> },
  ];

  return (
    <div className="space-y-6">
      {/* Top Cohort Metrics */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard label="Active Students" value={data.total_students} icon={GraduationCap} />
        <MetricCard label="Total Simulation Runs" value={data.total_jobs} icon={Clock} />
      </div>

      {/* Cohort Performance Tables */}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="p-6">
          <h3 className="text-sm font-bold uppercase tracking-wider text-ink mb-3">
            Quiz Completion Across Cohort
          </h3>
          <DataTable columns={quizCols} rows={data.quiz_completion ?? []} />
        </Card>

        <Card className="p-6">
          <h3 className="text-sm font-bold uppercase tracking-wider text-ink mb-3">
            Challenge Completion Across Cohort
          </h3>
          <DataTable columns={challengeCols} rows={data.challenge_completion ?? []} />
        </Card>
      </div>

      {/* Weakest Concepts & Leaderboard */}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="p-6">
          <h3 className="text-sm font-bold uppercase tracking-wider text-ink mb-3">
            Weakest Concepts in Cohort
          </h3>
          {data.weakest_tags.length > 0 ? (
            <MasteryChart
              rows={data.weakest_tags as unknown as MasteryRow[]}
              valueKey="average_score"
            />
          ) : (
            <p className="text-xs text-ink-3 py-6 text-center">No concept weaknesses identified.</p>
          )}
        </Card>

        <Card className="p-6">
          <h3 className="text-sm font-bold uppercase tracking-wider text-ink mb-3">
            Cohort Leaderboard
          </h3>
          <DataTable columns={leaderboardCols} rows={data.leaderboard ?? []} />
        </Card>
      </div>

      {/* Inspect Learner Details */}
      <Card className="p-6 space-y-4">
        <h3 className="text-base font-bold text-ink">Inspect Individual Learner</h3>
        <div className="max-w-md">
          <Label className="text-xs">Select Learner</Label>
          <Select
            value={pickedStudentId ? String(pickedStudentId) : ""}
            onValueChange={(val) => setPickedStudentId(Number(val))}
            className="bg-bg text-xs"
            placeholder="Select a student to inspect..."
          >
            {(students.data ?? []).map((student) => (
              <SelectItem key={student.id} value={String(student.id)}>
                {student.display_name || student.email} ({student.email})
              </SelectItem>
            ))}
          </Select>
        </div>

        {pickedStudentId !== null && (
          <div className="mt-4 pt-4 border-t border-line-soft">
            {detail.isLoading ? (
              <div className="flex items-center gap-2 text-xs text-ink-3">
                <Spinner className="h-4 w-4" /> Loading student profile…
              </div>
            ) : detail.data ? (
              <div className="space-y-4">
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                  <MetricCard label="Quizzes Taken" value={detail.data.quizzes_taken} />
                  <MetricCard label="Avg Score" value={`${detail.data.average_quiz_percentage}%`} />
                  <MetricCard label="Challenges Passed" value={detail.data.challenges_passed} />
                </div>
                {detail.data.mastery.length > 0 && (
                  <div className="mt-4">
                    <h4 className="text-xs font-bold uppercase text-ink-3 tracking-wider mb-2">
                      Mastery Profile
                    </h4>
                    <MasteryChart rows={detail.data.mastery} />
                  </div>
                )}
              </div>
            ) : null}
          </div>
        )}
      </Card>
    </div>
  );
}
