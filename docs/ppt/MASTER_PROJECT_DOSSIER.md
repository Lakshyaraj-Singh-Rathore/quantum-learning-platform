# QuantumLearnAI — Master Project Dossier

**Purpose:** a source-verified explanation of the whole project, written so you can
present it, demo it, and defend it in a viva. Every claim below was checked
against the code in this repository, not against earlier documentation.

**Baseline used:** commit `55d66f2` on `arena/01a0d874-quantum-learning-platform`
(GitHub tip). See §0 for the exact state, including what is *not* committed.

---

## 0. Confirmed repository state (read this first)

| Item | Value |
| --- | --- |
| Branch | `arena/01a0d874-quantum-learning-platform` |
| GitHub tip | `55d66f2` ("Add a self-booting browser check for the sidebar push/overlay contract", 2026-10-11) |
| Local git ref | **stale** — the sandbox re-cloned and left HEAD at `9b106fd` |
| Working tree | contains 3 further commits' worth of Streamlit-removal work, **uncommitted** |
| `main` | `53cf53e` ("Add files via upload", 2026-09-06) |
| `arena/01a0754d-…` | `9b106fd` — GPU ceiling 28 qubits; **fully merged into ours** |
| Remote | `https://github.com/Lakshyaraj-Singh-Rathore/quantum-learning-platform.git` |

### Three disclosures you must not skip

1. **Three commits are uncommitted and unpushed.** The Streamlit removal
   (`21a253c`, `7c75cfd`, `bbbb591`) exists only as working-tree changes. GitHub
   still shows `55d66f2`. Push was attempted and failed:
   `fatal: could not read Username for 'https://github.com'` — the sandbox's
   `GH_TOKEN` has expired (`gh auth status` → "token is no longer valid").
   `git ls-remote` and `git fetch` still work, so the branch table below is
   accurate. **Reconnect GitHub and commit before presenting.**

2. **The UI audit describes a UI that no longer exists.** `reports/UI_AUDIT.md`
   audited the *Streamlit* app: it inventories a "Home" page, expanders,
   `st.text_area`, `st.rerun()` races. That app was removed (§3.1). Treat the
   audit as historical evidence, not current truth.

3. **The `artifacts/ui-audit/` directory referenced by the brief does not exist
   in this repository.** There is no `FINAL_REPORT.md`, `coverage.json`,
   `defects.json`, `interactive-results.json`, or screenshot set. Only
   `reports/UI_AUDIT.md` (6.6 KB) is present. I could not verify claims that
   lived only in those files.

---

## 1. What the product is

A **quantum computing teaching platform**. A learner reads a lesson, builds a
circuit on a drag-and-drop grid, runs it on one of several real simulators,
sees the result visualised, and is assessed — with an AI tutor grounded in the
lesson corpus.

Two audiences:
- **Learner** — 67 lessons, 71 curriculum topics, circuit composer, playground,
  games, challenges, mastery dashboard.
- **Instructor** — progress per student, per-topic mastery, recommendations.

The distinguishing design choice: **it never fakes a result.** The Grover
module runs a real 2ⁿ state-vector simulation; the demos are pinned to numpy
goldens at 1e-9; the noise model is a real Aer noise model rather than a
cosmetic random jitter.

---

## 2. Architecture

```
                    Browser (React 18 SPA, Vite)
   /learn /curriculum /composer /challenges /codelab /dashboard /games /playground
                              │
                              │  fetch("/api/*")   ← same-origin
                              ▼
        nginx (in container) or Vite dev proxy  →  strips /api
                              │
                              ▼
                    FastAPI  (45 registered routes)
        ┌──────────┬──────────┼──────────┬───────────┬────────────┐
        │ auth     │ jobs     │ circuits │ curriculum│ assessments│
        │ (JWT)    │ (Celery) │ (CRUD,   │ (topics,  │ (quizzes,  │
        │          │          │  QASM3,  │  lessons, │  challenges│
        │          │          │  export, │  mastery) │  games)    │
        │          │          │  inspect)│           │            │
        └──────────┴──────────┴──────────┴───────────┴────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
     Quantum subsystem    AI / RAG        PostgreSQL + pgvector
     6 backends           Gemini          20 tables
     noise model          keyword fallback
                              │
                          Redis (Celery broker)
```

