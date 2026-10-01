/* Renders the REAL Challenges and Dashboard pages against REAL data.
 *
 *   npx tsx scripts/render-p5.mts
 *   npm run render:p5
 *
 * The fixture is test-fixtures/challenges.json, captured from a live API
 * (regenerate with scripts/challenge-fixtures.py): 5 quizzes, 13 challenges,
 * a scored quiz result, learner progress and the instructor overview.
 *
 * Honest limit, the same one the other harnesses have: renderToString never
 * runs effects and never fires a mutation, so anything behind a click is not
 * reachable here. Two things are therefore browser-only and are NOT claimed as
 * verified: the scored quiz view, and the graded-attempt result. The data
 * behind both was exercised against a live API instead (quiz submit returned
 * 1.0/3.0 with per-question feedback; a challenge submit graded with its
 * feedback string).
 */

import { readFileSync } from "node:fs";

const INSTRUCTOR = process.argv.includes("--instructor");

const store = new Map<string, string>();
store.set(
  "ql-session",
  JSON.stringify({
    state: {
      token: "render-p5-token",
      user: {
        id: 1,
        email: INSTRUCTOR ? "instructor@local.dev" : "a@b.dev",
        role: INSTRUCTOR ? "instructor" : "student",
        display_name: INSTRUCTOR ? "Instructor" : "Render P5",
        is_active: true,
      },
    },
    version: 0,
  }),
);
const storage = {
  getItem: (k: string) => store.get(k) ?? null,
  setItem: (k: string, v: string) => void store.set(k, v),
  removeItem: (k: string) => void store.delete(k),
  clear: () => store.clear(),
  key: () => null,
  length: 0,
};
(globalThis as { localStorage?: unknown }).localStorage = storage;
(globalThis as { window?: unknown }).window = {
  localStorage: storage,
  location: { hostname: "localhost", href: "http://localhost/", origin: "http://localhost" },
};

const { renderToString } = await import("react-dom/server");
const { createElement } = await import("react");
const { MemoryRouter } = await import("react-router-dom");
const { QueryClient, QueryClientProvider } = await import("@tanstack/react-query");
const { QuizTab, CodingTab } = await import("../src/pages/ChallengesPage.tsx");
const { ProgressPanel, InstructorPanel } = await import("../src/pages/DashboardPage.tsx");

