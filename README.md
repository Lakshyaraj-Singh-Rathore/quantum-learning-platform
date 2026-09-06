# QuantumLearn — AI-Based Interactive Quantum Algorithm Learning Platform

An interactive platform for learning quantum algorithms: a drag-and-drop circuit
composer, multi-backend simulation, a Gemini tutor grounded in course content via
RAG, auto-graded coding challenges and quizzes, and an instructor analytics
dashboard.

**Stack** — Streamlit (multi-page UI + a custom React/TypeScript composer
component) · FastAPI · Celery + Redis · Postgres + pgvector · Google Gemini ·
Docker Compose.

---

## Quick start

```bash
cp .env.example .env
# optional: GEMINI_API_KEY (AI tutor), QBRAID_API_KEY + QBRAID_DEVICE_ID (qBraid backend)
docker compose up --build
```

- UI — http://localhost:8501
- API docs — http://localhost:8000/docs

Database migrations run automatically on API start (`alembic upgrade head`), and
seed data plus `/content` ingestion run on application startup.

Bootstrap accounts:

| Role | Email | Password |
| --- | --- | --- |
| admin | admin@local.dev | admin123 |
| instructor | instructor@local.dev | instructor123 |

Register a student from the UI.

```bash
make test      # pytest inside the api container
make seed      # re-run seeding
make migrate   # alembic upgrade head
make composer  # build the React composer bundle
```

---

## Features

### Circuit composer

Rows are qubits, columns are layers. Dropping a gate onto an occupied column
performs a **global auto-insert column** (everything at layer ≥ t shifts right),
matching IBM Composer behaviour. The grid auto-grows to the right.

- **Gates** — H, X/NOT, Y, Z, Identity, S, S†, T, T†, SX, P(λ), RX/RY/RZ(θ)
- **Multi-qubit** — CNOT, SWAP, Toffoli (CCX), general **MCX**, and a `Control+`
  modifier that adds controls to an existing gate. Drop the gate on its *target*,
  then click control qubits in the same column.
- **Structural** — Measure, Reset, Barrier
- **Blocks** — `if/else`, `for`, `while`, `box`, with a nested block editor

Two measurement buttons, deliberately distinct:

- **Measure All (Append)** — dynamic-safe. Appends a measurement layer at the end
  and *never* deletes an existing measurement.
- **Normalize Terminal Measurement** — **top level only**. Strips top-level
  measurements and emits a single terminal measurement layer. Measurements nested
  inside blocks are never touched; a warning is shown for dynamic circuits, whose
  semantics depend on mid-circuit measurement.

**Parameters** use a restricted grammar: only `pi`, numbers and `+ - * / ( )`.
Symbolic variables such as `theta` are rejected. Both the expression
(`param_expr`) and the evaluated value in radians (`param_value`) are stored.

### Circuit language

OpenQASM 3 is the canonical import/export format. Supported control flow:

- `if / else`
- bitstring comparisons — `if (c[0:k] == value)`
- `for i in [0..N)` with a **compile-time constant** N
- `while (c[i] == 1)`, **hard-capped at 32 iterations**

### Execution backends

| Circuit | Backends |
| --- | --- |
| **Dynamic** (mid-circuit measurement / feedback) | Qiskit dynamic engine **only** — max 15 qubits, 4096 shots, while-cap 32 |
| **Static** | Qiskit Aer, Cirq, PennyLane (`default.qubit` via `qml.from_qiskit`), and **qBraid** as a real executable backend |

Static normalization: IR/QASM3 → Qiskit → transpile to the basis `rx, ry, rz, cx`
→ convert to Cirq / PennyLane / qBraid. This keeps results comparable across
backends (a per-backend global phase is normalized away).

qBraid submits, polls and retrieves real jobs using `QBRAID_API_KEY` and
`QBRAID_DEVICE_ID`. Without credentials the backend is rejected with
*"Missing qBraid credentials"*.

Celery limits: soft 8s / hard 15s. Identical submissions are de-duplicated via a
`run_hash` cache scoped per user.

### Exports

- OpenQASM 3 (`.qasm`)
- Qiskit (`.py`)
- Cirq (`.py`) — for **dynamic** circuits the export is a Cirq circuit **plus a
  Python driver script** implementing the classical control flow, since Cirq has
  no native dynamic execution.

### AI tutor

Gemini with RAG over the markdown in `/content`, chunked and embedded into
pgvector. Available tools:

