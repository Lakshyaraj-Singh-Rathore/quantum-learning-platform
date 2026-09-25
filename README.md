# QuantumLearn — AI-Based Interactive Quantum Algorithm Learning Platform

Learn quantum computing by building circuits, not by reading about them. A
drag-and-drop composer, five real simulation backends (one GPU-accelerated),
an AI tutor grounded in the course material, auto-graded challenges and
puzzle games, and an instructor
dashboard.

**Stack** — Streamlit (7 pages + two custom React/TypeScript components) ·
FastAPI (41 endpoints) · Celery + Redis · Postgres + pgvector · Google Gemini ·
Docker Compose.

**982 tests** pass: 463 backend, 519 frontend.

---

## Quick start

```bash
cp .env.example .env
# optional: GEMINI_API_KEY (AI tutor), QBRAID_API_KEY (qBraid backend)
make up        # auto-adds the GPU override iff Docker can use a GPU
```

`make up` replaces `docker compose up --build`. If the machine's Docker can
reach an NVIDIA GPU it automatically includes `docker-compose.gpu.yml`, so
the **CUDA-Q GPU (up to 28 qubits)** backend is offered in the Composer; on a
CPU-only box it is the plain stack and that backend shows greyed-out with the
reason. No flags, no modes to remember — one command, and the backend is a
per-run dropdown either way. (Force it with `make up GPU=1` / `GPU=0`.)

Then open <http://localhost:8501>. On first load press **Ctrl+Shift+R** — the
React bundles are fingerprinted and a cached copy can be stale.

Seeded accounts:

| Email | Password | Role |
| --- | --- | --- |
| `instructor@local.dev` | `instructor123` | instructor |
| `admin@local.dev` | `admin123` | admin |

Register your own account for the student view.

---

## What it does

### Build and run circuits

A drag-and-drop composer with the full gate set — H, X, Y, Z, I, S, S†, T, T†,
√X, P(λ), RX, RY, RZ, SWAP, CNOT, Toffoli, general MCX — plus measure, reset,
barrier and `if` / `for` / `while` / `box` control-flow blocks.

Static circuits run on **Qiskit Aer, Cirq, PennyLane, qBraid — and, on an
NVIDIA GPU, CUDA-Q**; dynamic circuits (mid-circuit measurement driving
later gates) run on the Qiskit dynamic engine. Every gate is pinned to its
textbook unitary and every backend is checked to agree with the others —
see *Correctness* below.

Export to OpenQASM 3, Qiskit, Cirq, PennyLane or a qBraid submission script;
import OpenQASM 3 back.

### See what the state is doing

Bloch spheres, Q-sphere, phase disks, density matrices, amplitude and phase
tables, a step-through timeline, and ideal-versus-noisy comparison under a
T1/T2/readout noise model (Qiskit Aer and CUDA-Q).

### Learn

13 lessons, each with interactive demonstrations embedded beside the text:
superposition, amplitude versus probability, measurement collapse,
interference, the Bloch sphere, |+⟩ versus |−⟩, exponential state space and
Qiskit bit ordering. Six lessons embed the real composer so you can build while
you read.

An AI tutor answers questions using retrieval over the lesson corpus. It has
**no simulation tool** by design: it can explain results already in the
database, never invent them.

### Practice

- **Quizzes** — multiple choice and short answer, auto-graded.
- **Coding challenges** — graded on distribution distance or state fidelity,
  with constraints on allowed gates, depth and qubit count.
- **Quantum Games** — 10 puzzle levels across four games:
  - *Bell Builder* — all four Bell states, graded on fidelity because |Φ+⟩ and
    |Φ−⟩ have identical histograms
  - *Open the Vault* — multi-controlled gates, graded over the complete truth
    table
  - *Find the Bug* — repair a broken circuit within an edit budget
  - *Shot Detective* — discover how many shots a distribution actually needs
- **Quantum Password Search** — a Grover's-algorithm simulator. Real
  state-vector maths, not an animation: watch the target amplitude grow from
  1/64 to 99.66% over six iterations, and watch it *fall again* if you
  over-rotate.
- **Code Lab** — write Qiskit, Cirq, PennyLane, OpenQASM 3, qBraid or
  CUDA-Q (`cudaq.make_kernel()`) code, with live diagnostics as you type and
  execution in a hardened sandbox. The CUDA-Q tab appears in installs that
  ship the wheel — under `make up` on a machine with a GPU.

### Teach

An instructor dashboard with per-student progress, completion rates, common
errors and concept-level mastery tracking.

---

## Correctness

The physics is tested rather than assumed.

- **Every gate** is compared against a closed-form matrix written out by hand,
  up to a global phase, plus the identities that must hold: S² = Z, T² = S,
  SX² = X, S† = S⁻¹, XYZ = iI.
- **Rotations** match `exp(-iθP/2)` at five angles.
- **Multi-controlled gates** are checked over the full truth table for one to
  three controls, including that the controls survive.
- **All three static backends agree** on every gate to within sampling noise
  (worst observed divergence 0.025 at 8000 shots), with each gate sandwiched
  between Hadamards so a phase-only gate still moves the distribution. The
  CUDA-Q GPU engine joins the same agreement battery automatically on any
  machine that has a GPU; it is skipped, not stubbed out, when there is none.
- **QASM 3 round-trips** preserve behaviour for every gate.
- **Known-answer runs**: Bell, GHZ, Deutsch-Jozsa (both branches) and Grover
  finding the marked state with certainty.
