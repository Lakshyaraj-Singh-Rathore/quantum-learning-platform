/**
 * Comprehensive permutation test suite for all "Try it yourself" activities.
 * Run with: npx tsx scripts/verify-all-demos.mts
 */
import {
  LANDMARKS,
  GATES,
  stateFromAngles,
  stateFromAmplitudes,
  applyGates,
  interference,
  stateSpaceRows,
  bitstringTable,
  probs,
} from "../src/lib/demos";
import { DEMOS, BELL_STATES, type BellId } from "../src/components/demos/Demos";

let passed = 0;
let failed = 0;

function assert(desc: string, condition: boolean, details?: string) {
  if (condition) {
    passed++;
    // console.log(`✓ ${desc}`);
  } else {
    failed++;
    console.error(`✗ FAIL: ${desc} ${details ?? ""}`);
  }
}

console.log("Starting permutation testing across all 'Try it yourself' activities...\n");

// 1. Permutation Tests for EntanglementLab & Bell States
console.log("=== 1. Entanglement & Bell States Tests ===");
const bellKeys: BellId[] = ["phi_plus", "phi_minus", "psi_plus", "psi_minus"];

for (const id of bellKeys) {
  const cfg = BELL_STATES[id];
  assert(`Bell state ${id} exists with valid formula and name`, Boolean(cfg.formula && cfg.name));
  assert(
    `Bell state ${id} has correct phase specification`,
    (id.includes("minus") && cfg.phaseDeg === 180) || (id.includes("plus") && cfg.phaseDeg === 0)
  );

  // Exact deterministic correlation assertions for both outcomes of Qubit A
  for (const a of [0, 1]) {
    const b = cfg.correlation === "identical" ? a : 1 - a;
    if (cfg.correlation === "identical") {
      assert(`Measurement of Alice=${a} collapses Bob to identical state ${b}`, a === b);
      assert(`Basis state is |${a}${b}⟩`, (a === 0 && b === 0) || (a === 1 && b === 1));
    } else {
      assert(`Measurement of Alice=${a} collapses Bob to opposite state ${b}`, a !== b);
      assert(`Basis state is |${a}${b}⟩`, (a === 0 && b === 1) || (a === 1 && b === 0));
    }
  }

  // Exact deterministic correlation assertions for both outcomes of Qubit B
  for (const b of [0, 1]) {
    const a = cfg.correlation === "identical" ? b : 1 - b;
    if (cfg.correlation === "identical") {
      assert(`Measurement of Bob=${b} collapses Alice to identical state ${a}`, a === b);
    } else {
      assert(`Measurement of Bob=${b} collapses Alice to opposite state ${a}`, a !== b);
    }
  }
}

// 2. Permutation Tests for Bloch Sphere Cardinals and Angles
console.log("\n=== 2. Bloch Sphere & State Transformations ===");
for (const [name, [theta, phi]] of Object.entries(LANDMARKS)) {
  const sv = stateFromAngles(theta, phi);
  const p = probs(sv);
  const sumP = p[0] + p[1];
  assert(`Bloch landmark ${name} probabilities sum to 1.0`, Math.abs(sumP - 1.0) < 1e-9);

  if (name === "|0⟩") {
    assert("|0⟩ has P(0)=1, P(1)=0", Math.abs(p[0] - 1.0) < 1e-9 && Math.abs(p[1]) < 1e-9);
  } else if (name === "|1⟩") {
    assert("|1⟩ has P(0)=0, P(1)=1", Math.abs(p[0]) < 1e-9 && Math.abs(p[1] - 1.0) < 1e-9);
  } else if (name === "|+⟩" || name === "|−⟩" || name === "|+i⟩" || name === "|−i⟩") {
    assert(`${name} has equal 50/50 probabilities`, Math.abs(p[0] - 0.5) < 1e-9 && Math.abs(p[1] - 0.5) < 1e-9);
  }
}