**Verified route count:** 45 registered routes — 34 application endpoints plus
`/health`, `/docs`, `/openapi.json`, `/redoc`, `/docs/oauth2-redirect`, `/`.
Measured by importing `app.main:app` and walking `app.routes`, not by reading
docs.

### Frontend

- **SPA only.** `frontend/web/` — React 18 + TypeScript + Vite + Tailwind.
- Routes (`src/App.tsx`): `/login`, `/register`, `/learn`, `/curriculum`,
  `/curriculum/topic/:topicId`, `/composer`, `/challenges`, `/dashboard`,
  `/codelab`, `/games`, `/playground`, `*` → NotFound.
- State: `src/state/circuit.ts` (shared circuit), `session.ts` (JWT),
  `theme.ts`.
- **The composer grid is shared from source.** `frontend/circuit_composer/frontend/src`
  lives outside `web/` and is compiled in via the `@composer` alias in
  `vite.config.ts`. `scripts/link-shared.mjs` symlinks `react`/`react-dom`/`@types`
  so exactly one React is resolved — a second copy fails at *runtime* with
  "invalid hook call", which is why the link exists.

### Backend layout (measured)

| Area | Files | Lines |
| --- | ---: | ---: |
| `quantum/` (incl. backends) | 21 | 4,165 |
| `services/` | 8 | 2,224 |
| `api/` | 9 | 1,380 |
| `ai/` | 5 | 857 |
| `models/` | 9 | 482 |
| `schemas/` | 7 | 227 |
| `workers/` | 3 | 164 |

---

## 3. Quantum subsystem

### 3.1 Circuit IR

`backend/app/quantum/ir.py`. Pydantic models: `Param`, `Condition`, `Op`,
`CircuitIR`.

Gate set (17): `h x y z id swap s sdg t tdg sx p rx ry rz`, plus controlled
forms via `CONTROLLED_ALIASES` (`cx/cnot`, `ccx/toffoli`, `mcx` arbitrary
controls, `cz`, `cy`, `cp`, `crz`, `cswap/fredkin`). Acceptance aliases
(`not`, `hadamard`, `i`, `u1`, `phase`).

**Control flow is first-class:** `CONTROL_FLOW_KINDS = {if, for, while, box}`,
with safety caps `WHILE_CAP = 32` and `FOR_LOOP_CAP = 1024`.

### 3.2 Backends — measured availability

Tested directly with a Bell circuit, 256 shots, no credentials set:

| Backend | Module | Runs credential-free? | Result |
| --- | --- | --- | --- |
| Qiskit Aer | `qiskit_aer.py` | **Yes** | `{'00':122, '11':134}` |
| Cirq | `cirq_sim.py` | **Yes** | `{'00':129, '11':127}` |
| PennyLane | `pennylane_sim.py` | **Yes** | `{'00':120, '11':136}` |
| Dynamic Qiskit | `dynamic_qiskit.py` | **Yes** | `{'00':119, '11':137}` |
| CUDA-Q | `cudaq_sim.py` | No — needs CUDA-Q + NVIDIA GPU | `BackendError: CUDA-Q is not installed` |
| qBraid | `qbraid_sim.py` | No — needs `QBRAID_API_KEY` | `BackendUnavailable: Missing qBraid credentials` |

Installed versions: Qiskit 1.2.4, qiskit-aer 0.16.0, PennyLane 0.44.1,
Cirq 1.4.1.

**For the demo and the viva: 4 of 6 backends are executable with zero
credentials, and all 4 agree on the Bell state.** Do not demo qBraid — it
spends real credits.

### 3.3 Noise model — what it actually is

`backend/app/quantum/noise.py`. Be precise about this in the viva.

It is a **parameterised configuration of Qiskit Aer's
`thermal_relaxation_error`**, not a new scientific noise model.

What it does:
- `NoiseParams`: `enabled`, `t1_us`, `t2_us`, `readout_error`,
  `gate_time_1q_us`, `gate_time_2q_us`, `gate_time_3q_us` (microseconds).
- 1q gates get `thermal_relaxation_error(t1, t2, gate_time_1q)`; 2q and 3q get
  the same error tensored 2× and 3× so every qubit in the gate decays.
