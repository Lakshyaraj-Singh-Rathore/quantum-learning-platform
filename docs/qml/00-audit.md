# QML Lab — Phase 0 Audit

**Status:** Phase 0 complete, no feature code written.
**Date of run:** 2026-10-22
**Commit audited:** `648dec4` (tree byte-identical to `origin/main @ 12d33df`)
**Governing documents:** `QML_Lab_Master_Prompt (1).md`, as amended by
[`docs/prompts/QML_LAB_VISION_AGENT.md`](../prompts/QML_LAB_VISION_AGENT.md) (the amendment wins on conflict).

Every number below was produced by a command run in this session. Commands are given so they can be re-run.
Where a number differs from the amendment's §0 table, the difference is reported rather than absorbed.

---

## 1. Entry gate (§5.1, §9)

| Check | Result |
|---|---|
| `git rev-parse --short HEAD` | `648dec4` |
| `git rev-parse --short origin/main` | `12d33df` |
| HEAD tree == origin/main tree | **YES** (`git rev-parse HEAD^{tree}` equal) |
| `git status --porcelain \| wc -l` | **0** — clean |
| Untracked files | **0** |
| Tracked file count | **531** (see §1.1) |
| Deleted Streamlit paths resurrected? | **No** — `frontend/pages`, `frontend/lib`, `frontend/live_bloch`, `frontend/tests`, `.streamlit`, `frontend/Home.py` all absent |

The tree is clean, so the §5.1 stop condition does not fire.

### 1.1 One discrepancy: tracked file count 531 vs documented 530

The amendment records a baseline of **530** tracked files; the working tree has **531**.

- `12d33df` is a **root commit** — `git ls-tree -r --name-only 12d33df^` fails with
  `fatal: Not a valid object name`. The history was re-pushed as a fresh single commit, so there is no
  parent to diff and the added file cannot be identified by `git`.
- `git ls-files | wc -l` minus `docs/prompts/QML_LAB_VISION_AGENT.md` (the amendment doc itself, authored
  for this task) is **exactly 530**.

**Reported, not adopted.** This is consistent with the amendment doc being the +1, but that is arithmetic
coincidence, not proof — the root commit makes it unverifiable. File count is a repo fact, not one of the
seven gates; all seven gates match exactly (§2), so this does not fire a §5.5 stop. Flagged for the senior agent.

---

## 2. Baseline, reproduced by running it

Each row was executed in this session. "Baseline" is the amendment's §0 figure.

| Gate | Command | Baseline | **Measured** | Verdict |
|---|---|---|---|---|
| Backend tests | `cd backend; PYTHONPATH=. python -m pytest -q` | 818 passed, 5 skipped | **818 passed, 5 skipped** (117.75 s) | MATCH |
| Typecheck | `cd frontend/web; npm run typecheck` | 0 errors | **0 errors** (exit 0) | MATCH |
| Build | `cd frontend/web; npx vite build` | PASS, ~2090 modules, ~638 kB | **PASS, 2090 modules, 639.18 kB** main chunk (gzip 187.58 kB), CSS 163.40 kB, 9.87 s | MATCH |
| Render harnesses | loop over `scripts/*.mts` | 284 PASS / 57 FAIL | **284 PASS / 57 FAIL** | MATCH |
| Goldens | `npm run golden:quantum` / `:demos` / `:grover` | 190 + 804 + 3306 @1e-9 | **190 + 804 + 3306 @1e-9** | MATCH |
| a11y | `npm run a11y` | 0 criticals | **0 criticals** | MATCH |
| API routes | introspect `app.main:app` | 58 paths | **58** `APIRoute` paths | MATCH |

**All seven gates match. No §5.5 stop condition fires.**

### 2.1 Harness loop, per script

Counted with `grep -coE "^[^A-Za-z]*(PASS|✓|ok )"` and the matching FAIL pattern over each script's output.

