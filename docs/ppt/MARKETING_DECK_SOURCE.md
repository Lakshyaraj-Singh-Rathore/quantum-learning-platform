# QuantumLearnAI — Marketing Deck Source Data

**Status:** every number below was measured in this repo, not quoted from docs.
**Verified against:** `main` @ `9bfad8c` (Phase 9B).
**Two rules this deck obeys:** nothing is claimed that isn't in shipped code, and
everything not yet built is labelled ROADMAP.

> **Read this before editing.** The previous version of this document described a
> Streamlit app. Streamlit is gone — deleted as the P9 cutover. Its features were
> **ported into the React SPA**, not lost. Any line below still saying Streamlit,
> `frontend/lib/viz.py`, `frontend/pages/`, or `Home.py` is wrong.

---

## Corrections made to the previous draft

| Claim in old draft | Reality |
|---|---|
| 7 Streamlit pages | **13 React SPA routes / 10 navigation items** across 4 sections; Streamlit deleted |
| `frontend/lib/viz.py`, phase colour | File deleted; **feature ported** to `ResultsViews.tsx:235` — `hsl(phase × 180/π, 65%, 55%)` |
| 519 frontend tests | **389 named checks** across 16 harnesses + **4,300 golden values** @1e-9 + **vision test suites** (`vision:embedded`, `qml:vision`, `test:portal`) |
| 982+ tests total | Backend **1358 passed / 5 skipped** (1304 base + 54 limit sweeps) + the above |
| 41 endpoints | **66** OpenAPI paths (70 operations) across 10 routers |
| Code Lab, 6 frameworks | **4**: Qiskit, Cirq, PennyLane, OpenQASM 3 |
| "Streamlit + FastAPI + Celery" | FastAPI + Celery + **React SPA** |

---

# SLIDE 1 — Title

**QuantumLearnAI**
*Build it visually. Run it on six engines that agree. Ask AI why — and get an answer it cannot invent.*

One `make up`. No quantum hardware. No cloud account. No per-student cost.

---

# SLIDE 2 — The Problem

Learners are forced to choose between two broken halves.

**The SDK path** (Qiskit / Cirq / PennyLane)
- Vertical learning curve before the first concept lands
- A stack trace, not an explanation
- No portability — learn one vendor, relearn for the next
- No cross-check: one simulator's word is the only word

**The visual-composer path**
- Single vendor, small static circuits
- **Cannot express dynamic circuits** — mid-circuit measurement plus classical feedback — which is precisely what teleportation, error correction and fault-tolerance rest on

**The consequence**
- No feedback loop between "what I built" and "why it's wrong"
- Dynamic circuits effectively untaught
- Grading quantum circuits by hand does not scale past one classroom
- A naive 30-qubit statevector OOMs, or burns real hardware credits learning nothing

---

# SLIDE 3 — Solution: Four Pillars

**BUILD** — Drag-and-drop composer, Qudit Lab ($d \in \{2,3,4,5\}$), Quantum ML Lab (VQC, Quantum Regression, Quantum Kernels, Hybrid PyTorch), and embedded Noise Lab & Smart Composer. Rows are qubits/qudits, columns are layers. Collision handling does a global auto-insert-column (IBM Composer behaviour): dropping on an occupied cell shifts right, never overwrites.

**RUN** — One circuit, six backends. See next slide.

**UNDERSTAND** — Gemini tutor with RAG over the curriculum. **Five tools only, and deliberately no simulation tool.** It reads results that already executed; it cannot produce a number itself.

**ASSESS** — Quizzes (MCQ + short answer; correct answers never sent to the client) and coding challenges autograded on total-variation distance plus structural constraints. Per-concept mastery. Instructor dashboard live from the database.

---

# SLIDE 4 — Six Backends, One Circuit *(core differentiator)*

**Shipped, in `backend/app/quantum/backends/`:**