- Readout: `ReadoutError([[1-r, r], [r, 1-r]])` — symmetric.
- **Virtual-Z gates carry no noise** (`z s sdg t tdg rz p` are zero-duration),
  matching how hardware implements them as a software frame change.
- `BASIS_GATES` keeps gates undecomposed so one user-facing gate ≈ one noise event.

**The one piece of genuine physics engineering is the T2 clamp.**
`clamped()` enforces `T2 ≤ 2·T1`, not `T2 ≤ T1`. Pure dephasing adds as
`1/T2 = 1/(2·T1) + 1/T_phi`, so the slowest possible dephasing still leaves
`T2 = 2·T1`. Aer raises on a violation; the clamp keeps a student's run alive
with an explanation instead of an exception.

Measured:
```
clean                {'00':1011, '11':1037}   P(odd-parity error)=0.000
mild  T1=50 T2=30    {'00':1016,'01':51,'10':45,'11':936}  P=0.047
harsh T1=2  T2=1     {'00':1023,'01':202,'10':228,'11':595} P=0.210
asked T1=10 T2=100 → clamped T2=20.0, note "T2 clamped to 2*T1 = 20 us"
```

**Noise UI:** `ComposerPage.tsx` has a `NoisePanel` (T1/T2/readout fields,
`NOISE_BACKENDS = {qiskit_aer, cudaq}` — greyed out on other backends).

### 3.4 QASM3, dynamic circuits, codegen

- `qasm3_codec.py` — OpenQASM 3 import/export for the subset the platform emits,
  including control flow.
- `dynamic_qiskit.py` — executes `if`/`for`/`while`/`box` with hard caps.
- `codegen_{qiskit,cirq,pennylane,qbraid}.py` — export to four SDKs.
- Samples: `samples/bell.qasm`, `grover.qasm`, `dynamic_while.qasm`.

---

## 4. AI / RAG

**Gemini** (`ai/gemini_client.py`): `is_configured()` returns **False** with no
`GEMINI_API_KEY` (verified). The client has deliberate engineering worth
mentioning: it overrides google-api-core's default 600-second retry deadline,
and detects *retired models* (`_is_retired_model`) and *deadline* errors
separately, because Google retires Gemini models on a rolling basis.

**RAG** (`ai/rag.py`): ingestion + retrieval over Postgres/pgvector.
- `CHUNK_TARGET_CHARS = 1200`; `split_on_headings()` then
  `chunk_markdown()` — **heading-aware**, so a chunk never splits mid-section.
- Measured: `content/01_qubits.md` (13,497 chars) → **14 chunks**.
- **Keyword fallback when embeddings are unavailable** (no API key) — the
  platform degrades instead of breaking.
- Self-healing: re-chunks when the stored split no longer matches
  (`stored N but chunker now yields M`), and backfills `embedding=NULL` rows so
  RAG never silently degrades to keyword mode forever.

**Status: partially executable.** RAG chunking and keyword retrieval work with
no credentials. Semantic embedding and chat do not.

---

## 5. Curriculum, content, assessment

- **67 lesson markdown files**, 153,324 words, **344 cross-lesson links**
  (all made navigable — commit `994a800`).
- **71 topics** in `backend/app/curriculum.py` registry: **17 `published` +
  54 `draft`**.
- **20 DB tables**, 8 Alembic migrations — **linear, single-headed chain**:
  `b5f10b499a50 → c7a2e4d19b30 → d8b3f6c02a11 → e9c4a7d31b22 → f1a2b3c4d5e6
  → a2b3c4d5e6f7 → g2a5b8c1d4e7 → h3c6d9e2f5a8`.
- Assessment: quizzes, coding challenges, autograder, games.

**Autograder thresholds** (`services/autograder.py`): `PASS_THRESHOLD = 0.8`
for coding challenges (partial credit), `GAME_PASS_THRESHOLD = 1.0` for game
levels — a puzzle has exactly one answer. Guarded by 44 tests.

### The 54-vs-71 discrepancy — resolved

The brief asks why the "draft registry has 54 topics while the published
database has 71". Here is the actual mechanism:

- M4 registered 54 topics as `draft` so the curriculum had stable IDs before
  content existed.
