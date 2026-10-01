/* Renders the REAL composer and checks the IBM-style canvas is actually drawn.
 *
 *   npx tsx scripts/render-composer.mts
 *   npm run render:composer
 *
 * This is not a screenshot diff -- it cannot tell you whether the result is
 * beautiful. What it can tell you is that the parts are present and correctly
 * wired: qubit chips, the ⊕ target marker, the measurement meter, the wire
 * from that meter down to a classical bit, and the double-line register.
 *
 * Those are the things that silently break. A restyle that drops the classical
 * register still renders a plausible-looking circuit, which is exactly the
 * kind of regression worth catching.
 */

const store = new Map<string, string>();
store.set(
  "ql-session",
  JSON.stringify({
    state: {
      token: "render-composer-token",
      user: { id: 1, email: "a@b.dev", role: "student", display_name: "Render", is_active: true },
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
const { QueryClient, QueryClientProvider } = await import("@tanstack/react-query");
const { ComposerInner } = await import("@composer/Composer");
const { emptyCircuit, makeOp } = await import("@composer/ir");

let failures = 0;
function check(name: string, ok: boolean, extra = "") {
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${extra ? ` — ${extra}` : ""}`);
  if (!ok) failures += 1;
}

/* A circuit exercising every shape the canvas has to draw. */
const ir = {
  ...emptyCircuit(3),
  n_clbits: 3,
  ops: [
    makeOp("gate", { gate: "h", qubits: [0], layer: 0 }),
    makeOp("gate", { gate: "x", qubits: [1], controls: [0], layer: 1 }),
    makeOp("gate", { gate: "t", qubits: [2], layer: 2 }),
    makeOp("barrier", { qubits: [0, 1, 2], layer: 3 }),
    makeOp("gate", { gate: "swap", qubits: [0, 2], layer: 4 }),
    makeOp("measure", { qubits: [0], clbits: [0], layer: 5 }),
    makeOp("measure", { qubits: [1], clbits: [1], layer: 5 }),
  ],
};

const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: Infinity } } });
const html = renderToString(
  createElement(
    QueryClientProvider,
    { client },
    createElement(ComposerInner, { value: ir, nQubits: 3 }),
  ),
);

// React splits an interpolated label into two text nodes and separates them
// with an empty comment, so `q{q}` reaches the DOM as `q<!-- -->0`. Strip the
// markers before asserting on label text; class names are unaffected.
const plain = html.replace(/<!--.*?-->/g, "");
const count = (needle: string) => html.split(needle).length - 1;

/* ---------- the canvas is drawn at all ---------- */

check("the composer renders", html.length > 4000, `${html.length} chars`);

/* ---------- qubit wires ---------- */

check("qubits are labelled IBM-style (q0, q1, q2)", plain.includes(">q0<") && plain.includes(">q1<") && plain.includes(">q2<"));
check("each qubit carries a colour chip", count('class="qchip"') === 3, `${count('class="qchip"')} chips`);
check("there is one wire per qubit", count('class="wire"') === 3, `${count('class="wire"')} wires`);

/* ---------- gate shapes ---------- */

check("Hadamard is a filled tile", html.includes(">H<"));
check("a CNOT target is drawn as ⊕, not as a tile", count("gate target") === 1);
check("a CNOT control is a dot on the control wire", count("ctrl-dot") === 1);
check("the control and target are joined", count("ctrl-line") >= 1);
check("SWAP is drawn as two ✕ joined by a line", count("gate swap") === 2 && html.includes("✕"));

/* ---------- measurement collapses into the register ---------- */

check("measurement is a meter dial, not the letter M", count("meter-dial") === 2, `${count("meter-dial")} meters`);
check(
  "each meter is wired down to a classical bit",
  count("m-wire") === 2,
  `${count("m-wire")} meter wires`,
);

/* ---------- the classical register ---------- */

check("the classical register is drawn", count('class="clbit"') === 6, `${count('class="clbit"')} strokes`);
check("each register line is a double stroke", count('class="clbit"') === ir.n_clbits * 2);
check("register bits are labelled", plain.includes(">c0<") && plain.includes(">c1<"));

/* ---------- barriers ---------- */

check("a barrier is a dashed rule across the wires", count('class="barrier"') === 1);

/* ---------- the palette rail ---------- */

check("the palette sits in its own rail", html.includes('class="palette"'));
check("the circuit sits beside it", html.includes('class="canvas-col"'));
check("gates and ops are both offered", html.includes("Multi-qubit") && html.includes("Ops"));
check("CNOT is offered by name", html.includes("CNOT"));

/* ---------- nothing regressed ---------- */

check("the qubit controls are still there", html.includes("Qubit"));
check("Measure All is still offered", html.includes("Measure All"));
check("no React error markup leaked", !html.includes("Element type is invalid"));

console.log(
  failures === 0
    ? "\nAll composer render checks passed."
    : `\n${failures} composer check(s) FAILED.`,
);
process.exit(failures === 0 ? 0 : 1);
