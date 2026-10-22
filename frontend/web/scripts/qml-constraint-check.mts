/**
 * One guard for a defect class, rather than two patches for two instances.
 *
 * QL-018 and QL-019 are the same bug seen from opposite sides: the config
 * form's HTML constraint attributes disagreeing with the limits
 * `/qml/describe` publishes.
 *
 *   QL-018  step=50 with min=20 made the API's own default of 200 INVALID,
 *           so the browser refused to submit and the feature was unusable.
 *   QL-019  a stale max=1000 let an over-cap value read as VALID, so
 *           checkValidity() disagreed with what the server would accept.
 *
 * Both are "the attribute does not track the published limit". This asserts
 * the property directly, over every algorithm and every dataset, instead of
 * pinning the two values that happened to break.
 *
 * Rendered server-side on purpose. SSR emits input attributes faithfully, so
 * the whole matrix can be swept deterministically and fast. The one thing SSR
 * cannot do is EVALUATE validity -- `step` and `max` are only enforced by a
 * real browser -- so qml-browser-metrics.mts keeps a checkValidity() assertion
 * for that. The two are complementary, not redundant.
 *
 *   npx tsx scripts/qml-constraint-check.mts
 */
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const describeFixture = JSON.parse(
  readFileSync(fileURLToPath(new URL("../test-fixtures/qml-describe.json", import.meta.url)), "utf-8"),
);

const { renderToString } = await import("react-dom/server");
const { createElement: h } = await import("react");
const { QueryClient, QueryClientProvider } = await import("@tanstack/react-query");
const { MemoryRouter } = await import("react-router-dom");
const { QmlConfigForm } = await import("../src/components/qml/QmlConfigForm.tsx");

let failures = 0;
function check(ok: boolean, name: string, extra = "") {
  if (!ok) failures += 1;
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${extra ? ` — ${extra}` : ""}`);
}

type Limit = { default: number; min: number; max: number };
type Dataset = { name: string; max_samples: number; n_features: number };
type Algorithm = {
  name: string;
  limits?: Record<string, Limit>;
  datasets: Dataset[];
};

const algorithms: Algorithm[] = describeFixture.algorithms ?? [];
check(algorithms.length === 4, "the fixture covers all four algorithms", algorithms.map((a) => a.name).join(", "));

/** Mount the real form for one algorithm/dataset pair and read its markup. */
function renderForm(algorithm: Algorithm, dataset: Dataset): string {
  const limits = algorithm.limits ?? describeFixture.limits;
  const config = {
    algorithm: algorithm.name,
    dataset: {
      name: dataset.name,
      n_samples: limits.n_samples?.default ?? 200,
      noise: 0.1,
      test_fraction: 0.3,
    },
    circuit: {
      n_qubits: Math.max(dataset.n_features, limits.n_qubits?.default ?? 2),
      n_layers: limits.n_layers?.default ?? 2,
      rotation: "Y",
      entanglement: "ring",
    },
    training: {
      epochs: limits.epochs?.default ?? 10,
      batch_size: limits.batch_size?.default ?? 16,
      learning_rate: 0.05,
      diff_method: "backprop",
    },
    seed: 7,
  };
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return renderToString(
    h(
      QueryClientProvider,
      { client },
      h(
        MemoryRouter,
        { initialEntries: ["/qml-lab"] },
        h(QmlConfigForm as never, {
          config,
          onChange: () => {},
          describe: describeFixture,
          describeError: null,
          onSubmit: () => {},
          submitting: false,
          submitError: null,
          disabled: false,
        }) as never,
      ),
    ) as never,
  );
}

/** Pull min/max/step off one input by id, from rendered markup. */
function attrs(html: string, id: string): { min?: string; max?: string; step?: string } | null {
  const tag = html.match(new RegExp(`<input[^>]*id="${id}"[^>]*>`));
  if (!tag) return null;
  const read = (name: string) => tag[0].match(new RegExp(`${name}="([^"]*)"`))?.[1];
  return { min: read("min"), max: read("max"), step: read("step") };
}

/* ---- the matrix ------------------------------------------------------- */

let pairs = 0;
let capPairs = 0;

for (const algorithm of algorithms) {
  const limits = algorithm.limits ?? describeFixture.limits;

  for (const dataset of algorithm.datasets ?? []) {
    pairs += 1;
    const html = renderForm(algorithm, dataset);
    const label = `${algorithm.name}/${dataset.name}`;

    // --- n_samples: the bound is the TIGHTER of the global limit and the
    //     dataset's own cap. This is the QL-019 property.
    const published = limits.n_samples as Limit | undefined;
    const effective = Math.min(dataset.max_samples, published?.max ?? dataset.max_samples);
    const a = attrs(html, "qml-n-samples");
    check(a !== null, `${label}: the samples field renders`);
    if (a) {
      check(
        a.max === String(effective),
        `${label}: samples max tracks the effective cap`,
        `max=${a.max} expected=${effective} (global ${published?.max}, dataset ${dataset.max_samples})`,
      );
      check(
        a.min === String(published?.min),
        `${label}: samples min tracks the published minimum`,
        `min=${a.min} expected=${published?.min}`,
      );
      // QL-018: a step that does not divide the range makes published
      // defaults invalid. No step at all is the correct state here.
      const stepOk =
        a.step === undefined ||
        a.step === "1" ||
        a.step === "any" ||
        ((published?.default ?? 0) - (published?.min ?? 0)) % Number(a.step) === 0;
      check(stepOk, `${label}: samples step cannot invalidate the published default`, `step=${a.step}`);
      if (dataset.max_samples < (published?.max ?? Infinity)) capPairs += 1;
    }

    // --- the circuit and training fields track their published limits too.
    for (const [id, key] of [
      ["qml-n-qubits", "n_qubits"],
      ["qml-n-layers", "n_layers"],
      ["qml-epochs", "epochs"],
      ["qml-batch-size", "batch_size"],
    ] as const) {
      const lim = limits[key] as Limit | undefined;
      const got = attrs(html, id);
      if (!lim || !got) continue;
      check(
        got.min === String(lim.min) && got.max === String(lim.max),
        `${label}: ${key} min/max track the published limit`,
        `min=${got.min} max=${got.max} expected ${lim.min}/${lim.max}`,
      );
      const stepOk =
        got.step === undefined ||
        got.step === "1" ||
        got.step === "any" ||
        (lim.default - lim.min) % Number(got.step) === 0;
      check(stepOk, `${label}: ${key} step cannot invalidate the published default`, `step=${got.step}`);
    }
  }
}

// A sweep that never meets a tightened cap would pass on a form that ignores
// max_samples entirely, so prove the matrix actually exercised the case.
check(
  capPairs > 0,
  "the sweep includes at least one dataset whose cap is tighter than the global max",
  `${capPairs} such pair(s) of ${pairs}`,
);

console.log(
  failures === 0
    ? `\nAll constraint-attribute checks passed over ${pairs} algorithm/dataset pair(s).`
    : `\n${failures} constraint check(s) FAILED.`,
);
if (failures > 0) process.exitCode = 1;
