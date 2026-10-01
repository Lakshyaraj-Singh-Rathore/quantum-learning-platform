/* Renders the REAL Grover module against the ported simulation.
 *
 *   npx tsx scripts/render-grover.mts
 *   npm run render:grover
 *
 * Every number asserted here is computed by src/lib/grover.ts at render time,
 * and that module is itself pinned to numpy by `npm run golden:grover`
 * (3306 values at 1e-9). So the defaults below -- 2⁶ = 64 states, optimal 6
 * iterations, 1.56% at iteration 0 rising to 99.66% -- are not transcribed
 * from anywhere; the page works them out.
 *
 * Click-only behaviour is deliberately not claimed: the predict-and-reveal
 * button and the over-rotation toggle are local state. The over-rotation
 * PROPERTY (probability peaks then falls) is asserted in the golden check
 * instead, where it belongs.
 */

const store = new Map<string, string>();
store.set(
  "ql-session",
  JSON.stringify({
    state: {
      token: "render-grover-token",
      user: { id: 1, email: "a@b.dev", role: "student", display_name: "Render Grover", is_active: true },
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
const { GroverLab } = await import("../src/components/grover/GroverLab.tsx");

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

function render(): string {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: Infinity } } });
  return renderToString(
    createElement(
      QueryClientProvider,
      { client },
      createElement(MemoryRouter, { initialEntries: ["/games"] }, createElement(GroverLab)),
    ),
  );
}

const html = render();
const body = text(html);

/* ---------- the framing ---------- */

check("the module renders", html.length > 8000, `${html.length} chars`);
check(
  "it says plainly that quantum computers do not crack passwords",
  body.includes("Quantum computers do not magically crack passwords"),
);
check("and that the speedup is quadratic, not magic", body.includes("quadratic") && body.includes("O(√N)"));
check("the oracle precondition is stated", body.includes("oracle"));
check("the password is described as a toy that stays local", body.includes("never leaves your browser session"));

/* ---------- the setup ---------- */

check("the search space is stated", body.includes("2^6 = 64 states"));
check("the qubit count is capped, with the reason", body.includes("Capped at 6"));

/* ---------- the pipeline and the numbers ---------- */

check(
  "the pipeline is shown as stages, not as brute force",
  body.includes("superposition → oracle (phase flip) → diffusion (amplify) → measure"),
);
check("the optimal count is stated", body.includes("⌊π/4·√N⌋ = 6"));
check("it opens at the optimum", body.includes("Iteration 6 / 6") || body.includes("6 / 6"));
// 1/64 at iteration 0, 99.66% at iteration 6 -- both computed, not transcribed.
check("the target probability at the optimum is shown", body.includes("99.66%"), "P(target) at iteration 6");
check("the other-state probability is shown too", body.includes("P(any other state)"));
check("the target amplitude is shown", body.includes("Target amplitude"));

/* ---------- the curve and the search space ---------- */

check("the growth curve is drawn", html.includes("<polyline"));
check("the over-rotation experiment is offered", body.includes("keep going past the optimum"));
check(
  "all 64 states are listed with their probabilities",
  (html.match(/<tr/g) ?? []).length >= 64,
  `${(html.match(/<tr/g) ?? []).length} table rows`,
);
check("the target is marked", body.includes("🎯"));

/* ---------- measurement ---------- */

check("shots can be chosen", body.includes("Shots"));
check("the measured result is compared against theory", body.includes("theory"));

/* ---------- the comparison ---------- */

check(
  "classical and Grover are compared side by side",
  body.includes("Classical brute force") && body.includes("How it searches"),
);
check("the complexities are given", body.includes("O(N)") && body.includes("O(√N)"));
check(
  "Grover is honest about being probabilistic",
  body.includes("Probabilistic") && body.includes("not guaranteed"),
);
check("the closed form is cross-checked on the page", body.includes("sin²"));

/* ---------- the honesty section ---------- */

check("the demonstration caveat is present", body.includes("Why 6 qubits is only a demonstration"));
check("it scales the claim up to a real password", body.includes("10²³"));
check("it mentions the defences real systems have", body.includes("salted and hashed") && body.includes("rate-limited"));
check(
  "and gives the takeaway about key length",
  body.includes("halves the effective key length") && body.includes("256 bits"),
);

console.log(
  failures === 0
    ? "\nAll Grover render checks passed."
    : `\n${failures} Grover check(s) FAILED.`,
);
process.exit(failures === 0 ? 0 : 1);