`get_simulation_result` · `inspect_circuit` · `summarize_circuit` ·
`generate_code_qiskit` · `generate_code_cirq`

There is deliberately **no simulation tool** — the AI may only explain results
that already exist in the database, so it can never fabricate a measurement
outcome. AI endpoints require authentication. Without `GEMINI_API_KEY` the AI
features degrade gracefully and the rest of the platform is unaffected.

### Assessments & personalization

Quizzes (MCQ + short answer) and coding challenges with an autograder that checks
count/fidelity tolerance, allowed gates and maximum depth. Attempts are stored,
mastery is tracked per concept tag, and the weakest-tag endpoint drives the
"what to learn next" recommendations. The instructor dashboard (instructor/admin
only) shows progress, completion rates, common errors and a leaderboard.

### Auth

Email + password with bcrypt hashing and JWTs. Roles: `student`, `instructor`,
`admin`. Endpoints `/auth/register`, `/auth/login`, `/auth/me`; the Streamlit UI
keeps the JWT in `session_state`.

---

## Layout

```
backend/
  alembic/            migrations (alembic upgrade head)
  app/
    api/              auth, jobs, circuits, assessments, dashboard, ai routers
    quantum/
      ir.py           circuit IR (gates, controls, params, blocks)
      qasm3_codec.py  OpenQASM 3 import/export
      normalize.py    static normalization + transpilation
      inspect.py      circuit analysis
      codegen_*.py    Qiskit / Cirq code export
      backends/       qiskit_aer, cirq_sim, pennylane_sim, dynamic_qiskit, qbraid_sim
    workers/          Celery app + tasks
    ai/               Gemini client, RAG, tools
    services/         autograder, mastery, ingestion
    models/ schemas/  SQLAlchemy models and Pydantic schemas
  tests/              64 tests
frontend/
  Home.py             landing + login
  pages/              Learn · Composer · Challenges · Dashboard
  lib/                api client, auth, visualizations, Python grid composer
  circuit_composer/   Streamlit custom component wrapper
    frontend/         React + TypeScript drag-and-drop composer
content/              8 lesson markdown files (the RAG corpus)
samples/              bell.qasm · grover.qasm · dynamic_while.qasm
```

---

## React composer

The React drag-and-drop composer is built automatically by the frontend Docker
image. To build it locally:

```bash
make composer
# or: cd frontend/circuit_composer/frontend && npm install && npm run build
```

If the bundle is absent the Composer page **falls back to an equivalent
pure-Python grid composer**, so the platform is fully usable either way. For
component development:

```bash
cd frontend/circuit_composer/frontend && npm run dev   # serves on :3001
COMPOSER_DEV_URL=http://localhost:3001 streamlit run Home.py
```

---

## Local development (no Docker)

Requires Postgres 16 with pgvector and Redis.

```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
celery -A app.workers.celery_app.celery_app worker -l info

cd ../frontend
pip install -r requirements.txt
PYTHONPATH=../backend API_BASE_URL=http://localhost:8000 streamlit run Home.py
```

**No Postgres or Redis?** The stack degrades for development:

```bash
export DATABASE_URL="sqlite:///./dev.db"   # pgvector columns fall back to JSON
export CELERY_TASK_ALWAYS_EAGER=true       # run simulations inline, no broker
```

### Migrations

```bash
cd backend
alembic upgrade head                                  # apply
alembic revision --autogenerate -m "describe change"  # create
alembic check                                         # fail if models drift
```

The database URL always comes from `DATABASE_URL` via the app settings, never
from `alembic.ini`, so migrations and the running app cannot disagree.

### Tests

```bash
cd backend && pytest -q
```

Covers QASM3 parse/import/export, transpilation and normalization, the dynamic
while-cap, job lifecycle and the auth login flow.

---

## Configuration

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | Postgres (pgvector) connection string |
| `REDIS_URL` | Celery broker / result backend |
| `JWT_SECRET` | JWT signing key — **change in production** |
| `GEMINI_API_KEY` | Enables the AI tutor and embeddings |
| `QBRAID_API_KEY` / `QBRAID_DEVICE_ID` | Enables the qBraid backend |
| `CONTENT_DIR` | Lesson markdown directory ingested for RAG |
| `CELERY_TASK_ALWAYS_EAGER` | Dev only — run tasks inline without a broker |
| `BOOTSTRAP_ADMIN_EMAIL` / `BOOTSTRAP_ADMIN_PASSWORD` | Seeded admin account |

See `.env.example` for the full list.
