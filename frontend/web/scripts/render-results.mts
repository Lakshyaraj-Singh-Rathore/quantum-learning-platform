/* Renders every result view against REAL engine output.
 *
 * The fixtures in test-fixtures/engine-results.json were produced by
 * scripts/engine-fixtures.py calling the same qiskit_aer.run() the Celery
 * worker calls — not hand-written numbers. So this checks that the views
 * actually draw what the simulator returned: the right bitstrings, the right
 * gauge values, the right refusals.
 *
 *   npx tsx scripts/render-results.mts
 */
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { renderToString } from "react-dom/server";
import { createElement } from "react";
import type { RunResult } from "../src/api/jobs.ts";
import { makeOp } from "../../circuit_composer/frontend/src/ir.ts";
import type { CircuitIR } from "../../circuit_composer/frontend/src/types.ts";
import { PhaseDisk, QSphere } from "../src/components/results/GeometryViews.tsx";
import { CircuitDiagram } from "../src/components/results/CircuitDiagram.tsx";
import {
  BlochView,
  BornVsShots,
  DensityMatrix,
  Histogram,
  IdealVsNoisy,
  MetricGauges,
  ProbabilityTable,
  ResultSummary,
  StatevectorTable,
} from "../src/components/results/ResultsViews.tsx";

const fixturePath = fileURLToPath(new URL("../test-fixtures/engine-results.json", import.meta.url));
const cases = JSON.parse(readFileSync(fixturePath, "utf-8")) as Record<string, RunResult>;