- **The noise model** reproduces `exp(-t/T1)` and `exp(-t/T2)` to 1e-9, and
  clamps T2 to the physical limit of 2·T1 — not T1, which is a common error.
  On CUDA-Q the same `NoiseParams` become CUDA-Q's own Kraus channels
  (`AmplitudeDampingChannel`, `PhaseFlipChannel`, readout as a bit-flip on
  `mz`), executed by CUDA-Q's density-matrix engine; its noisy marginals are
  gated against an independent hand-derived reference when the wheel is
  installed.
- **Bloch vectors** are verified against Pauli traces; all six cardinal states
  round-trip exactly.

---

## Layout

```
backend/
  app/
    api/            41 REST endpoints
    quantum/        IR, QASM3 codec, gate normalisation, noise, timeline
      backends/     qiskit_aer · cirq · pennylane · qbraid · cudaq · dynamic_qiskit
    ai/             Gemini client, RAG over the lesson corpus, tool policy
    services/       autograder, game graders, code sandbox, recommendations
    models/         SQLAlchemy models
  alembic/          4 migrations
  tests/            463 tests
frontend/
  Home.py
  pages/            Learn · Composer · Challenges · Dashboard · Code Lab ·
                    Games · Playground
  lib/              viz · composer · playground · grover_lab · code_checks …
  circuit_composer/ React drag-and-drop grid (TypeScript)
  live_bloch/       React continuous Bloch sphere (TypeScript)
  tests/            519 tests
content/            13 lessons in Markdown
docs/               deployment, UI redesign briefs, references
reports/            UI audit
```

---

## React components

Two TypeScript components are compiled into the Streamlit app. Docker builds
them automatically; for local development outside Docker:

```bash
cd frontend/circuit_composer/frontend && npm ci && npm run build
cd ../../live_bloch/frontend        && npm ci && npm run build
```

If a bundle is missing the app degrades gracefully — the composer falls back to
a pure-Python grid, and the Bloch demo to the verified Plotly sphere.

---

## Local development without Docker

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt -r frontend/requirements.txt

# API
cd backend
PYTHONPATH=. DATABASE_URL=sqlite:///./dev.db CELERY_TASK_ALWAYS_EAGER=true \
  alembic upgrade head
PYTHONPATH=. DATABASE_URL=sqlite:///./dev.db CELERY_TASK_ALWAYS_EAGER=true \
  uvicorn app.main:app --reload

# UI, in another shell
cd frontend
PYTHONPATH=../backend:. API_BASE_URL=http://localhost:8000 \
  streamlit run Home.py
```

`CELERY_TASK_ALWAYS_EAGER=true` runs jobs inline, so Redis and a worker are not
needed for development.

### Tests

```bash
cd backend  && PYTHONPATH=. ../.venv/bin/python -m pytest -q
cd frontend && PYTHONPATH=../backend:. ../.venv/bin/python -m pytest -q
```

Some frontend tests are integration tests and need the API running; they skip
cleanly if it is not. Lint with `ruff check .` — configured for correctness
rules rather than style preferences.

---

## Configuration

Everything is read from the environment; `.env.example` lists the full set.

| Variable | Default | Notes |
| --- | --- | --- |
| `DATABASE_URL` | postgres in compose | SQLite works for development |
| `GEMINI_API_KEY` | unset | AI tutor and code generation; degrades to keyword retrieval |
| `QBRAID_API_KEY` | unset | qBraid backend; shows "Missing credentials" if unset |
| `QBRAID_DEVICE_ID` | `ionq:ionq:sim:simulator` | free 0-credit simulator |
| `MAX_STATIC_QUBITS` | 20 | a statevector is 16 bytes × 2ⁿ |
| `MAX_DYNAMIC_QUBITS` | 15 | dynamic engine limit |
| `MAX_GPU_QUBITS` | 28 | CUDA-Q's VRAM ceiling; also `GPU_TEMP_LIMIT_C=80`, `GPU_COOLDOWN_SECONDS=3` (docs/CUDAQ_SETUP.md) |
| `WHILE_CAP` | 32 | hard cap on runtime loop iterations |
| `CELERY_TASK_ALWAYS_EAGER` | false | run jobs inline, no worker |

**Each variable must be on its own line in `.env`.** A missing newline silently
merges two settings — the qBraid backend now detects and reports that
specifically, because it is easy to do and hard to spot.

---

## Deployment

`make up` (a thin wrapper over `docker compose up --build` that adds the GPU
override when a GPU is present) is the supported path and runs the whole
stack locally.

`docs/DEPLOYMENT.md` documents a measured free-tier cloud split (Streamlit
Community Cloud for the UI, Render for the API, Neon for Postgres) including
the memory numbers that drive it and the limitations that come with it.

---

## Notes and limitations

- Static simulation is capped at 20 qubits; a 24-qubit statevector needs
  268 MB and will exhaust a small container.
- qBraid runs on a remote queue. Credits are spent at submission, so a run that
  later times out still costs them; the free IonQ simulator often exceeds the
  default 8-second soft limit. Use the local backends while iterating.
- The AI tutor needs `GEMINI_API_KEY`. Without it, retrieval falls back to
  keyword search and code generation returns a clear 503.
- The Code Lab sandbox blocks the filesystem, the network and subprocesses, and
  is covered by escape tests. It is a teaching sandbox, not a security boundary
  for untrusted internet traffic.

## Licence and references

Course content, algorithm sources and library citations are listed in
`docs/REFERENCES.md`.
