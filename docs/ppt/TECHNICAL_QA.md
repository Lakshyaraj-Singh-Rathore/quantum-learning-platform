# Technical Q&A — Viva Preparation

Answers are grounded in the code. Where something is unknown or unverified, it
says so. Learn the ⭐ ones first — they are the ones that decide the grade.

---

## Architecture & design

**Q: Why a custom Circuit IR instead of using Qiskit's `QuantumCircuit` directly?**
Because the platform must target six backends with different native types
(Qiskit, Cirq, PennyLane, CUDA-Q, qBraid, dynamic Qiskit) and must round-trip
through OpenQASM 3 *including control flow*. A Pydantic `CircuitIR`
(`backend/app/quantum/ir.py`) is the neutral pivot: each backend implements
`run()`, each codegen target implements a translation, and neither couples to
the UI. It also validates at the boundary — `Op` is a Pydantic model, so a
malformed op is rejected before it reaches a simulator.

**Q: Why is the composer grid outside `frontend/web/`?**
It was shared between two frontends during the migration, so it lived in its own
tree and was compiled into the SPA from source via a `@composer` Vite alias —
one implementation, no drift. Now that Streamlit is gone the alias is kept
because that is where the grid's history and tests live. The cost is that
`react` must resolve from that directory too, which is why
`scripts/link-shared.mjs` symlinks it: a second React copy fails at *runtime*
with "invalid hook call", not at build time.

**Q: Why Celery + Redis at all?**
Long simulations would otherwise occupy a FastAPI worker. Jobs are enqueued and
polled. In tests and in free-tier deployments `CELERY_TASK_ALWAYS_EAGER=true`
runs them inline, so the same code path works with no broker.

**Q: Why did you run two frontends in parallel instead of rewriting?**
Risk. The Streamlit app was the working product; the SPA was the replacement.
Running both let every page reach parity before anything was deleted, and the
cutover was gated (P8/P9) so it could only happen on a human decision.
Parity was reached — the SPA has all seven Streamlit routes plus `/curriculum`.

---

## Quantum simulation ⭐

**Q: Are you actually simulating, or is it scripted?**
Actually simulating. Verified this session: Qiskit Aer, Cirq, PennyLane and
dynamic Qiskit each produced a correct Bell distribution
(`{'00':~122, '11':~134}` at 256 shots). Grover is a real 2ⁿ state-vector
simulation with a genuine oracle phase flip and diffusion operator — and 3,306
of its values are checked against numpy at 1e-9.

**Q: How do you guarantee the TypeScript maths is right?**
You do not trust it — you check it against an independent oracle.
`frontend/web/scripts/golden-*.py` (numpy) generate fixtures;
`golden:demos` (804 values), `golden:grover` (3,306), `golden:quantum` (190)
assert the TypeScript agrees to 1e-9. It is not the port checking itself.

**Q: What happens with a 30-qubit circuit?**
`guard_static_size()` (`backends/base.py:80`) rejects it before it can exhaust
memory. `MAX_STATIC_QUBITS` is 20 locally and 14 on the free tier (Render's
512 MB would OOM at ~655 MB). Oversized circuits get a clean HTTP 422 with an
explanation, not a crash and not a timeout.

**Q: Do your backends agree with each other?**
That is exactly what `test_backend_agreement.py` (4 tests) and
`test_engine_matrix.py` (9 tests) check — the same circuit across engines must
produce statistically consistent distributions.

**Q: What about control flow / mid-circuit measurement?**
Supported. `CONTROL_FLOW_KINDS = {if, for, while, box}`, executed by
`dynamic_qiskit.py` with hard caps `WHILE_CAP = 32` and `FOR_LOOP_CAP = 1024`.
QASM3 import/export preserves it. `samples/dynamic_while.qasm` demonstrates it.

---

## Noise ⭐ (the section you will be pressed hardest on)

**Q: Is this a new noise model?**
**No, and I would not claim it is.** It is a parameterised *configuration* of
Qiskit Aer's `thermal_relaxation_error`, applied per gate class. T1 gives
amplitude damping, T2 gives dephasing, plus symmetric readout error. It is not
calibration from a real device; the parameters are teaching choices.
**Say this plainly** — a correct configuration plus one real correctness fix is
more defensible than a novelty claim you cannot support.

