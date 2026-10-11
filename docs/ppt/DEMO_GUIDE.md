# Demo Guide — Reproducible, with Expected Outputs

Two demos: **A. GUI walkthrough** (what you show) and **B. Command-line proof**
(what you run when the GUI cannot start). Every expected output below was
actually produced in this workspace.

> **Windows path:** `C:\Users\laksh\quantum-learning-platform`
> Every step below repeats `cd` so you can paste blocks independently.

---

## Prerequisites

```powershell
cd C:\Users\laksh\quantum-learning-platform
docker --version
docker compose version
git status
```

WSL / Git Bash equivalents:
```bash
cd /mnt/c/Users/laksh/quantum-learning-platform
docker --version
docker compose version
git status
```

**⚠ Do before presenting:**
1. Commit and push the three Streamlit-removal commits — GitHub still shows
   `55d66f2`, which contains **two** frontends.
2. Confirm `git log --oneline -1` shows the cutover commit.

---

## A. GUI walkthrough

### A0. Start the stack

```powershell
cd C:\Users\laksh\quantum-learning-platform
make up
```

`make up` auto-detects an NVIDIA GPU and layers `docker-compose.gpu.yml`.
Force with `make up GPU=1` or `make up GPU=0`.

```powershell
cd C:\Users\laksh\quantum-learning-platform
docker compose ps
```

**Expected:** `postgres`, `redis`, `api`, `worker`, `web` all `running`.
**Then open <http://localhost:3000>** and press **Ctrl+Shift+R** once — the
React bundles are content-hashed and a stale cached copy will misbehave.

### A1. Sign in

Seeded accounts (from `README.md`):

| Role | Email | Password |
| --- | --- | --- |
| Instructor | `instructor@local.dev` | `instructor123` |
| Learner | `learner@local.dev` | `learner123` |

**Sign in as the learner** for the walkthrough; switch to instructor for A7.

**Fallback:** if seeding did not run, register a new account at `/register`.

### A2. Learn — reading with real demos

1. Sidebar → **Learn**.
2. Open lesson **01_qubits**.
3. Interact with the Bloch / state demos.

**Expected:** maths renders typeset (KaTeX), tables render as `<table>`, and no
raw `$$` survives. The demos respond live; their numbers are the golden-pinned
values.

**Proof it is real:** `npm run render:learn` → **37 checks PASS**;
`npm run render:content` → **67 lessons rendered**.

### A3. Composer — build and run a Bell pair ⭐

1. Sidebar → **Composer**.
2. Drag **H** onto qubit 0, column 0.
3. Drag **CNOT** with control q0, target q1, column 1.
4. Backend: **Qiskit Aer**; shots: **1024**.
5. Press **Run simulation**.

**Expected:** roughly 50/50 on `00` and `11`, and **nothing** on `01`/`10`.

**Verified equivalent (this workspace, 256 shots, seed 7):**
`{'00': 122, '11': 134}`

**Then repeat on Cirq and PennyLane** — same result. That is the multiple-backend
point, made visually.

### A4. Composer — noise ⭐ (the best slide in the deck)

1. Backend must be **Qiskit Aer** or **CUDA-Q** (the panel is greyed out
   otherwise — `NOISE_BACKENDS = {qiskit_aer, cudaq}`).
2. Enable **Noise model (T1 / T2 / readout)**.
3. Start at T1 = 50 µs, T2 = 30 µs → **Run**.
4. Drop to T1 = 2 µs, T2 = 1 µs, readout 5% → **Run**.

**Expected (2048 shots, seed 11 — reproduced here):**

| Setting | Counts | P(odd-parity error) |
| --- | --- | --- |
| clean | `00:1011, 11:1037` | **0.000** |
| mild T1=50 T2=30 | `00:1016, 01:51, 10:45, 11:936` | **0.047** |
| harsh T1=2 T2=1 | `00:1023, 01:202, 10:228, 11:595` | **0.210** |

**The teaching moment:** `01` and `10` are *impossible* in a clean Bell state.
They appear only because decoherence moved population out of the subspace. The
results view shows **"Noisy minus ideal"** (`ResultsViews.tsx:489`).

**Then show the physical guard:** set T1 = 10, T2 = 100.
**Expected:** T2 is clamped to **20 µs** with the note
*"T2 clamped to 2\*T1 = 20 us (physical limit)."* — because T2 can never exceed
2·T1, and Aer would otherwise raise.

### A5. Playground — single-qubit intuition

1. Sidebar → **Playground**.
2. Drag theta/phi and watch the Bloch vector, the probability bars and the phase
   indicator move together.

**Expected:** instant, no network round-trip per drag — the maths is local
(`src/lib/playground.ts`), which is why it is golden-pinned rather than
server-computed. **20 harness checks PASS.**

**Fallback:** if the canvas misbehaves, show the Bloch view in
**Composer → results** instead; it shares the same maths.

### A6. Games — Grover, with a real simulation

