import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
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
import { Card, ErrorNote, Spinner, cn } from "../components/ui";

export function DashboardPage() {
  const user = useSession((state) => state.user);
  const isInstructor = user?.role === "instructor" || user?.role === "admin";
  const [tab, setTab] = useState<"mine" | "instructor">("mine");

  return (
    <div className="flex flex-col gap-5 p-6">
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="text-xl font-semibold tracking-tight">Dashboard</h2>
        {isInstructor && (
          <div className="ml-auto flex gap-1 rounded-lg border border-line bg-raised p-1">
            {(["mine", "instructor"] as const).map((value) => (
              <button
                key={value}
                onClick={() => setTab(value)}
                className={cn(
                  "rounded-md px-3 py-1 text-[13px] transition-colors",
                  tab === value ? "bg-accent text-white" : "text-ink-2 hover:bg-hover",
                )}
              >
                {value === "mine" ? "My progress" : "Instructor"}
              </button>
            ))}
          </div>
        )}
      </div>
      {tab === "mine" || !isInstructor ? <ProgressPanel /> : <InstructorPanel />}
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* shared pieces                                                              */
/* -------------------------------------------------------------------------- */

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg border border-line bg-raised px-3 py-2">
      <p className="text-[11px] uppercase tracking-wide text-ink-3">{label}</p>
      <p className="text-lg font-semibold text-ink">{value}</p>
    </div>
  );
}

/** The mastery bars Streamlit drew with st.bar_chart. */
function MasteryChart({ rows, valueKey = "score" }: { rows: MasteryRow[]; valueKey?: string }) {
  const peak = Math.max(...rows.map((row) => Number(row[valueKey] ?? 0)), 1);
  return (
    <div className="flex flex-col gap-1">
      {rows.map((row) => {
        const value = Number(row[valueKey] ?? 0);
        return (
          <div key={String(row.tag)} className="flex items-center gap-2">
            <span className="w-24 truncate text-[12px] text-ink-2">{String(row.tag)}</span>
            <div className="h-3 flex-1 overflow-hidden rounded bg-hover">
              <div className="h-full bg-accent" style={{ width: `${(value / peak) * 100}%` }} />
            </div>
            <span className="w-12 text-right font-mono text-[11px] text-ink-3">
              {value.toFixed(2)}
            </span>
          </div>
        );
      })}
    </div>
  );
}