| Script | PASS | FAIL | exit |
|---|---:|---:|---:|
| a11y-check | 9 | 0 | 0 |
| curriculum-check | 29 | 0 | 0 |
| golden-demos | 0 | 0 | 0 |
| golden-grover | 0 | 0 | 0 |
| golden-quantum | 0 | 0 | 0 |
| push-overlay-check | — | — | 1 (BLOCKED, §2.2) |
| render-b5-check | 0 | 0 | 0 |
| render-check | 24 | 0 | 0 |
| render-codelab | 6 | **9** | 1 |
| render-composer | 36 | 0 | 0 |
| render-games | 12 | **20** | 1 |
| render-grover | 27 | 0 | 0 |
| render-learn | 37 | 0 | 0 |
| render-p5 | 14 | **20** | 1 |
| render-playground | 20 | 0 | 0 |
| render-results | 39 | **8** | 1 |
| smoke-auth | 13 | 0 | 0 |
| smoke-composer | 10 | 0 | 0 |
| states-check | 31 | 0 | 0 |
| verify-all-demos | 0 | 0 | 0 |
| **TOTAL** | **284** | **57** | |

The 57 pre-existing FAILs are **exactly** the four SSR render harnesses: `render-codelab` (9) +
`render-games` (20) + `render-p5` (20) + `render-results` (8) = 57. The regression gate for every later
phase is therefore precise: **these same four scripts, these same counts, no new failing script.**

Per the amendment: these 57 are pre-existing and **must not be "fixed"**, deleted, or counted as regressions.

### 2.2 Harness invocation facts (cost real time to discover — recorded so they are not rediscovered)

1. **`npm run typecheck`, never bare `npx tsc --noEmit`.** The npm script runs
   `node scripts/link-shared.mjs` first, which symlinks `react`, `react-dom` and `@types` into
   `frontend/circuit_composer`. Skipping it produces **false** `TS2307 Cannot find module 'react'` errors in
   `circuit_composer/frontend/src/Grid.tsx`. Those errors are an invocation artefact, not a defect.
2. **`smoke-auth` and `smoke-composer` need `API_TARGET`.** Default is `http://127.0.0.1:8123`; the dev API
   listens on `:8000`. Without it both abort with `ApiError: Cannot reach the API` and contribute 0/0.
   With `API_TARGET=http://127.0.0.1:8000` they return 13 PASS and 10 PASS.
3. **`push-overlay-check` is BLOCKED in this environment, not failing.** It is the only real Playwright
   harness. It seeds a fabricated token (`push-overlay-token`, `scripts/push-overlay-check.mts:115`) into
   `localStorage.ql-session`; the live API rejects it, the shell redirects to `/login`, and the script times
   out on `waitForSelector('aside')`. With no API running it instead emits 6 ECONNREFUSED proxy errors.
   It contributes **0 PASS** either way, which is why the documented 284/57 reconciles exactly without it.
   Recorded as **BLOCKED (environment)** — not PASS, not FAIL.
4. Never pipe `tsx` output into `tail`; redirect to a file and read the file.
5. Run pytest from `backend/` with `PYTHONPATH=.`. From the repo root,
   `test_curriculum.py::test_downgrade_places_every_lesson_and_preserves_secondary_placements` fails with
   `alembic.util.exc.CommandError: Path doesn't exist`. Invocation bug, not a defect.

---

## 3. Environment

| Item | Value |
|---|---|
| OS (this sandbox) | Linux 6.1.158+ |
| Python | 3.11.2 (venv at `/home/user/.venv-ql`) |
| pytest | 8.3.4 |
| Node | v22.22.3 |
| npm | 10.9.8 |
| Chromium (harnesses) | 153.0.8010.0 via `tools/browser-setup.sh` |
| Local DB | `sqlite:///./local.db`, `alembic upgrade head` applied all 8 migrations cleanly |
| Redis / Celery worker | **not running**; API started with `CELERY_TASK_ALWAYS_EAGER=true` |
| `GEMINI_API_KEY` | absent — API logs `gemini=False, qbraid=False` |

