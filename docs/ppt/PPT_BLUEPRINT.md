# PPT Blueprint — QuantumLearnAI

**14 core slides + appendix.** Every "Evidence" line points at something real in
the repository. Speaker notes are written to be said aloud.

**Golden rule for this deck:** the strongest thing about this project is that
it *does not overclaim*. The noise section says "parameterised configuration of
Aer's `thermal_relaxation_error`", not "a novel noise model". The demos are
pinned to numpy, not "correct". Say that out loud — it is more impressive than
a novelty claim you cannot defend.

**Before presenting:** commit and push the three Streamlit-removal commits
(§"Disclose" on slide 14). GitHub at `55d66f2` still shows two frontends.

---

## Slide 1 — Title

**QuantumLearnAI**
*A verified platform for learning quantum computing — lessons, circuits, real
simulation, and honest noise*

- 67 lessons · 71 curriculum topics · 6 simulation backends · 34 API endpoints
- 707 backend tests · 16 frontend harnesses / 389 checks · 4,300 golden values at 1e-9

**Visual:** architecture one-pager (see `ARCHITECTURE_DIAGRAMS.md`).
**Evidence:** measured this session, not from docs.

**Speaker notes:** "This is a teaching platform where every number a student
sees comes from a real simulation. That constraint drove most of the
engineering, and it's what I'll keep coming back to."

---

## Slide 2 — The problem

**Quantum education tools lie in one of three ways:**

1. **Simulation is faked.** A "Grover" animation with hardcoded percentages.
2. **Noise is cosmetic.** Random jitter with no physical meaning.
3. **The learner cannot tell which.**

**What we required instead:**
- Real state-vector simulation, or nothing
- Noise derived from T1/T2 with correct physics
- Every displayed number checkable against an independent reference

**Visual:** three crossed-out boxes vs. three green ones.

**Speaker notes:** "The failure mode I cared about most is a student learning
something false and having no way to detect it."

---

## Slide 3 — Architecture

**Visual:** the main architecture diagram (`ARCHITECTURE_DIAGRAMS.md` §1).

- **React 18 + TypeScript SPA** (Vite, Tailwind) — the only UI
- **FastAPI** — 45 registered routes, 34 application endpoints
- **Celery + Redis** — long simulations off the request path
- **PostgreSQL + pgvector** — 20 tables, curriculum + RAG vectors
- **Quantum subsystem** — 6 backends behind one IR

**Speaker notes:** "One circuit IR, six backends. Adding a backend means
implementing `run()` — it never touches the UI."

---

## Slide 4 — One IR, six backends

**Measured availability, no credentials set, Bell circuit, 256 shots:**

| Backend | Runs? | Counts |
| --- | --- | --- |
| Qiskit Aer 1.2.4 / Aer 0.16.0 | ✅ | `00:122, 11:134` |
| Cirq 1.4.1 | ✅ | `00:129, 11:127` |
| PennyLane 0.44.1 | ✅ | `00:120, 11:136` |
| Dynamic Qiskit | ✅ | `00:119, 11:137` |
| CUDA-Q (GPU) | ⚠ needs GPU | `BackendError` |
| qBraid (real hardware) | 🔒 needs key | `BackendUnavailable` |

**Evidence:** `backend/app/quantum/backends/`, measured directly.

**Speaker notes:** "Four of six run with zero credentials and all four agree.
I deliberately do not demo qBraid — it spends real credits."

---

## Slide 5 — Control flow is real

Most teaching tools stop at static circuits. This one does not.

- `CONTROL_FLOW_KINDS = {if, for, while, box}` in `quantum/ir.py`
- Hard safety caps: `WHILE_CAP = 32`, `FOR_LOOP_CAP = 1024`
- OpenQASM 3 import/export *including* control flow
- `dynamic_qiskit.py` executes it; `samples/dynamic_while.qasm` demos it

**Evidence:** `backend/app/quantum/ir.py:59-66`, `test_dynamic.py` (8 tests),
`test_qasm3.py` (8), `test_codelab_qasm3_and_imports.py` (14).

**Speaker notes:** "Mid-circuit measurement feeding a branch is where quantum
stops looking like linear algebra and starts looking like programming. Students
should see that."

---

## Slide 6 — Noise: what it is and is not ⭐

**This is the slide a reviewer will press hardest on. Get it exactly right.**

### It IS
- A parameterised configuration of **Qiskit Aer's `thermal_relaxation_error`**
- T1 (amplitude damping), T2 (dephasing), symmetric readout error
- Per-gate-class durations: 1q / 2q / 3q; 2q and 3q errors tensored across qubits
- **Virtual-Z gates carry zero noise** — hardware implements them as a software
  frame change, not a pulse

### It is NOT
- ❌ A new scientific noise model
- ❌ Calibration from any real device
- ❌ Crosstalk, leakage, or correlated errors

### The one genuine piece of physics engineering: the T2 clamp
`T2 ≤ 2·T1`, **not** `T2 ≤ T1`.
Because `1/T2 = 1/(2·T1) + 1/T_phi`, the slowest possible dephasing still leaves
`T2 = 2·T1`. Aer *raises* on a violation; the clamp keeps a student's run alive
with an explanation instead of a stack trace.

