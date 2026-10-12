# QuantumLearn — AI-Based Interactive Quantum Algorithm Learning Platform

### Presentation source material

> **Every figure in this document was measured against the running system, not
> carried over from an earlier draft.** Where a number was previously quoted
> from memory and contradicted by measurement, the measured value is used and
> the discrepancy is noted in [§10](#10-corrections-made-to-earlier-drafts).

---

## 1. Problem Statement

**Quantum computing education has a tooling gap: the tools that teach are not
the tools that run, and the tools that run do not teach.**

Quantum algorithms are counter-intuitive. Superposition, entanglement, phase
kickback and interference have no classical analogue, so learners cannot rely
on existing intuition — they must build it by *experimenting*. Yet the
software landscape forces a choice between two unsatisfactory options:

**Option A — Professional SDKs (Qiskit, Cirq, PennyLane).**
Powerful and industry-standard, but they assume Python fluency, linear
algebra, and prior quantum knowledge *before* a learner can run their first
circuit. The learning curve is vertical. A student who mis-orders two gates
gets a stack trace, not an explanation. Each SDK also has its own API, so
skills do not transfer, and a student cannot easily tell whether a surprising
result is a bug in their circuit or a quirk of the simulator.

**Option B — Visual composers and tutorials.**
Approachable drag-and-drop editors exist, but they are typically limited to
small static circuits, are locked to a single vendor's cloud, and are
disconnected from the curriculum. They show *what* happened without
explaining *why*. Crucially, most cannot express **dynamic circuits** —
mid-circuit measurement with real-time classical feedback — even though that
capability is central to error correction, teleportation and modern
fault-tolerant algorithms, and is where hardware is actually heading.

**The consequences of this gap:**

1. **No feedback loop.** A student sees an unexpected histogram and has no way
   to ask "why?". Debugging is guesswork, and misconceptions harden.
2. **No portability.** Concepts learned in one SDK do not obviously transfer,
   and cross-checking one simulator against another is a manual chore.
3. **Dynamic circuits are effectively untaught.** The most important modern
   primitive is missing from beginner tooling, so learners meet it only in
   research papers.
4. **No measurement of learning.** Educators cannot see who is struggling,
   which concept is failing, or whether a submitted circuit is correct —
   grading quantum circuits by hand does not scale.
5. **Safety and cost.** Naive execution of an unbounded loop or a 30-qubit
   statevector will exhaust memory or burn real hardware credits.

**Problem statement (one sentence for the slide):**

> *Learners have no single environment where they can visually build a quantum
> circuit — including dynamic, mid-circuit-measurement circuits — execute it
> across multiple industry simulators, and receive grounded AI explanations of
> their own results, while educators automatically assess progress and diagnose
> misconceptions.*

> ⚠️ **Do not add "and real quantum hardware" to that sentence.** The qBraid
> adapter is written for hardware, but every result in this document comes from
> simulators. Claiming hardware execution is unsupported by evidence.

**QuantumLearn closes that gap** with one integrated platform: a visual
composer, a multi-backend execution engine, a retrieval-grounded AI tutor
that can only explain *real, stored* results, and an autograding and analytics
layer for instructors.

---

## 2. Proposed Solution

A web platform combining four pillars:

| Pillar | What it does |
|---|---|
| **Build** | Drag-and-drop circuit composer with 15 base gates, 11 controlled aliases, and nested control-flow blocks (if/else, for, while, box) |
| **Run** | One circuit, **six** backends: Qiskit Aer, Cirq, PennyLane, a Qiskit dynamic engine, qBraid cloud, and CUDA-Q (GPU) |
| **Understand** | Gemini-powered AI tutor with RAG over the curriculum; can inspect circuits and explain stored results, but *cannot* run simulations itself |
| **Assess** | Quizzes, coding challenges with automatic grading, **4 games across 10 levels plus a Grover Lab**, concept-level mastery tracking, and an instructor analytics dashboard |

---

## 3. Key Differentiators

1. **Dynamic circuits are first-class.** Mid-circuit measurement, `if/else` on
   classical bits, bounded `while` loops and `for` loops — visually editable,
   correctly simulated, and exportable. Most educational tools cannot express
   these at all.

2. **Cross-backend verification as a teaching tool.** The same circuit runs on
   Aer, Cirq and PennyLane and produces agreeing histograms. Students learn
   that quantum results are *reproducible physics*, not simulator artefacts.

   > ⚠️ **Scope this claim.** These are simulators of the *same physics*.
   > Agreement demonstrates that the transpilation and normalization are
   > correct — it is **not** validation against real hardware.

3. **The AI tutor has no simulation tool — by design.** It can read circuits
   and results already in the database, but it cannot invent numbers. This
   removes an entire class of hallucination: the AI can only explain runs that
   actually happened.

   > ⚠️ **Scope this too.** The AI cannot fabricate a *measurement result*.
   > It can still be wrong about prose. Say "cannot invent a measurement",
   > never "cannot hallucinate".

4. **Phase is shown as colour, not just bar height.** Z, S, T and RZ change a
   state's phase without moving a single count. The histogram can therefore be
   coloured by *relative* phase (global phase removed first), so a learner sees
   two histograms with identical bar heights and different colours — the phase
   information that height alone cannot carry.

5. **Safety limits are architectural, not advisory.** `while` loops are hard
   capped at 32 iterations at the IR level, dynamic circuits at 15 qubits and
   4096 shots, with Celery soft/hard timeouts of 8s/15s. A student cannot hang
   the platform or accidentally spend hardware credits.

6. **OpenQASM 3 as the canonical format.** Circuits are portable in and out of
   the platform; students are not locked into our representation.

7. **Missing capability degrades with an explanation.** A backend with no
   credentials or no GPU does not silently disappear — it reports *why* it is
   unavailable, and the rest of the platform keeps working.

---

## 4. System Architecture

```
┌────────────────────────── React SPA (Vite) — 11 pages ──────────────────────────┐
│  Learn  │  Curriculum  │  Composer  │  Challenges  │  Code Lab                  │
│  Dashboard  │  Games  │  Playground  │  Login  │  Topic detail                  │
│                   └─ shared drag-drop composer grid, built from source           │
└───────────────────────────────┬─────────────────────────────────────────────────┘
                                │ REST (JWT auth), same-origin /api
┌───────────────────────────────▼─────────────────────────────────────────────────┐
│                     FastAPI backend — 41 operations / 38 paths                  │
│  auth │ jobs │ circuits │ QASM3 I/O │ export │ inspect │ backends                │
│  lessons │ quizzes │ challenges │ attempts │ games │ dashboard │ ai               │
└───┬──────────────────┬──────────────────┬──────────────────┬─────────────────────┘
    │                  │                  │                  │
┌───▼────────┐  ┌──────▼───────┐  ┌───────▼────────┐  ┌──────▼─────────────────────┐
│ Circuit IR │  │  Celery +    │  │  Gemini + RAG  │  │  PostgreSQL 16 + pgvector  │
│  + QASM3   │  │  Redis queue │  │  (pgvector)    │  │  14 tables, 8 migrations   │
│   codec    │  │              │  │  1,008 chunks  │  │                            │
└───┬────────┘  └──────┬───────┘  └────────────────┘  └────────────────────────────┘
    │                  │
    │      ┌───────────┴──────────────────────────────────────────────┐
    │      ▼            ▼            ▼         ▼          ▼            ▼
    │  Qiskit Aer     Cirq      PennyLane   Qiskit     qBraid      CUDA-Q
    │  (static)     (static)    (static)   dynamic     (cloud)      (GPU)
    │                                                               ≤28 qubits
    └──── normalize: IR → Qiskit → transpile to {rx, ry, rz, cx} → convert
```

**Execution routing:** dynamic circuits are always routed to the Qiskit
dynamic engine (other backends cannot express runtime control flow). Static
circuits are normalized through a common basis so every backend executes the
*same* program — which is why their histograms agree.

**Backend availability is per-deployment, not fixed.** Four backends run with
no credentials at all. qBraid needs `QBRAID_API_KEY`; CUDA-Q needs an NVIDIA
GPU and the CUDA-Q wheel. Both self-disable with a human-readable reason
rather than failing at run time.

---

## 5. Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React 18 + TypeScript SPA (Vite), with a shared drag-and-drop circuit grid compiled in from source |
| Backend | FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic |
| Async | Celery 5.4 + Redis 7 |
| Database | PostgreSQL 16 + pgvector |
| Quantum | Qiskit 1.2, Qiskit Aer, Cirq, PennyLane, OpenQASM 3, qBraid SDK, CUDA-Q 0.16 |
| AI | Google Gemini (chat + embeddings), RAG over pgvector with keyword fallback |
| Auth | JWT, bcrypt, roles: student / instructor / admin |
| Deploy | Docker Compose (5 services), multi-stage builds |

---

## 6. Feature Detail

### 6.1 Circuit Composer
- **Grid model:** rows = qubits, columns = layers
- **Collision policy:** global auto-insert column (IBM Composer behaviour) —
  dropping a gate onto an occupied cell shifts all operations at that layer
  and beyond to the right, never silently overwriting
- **Gate set:** 15 base gates (`h, x, y, z, s, sdg, t, tdg, sx, id, swap, p,
  rx, ry, rz`) plus 11 controlled aliases (`cx/cnot, ccx/toffoli, mcx, cz, cy,
  cp, crz, cswap/fredkin`) — MCX supports arbitrary control counts
- **Parameters:** restricted grammar — only `pi`, numbers and `+ - * / ( )`.
  Free variables like `theta` are rejected, so every circuit is numerically
  executable the instant Run is pressed
- **Two measurement modes:**
  - *Measure All (Append)* — dynamic-safe, never deletes existing operations
  - *Normalize Terminal Measurement* — top-level only, never touches
    measurements nested inside blocks

### 6.2 Dynamic Circuits
- `if/else` on classical bits, including bitstring comparison `c[0:k] == v`
- `for i in [0..N)` with compile-time constant N
- `while (c[i] == 1)` **hard capped at 32 iterations**
- Nested block editing
- Cirq export ships the circuit *plus* a Python driver script that reproduces
  the control flow — verified to agree with the native engine

### 6.3 AI Tutor
- **RAG:** 67 curriculum lessons chunked into pgvector — **1,008 chunks**
  ingested on startup. Semantic retrieval with keyword fallback; without a
  Gemini key, retrieval runs entirely on the keyword path.
- **Tools:** `get_simulation_result`, `inspect_circuit`, `summarize_circuit`,
  `generate_code_qiskit`, `generate_code_cirq`
- **Deliberately no simulation tool** — the AI explains results that already
  exist in the database, so it cannot fabricate outcomes
- Every answer shows its curriculum sources
- **Without `GEMINI_API_KEY`:** code generation returns a clear 503 and the UI
  shows an explicit explanation rather than failing silently

### 6.4 Assessment & Analytics
- **Quizzes:** MCQ + short answer; answers never sent to the client
- **Coding challenges:** autograded on total-variation distance between the
  observed and target distribution, plus constraints (allowed gates, max
  depth, max qubits, must-be-dynamic)
- **Games:** 4 games across 10 levels, plus a Grover Lab
  | Game | Levels | Teaches |
  |---|---|---|
  | Bell Builder | 4 | All four Bell states. Graded on **fidelity**, because \|Φ+⟩ and \|Φ−⟩ have identical histograms |
  | Open the Vault | 3 | Multi-controlled gates over the complete truth table |
  | Find the Bug | 2 | Repair a broken circuit within an edit budget |
  | Shot Detective | 1 | How many shots a distribution actually needs |
  - **Grover Lab** runs real state-vector maths, not an animation: target
    amplitude grows from 1/64 to **99.66% over 6 iterations**, and falls again
    if over-rotated
  - **Grading tolerance is measured, not guessed.** The Bell tolerance was
    0.12 and failed 12% of *correct* circuits purely from shot noise at 1024
    shots. Widened to 0.25, false failures fell to **0.14%** — while a wrong
    `|00⟩`-only circuit still scores zero.
- **Mastery tracking:** concept tags on lessons and challenges feed
  `user_mastery`; a recommendation endpoint surfaces the weakest tag
- **Instructor dashboard:** progress, completion rates, common errors ranked
  by frequency, weakest concepts across the cohort, per-student view

### 6.5 Authentication & Access Control
- JWT authentication: `/auth/register`, `/auth/login`, `/auth/me`
- bcrypt password hashing
- Three roles: **student / instructor / admin**
- Role-gated endpoints — the instructor dashboard requires instructor or admin
- All AI endpoints require an authenticated session

### 6.6 Personalization & Recommendations
- Concept tags attached to lessons and challenges
- `user_mastery` updated from **both** quiz and challenge outcomes
- Weakest-concept recommendation endpoint drives next-step suggestions in the UI

### 6.7 Code Lab
- Four languages: **Qiskit, Cirq, PennyLane, OpenQASM 3**
- Live diagnostics as you type; static checks catch typos, blocked imports and
  a missing `circuit`, and never run the program to find them
- Execution in a hardened sandbox that blocks filesystem, network and
  subprocesses, covered by escape tests
- `print()` output is shown back for debugging
- Circuits are converted to OpenQASM 3 internally, so an unsupported gate is
  **reported, not silently dropped**

### 6.8 Code Generation & Export
- **OpenQASM 3** — canonical import/export (file upload *or* paste), `.qasm` download
- **Qiskit** `.py` and **Cirq** `.py` source generation
- Dynamic circuits additionally export a **Python control-flow driver script**
  that reproduces `if/else` and capped `while` semantics — verified to agree
  with the native dynamic engine

### 6.9 Curriculum
- **67 lessons · 71 topics · 10 sections**, from Mathematical Foundations
  through Core Theory, Algorithms, NISQ, Error Correction and Hardware
- The registry is the source of truth with **permanent namespaced IDs**, not
  filenames — lessons may be renamed, moved, split or merged without breaking
  links
- Prerequisite graph is acyclic: VQE requires noise, entanglement requires
  Bell, measurement precedes sampling
- Interactive concept demos are embedded beside the lesson text

### 6.10 Visualization
Six complementary views of the same run: histogram, probability table, Bloch
sphere, phase disk, amplitude table, circuit diagram — plus Q-sphere and
density matrices.

**Ideal vs noisy:** T1/T2/readout noise is available on `qiskit_aer` and
`cudaq`. The noise model reproduces `exp(-t/T1)` and `exp(-t/T2)` to **1e-9**,
and clamps T2 to **2·T1** — the physical bound, since
`1/T2 = 1/(2T1) + 1/T_phi`. Clamping to T1 is the common error and we do not
make it. The statevector shown is always the *ideal* state; only the counts
carry noise.

### 6.11 Saved Circuits
- Full CRUD (create / list / fetch / delete), scoped per user

### 6.12 Data Layer
- PostgreSQL 16 + **pgvector** for semantic retrieval
- **Alembic** versioned migrations — 14 tables, 8 revisions, one linear head,
  applied automatically on container startup

### 6.13 Engineering Safeguards
| Control | Value |
|---|---|
| Max static qubits | 20 (24q ≈ 268 MB) |
| Max dynamic qubits | 15 |
| Max dynamic shots | 4096 |
| While-loop cap | 32 iterations |
| Celery soft / hard timeout | 8s / 15s |
| Result caching | `run_hash` per (circuit, engine, shots, mode, user) |
| GPU qubit ceiling | 28 (measured: 2.5 GB at fp32 on a 6141 MiB card) |
| GPU thermal limit | 80 °C, 3 s cooldown between jobs |
| GPU noise ceiling | 11 qubits (density-matrix engine) |

---

### 6.14 Software Components (slide-ready list)

**Frontend / User Interface**
- React 18 + TypeScript single-page application (Vite), 11 pages, served as a
  static bundle behind an `/api` proxy
- Custom drag-and-drop circuit composer, shared into the SPA from source so
  there is one implementation

**Quantum Circuit Composer**
- Drag-and-drop gate placement, global auto-insert-column collision policy
- OpenQASM 3 import (upload or paste) and export
- Controlled gates, Toffoli, arbitrary-control MCX, barriers, parameterized gates
- Nested control-flow block editing

**Circuit Validation Engine**
- Gate and circuit validity checking
- Restricted parameter grammar (`pi`, numbers, `+ - * / ( )`); free variables rejected
- Control-flow and loop validation
- Safety limits and resource constraints

**Quantum Simulation Engine**
- Qiskit Aer, Cirq, PennyLane (static)
- Qiskit Dynamic Engine for `if` / `for` / `while` circuits
- qBraid cloud integration (submit / poll / retrieve)
- CUDA-Q GPU statevector, up to 28 qubits

**Execution & Processing Layer**
- FastAPI backend, 41 REST operations across 38 paths
- Celery + Redis for asynchronous simulation jobs
- Transpilation to a portable basis `{rx, ry, rz, cx}` for backend normalization
- Execution-time, qubit, shot and loop limits

**Authentication & Access Control**
- JWT authentication, bcrypt password hashing
- Role-based access: student / instructor / admin

**Result Management**
- PostgreSQL 16, standardized result JSON
- `run_hash` based caching and result reusability
- Simulation metadata and job lifecycle tracking

**Visualization Engine**
- Measurement histograms and probability tables
- Circuit diagram rendering
- Bloch sphere / state visualization
- Phase-disk visualization, amplitude table
- **Phase-as-colour on histogram bars** — relative phase, global phase removed
- Ideal-vs-noisy comparison under T1/T2/readout

**AI Tutor**
- Google Gemini conversational tutor
- RAG over 1,008 curriculum chunks, pgvector semantic retrieval with keyword fallback
- Tools: `get_simulation_result`, `inspect_circuit`, `summarize_circuit`,
  `generate_code_qiskit`, `generate_code_cirq`
- Explanations grounded in stored results — **no AI-triggered simulation**

**Code Generation & Export**
- OpenQASM 3, Qiskit `.py`, Cirq `.py`
- Dynamic circuits export a Python control-flow driver script

**Code Lab**
- Qiskit, Cirq, PennyLane, OpenQASM 3
- Live diagnostics, static checks, hardened sandbox

**Assessment Engine**
- Interactive quizzes (MCQ + short answer)
- Coding challenges with automated circuit evaluation
- Autograding on total-variation distance plus gate/depth/qubit constraints

**Quantum Games**
- Bell Builder, Open the Vault, Find the Bug, Shot Detective (10 levels)
- Grover Lab with real state-vector maths

**Personalization Engine**
- Concept-tag mastery tracking from quizzes and challenges
- Weakest-concept recommendations

**Analytics & Dashboard**
- Learner progress tracking and performance analytics
- Common-error analysis, instructor dashboard

**Deployment & Infrastructure**
- Docker Compose, 5 services, multi-stage builds
- Alembic versioned migrations (14 tables) applied on startup
- Opt-in GPU override composes CUDA-Q into api and worker

---

## 7. Results / Validation

**Cross-backend agreement** — the same Bell circuit (H then CNOT, 2048 shots)
submitted through `POST /jobs` to each engine:

| Backend | `00` | `11` | `P(odd parity)` |
|---|---|---|---|
| Qiskit Aer | 1018 | 1030 | 0.000 |
| Cirq | 1074 | 974 | 0.000 |
| PennyLane | 1005 | 1043 | 0.000 |

Nothing on `01` or `10` in any run — the expected Bell signature, reproduced
on three independent engines.

Previously recorded (1000 shots, seed 3): Aer 489/511 · Cirq 488/512 ·
PennyLane 502/498. Worst divergence across the suite is **0.025 at 8000
shots**, with each gate sandwiched between Hadamards so that phase-only gates
move the distribution. Grover (2-qubit): `11` at probability **1.000** on all
three. Dynamic circuits: native engine and exported Cirq driver agree
(`{00: 991, 10: 3009}` vs `{00: 1025, 10: 2975}`), within shot noise.

**Noise validation:** clean Bell `P(odd)` = **0.000**; mild (T1=50, T2=30) =
**0.047**; harsh (T1=2, T2=1, readout 0.05) = **0.210**. `exp(-t/T)` matches
to 1e-9, and `T2` clamps to `2·T1` with an explanatory note.

**Scale:**
- **41 REST operations** across 38 paths · **14 tables** · 8 migrations
- **67 lessons / 71 topics / 10 sections** · **1,008 RAG chunks**
- **13,275 lines** of Python across 71 backend modules
- **9,232 lines** of TypeScript across 50 SPA files, plus **2,152 lines** for
  the shared composer grid
- **4 games / 10 levels** + Grover Lab · **11 SPA pages** · **6 backends**

**Automated verification:**
- Backend: **707 passed, 5 skipped** (419 test functions across 32 files)
- Frontend: **16 harness scripts** producing **389 named checks**
- Golden numerics: **4,300 values** compared against NumPy references at
  **1e-9** (190 quantum, 804 demo, 3,306 Grover)

> ⚠️ **There is no CI.** Every suite above is run manually. State that plainly
> rather than implying automation.

**Deployment:** verified end-to-end under Docker Compose — Postgres, Redis,
Celery worker, FastAPI and the SPA, with Alembic migrations applied on
startup. Verified by booting the API and running real jobs through it.

---

## 8. Slide Deck Structure

The hackathon deck is **16 slides** across four parts, with Part II (the
website) deliberately the largest:

| Part | Slides | Covers |
|---|---|---|
| I — Problem and solution | 1–4 | Title, problem statement, objectives, proposed solution |
| II — Website and integrated tasks | 5–11 | Navigation, curriculum, composer, visualization, games, Code Lab, progress |
| III — Architecture and implementation | 12–14 | System architecture, engineering decisions, testing |
| IV — Evaluation and conclusion | 15–16 | Limitations, conclusion and live demo |

The full generation prompt, the fact pack it is allowed to use, and the
anti-hallucination rules live in **`docs/ppt/HACKATHON_PPT_PROMPT.md`**.
Supporting material: `MASTER_PROJECT_DOSSIER.md`, `PPT_BLUEPRINT.md`,
`TECHNICAL_QA.md`, `ARCHITECTURE_DIAGRAMS.md`, `DEMO_GUIDE.md`,
`BRANCH_AUDIT.md`.

---

## 9. Limitations

State these before a judge finds them.

1. **No CI.** All tests are run by hand.
2. **Composer keyboard accessibility.** The drag tiles in the composer grid
   have `draggable` and `onClick` but no `role`, `tabIndex` or `onKeyDown`.
   Tracked, not fixed.
3. **AI features need a key.** Without `GEMINI_API_KEY`, retrieval falls back
   to keyword search and code generation returns a clear 503. The rest of the
   platform is unaffected.
4. **The noise model is a parameterised configuration of Aer's
   `thermal_relaxation_error`.** It has no crosstalk, leakage or correlated
   errors. Do not describe it as a new noise model.
5. **Cross-backend agreement is between simulators**, not against hardware.
6. **Registry/DB divergence.** 54 topics are `draft` in the curriculum
   registry but published in the database. This is deliberate, it is why
   learners see 71 rather than 17, and two tests depend on it.

---

## 10. Future Scope

**In progress this week — not yet shipped:**

- **Noise Lab** — T1/T2/readout exploration, Kraus channels, ideal-vs-noisy
  side by side, zero-noise extrapolation, probabilistic error cancellation,
  readout correction. Builds on the existing `NoiseParams` and `clamped()`.
  *Known risk: the plan specifies T1/T2 in nanoseconds while the codebase uses
  microseconds.*
- **Smart Composer** — circuit reduction via identities (H²=I, adjacent-inverse
  cancellation, SWAP as three CNOTs) with verification, a circuit-diff view,
  and resource estimation. *Known risk: Mode 2 targets a `coupling_map` that no
  backend currently exposes.*

**Planned:**

- Real QPU execution (qBraid free simulators today; hardware is a config change)
- Practice vs exam mode, as genuinely distinct products
- Spaced repetition and concept checkpoints gating progression
- Collaborative/classroom mode with a live instructor view
- Expanded curriculum: QFT, Shor, error-correction codes
- Searchable glossary and formula library, reusing the result visualisations
  as teaching components
- Algorithm comparison (query count, gate count, depth) and classical-vs-quantum
  comparison with equivalent problem definitions
- Edit-level debugging traces: time-to-first-correct-circuit
- CI

---

## 11. Corrections made to earlier drafts

Recorded so the wrong figures do not re-enter.

| Was | Now | Why |
|---|---|---|
| 29 endpoints | **41 operations / 38 paths** | Counted from the running app's OpenAPI document. A grep for decorators undercounts routes assembled at mount time. |
| 23 chunks, 8 lessons | **1,008 chunks, 67 lessons** | Printed by the ingestion step on startup. |
| 87 automated tests | **707 backend + 389 frontend checks + 4,300 golden values** | The old figure predates most of the suite. |
| ~7,800 lines Python | **13,275** | Measured across 71 backend modules. |
| ~1,500 lines TypeScript | **9,232** (+2,152 composer) | Measured across 50 SPA files. |
| Five backends | **Six** | CUDA-Q was missing. |
| "real quantum cloud hardware" | removed | Only qBraid *simulators* have been run. |
| — | Games, Code Lab, curriculum, phase-colour, ideal-vs-noisy, GPU limits | Sections that did not exist and do now. |
| 12-slide structure | **16-slide structure** | Superseded by `docs/ppt/HACKATHON_PPT_PROMPT.md`. |