| Adapter | What it is |
|---|---|
| `qiskit_aer.py` | Static statevector + noise |
| `cirq_sim.py` | Static |
| `pennylane_sim.py` | Static |
| `dynamic_qiskit.py` | `if` / `for` / `while` engine |
| `qbraid_sim.py` | Cloud hardware & simulators |
| `cudaq_sim.py` | GPU statevector to 28 qubits |

**Why they agree — this is the point.** IR → Qiskit → transpile to the portable basis `{rx, ry, rz, cx}` → convert to target. Every backend executes *the same program*. Histograms agree because it's physics, not simulator opinion.

**Measured agreement, Bell state, 1000 shots, seed 3:**
- Qiskit Aer 489/511 · Cirq 488/512 · PennyLane 502/498
- Worst divergence **0.025 at 8000 shots** — each gate sandwiched between Hadamards, so phase-only gates move the distribution
- Grover 2-qubit: `11` with probability **1.000 on all three**

**Dynamic circuits verified:** native engine vs exported Cirq driver — `{00:991, 10:3009}` vs `{00:1025, 10:2975}`, within shot noise.

**Self-disable with explanation, not a silent grey-out:**
- qBraid: "Missing credentials" when no key
- CUDA-Q: disabled with the reason "no usable GPU", not just a dead button
- `make up` auto-adds the GPU override if Docker sees a GPU, else runs the plain stack. No flags to remember.

**Safety limits are architectural, not advisory:**
- Max static 20 qubits (24q ≈ 268 MB) · max dynamic 15 qubits · 4096 shots
- `while` hard-capped at **32 iterations at the IR level**
- Celery soft 8s / hard 15s
- `run_hash` caching per (circuit, engine, shots, mode, user)

**Nowhere else:** cross-backend verification used as *pedagogy*; dynamic circuits as a first-class editable object; GPU auto-detect that degrades with an explanation.

---

# SLIDE 5 — AI That Cannot Hallucinate a Measurement

**Models** (from `.env.example`): `GEMINI_CHAT_MODEL`, `GEMINI_EMBED_MODEL`.

**The architecture — this is the claim that matters:**

```
Computation  →  deterministic engines  →  PostgreSQL
Explanation  →  Gemini, reading that record
```

**Five tools only:** `get_simulation_result`, `inspect_circuit`, `summarize_circuit`, `generate_code_qiskit`, `generate_code_cirq`.

There is **no simulation tool**. The AI can read circuits and results that are already in the database. It cannot produce a number itself. A hallucinated histogram is impossible **by architecture**, not by prompting.

- Every answer cites curriculum sources; the UI shows them
- Retrieval: pgvector semantic search, with keyword fallback when embeddings are unavailable
- Corpus: **67 lesson files ≈ 1,003,000 characters**, fence-aware chunker, **1,008** chunks
- Without an API key: retrieval falls back to keyword search, and Code Lab shows a yellow box — *"AI generation is unavailable — GEMINI_API_KEY is not set. Add it to .env and restart api container"* — wired with `aria-describedby`, so it is announced to screen readers rather than failing silently

---

# SLIDE 6 — See the Physics: Six Views of One Run

**Six complementary views of the same run** (`frontend/web/src/components/results/`):
Histogram · probability table · Bloch sphere · phase disk · amplitude table · circuit diagram — plus Q-sphere and density matrices.

### The headline: phase shown as colour

A histogram shows counts. It cannot show phase — and Z, S, T and RZ change phase **without moving a single count**.

So we colour the bars by relative phase.

- Global phase removed first — a statevector is only defined up to overall phase
- `ResultsViews.tsx:235` — *"Colour bars by relative phase"*, rendered as `hsl(phase × 180/π, 65%, 55%)`
- Same bars, same heights, different colours after a Z gate

**The learner sees, in one glance:** phase is invisible in bar height and visible in bar colour. This is the single most-photogenic feature in the product — lead with a screenshot of two histograms, identical heights, different colours.