let failures = 0;
function check(name: string, ok: boolean, extra = "") {
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${extra ? ` — ${extra}` : ""}`);
  if (!ok) failures += 1;
}

const ENTITIES: Record<string, string> = { "&#x27;": "'", "&quot;": '"', "&amp;": "&", "&lt;": "<", "&gt;": ">", "&#39;": "'" };
function text(html: string): string {
  return html
    .replace(/<!-- -->/g, "")
    .replace(/<[^>]+>/g, " ")
    .replace(/&#x27;|&quot;|&amp;|&lt;|&gt;|&#39;/g, (m) => ENTITIES[m] ?? m)
    .replace(/\s+/g, " ");
}

const fixture = JSON.parse(
  readFileSync(new URL("../test-fixtures/challenges.json", import.meta.url), "utf8"),
) as {
  quizzes: { slug: string; title: string; tags: string[]; questions: { id: number; prompt: string; qtype: string; options: string[] }[] }[];
  challenges: {
    slug: string;
    title: string;
    prompt: string;
    allowed_gates: string[];
    constraints: Record<string, unknown>;
    is_dynamic: boolean;
  }[];
  progress: {
    quizzes_taken: number;
    challenges_attempted: number;
    challenges_passed: number;
    average_quiz_percentage: number;
    mastery: Record<string, unknown>[];
    recommendations: { kind: string; slug: string; title?: string; reason: string }[];
  };
  overview: Record<string, unknown> & { total_students: number; total_jobs: number };
  students: { id: number; email: string; display_name: string | null }[];
};

check("the fixture is real data", fixture.quizzes.length === 5 && fixture.challenges.length === 13, `${fixture.quizzes.length} quizzes, ${fixture.challenges.length} challenges`);

function render(node: React.ReactElement, seed: Record<string, unknown> = {}): string {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: Infinity } } });
  client.setQueryData(["quizzes"], fixture.quizzes);
  client.setQueryData(["challenges"], fixture.challenges);
  client.setQueryData(["progress", "me"], fixture.progress);
  client.setQueryData(["jobs", "recent"], []);
  client.setQueryData(["instructor-overview"], fixture.overview);
  client.setQueryData(["students"], fixture.students);
  client.setQueryData(["student", fixture.students[0].id], fixture.students[0]);
  for (const [key, value] of Object.entries(seed)) client.setQueryData(JSON.parse(key), value);
  return renderToString(
    createElement(QueryClientProvider, { client }, createElement(MemoryRouter, { initialEntries: ["/challenges"] }, node)),
  );
}

/* ---------- Quizzes ---------- */

const quizHtml = render(createElement(QuizTab));
const quizText = text(quizHtml);

check("the quiz tab renders", quizHtml.length > 1500, `${quizHtml.length} chars`);
check("it is not the P5 placeholder", !quizText.includes("Not built yet"));
check("every quiz is selectable", fixture.quizzes.every((q) => quizText.includes(q.title)));
const firstQuiz = fixture.quizzes[0];
check(
  "the questions are numbered and shown",
  firstQuiz.questions.every((q, i) => quizText.includes(`${i + 1}. ${q.prompt}`)),
  firstQuiz.questions.map((q) => q.qtype).join(", "),
);
check(
  "multiple choice renders as real radio buttons",
  quizHtml.includes('type="radio"') && firstQuiz.questions.some((q) => q.options.every((o) => quizText.includes(o))),
);
check("there is a submit control", quizText.includes("Submit answers"));
check("the concepts line is kept", quizText.includes("Concepts:"));

/* ---------- Coding challenges ---------- */

const codingHtml = render(createElement(CodingTab));
const codingText = text(codingHtml);

check("the coding tab renders", codingHtml.length > 1500, `${codingHtml.length} chars`);
check(
  "every challenge is selectable",
  fixture.challenges.every((c) => codingText.includes(c.title)),
);
const challenge = fixture.challenges[0];
check("the challenge title is shown", codingText.includes(challenge.title));
check(
  "the allowed gates are listed",
  challenge.allowed_gates.every((gate) => codingText.includes(gate)),
  challenge.allowed_gates.join(", "),
);
check(
  "the constraints are listed",
  Object.entries(challenge.constraints).every(([key, value]) => codingText.includes(`${key}=${String(value)}`)),
  JSON.stringify(challenge.constraints),
);
check("it points at the Composer to build", codingText.includes("Build your solution in the Composer"));
// The circuit comes from the shared store, whose initial state is a Bell pair.
check("the shared circuit is shown", codingText.includes("Current circuit: 2 qubits, depth 3, static"));
check("there is a submit control", codingText.includes("Submit this circuit"));
check(
  "no result is claimed before submitting",
  !codingText.includes("Grading details") && !codingText.includes("Score"),
);

/* ---------- Learner dashboard ---------- */

const progressHtml = render(createElement(ProgressPanel));
const progressText = text(progressHtml);

check("the progress panel renders", progressHtml.length > 1200, `${progressHtml.length} chars`);
check(
  "all four headline metrics are shown",
  ["Quizzes taken", "Challenges attempted", "Challenges passed", "Average quiz score"].every((label) =>
    progressText.includes(label),
  ),
);
check("mastery is drawn", progressText.includes("Concept mastery") && progressHtml.includes("bg-accent"));
check(
  "every mastery row is listed",
  fixture.progress.mastery.every((row) => progressText.includes(String(row.tag))),
  fixture.progress.mastery.map((r) => r.tag).join(", "),
);
check(
  "every recommendation is listed with its reason",
  fixture.progress.recommendations.every((item) => progressText.includes(item.reason)),
);
check("recent simulations has an honest empty state", progressText.includes("No simulations yet."));

/* ---------- Instructor dashboard ---------- */

const instructorHtml = render(createElement(InstructorPanel));
const instructorText = text(instructorHtml);

check("the instructor panel renders", instructorHtml.length > 1500, `${instructorHtml.length} chars`);
check("the cohort metrics are shown", instructorText.includes("Students") && instructorText.includes("Simulation jobs"));
check("quiz completion is tabled", instructorText.includes("Quiz completion") && instructorHtml.includes("<table"));
check("challenge completion is tabled", instructorText.includes("Challenge completion"));
check(
  "common errors are listed",
  (fixture.overview.common_errors as { error: string }[]).every((row) => instructorText.includes(row.error.slice(0, 40))),
);
check(
  "the cohort's weakest concepts are charted",
  (fixture.overview.weakest_tags as { tag: string }[]).every((row) => instructorText.includes(row.tag)),
);
check("the leaderboard is tabled", instructorText.includes("Leaderboard"));
check(
  "every student is listed",
  fixture.students.every((student) => instructorText.includes(student.email)),
  fixture.students.map((s) => s.email).join(", "),
);
check("a learner can be inspected", instructorText.includes("Inspect a learner"));

const EMPTY_OVERVIEW = {
  ...fixture.overview,
  quiz_completion: [],
  challenge_completion: [],
  common_errors: [],
  weakest_tags: [],
  leaderboard: [],
};
const emptyInstructor = text(
  render(createElement(InstructorPanel), { '["instructor-overview"]': EMPTY_OVERVIEW }),
);
check(
  "a fresh cohort gets honest empty states, not empty boxes",
  [
    "No quiz attempts yet.",
    "No challenge attempts yet.",
    "No errors recorded.",
    "Not enough data yet.",
    "No completed challenges yet.",
  ].every((message) => emptyInstructor.includes(message)),
  [
    "No quiz attempts yet.",
    "No challenge attempts yet.",
    "No errors recorded.",
    "Not enough data yet.",
    "No completed challenges yet.",
  ].filter((m) => !emptyInstructor.includes(m)).join(" | ") || "all five",
);
check(
  "a fresh cohort still shows its zero counts",
  emptyInstructor.includes("Students") && emptyInstructor.includes("Simulation jobs"),
);

console.log(
  failures === 0 ? "\nAll P5 render checks passed." : `\n${failures} P5 check(s) FAILED.`,
);
process.exit(failures === 0 ? 0 : 1);