- Migration `h3c6d9e2f5a8` publishes them at the **database** level via an
  explicit `PUBLISHED_TOPIC_IDS` frozenset — explicit rather than derived,
  because the API container mounts only `./backend`, `./content`, `./samples`,
  so `docs/` is unreadable from inside a migration, and an explicit list keeps
  `downgrade` exact.
- `build_curriculum()` filters `CurriculumTopic.status == "published"` — reading
  the **database**, not the registry.

**So: DB says 71 published; the Python registry still says 54 of them are
draft.** The learner sees all 71. If anyone re-syncs from the registry, those
54 revert to draft and the curriculum appears to empty itself. Two tests depend
on the registry values. **This is a known open decision for the owner — report
it, do not silently fix it.**

---

## 6. Testing — reproduced, not assumed

### Backend (newly reproduced this session)

```
cd backend && PYTHONPATH=. /home/user/.venv-ql/bin/python -m pytest -q
→ 707 passed, 5 skipped in 107.18s
```

419 test functions → 707 cases after parametrisation. Hermetic: `conftest.py`
uses a throwaway SQLite file and blanks `GEMINI_API_KEY`/`QBRAID_API_KEY`, so
tests never hit real providers. `QL_TEST_DATABASE_URL` opts into a real
Postgres run.

Largest suites: `test_curriculum.py` (63), `test_quantum_games.py` (44),
`test_gpu_backend.py` (34), `test_curriculum_api.py` (24),
`test_gate_physics.py` (19), `test_noise_physics.py` (15),
`test_noise_model.py` (7).

**No Alembic failure reproduces.** The brief mentions one; the suite is green
and the migration chain is linear and single-headed. The likely cause was
environmental (a stale `alembic_version` row or a pre-migration dev DB). Note
`database.py:89` guards this: `create_all` is a **no-op when an
`alembic_version` table exists**, so Alembic stays the owner.

### Frontend harnesses (newly reproduced)

16 scripts: 12 emit named checks (389 total), 3 are golden-number comparators
(4,300 values at 1e-9), and `render:content` renders the 67-lesson corpus.

```
typecheck: PASS | build: PASS
curriculum 58 · render:learn 37 · render:check 72 · a11y 8 · states 31
render:results 47 · render:codelab 15 · render:composer 36 · render:games 32
render:playground 20 · render:grover 27
golden:quantum 190 values · golden:demos 804 values · golden:grover 3306 values
                                              (all at 1e-9 against numpy)
render:content → 67 lessons rendered
```

`push:overlay` (6 checks, real Chromium) also passes but needs
`bash tools/browser-setup.sh` first; it self-skips with exit 0 when no browser
is present.

### Route coverage gaps

`/inspect` and `/circuits/timeline` are tested at the **module** level
(`test_audit_hardening.py`, `test_timeline_and_metrics.py`), not over HTTP.
`/codelab/build` is tested via `build_circuit()` in `test_codelab.py` (18 tests).
`/dashboard/recommendations` is covered indirectly in
`test_instructor_progress.py`. So: **every endpoint has some coverage, but a
few are not exercised through the HTTP layer.**

### Environment

No CI exists (`.github/workflows/` absent). Docker Compose services: `postgres`,
`redis`, `api`, `worker`, `web`. `make up` auto-detects a GPU and layers
`docker-compose.gpu.yml`.

---

## 7. Feature status matrix

