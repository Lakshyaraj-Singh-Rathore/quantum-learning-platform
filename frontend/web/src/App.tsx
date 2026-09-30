import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./components/shell/AppShell";
import { RequireAuth } from "./components/RequireAuth";
import { LoginPage } from "./pages/LoginPage";
import { PlaceholderPage } from "./pages/PlaceholderPage";
import { ComposerPage } from "./pages/ComposerPage";

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
    <Routes>
      <Route path="/login" element={<LoginPage mode="login" />} />
      <Route path="/register" element={<LoginPage mode="register" />} />
      <Route element={<RequireAuth />}>
        <Route element={<AppShell />}>
          <Route index element={<Navigate to="/learn" replace />} />
          <Route
            path="/learn"
            element={
              <PlaceholderPage
                title="Learn"
                phase="P4"
                intro="13 lessons with the interactive demos embedded beside the text — the same widgets that live in the Streamlit app today, rebuilt as React components with golden-number parity."
                bullets={[
                  "Lesson reader with TOC and quizzes via GET /lessons and /quizzes",
                  "Live Bloch demo (the existing React island, mounted directly)",
                  "Grover amplitude lab — the 1/64 → 99.66% over-rotation story, ported with golden tests",
                  "Every demo number pinned to fixtures recorded from today's build",
                ]}
                proof
              />
            }
          />
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
          <Route
            path="/codelab"
            element={
              <PlaceholderPage
                title="Code Lab"
                phase="P3"
                intro="The sandboxed editor for six frameworks including native CUDA-Q kernels — CodeMirror left, live diagnostics (via the new POST /codelab/check), Build/Run into the same result views as Composer."
                bullets={[
                  "Framework tabs from GET /codelab/starters (availability-filtered, so CUDA-Q appears on the GPU stack)",
                  "Syntax, blocked-import and missing-circuit diagnostics as gutter markers",
                  "stdout, sandbox errors and the AI draft box with its 'AI cannot execute' note, verbatim",
                ]}
              />
            }
          />
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
  );
}
