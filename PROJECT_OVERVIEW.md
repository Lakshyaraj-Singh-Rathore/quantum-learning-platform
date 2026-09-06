# QuantumLearn — AI-Based Interactive Quantum Algorithm Learning Platform
### Presentation source material

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
   to ask "why?" Debugging is guesswork, and misconceptions harden.
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
> across multiple industry simulators and real quantum cloud hardware, and
> receive grounded AI explanations of their own results, while educators
> automatically assess progress and diagnose misconceptions.*

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
| **Run** | One circuit, five backends: Qiskit Aer, Cirq, PennyLane, a Qiskit dynamic engine, and qBraid cloud hardware/simulators |
| **Understand** | Gemini-powered AI tutor with RAG over the curriculum; can inspect circuits and explain stored results, but *cannot* run simulations itself |
| **Assess** | Quizzes, coding challenges with automatic grading, concept-level mastery tracking, and an instructor analytics dashboard |

---

## 3. Key Differentiators (the "why us" slide)

1. **Dynamic circuits are first-class.** Mid-circuit measurement, `if/else` on
   classical bits, bounded `while` loops and `for` loops — visually editable,
   correctly simulated, and exportable. Most educational tools cannot express
   these at all.

2. **Cross-backend verification as a teaching tool.** The same circuit runs on
   Aer, Cirq and PennyLane and produces agreeing histograms. Students learn
   that quantum results are *reproducible physics*, not simulator artefacts.

3. **The AI tutor has no simulation tool — by design.** It can read circuits
   and results already in the database, but it cannot invent numbers. This
   removes an entire class of hallucination: the AI can only explain runs that
   actually happened.

4. **Safety limits are architectural, not advisory.** `while` loops are hard
   capped at 32 iterations at the IR level, dynamic circuits at 15 qubits and
   4096 shots, with Celery soft/hard timeouts of 8s/15s. A student cannot hang
   the platform or accidentally spend hardware credits.

5. **OpenQASM 3 as the canonical format.** Circuits are portable in and out of
   the platform; students are not locked into our representation.

---

## 4. System Architecture

```
┌──────────────────────── Streamlit UI (5 pages) ───────────────────────┐
│  Home  │  Learn + AI tutor  │  Composer  │  Challenges  │  Dashboard  │
│                   └─ React/TypeScript drag-drop composer component    │
└───────────────────────────────┬───────────────────────────────────────┘
                                │ REST (JWT auth)
┌───────────────────────────────▼───────────────────────────────────────┐
│                     FastAPI backend — 29 endpoints                    │
│  auth │ jobs │ circuits │ QASM3 I/O │ export │ inspect │ backends     │
│  lessons │ quizzes │ challenges │ attempts │ dashboard │ ai           │
└───┬──────────────────┬──────────────────┬──────────────────┬──────────┘
    │                  │                  │                  │
┌───▼────────┐  ┌──────▼───────┐  ┌───────▼────────┐  ┌──────▼────────┐
│ Circuit IR │  │  Celery +    │  │  Gemini + RAG  │  │  PostgreSQL   │
│  + QASM3   │  │  Redis queue │  │  (pgvector)    │  │  + pgvector   │
│   codec    │  │              │  │                │  │  14 tables    │
└───┬────────┘  └──────┬───────┘  └────────────────┘  └───────────────┘
    │                  │
    │      ┌───────────┴───────────────────────────────┐
    │      ▼            ▼            ▼         ▼        ▼
    │  Qiskit Aer     Cirq      PennyLane   Qiskit   qBraid
    │  (static)     (static)    (static)   dynamic   (cloud)
    └──── normalize: IR → Qiskit → transpile to {rx, ry, rz, cx} → convert
```

**Execution routing:** dynamic circuits are always routed to the Qiskit
dynamic engine (other backends cannot express runtime control flow). Static
circuits are normalized through a common basis so every backend executes the
*same* program — which is why their histograms agree.

---

## 5. Technology Stack

| Layer | Technology |
|---|---|
| Frontend | Streamlit (multi-page), custom React + TypeScript + Vite component |
| Backend | FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic |
| Async | Celery 5.4 + Redis 7 |
| Database | PostgreSQL 16 + pgvector |
| Quantum | Qiskit 1.2, Qiskit Aer, Cirq, PennyLane, OpenQASM 3, qBraid SDK |
| AI | Google Gemini (chat + embeddings), RAG over pgvector |
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
- **RAG:** curriculum markdown chunked into pgvector (23 chunks, 8 lessons),
  semantic retrieval with keyword fallback
- **Tools:** `get_simulation_result`, `inspect_circuit`, `summarize_circuit`,
  `generate_code_qiskit`, `generate_code_cirq`
- **Deliberately no simulation tool** — the AI explains results that already
  exist in the database, so it cannot fabricate outcomes
- Every answer shows its curriculum sources

