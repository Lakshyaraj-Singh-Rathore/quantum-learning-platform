/* Renders the QML Lab in every flag state and checks what actually reaches
 * the markup.
 *
 *   npx tsx scripts/qml-render-check.mts
 *   npm run qml:render
 *
 * The flag has three states, not two — on, off, and *not yet answered* — and
 * the third is the one that breaks. A page that reads `data?.qml_enabled`
 * while the request is still in flight renders the disabled branch for a few
 * hundred milliseconds on every hard refresh, so a real user with the feature
 * enabled sees a 404 flash before their lab appears. Seeding the query cache
 * here reproduces all three deterministically.
 *
 * It also renders the charts with real data. They are hand-rolled SVG with no
 * library behind them, so "the component returned without throwing" is not
 * evidence that anything was drawn: these checks look for the actual <path>
 * geometry, the legend, and the confusion-matrix cells.
 */

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const store = new Map<string, string>();
store.set(
  "ql-session",
  JSON.stringify({
    state: {
      token: "qml-render-token",
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
  matchMedia: () => ({ matches: false, addEventListener() {}, removeEventListener() {} }),
};

/* The capability payload is captured from a live `GET /qml/describe` rather
 * than hand-written here. A hand-written one drifts: the first draft of this
 * harness invented `learning_rate`, `noise`, `test_fraction` and `seed`
 * limits that the server does not publish, so it was testing a contract that
 * does not exist. Regenerate with:
 *     curl -H "Authorization: Bearer $TOK" localhost:8000/qml/describe \
 *       > test-fixtures/qml-describe.json
 */
const describeFixture = JSON.parse(
  readFileSync(fileURLToPath(new URL("../test-fixtures/qml-describe.json", import.meta.url)), "utf-8"),
);

const { renderToString } = await import("react-dom/server");
const { createElement: h } = await import("react");
const { QueryClient, QueryClientProvider } = await import("@tanstack/react-query");
const { MemoryRouter } = await import("react-router-dom");
const { Sidebar } = await import("../src/components/shell/Sidebar.tsx");
const QmlLabPage = (await import("../src/pages/QmlLabPage.tsx")).default;
const { QmlTrainingDashboard } = await import("../src/components/qml/QmlTrainingDashboard.tsx");
const { QmlResultsPanel } = await import("../src/components/qml/QmlResultsPanel.tsx");
const { QmlCircuitPreview } = await import("../src/components/qml/QmlCircuitPreview.tsx");

/** React separates adjacent text nodes with an empty comment, so "85.0%"
 *  reaches the markup as `85.0<!-- -->%`. Stripping those makes a content
 *  assertion test the rendered text rather than React's node bookkeeping. */
const text = (html: string) => html.replace(/<!-- -->/g, "");

let failures = 0;
function check(name: string, ok: boolean, extra = "") {
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${extra ? ` — ${extra}` : ""}`);
  if (!ok) failures += 1;
}

type FlagState = "on" | "off" | "pending";

function render(node: unknown, flag: FlagState, path = "/qml-lab"): string {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: Infinity } },
  });
  // "pending" leaves the cache empty, which is exactly what a cold load is.
  if (flag !== "pending") {
    client.setQueryData(["features"], { qml_enabled: flag === "on" });
  }
  if (flag === "on") {
    client.setQueryData(["qml", "describe"], describeFixture);
    client.setQueryData(["qml", "experiments"], []);
  }
  return renderToString(
    h(
      QueryClientProvider,
      { client },
      h(MemoryRouter, { initialEntries: [path] }, node as never),
    ) as never,
  );
}

/* -------------------------------------------------------------------------- */
/* 0. The capability fixture is the shape the form is built against           */
/* -------------------------------------------------------------------------- */

check(
  "describe fixture: carries every key QmlDescribe declares",
  ["limits", "datasets", "diff_methods", "rotations", "entanglements", "device", "max_concurrent_experiments", "statuses"]
    .every((k) => k in describeFixture),
  Object.keys(describeFixture).join(", "),
);
// The form renders a range hint only for limits the server actually
// publishes. Recording which those are keeps the gap visible instead of
// letting a missing bound look like a bug in the form.
const published = Object.keys(describeFixture.limits).sort();
check(
  "describe fixture: published limits are the four bounded circuit/training fields",
  ["batch_size", "concurrent_jobs", "density_matrix_qubits", "epochs", "n_layers", "n_qubits", "n_samples"]
    .every((k) => published.includes(k)),
  published.join(", "),
);

/* -------------------------------------------------------------------------- */
/* 1. The nav entry, in all three flag states                                 */
/* -------------------------------------------------------------------------- */

const navOn = render(h(Sidebar, {}), "on");
const navOff = render(h(Sidebar, {}), "off");
const navPending = render(h(Sidebar, {}), "pending");

check("nav: entry present when the flag is on", navOn.includes("/qml-lab"));
check("nav: label rendered when on", navOn.includes("Quantum ML Lab"));
check("nav: entry absent when the flag is off", !navOff.includes("/qml-lab"));
check(
  "nav: entry absent while the flag is unresolved (no flash)",
  !navPending.includes("/qml-lab"),
);
check(
  "nav: existing entries unaffected by the flag",
  ["/learn", "/curriculum", "/composer", "/qudit-lab", "/codelab", "/challenges", "/games", "/dashboard", "/playground"]
    .every((p) => navOff.includes(p) && navOn.includes(p)),
);
check(
  "nav: the gated entry is the ONLY difference between on and off",
  navOn.replace(/<a[^>]*\/qml-lab[\s\S]*?<\/a>/g, "").length === navOff.length,
  `on=${navOn.length} off=${navOff.length}`,
);

/* -------------------------------------------------------------------------- */
/* 2. The route, in all three flag states                                     */
/* -------------------------------------------------------------------------- */

const pageOn = render(h(QmlLabPage, {}), "on");
const pageOff = render(h(QmlLabPage, {}), "off");
const pagePending = render(h(QmlLabPage, {}), "pending");

check("route: lab heading rendered when on", pageOn.includes("Quantum ML Lab"));
check(
  "route: all four views present when on",
  ["Configuration", "Circuit", "Training", "Results"].every((t) => pageOn.includes(t)),
);
check("route: config form rendered when on", pageOn.includes("qml-n-qubits"));
check("route: 404 body when the flag is off", pageOff.includes("404 - State Undefined"));
check("route: no config form when off", !pageOff.includes("qml-n-qubits"));
check(
  "route: neither lab nor 404 while unresolved (no flash)",
  !pagePending.includes("qml-n-qubits") && !pagePending.includes("404 - State Undefined"),
);

/* -------------------------------------------------------------------------- */
/* 3. Hand-rolled SVG actually draws                                          */
/* -------------------------------------------------------------------------- */

const history = Array.from({ length: 8 }, (_, i) => ({
  epoch: i + 1,
  train_loss: 0.9 - i * 0.08,
  train_accuracy: 0.5 + i * 0.05,
  test_loss: 0.95 - i * 0.07,
  test_accuracy: 0.48 + i * 0.05,
  elapsed_seconds: (i + 1) * 1.5,
}));

const dash = render(
  h(QmlTrainingDashboard, {
    experimentId: 7,
    status: "running",
    history,
    totalEpochs: 10,
    error: null,
    cached: false,
    onCancel: () => {},
    cancelling: false,
    cancelError: null,
    onViewResults: () => {},
  } as never),
  "on",
);

// Count only the *stroked* curves. The gradient fill under the first series
// is also a <path> with M…L…L geometry, so a count of all paths — or a
// coordinate regex over the whole document — stays green even when every
// line is blanked out. Ask specifically for fill="none" paths carrying a
// polyline of at least three points.
const strokedCurves = [...dash.matchAll(/<path([^>]*)\/?>/g)]
  .map((m) => m[1])
  .filter((attrs) => /fill="none"/.test(attrs))
  .map((attrs) => /\sd="([^"]*)"/.exec(attrs)?.[1] ?? "");
const drawnCurves = strokedCurves.filter((d) => (d.match(/[ML]/g) ?? []).length >= 3);
check(
  "charts: loss and accuracy curves emit stroked <path> geometry",
  drawnCurves.length >= 4,
  `${drawnCurves.length} drawn of ${strokedCurves.length} stroked paths`,
);
check(
  "charts: every stroked curve has real coordinates",
  strokedCurves.length > 0 && strokedCurves.every((d) => /^M[\d.]+,[\d.]+( L[\d.]+,[\d.]+)+$/.test(d)),
  strokedCurves.map((d) => d.slice(0, 24)).join(" | "),
);
// Well-formed coordinates are not enough: a broken y-scale produces a
// perfectly valid path that is a flat line, which renders cleanly and tells
// the reader nothing. Every series in the fixture is monotone, so each curve
// must span a range of y values.
const ySpans = strokedCurves.map((d) => {
  const ys = [...d.matchAll(/[ML]([\d.]+),([\d.]+)/g)].map((m) => Number(m[2]));
  return ys.length === 0 ? 0 : Math.max(...ys) - Math.min(...ys);
});
check(
  "charts: curves vary on the y axis (the scale is live, not flat)",
  ySpans.length > 0 && ySpans.every((span) => span > 1),
  ySpans.map((v) => v.toFixed(1)).join(", "),
);
check("charts: legend labels both series", dash.includes("train loss") && dash.includes("test loss"));
check("charts: colours come from theme tokens", dash.includes("var(--color-accent)"));
check(
  "charts: no interpolated class reached the markup",
  !/class="[^"]*\$\{/.test(dash) && !dash.includes("undefined-"),
);
check("dashboard: progress bar exposes a value", dash.includes('role="progressbar"'));
check("dashboard: epoch counter reflects the history", dash.includes("8"));
check("dashboard: cancel offered while running", dash.includes("Cancel"));

/* -------------------------------------------------------------------------- */
/* 4. Results: confusion matrix and the baseline comparison                   */
/* -------------------------------------------------------------------------- */

const results = render(
  h(QmlResultsPanel, {
    status: "completed",
    error: null,
    inference: undefined,
    onRunInference: () => {},
    inferenceRunning: false,
    inferenceError: null,
    result: {
      evaluation: {
        accuracy: 0.85,
        precision: 0.8,
        recall: 0.9,
        f1: 0.847,
        confusion_matrix: [[23, 4], [3, 30]],
        n_samples: 60,
      },
      baseline: {
        model: "logistic_regression",
        train_accuracy: 0.88,
        test_accuracy: 0.83,
        n_parameters: 3,
        converged: true,
      },
      circuit: { n_parameters: 8 },
      dataset: { n_features: 2, feature_names: ["x1", "x2"] },
      epochs_completed: 10,
      duration_seconds: 12.4,
      final_train_loss: 0.21,
      final_train_accuracy: 0.87,
    },
  } as never),
  "on",
);

// Position matters, not just presence. The fixture [[23,4],[3,30]] contains
// the same four numbers when transposed, so checking that each value appears
// somewhere cannot tell a correct matrix from one with precision and recall
// swapped. Read the cells back in document order instead.
const cells = [...results.matchAll(/title="(?:Correct|Incorrect): true (\d), predicted (\d)[^"]*?(\d+)"/g)]
  .map((m) => [Number(m[1]), Number(m[2]), Number(m[3])]);
check(
  "results: confusion-matrix cells are in the right positions",
  JSON.stringify(cells) === JSON.stringify([[0, 0, 23], [0, 1, 4], [1, 0, 3], [1, 1, 30]]),
  JSON.stringify(cells),
);
check(
  "results: matrix orientation is labelled",
  text(results).includes("true 0") && text(results).includes("pred 1"),
);
check("results: accuracy shown", text(results).includes("85.0%"));
check(
  "results: classical baseline shown alongside",
  text(results).includes("logistic_regression") && text(results).includes("83.0%"),
);
check("results: inference panel offers one input per feature", results.includes("qml-feature-0") && results.includes("qml-feature-1"));
check("results: cell colours are inline tokens, not classes", results.includes("var(--color-ok)"));

const cancelled = render(
  h(QmlResultsPanel, {
    status: "cancelled",
    error: null,
    inference: undefined,
    onRunInference: () => {},
    inferenceRunning: false,
    inferenceError: null,
    result: { interrupted: true, reason: "cancelled" },
  } as never),
  "on",
);
check(
  "results: an interrupted run offers no model, and says so",
  cancelled.includes("Run cancelled") && !cancelled.includes("qml-feature-0"),
);

/* -------------------------------------------------------------------------- */
/* 5. Circuit view reuses the shared diagram                                  */
/* -------------------------------------------------------------------------- */

const circuit = render(
  h(QmlCircuitPreview, {
    circuit: { n_qubits: 3, n_layers: 2, rotation: "Y", entanglement: "ring" },
    nFeatures: 2,
    serverParameters: 12,
  } as never),
  "on",
);
check("circuit: a diagram is drawn", circuit.includes("<svg"));
check("circuit: parameter count agrees with the server", !circuit.includes("no longer matches"));
check("circuit: idle ancilla wire explained", circuit.includes("ancilla"));

const drifted = render(
  h(QmlCircuitPreview, {
    circuit: { n_qubits: 3, n_layers: 2, rotation: "Y", entanglement: "ring" },
    nFeatures: 2,
    serverParameters: 99,
  } as never),
  "on",
);
check("circuit: drift from the server is surfaced, not hidden", drifted.includes("no longer matches"));

console.log(
  failures === 0
    ? "ALL CHECKS PASSED — QML Lab renders correctly in every flag state"
    : `${failures} QML render check(s) FAILED.`,
);
process.exit(failures === 0 ? 0 : 1);