**Q: Then what is actually yours?**
Two things. (1) **The T2 clamp.** `T2 ≤ 2·T1`, not `T2 ≤ T1`. Since
`1/T2 = 1/(2·T1) + 1/T_phi`, the slowest possible dephasing still leaves
`T2 = 2·T1`; the region `T1 < T2 < 2·T1` is physical and must be preserved.
A naive implementation clamps at `T1`, which is simply wrong, and Aer raises on
a true violation — so the clamp turns a crash into a run that continues with an
explanation. (2) **Virtual-Z gates carry no thermal error**, matching hardware,
where `z/s/sdg/t/tdg/rz/p` are software frame changes rather than pulses.

**Q: Why keep gates undecomposed (`BASIS_GATES`)?**
So one user-facing gate is roughly one noise event. If Aer decomposed `h` into
a sequence, one drawn gate would accumulate several pulses' worth of error and
the student's mental model would break.

**Q: Prove the noise does something physical.**
Measured, Bell state, 2048 shots:
- clean → `00:1011, 11:1037`, P(odd-parity error) = **0.000**
- mild (T1=50, T2=30) → `01` and `10` appear, P = **0.047**
- harsh (T1=2, T2=1, readout 5%) → P = **0.210**

And `test_noise_physics.py` asserts the decay *laws* directly:
`test_population_decays_as_exp_minus_t_over_t1`,
`test_coherence_decays_as_exp_minus_t_over_t2`,
`test_longer_t1_means_less_decay`,
`test_two_qubit_error_hits_both_qubits_equally`.

**Q: What noise is missing?**
Crosstalk, leakage, correlated/spatially-varying errors, and any real-device
calibration. State that as a limitation.

---

## AI / RAG

**Q: Does it work without an API key?**
Partially. `is_configured()` returns False (verified) — no semantic embedding,
no chat. But chunking works (measured: `01_qubits.md` → 14 chunks) and retrieval
**falls back to keyword scoring**, so the feature degrades rather than breaking.

**Q: Why is the chunker heading-aware?**
`split_on_headings()` then packs to `CHUNK_TARGET_CHARS = 1200`. A chunk that
splits mid-section retrieves badly and cites badly. Splitting on structure first
keeps each chunk semantically whole.

**Q: What stops RAG silently degrading to keyword mode forever?**
Two self-healing behaviours in `ai/rag.py`: it re-chunks when the stored split
no longer matches what the chunker now produces (a stale one-chunk-per-lesson
split would otherwise persist forever), and it backfills rows with
`embedding=NULL` so they gain vectors once a key exists.

**Q: Any real Gemini engineering worth mentioning?**
Yes. The client overrides google-api-core's default **600-second** retry
deadline, and classifies errors into *transient*, *retired model*, and
*deadline* — because Google retires Gemini models on a rolling basis and the
three need different advice. Also, on Gemini 3.x "thinking" tokens are billed
against the output budget, which is documented in the client.

---

## Testing & engineering rigour ⭐

**Q: How do you know it works?**
```
backend:   707 passed, 5 skipped in 107s   (419 test functions)
frontend:  16 harnesses, all green — 389 named checks
goldens:   804 + 3,306 + 190 values matched to numpy at 1e-9
```
Both reproduced this session, not quoted from a report.

**Q: Are the tests hermetic?**
Yes. `conftest.py` uses a throwaway SQLite file and blanks `GEMINI_API_KEY` and
`QBRAID_API_KEY`, so no test can hit a real provider or spend credits.
`QL_TEST_DATABASE_URL` opts into a real Postgres run for cross-database checks.

**Q: The audit mentioned an Alembic failure — is it still there?**
**No. It does not reproduce.** The suite is 707 green, and the migration chain
is linear and single-headed (`b5f10b499a50 → … → h3c6d9e2f5a8`) with no branch
points. The likely cause was environmental — a stale `alembic_version` row in a
dev database. Note `database.py:89`: `create_all` is a **no-op when an
`alembic_version` table exists**, so Alembic remains the schema owner.

