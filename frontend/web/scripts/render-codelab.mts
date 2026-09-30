/* Renders the REAL Code Lab page with the REAL providers, as a smoke test that
 * a type-check cannot give: import cycles, a hook outside its provider, a
 * component that throws on first paint.
 *
 *   npx tsx scripts/render-codelab.mts
 *   npm run render:codelab
 *
 * Two honest limits, both because renderToString never runs effects:
 *
 * 1. The language is chosen and the starter is loaded into the editor inside
 *    useEffect, so under SSR `framework` is still null. The interactive path —
 *    picking a language, typing, Build, Run — is verified in a browser only;
 *    see WEB_DEV.md. What is asserted here is the part that does not move.
 * 2. @uiw/react-codemirror is a browser component: server-side it mounts as an
 *    empty <div class="cm-theme-light"> and fills itself in on the client. The
 *    harness asserts that mount point and nothing more — the buffer contents,
 *    gutter markers and syntax colours are browser-only.
 *
 * The data contract behind the interactive path is covered separately: against
 * a live API by scripts/smoke-*.mts, and end to end by
 * backend/tests/test_codelab_check.py.
 */

const store = new Map<string, string>();
store.set(
  "ql-session",
  JSON.stringify({
    state: {
      token: "render-codelab-token",
      user: {
        id: 1,
        email: "a@b.dev",
        role: "student",
        display_name: "Render Check",
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
const { CodeLabPage } = await import("../src/pages/CodeLabPage.tsx");

let failures = 0;
function check(name: string, ok: boolean, extra = "") {
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${extra ? ` — ${extra}` : ""}`);
  if (!ok) failures += 1;
}

/** React separates adjacent text nodes with `<!-- -->` under renderToString. */
function text(html: string): string {
  return html.replace(/<!-- -->/g, "").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ");
}

const FRAMEWORKS = ["qiskit", "cirq", "pennylane", "qasm3", "qbraid"];
const STARTERS: Record<string, string> = {
  qiskit: "from qiskit import QuantumCircuit\ncircuit = QuantumCircuit(2, 2)\n",
  cirq: "import cirq\nq = cirq.LineQubit.range(2)\n",
  pennylane: "import pennylane as qml\n",
  qasm3: "OPENQASM 3.0;\ninclude \"stdgates.inc\";\n",
  qbraid: "from qbraid import QuantumProgram\n",
};

function render(): string {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: Infinity } },
  });
  client.setQueryData(["codelab-starters"], { frameworks: FRAMEWORKS, starters: STARTERS });
  return renderToString(
    createElement(
      QueryClientProvider,
      { client },
      createElement(MemoryRouter, { initialEntries: ["/codelab"] }, createElement(CodeLabPage)),
    ),
  );
}

const html = render();
const body = text(html);

/* ---------- it renders, and it is the real page ---------- */

check("the page renders without throwing", html.length > 2000, `${html.length} chars`);
check("it is no longer the P3 placeholder", !body.includes("Not built yet"));
// The editor mounts but paints nothing until it reaches a DOM; see the note
// above. Asserting the mount point is what SSR can honestly prove.
check("the CodeMirror editor mounts", html.includes("cm-theme"));
check("the build button is offered", body.includes("Build circuit"));
check("a reset-to-example control is offered", html.includes("Reset to example"));

/* ---------- the language list comes from the API, not a hard-coded guess ---------- */

check(
  "every language from GET /codelab/starters is offered",
  FRAMEWORKS.every((f) => html.includes(`value="${f}"`)),
);
check("each is shown under its own label", body.includes("PennyLane") && body.includes("OpenQASM 3"));

/* ---------- the honesty rules survive the port ---------- */

check("the one rule is stated", body.includes("assign your circuit to a variable named"));
check("the sandbox is described", body.includes("sandbox"));
check(
  "the AI box says the draft is not executed until you build it",
  body.includes("Nothing runs until you press Build"),
);
check(
  "the AI draft is called a starting point, not an answer",
  body.includes("treat it as a starting point, not an answer"),
);
check(
  "the list of importable libraries is kept",
  body.includes("networkx") && body.includes("sympy"),
);
check(
  "the concrete-angles rule is kept",
  body.includes("Angles must be concrete numbers"),
);
check(
  "the stdout promise is kept",
  body.includes("print()") && body.includes("shown back to you"),
);
check(
  "no result is claimed before a build",
  !body.includes("circuit built") && !body.includes("Built circuit"),
);

console.log(
  failures === 0
    ? "\nAll Code Lab render checks passed."
    : `\n${failures} Code Lab render check(s) FAILED.`,
);
process.exit(failures === 0 ? 0 : 1);
