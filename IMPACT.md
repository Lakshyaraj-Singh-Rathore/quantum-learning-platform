# QuantumLearn — Impact & Value Proposition
### Presentation source material (every claim traceable to shipped code)

---

## 0. Ground rules for this document

Everything below is either **(a)** implemented and verifiable in the repository,
or **(b)** explicitly labelled as *Roadmap*. Nothing is asserted that a judge
could not confirm by opening the app. Numbers are measured, not estimated.

---

## 1. The one-line impact statement

> **QuantumLearn turns quantum computing education from reading about circuits
> into building them — a learner composes a circuit visually, executes it on
> four real simulation frameworks, sees the same physics agree across all of
> them, asks an AI tutor grounded in their own stored results why it behaved
> that way, and is graded automatically against a target distribution.**

The critical phrase is **"their own stored results"** — see §4.

---

## 2. The workflow this project actually enables

Traditional quantum coursework:

```
Read theory  →  Study a printed circuit diagram  →  Trust the stated output
```

QuantumLearn, as implemented:

```
LEARN            8 lessons, chunked into 23 retrievable passages
  ↓
BUILD            Drag-and-drop composer, 15 base gates + 11 controlled aliases,
                 nested if / for / while blocks
  ↓
VALIDATE         Circuit inspector rejects invalid circuits BEFORE execution
  ↓
RUN              Qiskit Aer · Cirq · PennyLane · Qiskit dynamic engine · qBraid
  ↓
VISUALIZE        Histogram · probability table · Bloch sphere · phase disk ·
                 amplitude table · circuit diagram
  ↓
UNDERSTAND       AI tutor explains THIS run, citing the curriculum
  ↓
ASSESS           Autograder scores the circuit against a target distribution
  ↓
IMPROVE          Mastery per concept tag drives the next recommendation
```

Each stage above corresponds to shipped code, not aspiration.

---

## 3. Impact on students

### 3.1 Invisible concepts become observable

Superposition, entanglement and phase cannot be seen in a measurement
histogram alone. The platform exposes **six** complementary views of the same
run — histogram, probability table, Bloch sphere, phase disk, amplitude table
and circuit diagram — so a learner can move between the *statistical* result
and the *state* that produced it.

Concrete example a judge can reproduce in 30 seconds:

1. Place `H` on q0 → run → histogram shows ~50/50
2. Add `CNOT(q0→q1)` → run → **only** `00` and `11` appear, never `01`/`10`
3. The amplitude view shows 1/√2 on indices 0 and 3, exactly zero on 1 and 2

That last step is the difference between *being told* two qubits are entangled
and *seeing* the amplitudes that make it true.

### 3.2 No hardware required, no credentials required

The four local backends run entirely on classical simulation inside Docker.
A student needs no quantum hardware, no cloud account, and no API key to
complete the full curriculum. qBraid is available for real cloud execution
when credentials are supplied, and is cleanly disabled with an explanatory
message when they are not.

**Institutional consequence:** a college can deploy the entire platform with
`docker compose up` and teach a quantum course with zero quantum
infrastructure and zero per-student cost.

### 3.3 Debugging becomes a learning loop

Beginners routinely invert control and target, measure into the wrong
classical bit, or mis-order gates. Ordinarily the student learns only that the
answer is wrong.

Here the failure is decomposed:

| Layer | Catches |
|---|---|
| Validator | Invalid gates, bad parameters, unbounded loops, resource violations — *before* running |
| Inspector | Depth, qubit count, dynamic-vs-static classification, per-backend warnings |
| Autograder | *Which* constraint failed: disallowed gate, excess depth, or wrong distribution |
| AI tutor | *Why* the result looks the way it does, grounded in the stored run |

The loop becomes **wrong answer → inspect → understand → modify → rerun**
rather than **wrong answer → stuck**.

---

## 4. The strongest design decision: the AI cannot simulate

The tutor is deliberately given **five** tools —
`get_simulation_result`, `inspect_circuit`, `summarize_circuit`,
`generate_code_qiskit`, `generate_code_cirq` — and **no simulation tool**.

