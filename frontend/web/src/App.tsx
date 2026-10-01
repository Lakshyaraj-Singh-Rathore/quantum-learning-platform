import { Suspense, lazy } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./components/shell/AppShell";
import { RequireAuth } from "./components/RequireAuth";
import { LoginPage } from "./pages/LoginPage";
import { PlaceholderPage } from "./pages/PlaceholderPage";
import { ComposerPage } from "./pages/ComposerPage";

// The editor drags in CodeMirror, which nothing else uses. Keeping it out of
// the main chunk means the other pages still load at ~95 kB gzip.
const CodeLabPage = lazy(() =>
  import("./pages/CodeLabPage").then((m) => ({ default: m.CodeLabPage })),
);
// Same reason: the reader pulls in react-markdown and KaTeX, which nothing
// else on the platform needs.
const LearnPage = lazy(() => import("./pages/LearnPage").then((m) => ({ default: m.LearnPage })));

function NotFound() {
  return (
    <div className="grid h-full place-items-center">
      <div className="text-center">
        <p className="text-3xl font-semibold tracking-tight">404</p>
        <p className="mt-2 text-sm text-ink-3">
          No such page in this shell.{" "}
          <a href="/learn" className="text-accent hover:underline">
            Back to Learn
          </a>
        </p>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <Suspense fallback={<RouteFallback />}>
      <Routes>
        <Route path="/login" element={<LoginPage mode="login" />} />
        <Route path="/register" element={<LoginPage mode="register" />} />
        <Route element={<RequireAuth />}>
          <Route element={<AppShell />}>
            <Route index element={<Navigate to="/learn" replace />} />
            <Route path="/learn" element={<LearnPage />} />
            <Route path="/composer" element={<ComposerPage />} />
            <Route
              path="/challenges"
              element={
                <PlaceholderPage
                  title="Challenges"
                  phase="P5"
                  intro="Graded circuits against target distributions. Grading stays exactly where it is — server-side — with the shot-noise tolerance notes carried over verbatim."
                  bullets={[
                    "Challenge cards with difficulty and personal best",
                    "Target distribution plot + 'open in Composer with this circuit'",
                    "Submission history and the pass/fail explanation copy, unchanged",
                  ]}
                />
              }
            />
            <Route
              path="/dashboard"
              element={
                <PlaceholderPage
                  title="Dashboard"
                  phase="P5"
                  intro="Learner progress and the instructor overview, same data and role gating as today."
                  bullets={[
                    "Stat row, recent runs with backend badges, lesson progress",
                    "Instructor table with per-student drill-in drawer",
                    "Recommendations chip from GET /recommendations",
                  ]}
                  proof
                />
              }
            />
            <Route path="/codelab" element={<CodeLabPage />} />
            <Route
              path="/games"
              element={
                <PlaceholderPage
                  title="Games"
                  phase="P6"
                  intro="Gate golf, circuit reversal and the rest — scoring semantics untouched, validation ratified by POST /inspect like the Composer."
                  bullets={[
                    "Level cards and play field with the same scoring rules",
                    "GET /games catalogue, server-side grading",
                  ]}
                />
              }
            />
            <Route
              path="/playground"
              element={
                <PlaceholderPage
                  title="Playground"
                  phase="P6"
                  intro="Free-form experiments: gate table, parameter sliders, instant state previews. Preview math ports to TypeScript with golden tests; real circuits run through /jobs."
                  bullets={[
                    "Gate preview table with exact amplitudes (fixture-pinned)",
                    "Parameter sliders wired to the same state views as Composer",
                  ]}
                />
              }
            />
            <Route path="*" element={<NotFound />} />
          </Route>
        </Route>
      </Routes>
    </Suspense>
  );
}

/** Shown while a lazily-loaded page's chunk is in flight. */
function RouteFallback() {
  return (
    <div className="flex items-center gap-2 p-6 text-sm text-ink-3">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-line border-t-accent" />
      loading…
    </div>
  );
}
