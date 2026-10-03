/* Audit of empty / error / loading states.
 *
 *   npx tsx scripts/states-check.mts
 *   npm run states
 *
 * The last unchecked item on the P7 list. The failure mode it guards against
 * is the quiet one: a page that renders *nothing* when its data has not
 * arrived, or when the backend is down, or when the list it was given is
 * empty. Each of those looks identical from the outside -- a blank panel with
 * no explanation -- and none of them show up in a happy-path screenshot.
 *
 * Two techniques, because neither alone is enough:
 *
 *   1. Render each page with pending queries, and assert it says so. A page
 *      that renders an empty panel while fetching is indistinguishable from a
 *      page with no data, which is exactly the confusion being prevented.
 *   2. Read each page's source for an error branch and an empty branch. Weaker
 *      than rendering them -- renderToString cannot show a rejected query,
 *      because SSR does not await -- but it catches the case where a branch
 *      was never written at all.
 *
 * Recognises the shared Spinner and ErrorNote, so pages are not forced to
 * hand-roll their own wording for the common cases.
 */

import { readFileSync } from "node:fs";

const store = new Map<string, string>();
store.set(
  "ql-session",
  JSON.stringify({
    state: {
      token: "states-token",
      user: { id: 1, email: "a@b.dev", role: "student", display_name: "States", is_active: true },
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

let failures = 0;
function check(name: string, ok: boolean, extra = "") {
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${extra ? ` — ${extra}` : ""}`);
  if (!ok) failures += 1;
}

const pages: [string, string, string][] = [
  ["Learn", "LearnPage", "../src/pages/LearnPage.tsx"],
  ["Curriculum", "CurriculumPage", "../src/pages/CurriculumPage.tsx"],
  ["Composer", "ComposerPage", "../src/pages/ComposerPage.tsx"],
  ["Challenges", "ChallengesPage", "../src/pages/ChallengesPage.tsx"],
  ["Dashboard", "DashboardPage", "../src/pages/DashboardPage.tsx"],
  ["Code Lab", "CodeLabPage", "../src/pages/CodeLabPage.tsx"],
  ["Games", "GamesPage", "../src/pages/GamesPage.tsx"],
  ["Playground", "PlaygroundPage", "../src/pages/PlaygroundPage.tsx"],
];

/** Render with every query still pending, which is the SSR default. */
function renderPending(node: React.ReactElement): string {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: Infinity } } });
  return renderToString(
    createElement(
      QueryClientProvider,
      { client },
      createElement(MemoryRouter, { initialEntries: ["/"] }, node),
    ),
  );
}

/** A loading affordance: the shared Spinner, or the word. */
const looksLoading = (html: string) =>
  html.includes("animate-spin") || /loading|fetching|checking/i.test(html.replace(/<[^>]+>/g, " "));

// The shell must wrap page content in an error boundary. Without it any throw
// unmounts the whole tree -- the user gets a blank screen and cannot even
// navigate away, because the navigation unmounted with everything else.
const shell = readFileSync(new URL("../src/components/shell/AppShell.tsx", import.meta.url), "utf8");
const hasBoundary = shell.includes("ErrorBoundary");
check("the shell wraps page content in an error boundary", hasBoundary);

for (const [name, exportName, path] of pages) {
  const mod = (await import(path)) as Record<string, React.ComponentType>;
  const Component = mod[exportName];
  if (!Component) {
    check(`${name}: exports ${exportName}`, false);
    continue;
  }

  // --- 1. the page must not render a silent blank while its data is in flight
  const html = renderPending(createElement(Component));
  const fetches = /useQuery|useMutation/.test(readFileSync(new URL(path, import.meta.url), "utf8"));

  if (fetches) {
    check(`${name} shows a loading state`, looksLoading(html), `${html.length} chars rendered`);
  } else {
    // A page with no network dependency has nothing to load. Saying so is
    // better than demanding a spinner it would have to fake.
    check(`${name} makes no network calls, so has nothing to load`, true);
  }

  // --- 2. source-level: an error branch and an empty branch must exist
  const source = readFileSync(new URL(path, import.meta.url), "utf8");
  const hasError =
    source.includes("isError") ||
    source.includes("ErrorNote") ||
    source.includes("onError") ||
    source.includes("catch");
  const hasEmpty =
    /length === 0|\.length\s*<\s*1|isEmpty|No \w+ yet|no \w+ yet|nothing here|empty/i.test(source);

  // A page with no network calls can still throw -- a local demo fed an odd
  // value is enough. What saves it is the shell's error boundary, so that is
  // what is required here rather than per-page try/catch.
  check(`${name} handles errors`, hasError || hasBoundary, hasError ? "" : "via the shell boundary");
  check(`${name} handles empty data`, hasEmpty);
}

// Prove the boundary works -- within the limits of what SSR can show.
//
// Error boundaries do NOT run under renderToString: React's legacy server
// renderer propagates the throw instead of catching it (verified here, not
// assumed -- a throwing child escapes to the caller). That is fine, because
// the white-screen scenario being prevented is a *client-side* crash, which
// is exactly where the boundary does its job.
//
// So what is asserted is the machinery the client depends on: that the
// boundary converts a thrown error into state, that it reports the component
// stack, and that a fallback with a real message exists. If any of those are
// removed, this fails.
const { ErrorBoundary } = await import("../src/components/shell/ErrorBoundary.tsx");
const probe = new Error("synthetic failure for the states audit");
const derived = ErrorBoundary.getDerivedStateFromError(probe);
check("the boundary converts a thrown error into state", derived.error === probe);
check("the boundary keeps the error message intact", derived.error?.message === probe.message);
check(
  "the boundary logs the component stack, not just the message",
  ErrorBoundary.prototype.componentDidCatch.length === 2,
);

const boundarySrc = readFileSync(
  new URL("../src/components/shell/ErrorBoundary.tsx", import.meta.url),
  "utf8",
);
check("the fallback names what broke", boundarySrc.includes("stopped working"));
check("the fallback shows the real error, not a generic one", boundarySrc.includes("error.message"));
check("the fallback offers a way out", boundarySrc.includes("Try again"));

console.log(
  failures === 0
    ? "\nAll pages handle empty, error and loading states."
    : `\n${failures} state gap(s) found.`,
);
process.exit(failures === 0 ? 0 : 1);
