# Implementation Audit — QuantumLearnAI

Verified against the repository on the `arena/01a0d874-quantum-learning-platform`
branch at **commit `7ee6c01`**. Every claim below was checked against the code or
against a test run, not recalled from a previous report.

This is the Phase 0 deliverable requested by the master implementation prompt.
It deliberately precedes any curriculum restructuring: the restructuring asks
for prerequisite graphs, difficulty levels, and mastery integration, and none
of those can be built correctly until it is known what the platform actually
stores today.

---

## 1. Verified project structure

```
quantum-learning-platform/
├── backend/          FastAPI application, SQLAlchemy models, Celery tasks
├── frontend/         Streamlit application (pages/, lib/) — live, frozen from P0
├── frontend/web/     React SPA — the replacement front end
├── frontend/circuit_composer/frontend/src/
│                     The drag-and-drop grid. SHARED SOURCE: both hosts build it.
├── content/          13 markdown lessons — the entire learning corpus
├── docs/             Plans, roadmap, this audit
├── samples/, reports/, scripts/
└── docker-compose.yml (+ .gpu, .webdev)
```

## 2. Architecture and technology stack (verified)

| Layer | What is actually there |
|---|---|
| Backend | FastAPI, SQLAlchemy 2.x (`Mapped`/`mapped_column`), Pydantic v2 |
| Async | Celery + Redis. **Not available in this sandbox** — submissions fail with `Could not enqueue job: Error -2 connecting to redis:6379`. Graded passes are therefore unverified here. |
| Database | PostgreSQL in compose; SQLite for the development/test setup |
| Frontend | Streamlit (live) **and** React + Vite + TypeScript + Tailwind (newer) |
| Quantum | Qiskit + Aer, Cirq, PennyLane, CUDA-Q. Backend resolution in `backend/app/quantum/backends/` |
| AI | Gemini + RAG (`backend/app/ai/rag.py`), embeddings on `ContentChunk` |
| Visualisation | Bloch sphere, density matrix, phase disk, Q-sphere, histogram |
| Testing | pytest (backend + frontend), plus `tsx` render/golden harnesses in `frontend/web/scripts/` |

The shared composer source is important: `frontend/web` imports it as `@composer`
via a Vite alias, and Streamlit's component builds the same file. Any change to
the grid lands in **both** applications.

## 3. Current learning content — the core finding

**13 lessons, all plain markdown in `content/`. No front matter at all.**

| # | File | Words | Track | Has demos |
|---|---|---|---|---|
| 01 | `01_qubits` | 430 | theory | yes (4) |
| 02 | `02_gates` | 527 | theory | yes (3) |
| 03 | `03_entanglement` | 265 | theory | yes (1) |
| 04 | `04_measurement` | 528 | theory | yes (2) |
| 05 | `05_deutsch_jozsa` | 345 | theory | yes (1) |
| 06 | `06_grover` | 372 | theory | yes (1) |
| 07 | `07_vqe_qaoa` | 374 | theory | **none** |
| 08 | `08_dynamic_circuits` | 515 | theory | **none** |
| 09 | `09_quantum_noise` | 1081 | theory (explicit) | **none** |
| 10 | `10_gates_bootcamp` | 1342 | circuit | yes (3) |
| 11 | `11_bell_states` | 584 | circuit | yes (3) |
| 12 | `12_control_flow` | 769 | circuit | yes (2) |
| 13 | `13_classical_bit_vs_qubit` | 845 | theory (explicit) | yes (4) |

### 3.1 How lessons reach the database

`backend/app/ai/rag.py :: ingest_content_folder()` runs at startup:

- **slug** = filename stem
- **order_index** = position in `sorted(glob("*.md"))` — i.e. **the filename number is the entire curriculum sequence**
- **track** = optional `<!-- track: circuit -->` comment; defaults to `theory`. Only 4 of 13 files carry the marker.
- **tags** = `infer_tags(text)` — **keyword-matched from the lesson body**, against only eight keywords: `algorithms, dynamic, entanglement, gates, grover, measurement, qubit, variational`

### 3.2 The `Lesson` model has no curriculum fields

`backend/app/models/content.py`:

```
Lesson: id, slug, title, path, tags, order_index, track
```