```
asked T1=10, T2=100  →  T2=20.0   "T2 clamped to 2*T1 = 20 us (physical limit)."
```

**Evidence:** `backend/app/quantum/noise.py`; `test_noise_physics.py` (15) +
`test_noise_model.py` (7), including `test_population_decays_as_exp_minus_t_over_t1`
and `test_coherence_decays_as_exp_minus_t_over_t2`.

**Speaker notes:** "If someone asks 'is this a new noise model?' the answer is
no, and that's the point. It's a correct, physically-bounded *configuration* of
a standard channel, plus one non-obvious correctness fix that a naive
implementation gets wrong."

---

## Slide 7 — Noise: measured behaviour

**Bell state, 2048 shots, seed 11 — reproduced this session:**

| Setting | Counts | P(odd-parity error) |
| --- | --- | --- |
| clean | `00:1011, 11:1037` | **0.000** |
| mild T1=50 T2=30 | `00:1016, 01:51, 10:45, 11:936` | **0.047** |
| harsh T1=2 T2=1, readout 5% | `00:1023, 01:202, 10:228, 11:595` | **0.210** |

**Visual:** side-by-side histograms, clean vs harsh. The UI renders exactly this
("Noisy minus ideal" view — `ResultsViews.tsx:489`).

**Speaker notes:** "A clean Bell state only ever gives 00 and 11. Turn on noise
and 01 and 10 appear — that's decoherence creating population outside the
subspace. The student sees the physics, not a warning message."

---

## Slide 8 — Nothing is faked: the golden-number discipline ⭐

**The demos and labs are TypeScript. Their correctness is checked against numpy.**

| Harness | Values | Tolerance |
| --- | ---: | --- |
| `golden:demos` | **804** | 1e-9 |
| `golden:grover` | **3,306** | 1e-9 |
| `golden:quantum` | **190** | 1e-9 |

The Python reference implementations (`frontend/web/scripts/lib/playground.py`,
`grover_lab.py`) generate the fixtures; the TypeScript port must reproduce every
value. **This is not the port checking itself** — it is an independent oracle.

Grover is a **real 2ⁿ state-vector simulation** — genuine oracle phase flip,
genuine diffusion operator. Nothing is hardcoded.

**Evidence:** `frontend/web/scripts/golden-*.py` / `.mts`; `test_grover_lab.py`,
`test_playground.py` (104 tests) also live beside the reference modules.

**Speaker notes:** "If I change a Schroedinger implementation in TypeScript and
get a sign wrong, a harness fails. That's the difference between a demo and a
teaching tool."

---

## Slide 9 — Curriculum at scale

- **67 lessons**, 153,324 words
- **71 topics** with prerequisites and mastery evaluation
- **344 cross-lesson links** — all navigable (commit `994a800`); a harness
  guards them so they cannot rot again
- **20 tables**, 8 migrations, linear single-headed chain
- Prerequisite engine: `evaluate_prerequisites()` gates a topic until its
  prerequisites are met

**Visual:** the learning-workflow diagram (`ARCHITECTURE_DIAGRAMS.md` §4).

**⚠ Known open decision to disclose:** the Python registry marks 54 of 71
topics `draft`; migration `h3c6d9e2f5a8` publishes them at the DB level, and
`build_curriculum()` filters on the **DB**, so learners see all 71. A re-sync
from the registry would hide 54 topics. Two tests depend on the registry values.
**Report it; don't silently fix it.**

**Evidence:** `backend/app/curriculum.py`, `services/curriculum_service.py:149`,
`test_curriculum.py` (63), `test_curriculum_api.py` (24).

---

## Slide 10 — AI tutor and RAG

- **Gemini** for explanation and code generation
- **pgvector** for retrieval over lesson chunks
- **Heading-aware chunker**: `split_on_headings()` then `chunk_markdown()`,
  `CHUNK_TARGET_CHARS = 1200` — a chunk never splits mid-section
  (measured: `01_qubits.md`, 13,497 chars → **14 chunks**)
- **Keyword fallback** when embeddings are unavailable, so the feature degrades
  instead of breaking
- **Self-healing**: re-chunks when the stored split drifts, and backfills
  `embedding=NULL` rows so RAG never silently degrades forever

**Honest status:** with no `GEMINI_API_KEY`, `is_configured()` returns False.
Chunking and keyword retrieval work; semantic embedding and chat do not.

**Nice engineering detail worth one sentence:** the Gemini client overrides
google-api-core's default 600-second retry deadline, and distinguishes *retired
model* errors from *deadline* errors — because Google retires Gemini models on a
rolling basis and the two need different advice.

**Evidence:** `backend/app/ai/gemini_client.py`, `ai/rag.py`.

---

## Slide 11 — Testing and verification

**Backend — reproduced this session:**
```
707 passed, 5 skipped in 107s        (419 test functions × parametrisation)
```
Hermetic: throwaway SQLite, blanked API keys, so tests never hit real providers.

