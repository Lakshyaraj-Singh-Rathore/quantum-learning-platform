# Ready-to-use generation prompt — QuantumLearnAI hackathon deck

Copy everything in **Part A** into Claude. **Part B** is the fact pack it must obey.
**Part C** is what you still need to supply before generating.

---

# PART A — THE PROMPT

---

You are generating a **16-slide technical presentation for a hackathon judging panel**.

The project is **QuantumLearnAI**, an integrated web platform for learning quantum
computing. This is an **engineering project presentation**, not a startup pitch, not a
product advertisement, and not a collection of impressive-looking statistics. Judges are
technical. They will reward: a real problem, a working system, honest evidence, and
clear thinking about limits. They will punish: invented numbers, vague capability
claims, and features described as if they ship when they do not.

**Tone:** precise, technical, restrained. Every number traceable to something that was
measured. No superlatives that cannot be defended. No "revolutionary", "seamless",
"cutting-edge", "game-changing", "leveraging", "robust solution".

---

## Structure — four parts, 16 slides

**Part I — Problem and proposed solution (slides 1–4)**
**Part II — The website and integrated tasks (slides 5–11)** ← largest, most visual
**Part III — Architecture and implementation (slides 12–14)**
**Part IV — Evaluation and conclusion (slides 15–16)**

Part II must be the biggest section. Judges need to **see the working website**, not hear
a description of it.

---

## Slide-by-slide

### 01 — Title
Project name **QuantumLearnAI**. Team, institution, hackathon name.
Background is a **genuine screenshot** of the platform (the Composer with a Bell state
loaded is the strongest image). No metric dashboard. No equations.

### 02 — Problem statement
Why quantum computing is hard to learn: states and phases are abstract and mathematical;
learners must connect theory → circuit construction → simulation → interpretation of
results; and feedback on a wrong answer is usually absent.

**Frame this as the problem QuantumLearnAI addresses.** Do **not** claim existing tools
are inadequate. Do not name or criticise competitor products.

### 03 — Objectives and user requirements
What the platform must provide: structured learning, visual explanation, circuit
execution, immediate feedback, progressive practice, progress tracking.
Two user groups: **learners** and **instructors**. State what each needs.

### 04 — Proposed solution
Introduce the platform. Show **one connected workflow diagram** —
Lessons → Composer → Simulation → Visualisation → Practice → Progress —
with arrows, showing how a learner moves through it. Not a feature list.

### 05 — Website overview and navigation
**Real screenshot** of the React SPA with numbered annotations marking the main
sections. Explain the 11 pages and how a learner navigates between them.

### 06 — Learning environment and curriculum
The Learn and Curriculum sections. 67 lessons, 71 topics, 10 sections. Prerequisite
handling (acyclic dependency graph). Interactive concept demos embedded beside the text.
Show how a learner moves from explanation to experimentation — **screenshot**.

### 07 — Circuit composer and simulation
Walk through: place gates → build circuit → pick simulator → run → inspect output.
Use a **real Bell-pair example**: H then CNOT, then the measurement histogram.
Explain what the learner observes and why (~50/50 on `00` and `11`, nothing on `01`/`10`).

### 08 — Visualisation and intuitive understanding
Bloch vectors, probability distributions, **phase-coloured histograms**, ideal vs noisy.
Give phase-colour particular attention: **Z, S, T and RZ change phase without moving a
single count**, so bar heights stay identical while colours change. This communicates
information invisible from bar height alone. **Two side-by-side histograms, same heights,
different colours** is the key image of the whole deck.

### 09 — Practice tasks and games
Quizzes, challenges, **4 games across 10 levels**, and Grover Lab. Show **one authentic
example** of a task and its feedback, not every activity. Explain the feedback itself is
the product — which constraint failed, not just pass/fail.

### 10 — Code Lab
Qiskit, Cirq, PennyLane, OpenQASM 3. Show the real workflow: write → live diagnostics →
run in sandbox → see output. **Distinguish editor features from code that is actually
executed.** Mention dynamic-circuit support (if/for/while).

### 11 — Progress tracking and guided learning
Learner progress and per-topic mastery, instructor dashboard, recommendations.
Cover the AI/RAG component **accurately**, including that **live Gemini chat requires an
API key** and degrades to keyword retrieval without one.

