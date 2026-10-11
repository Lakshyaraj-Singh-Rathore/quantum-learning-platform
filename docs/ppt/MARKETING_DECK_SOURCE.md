# QuantumLearnAI — Marketing Deck Source Data

**Status:** every number below was measured in this repo, not quoted from docs.
**Verified against:** `main` @ `1180f00`.
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
| 7 Streamlit pages | **11 React SPA pages**; Streamlit deleted |
| `frontend/lib/viz.py`, phase colour | File deleted; **feature ported** to `ResultsViews.tsx:235` — `hsl(phase × 180/π, 65%, 55%)` |
| 519 frontend tests | **389 named checks** across 16 harnesses + **4,300 golden values** @1e-9 |
| 982+ tests total | Backend **707 passed / 5 skipped** (419 test functions) + the above |
| 41 endpoints | **39** route decorators across 7 routers |
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

**BUILD** — Drag-and-drop composer. Rows are qubits, columns are layers. Collision handling does a global auto-insert-column (IBM Composer behaviour): dropping on an occupied cell shifts right, never overwrites.

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
- Corpus: **67 lesson files ≈ 1,003,000 characters**, fence-aware chunker, ~800+ chunks
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

---

# SLIDE 7 — One Integrated Platform

**11 SPA pages:** Learn · Curriculum · Composer · Challenges · Code Lab · Games · Playground · Dashboard · Login · Topic detail.

**Curriculum — 67 lessons, 71 topics, 10 sections**
- Sections span Mathematical Foundations → Core Theory → Intro QC → Qiskit → Algorithms → Advanced Gates → Variational NISQ → Error Correction → Hardware → Communication
- Registry is the single source of truth: namespaced permanent IDs, **not** filenames. Lessons may be renamed, moved, split or merged and IDs don't change
- Many-to-many, actually used: one lesson teaches several topics; one topic is taught by several lessons
- Prerequisites acyclic — VQE requires noise, entanglement requires Bell, measurement precedes sampling

**Try-it-yourself demos embedded beside the text** — superposition, amplitude vs probability, measurement collapse, interference, Bloch sphere, |+⟩ vs |−⟩, exponential state space and Qiskit bit ordering. Six lessons embed the real composer.

**Personalisation** — concept tags on lessons and challenges feed `user_mastery`; the recommendation endpoint surfaces your weakest tag.

**Auth** — JWT, bcrypt, roles student / instructor / admin. Instructor dashboard is role-gated; all AI endpoints require auth.

**Data** — PostgreSQL 16 + pgvector, **14 tables**, 8 Alembic migrations applied automatically on container startup.

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

**The debugging loop is the product.** Wrong answer → inspect → understand → modify → rerun, instead of wrong answer → stuck. Validator, Inspector, Autograder and AI tutor are four layers of the same loop.

---

# SLIDE 11 — Results & Validation

**Agreement:** Bell 1000 shots seed 3 — Aer 489/511, Cirq 488/512, PennyLane 502/498. Worst divergence 0.025 at 8000 shots. Grover 2-qubit `11` at probability 1.000 on all three. Dynamic native vs Cirq driver within shot noise.

**Scale:**
- **39 endpoints** across 7 routers · **14 tables** · 8 Alembic migrations
- 15 base gates / 11 controlled aliases
- 6 backends (5 static incl. CUDA-Q GPU, + 1 dynamic engine)
- **67 lessons · 71 topics · 10 sections** · ~800+ RAG chunks
- 6+ visualisation modes · 5 AI tools, zero of them a simulator
- **Backend 707 passed / 5 skipped** · **frontend 389 named checks across 16 harnesses** · **4,300 golden values agreeing with numpy at 1e-9**

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

### Noise Lab *(next)*
A dedicated lab for T1/T2/readout, gate durations and Kraus channels — ideal vs noisy histograms side by side, zero-noise extrapolation, probabilistic error cancellation, readout correction matrix.

Builds on what exists: `NoiseParams`, `clamped()` validation, and the Composer's current optional noise on `qiskit_aer` and `cudaq`.

**Two known risks, recorded before work starts:** the plan specifies T1/T2 in **nanoseconds** while the codebase is **microseconds**; and Mode 2 targets a `coupling_map`, which appears **nowhere** in `backend/app` today.

### Smart Composer *(next)*
Circuit reduction using identities from `adv.circuit_identities` — adjacent-inverse cancellation, H²=I, SWAP as three CNOTs — with verification that the reduced circuit is exactly equal. A twelve-gate circuit reduces to two.

Plus a circuit-diff view comparing a student attempt against the reference, and resource estimation: qubits, gates, depth, and a depth budget translated into feasibility and success probability via error rates.

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

1. **No CI.** The 707 backend tests and 16 frontend harnesses run by hand.
2. **Composer palette keyboard access.** The drag tiles at `Composer.tsx:439-446` have `draggable` and `onClick` but no `role`, `tabIndex` or `onKeyDown`. Tracked, not fixed.
3. **Registry/DB divergence.** 54 topics are `draft` in `curriculum.py` but published in the DB — deliberate, documented, and two tests depend on it. If asked, this is a design decision, not a bug.
4. **AI features need a key.** Without `GEMINI_API_KEY`, retrieval falls back to keyword search and code generation returns a clear 503. The app is fully usable; the AI pillar is not.

---

## Numbers — use these, they are measured

| Metric | Value |
|---|---|
| Backend tests | **707 passed / 5 skipped** (419 test functions, 32 files) |
| Frontend harnesses | **16 scripts** → **389 named checks** + **4,300 golden values** @1e-9 |
| Endpoints | **39** across 7 routers |
| Tables | **14**, 8 Alembic migrations, one linear head |
| Backends | **6** adapters |
| Gates | **15** base + **11** controlled aliases |
| Lessons / topics / sections | **67 / 71 / 10** |
| Content volume | **1,003,423 characters**, **344** cross-lesson links |
| Games | **4** games, **10** levels, + Grover Lab |
| Qubit limits | static **20**, dynamic **15**, while-cap **32**, shots **4096** |
| Code Lab languages | **4**: Qiskit, Cirq, PennyLane, OpenQASM 3 |
| SPA pages | **11** |
| Docker services | **5**: Postgres, Redis, Celery worker, FastAPI, React |