**Frontend — 16 harnesses, all green (389 named checks):**
```
curriculum 58 · render:check 72 · render:results 47 · render:composer 36
render:learn 37 · render:games 32 · states 31 · render:playground 20
render:grover 27 · render:codelab 15 · a11y 8 · push:overlay 6
```

**Notable:** `push:overlay` drives a **real Chromium** to prove the sidebar
pushes content on reading pages but overlays on the Composer — a CSS regression
that is invisible to unit tests. It self-skips (exit 0) when no browser exists.

**Disclose:** there is **no CI** (`.github/workflows/` absent). Everything runs
manually via `make test` and `npm run <harness>`.

---

## Slide 12 — The Streamlit → SPA cutover ⭐ (engineering maturity)

The platform ran **two frontends in parallel** for a controlled migration.
The React SPA reached route parity — Learn, Composer, Challenges, Dashboard,
Code Lab, Games, Playground, **plus** `/curriculum`, which Streamlit never had.

**What made this safe:**
- The composer grid was **shared from source** via a `@composer` Vite alias, so
  the two UIs could never drift
- `scripts/link-shared.mjs` guarantees **one React** — a second copy fails at
  runtime with "invalid hook call", not at build time
- A `data-cutover-gate` marker plus explicit P8/P9 gates made the cutover a
  *deliberate decision*, not an accident

**The removal (−14,665 lines, 111 files) preserved what was not Streamlit code:**
`playground.py` and `grover_lab.py` are pure maths and generate the golden
fixtures — they moved to `frontend/web/scripts/lib/`, and regenerating both
goldens from the new location reproduces the committed files **byte for byte**.

**Speaker notes:** "Two things worth flagging. First, deleting `viz.py` cost us
four tests, so I rewrote them to assert against Pauli expectation values — the
definition `viz.py` was proxying for — rather than deleting coverage. Second, I
did not scrub the backend comments that justify content rules by reference to
Streamlit; the rules are still correct for KaTeX, and rewriting them would trade
true history for a comment that says less."

---

## Slide 13 — Honest limitations ⭐

Say these before you are asked.

| Limitation | Detail |
| --- | --- |
| Noise is a **configuration**, not a model | No crosstalk, leakage, or correlated errors |
| No real-device calibration | T1/T2 are user-chosen teaching parameters |
| 2 backends not runnable here | CUDA-Q needs a GPU; qBraid needs paid credentials |
| **Composer keyboard a11y gap** | Palette tiles (`Composer.tsx:439-446`) are `draggable` + `onClick` with **no `role`, `tabIndex`, or `onKeyDown`** — click-only, not Tab-reachable |
| Registry/DB status divergence | 54 topics `draft` in Python, `published` in DB |
| **No CI** | 707 tests + 16 harnesses run manually |
| Gemini inert without a key | Semantic embedding and chat unavailable |
| Composer is dense | 40 interactive controls on one screen (audit §1); recommended fix not applied |
| 3 result views unported | Phase disk, Q-sphere, circuit diagram |

**Speaker notes:** "I'd rather list these than have you find them."

---

## Slide 14 — Roadmap: Noise Lab + Smart Composer

**Status: PROPOSED. Not implemented. No `core/` directory, no `evaluate()`, no
`verify()` exists.** Present as future work, never as a feature.

### Noise Lab
Sweeps and heatmaps over T1/T2; sensitivity and attribution analysis; a
findings report. Turns the existing single-point noise panel into an
*experimental* tool.

### Smart Composer — three modes
1. **Teach** — fewest gates, most readable
2. **Execute** — shortest depth / fewest SWAPs on a target device
3. **Balance** — Pareto frontier between them

With a change log so a student sees *what* was changed and *why*.

### Non-negotiables designed in
- **Never recommend an unverified candidate** — every suggestion is re-simulated
  and checked for equivalence before it is shown
- **Noise is applied to the transpiled candidate**, never the source circuit
- **Identical conditions across candidates** — the comparison is only fair if
  every candidate sees the same shots, seed, and noise
- **"No improvement found" is a first-class result**, not an error
- Gemini may **explain** and emit whitelisted intent — it never emits circuits

### Three risks found by reading the plan against this codebase
1. **The plan specifies T1/T2 in nanoseconds; this codebase is microseconds**
   (`t1_us`/`t2_us`). Must be reconciled or the two systems will disagree.
2. **Mode 2 has nothing to target.** No backend exposes a `coupling_map` — they
   are simulators. SWAP-count optimisation has no device model yet.
3. **The composer is shared** — though the Streamlit removal has now largely
   defused this risk.

**Speaker notes:** "The interesting engineering here isn't the optimisation
passes — Qiskit already has those. It's the verification harness that refuses
to show a candidate it hasn't proven equivalent."

---

## Appendix slides (as needed)

- **A1** — Circuit IR schema and gate set
- **A2** — QASM3 round-trip example
- **A3** — Dynamic circuit execution trace
- **A4** — Noise equations: `p_T1 = 1−e^(−t/T1)`, `1/T2 = 1/(2T1) + 1/T_phi`
- **A5** — RAG chunking worked example
- **A6** — DB schema (20 tables)
- **A7** — Full test inventory with counts
- **A8** — Cutover diff statistics and preserved-module evidence
