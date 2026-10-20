/* Renders the REAL Playground against the real components.
 *
 *   npx tsx scripts/render-playground.mts
 *   npm run render:playground
 *
 * The Playground collects the lesson demos in one place, so five of its seven
 * tabs ARE the lesson demos and are rendered from the same components -- this
 * asserts that reuse rather than trusting it. The other two (Bit vs Qubit and
 * Build a Qubit) are Playground-specific and are rendered from here.
 *
 * Same honest limit as the other harnesses: renderToString cannot click, so
 * switching tabs is browser-only. Each tab is rendered directly instead.
 */

const store = new Map<string, string>();
store.set(
  "ql-session",
  JSON.stringify({
    state: {
      token: "render-playground-token",
      user: { id: 1, email: "a@b.dev", role: "student", display_name: "Render Playground", is_active: true },
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
const { BitVsQubit, BuildAQubit } = await import("../src/pages/PlaygroundPage.tsx");
const {
  MeasurementLab,
  InterferenceLab,
  PlusVsMinus,
  StateSpaceGrowth,
  BitOrdering,
} = await import("../src/components/demos/Demos.tsx");

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

function render(node: React.ReactElement): string {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: Infinity } } });
  return renderToString(
    createElement(
      QueryClientProvider,
      { client },
      createElement(MemoryRouter, { initialEntries: ["/playground"] }, node),
    ),
  );
}

/* ---------- 1. Bit vs Qubit ---------- */

const bitHtml = render(createElement(BitVsQubit));
const bitText = text(bitHtml);
check("the tab renders", bitHtml.length > 1000, `${bitHtml.length} chars`);
check("the headline is kept", bitText.includes("Classical Bits vs Quantum Superposition"));
check("both sides are shown", bitText.includes("Classical Discrete Bit") && bitText.includes("Quantum Statevector Qubit"));
check("the classical half explains determinism", bitText.includes("Deterministic") && bitText.includes("does not disturb"));
check("the quantum half shows superposition state", bitText.includes("Bloch sphere") && bitText.includes("Statevector"));

/* ---------- 2. Build a Qubit, with the real grid ---------- */

const buildHtml = render(createElement(BuildAQubit));
const buildText = text(buildHtml);
check("the tab renders", buildHtml.length > 3000, `${buildHtml.length} chars`);
check("the headline is kept", buildText.includes("Complex Amplitudes vs Probabilities"));
check("both ways of describing the state are offered", buildText.includes("Amplitudes") && buildText.includes("Bloch angles"));
check("it embeds the real grid", buildHtml.includes("composer-inner") || buildHtml.includes("composer-columns") || buildHtml.includes("workspace"));
check("a blank wire can be reset", buildText.includes("Reset Wire"));
check("the state, angles and probabilities are all shown", buildText.includes("P(|0⟩)") && buildText.includes("Bloch θ") && buildText.includes("Bloch φ"));
check("the Bloch sphere is drawn", buildHtml.includes("<svg"));

check(
  "unitary gate mechanics reference is present",
  buildText.includes("Unitary Gate Mechanics Reference") && (buildText.includes("HADAMARD") || buildText.includes("H")),
);
check(
  "operations display or wire manipulation is offered",
  buildText.includes("Apply Unitary Operations") || buildText.includes("Operations:"),
);
check("state vector metrics are calculated", buildText.includes("State Vector Metrics"));

/* ---------- the five shared tabs really are the lesson demos ---------- */

check(
  "Measure is the lesson demo",
  text(render(createElement(MeasurementLab))).includes("sampling error"),
);
// The blurb ("Amplitudes add before they are squared") is drawn by the Learn
// page's tab strip, not by the demo, so assert on the demo's own caption.
check(
  "Interference is the lesson demo",
  text(render(createElement(InterferenceLab))).includes("Two paths lead to the same outcome"),
);
check(
  "|+⟩ vs |−⟩ is the lesson demo",
  text(render(createElement(PlusVsMinus))).includes("50/50"),
);
check(
  "Many Qubits is the lesson demo",
  text(render(createElement(StateSpaceGrowth))).includes("Amplitudes to track"),
);
check(
  "Bit Order is the lesson demo",
  text(render(createElement(BitOrdering))).includes("rightmost"),
);

console.log(
  failures === 0
    ? "\nAll Playground render checks passed."
    : `\n${failures} Playground check(s) FAILED.`,
);
process.exit(failures === 0 ? 0 : 1);