function DataTable({ rows }: { rows: Record<string, unknown>[] }) {
  const columns = Object.keys(rows[0] ?? {});
  return (
    <div className="overflow-auto rounded-lg border border-line-soft">
      <table className="w-full text-[13px]">
        <thead>
          <tr className="border-b border-line bg-hover/40 text-left text-[11px] uppercase tracking-wide text-ink-3">
            {columns.map((column) => (
              <th key={column} className="whitespace-nowrap px-3 py-2 font-medium">
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={index} className="border-b border-line-soft/60 last:border-0">
              {columns.map((column) => (
                <td key={column} className="whitespace-nowrap px-3 py-1.5 font-mono text-ink-2">
                  {String(row[column] ?? "")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Recommendations({ progress }: { progress: LearnerProgress }) {
  const items = progress.recommendations ?? [];
  if (items.length === 0) {
    return <p className="text-[13px] text-ink-3">No recommendations yet.</p>;
  }
  return (
    <div className="flex flex-col gap-2">
      {items.map((item) => (
        <div key={`${item.kind}-${item.slug}`}>
          <p className="text-[13px] font-semibold text-ink">
            {item.kind === "lesson" ? "📘" : "🧩"} {item.title ?? item.slug}
          </p>
          <p className="text-[12px] text-ink-3">{item.reason}</p>
        </div>
      ))}
    </div>
  );
}

function ProgressBody({ progress }: { progress: LearnerProgress }) {
  return (
    <>
      <div className="grid grid-cols-2 gap-2 lg:grid-cols-4">
        <Metric label="Quizzes taken" value={progress.quizzes_taken} />
        <Metric label="Challenges attempted" value={progress.challenges_attempted} />
        <Metric label="Challenges passed" value={progress.challenges_passed} />
        <Metric label="Average quiz score" value={`${progress.average_quiz_percentage}%`} />
      </div>
      <div className="grid gap-5 lg:grid-cols-2">
        <div>
          <h3 className="mb-2 text-sm font-semibold">Concept mastery</h3>
          {(progress.mastery ?? []).length > 0 ? (
            <div className="flex flex-col gap-3">
              <MasteryChart rows={progress.mastery} />
              <DataTable
                rows={progress.mastery.map((row) => row as unknown as Record<string, unknown>)}
              />
            </div>
          ) : (
            <p className="text-[13px] text-ink-3">
              Take a quiz or submit a challenge to start tracking mastery.
            </p>
          )}
        </div>
        <div>
          <h3 className="mb-2 text-sm font-semibold">Recommended next</h3>
          <Recommendations progress={progress} />
        </div>
      </div>
    </>
  );
}

/* -------------------------------------------------------------------------- */
/* Learner                                                                    */
/* -------------------------------------------------------------------------- */

export function ProgressPanel() {
  const progress = useQuery({ queryKey: ["progress", "me"], queryFn: myProgress });
  const jobs = useQuery({ queryKey: ["jobs", "recent"], queryFn: () => listJobs(15) });

  if (progress.isError) return <ErrorNote>{String(progress.error)}</ErrorNote>;
  if (progress.isLoading || !progress.data) {
    return (
      <p className="flex items-center gap-2 text-sm text-ink-3">
        <Spinner /> loading progress…
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-5">
      <Card className="flex flex-col gap-5">
        <ProgressBody progress={progress.data} />
      </Card>

      <Card>
        <h3 className="mb-3 text-sm font-semibold">Recent simulations</h3>
        {jobs.isError ? (
          <p className="text-[13px] text-warn">{String(jobs.error)}</p>
        ) : jobs.isLoading ? (
          <p className="flex items-center gap-2 text-[13px] text-ink-3">
            <Spinner /> loading…
          </p>
        ) : (jobs.data ?? []).length === 0 ? (
          <p className="text-[13px] text-ink-3">No simulations yet.</p>
        ) : (
          <DataTable rows={jobs.data as unknown as Record<string, unknown>[]} />
        )}
      </Card>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Instructor                                                                 */
/* -------------------------------------------------------------------------- */

function Section({
  title,
  rows,
  empty,
  children,
}: {
  title: string;
  rows?: Record<string, unknown>[];
  empty: string;
  children?: React.ReactNode;
}) {
  return (
    <div>
      <h3 className="mb-2 text-sm font-semibold">{title}</h3>
      {children ?? (rows && rows.length > 0 ? <DataTable rows={rows} /> : <p className="text-[13px] text-ink-3">{empty}</p>)}
    </div>
  );
}

export function InstructorPanel() {
  const overview = useQuery({
    queryKey: ["instructor-overview"],
    queryFn: instructorOverview,
  });
  const students = useQuery({ queryKey: ["students"], queryFn: listStudents });
  const [picked, setPicked] = useState<number | null>(null);
  const detail = useQuery({
    queryKey: ["student", picked],
    queryFn: () => studentDetail(picked as number),
    enabled: picked !== null,
  });

  if (overview.isError) return <ErrorNote>{String(overview.error)}</ErrorNote>;
  if (overview.isLoading || !overview.data) {
    return (
      <p className="flex items-center gap-2 text-sm text-ink-3">
        <Spinner /> loading the cohort…
      </p>
    );
  }

  const data = overview.data;

  return (
    <div className="flex flex-col gap-5">
      <Card className="flex flex-col gap-5">
        <div className="grid grid-cols-2 gap-2 lg:grid-cols-4">
          <Metric label="Students" value={data.total_students} />
          <Metric label="Simulation jobs" value={data.total_jobs} />
        </div>
        <Section title="Quiz completion" rows={data.quiz_completion} empty="No quiz attempts yet." />
        <Section
          title="Challenge completion"
          rows={data.challenge_completion}
          empty="No challenge attempts yet."
        />
        <div className="grid gap-5 lg:grid-cols-2">
          <Section title="Common errors" rows={data.common_errors} empty="No errors recorded." />
          <Section
            title="Weakest concepts (cohort)"
            empty="Not enough data yet."
            rows={undefined}
          >
            {data.weakest_tags.length > 0 ? (
              <MasteryChart
                rows={data.weakest_tags as unknown as MasteryRow[]}
                valueKey="average_score"
              />
            ) : (
              <p className="text-[13px] text-ink-3">Not enough data yet.</p>
            )}
          </Section>
        </div>
        <Section title="Leaderboard" rows={data.leaderboard} empty="No completed challenges yet." />
      </Card>

      <Card>
        <h3 className="mb-3 text-sm font-semibold">Students</h3>
        {students.isError ? (
          <p className="text-[13px] text-warn">{String(students.error)}</p>
        ) : students.isLoading ? (
          <p className="flex items-center gap-2 text-[13px] text-ink-3">
            <Spinner /> loading…
          </p>
        ) : (students.data ?? []).length === 0 ? (
          <p className="text-[13px] text-ink-3">No learner accounts yet.</p>
        ) : (
          <div className="flex flex-col gap-4">
            <DataTable rows={students.data as unknown as Record<string, unknown>[]} />
            <div>
              <p className="mb-2 text-[13px] font-semibold text-ink">Inspect a learner</p>
              <select
                value={picked ?? ""}
                onChange={(e) => setPicked(Number(e.target.value))}
                className="h-9 w-full max-w-md rounded-lg border border-line bg-raised px-2 text-sm text-ink"
              >
                <option value="" disabled>
                  Student
                </option>
                {(students.data ?? []).map((student) => (
                  <option key={student.id} value={student.id}>
                    {student.display_name || student.email} ({student.email})
                  </option>
                ))}
              </select>
            </div>
            {picked !== null &&
              (detail.isLoading ? (
                <p className="flex items-center gap-2 text-[13px] text-ink-3">
                  <Spinner /> loading…
                </p>
              ) : detail.isError ? (
                <ErrorNote>{String(detail.error)}</ErrorNote>
              ) : detail.data ? (
                <div className="flex flex-col gap-4 rounded-lg border border-line-soft p-3">
                  <ProgressBody progress={detail.data} />
                </div>
              ) : null)}
          </div>
        )}
      </Card>
    </div>
  );
}
