import { Suspense, lazy } from "react";
import { Link, Route, Routes } from "react-router-dom";
import { AppShell } from "./components/shell/AppShell";
import { RequireAuth } from "./components/RequireAuth";
import { LoginPage } from "./pages/LoginPage";
import { HomePage } from "./pages/HomePage";
import { ComposerPage } from "./pages/ComposerPage";
import { Button, Spinner } from "./components/ui";
import { Compass } from "lucide-react";

// Lazy-loaded page bundles to keep initial load lean
const CodeLabPage = lazy(() =>
  import("./pages/CodeLabPage").then((m) => ({ default: m.CodeLabPage })),
);
const LearnPage = lazy(() =>
  import("./pages/LearnPage").then((m) => ({ default: m.LearnPage })),
);
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
const CurriculumPage = lazy(() =>
  import("./pages/CurriculumPage").then((m) => ({ default: m.CurriculumPage })),
);
const TopicDetailPage = lazy(() =>
  import("./pages/TopicDetailPage").then((m) => ({ default: m.TopicDetailPage })),
);
const QuditLabPage = lazy(() =>
  import("./pages/QuditLabPage").then((m) => ({ default: m.QuditLabPage })),
);
// Lazy like every other page, so the lab's chunk is never downloaded by a
// deployment that has the flag off. The page gates itself as well: the route
// stays registered, and renders the 404 body when the server says off.
const QmlLabPage = lazy(() => import("./pages/QmlLabPage"));

function NotFound() {
  return (
    <div className="flex h-full flex-col items-center justify-center p-8 text-center">
      <div className="grid h-16 w-16 place-items-center rounded-2xl bg-subtle border border-line text-ink-3 mb-4">
        <Compass className="h-8 w-8 text-accent" />
      </div>
      <h1 className="text-3xl font-bold tracking-tight text-ink">404 - State Undefined</h1>
      <p className="mt-2 text-sm text-ink-3 max-w-sm">
        The quantum route you collapsed does not exist in this Hilbert space.
      </p>
      <Link to="/learn" className="mt-6">
        <Button variant="primary" size="md">
          Return to Learn Workspace
        </Button>
      </Link>
    </div>
  );
}

export default function App() {
  return (
    <Suspense fallback={<RouteFallback />}>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/login" element={<LoginPage mode="login" />} />
        <Route path="/register" element={<LoginPage mode="register" />} />
        <Route element={<RequireAuth />}>
          <Route element={<AppShell />}>
            <Route path="/learn" element={<LearnPage />} />
            <Route path="/curriculum" element={<CurriculumPage />} />
            <Route path="/curriculum/topic/:topicId" element={<TopicDetailPage />} />
            <Route path="/composer" element={<ComposerPage />} />
            <Route path="/qudit-lab" element={<QuditLabPage />} />
            <Route path="/qml-lab" element={<QmlLabPage />} />
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

/** Fallback loader when lazy chunks are in transit */
function RouteFallback() {
  return (
    <div className="flex h-screen w-screen items-center justify-center bg-bg text-ink-3 text-sm">
      <Spinner className="mr-2.5 h-5 w-5" />
      <span>Initializing quantum interface…</span>
    </div>
  );
}
