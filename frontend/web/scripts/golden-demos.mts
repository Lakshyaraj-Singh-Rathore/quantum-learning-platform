/* Checks src/lib/demos.ts against numpy, via test-fixtures/demo-golden.json.
 *
 *   npx tsx scripts/golden-demos.mts
 *   npm run golden:demos
 *
 * The fixture is produced by scripts/golden-demos.py, which calls the same
 * frontend/lib/playground.py the Streamlit demos call. So this is not checking
 * the port against itself: it is checking that every number a learner sees in
 * the React demos is the number they would have seen in Streamlit.
 */

import { readFileSync } from "node:fs";

import {
  applyGates,
  bitstringTable,
  interference,
  probs,
  stateFromAmplitudes,
  stateFromAngles,
  stateSpaceRows,
} from "../src/lib/demos";
import { blochAngles, blochVector, reducedDensityMatrix } from "../src/lib/quantum";

const fixture = JSON.parse(
  readFileSync(new URL("../test-fixtures/demo-golden.json", import.meta.url), "utf8"),
) as {
  stateFromAngles: { theta: number; phi: number; state: [number, number][]; probabilities: number[] }[];
  stateFromAmplitudes: { alpha: number; beta: number; state: [number, number][] }[];
  applyGates: {
    start: string;
    gates: string[];
    state: [number, number][];
    probabilities: number[];
    theta: number;
    phi: number;
  }[];
  interference: { a: number; b: number; amplitude: number; probability: number; classical: number }[];
  stateSpaceRows: { qubits: number; states: number; megabytes: number }[];
  bitstringTable: { value: number; n: number; rows: { qubit: string; value: number; position: string; rightmost: boolean }[] }[];
};

let comparisons = 0;
let failures = 0;

function close(name: string, got: number, expected: number, tol = 1e-9) {
  comparisons += 1;
  if (!Number.isFinite(got) && !Number.isFinite(expected)) return;
  if (Math.abs(got - expected) > tol) {
    failures += 1;
    console.log(`FAIL  ${name}: got ${got}, expected ${expected}`);
  }
}

function closeState(name: string, got: [number, number][], expected: [number, number][]) {
  for (let i = 0; i < expected.length; i += 1) {
    close(`${name}[${i}].re`, got[i][0], expected[i][0]);
    close(`${name}[${i}].im`, got[i][1], expected[i][1]);
  }
}

/** (theta, phi) out of the state, the same way the demos derive it. Both come
 *  back in degrees already; blochAngles wraps phi into [0, 360). */
function anglesOf(state: [number, number][]): [number, number] {
  const amps = state.map(([re, im]) => ({ re, im }));
  const [x, y, z] = blochVector(reducedDensityMatrix(amps, 1, 0));
  const { theta, phi } = blochAngles(x, y, z);
  return [theta, phi];
}

/** Angles are only defined up to a full turn, so 0 and 360 are the same point. */
function closeAngle(name: string, got: number, expected: number, tol = 1e-6) {
  comparisons += 1;
  if (Number.isNaN(got) || Number.isNaN(expected)) return;
  let difference = (got - expected) % 360;
  if (difference > 180) difference -= 360;
  if (difference < -180) difference += 360;
  if (Math.abs(difference) > tol) {
    failures += 1;
    console.log(`FAIL  ${name}: got ${got}, expected ${expected}`);
  }
}

for (const testCase of fixture.stateFromAngles) {
  const state = stateFromAngles(testCase.theta, testCase.phi);
  closeState(
    `stateFromAngles(${testCase.theta}, ${testCase.phi})`,
    state,
    testCase.state,
  );
  const [p0, p1] = probs(state);
  close(`stateFromAngles(${testCase.theta}, ${testCase.phi}) P(0)`, p0, testCase.probabilities[0]);
  close(`stateFromAngles(${testCase.theta}, ${testCase.phi}) P(1)`, p1, testCase.probabilities[1]);
}