| Feature | Status | Evidence |
| --- | --- | --- |
| Multi-backend execution (6) | **Implemented & verified** — 4 run credential-free, measured | §3.2 |
| Circuit editing + simulation | **Implemented & verified** | render:composer 36, test_jobs 14 |
| QASM3 import/export | **Implemented & verified** | test_qasm3 8, test_codelab_qasm3 14 |
| Dynamic circuits (if/for/while/box) | **Implemented & verified** | test_dynamic 8, dynamic_qiskit runs |
| Noise modelling (T1/T2/readout) | **Implemented & verified** | 22 noise tests + measured decay curve |
| Visualisations (Bloch, density matrix, histogram, phase) | **Implemented & verified** | render:results 47 |
| Curriculum + mastery + progress | **Implemented & verified** | test_curriculum 63, test_curriculum_api 24 |
| Golden-pinned demos vs numpy | **Implemented & verified** | 804 + 3306 + 190 values @1e-9 |
| Quizzes / challenges / autograder | **Implemented & verified** | GAME_PASS_THRESHOLD, 44 game tests |
| RAG chunking + keyword retrieval | **Implemented & verified** | 14 chunks measured, fallback works |
| Gemini semantic embedding + chat | **Partially implemented** — needs `GEMINI_API_KEY` | `is_configured()` → False |
| CUDA-Q GPU backend | **Implemented, not runnable here** | `BackendError: CUDA-Q is not installed` |
| qBraid hardware backend | **Implemented, credential-gated** | `BackendUnavailable` |
| Code Lab (6-framework editor) | **Implemented & verified** | render:codelab 15, test_codelab 18 |
| **Smart Composer (optimisation)** | **NOT IMPLEMENTED — proposed** | No `core/` dir, no `evaluate()`, no `verify()` |
| **Noise Lab (sweeps/heatmaps)** | **NOT IMPLEMENTED — proposed** | Only the Composer's `NoisePanel` exists |
| Circuit *optimisation* passes | **Existing transpiler only** | `normalize.py` → `transpile(opt_level=1)` |
| CI/CD | **Absent** | no `.github/workflows/` |

---

## 8. Reconciling the UI audit with the code

`reports/UI_AUDIT.md` claims three fixes. Verified:

| Audit claim | Verdict | Evidence |
| --- | --- | --- |
| `GAME_PASS_THRESHOLD = 1.0` for game levels | **Present & verified** | `autograder.py:26`; 44 tests in `test_quantum_games.py` |
| Duplicated toolbar + grid-epoch race | **Moot — superseded** | Subject was `frontend/lib/composer.py` (Streamlit); deleted. Bug was a Streamlit↔React replay race that **cannot occur** with a single host |
| `code_checks.py` live diagnostics | **Present, relocated, reduced** | Now `backend/app/services/code_checks.py`; 8 tests in `test_codelab_check.py` (audit claimed ~20 — the rest were Streamlit-UI tests that died with the UI) |

Audit-cited guard files: `test_quantum_games.py` **survives**;
`test_ui_integrity.py` and `test_code_checks.py` **were deleted with Streamlit**.

**Remaining a11y gap — still present, verified in source.** The composer
palette tiles (`frontend/circuit_composer/frontend/src/Composer.tsx:439-446`)
are `draggable` + `onClick` with **no `role`, no `tabIndex`, no `onKeyDown`**.
Selectable by click, unreachable by Tab. `a11y-check.mts` prints this as a
known, non-critical gap.

---

## 9. Technical debt and open items

1. **3 commits uncommitted; push blocked by an expired token.** Highest risk.
2. **Registry/DB status divergence** (54 draft vs 71 published) — open decision.
3. **Composer palette keyboard accessibility** — real, unfixed.
4. **No CI** — all 707 backend tests and 16 frontend harnesses run manually.
5. **Composer is overloaded**: 40 interactive controls on one screen (audit §1).
   The audit recommended moving the 7 export tabs behind one expander; not done.
6. **Unported result views**: phase disk, Q-sphere, circuit diagram (WEB_DEV.md).
7. **`VITE_API_BASE` is compile-time** — changing the API URL needs a rebuild.
8. **Backend comments still cite Streamlit** as the rationale for content rules
   (e.g. "Streamlit renders the remainder as raw LaTeX"). The rules are still
   correct for the SPA's KaTeX renderer; the justifications are stale.

---

## 10. Contribution matrix

The brief asks specifically to distinguish a parameterised configuration of
established noise channels from a genuinely new noise model, and existing
compiler passes from custom optimisation logic. The two "❌ not a contribution"
rows are deliberate — they are the claims most likely to be made and least
likely to survive questioning.