It can read circuits and results already recorded in the database. It cannot
produce a number itself.

This is an architectural separation:

```
Computation   →  deterministic quantum engines  →  written to PostgreSQL
Explanation   →  Gemini, restricted to reading that record
```

**Why this matters for an educational product:** an LLM asked "what does this
circuit output?" will happily invent a plausible histogram. A student cannot
tell the difference. By construction, this platform's tutor can only explain
runs that genuinely happened, so a hallucinated measurement outcome is not
merely unlikely — it is impossible.

Retrieval is grounded the same way: answers cite the curriculum passages they
came from, and the UI shows those sources.

---

## 5. Multi-backend execution as pedagogy

Most tools lock a learner into one SDK. Here one circuit is normalized
(IR → Qiskit → transpiled to the portable basis `{rx, ry, rz, cx}`) and then
converted for each target, so every backend executes the *same* program.

**Measured agreement** — Bell state, 1000 shots, seed 3:

| Backend | `00` | `11` |
|---|---|---|
| Qiskit Aer | 489 | 511 |
| Cirq | 488 | 512 |
| PennyLane | 502 | 498 |

Grover (2-qubit) returns `11` with probability 1.000 on all three.

The teaching point: results agree because they describe **physics**, not a
simulator's opinion. Students also learn that the same algorithm has multiple
valid software representations — the actual state of the quantum ecosystem.

---

## 6. Dynamic circuits: the differentiator

Most beginner platforms stop at `gate → gate → measure`. This one implements
runtime classical control:

- `if / else` on classical bits, including bitstring comparison `c[0:k] == v`
- `for i in [0..N)` with compile-time constant N
- `while (c[i] == 1)`, **hard-capped at 32 iterations at the IR level**
- Nested block editing in the composer

This is the primitive underlying teleportation, error correction and
measurement-based computation — and it is where real hardware is heading.

**Verified:** the native dynamic engine and the exported Cirq driver script
agree on the same dynamic circuit (`{00: 991, 10: 3009}` vs
`{00: 1025, 10: 2975}` — consistent within shot noise).

---

## 7. Impact on educators

The instructor dashboard is **implemented**, not planned. It computes, live
from the database:

| Metric | Source |
|---|---|
| Quiz attempts, unique students, completion rate, average score | `quiz_attempts` |
| Challenge attempts, pass rate, completion rate | `challenge_attempts` |
| **Common errors, ranked by frequency** | Failed autogrades + failed jobs |
| **Weakest concepts across the cohort** | `user_mastery`, averaged by tag |
| Per-student progress | `/dashboard/students` |

The "common errors" feed is the pedagogically valuable one: it aggregates
constraint violations (disallowed gate, excess depth) and distribution
mismatches across the most recent 500 autograde results, so an instructor sees
*what the class is actually getting wrong* rather than only who scored badly.

**Worked example:** if "Output distribution does not match the target" ranks
first on the Grover challenge, the cohort has likely misunderstood the
diffuser — a targeted 15-minute session, not a re-taught module.

---

## 8. Automated assessment

Grading quantum circuits by hand does not scale: an instructor must read the
circuit, reason about the expected state, and judge whether a noisy histogram
is close enough.

The autograder does this deterministically:

- **Behavioural score:** total-variation distance between observed and target
  distribution, against a per-challenge tolerance
- **Structural constraints:** allowed gates, max depth, max qubits,
  must-be-dynamic
- **Feedback:** which specific constraint failed, plus the measured distance
- **Mastery update:** the outcome updates `user_mastery` for that concept tag

Shipped: **6 coding challenges** and **3 quizzes** across 8 lessons.

*Engineering note worth telling:* the Bell challenge originally used a
tolerance of 0.12, which — measured over 20,000 simulated submissions — failed
**~12% of correct answers** purely from shot noise at 1024 shots. It was
widened to 0.25, cutting false failures to ~0.14% while still scoring a wrong
`|00>`-only circuit at zero. This is the kind of statistical care an
autograder for a probabilistic machine requires.

---