1. Sidebar → **Games**.
2. Open the Grover / password-search module.
3. Drag the iteration slider **past** the optimum.

**Expected:** success probability **falls** after the optimum — over-rotation.
That is asserted explicitly in the goldens, not just displayed.
**3,306 Grover values agree with numpy at 1e-9.**

### A7. Dashboard — instructor view

1. Sign in as `instructor@local.dev`.
2. Sidebar → **Dashboard**.

**Expected:** per-student progress, topic mastery, recommendations.
**Proof:** `test_instructor_progress.py` (8 tests), `test_curriculum_api.py` (24).

### A8. Code Lab — six frameworks

1. Sidebar → **Code Lab**.
2. Pick a language (six supported), type an invalid line.

**Expected:** diagnostics appear **as you type**, with line and column, without
executing your program. Blocked imports (`os`, `subprocess`, `socket`,
`qbraid.runtime`) are reported.

**Then** press Build → the sandbox runs it.
**Proof:** `render:codelab` 15 checks; `test_codelab.py` 18;
`test_codelab_check.py` 8; `test_codelab_sandbox_escapes.py` 9.

---

## B. Command-line proofs (use when the GUI will not start)

These are the receipts. Run them live if you can — they take seconds.

### B1. Backend test suite

```powershell
cd C:\Users\laksh\quantum-learning-platform\backend
$env:PYTHONPATH="."
python -m pytest -q
```
```bash
cd /mnt/c/Users/laksh/quantum-learning-platform/backend
PYTHONPATH=. python -m pytest -q
```

**Expected (reproduced here):**
```
707 passed, 5 skipped in 107.18s (0:01:47)
```

### B2. Frontend harnesses

```powershell
cd C:\Users\laksh\quantum-learning-platform\frontend\web
npm install
npm run typecheck
npm run render:composer
npm run golden:demos
npm run golden:grover
```

**Expected:**
```
typecheck: clean
render:composer  → 36 checks PASS
golden:demos     → ALL CHECKS PASSED — 804 demo values agree with numpy (1e-9)
golden:grover    → ALL CHECKS PASSED — 3306 Grover values agree with numpy (1e-9)
```

`push:overlay` needs a browser:
```bash
cd /mnt/c/Users/laksh/quantum-learning-platform
bash tools/browser-setup.sh
cd frontend/web && npm run push:overlay
```
It self-skips with exit 0 when no browser is present — that is by design.

### B3. Backend availability, live

```bash
cd /mnt/c/Users/laksh/quantum-learning-platform/backend
PYTHONPATH=. python -c "
from app.quantum.ir import CircuitIR, Op, empty_circuit
ir = empty_circuit(2)
ir.ops = [Op(kind='gate',gate='h',qubits=[0]),
          Op(kind='gate',gate='cx',qubits=[0,1],controls=[]),
          Op(kind='measure',qubits=[0],clbits=[0]),
          Op(kind='measure',qubits=[1],clbits=[1])]
from app.quantum.backends import qiskit_aer, cirq_sim, pennylane_sim
for m in (qiskit_aer, cirq_sim, pennylane_sim):
    print(m.NAME, m.run(ir, shots=256, seed=7)['counts'])
"
```

**Expected:**
```
qiskit_aer {'00': 122, '11': 134}
cirq {'00': 129, '11': 127}
pennylane {'00': 120, '11': 136}
```

---

## C. Fallback matrix

| If this fails | Do this instead |
| --- | --- |
| Docker will not start | Run **section B** only — all three proofs are real and fast |
| `web` container unhealthy | Use `make web-dev` (Vite on :3001) or serve `frontend/web/dist` |
| No GPU | Fine — 4 of 6 backends need no GPU; CUDA-Q will report unavailable, which is honest |
| No `GEMINI_API_KEY` | Skip the AI tutor; **say** that RAG falls back to keyword scoring. Chunking still demos |
| No network | Docker images need pulling once; after that `make up` is offline |
| Composer grid blank | Run `node scripts/link-shared.mjs` in `frontend/web` — a second React copy breaks it at runtime |
| DB empty | `make seed`; migrations run automatically on `api` start |

---

## D. Do NOT demo these

- **qBraid** — spends real credits, and will usually exceed the 8 s soft limit.
- **CUDA-Q** — needs an NVIDIA GPU; it reports unavailable, which is correct
  behaviour, not a defect. (Show the graceful message as a *feature*: backends
  report *why* they are unavailable.)
- **Very large qubit counts** — the guard will 422 them. If you want to show the
  guard, use 21 qubits locally and explain the clean refusal.

---

## E. 60-second version if you are out of time

1. Composer → H + CNOT → Run → 50/50 on `00`/`11`. *(real simulation)*
2. Enable noise, T1=2 / T2=1 → `01`/`10` appear. *(physics, not decoration)*
3. Set T1=10, T2=100 → clamped to 20 with an explanation. *(correctness fix)*
4. `pytest -q` → 707 passed. *(verification)*

That sequence alone demonstrates simulation, noise, physics correctness, and
engineering rigour.