There is **no** `prerequisites`, `difficulty`, `learning_objectives`, `section`,
`module`, or `estimated_time`. There is no adjacency or dependency table. The
only structure is a flat integer and a two-valued track.

### 3.3 Mastery is keyed by tag, and the tags are unreliable

`UserMastery` is `(user_id, tag, score, attempts)`. Since tags are inferred from
prose keywords, running the real ingester over the real content produces:

```
01_qubits                 theory  ['dynamic','gates','measurement','qubit']
04_measurement            theory  ['algorithms','dynamic','measurement','qubit']
05_deutsch_jozsa          theory  ['algorithms','gates','grover','measurement','qubit']
13_classical_bit_vs_qubit theory  ['dynamic','entanglement','gates','measurement','qubit']
```

Every lesson is tagged `measurement` and `qubit`; nearly every one is tagged
`gates`. `04_measurement` is tagged `algorithms` and `dynamic`. `05_deutsch_jozsa`
is tagged `grover`. `13_classical_bit_vs_qubit` is tagged `entanglement` and
`dynamic`.

**Consequence:** the existing mastery signal is close to noise. A learner who
has only read the qubits lesson already carries `gates`, `measurement` and
`qubit` credit. Any prerequisite gating or mastery display built on the current
tags would be actively misleading, and any restructuring that edits lesson prose
would silently change the mastery keys underneath existing rows. This is the
single most important thing to fix before building prerequisites.

### 3.4 Lesson → simulation linkage is hardcoded in the UI

`frontend/web/src/pages/LearnPage.tsx` holds `DEMOS_FOR_LESSON`, a literal map
from slug to demo keys. Ten demos exist: `bit_vs_qubit, build_a_qubit, bloch,
circuit_lab, gates, plus_minus, state_space, measure, bit_order, interference`.
Ten of thirteen lessons are linked; **07, 08 and 09 have no interactive
component at all** — including the longest lesson in the corpus (quantum noise,
1081 words).

Because the map lives in the UI rather than the content, adding a lesson cannot
attach a demo without a front-end change.

## 4. Sequencing problems in the current corpus

Ordering is the filename number, which was chosen for authoring convenience, not
for pedagogy. Measured against prerequisite order:

1. **`07_vqe_qaoa` precedes `09_quantum_noise`.** VQE is a noisy-intermediate-scale
   algorithm whose entire motivation is device noise and shallow circuits.
   Teaching it before noise, decoherence and density matrices inverts the
   dependency.
2. **`03_entanglement` (265 w) precedes `11_bell_states` (584 w) by eight
   lessons.** Bell states are the canonical entanglement example. A learner meets
   the general concept before the concrete case, and the richer lesson sits in a
   different track.
3. **Duplication across three pairs:** `01_qubits` / `13_classical_bit_vs_qubit`
   (both cover bit-vs-qubit and the Bloch sphere); `02_gates` / `10_gates_bootcamp`
   (both cover gates); `03_entanglement` / `11_bell_states` (both cover
   entanglement).
4. **No mathematical foundations precede anything.** There is no lesson on
   complex numbers, linear algebra, or probability, yet `01_qubits` uses complex
   amplitudes and the Born rule in its first paragraph.

## 5. What exists versus what the roadmap asks for

Against the ten-section target curriculum, the platform currently covers
**three sections partially** and has **no content at all** for seven.