**Divergence from the user's machine, stated plainly (§6).** The target environment is Windows +
PowerShell 5, where `&&` is a parser error, Celery cannot use the `prefork` pool (`--pool=solo` required),
and `docker compose` is always invoked with `-f docker-compose.gpu.yml`. This sandbox is Linux. Anything
whose behaviour is OS-dependent — above all **per-task Celery time limits, which are the §1.1 amendment's
central requirement** — is verified here on Linux and **cannot be claimed verified on Windows from this
session**. The P2 report will state which half was proven where. If per-task limits turn out not to work
under `--pool=solo` on Windows, that is a §5.7 stop condition.

### 3.1 Dependency dry-run (§1.3) — **torch will not be installed**

```
$ /home/user/.venv-ql/bin/pip install --dry-run torch
Would install Jinja2-3.1.6 cuda-bindings-13.4.4 cuda-pathfinder-1.8.3 cuda-toolkit-13.0.3.0
filelock-4.2.4 fsspec-2026.9.0 nvidia-cublas-13.1.1.3 nvidia-cuda-cupti-13.0.85
nvidia-cuda-nvrtc-13.0.88 nvidia-cuda-runtime-13.0.96 nvidia-cudnn-cu13-9.24.0.43
nvidia-cufft-12.0.0.61 nvidia-cufile-1.15.1.6 nvidia-curand-10.4.0.35 nvidia-cusolver-12.0.4.66
nvidia-cusparse-12.6.3.3 nvidia-cusparselt-cu13-0.8.1 nvidia-nccl-cu13-2.30.7
nvidia-nvjitlink-13.4.92 nvidia-nvshmem-cu13-3.4.5 nvidia-nvtx-13.0.85 setuptools-84.2.1
sympy-1.14.0 torch-2.14.1 triton-3.8.0
```

**Result: the resolver would NOT move the numpy pin.** `numpy` does not appear in the install set;
`numpy==1.26.4` and `scipy==1.17.1` stay put. The §1.3 STOP condition therefore does **not** fire.

**Decision anyway: do not install torch.** It would add 24 packages including the complete CUDA toolkit
(multi-GB) to a CPU-only simulation feature, for no capability the alternative lacks. This is a choice, not
a constraint — recorded as such in `DECISIONS.md` (D-003).

The no-torch path was not assumed to work; it was **executed**:

```
pennylane      : 0.44.1
numpy          : 1.26.4
expval         : 0.9199117432272603
grad shape     : (2, 2)
max|ps - bp|   : 2.220e-16
AGREE @1e-9    : True
torch imported : False
```

A 2-qubit `AngleEmbedding` + `BasicEntanglerLayers` QNode on `default.qubit`, differentiated two ways
(`diff_method="parameter-shift"` and `diff_method="backprop"`, both `interface="autograd"`). The gradients
agree to **2.22e-16**, and `torch` is absent from `sys.modules`. This is the P1 engine's differentiation
story, proven on day one, and it doubles as the template for the P1 "backprop vs parameter-shift agreement"
test the master prompt requires.

**Finding — a real deprecation warning, recorded not suppressed:**

```
PennyLaneDeprecationWarning: PennyLane v0.44 has dropped maintainence support for NumPy < 2.0.0.
You have version 1.26.4 installed. Future versions of PennyLane will not work with NumPy<2.0.
```

PennyLane 0.44.1 still works on numpy 1.26.4 (proven above). The pin exists because `cirq-core 1.4.1`
requires `numpy<2`. This is a known, documented, *future* tension: a later PennyLane upgrade will force a
numpy upgrade that cirq cannot take. **Out of scope for this task — the pins do not move (§1.3).** Logged so
the decision is deliberate rather than accidental.

---

## 4. Integration surface (verified by reading, with line numbers)

### 4.1 Backend