**Q: Why does `push:overlay` need a real browser?**
Because the bug it guards is invisible to unit tests. The sidebar must *push*
content on reading pages but *overlay* it on the Composer. Delete the `peer`
class and reading pages silently start overlaying — typecheck passes, build
passes, the layout is wrong. The harness drives Chromium at 1440×900, hovers the
rail, and measures both the rail width and the content padding. It was proven to
bite: removing `peer` makes it fail with exit 1.

**Q: Is there CI?**
No — `.github/workflows/` does not exist. Everything runs manually via
`make test` and `npm run <harness>`. **Disclose this; do not imply otherwise.**

---

## Contributions ⭐

**Q: What is genuinely yours?**
Ranked, with honest framing:

1. **Verified-integration teaching loop** — the composer, six backends, the
   noise model and the visualisations under one IR, with every displayed number
   pinned to an independent oracle. The contribution is the *integration and its
   verification*, not any single algorithm.
2. **The golden-number discipline** — 4,300 numeric values checked against
   numpy at 1e-9, so a TypeScript physics port cannot silently drift.
3. **The T2 ≤ 2·T1 clamp** — small, correct, and a genuine correctness fix that
   a naive implementation gets wrong.
4. **Dynamic-circuit support in a teaching tool** — `if`/`for`/`while`/`box`
   with safety caps and QASM3 round-trip; most teaching platforms stop at static
   circuits.
5. **The controlled dual-frontend cutover** — −14,665 lines removed with the
   shared grid, the goldens and 104 tests preserved and byte-identical output
   proven.

**Q: Is the circuit optimiser yours?**
**No — and the Smart Composer is not built.** Today's optimisation is Qiskit's
`transpile(optimization_level=1)` in `normalize.py`. Any "optimisation" claim
before the Smart Composer exists would be false. Present it as future work.

---

## Tricky questions to expect

**"54 topics are draft in the registry but 71 are published in the DB — is that a bug?"**
It is a **known, deliberate divergence**, and I can explain the mechanism.
M4 registered 54 topics as `draft` to get stable IDs before content existed.
Migration `h3c6d9e2f5a8` publishes them with an explicit
`PUBLISHED_TOPIC_IDS` frozenset — explicit, not derived, because the API
container mounts only `./backend`, `./content` and `./samples`, so `docs/` is
unreadable from inside a migration, and an explicit list keeps `downgrade` exact.
`build_curriculum()` filters on `status == "published"` reading the **database**,
so learners see 71. **The risk:** re-syncing from the registry would hide 54
topics. Two tests depend on the registry values. It is an open decision for the
owner.

**"Your audit says X — is that still true?"**
Be careful. `reports/UI_AUDIT.md` audited the **Streamlit** app (a "Home" page,
`st.text_area`, `st.rerun()` races). Streamlit is gone. Of its three claimed
fixes: `GAME_PASS_THRESHOLD = 1.0` is **present and verified** (44 tests); the
duplicated-toolbar/epoch fix is **moot** (its subject was deleted, and the race
cannot occur with one host); the `code_checks` diagnostics **survived but moved**
to `backend/app/services/code_checks.py` with 8 tests, not the ~20 claimed — the
rest were Streamlit-UI tests. Also, the `artifacts/ui-audit/` directory the brief
references **does not exist in this repository**.

**"Is the composer accessible?"**
Partially. Zero a11y criticals across every page, **but** the palette tiles
(`Composer.tsx:439-446`) are `draggable` + `onClick` with no `role`, no
`tabIndex`, no `onKeyDown` — click-only, not Tab-reachable. A real,
acknowledged gap. Fixing it means giving each tile a button role and a keyboard
placement flow.

**"What would you do next?"**
In priority order: (1) commit and push the cutover; (2) add CI — 707 tests that
nobody runs automatically are 707 tests that rot; (3) fix the palette keyboard
path; (4) resolve the registry/DB divergence; (5) thin the Composer's 40 controls
behind an "Export & share" expander (the audit's cheapest recommendation, ~1
hour, still not applied); (6) then the Noise Lab / Smart Composer — with the ns
vs µs unit mismatch fixed first, and Mode 2 deferred until a backend actually
exposes a coupling map.