| Target section | Status |
|---|---|
| 1. Mathematical Foundations | **Absent.** No lesson on complex numbers, linear algebra, probability, or group theory. |
| 2. Core Quantum Theory | **Partial.** Measurement exists (`04`). No density matrices, POVMs, quantum channels, entanglement entropy, no-cloning. |
| 3. Introduction to Quantum Computing | **Partial.** Qubits, gates, entanglement, measurement, Bell states exist. **Absent:** Dirac notation, tensor products, inner products as a lesson, superposition as a dedicated lesson, teleportation. |
| 4. Introduction to Qiskit | **Absent as lessons.** Composer exists as a tool; no Sampler/Estimator/histogram/noise lessons. |
| 5. Quantum Algorithms | **Partial.** Deutsch–Jozsa and Grover exist. **Absent:** Shor, QKD, QFT, phase estimation, Bernstein–Vazirani, Simon, quantum walks, amplitude estimation. |
| 6. Advanced Theory and Circuits | **Partial.** Dynamic circuits and control flow exist. **Absent:** transpilation, universality, GHZ vs W, resource estimation, multi-controlled gates. |
| 7. Variational and NISQ | **Partial.** `07_vqe_qaoa` exists. **Absent:** ansatz construction, optimiser loops, parameter-shift, barren plateaus, QML. |
| 8. Error Correction and Fault Tolerance | **Absent.** No stabiliser formalism, surface code, threshold theorem, or error mitigation. |
| 9. Hardware and Ecosystem | **Absent.** No hardware modalities, connectivity, benchmarking, complexity classes, or ecosystem survey. |
| 10. Communication and Simulation | **Absent.** No superdense coding, repeaters, QKD-vs-PQC, or quantum simulation. |

## 6. Capability inventory

**Fully implemented**
- Circuit composer with drag-and-drop, multi-qubit gates, control flow
  (`if`/`for`/`while`/`box`), barriers, measurement to classical register
- Multi-backend execution with results, caching and job polling
- All ten result visualisations (P2)
- Code Lab with six frameworks and static checking (P3)
- Learn reader, quizzes, AI tutor (P4)
- Challenges, learner and instructor dashboards, recommendations (P5)
- Games (levels + Grover lab) and Playground (P6)
- Command palette, a11y audit, CSP, responsive notices, error boundary (P7)
- Golden-number parity harnesses: quantum 190, demos 804, Grover 3306 values

**Partially implemented / needs work**
- Curriculum structure (the subject of this audit)
- Mastery signal (see §3.3)
- Lesson → demo linkage (hardcoded, three lessons unlinked)

**Not implemented**
- Prerequisite graph, difficulty levels, learning objectives
- Learning paths, placement diagnostics, exam mode, spaced repetition
- Reference library, glossary, formula sheet
- Sandbox execution of learner Qiskit code

## 7. Test and build results (this audit, not a prior report)

| Check | Result |
|---|---|
| `npm run build` | clean |
| `golden:quantum` | 190/190 values, 1e-9 |
| `golden:demos` | 804/804 values, 1e-9 |
| `golden:grover` | 3306/3306 values, 1e-9 |
| `render:composer` | pass (36 checks) |
| `render:grover` | pass (27 checks) |
| `render:check` | 0 failures, student / anonymous / instructor |
| `a11y` | 0 criticals, all seven pages |
| `states` | all pages handle empty/error/loading |
| Backend pytest | **511 passed, 5 skipped** |
| Frontend pytest | **418 passed, 77 skipped** |

## 8. Cutover gate status

**P8 — NOT STARTED, and correctly so.** The gate is recorded in three places:
a sidebar banner tagged `data-cutover-gate="pending-personal-ui-testing"`, a
block above the P8 row in `docs/UI_REDESIGN_PLAN.md`, and a block at the top of
`frontend/web/WEB_DEV.md`. P8 requires a human to personally test the UI; no
agent can honestly claim that. Streamlit remains live and both stacks run side
by side.

**P9 — BLOCKED on P8.** Must not begin until P8 is approved.

Per the master prompt: *"Do not claim personal visual testing has been performed
unless an authorized human has actually completed it."* It has not. The audit
below deliberately stops short of Phase 1.

## 9. Conclusions relevant to the restructuring request

1. **Do not build prerequisites on the existing tags.** Introduce stable, authored
   topic identifiers first, and migrate `UserMastery` rows onto them. Otherwise
   the prerequisite graph is built on keyword noise and the migration is a
   one-way door.
2. **Do not delete or renumber the existing 13 files.** Slugs are the foreign key
   for quiz attempts, challenge attempts, recommendations and chat history.
   Restructure by *adding* structure around stable slugs.
3. **Filename order is the only sequencing that exists.** Moving to a real
   curriculum requires a new ordering key that does not depend on filenames.
4. **Three lessons have no interactive component**, including the longest.
   Attaching demos is cheap; they already exist.
5. **Seven of ten target sections have no content.** This is authoring work, not
   restructuring work, and should be sequenced separately so it does not block
   the structural change.