| Concern | Location | Notes for QML |
|---|---|---|
| Settings | `backend/app/config.py` | `celery_soft_time_limit: int = 8` (`:24`), `celery_hard_time_limit: int = 15` (`:25`), `celery_task_always_eager` (`:28`). **No feature-flag convention exists** — `qml_enabled` will be the first. |
| Router registry | `backend/app/api/router.py:17-26` | 10 `include_router` calls. QML adds **one**, flag-gated. |
| Auth dependency | **`backend/app/deps.py`** (not `app/api/deps.py` — the reuse map's path was wrong) | Routers use `from app.deps import get_current_user` (and `require_roles`). |
| Error envelope | `backend/app/api/jobs.py:120,127` | `HTTPException(status_code=422, detail={"errors": [...]})`. QML validation errors copy this shape. |
| Celery app | `backend/app/workers/celery_app.py` | `include=["app.workers.tasks"]` (`:11`); `conf.update` (`:14`) sets `task_soft_time_limit`/`task_time_limit` **globally** (`:20-21`), plus `task_acks_late=True`, `worker_prefetch_multiplier=1`, `task_track_started=True`, `task_always_eager` from settings. |
| Existing task | `backend/app/workers/tasks.py:57` | `@celery_app.task(bind=True, name="app.workers.tasks.run_simulation")`; sets `status="running"`, `started_at`, `celery_task_id = self.request.id`; catches `SoftTimeLimitExceeded` at `:109`. |
| Global-limit proof | `backend/app/workers/tasks.py:96` | `budget = max(5.0, get_settings().celery_soft_time_limit - 1.0)` — existing code **derives a timeout from the global setting**. Raising it to suit QML would silently change qBraid's remote-wait budget. This is the concrete reason §1.1 forbids touching it. |
| Job model | `backend/app/models/job.py` | `SimulationJob`: `status` (indexed), `run_hash` (indexed), `result` JSON, `error`, `celery_task_id`, `created_at`/`started_at`/`finished_at`. The shape `QmlExperiment` mirrors. |
| Idempotency | `backend/app/api/jobs.py:150-166` | Pre-insert `select(SimulationJob).where(run_hash==…, user_id==…, status=="completed").order_by(desc(id)).limit(1)`; on hit returns the cached row. **Copy this; do not invent an idempotency system.** |
| Migrations | `backend/alembic/versions/` | 8 files, chain **linear**: `b5f10b499a50` (root) → `c7a2e4d19b30` → `d8b3f6c02a11` → `e9c4a7d31b22` → `f1a2b3c4d5e6` → `a2b3c4d5e6f7` → `g2a5b8c1d4e7` → `h3c6d9e2f5a8` (**head**). Verified by `alembic upgrade head` applying all 8 in order. |
| Model registry | `backend/app/models/__init__.py` | Flat re-export list. QML adds **one** import line. |
| PennyLane idioms | `backend/app/quantum/backends/pennylane_sim.py:27-69` | `run(ir, shots=1024, *, seed=None)`; `qml.device("default.qubit", wires=n)` (`:43`); `@qml.qnode(dev)` (`:45`, `:50`); `np.random.default_rng(seed)` (`:69`). Seeding discipline to copy. |
| Validator precedent | `backend/app/quantum/qudit_lab/validator.py` | Module-level caps (`DIMENSION_MAX_QUDITS`, `MAX_CIRCUIT_OPERATIONS = 150`), `estimate_resources()` + `validate_qudit_circuit()` returning structured errors. QML's validator follows this. |

**No cancellation precedent exists.** `grep -rn "revoke\|terminate" app/ --include=*.py` returns only
unrelated hits in `app/services/codelab.py` (sandbox capability revocation). There is no cancel endpoint in
`jobs.py` and no Celery `revoke` anywhere. **P2 cooperative cancellation is greenfield** — it will be a
DB-flag check between minibatches, not a Celery revoke.

### 4.2 The §7 nested-config trap — reproduced, not quoted

`backend/app/quantum/noise_lab/models.py` declares `enabled: bool = False` on five groups
(`:37`, `:64`, `:75`, `:83`, `:90`) inside `NoiseConfig` (`:95`). Executed:

```python
cfg = NoiseConfig(depolarizing=0.35, amplitude_damping=0.1, t1=50.0)
# flat payload accepted : True
# model_config.extra    : <default: ignore>
# every group enabled?  : {'decoherence': False, 'stochastic': False,
#                          'coherent': False, 'readout': False, 'correlated': False}
```

A caller who sends a flat, plausible-looking noise payload gets **silently ignored input and a
noiseless result that looks like a real answer**. Nothing raises.

**Binding consequence for the QML schema:** `model_config = ConfigDict(extra="forbid")` on every QML model,
required nesting with no silent fallbacks, and a test that asserts a flat/misshapen payload raises **422**
rather than returning a default-shaped success. Wrong shape must fail loudly.

### 4.3 Frontend

| Concern | Location | Notes for QML |
|---|---|---|
| Routes | `src/App.tsx:68-78` | 11 routes + `<Route path="*" element={<NotFound />} />`. QML adds one lazy import + one route, flag-gated. |
| Nav | `src/components/shell/nav.ts:25-46` | 9 items in 4 sections (`study`, `build`, `practice`, `insights`). QML Lab belongs in **`build`**, beside `Qudit Lab (Beta)`. |
| API client | `src/api/client.ts` | Exports `ApiError` (`:8`), `API_BASE = envBase ?? "/api"` (`:57`), `request<T>` (`:59`), `api` (`:99`). 14 modules in `src/api/`. QML adds `src/api/qml.ts` on top of `api` — **never a raw `fetch`**. |
| Circuit rendering | `src/components/results/CircuitDiagram.tsx:44` | `export function CircuitDiagram({ ir }: { ir: CircuitIR })`. Reused by the P3 Circuit View. |
| Test stack | `frontend/web/scripts/*.mts` (20 files), 29 npm scripts | No vitest/jest/@testing-library/jsdom (`grep -c` → **0**). New tests are `.mts` harnesses registered in `package.json`. |
| Charting | — | No `recharts`/`chart.js`/`d3`/`victory`/`nivo`/`visx` (`grep -cE` → **0**). All QML charts are hand-rolled SVG. |
| Installed UI deps | `package.json` | `@radix-ui/react-dialog`, `@radix-ui/react-select`, `@radix-ui/react-tooltip`, `lucide-react`, `clsx`, `zustand`, `@tanstack/react-query`, `tailwindcss`. Nothing else may be added. |

Full UI detail — tokens, the `bg-card` trap, the QL-001 rule — is in [`ui-audit.md`](./ui-audit.md).

---

## 5. Proposed QML structure (no code written yet)

### 5.1 New modules (all net-new files)

```
backend/app/quantum/qml/            # engine — pure, no FastAPI, no Celery
  __init__.py
  config.py                         # strict Pydantic schema, extra="forbid", all limits
  datasets.py                       # moons / circles / binary-iris, seeded; scaler fit on TRAIN split only
  encoding.py                       # angle encoder
  circuits.py                       # variational circuit builder
  model.py                          # VQC: predict / params / save / load (JSON + npz, never pickle)
  trainer.py                        # minibatch loop, real loss, progress + cancel callbacks, seeded
  evaluator.py                      # accuracy, confusion matrix, loss curve
  baseline.py                       # classical reference (logistic regression)
  manager.py                        # artifact persistence, path sanitisation
  resources.py                      # cost estimate + limit enforcement (shared by API and worker)
backend/app/api/qml.py              # router: create/status/cancel/results/list/describe/inference
backend/app/models/qml.py           # QmlExperiment ORM model
backend/app/workers/qml_tasks.py    # Celery task — per-task time limits live on THIS decorator only
backend/alembic/versions/<new>.py   # additive CREATE TABLE qml_experiments, with a working downgrade()
backend/tests/test_qml_*.py         # real circuits, real gradients
frontend/web/src/api/qml.ts
frontend/web/src/pages/QmlLabPage.tsx
frontend/web/src/components/qml/    # Configuration · CircuitView · TrainingDashboard · Results
frontend/web/scripts/qml-*.mts      # harnesses, registered in package.json
docs/qml/                           # every report and all evidence (never artifacts/, §2.3)
```

### 5.2 Touch points on existing files — the complete list

Nine edits, each minimal and justified. Anything beyond this list is a §5.2 stop.

| File | Edit | Why |
|---|---|---|
| `backend/app/config.py` | add `qml_enabled: bool = False`, `qml_task_soft_time_limit: int = 900`, `qml_task_hard_time_limit: int = 1200` | §1.1 / §1.7. **Existing `celery_*_time_limit` values are not touched.** |
| `backend/app/api/router.py` | one `include_router`, flag-gated | registration |
| `backend/app/workers/celery_app.py` | add `"app.workers.qml_tasks"` to `include=[...]` **only** | task discovery; `conf.update` untouched |
| `backend/app/models/__init__.py` | one import | alembic autogenerate + mapper registration |
| `backend/alembic/versions/` | one new additive migration | §1.6 (pre-authorised) |
| `backend/requirements.txt` | **no change expected** (no torch, §3.1) | — |
| `frontend/web/src/components/shell/nav.ts` | one nav item, flag-gated | navigation |
| `frontend/web/src/App.tsx` | one lazy import + one route | routing |
| `frontend/web/package.json` | `scripts` entries only | test registration |

Untouched, per §4: `ComposerPage.tsx`, `QuditLabPage.tsx`, `components/qudit/*`, `components/noise/*`,
`components/smart_composer/*`, `src/lib/circuitSimulator.ts`, `backend/app/quantum/**` (existing subtrees),
`curriculum.py`, `seed.py`, all existing tests, all existing migrations, `globals.css`.

### 5.3 Defaults proposed for the open decisions

| Parameter | Default | Max | Rationale |
|---|---:|---:|---|
| Qubits | 4 | 8 | master prompt; existing caps (static 20 / dynamic 15 / `PREVIEW_MAX_QUBITS = 12`) are settled and untouched |
| Layers | 2 | 4 | master prompt |
| Samples | 200 | 1 000 | master prompt |
| Epochs | 20 | 100 | master prompt |
| Batch size | 16 | 32 | master prompt |
| Concurrent jobs / user | 1 | 1 | master prompt |
| Density-matrix qubit cap | 4 | **6** | stricter than the state-vector cap, per the master prompt's instruction to propose 4–6; to be re-tuned from measured P4 data |
| Soft / hard task limit | 900 s / 1200 s | — | §1.1, on the QML decorator only |
| Differentiation | `parameter-shift` | — | proven above; `backprop` used in tests as the cross-check oracle |
| Device | `default.qubit` | — | already a dependency, no new install |

Limits are enforced **twice** — in the request validator and again inside the worker — so a job cannot
exceed them even if it was queued before a limit changed.

---

## 6. What Phase 0 did not establish

Stated rather than glossed:

1. **Per-task Celery time limits are unproven on Windows `--pool=solo`.** Verified on Linux in P2;
   the Windows half cannot be executed from this sandbox.
2. **`push-overlay-check` is BLOCKED**, not passing — it needs a token the live API accepts.
3. **The 531 vs 530 file count** is unexplained by `git` because `12d33df` is a root commit.
4. **No Redis/Celery worker ran in Phase 0.** Eager mode only so far; P2 must test both the eager path
   and a real broker path.
5. **No GPU/CUDA-Q work** was attempted — optional and out of scope unless asked.

---

## 7. Exit gate

| Requirement | Status |
|---|---|
| Baseline recorded from first-hand runs | DONE — §2, all 7 gates match |
| Tree clean, HEAD == `origin/main` | DONE — §1 |
| Dependency dry-run recorded | DONE — §3.1, torch declined by choice |
| `docs/qml/00-audit.md` | this file |
| `docs/qml/ui-audit.md` | written |
| `docs/qml/DECISIONS.md` | started |
| Feature code written | **none**, as required |