for (const testCase of fixture.stateFromAmplitudes) {
  closeState(
    `stateFromAmplitudes(${testCase.alpha}, ${testCase.beta})`,
    stateFromAmplitudes(testCase.alpha, testCase.beta),
    testCase.state,
  );
}

for (const testCase of fixture.applyGates) {
  const label = `applyGates(${testCase.start}, [${testCase.gates.join(",")}])`;
  const state = applyGates(stateFromAngles(...(landmarkOf(testCase.start) as [number, number])), testCase.gates);
  closeState(label, state, testCase.state);
  const [p0, p1] = probs(state);
  close(`${label} P(0)`, p0, testCase.probabilities[0]);
  close(`${label} P(1)`, p1, testCase.probabilities[1]);
  const [theta, phi] = anglesOf(state);
  // At a pole (P(0) = 0 or 1) the Bloch vector sits on the z axis and phi is
  // genuinely arbitrary: numpy and the port wrap it differently and neither is
  // wrong. Skip phi there, but keep comparing P(0), P(1) and theta.
  const atPole =
    testCase.probabilities[0] < 1e-12 || testCase.probabilities[0] > 1 - 1e-12;
  if (atPole) continue;
  closeAngle(`${label} theta`, theta, testCase.theta);
  closeAngle(`${label} phi`, phi, testCase.phi);
}

for (const testCase of fixture.interference) {
  const got = interference(testCase.a, testCase.b);
  close(`interference(${testCase.a}, ${testCase.b}).amplitude`, got.amplitude, testCase.amplitude);
  close(`interference(${testCase.a}, ${testCase.b}).probability`, got.probability, testCase.probability);
  close(`interference(${testCase.a}, ${testCase.b}).classical`, got.classical, testCase.classical);
}

const rows = stateSpaceRows(20);
for (let i = 0; i < fixture.stateSpaceRows.length; i += 1) {
  const expected = fixture.stateSpaceRows[i];
  close(`stateSpaceRows[${i}].qubits`, rows[i].qubits, expected.qubits);
  close(`stateSpaceRows[${i}].states`, rows[i].states, expected.states);
  close(`stateSpaceRows[${i}].megabytes`, rows[i].megabytes, expected.megabytes);
}

for (const testCase of fixture.bitstringTable) {
  const got = bitstringTable(testCase.value, testCase.n);
  close(`bitstringTable(${testCase.value}, ${testCase.n}).length`, got.length, testCase.rows.length);
  testCase.rows.forEach((expected, i) => {
    close(`bitstringTable[${i}].qubit`, Number(got[i].qubit.slice(1)), Number(expected.qubit.slice(1)));
    close(`bitstringTable[${i}].value`, got[i].value, expected.value);
    comparisons += 1;
    if (got[i].position !== expected.position) {
      failures += 1;
      console.log(`FAIL  bitstringTable[${i}].position: got ${got[i].position}, expected ${expected.position}`);
    }
    comparisons += 1;
    if (got[i].rightmost !== expected.rightmost) {
      failures += 1;
      console.log(`FAIL  bitstringTable[${i}].rightmost: got ${got[i].rightmost}, expected ${expected.rightmost}`);
    }
  });
}

/** The six cardinal states, matching playground.LANDMARKS. */
function landmarkOf(name: string): readonly [number, number] {
  const LANDMARKS: Record<string, [number, number]> = {
    "|0⟩": [0, 0],
    "|1⟩": [180, 0],
    "|+⟩": [90, 0],
    "|−⟩": [90, 180],
    "|+i⟩": [90, 90],
    "|−i⟩": [90, 270],
  };
  const found = LANDMARKS[name];
  if (!found) throw new Error(`unknown landmark ${name}`);
  return found;
}

console.log(
  failures === 0
    ? `ALL CHECKS PASSED — ${comparisons} demo values agree with numpy (1e-9)`
    : `${failures} of ${comparisons} DEMO VALUES DISAGREE`,
);
process.exit(failures === 0 ? 0 : 1);