| # | Candidate contribution | What is actually implemented | Libraries reused | Distinctive engineering | Test evidence | Limitations | Defensible claim |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | **Verified multi-backend teaching loop** | One Pydantic `CircuitIR` → 6 backends → one result schema → shared visualisations, with noise and QASM3 throughout | Qiskit Aer, Cirq, PennyLane, CUDA-Q, qBraid, `transpile()` | The IR as a neutral pivot (incl. control flow), a single result schema across engines, and **golden-pinning every displayed number** | 707 backend tests; `test_backend_agreement.py` (4); `test_engine_matrix.py` (9); 4 cross-backend Bell runs reproduced | 2 backends not runnable here (GPU / paid key) | "An integrated, verification-backed teaching loop" — **not** "a new simulator" |
| 2 | **Golden-number discipline** | numpy reference modules generate fixtures; the TypeScript port must reproduce them at 1e-9 | numpy (oracle), tsx harnesses | Keeping the Python reference *and* its tests as the oracle, so the port is never self-certifying | 804 + 3,306 + 190 = **4,300 values** at 1e-9; 104 Python tests beside the reference | Requires numpy in the toolchain; covers maths, not layout | "Every number a student sees is checked against an independent reference" |
| 3 | **T2 ≤ 2·T1 clamp** ⭐ | `NoiseParams.clamped()` | Qiskit Aer `thermal_relaxation_error` | Recognising that the physical bound is **2·T1**, not T1 (`1/T2 = 1/(2T1) + 1/T_phi`), and clamping with an explanatory note instead of letting Aer raise | `test_t2_is_clamped_to_twice_t1`, `test_the_limit_is_not_half_of_t1`, `test_clamping_explains_itself`; 22 noise tests total | One function — small, but a *correctness* fix, not a feature | "A correctness fix a naive implementation gets wrong" |
| 4 | **Virtual-Z noise exemption** | Zero-duration treatment for `z s sdg t tdg rz p` | Aer noise model | Matching hardware reality (software frame change, not a pulse) so the student's mental model is right | `test_virtual_z_gates_carry_no_noise`, `test_virtual_z_gates_take_no_thermal_error` | Teaching approximation | "Physically-motivated modelling detail" |
| 5 | **Dynamic circuits in a teaching tool** | `if/for/while/box` in the IR, QASM3 round-trip, executed by `dynamic_qiskit.py` | Qiskit | Hard safety caps (`WHILE_CAP=32`, `FOR_LOOP_CAP=1024`) so a student's infinite loop cannot hang the worker | `test_dynamic.py` (8); `test_qasm3.py` (8); `test_codelab_qasm3_and_imports.py` (14) | Only one dynamic backend | "Control flow where most teaching tools stop at static circuits" |
| 6 | **Controlled dual-frontend cutover** | Streamlit removed: −14,665 lines, 111 files | Vite, Playwright | Preserving what was *not* Streamlit code; proving byte-identical goldens after relocation; rewriting 4 orphaned tests against Pauli expectations rather than deleting them | 16 harnesses green; goldens byte-identical; `push:overlay` 6/6 in real Chromium | 3 commits uncommitted; composer keyboard a11y still open | "A migration executed without losing the verification" |
| 7 | **Degradation by design** | RAG keyword fallback; backend-unavailable reasons shown in the UI; disabled AI Generate explains itself (`a805f30`) | pgvector, Gemini SDK | Every unavailable capability says **why** instead of failing silently | `test_qbraid_config.py` (6); `is_configured()` → False verified | Semantic features inert without a key | "The product stays honest when a dependency is missing" |
| ❌ | **"A new noise model"** | It is a parameterised **configuration** of Aer's `thermal_relaxation_error` | Qiskit Aer | — | — | No crosstalk, leakage, correlated errors, or device calibration | **Do not claim.** Say "a correct, physically-bounded configuration, plus one real correctness fix" |
| ❌ | **"A circuit optimiser"** | Only `transpile(optimization_level=1)` in `normalize.py`. **Smart Composer is not built** — no `core/`, no `evaluate()`, no `verify()` | Qiskit transpiler | — | — | Nothing to verify yet | **Do not claim.** Present as future work |

### Recommended top five for the PPT

1. **Verified multi-backend teaching loop** (breadth + integration)
2. **Golden-number discipline** (the honesty hook — most memorable)
3. **T2 ≤ 2·T1 clamp** (depth: one small, provably-correct piece)
4. **Dynamic circuits** (differentiation vs. typical teaching tools)
5. **Controlled cutover** (engineering maturity)

Lead with #2 if the audience is academic; lead with #1 if it is product-focused.