### 6.4 Assessment & Analytics
- **Quizzes:** MCQ + short answer; answers never sent to the client
- **Coding challenges:** autograded on total-variation distance between the
  observed and target distribution, plus constraints (allowed gates, max
  depth, max qubits, must-be-dynamic)
- **Mastery tracking:** concept tags on lessons and challenges feed
  `user_mastery`; a recommendation endpoint surfaces the weakest tag
- **Instructor dashboard:** progress, completion rates, common errors

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

### 6.7 Code Generation & Export
- **OpenQASM 3** — canonical import/export (file upload *or* paste), `.qasm` download
- **Qiskit** `.py` and **Cirq** `.py` source generation
- Dynamic circuits additionally export a **Python control-flow driver script**
  that reproduces `if/else` and capped `while` semantics — verified to agree
  with the native dynamic engine

### 6.8 Saved Circuits
- Full CRUD (create / list / fetch / delete), scoped per user

### 6.9 Data Layer
- PostgreSQL 16 + **pgvector** for semantic retrieval
- **Alembic** versioned migrations — 14 tables, applied automatically on
  container startup

### 6.10 Engineering Safeguards
| Control | Value |
|---|---|
| Max dynamic qubits | 15 |
| Max dynamic shots | 4096 |
| While-loop cap | 32 iterations |
| Celery soft / hard timeout | 8s / 15s |
| Result caching | `run_hash` per (circuit, engine, shots, mode, user) |

---

### 6.11 Software Components (slide-ready list)

**Frontend / User Interface**
- Streamlit multi-page web application (Home, Learn, Composer, Challenges, Dashboard)
- Custom React + TypeScript drag-and-drop circuit composer component

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

**Execution & Processing Layer**
- FastAPI backend, 29 REST endpoints
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

**AI Tutor**
- Google Gemini conversational tutor
- RAG over curriculum content, pgvector semantic retrieval with keyword fallback
- Tools: `get_simulation_result`, `inspect_circuit`, `summarize_circuit`,
  `generate_code_qiskit`, `generate_code_cirq`
- Explanations grounded in stored results — **no AI-triggered simulation**

**Code Generation & Export**
- OpenQASM 3, Qiskit `.py`, Cirq `.py`
- Dynamic circuits export a Python control-flow driver script

**Assessment Engine**
- Interactive quizzes (MCQ + short answer)
- Coding challenges with automated circuit evaluation
- Autograding on total-variation distance plus gate/depth/qubit constraints

**Personalization Engine**
- Concept-tag mastery tracking from quizzes and challenges
- Weakest-concept recommendations

**Analytics & Dashboard**
- Learner progress tracking and performance analytics
- Common-error analysis, instructor dashboard

**Deployment & Infrastructure**
- Docker Compose, 5 services, multi-stage builds
- Alembic versioned migrations (14 tables) applied on startup
- Modular backend, API-based service integration, cloud-ready

---

## 7. Results / Validation

**Cross-backend agreement** (Bell state, 1000 shots, seed 3):

| Backend | `00` | `11` |
|---|---|---|
| Qiskit Aer | 489 | 511 |
| Cirq | 488 | 512 |
| PennyLane | 502 | 498 |

Grover (2-qubit): `11` with probability 1.000 on all three backends.
Dynamic circuit: native engine and exported Cirq driver agree
(`{00: 991, 10: 3009}` vs `{00: 1025, 10: 2975}`).

**Scale:** 29 REST endpoints · 14 database tables · ~7,800 lines of Python ·
~1,500 lines of TypeScript · **87 automated tests passing**.

**Deployment:** verified end-to-end under Docker Compose — Postgres, Redis,
Celery worker, FastAPI and Streamlit, with Alembic migrations applied on
startup.

---

## 8. Suggested Slide Deck Structure (12 slides)

| # | Slide | Content |
|---|---|---|
| 1 | Title | QuantumLearn — AI-Based Interactive Quantum Algorithm Learning Platform |
| 2 | **Problem Statement** | Section 1 — the two-option trap, 5 consequences |
| 3 | Solution Overview | The four pillars table (Section 2) |
| 4 | Why It's Different | The 5 differentiators (Section 3) |
| 5 | Architecture | The diagram (Section 4) |
| 6 | Tech Stack | The stack table (Section 5) |
| 7 | Demo: Composer | Screenshot — Bell circuit + gate palette |
| 8 | Demo: Multi-backend | Screenshot — histogram, plus the agreement table |
| 9 | Demo: AI Tutor | Screenshot — a question, answer, and its citations |
| 10 | Demo: Dynamic Circuits | Screenshot — if/else + capped while |
| 11 | Assessment & Analytics | Autograder + instructor dashboard |
| 12 | Results & Roadmap | Section 7 metrics, then future work |

---

## 9. Future Scope

- Real QPU execution (currently qBraid free simulators; hardware is a config change)
- Noise models and error-mitigation lessons
- Collaborative/classroom mode with live instructor view
- Expanded curriculum: QFT, Shor, error correction codes
- Circuit-diff view to compare a student's attempt against a reference
