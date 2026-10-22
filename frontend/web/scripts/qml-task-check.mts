/* Does the Lab tell the truth about a task that has no accuracy, and about a
 * run that has no epochs?
 *
 *   npx tsx scripts/qml-task-check.mts
 *   npm run qml:tasks
 *
 * Why this exists. `api/qml.ts:98` declared `train_accuracy: number` while
 * the database column is nullable and every regression epoch stores NULL.
 * TypeScript erases at runtime, so the value arrived as `null` and
 * `(null * 100).toFixed(1)` renders "0.0%" — a measurement the model never
 * produced, displayed under a legend that says "accuracy". That is D-033 for
 * the third time, now at the type layer, and no backend test can see it:
 * the API is correct, the renderer is not.
 *
 * The second half is the kernel. It is one closed-form solve, so it writes
 * **zero** epoch rows. A dashboard that assumes a curve exists shows an empty
 * axis or spins forever, both of which claim something false about a run that
 * completed successfully.
 *
 * Fixtures are captured from real runs by `scripts/qml-task-fixtures.py`,
 * not hand-written. A hand-written regression history would have whatever
 * the author believed the null handling to be, which is the belief under
 * test.
 */

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const store = new Map<string, string>();
store.set(
  "ql-session",
  JSON.stringify({
    state: {
      token: "qml-task-token",
      user: { id: 1, email: "a@b.dev", role: "student", display_name: "Task", is_active: true },
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

const read = (name: string) =>
  JSON.parse(readFileSync(fileURLToPath(new URL(`../test-fixtures/${name}`, import.meta.url)), "utf-8"));

const payloads = read("qml-task-payloads.json");
const describeFixture = read("qml-describe.json");

const { renderToString } = await import("react-dom/server");
const { createElement: h } = await import("react");
const { QueryClient, QueryClientProvider } = await import("@tanstack/react-query");
const { MemoryRouter } = await import("react-router-dom");
const { QmlTrainingDashboard } = await import("../src/components/qml/QmlTrainingDashboard.tsx");
const { QmlResultsPanel } = await import("../src/components/qml/QmlResultsPanel.tsx");
const { QmlConfigForm } = await import("../src/components/qml/QmlConfigForm.tsx");
const qmlApi = await import("../src/api/qml.ts");
const { nextConfigForAlgorithm } = await import("../src/components/qml/algorithmSwitch.ts");

/** React separates adjacent text nodes with an empty comment, so "0.0%"
 *  reaches the markup as `0.0<!-- -->%`. */
const text = (html: string) => html.replace(/<!-- -->/g, "");

let failures = 0;
function check(name: string, ok: boolean, extra = "") {
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${extra ? ` — ${extra}` : ""}`);
  if (!ok) failures += 1;
}

function render(node: unknown): string {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: Infinity } } });
  client.setQueryData(["features"], { qml_enabled: true });
  client.setQueryData(["qml", "describe"], describeFixture);
  return text(
    renderToString(
      h(QueryClientProvider, { client }, h(MemoryRouter, { initialEntries: ["/qml-lab"] }, node as never)) as never,
    ),
  );
}

const algorithmInfo = (name: string) =>
  describeFixture.algorithms.find((a: { name: string }) => a.name === name);

function dashboard(algorithm: string) {
  const detail = payloads[algorithm].detail;
  const info = algorithmInfo(algorithm);
  const result = detail.result;
  return render(
    h(QmlTrainingDashboard, {
      experimentId: 1,
      status: detail.status,
      history: detail.history,
      totalEpochs: detail.config.training.epochs,
      error: null,
      cached: false,
      onCancel: () => {},
      cancelling: false,
      cancelError: null,
      onViewResults: () => {},
      algorithm: info,
      kernel: result?.kernel,
    } as never),
  );
}

function results(algorithm: string) {
  const detail = payloads[algorithm].detail;
  return render(
    h(QmlResultsPanel, {
      result: detail.result,
      status: detail.status,
      error: null,
      inference: payloads[algorithm].inference,
      onRunInference: () => {},
      inferenceRunning: false,
      inferenceError: null,
    } as never),
  );
}

/* -------------------------------------------------------------------------- */
/* 0. The fixtures really do contain the two hostile shapes                    */
/* -------------------------------------------------------------------------- */

const regressionHistory = payloads.quantum_regression.detail.history;
const kernelHistory = payloads.quantum_kernel.detail.history;

check(
  "fixture: every regression epoch stores train_accuracy = null",
  regressionHistory.length > 0 &&
    regressionHistory.every((r: { train_accuracy: unknown }) => r.train_accuracy === null),
  `${regressionHistory.length} epochs`,
);
check(
  "fixture: every regression epoch stores a real train_r2",
  regressionHistory.every((r: { train_r2: unknown }) => typeof r.train_r2 === "number"),
  `first = ${regressionHistory[0]?.train_r2}`,
);
check(
  "fixture: the kernel run recorded zero epoch rows",
  Array.isArray(kernelHistory) && kernelHistory.length === 0,
  `${kernelHistory.length} rows`,
);

/* -------------------------------------------------------------------------- */
/* 1. A null accuracy is absent, not zero                                      */
/* -------------------------------------------------------------------------- */

const regressionDash = dashboard("quantum_regression");

check(
  "regression dashboard: renders no accuracy tile at all",
  !/Train acc|Test acc/i.test(regressionDash),
  "a tile headed 'Train acc' asserts the metric applies here",
);
check(
  "regression dashboard: never prints 0.0% for a null accuracy",
  !/\b0\.0%/.test(regressionDash),
  "null coerced to 0 renders as 0.0%",
);
check(
  "regression dashboard: no em-dash placeholder under an accuracy heading",
  !/Train acc[\s\S]{0,120}—/.test(regressionDash),
  "'—' still asserts the metric is meaningful and merely missing",
);
check(
  "regression dashboard: plots R\u00b2 instead",
  /R\u00b2/.test(regressionDash),
);
check(
  "regression dashboard: R\u00b2 renders with its sign",
  /[+-]\d+\.\d{3}/.test(regressionDash),
  (regressionDash.match(/[+-]\d+\.\d{3}/) ?? ["none"])[0],
);

// The series helper is the mechanism; assert it directly too, because a
// component can be right by accident while the helper is wrong.
const nulls = qmlApi.finiteSeries(regressionHistory, "train_accuracy");
const r2s = qmlApi.finiteSeries(regressionHistory, "train_r2");
check("finiteSeries: drops every null accuracy point", nulls.length === 0, `${nulls.length} points`);
check(
  "finiteSeries: keeps every real R\u00b2 point",
  r2s.length === regressionHistory.length,
  `${r2s.length}/${regressionHistory.length}`,
);
check(
  "finiteSeries: a null never becomes a zero",
  !nulls.some((p: { value: number }) => p.value === 0),
);

/* -------------------------------------------------------------------------- */
/* 2. A classification run still shows its accuracy                            */
/* -------------------------------------------------------------------------- */

const vqcDash = dashboard("vqc");
check(
  "vqc dashboard: still renders an accuracy tile",
  /Train acc/.test(vqcDash),
  "skipping nulls must not skip real values",
);
check("vqc dashboard: renders no R\u00b2", !/R\u00b2/.test(vqcDash));

/* -------------------------------------------------------------------------- */
/* 3. A kernel run with zero epochs renders its outcome                        */
/* -------------------------------------------------------------------------- */

const kernelDash = dashboard("quantum_kernel");

check(
  "kernel dashboard: names the closed-form solve",
  /closed[- ]form/i.test(kernelDash),
);
check(
  "kernel dashboard: reports the measured kernel cost",
  /Kernel evals/i.test(kernelDash) && /1,617|1617/.test(kernelDash),
);
check(
  "kernel dashboard: draws no empty chart axis",
  !/\bepoch\b[\s\S]{0,40}<\/text>/i.test(kernelDash) || !/<svg/.test(kernelDash),
  "an axis with no data implies the curve failed to load",
);
check(
  "kernel dashboard: does not spin on a completed run",
  !/animate-spin/.test(kernelDash),
  "a spinner on a terminal run implies work still in progress",
);
check(
  "kernel dashboard: states that no epochs is correct, not missing",
  /no epochs/i.test(kernelDash),
);

/* -------------------------------------------------------------------------- */
/* 4. Results: each task shows only its own metrics                            */
/* -------------------------------------------------------------------------- */

const regressionResults = results("quantum_regression");
const vqcResults = results("vqc");
const kernelResults = results("quantum_kernel");

for (const banned of ["Accuracy", "Precision", "Recall", "Confusion"]) {
  check(
    `regression results: no "${banned}" anywhere`,
    !new RegExp(banned, "i").test(regressionResults.replace(/R\u00b2/g, "")),
  );
}
check("regression results: shows MAE", /MAE/.test(regressionResults));
check("regression results: shows RMSE", /RMSE/.test(regressionResults));
check(
  "regression results: MAE is in target units, not a percentage",
  /MAE[\s\S]{0,160}?0\.\d{3}\s*y/.test(regressionResults),
  (regressionResults.match(/MAE[\s\S]{0,160}?0\.\d{3}\s*y/) ?? ["not found"])[0].slice(-24),
);
check(
  "regression results: R\u00b2 carries an explicit sign",
  /[+-]0\.\d{3}/.test(regressionResults),
);
check(
  "classification results: shows accuracy and a confusion matrix",
  /Accuracy/.test(vqcResults) && /Confusion matrix/.test(vqcResults),
);
check(
  "classification results: shows no regression metric",
  !/\bMAE\b/.test(vqcResults) && !/\bRMSE\b/.test(vqcResults),
);
check(
  "kernel results: renders the Gram heatmap and says it is symmetric",
  /kernel matrix/i.test(kernelResults) && /symmetric/i.test(kernelResults),
);
check(
  "kernel results: heatmap cells use inline styles, never an interpolated class",
  !/class="[^"]*bg-\w+\/\$\{/.test(kernelResults) && /opacity:/.test(kernelResults),
  "QL-001",
);

/* -------------------------------------------------------------------------- */
/* 5. Inference: three shapes, no borrowed field                               */
/* -------------------------------------------------------------------------- */

check(
  "regression inference: labels the column 'Predicted value'",
  /Predicted value/.test(regressionResults),
);
check(
  "regression inference: shows no probability bar",
  !/P\(class 1\)/.test(regressionResults),
  "a regression prediction is not a probability",
);
check(
  "regression inference: states the stored scaler was reused",
  /stored alongside the model|not refitted/i.test(regressionResults),
);
check(
  "kernel inference: calls the value a margin, not a probability",
  /Margin/.test(kernelResults) && !/P\(class 1\)/.test(kernelResults),
);
check(
  "kernel inference: says the margin is a signed distance",
  /signed distance/i.test(kernelResults),
);
check(
  "vqc inference: still shows P(class 1)",
  /P\(class 1\)/.test(vqcResults),
);

/* -------------------------------------------------------------------------- */
/* 6. Configuration form follows `supports`, not the algorithm's name          */
/* -------------------------------------------------------------------------- */

function form(algorithm: string) {
  const info = algorithmInfo(algorithm);
  const config = {
    ...qmlApi.DEFAULT_CONFIG,
    algorithm,
    dataset: { ...qmlApi.DEFAULT_CONFIG.dataset, name: info.datasets[0].name },
    circuit: {
      ...qmlApi.DEFAULT_CONFIG.circuit,
      ...(info.supports.n_hidden ? { n_hidden: 4 } : {}),
    },
  };
  return render(
    h(QmlConfigForm, {
      config,
      onChange: () => {},
      describe: describeFixture,
      describeError: null,
      onSubmit: () => {},
      submitting: false,
      submitError: null,
      disabled: false,
    } as never),
  );
}

const kernelForm = form("quantum_kernel");
const hybridForm = form("hybrid_qnn");
const regressionForm = form("quantum_regression");

check(
  "kernel form: offers no epoch field",
  !/id="qml-epochs"/.test(kernelForm),
  "supports.epochs === false",
);
check(
  "kernel form: offers no learning rate",
  !/id="qml-learning-rate"/.test(kernelForm),
);
check(
  "kernel form: explains why there are no epochs",
  /no training loop/i.test(kernelForm),
);
check("hybrid form: offers the hidden-units field", /id="qml-n-hidden"/.test(hybridForm));
check("vqc form: offers no hidden-units field", !/id="qml-n-hidden"/.test(form("vqc")));
check("regression form: offers an epoch field", /id="qml-epochs"/.test(regressionForm));
// Radix renders Select items in a portal, so the option list is NOT in the
// SSR markup -- asserting on it would assert on nothing. The real invariant
// is tested against the pure switch function below instead.
check(
  "regression form: shows the angle-frequency note its dataset carries",
  /angle frequency/i.test(regressionForm),
  "proves the form read the algorithm's own dataset metadata",
);

/* -------------------------------------------------------------------------- */
/* 7. Switching algorithm never strands an invalid pair                        */
/* -------------------------------------------------------------------------- */

const everyAlgorithm = describeFixture.algorithms as {
  name: string;
  datasets: { name: string }[];
  supports: { n_hidden: boolean };
  limits: Record<string, { min: number; max: number }>;
}[];

let stranded: string[] = [];
let strayHidden: string[] = [];
let overCap: string[] = [];
for (const from of everyAlgorithm) {
  for (const dataset of from.datasets) {
    for (const to of everyAlgorithm) {
      const start = {
        ...qmlApi.DEFAULT_CONFIG,
        algorithm: from.name,
        dataset: { ...qmlApi.DEFAULT_CONFIG.dataset, name: dataset.name, n_samples: 1000 },
        circuit: {
          ...qmlApi.DEFAULT_CONFIG.circuit,
          ...(from.supports.n_hidden ? { n_hidden: 4 } : {}),
        },
      };
      const next = nextConfigForAlgorithm(start as never, to as never);
      const label = `${from.name}/${dataset.name} -> ${to.name}`;
      if (!to.datasets.some((d) => d.name === next.dataset.name)) stranded.push(label);
      if (!to.supports.n_hidden && "n_hidden" in next.circuit) strayHidden.push(label);
      if (next.dataset.n_samples > (to.limits.n_samples?.max ?? Infinity)) overCap.push(label);
    }
  }
}

check(
  "algorithm switch: no transition strands an incompatible dataset",
  stranded.length === 0,
  `${everyAlgorithm.length * 3 * everyAlgorithm.length} transitions checked${stranded.length ? `: ${stranded.slice(0, 3).join(", ")}` : ""}`,
);
check(
  "algorithm switch: n_hidden is dropped for algorithms that forbid it",
  strayHidden.length === 0,
  strayHidden.slice(0, 3).join(", ") || "extra=forbid would 422",
);
check(
  "algorithm switch: sample count is clamped into the new ceiling",
  overCap.length === 0,
  overCap.slice(0, 3).join(", "),
);
check(
  "algorithm switch: a compatible dataset is preserved, not reset",
  nextConfigForAlgorithm(
    { ...qmlApi.DEFAULT_CONFIG, algorithm: "vqc", dataset: { ...qmlApi.DEFAULT_CONFIG.dataset, name: "circles" } } as never,
    everyAlgorithm.find((a) => a.name === "quantum_kernel") as never,
  ).dataset.name === "circles",
  "switching VQC -> kernel on circles must not move the user off their data",
);
check(
  "regression form: mentions data re-uploading",
  /re-uploading/i.test(regressionForm),
  "supports.data_reuploading",
);

console.log(`\n${failures === 0 ? "OK" : `${failures} FAILED`}`);
process.exit(failures === 0 ? 0 : 1);