### 12 — System architecture
**One technically accurate diagram**: React frontend → FastAPI → validated `CircuitIR`
→ backend adapters → job execution → PostgreSQL/pgvector → AI retrieval.
Explain component communication. No repository tree. No wall of logos.

### 13 — Core engineering decisions
Shared circuit representation; multiple backend adapters; dynamic circuits; the
simulation/visualisation pipeline; **physically bounded noise configuration** (T2 clamped
to 2·T1, not T1). Explain what was implemented and **why the decision matters**.

### 14 — Testing and verification
The real evidence: **4,300 golden values** checked against NumPy references at 1e-9;
**707 backend tests passing, 5 skipped**; **389 frontend checks** across 16 harnesses;
cross-backend agreement figures.
**State plainly that there is no CI — these are run manually.** Do not imply automation.

### 15 — Limitations and future improvements
Honest constraints: credential-dependent features, GPU requirements, simplified noise
modelling, no CI, the composer keyboard-accessibility gap.
Then **clearly separate planned work from completed work.**

### 16 — Conclusion and live demonstration
Summarise: problem, integrated platform, technical contribution.
End with the **demo path**: open a lesson → build a circuit → run → interpret the result.

---

## Roadmap content — label it, never blend it

Two features are **in progress this week and NOT yet shipped**:

- **Noise Lab** — T1/T2/readout exploration, Kraus channels, ideal-vs-noisy side by side,
  zero-noise extrapolation, probabilistic error cancellation, readout correction.
- **Smart Composer** — circuit reduction via identities (H²=I, adjacent-inverse
  cancellation, SWAP as three CNOTs) with verification, a circuit-diff view, and resource
  estimation.

**Rules:** put these on the limitations slide and/or a clearly-marked roadmap callout.
Greyed out, tagged **"In progress — not yet shipped"**. Never place them in the same
visual language as shipped features. If asked, they are work underway, not delivered.

---

## Anti-hallucination rules — these are hard constraints

1. **Use only the numbers in the fact pack.** If a number is not there, do not write one.
2. **Never invent** user counts, deployments, benchmarks, adoption figures, or
   performance comparisons.
3. **Never describe an unbuilt feature in the present tense.**
4. **Never claim the AI "cannot hallucinate" unqualified.** It cannot *invent a
   measurement result* — it has no simulation tool. It can still be wrong about prose.
   Scope the claim.
5. **Never call cross-backend agreement "hardware validation."** They are simulators of
   the same physics. Agreement demonstrates correct transpilation.
6. **If two sources conflict, do not pick one silently** — flag it or omit the number.
7. **Every screenshot must be genuine.** No mock-ups, no placeholder frames, no stock
   imagery, no invented UI.

---

## Visual rules

- One idea per slide.
- Screenshots for the website. Diagrams for architecture. Workflows for tasks.
  Charts for measured results.
- Do **not** force every slide into one template — vary layout by content type.
- Professional technical style: clear hierarchy, consistent typography, readable
  diagrams, restrained colour, deliberate spacing.
- Dark background, high contrast, one accent colour. No gradients on text.

## Speaker notes

Write notes a presenter can actually **speak** during a timed hackathon slot. Concrete,
technical, first-person-plural ("we implemented…", "we measured…").
**No marketing language.** Where a slide has a weak spot a judge might attack, put the
honest answer in the notes.

---

# PART B — FACT PACK (measured, use verbatim)

| Metric | Value |
|---|---|
| Backend tests | **707 passed / 5 skipped** (419 test functions, 32 files) |
| Frontend | **16 harness scripts** → **389 named checks** |
| Golden values | **4,300** compared against NumPy at **1e-9** |
| Endpoints | **41** across **7** routers |
| Database | **14 tables**, 8 Alembic migrations, one linear head |
| Backends | **6 adapters** (Aer, Cirq, PennyLane, dynamic Qiskit, qBraid, CUDA-Q) |
| Gates | **15 base** + **11 controlled aliases** |
| Curriculum | **67 lessons · 71 topics · 10 sections** |
| Content | **1,003,423 characters**, **344** cross-lesson links |
| Games | **4 games, 10 levels** + Grover Lab |
| SPA pages | **11** |
| Code Lab languages | **4**: Qiskit, Cirq, PennyLane, OpenQASM 3 |
| Limits | static **20 qubits**, dynamic **15**, while-cap **32**, shots **4096** |
| Services | **5**: Postgres, Redis, Celery worker, FastAPI, React |

