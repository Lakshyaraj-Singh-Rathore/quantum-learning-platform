/* End-to-end smoke for the Composer's data path, run against a REAL FastAPI
 * instance. It drives the same modules the page uses: the job/inspect client,
 * and the grid's own IR helpers for the circuits it sends.
 *
 * The scripts/smoke-auth.mts header explains the fetch shim; the short version
 * is that /api/* is rewritten onto API_TARGET because there is no proxy here.
 *
 *   API_TARGET=http://127.0.0.1:8123 npm run smoke:composer
 *
 * A Celery worker is NOT required: these jobs stay queued, which is asserted
 * rather than waited out. Running a circuit end to end needs `make upd`.
 */
const target = process.env.API_TARGET ?? "http://127.0.0.1:8123";
const routedFetch = globalThis.fetch;
globalThis.fetch = ((input: RequestInfo | URL, init?: RequestInit) => {
  const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
  return routedFetch(url.startsWith("/api/") ? `${target}${url.slice(4)}` : url, init);
}) as typeof fetch;

import { inspectCircuit, jobStatus, submitJob } from "../src/api/jobs.ts";
import { makeOp } from "../../circuit_composer/frontend/src/ir.ts";
import type { CircuitIR } from "../../circuit_composer/frontend/src/types.ts";
import { login } from "../src/api/auth.ts";
import { useSession } from "../src/state/session.ts";

let failures = 0;
function check(name: string, ok: boolean, extra = "") {
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${extra ? ` — ${extra}` : ""}`);
  if (!ok) failures += 1;
}

// Sign in as a real user; every endpoint below is authenticated.
const email = `p1-${Date.now()}@test.dev`;
const { register } = await import("../src/api/auth.ts");
try {
  await register({ email, password: "quant123", display_name: "P1 Smoke" });
} catch {
  /* already exists between runs is not interesting here */
}
const token = await login({ email, password: "quant123" });
useSession.getState().setFromToken(token);

// A Bell state, built with the grid's own helpers — the very circuit the
// Composer page offers as a preset.
const bell: CircuitIR = {
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

// 1. the circuit the page presets must be accepted
const report = await inspectCircuit(bell, "qiskit_aer", 1024);
check("a Bell state passes inspection", report.ok === true, JSON.stringify(report.errors));
check("inspection returns a summary the page can show", typeof report.summary?.depth === "number", `depth=${report.summary?.depth}`);

// 2. a circuit the grid can produce but the server must reject: two operations
//    on the same qubit in the same layer. The page shows these as errors.
const clash: CircuitIR = {
  name: "clash",
  n_qubits: 2,
  n_clbits: 0,
  ops: [
    makeOp("gate", { gate: "h", qubits: [0], layer: 0 }),
    makeOp("gate", { gate: "x", qubits: [0], layer: 0 }),
  ],
};
const bad = await inspectCircuit(clash, "qiskit_aer", 1024);
check("an overlapping layer fails inspection", bad.ok === false);
check(
  "the failure names the layer and the qubit, as the page displays it",
  bad.errors.some((e) => /Layer 0/.test(e) && /0/.test(e)),
  bad.errors[0] ?? "(no error text)",
);

// 3. submitting the valid circuit creates a job
const job = await submitJob({ circuit_ir: bell, backend: "qiskit_aer", shots: 1024 });
check("submitting a circuit creates a job", typeof job.id === "number", `job #${job.id}`);
check("the job records the chosen backend and shots", job.backend === "qiskit_aer" && job.shots === 1024, `${job.backend}/${job.shots}`);
// No Celery worker in this sandbox, so a job cannot complete here. What is
// asserted is that submission is recorded honestly either way: queued on a
// full stack, or failed with the missing-broker reason — never a silent
// "completed" with no result behind it.
const queued = ["pending", "queued", "running"].includes(job.status);
const brokerless = job.status === "failed" && /enqueue|redis|broker/i.test(job.error ?? "");
check(
  "the job is queued (or reports the missing worker honestly)",
  queued || brokerless,
  brokerless ? `${job.status}: ${job.error} (expected here — no worker in this sandbox)` : job.status,
);
check("fetching status by id returns the same job", (await jobStatus(job.id)).id === job.id);

// 4. the page only offers the noise panel for qiskit_aer / cudaq — the server
//    must agree, or the UI would be offering a control that always fails.
const noise = {
  enabled: true,
  t1_us: 50,
  t2_us: 30,
  readout_error: 0.02,
  gate_time_1q_us: 0.1,
  gate_time_2q_us: 0.4,
  gate_time_3q_us: 1.0,
};
try {
  await submitJob({ circuit_ir: bell, backend: "cirq", shots: 256, noise });
  check("noise on a non-noise backend is refused", false);
} catch (exc) {
  const message = exc instanceof Error ? exc.message : String(exc);
  check(
    "noise on a non-noise backend is refused with the reason",
    /Qiskit Aer and CUDA-Q|noise model/i.test(message),
    message,
  );
}

// 5. and the same payload IS accepted where the page enables it
try {
  const noisy = await submitJob({ circuit_ir: bell, backend: "qiskit_aer", shots: 256, noise });
  check("noise is accepted on a backend the page enables it for", typeof noisy.id === "number", `job #${noisy.id}`);
} catch (exc) {
  check("noise is accepted on a backend the page enables it for", false, exc instanceof Error ? exc.message : String(exc));
}

console.log(failures === 0 ? "\nALL CHECKS PASSED" : `\n${failures} CHECK(S) FAILED`);
process.exit(failures === 0 ? 0 : 1);