### Ideal vs noisy

- T1 / T2 / readout noise on `qiskit_aer` and `cudaq`
- Metrics: entanglement entropy separates product from Bell; the timeline tracks entanglement appearing at the CNOT and stopping after measurement
- Reproduces `exp(-t/T1)` and `exp(-t/T2)` to **1e-9**
- **Clamps T2 to 2·T1, not T1** — the physical bound is `1/T2 = 1/(2T1) + 1/T_phi`. Clamping to T1 is the common error, and we don't make it
- On CUDA-Q the same `NoiseParams` become `AmplitudeDampingChannel` and `PhaseFlipChannel`, with readout as bit-flip on `mz`, run on the density-matrix engine
- Statevector shown is **ideal**; only the counts carry noise — the UI states this rather than leaking one into the other

### Noise Lab & Smart Composer (Shipped)

- **Noise Lab (`/composer` bottom panel):** T1/T2/readout noise modeling, Kraus operator channels, side-by-side ideal vs noisy distribution, zero-noise extrapolation (ZNE) and readout error mitigation.
- **Smart Composer (`/composer` smart panel):** Automated circuit identity optimization (H²=I, adjacent inverse cancellation, SWAP decomposition), matrix equivalence verification, circuit diff vs target reference, and depth/gate resource estimation. Verified across 4 viewports with 48/48 automated vision checks (`vision:embedded`).

---

# SLIDE 7 — One Integrated Platform

**13 SPA routes across 10 navigation items (4 sections):**
- **Study:** Learn (`/learn`), Curriculum (`/curriculum`, `/curriculum/topic/:topicId`), Playground (`/playground`)
- **Build & Simulate:** Composer (`/composer` with embedded Noise Lab & Smart Composer), Qudit Lab (Beta) (`/qudit-lab`), Code Lab (`/codelab`), Quantum ML Lab (`/qml-lab`, flag-gated)
- **Practice:** Challenges (`/challenges`), Games (`/games`)
- **Insights:** Dashboard (`/dashboard`)
- **Auth & System:** Home (`/`), Login (`/login`), Register (`/register`)

### Qudit Lab (Shipped)
- Multilevel quantum simulation across dimensions $d \in \{2, 3, 4, 5\}$ with native qudit statevector backend
- Generalised Pauli/Gell-Mann gates ($X_d, Z_d, H_d$, embedded single-qudit transitions, entangling gates)
- Full density matrix inspector: populations & coherences, purity, von Neumann entropy
- Validated with negative-path limit sweeps and multi-viewport responsive layout

### Quantum ML Lab (Shipped, flag-gated `qml_enabled`)
- 4 production quantum algorithms: Variational Quantum Classifier (VQC), Quantum Regression, Quantum Kernels (Gram matrix evaluation), and Hybrid PyTorch QNN (jointly differentiated circuit + classical layer)
- Parameter-shift and adjoint differentiation, live epoch training stream via Celery async dispatch
- Decision boundary visualization, interactive dataset selectors (moons, circles, spirals, sine, damped cosine), and signed R² display
- Audited with headless Chromium vision verification (`qml:vision`, 66 PASS / 0 FAIL)

**Curriculum — 67 lessons, 71 topics, 10 sections**
- Sections span Mathematical Foundations → Core Theory → Intro QC → Qiskit → Algorithms → Advanced Gates → Variational NISQ → Error Correction → Hardware → Communication
- Registry is the single source of truth: namespaced permanent IDs, **not** filenames. Lessons may be renamed, moved, split or merged and IDs don't change
- Many-to-many, actually used: one lesson teaches several topics; one topic is taught by several lessons
- Prerequisites acyclic — VQE requires noise, entanglement requires Bell, measurement precedes sampling

**Try-it-yourself demos embedded beside the text** — superposition, amplitude vs probability, measurement collapse, interference, Bloch sphere, |+⟩ vs |−⟩, exponential state space and Qiskit bit ordering. Six lessons embed the real composer.