**Cross-backend agreement** (Bell, 1000 shots, seed 3): Aer 489/511 · Cirq 488/512 ·
PennyLane 502/498. Worst divergence **0.025 at 8000 shots**. Grover 2-qubit: `11` at
probability **1.000** on all three.

**Noise:** reproduces `exp(-t/T1)` and `exp(-t/T2)` to **1e-9**. T2 clamped to **2·T1**
(the physical bound, since `1/T2 = 1/(2T1) + 1/T_phi`) — clamping to T1 is the common
error. Bell `P(odd parity)`: clean **0.000**, mild (T1=50,T2=30) **0.047**, harsh
(T1=2,T2=1,ro=.05) **0.210**.

**Phase colour (verified in code):** `ResultsViews.tsx:235`, "Colour bars by relative
phase", rendered `hsl(phase × 180/π, 65%, 55%)`, global phase removed first.

**AI/RAG:** 5 tools — `get_simulation_result`, `inspect_circuit`, `summarize_circuit`,
`generate_code_qiskit`, `generate_code_cirq`. **No simulation tool.** Retrieval is
pgvector semantic search with keyword fallback; falls back to keyword when no
`GEMINI_API_KEY`. Code Lab shows an explicit yellow "AI generation is unavailable" box
wired with `aria-describedby`.

**Games:** Bell Builder (4 levels, graded on **fidelity** because |Φ+⟩ and |Φ−⟩ have
identical histograms) · Open the Vault (3) · Find the Bug (2) · Shot Detective (1).
Grover Lab: amplitude **1/64 → 99.66% over 6 iterations**, falls if over-rotated.

**Grading:** total-variation distance vs target + structural constraints (allowed gates,
max depth, max qubits) + feedback naming which constraint failed + mastery update.
Bell tolerance widened 0.12 → 0.25 after measuring **12% false failures** at 1024 shots;
false-failure rate fell to **0.14%** while a wrong `|00⟩`-only circuit still scores zero.

**Honest gaps:**
1. **No CI** — all tests run manually.
2. **Composer palette keyboard access** — `Composer.tsx:439-446`, tiles have `draggable`
   and `onClick` but no `role`, `tabIndex`, or `onKeyDown`. Tracked, not fixed.
3. **Registry/DB divergence** — 54 topics `draft` in `curriculum.py`, published in DB.
   Deliberate; two tests depend on it. A design decision, not a bug.
4. **AI pillar needs a key.** Everything else works without one.
5. **Noise model is a parameterised configuration of Aer's `thermal_relaxation_error`** —
   no crosstalk, leakage, or correlated errors. Do not call it a new noise model.
6. **CUDA-Q needs an NVIDIA GPU; qBraid needs credentials.** Both self-disable with an
   explanation rather than failing silently.

---

# PART C — WHAT YOU MUST SUPPLY FIRST

1. **Team names, institution, hackathon name** (slide 1).
2. **Genuine screenshots.** There are currently **zero images in the repository**. Every
   slide marked "real screenshot" above is blocked until these exist. Needed at minimum:
   - Composer with a Bell state + histogram (slides 1, 7)
   - Two histograms side by side, phase-colour on vs off (slide 8 — the key image)
   - Learn page with an embedded demo (slide 6)
   - Navigation overview with annotations (slide 5)
   - One game task with its feedback (slide 9)
   - Code Lab with diagnostics visible (slide 10)
   - Dashboard / mastery view (slide 11)
3. **Decide the roadmap framing** before generating: "in progress this week" only if you
   will actually ship it. Otherwise say "planned".
4. **If you finish Noise Lab / Smart Composer this week**, re-verify and update Part B
   before presenting. Two known risks in those plans: the plan specifies T1/T2 in
   **nanoseconds** while the codebase uses **microseconds**; and Mode 2 targets a
   `coupling_map` that **no backend currently exposes**.
