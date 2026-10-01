/* Checks src/lib/grover.ts against numpy, via test-fixtures/grover-golden.json.
 *
 *   npx tsx scripts/golden-grover.mts
 *   npm run golden:grover
 *
 * The fixture is produced by scripts/golden-grover.py, which calls the same
 * frontend/lib/grover_lab.py the Streamlit Grover lab calls. So this is not
 * the port checking itself: it is a check that the React module shows the same
 * probabilities a learner would have seen in Streamlit.
 *
 * Two things the module is built around are asserted explicitly: the closed
 * form agrees with the simulation, and overshooting the optimum makes the
 * probability FALL. That second one is the whole point of letting the learner
 * drag the iteration slider past the optimum.
 *
 * `measure` is not pinned: it draws from numpy's PCG64, which JavaScript
 * cannot reproduce.
 */

import { readFileSync } from "node:fs";

import {
  analyticProbability,
  classicalAttempts,
  label,
  optimalIterations,
  parsePassword,
  run,
} from "../src/lib/grover";

const fixture = JSON.parse(
  readFileSync(new URL("../test-fixtures/grover-golden.json", import.meta.url), "utf8"),
) as {
  optimalIterations: { n_qubits: number; value: number }[];
  run: {
    n_qubits: number;
    target: number;
    iterations: number;
    frames: {
      iteration: number;
      stage: string;
      target_probability: number;
      probabilities: number[];
      amplitudes: [number, number][];
    }[];
  }[];
  analytic: { n_qubits: number; iteration: number; value: number }[];
  parsePassword: { text: string; n_qubits: number; target: number | null; error: string }[];
  classicalAttempts: {
    n_qubits: number;
    target: number;
    checked_to_find: number;
    worst_case: number;
    average_case: number;
  }[];
  label: { index: number; n_qubits: number; value: string }[];
};

let comparisons = 0;
let failures = 0;

function close(name: string, got: number, expected: number, tol = 1e-9) {
  comparisons += 1;
  if (Math.abs(got - expected) > tol) {
    failures += 1;
    console.log(`FAIL  ${name}: got ${got}, expected ${expected}`);
  }
}

for (const testCase of fixture.optimalIterations) {
  close(
    `optimalIterations(${testCase.n_qubits})`,
    optimalIterations(testCase.n_qubits),
    testCase.value,
  );
}

for (const testCase of fixture.run) {
  const frames = run(testCase.n_qubits, testCase.target, testCase.iterations);
  for (const expected of testCase.frames) {
    const got = frames[expected.iteration];
    close(`run(${testCase.n_qubits},${testCase.target})[${expected.iteration}].target`, got.targetProbability, expected.target_probability);
    for (let index = 0; index < expected.probabilities.length; index += 1) {
      close(
        `run(${testCase.n_qubits},${testCase.target})[${expected.iteration}].p[${index}]`,
        got.probabilities[index],
        expected.probabilities[index],
      );
      close(
        `run(${testCase.n_qubits},${testCase.target})[${expected.iteration}].amp[${index}].re`,
        got.amplitudes[index].re,
        expected.amplitudes[index][0],
      );
      close(
        `run(${testCase.n_qubits},${testCase.target})[${expected.iteration}].amp[${index}].im`,
        got.amplitudes[index].im,
        expected.amplitudes[index][1],
      );
    }
  }
}

for (const testCase of fixture.analytic) {
  close(
    `analyticProbability(${testCase.n_qubits}, ${testCase.iteration})`,
    analyticProbability(testCase.n_qubits, testCase.iteration),
    testCase.value,
  );
}

for (const testCase of fixture.parsePassword) {
  const got = parsePassword(testCase.text, testCase.n_qubits);
  comparisons += 1;
  if (got.target !== testCase.target) {
    failures += 1;
    console.log(`FAIL  parsePassword("${testCase.text}") target: got ${got.target}, expected ${testCase.target}`);
  }
  comparisons += 1;
  if (got.error !== testCase.error) {
    failures += 1;
    console.log(`FAIL  parsePassword("${testCase.text}") error: got "${got.error}", expected "${testCase.error}"`);
  }
}

for (const testCase of fixture.classicalAttempts) {
  const got = classicalAttempts(testCase.n_qubits, testCase.target);
  close(`classicalAttempts(${testCase.n_qubits},${testCase.target}).checkedToFind`, got.checkedToFind, testCase.checked_to_find);
  close(`classicalAttempts(${testCase.n_qubits},${testCase.target}).worstCase`, got.worstCase, testCase.worst_case);
  close(`classicalAttempts(${testCase.n_qubits},${testCase.target}).averageCase`, got.averageCase, testCase.average_case);
}

for (const testCase of fixture.label) {
  comparisons += 1;
  const got = label(testCase.index, testCase.n_qubits);
  if (got !== testCase.value) {
    failures += 1;
    console.log(`FAIL  label(${testCase.index}, ${testCase.n_qubits}): got ${got}, expected ${testCase.value}`);
  }
}

/* ---------- the two properties the module is actually about ---------- */

// The closed form must agree with the simulation.
let analyticDrift = 0;
for (const testCase of fixture.run) {
  for (const frame of testCase.frames) {
    if (frame.stage !== "amplified") continue;
    const closed = analyticProbability(testCase.n_qubits, frame.iteration);
    analyticDrift = Math.max(analyticDrift, Math.abs(closed - frame.target_probability));
  }
}
comparisons += 1;
if (analyticDrift > 1e-9) {
  failures += 1;
  console.log(`FAIL  closed form drifted from the simulation by ${analyticDrift}`);
}

// Overshooting the optimum must make the probability FALL. This is the
// 1/64 -> 99.66% -> back down story.
const six = fixture.run.find((entry) => entry.n_qubits === 6);
const optimal = fixture.optimalIterations.find((entry) => entry.n_qubits === 6)?.value ?? 0;
if (six && six.frames.length > optimal + 1) {
  const peak = six.frames[optimal].target_probability;
  const after = six.frames[six.frames.length - 1].target_probability;
  comparisons += 1;
  if (!(peak > 0.99 && after < 0.01)) {
    failures += 1;
    console.log(`FAIL  over-rotation: peak ${peak} then ${after}`);
  }
}

console.log(
  failures === 0
    ? `ALL CHECKS PASSED — ${comparisons} Grover values agree with numpy (1e-9)`
    : `${failures} of ${comparisons} GROVER VALUES DISAGREE`,
);
process.exit(failures === 0 ? 0 : 1);