## 9. Engineering safeguards (credibility with technical judges)

| Control | Value | Why |
|---|---|---|
| `while` cap | 32 iterations | Enforced in the IR — a student cannot write an infinite loop |
| Max dynamic qubits | 15 | Bounds statevector memory |
| Max dynamic shots | 4096 | Bounds runtime |
| Celery soft / hard timeout | 8s / 15s | No job can hang the platform |
| `run_hash` caching | per (circuit, engine, shots, mode, user) | Identical resubmissions reuse the stored result |
| Auth | JWT + bcrypt, roles student/instructor/admin | Multi-user, with role-gated dashboards |

These are architectural, not advisory: a learner **cannot** exhaust the server
or accidentally spend hardware credits.

---

## 10. Six differentiators (the slide)

| Differentiator | Impact |
|---|---|
| **Interactive circuit composer** | Converts theory into hands-on experimentation |
| **AI tutor that cannot hallucinate results** | Explanations are provably grounded in real runs |
| **Multi-backend execution with verified agreement** | Transferable skills; teaches reproducibility |
| **Dynamic circuits + OpenQASM 3** | Introduces modern quantum programming, not toy circuits |
| **Six visualization modes** | Makes invisible quantum behaviour observable |
| **Autograding + cohort analytics** | Turns learning into measurable, actionable data |

---

## 11. Measurable KPIs

Split honestly into what the platform records **today** versus what would need
instrumentation.

**Measurable now (data already stored):**

| KPI | Derived from |
|---|---|
| Quiz accuracy and completion rate | `quiz_attempts` |
| Challenge pass rate and attempts per student | `challenge_attempts` |
| Concept mastery per learner and per cohort | `user_mastery` |
| Most frequent student errors | `autograde_results` + failed jobs |
| Simulation success/failure rate | `simulation_jobs.status` |
| Execution latency | `simulation_jobs.started_at` → `finished_at` |
| Backend usage distribution | `simulation_jobs.backend` |
| Cache reuse | `run_hash` collisions |

**Roadmap (needs instrumentation):**
time-to-first-correct-circuit, edit-level debugging traces, AI response
latency, session-level engagement. The `analytics_events` table exists in the
schema for exactly this and is not yet written to — stated plainly rather than
claimed as delivered.

> Deliberately **no** unsupported claims such as "30% faster learning."
> No user study has been run; presenting measured KPIs is more defensible.

---

## 12. Slide 5 — the four-pillar impact graphic

```
 01 LEARN          02 EXPERIMENT       03 UNDERSTAND      04 MEASURE
 8 lessons,        Drag-and-drop       6 visualizations   Autograding on
 23 RAG passages   circuits on 5       + AI tutor         distribution
                   backends, no        grounded in your   distance +
                   hardware needed     own results        cohort analytics
```

**Caption:**
*From theoretical understanding to practical quantum skills — in one platform.*

---

## 13. Answering "so what is the real impact?" out loud

> "Quantum computing has a talent bottleneck: the tools that teach can't run
> real circuits, and the tools that run real circuits assume you already know
> quantum mechanics. QuantumLearn is one platform where a student builds a
> circuit visually, runs it on four simulation frameworks that all agree,
> sees six different views of what the state is doing, and asks an AI tutor
> why — an AI that is architecturally incapable of inventing a result,
> because it can only read runs that actually executed. Meanwhile the
> instructor sees exactly which concept the class is failing. No quantum
> hardware, no cloud account, one `docker compose up`."

---

## 14. Verified project metrics

| Metric | Value |
|---|---|
| REST endpoints | 29 |
| Database tables | 14 (Alembic-managed) |
| Base gates / controlled aliases | 15 / 11 |
| Execution backends | 5 |
| Lessons / RAG chunks | 8 / 23 |
| Quizzes / coding challenges | 3 / 6 |
| Visualization modes | 6 |
| AI tools (no simulation tool) | 5 |
| Automated tests | **87 passing** |
| Python / TypeScript | ~7,800 / ~1,500 lines |
| Deployment | Docker Compose, 5 services |