**Personalisation** — concept tags on lessons and challenges feed `user_mastery`; the recommendation endpoint surfaces your weakest tag.

**Auth** — JWT, bcrypt, roles student / instructor / admin. Instructor dashboard is role-gated; all AI endpoints require auth.

**Data** — PostgreSQL 16 + pgvector, **15 tables**, 10 Alembic migrations applied automatically on container startup.

**Front-end engineering note worth one line:** the sidebar push/overlay contract is enforced by an automated harness (`push:overlay`), not by eyeballing it.

---

# SLIDE 8 — Quantum Games: 10 Levels, 4 Games + Grover Lab

All shipped, all autograded.

| Game | Levels | Teaches |
|---|---|---|
| 🔗 **Bell Builder** | 4 | All four Bell states. Graded on **fidelity**, because \|Φ+⟩ and \|Φ−⟩ have identical histograms — the phase difference is invisible on counts |
| 🔐 **Open the Vault** | 3 | Multi-controlled gates, graded over the complete truth table, one to three controls |
| 🐛 **Find the Bug** | 2 | Repair a broken circuit within an edit budget. One-gate fix = one edit. Over budget is penalised, not zeroed. A broken circuit scores zero however few edits you spent |
| 🎲 **Shot Detective** | 1 | Discover how many shots a distribution actually needs. Fewer shots scores higher *when accurate*; an inaccurate sample scores zero |

**Grover Lab — real state-vector maths, not an animation.** Watch the target amplitude grow from 1/64 to **99.66% over 6 iterations**, and fall again if you over-rotate. Superposition is detected, not guessed. Game pass threshold is exactly 1.

**Grading:** behavioural score (total-variation distance vs target) + structural constraints (allowed gates, max depth, max qubits, must-be-dynamic) + feedback naming *which* constraint failed + mastery update.

**The statistical care is the brag:** the Bell tolerance was 0.12 and failed 12% of correct circuits purely from shot noise at 1024 shots. Widened to 0.25, false failures fell to **0.14%** — while a wrong `|00⟩`-only circuit still scores zero.

---

# SLIDE 9 — The Qiskit Spine *(dedicated technical slide)*

Qiskit is the pivot, not one option among six.

**IR design** — rows = qubits, columns = layers. Collision = global auto-insert-column.
**15 base gates:** `h x y z s sdg t tdg sx id swap p rx ry rz`
**11 controlled aliases:** `cx/cnot ccx/toffoli mcx cz cy cp crz cswap/fredkin`, MCX with arbitrary control counts.
**Parameter grammar is restricted:** only `pi`, numbers and `+ - * / ( )`. Free variables like `theta` are rejected — so every circuit is numerically executable the instant it's drawn.

**Two measurement modes** — Measure All (append, dynamic-safe, never deletes) and Normalize Terminal Measurement (top-level only, never touches nested blocks).

**The pipeline:** IR → Qiskit `QuantumCircuit` → transpile to `{rx, ry, rz, cx}` → convert to Cirq / PennyLane / qBraid / CUDA-Q.

**Dynamic circuits in Qiskit:** `if/else` on classical bits including bitstring comparison `c[0:k]==v`; `for i in [0..N)` with compile-time constant N; `while (c[i]==1)` hard-capped at 32 **at the IR level**. Nested block editing.

**Code snippet for the slide:**
```python
from qiskit import QuantumCircuit
circuit = QuantumCircuit(2, 2)
circuit.h(0)
circuit.cx(0, 1)
circuit.measure([0, 1], [0, 1])
```

**Correctness is verified, not assumed:**
- Every gate compared against a hand-written closed-form matrix, up to global phase
- Identities: S²=Z, T²=S, SX²=X, S†=S⁻¹, XYZ=iI
- Rotations match `exp(-iθP/2)` at five angles
- Multi-controlled checked over the full truth table, one to three controls
- Bloch vectors verified against Pauli traces; six cardinal states round-trip exactly
- QASM3 round-trips preserve behaviour
- Known-answer runs: Bell, GHZ, Deutsch-Jozsa both branches, Grover certainty

