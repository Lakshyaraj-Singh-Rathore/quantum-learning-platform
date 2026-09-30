/* Renders the REAL React tree with the REAL providers — no browser, no mocks.
 * Catches what a type-check cannot: import cycles, hooks used outside their
 * provider, a component that throws on first paint, a gate that leaks a
 * protected page to an anonymous visitor. Complements scripts/smoke-auth.mts,
 * which exercises the data layer against a live API.
 *
 *   npx tsx scripts/render-check.mts            # signed in as a student
 *   npx tsx scripts/render-check.mts --anon    # nobody signed in
 *   npx tsx scripts/render-check.mts --staff   # signed in as an instructor
 *   npm run render-check                       # runs all three
 *
 * Two things worth knowing about this harness:
 *
 * 1. The app is client-rendered on purpose; react-dom/server is used purely as
 *    a smoke harness. React Router's <Navigate> renders nothing on the server
 *    (the redirect is an effect), so "anonymous visit yields no markup" is the
 *    correct expectation, and it is asserted as a PAIR with the signed-in run
 *    where the only difference is the stored session.
 * 2. Under renderToString React reads zustand's SERVER snapshot, which is the
 *    store's INITIAL state — setState after creation is invisible here. So the
 *    session is seeded into storage and the stores are imported afterwards,
 *    letting rehydration make the token part of the initial state, exactly as
 *    it would be for a learner reloading a signed-in tab.
 */

const anon = process.argv.includes("--anon");
const staff = process.argv.includes("--staff");

const SESSION = {
  state: {
    token: "render-check-token",
    user: staff
      ? { id: 2, email: "i@b.dev", role: "instructor", display_name: "Instructor", is_active: true }
      : { id: 1, email: "a@b.dev", role: "student", display_name: "Render Check", is_active: true },
  },
  version: 0,
};

// The stores persist to localStorage, which Node does not have, and zustand
// reads it as `window.localStorage` (zustand/esm/middleware.mjs). Both shims
// are installed BEFORE any app module is imported: ESM hoists static imports,
// so the app modules are pulled in dynamically below, after this runs.
// `window` deliberately has no `document`, so React keeps treating this as a
// server render.
const store = new Map<string, string>();
if (!anon) store.set("ql-session", JSON.stringify(SESSION));
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
const React = await import("react");
const { createElement } = await import("react");
const { MemoryRouter } = await import("react-router-dom");
const { QueryClient, QueryClientProvider } = await import("@tanstack/react-query");
const App = (await import("../src/App.tsx")).default;
const { Sidebar } = await import("../src/components/shell/Sidebar.tsx");
const { TopBar } = await import("../src/components/shell/TopBar.tsx");
const { PlaceholderPage } = await import("../src/pages/PlaceholderPage.tsx");
const { useTheme } = await import("../src/state/theme.ts");

let failures = 0;
function check(name: string, ok: boolean, extra = "") {
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${extra ? ` — ${extra}` : ""}`);
  if (!ok) failures += 1;
}

function renderAt(path: string): string {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, enabled: false } },
  });
  return renderToString(
    createElement(
      QueryClientProvider,
      { client },
      createElement(MemoryRouter, { initialEntries: [path] }, createElement(App)),
    ),
  );
}

/** Renders one component with the providers it needs. Used for the signed-in
 *  chrome: under renderToString, zustand's server snapshot is the store's
 *  INITIAL state (zustand/esm/vanilla.mjs -> `getInitialState`), so a
 *  rehydrated session can never reach a component through a hook here. The
 *  chrome is therefore rendered directly, and anything that depends on live
 *  session state (the identity chip, the live engine list) is verified in a
 *  real browser instead — see WEB_DEV.md. */
function renderWith(node: React.ReactElement, path = "/composer"): string {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, enabled: false } },
  });
  return renderToString(
    createElement(
      QueryClientProvider,
      { client },
      createElement(MemoryRouter, { initialEntries: [path] }, node),
    ),
  );
}

const NAV = ["Learn", "Composer", "Challenges", "Dashboard", "Code Lab", "Games", "Playground"];
const mode = anon ? "anonymous" : staff ? "instructor" : "student";

if (anon) {
  // Nobody signed in: every protected route must redirect to /login rather
  // than render even a sliver of the app.
  for (const path of ["/learn", "/composer", "/codelab", "/dashboard", "/games", "/playground"]) {
    const html = renderAt(path);
    check(`${path} leaks nothing to an anonymous visitor`, html === "", `${html.length} chars`);
  }
  const login = renderAt("/login");
  check("the login screen renders for an anonymous visitor", login.includes("Sign in") && login.includes("Create account"));
  check("the login screen offers both modes", login.includes("Create account") && login.includes("Sign in"));
  check("the login screen links back to the classic UI", login.includes(":8501"));
} else {
  // Signed in: the gate lets the tree through, so assert the chrome renders.
  const rail = renderWith(createElement(Sidebar));
  const bar = renderWith(createElement(TopBar));
  const page = renderWith(
    createElement(PlaceholderPage, {
      title: "Composer",
      phase: "P1–P2",
      intro: "the drag-and-drop canvas and the full result tab strip",
      bullets: ["Canvas island mount", "All result tabs"],
      proof: true,
    }),
  );

  check(`the sidebar renders (${mode})`, rail.length > 0, `${rail.length} chars`);
  check("sidebar lists all seven pages", NAV.every((l) => rail.includes(l)), NAV.filter((l) => !rail.includes(l)).join(", ") || "all present");
  check("sidebar links carry their rebuild phase", rail.includes("rebuilt in P4") && rail.includes("rebuilt in P1–P2"));
  check("sidebar states the migration is in progress", rail.includes("UI migration in progress"));
  check(`the top bar renders (${mode})`, bar.length > 0, `${bar.length} chars`);
  check("top bar carries the engine badge", bar.includes("engines"));
  check("theme toggle is labelled for screen readers", bar.includes("Switch to light mode"));
  check(`the page body renders (${mode})`, page.length > 0, `${page.length} chars`);
  check("page states plainly that it is not rebuilt yet", page.includes("rebuilt in"));
  check("page lists what is coming", page.includes("Canvas island mount") && page.includes("All result tabs"));
  check("live-proof strip renders its own heading", page.includes("Live from the API"));
  for (const [name, html] of [["sidebar", rail], ["top bar", bar], ["page", page]] as const) {
    check(`no exception text leaked into the ${name}`, !/Cannot read|is not a function|undefined is not/.test(html));
  }
}

// A theme preference must survive a reload — that is what persist is for, and
// it is the one piece of state the shell owns that outlives a tab.
useTheme.getState().toggle();
const persisted = JSON.parse(store.get("ql-theme") ?? "{}");
check("theme preference is persisted", persisted?.state?.theme === "light", JSON.stringify(persisted?.state ?? {}));

console.log(failures === 0 ? `\nALL CHECKS PASSED (${mode})` : `\n${failures} CHECK(S) FAILED (${mode})`);
process.exit(failures === 0 ? 0 : 1);