let failures = 0;
function check(name: string, ok: boolean, extra = "") {
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${extra ? ` — ${extra}` : ""}`);
  if (!ok) failures += 1;
}

/** renderToString separates adjacent text nodes with "<!-- -->", so a value
 *  rendered as `{x}%` comes back as "5.6<!-- -->%". Stripping the markers
 *  makes the assertions read like the text a person sees. */
const render = (node: React.ReactElement) => renderToString(node).replaceAll("<!-- -->", "");
const bell = cases.bell;
const ghz3 = cases.ghz3;
const noisy = cases.bell_noisy;

// ---------------------------------------------------------------- summary
{
  const html = render(createElement(ResultSummary, { result: bell }));
  check("summary names the engine", html.includes("qiskit_aer"));
  check("summary shows shots, qubits and runtime", html.includes("1024") && html.includes("2"));
  check("summary states the bit order", html.includes("qubit 0 = rightmost"));
}

// ----------------------------------------------------------------- gauges
{
  const html = render(createElement(MetricGauges, { result: bell }));
  check("entanglement gauge renders for a Bell state", html.includes("Entanglement S"));
  check("a maximally entangled pair is labelled ENTANGLED", html.includes("ENTANGLED"));
  check("concurrence is shown to two decimals", html.includes("C=1.00"), "C=1.00");
  check("fidelity and purity gauges render when the backend reports them", html.includes("Fidelity") && html.includes("Purity"));
  check("a noiseless run says so on the fidelity gauge", html.includes("no noise applied"));

  const noisyHtml = render(createElement(MetricGauges, { result: noisy }));
  check("a noisy run labels fidelity against the ideal state", noisyHtml.includes("F(ideal, noisy rho)"));
  check("TV distance is shown for noisy runs", noisyHtml.includes("TV distance") && noisyHtml.includes("0.060"));
  check("shot leakage is shown as a percentage", noisyHtml.includes("Shot leakage") && noisyHtml.includes("5.6%"));

  // The CUDA-Q honesty rule: that backend reports no fidelity or purity, and
  // the page must omit those gauges rather than invent a number for them.
  const cudaqLike: RunResult = {
    ...bell,
    metadata: {
      ...bell.metadata,
      metrics: { entanglement_entropy: 1.0, concurrence: 1.0, entangled: true },
    },
  };
  const cudaqHtml = render(createElement(MetricGauges, { result: cudaqLike }));
  check(
    "a backend with no fidelity/purity gets no such gauges (CUDA-Q rule)",
    !cudaqHtml.includes("Fidelity") && !cudaqHtml.includes("Purity") && cudaqHtml.includes("Entanglement S"),
  );

  const noMetrics: RunResult = { ...bell, metadata: { ...bell.metadata, metrics: undefined } };
  check(
    "no metrics at all renders nothing rather than empty dials",
    render(createElement(MetricGauges, { result: noMetrics })) === "",
  );
}

// -------------------------------------------------------------- histogram
{
  const html = render(createElement(Histogram, { result: bell }));
  check("histogram shows the measured bitstrings", html.includes("00") && html.includes("11"));
  check("histogram offers the probability toggle", html.includes("Show probability instead of counts"));
  check("histogram offers the phase-colour toggle", html.includes("Colour bars by relative phase"));
  check("histogram does not claim truncation for 2 outcomes", !html.includes("most frequent of"));
}

// ----------------------------------------------------------------- tables
{
  const html = render(createElement(ProbabilityTable, { result: bell }));
  const total = Object.values(bell.counts).reduce((a, b) => a + b, 0);
  const expected = ((bell.counts["00"] / total) * 100).toFixed(3);
  check("probability table computes percentages from real counts", html.includes(`${expected}%`), `${expected}%`);

  const stateHtml = render(createElement(StatevectorTable, { result: bell }));
  check("statevector view writes the state in ket notation", stateHtml.includes("|ψ⟩ ="));
  check("statevector view lists both amplitudes", stateHtml.includes("|00⟩") && stateHtml.includes("|11⟩"));
  check("statevector view explains relative phase", stateHtml.includes("relative") && stateHtml.includes("global phase"));

  const noStatevector: RunResult = { ...bell, statevector: null };
  check(
    "without a statevector the view says why",
    render(createElement(StatevectorTable, { result: noStatevector })).includes("needs a statevector"),
  );
}

// ------------------------------------------------------------ comparisons
{
  const html = render(createElement(BornVsShots, { result: bell }));
  check("born-vs-shots compares exact and sampled", html.includes("exact |psi|²") && html.includes("1024 shots"));
  check("born-vs-shots explains the gap is sampling error", html.includes("sampling error"));

  const noIdeal = render(createElement(IdealVsNoisy, { result: bell }));
  check(
    "ideal-vs-noisy explains how to get a comparison when there is none",
    noIdeal.includes("Enable the noise model"),
  );

  const withIdeal = render(createElement(IdealVsNoisy, { result: noisy }));
  check("ideal-vs-noisy draws both series when ideal counts exist", withIdeal.includes("Ideal") && withIdeal.includes("Noisy"));
  check("ideal-vs-noisy shows the difference chart", withIdeal.includes("Noisy minus ideal"));
}

// ------------------------------------------------------- density & bloch
{
  const html = render(createElement(DensityMatrix, { result: ghz3 }));
  check("density matrix renders for 3 qubits", html.includes("Ideal |rho|"));
  check("density matrix explains the off-diagonal corners", html.includes("entanglement"));

  const tooBig: RunResult = {
    ...ghz3,
    statevector: Array.from({ length: 128 }, () => [Math.SQRT1_2 / 8, 0] as [number, number]),
  };
  check(
    "density matrix refuses more than 5 qubits with the reason",
    render(createElement(DensityMatrix, { result: tooBig })).includes("limited to 5 qubits"),
  );

  const bloch = render(createElement(BlochView, { result: bell }));
  check("bloch view lists one row per qubit", bloch.includes("q0") && bloch.includes("q1"));
  check(
    "bloch view reports a maximally mixed qubit as |r| ~ 0",
    bloch.includes("|r| = 0.000"),
    bloch.match(/\|r\| = [\d.]+/)?.[0] ?? "(not found)",
  );

  const noSv: RunResult = { ...bell, statevector: null };
  check(
    "bloch view says it needs a statevector",
    render(createElement(BlochView, { result: noSv })).includes("needs a statevector"),
  );
}

// ------------------------------------------- phase disk, Q-sphere, diagram
{
  const noSv: RunResult = { ...bell, statevector: null };

  const disk = render(createElement(PhaseDisk, { result: bell }));
  check("phase disk labels each basis state", disk.includes("|00⟩") && disk.includes("|11⟩"));
  check("phase disk explains the per-state rings", disk.includes("own ring"));
  // A Bell pair shares one phase: without per-state rings the two markers
  // would land on the same point, which is the bug this design fixes.
  check(
    "phase disk draws one ring per populated state",
    (disk.match(/<circle[^>]*fill="none"/g) ?? []).length >= 2,
  );
  check(
    "phase disk says why it is unavailable without a statevector",
    render(createElement(PhaseDisk, { result: noSv })).includes("no statevector"),
  );

  const sphere = render(createElement(QSphere, { result: ghz3 }));
  check("Q-sphere shows the Hamming-weight poles", sphere.includes("|000⟩") && sphere.includes("|111⟩"));
  check("Q-sphere explains latitude and phase", sphere.includes("Latitude is Hamming weight"));
  check("Q-sphere warns it is not a Bloch sphere", sphere.includes("cannot show a mixed state"));
  check(
    "Q-sphere says why it is unavailable without a statevector",
    render(createElement(QSphere, { result: noSv })).includes("Q-sphere unavailable"),
  );
}

{
  const bellIr: CircuitIR = {
    name: "bell",
    n_qubits: 2,
    n_clbits: 2,
    ops: [
      makeOp("gate", { gate: "h", qubits: [0], layer: 0 }),
      makeOp("gate", { gate: "x", qubits: [1], controls: [0], layer: 1 }),
      makeOp("measure", { qubits: [0], clbits: [0], layer: 2 }),
      makeOp("measure", { qubits: [1], clbits: [1], layer: 2 }),
    ],
  };
  const html = render(createElement(CircuitDiagram, { ir: bellIr }));
  check("diagram draws one wire per qubit", html.includes("q[0]") && html.includes("q[1]"));
  check("diagram labels the gates", html.includes("H"));
  check("diagram marks measurements", html.includes("M"));
  check(
    "diagram draws a controlled-X target as a ring, not an X box",
    html.includes('r="14"'),
  );
  check(
    "diagram uses the app tokens rather than a hardcoded light palette",
    html.includes("var(--ink-3)") && !html.includes("#2D3436"),
  );

  const empty: CircuitIR = { name: "empty", n_qubits: 2, n_clbits: 2, ops: [] };
  check(
    "an empty circuit says so instead of drawing nothing",
    render(createElement(CircuitDiagram, { ir: empty })).includes("Circuit is empty"),
  );
}

console.log(failures === 0 ? "\nALL CHECKS PASSED" : `\n${failures} CHECK(S) FAILED`);
process.exit(failures === 0 ? 0 : 1);