**Code Lab (4 languages):** Qiskit, Cirq, PennyLane, OpenQASM 3.
Live diagnostics as you type. Static checks catch typos, blocked imports and a missing `circuit` — never runs the program. Execution in a hardened sandbox that blocks filesystem, network and subprocesses, covered by escape tests. `print()` output is shown back for debugging. Circuits are converted to OpenQASM 3 internally, so an unsupported gate is **reported, not silently dropped**.

---

# SLIDE 10 — What You Will Not Find Elsewhere

| Feature | Why it's rare |
|---|---|
| **Dynamic circuits, first-class** | Visually editable, correctly simulated, exportable. Most educational tools cannot express them at all |
| **Cross-backend verification as teaching** | Same circuit on Aer / Cirq / PennyLane agreeing teaches reproducibility and transfers skills across SDKs |
| **AI with no simulation tool** | 5 tools only. A hallucinated measurement is impossible by architecture, not by prompt discipline |
| **Phase as bar colour** | Z / S / T / RZ change phase without moving counts — same heights, different colours |
| **Ideal vs noisy, with the physics right** | T2 clamped to 2·T1 (not T1), `exp(-t/T)` to 1e-9, ideal statevector kept distinct from noisy counts |
| **Limits that can't be argued with** | while=32, dynamic 15q, 4096 shots, 8s/15s — enforced, not advised |
| **OpenQASM 3 canonical in/out** | Import, export, paste, download. Not locked to one vendor |
| **Autograding with statistical care** | TVD + gate/depth/qubit constraints; tolerance tuned against measured false-failure rates |
| **Grover Lab: real maths** | 1/64 → 99.66% over 6 iterations, and falls if you over-rotate |
| **Degrades with an explanation** | Missing GPU or credentials produces a sentence saying why, not a dead button |
| **Instructor dashboard, live from DB** | Completion rate, pass rate, common errors ranked by frequency, weakest concepts averaged by tag, per-student |
| **Qudit simulation ($d=2..5$)** | Native qudit statevector simulation, Gell-Mann basis, density matrix inspection |
| **Quantum Machine Learning Lab** | 4 algorithms (VQC, QNN, Kernel, Regression) with live training stream, parameter-shift/adjoint gradients, decision boundaries |
| **Smart Composer & Noise Lab** | Circuit equivalence reduction + real T1/T2/readout noise modeling embedded in the composer workflow |

**The debugging loop is the product.** Wrong answer → inspect → understand → modify → rerun, instead of wrong answer → stuck. Validator, Inspector, Autograder and AI tutor are four layers of the same loop.

---

# SLIDE 11 — Results & Validation

**Agreement:** Bell 1000 shots seed 3 — Aer 489/511, Cirq 488/512, PennyLane 502/498. Worst divergence 0.025 at 8000 shots. Grover 2-qubit `11` at probability 1.000 on all three. Dynamic native vs Cirq driver within shot noise.

**Scale:**
- **66 OpenAPI endpoints (70 operations)** across 10 routers · **15 tables** · 10 Alembic migrations
- 15 base gates / 11 controlled aliases + qudit gate library ($d \in \{2,3,4,5\}$)
- 6 backends (5 static incl. CUDA-Q GPU, + 1 dynamic engine) + qudit statevector engine
- **67 lessons · 71 topics · 10 sections** · **1,008** RAG chunks
- 6+ visualisation modes + qudit density matrix inspector + QML decision boundary & loss landscape
- **Backend 1358 passed / 5 skipped** (1304 base + 54 limit sweeps) · **frontend 41+ harnesses & vision suites** (including `qml:vision`, `test:portal`, `vision:embedded`, `viewport`, `render:*`) · **4,300 golden values agreeing with numpy at 1e-9**

