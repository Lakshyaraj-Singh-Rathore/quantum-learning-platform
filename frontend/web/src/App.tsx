import { Suspense, lazy } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./components/shell/AppShell";
import { RequireAuth } from "./components/RequireAuth";
import { LoginPage } from "./pages/LoginPage";
import { ComposerPage } from "./pages/ComposerPage";

// The editor drags in CodeMirror, which nothing else uses. Keeping it out of
// the main chunk means the other pages still load at ~95 kB gzip.
const CodeLabPage = lazy(() =>
  import("./pages/CodeLabPage").then((m) => ({ default: m.CodeLabPage })),
);
// Same reason: the reader pulls in react-markdown and KaTeX, which nothing
// else on the platform needs.
const LearnPage = lazy(() => import("./pages/LearnPage").then((m) => ({ default: m.LearnPage })));
// Same reason again: both of these pull in the shared composer grid.
const ChallengesPage = lazy(() =>
  import("./pages/ChallengesPage").then((m) => ({ default: m.ChallengesPage })),
);
const DashboardPage = lazy(() =>
  import("./pages/DashboardPage").then((m) => ({ default: m.DashboardPage })),
);
const GamesPage = lazy(() =>
  import("./pages/GamesPage").then((m) => ({ default: m.GamesPage })),
);
const PlaygroundPage = lazy(() =>
  import("./pages/PlaygroundPage").then((m) => ({ default: m.PlaygroundPage })),
);

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
<Route path="/challenges" element={<ChallengesPage />} />
<Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/codelab" element={<CodeLabPage />} />
<Route path="/games" element={<GamesPage />} />
<Route path="/playground" element={<PlaygroundPage />} />
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
