/* Renders the REAL composer and checks the reference interface is drawn.
 *
 *   npx tsx scripts/render-composer.mts
 *   npm run render:composer
 *
 * This cannot tell you whether the result is beautiful. What it can tell you
 * is that the parts are present, correctly coloured, and correctly wired: the
 * six-column palette, the gate colours, the ⊕ target, the measurement meter,
 * the double-line register, the circular wire endpoints, the toolbar, and the
 * code panel.
 *
 * A restyle that silently dropped the classical register, or turned a ⊕ back
 * into a plain tile, would still render a plausible-looking circuit. That is
 * exactly the regression this exists to catch.
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

// React splits an interpolated label into two text nodes separated by an empty
// comment, so `q[{q}]` reaches the DOM as `q[<!-- -->0]`. Strip them before
// asserting on label text; class names are unaffected.
const plain = html.replace(/<!--.*?-->/g, "");
const count = (needle: string) => html.split(needle).length - 1;

/* ---------- shell ---------- */

check("the composer renders", html.length > 6000, `${html.length} chars`);
check("it is a three-column shell", html.includes("composer-columns"));
check("the operations sidebar is present", html.includes("ops-sidebar"));
check("the workspace is present", html.includes('class="workspace"'));
check("the code panel is present", html.includes("code-panel"));

/* ---------- palette ---------- */

check("the palette is a grid of gate buttons", count("gate-btn") === 25, `${count("gate-btn")} buttons`);
check("Hadamard is red, per the reference", html.includes("#F84D63"));
check("the X family is blue", html.includes("#4385F5"));
check("standard single-qubit gates are pale blue", html.includes("#B5E1F6"));
check("rotations are pink", html.includes("#F66DB8"));
check("structural ops are grey", html.includes("#A2A9AE"));
check("CNOT is offered by name", html.includes("CNOT"));
check("Controlled-Y is offered", html.includes(">CY<"));
check("SWAP is offered", html.includes("SWAP"));
check(
  "control flow is offered",
  html.includes("If / Else") && html.includes(">For<") && html.includes(">While<"),
);

/* ---------- toolbar ---------- */

check("undo and redo are present", plain.includes("↶") && plain.includes("↷"));
check("undo starts disabled with no history", count("disabled") >= 2);
check("an alignment control is present", html.includes("align-select"));
check("an Inspect toggle is present", html.includes("inspect-toggle") && html.includes("Inspect"));
check("the qubit and measurement actions survived", html.includes("Qubit") && html.includes("Measure All"));

/* ---------- canvas ---------- */

check("qubits are labelled q[0], q[1], q[2]", plain.includes(">q[0]<") && plain.includes(">q[1]<") && plain.includes(">q[2]<"));
check("there is one wire per qubit", count('class="wire"') === 3);
check("each wire ends in a circular control", count('endpoint') === 3, `${count("endpoint")} endpoints`);
check("Hadamard is a tile", plain.includes(">H<"));
check("a CNOT target is a ⊕, not a tile", count("gate target") === 1);
check("a CNOT control is a dot", count("ctrl-dot") === 1);
check("control and target are joined", count("ctrl-line") >= 1);
check("SWAP draws two ✕ joined by a line", count("gate swap") === 2 && html.includes("✕"));

/* ---------- measurement and the classical register ---------- */

check("measurement is a meter dial, not the letter M", count("meter-dial") === 2, `${count("meter-dial")} meters`);
check("each meter is wired down to the register", count("m-wire") === 2);
check("the register is a double line", count('class="clbit"') === 2, `${count('class="clbit"')} strokes`);
check("the register is labelled with its width", plain.includes(">c3<"));

/* ---------- barriers ---------- */

check("a barrier is a dashed rule across the wires", count('class="barrier"') === 1);

/* ---------- code panel ---------- */

check("the code panel shows line numbers", count('class="ln"') === 7, `${count('class="ln"')} lines`);
check("the code panel shows the circuit text", plain.includes("measure q0"));

/* ---------- nothing regressed ---------- */

check("no React error markup leaked", !html.includes("Element type is invalid"));

console.log(
  failures === 0
    ? "\nAll composer render checks passed."
    : `\n${failures} composer check(s) FAILED.`,
);
process.exit(failures === 0 ? 0 : 1);