**Deployment:** Docker Compose — Postgres, Redis, Celery worker, FastAPI, React. Migrations applied on startup. End-to-end verified.

**Landed in the final sprint:** sidebar push via CSS peer (no re-render stutter), overlay composer, and Code Lab's AI-disabled explanation with `aria-describedby`.

---

# SLIDE 12 — Impact Statement

> Quantum computing has a talent bottleneck: tools that teach can't run real circuits, and tools that run assume you already know quantum.
>
> QuantumLearn is one platform where a student builds a circuit visually, runs it on simulation engines that all agree, sees six views of what the state is actually doing, and asks an AI tutor why — an AI that is architecturally incapable of inventing the result, because it can only read runs that really executed. Meanwhile the instructor sees exactly which concept the class is failing.
>
> No quantum hardware. No cloud account. One `docker compose up`.

---

# SLIDE 13 — ROADMAP

> **Label this slide "Roadmap" and grey it out. None of the below is shipped.**
> Do not merge any of it into the claims above.

### Further out

| Item | Note |
|---|---|
| Real QPU execution | qBraid gives free simulators today; hardware is a config change |
| Practice vs exam mode | Genuinely distinct: unlimited hints vs timed and limited |
| Spaced repetition & checkpoints | Concept gates on progression |
| Classroom / collaborative mode | Live instructor view |
| Expanded curriculum | QFT, Shor, error-correction codes |
| Seven empty sections | Authoring, not restructuring — maths foundations first, highest leverage |
| Searchable glossary & formula library | Reuse the result visualisations as teaching components |
| Algorithm comparison | Query count, gate count, depth; classical-vs-quantum with equivalent problem definitions |
| Edit-level debugging traces | Time-to-first-correct-circuit; `analytics_events` table exists but is not yet written to |

### Honest gaps — say these before a judge finds them

1. **No CI.** The 1358 backend tests and 41+ frontend harnesses run by hand.
2. **Composer palette keyboard access.** The drag tiles at `Composer.tsx:439-446` have `draggable` and `onClick` but no `role`, `tabIndex` or `onKeyDown`. Tracked, not fixed.
3. **Registry/DB divergence.** 54 topics are `draft` in `curriculum.py` but published in the DB — deliberate, documented, and two tests depend on it. If asked, this is a design decision, not a bug.
4. **AI features need a key.** Without `GEMINI_API_KEY`, retrieval falls back to keyword search and code generation returns a clear 503. The app is fully usable; the AI pillar is not.

---

## Numbers — use these, they are measured

| Metric | Value |
|---|---|
| Backend tests | **1358 passed / 5 skipped** (1304 baseline + 54 negative-path limit sweeps) |
| Frontend harnesses | **41+ scripts & vision suites** (including `vision:embedded`, `qml:vision`, `test:portal`, `render:*`) + **4,300 golden values** @1e-9 |
| Endpoints | **66** OpenAPI paths (70 operations) across 10 routers |
| Tables | **15**, 10 Alembic migrations, one linear head `j5e8f1a4b7c2` |
| Backends | **6** adapters + qudit statevector engine |
| Gates | **15** base + **11** controlled aliases + qudit gate library ($d \in \{2,3,4,5\}$) |
| Lessons / topics / sections | **67 / 71 / 10** |
| Content volume | **1,003,423 characters**, **344** cross-lesson links |
| Games | **4** games, **10** levels, + Grover Lab |
| Qubit & dimension limits | static **20q**, dynamic **15q**, QML **8q**, qudit $d \in \{2..5\}$, while-cap **32**, shots **4096** |
| Code Lab languages | **4**: Qiskit, Cirq, PennyLane, OpenQASM 3 |
| SPA routes / Nav items | **13 routes / 10 nav items** across 4 sections |
| Docker services | **5**: Postgres, Redis, Celery worker, FastAPI, React (plus GPU overlay & `--profile qml`) |