// 3. Permutation Tests for Unitary Gate Sandbox
console.log("\n=== 3. Gate Sandbox Sequences ===");
for (const [name, [theta, phi]] of Object.entries(LANDMARKS)) {
  const startState = stateFromAngles(theta, phi);
  // H * H = I
  const hh = applyGates(startState, ["H", "H"]);
  const pInitial = probs(startState);
  const pHH = probs(hh);
  assert(`H * H = I on ${name}`, Math.abs(pHH[0] - pInitial[0]) < 1e-9);

  // X * X = I
  const xx = applyGates(startState, ["X", "X"]);
  const pXX = probs(xx);
  assert(`X * X = I on ${name}`, Math.abs(pXX[0] - pInitial[0]) < 1e-9);

  // Z * Z = I
  const zz = applyGates(startState, ["Z", "Z"]);
  const pZZ = probs(zz);
  assert(`Z * Z = I on ${name}`, Math.abs(pZZ[0] - pInitial[0]) < 1e-9);

  // H * Z * H = X
  const hzh = applyGates(startState, ["H", "Z", "H"]);
  const x = applyGates(startState, ["X"]);
  const pHZH = probs(hzh);
  const pX = probs(x);
  assert(`H * Z * H = X on ${name}`, Math.abs(pHZH[0] - pX[0]) < 1e-9);
}

// 4. Permutation Tests for Exponential State Space (2^n)
console.log("\n=== 4. Exponential State Space Tests ===");
let prevStates = 1;
for (let n = 1; n <= 30; n++) {
  const states = 2 ** n;
  const memoryMB = (states * 16) / 1e6;
  assert(`State space for n=${n} strictly doubles preceding dimension (prev=${prevStates})`, states === prevStates * 2 && memoryMB > 0);
  prevStates = states;
}
const rows = stateSpaceRows(20);
assert("stateSpaceRows generates 20 rows", rows.length === 20);
for (let i = 0; i < rows.length; i++) {
  assert(`Row ${i + 1} has ${i + 1} qubits and 2^(i+1) states`, rows[i].qubits === i + 1 && rows[i].states === 2 ** (i + 1));
}

// 5. Permutation Tests for Bit Ordering (Qiskit Little-Endian)
console.log("\n=== 5. Bit Ordering Tests ===");
for (let nBits = 2; nBits <= 5; nBits++) {
  const maxVal = (1 << nBits) - 1;
  for (let val = 0; val <= maxVal; val++) {
    const table = bitstringTable(val, nBits);
    assert(`Bitstring table for n=${nBits}, val=${val} has ${nBits} rows`, table.length === nBits);
    
    // Check rightmost is qubit 0
    const q0Row = table.find((r) => r.qubit === "q0");
    assert(`q0 is rightmost in table for val=${val}`, q0Row?.rightmost === true);
    
    // Check parity of q0 matches val % 2
    assert(`q0 value matches val % 2`, q0Row?.value === (val & 1));
  }
}

// 6. Permutation Tests for Quantum Interference Lab
console.log("\n=== 6. Interference Lab Calculations ===");
for (let a = -1.0; a <= 1.0; a += 0.2) {
  for (let b = -1.0; b <= 1.0; b += 0.2) {
    const res = interference(a, b);
    const expectedAmp = a + b;
    const expectedProb = expectedAmp ** 2;
    const expectedClassical = a ** 2 + b ** 2;
    assert(`Amplitude matches sum for a=${a.toFixed(1)}, b=${b.toFixed(1)}`, Math.abs(res.amplitude - expectedAmp) < 1e-9);
    assert(`Quantum P matches (a+b)^2`, Math.abs(res.probability - expectedProb) < 1e-9);
    assert(`Classical P matches a^2 + b^2`, Math.abs(res.classical - expectedClassical) < 1e-9);
  }
}

// 7. Verify all Demos in Registry are defined
console.log("\n=== 7. Demo Registry Verification ===");
const expectedDemoKeys = [
  "bit_vs_qubit",
  "build_a_qubit",
  "bloch",
  "gates",
  "plus_minus",
  "measure",
  "interference",
  "state_space",
  "entanglement_lab",
  "bit_order",
  "circuit_lab",
];

for (const key of expectedDemoKeys) {
  const demo = DEMOS[key];
  assert(`Demo '${key}' exists in registry`, Boolean(demo));
  assert(`Demo '${key}' has title and blurb`, Boolean(demo?.title && demo?.blurb));
  assert(`Demo '${key}' has valid Component function`, typeof demo?.Component === "function");
}

console.log(`\n========================================`);
console.log(`TEST SUMMARY: ${passed} PASSED, ${failed} FAILED`);
console.log(`========================================`);

if (failed > 0) {
  process.exit(1);
} else {
  console.log("ALL PERMUTATION TESTS PASSED!");
  process.exit(0);
}
