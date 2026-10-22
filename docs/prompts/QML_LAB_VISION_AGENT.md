# QML Lab — Repo Truth Sheet & Binding Amendments

**Paste this AFTER `QML_Lab_Master_Prompt.md`, in the same message.** It does not replace that
prompt — it corrects it. Where the two disagree, **this document wins**, because it was written
by reading the repository at `main @ 9cdd3a1` rather than by assumption.

The master prompt was written generically. Several of its instructions are false for this repo,
and two of them would break working features if followed literally. Read §1 and §2 before you
write any code.

---

## 0. Baseline: the numbers you must not move

Recorded at `main @ 9cdd3a1`, re-verified in this sandbox. These are **your regression baseline**.
Any deviation is a failure you caused, not a pre-existing condition.

| Gate | Command | Baseline |
|---|---|---|
| Backend tests | `cd backend; PYTHONPATH=. pytest -q` | **818 passed, 5 skipped** |
| Typecheck | `cd frontend/web; npm run typecheck` | **0 errors** |
| Production build | `cd frontend/web; npm run build` | **PASS**, ~2090 modules, ~639 kB main chunk |
| Render harnesses | `frontend/web/scripts/*.mts` loop | **284 PASS / 57 FAIL** without `API_TARGET`; **307 PASS / 57 FAIL** with it |
| Golden values | `golden-quantum`, `golden-demos`, `golden-grover` | **190 + 804 + 3306 @ 1e-9, all PASS** |
| Accessibility | `npx tsx scripts/a11y-check.mts` | **0 criticals** |
| API routes | `python -c "..."` on `app.main:app` | **58 APIRoute objects** |

⚠ **Use the npm scripts, not bare `npx`.** `package.json` defines
`typecheck: node scripts/link-shared.mjs && tsc --noEmit` and
`build: node scripts/link-shared.mjs && tsc --noEmit && vite build`. Running `npx tsc --noEmit`
directly **skips the `link-shared.mjs` prestep** and fabricates `TS2307` module-not-found errors
that are not real. This is an invocation trap, not a defect — never report it as one.

⚠ **Smoke harnesses need the API on the port they expect.** `API_TARGET` defaults to **8123**,
not 8000. If you start uvicorn on 8000, pass `API_TARGET=http://127.0.0.1:8000` or the harnesses
fail with `ECONNREFUSED` and inflate the FAIL count.

⚠ **Count APIRoutes, not `app.routes`.** The latter includes FastAPI's four built-in doc routes
(`openapi.json`, `docs`, `docs/oauth2-redirect`, `redoc`), giving 62. The baseline is **58**.

**The 57 harness FAILs are pre-existing and expected.** Do not "fix" them, do not delete them,
do not treat them as your regressions. They resolve to exactly four SSR render scripts —
`render-codelab` 9, `render-games` 20, `render-p5` 20, `render-results` 8 (9+20+20+8 = 57).
Hold that per-script breakdown, not just the total: a harness that moves from FAIL to PASS, or a
new script that fails, is a change you must explain. Your gate is **the same 57 and no new ones**.

**PASS is 284 or 307 depending on `API_TARGET`, and both are correct.** Without it,
`smoke-auth` (13 assertions) and `smoke-composer` (10) crash on `ECONNREFUSED` *before printing any
assertion*, so they **deflate PASS** rather than adding to FAIL. 284 + 23 = 307. FAIL is **57
either way**, which is the number that actually gates you. State which mode you ran in.

Two further environment notes: piping `tsx` output into `tail` truncates it, so redirect the
golden suites to files and then read them. And `scripts/push-overlay-check.mts` is
**environment-blocked, not passing** — it seeds a fabricated token that a live API rejects with
`401`, so the `aside` it waits for never renders. It contributes 0 PASS and 0 FAIL to the tally;
record it as BLOCKED rather than counting it either way.

There is **no CI**. Nothing runs these for you. Every gate is your responsibility, and every
claim needs pasted command output.

---

## 1. Corrections to the master prompt — these assumptions are FALSE here

### 1.1 The Celery time limit will kill every training job *(highest-risk item)*

`backend/app/config.py:24-25`:

```python
celery_soft_time_limit: int = 8
celery_hard_time_limit: int = 15
```

These are **global** and are set deliberately low, because every existing task is a short
circuit simulation. `celery_app.py` applies them to all tasks via `conf.update(...)`, and
`backend/app/workers/tasks.py:96` computes a wait budget *from* `celery_soft_time_limit`.

A QML training run takes minutes. Under the global limit it would be `SoftTimeLimitExceeded`
at 8 s and hard-killed at 15 s — every single time.

**Do NOT raise the globals.** That silently changes the failure semantics of `run_simulation`
and `autograde_attempt`, which is exactly the kind of collateral damage §3 of the master prompt
forbids, and it would be invisible until a simulation job started hanging for minutes.

**Required approach:** give the QML task its own limits and its own settings, leaving the
existing ones untouched:

```python
# config.py — additive, do not edit the two existing lines
qml_task_soft_time_limit: int = 900
qml_task_hard_time_limit: int = 1200

# the QML task decorator
@celery_app.task(bind=True, name="app.workers.tasks.run_qml_training",
                 soft_time_limit=get_settings().qml_task_soft_time_limit,
                 time_limit=get_settings().qml_task_hard_time_limit)
```

Then prove it: a test that an existing simulation task still dies at ~8 s, and a QML task
survives past 15 s.

### 1.2 PennyLane is already installed and already used

`backend/requirements.txt:41-42`: `pennylane==0.44.1`, `pennylane-qiskit==0.42.0`.
Already imported in **7 files**: `backend/app/quantum/backends/pennylane_sim.py`,
`quantum/codegen_pennylane.py`, `quantum/inspect.py`, `api/jobs.py`, `services/codelab.py`,
`services/codelab_ai.py`, `workers/tasks.py`.

So Phase 1's "add PennyLane" is not a dependency task — it is a **reuse** task. Read
`pennylane_sim.py` first and match its device/qnode idioms. Do not introduce a second,
competing way of constructing PennyLane circuits.

### 1.3 `numpy` is deliberately pinned below 2.0 — do not let torch break it

`backend/requirements.txt:2-3` says so explicitly:

> *cirq-core 1.4.x requires numpy<2 while newer PennyLane requires numpy>=2, so numpy is held
> below 2.0 and PennyLane/pennylane-qiskit are pinned to match.*

Current: `numpy==1.26.4`, `scipy==1.17.1`. This pin is load-bearing for cirq.

If you need PyTorch, **resolve before installing**:

```bash
cd backend
python -m pip install --dry-run "torch==<candidate>" 2>&1 | grep -iE "numpy|would install"
```

If the resolver wants `numpy>=2`, **STOP** per §5. Do not upgrade numpy to accommodate torch,
and do not add torch with `--no-deps`. Note that PennyLane's `default.qubit` supports
`interface="autograd"` and `diff_method="parameter-shift"` with **no torch at all** — for
Phase 1 that is likely sufficient and avoids the entire conflict. Reach for torch only in
Phase 5 (Hybrid QNN), and only after the dry-run passes.

### 1.4 There is no charting library — and you may not add one

The master prompt says "reuse the existing chart library" for loss/accuracy curves.
**There is none.** `frontend/web/package.json` contains no recharts, chart.js, d3, victory,
nivo or visx.

The repo's actual pattern is **hand-rolled SVG using design tokens**. Follow it:

- `src/components/results/CircuitDiagram.tsx` — SVG circuit rendering
- `src/components/grover/GroverLab.tsx` — SVG bar/amplitude plots
- `src/components/results/InteractiveBlochSphere.tsx` — SVG sphere
- `src/components/illustrations/*.tsx` — SVG empty states

Build `LossCurve` / `AccuracyCurve` / `ConfusionMatrix` as small SVG components from those
primitives, coloured with `var(--accent)`, `var(--ok)`, `var(--warn)`, `var(--danger)`,
`var(--line)`. Adding a chart library would violate "no new UI library", inflate the 638 kB
bundle, and look foreign next to every existing plot.

### 1.5 There is no frontend component/unit test stack — use the `.mts` harness pattern

The master prompt says "component/unit tests per the repo's frontend test stack".
**There is none**: no vitest, no jest, no `@testing-library`, no jsdom.

The real frontend test stack is **20 TypeScript harness scripts** in
`frontend/web/scripts/*.mts`, run with `npx tsx`, driven by Playwright where a browser is
needed, and registered as npm scripts in `package.json` (`golden:quantum`, `render:composer`,
`a11y`, `smoke:composer`, …).

So Phase 3's tests are `.mts` scripts. Wire every new one into `package.json` scripts — an
unwired check is an unrun check. Prove each one can fail (break the thing it asserts, watch it
go red, restore it). This is the repo's standing rule, and the previous QA campaign was judged
on it.

**Do not cite `scripts/verify-all-demos.mts` as evidence.** Its assertions at lines 119-123 are
tautological — it passes regardless of correctness. Use the 4,300 golden values instead.

### 1.6 A database migration IS required — you are pre-authorised

The master prompt says stop and ask if a migration seems necessary. For this feature it is
unavoidable: an experiment record needs a table. **Do not stall on it.** You are authorised to
add one, under these conditions:

- Alembic is already set up: `backend/alembic.ini`, `backend/alembic/env.py`, and
  **8 existing migrations** in `backend/alembic/versions/`
  (`b5f10b499a50_initial_schema.py` … `a2b3c4d5e6f7_stable_topic_identifiers.py`).
- Register the new model in **`backend/app/models/__init__.py`** or autogenerate will not see it.
- Additive only. **Never** alter, drop or rename an existing table or column.
- **Two tables are authorised**, not one — see §2A for the shape and the reason.
- Write `downgrade()` and **actually run it** to prove the rollback works. Paste the output.
- Use the existing revision-id style and `Revises:` chain correctly — head must stay linear.

⚠ **Gotcha that will waste you an hour:** pytest must run from `backend/` with `PYTHONPATH=.`.
Run it from the repo root and `test_curriculum.py::test_downgrade_places_every_lesson_and_preserves_secondary_placements`
fails with `alembic.util.exc.CommandError: Path doesn't exist: '.../alembic'`. That is an
invocation bug, **not** a defect — never report it as one, and never "fix" it by editing the test.

### 1.7 There is no feature-flag convention — you are creating the first one

The master prompt requires a flag, off by default, and says to follow existing conventions.
**There are none**: no `feature_flag`, no `/config` endpoint, no frontend gating mechanism.

Build it in the repo's existing idiom — `pydantic_settings.BaseSettings` fields in
`backend/app/config.py`, snake_case, env-overridable, defaults in code:

```python
#: Quantum ML Lab. Off by default; the app must behave exactly as before when disabled.
qml_enabled: bool = False
```

Then: gate the router in `backend/app/api/router.py` (flag off ⇒ routes absent, so 404),
gate the nav item in `frontend/web/src/components/shell/nav.ts`, gate the route in
`frontend/web/src/App.tsx`. Expose the flag to the browser through a small authenticated
endpoint rather than a build-time constant, so one image can be flipped by env. Prove both
states with pasted output — flag off must be byte-identical in behaviour to today.

Note there is no precedent for a flag-gated nav item; **Noise Lab and Smart Composer are not
separate routes at all** — they are embedded inside `ComposerPage.tsx` (imports at `:60-61`,
mounted at `:584` and `:824`). QML Lab is big enough to warrant its own route; that is a
deliberate, documented departure, not an inconsistency.

---

## 1A. The dependency gap you have not hit yet — decide it in Phase 1, not mid-Phase 1

`backend/requirements.txt` has **28 dependencies and neither `scikit-learn` nor `torch` is among
them.** What you have for numerics is `numpy==1.26.4`, `scipy==1.17.1` and `pennylane==0.44.1`.
(`autograd` arrives as a PennyLane dependency, which is why the no-torch path you proved works.)

Three things the master prompt asks for are conventionally sklearn imports, and **none of them
exist here**:

| Master prompt asks for | Usual source | Status |
|---|---|---|
| Seeded datasets — two moons, circles, reduced binary Iris | `sklearn.datasets` | **absent** |
| Scaler fit on the train split only | `sklearn.preprocessing.StandardScaler` / `MinMaxScaler` | **absent** |
| Classical baseline — logistic regression / MLP | `sklearn.linear_model` / `neural_network` | **absent** |

**Binding decision: implement all three with `numpy` + `scipy`. Do not add scikit-learn.**

Rationale: the master prompt permits only dependencies that are *required*, and none of these
are. Logistic regression with L2 via `scipy.optimize.minimize` is a few dozen lines and fully
deterministic under a seed; two-moons and circles are closed-form samplers; a standardiser is
two array operations. Adding sklearn would pull `joblib` and `threadpoolctl` alongside it for a
feature whose only job is to be a comparison point — and a heavyweight reference implementation
would mask bugs in your own code rather than exposing them.

What this obliges you to do, because hand-rolling removes the safety net:

- **Datasets must be verified, not assumed.** Test the shape, the class balance, that the seed
  reproduces bit-for-bit, and that the classes are actually separable to the degree you claim.
  A malformed dataset silently caps achievable accuracy and makes the QNN look bad for a reason
  that has nothing to do with the QNN.
- **Scaler leakage is your responsibility.** Fit on the train split *only*; assert in a test that
  the fitted mean/scale equal the train split's statistics and **not** the full dataset's. This
  is the single easiest thing to get subtly wrong and the hardest to notice afterwards.
- **The baseline must be a real trained model**, not a constant or majority-class predictor.
  Test it against a floor: on a linearly separable seeded dataset it must reach a stated
  accuracy, and its coefficients must move from their initialisation. Otherwise the
  quantum-vs-classical comparison in Phase 3 view D is meaningless.
- **Evaluator metrics must be checked against hand-computed values** on a small fixed prediction
  vector, since there is no sklearn to cross-check against. Compute the expected accuracy,
  precision, recall, F1 and confusion matrix in the test itself, from first principles.

If you reach a point where you genuinely cannot make one of these trustworthy without sklearn,
**STOP and ask** (§5). Do not `pip install` it silently, and do not add it to `requirements.txt`
without saying so in the phase report and justifying it against the master prompt's §4.

Same rule for the PennyLane deprecation warning you already noticed: record **which** API is
deprecated and build Phase 1 on the non-deprecated path. Do not ship a module whose core call
emits a warning — it will break on the next PennyLane bump and nobody will know why.

---

## 2. Binding branch rules — the master prompt's §1 is overridden

The master prompt says *"work only on `feature/quantum-ml`, never modify `main`"*. **That is
overridden.** This repo works on `main` only. A previous agent built on a stale base on a side
branch, and the result was a 47-file resurrection of a deleted app plus 43 MB of force-added
artifacts, none of which reached `main`. Do not repeat that.

### 2.1 `main` is the source of truth; your harness may pin you to a session branch

`main` is authoritative and is the only branch that ships. If your harness pins this session to a
branch of its own, that is **accepted, not a deviation to apologise for** — but it is conditional,
because the last time an agent built on a side branch it resurrected 47 deleted files and none of
its work reached `main`.

Start every phase like this, and paste the output:

```bash
cd /path/to/quantum-learning-platform
git fetch --all --prune
git fetch --deepen=300 origin main      # see the shallow-clone warning below
git status                               # must be clean; if not, STOP (§5)
git rev-parse --short origin/main        # record this — it is the baseline you build on
```

**The additive check — run it at the start AND end of every phase:**

```bash
git diff --diff-filter=MD --name-only origin/main HEAD   # must be EMPTY
git diff --diff-filter=A  --name-only origin/main HEAD   # only files you added on purpose
```

Zero modified and zero deleted files relative to `origin/main`, until a phase deliberately edits
something in §4's allowlist — and then only those. If that check ever shows a modification you
did not intend, or a deletion, **stop and report it**. This single check is what would have
caught the Streamlit resurrection before it was committed.

Never `--force`. Never `--force-with-lease`. Never push to `main` if your harness forbids it;
say so plainly in the phase report and name the branch you did push to, so the port to `main`
is mechanical rather than archaeological.

⚠ **The shallow-clone trap.** A freshly provisioned sandbox may be a **depth-1 shallow clone**.
That makes `main`'s tip look like a *root commit* and makes `git merge-base` against your branch
return nothing, which invites the wrong conclusion that history was rewritten or that the
branches are unrelated. `main` actually has **224 commits**. Before drawing *any* conclusion
about history, run `git rev-parse --is-shallow-repository`; if it says `true`, deepen first.
Also note the agent-side ref may not exist locally as `origin/<branch>` until you fetch it
explicitly into a remote-tracking ref — `FETCH_HEAD` alone will make later commands fail with
`ambiguous argument`.

⚠ **The stale-local-`main` trap.** Pushing with `HEAD:main` while your local `main` ref lags
behind produces nonsense comparisons — `git diff main <sha>` will claim files are missing that
are plainly present. Always compare against **`origin/main`**, never bare `main`.

⚠ **Never run `git checkout origin/main -- .`** to "sync". It overwrites files but **never
deletes** them, so anything removed from `main` reappears in your working tree as untracked
cruft and can be committed by a later `git add -A`. Sync by fetching and resetting, not by
checking paths out over your tree. If you must snapshot stale local state first so nothing is
unrecoverable, commit the snapshot to your own branch and say so.

### 2.2 The flag replaces branch isolation

The master prompt wanted a side branch so `main` stayed safe. Here, **`qml_enabled = False` is
the safety mechanism**, and it has to be stronger than a branch would have been: whatever branch
carries the work, its content must be deployable after *every* commit, not just at the end.
Commit in small verified steps (§10 of the master prompt) and keep the flag off until Phase 8.

### 2.3 Commit hygiene — the two things that got the last agent in trouble

- **`artifacts/` is gitignored** (`.gitignore:29`). Do **not** `git add -f` anything under it.
  Your evidence — reports, benchmarks, screenshots — goes in **`docs/qml/`**, which is tracked.
  Never commit screenshots you do not cite; the last campaign shipped 43 MB / 392 files and only
  91 were referenced.
- **Do not resurrect deleted code.** The Streamlit app was removed on purpose. These paths must
  stay absent: `frontend/pages/`, `frontend/lib/`, `frontend/live_bloch/`, `frontend/tests/`,
  `.streamlit/`, `frontend/Home.py`. If you find any of them in your working tree, they are
  leftovers — delete them, do not commit them. Tracked-file count: **531** at the Phase 0
  baseline, **558** on `main` after the Phase 1 port (`main @ 6169f0b`). Compare against
  `origin/main` as it is when you start, and account for every file you add.
- Also gitignored and never to be committed: `*.db`, `*.db-wal`, `dev.db`, `dist/`, `.venv/`,
  `node_modules/`.

---

## 2A. Phase 2 decisions, settled in advance

These were the two open questions Phase 2 would otherwise have stopped on. Both are decided;
build to them.

### 2A.1 Migration shape — two tables: normalise the time series, blob the document

```
qml_experiments                      qml_epoch_metrics
  id                PK                 id                PK
  user_id           FK users.id, idx   experiment_id     FK qml_experiments.id, idx
  run_hash          String(64), idx    epoch             Integer
  status            String(32), idx    train_loss        Float
  config            JSONType           val_loss          Float, nullable
  result            JSONType, nullable train_accuracy    Float
  error             Text, nullable     val_accuracy      Float, nullable
  celery_task_id    String(128), null  elapsed_seconds   Float
  cancel_requested  Boolean, dflt F    UniqueConstraint(experiment_id, epoch)
  model_path        String(512), null
  created_at / started_at / finished_at   (server_default=func.now(), as SimulationJob)
```

`status` is the state machine from the master prompt: `queued | running | completed | failed |
cancelled | timed_out`.

**Why not a single row with the epoch history in a JSON blob** — this is the expensive-to-reverse
choice, so the reasoning matters:

1. **SQLAlchemy does not detect in-place mutation of a JSON column.** Unless you wrap it in
   `MutableDict` or call `flag_modified()` every time, an appended epoch silently never persists.
   The symptom is a progress bar that never moves, and it looks like a frontend bug. The trainer
   would be doing a read-modify-write of a growing column up to 100 times per job to publish
   progress. Appending a row has no such failure mode.
2. **Polling becomes incremental.** `WHERE experiment_id = ? AND epoch > ?` returns only what the
   dashboard hasn't seen, instead of re-downloading the whole history every poll.
3. **`UniqueConstraint(experiment_id, epoch)` buys idempotency for free.** `celery_app.py` sets
   `task_acks_late=True`, so **task redelivery is real** — Celery is at-least-once. A redelivered
   epoch must not duplicate, and must not crash the job.
4. **`cancel_requested` as its own column** means cancelling is a single-column `UPDATE`, not a
   read-modify-write of the whole row — which matters because the worker polls it every batch.

Config and final result stay JSON blobs: they are write-once/read-many documents, and this matches
the house pattern (`SimulationJob.circuit_ir`, `.noise`, `.result`).

`run_hash` is the duplicate-submission guard the master prompt asks for — copy
`SimulationJob.run_hash` (`models/job.py:22`) and the cache lookup at `api/jobs.py:154-170`.

Model artifacts (`persistence.py`'s JSON + `.npz`) go to a **file** path recorded in `model_path`,
resolved from a new `qml_artifact_dir` setting and joined **only** with the integer experiment id.
Never with a user-supplied string. That directory must be gitignored — never commit a trained
model.

### 2A.2 Timeouts — the cooperative deadline is primary; Celery's limits are the backstop

**§5.7 is discharged. Do not stop on the Windows question.** The answer is a platform fact, not
something to discover by experiment:

- Celery implements `soft_time_limit` with **SIGALRM**, which does not exist on Windows. Soft
  limits are unenforceable there.
- `time_limit` (hard) works by killing the worker's **child process** under prefork. With
  `--pool=solo` the task runs in the worker's own main thread, so there is no child to kill — the
  hard limit cannot fire without killing the worker.

So on Windows + `solo`, **neither** limit is reliable, and no amount of Linux-sandbox testing will
tell you otherwise. Build both layers:

- **Celery per-task limits** — `soft_time_limit` / `time_limit` on the QML decorator only, from new
  `qml_task_soft_time_limit` / `qml_task_hard_time_limit` settings. Never the globals (§1.1). This
  layer works in Docker, WSL2 and any Linux worker — which is how the app actually ships, since
  `docker-compose.yml` has a `worker` service.
- **A cooperative `deadline_seconds` on `train()`** — checked in the *same place* `should_cancel()`
  is already checked (before every batch and at end of every epoch), using the `time.perf_counter()`
  the trainer already imports for elapsed reporting. On expiry: return `timed_out`, clean partial
  artifacts, leak no exception. Pure Python, so it works on every platform. This is the layer that
  actually protects the user's machine.

**Set the in-trainer deadline strictly below the Celery soft limit** (soft 900 → deadline ~870),
derived from the same settings rather than hardcoded. Then the cooperative path always wins and the
user gets a clean `timed_out` with a readable message, instead of a `SoftTimeLimitExceeded`
traceback. Celery's limit is left to catch a genuinely hung, non-cooperative task.

Prove on Linux: (a) the deadline fires and yields `timed_out` — set it to ~1 s with a config slow
enough to exceed it; (b) the §1.1 both-directions test — an existing simulation task still dies at
~8 s while the QML task survives past 15 s. **Document, do not test,** the Windows/`solo`
limitation, and say plainly that the cooperative deadline is the platform-independent mechanism.

### 2A.3 Two more Phase 2 decisions, so you don't have to ask

**Concurrency = 1 needs two mechanisms, not one.** `run_hash` covers *duplicate submission* (same
config), not *concurrency* (two different configs). A DB count alone is racy. So: route QML tasks to
a **dedicated `qml` queue** via `task_routes`, which makes worker concurrency structurally 1 — that
is the guarantee — **and** check for non-terminal experiments before dispatch, returning a clean
**409** with a readable message. The queue guarantees it; the DB check explains it to the user.
Note `worker_prefetch_multiplier=1` is already set, which helps but is not the guarantee.

⚠ **Scope the guard globally, not per user.** `limits.py:43` names the constant
`MAX_CONCURRENT_JOBS_PER_USER = 1`, but the master prompt's table says *"Concurrent training jobs |
1 | 1"* with no qualification, and the resource being protected is **the machine** — one worker on
a 16 GB laptop — not a per-user quota. So the pre-dispatch check must count non-terminal
experiments **across all users**:

```python
db.query(QmlExperiment).filter(QmlExperiment.status.in_(("queued", "running"))).count()
```

not `... .filter(QmlExperiment.user_id == user.id, ...)`. With the per-user form, two users each
pass the check and both dispatch; the queue still serialises them, but the second user gets a
silent multi-hour wait instead of the immediate 409 that tells them the truth. Rename the constant
to `MAX_CONCURRENT_JOBS` so the name matches the semantics. If per-user fairness is wanted later,
add it as a *second*, tighter cap on top of the global one — the global cap is the binding
constraint and must exist regardless.

**The cancel endpoint has no precedent here** — you found that in Phase 0. So:
`POST /qml/experiments/{id}/cancel` sets `cancel_requested = True`; the worker observes it through
the `should_cancel()` hook you already built. It must be **idempotent** (cancelling twice is 200,
not 500) and must reject a terminal experiment with a clear **409**. Ownership mirrors
`api/jobs.py:200-206` — `404` first, then `403 "Not your job"`.

### 2A.4 Phase 2 changes the additive check — this is expected, not a violation

Phase 1 was purely additive. Phase 2 cannot be: it must register things. So §2.1's
`git diff --diff-filter=MD --name-only origin/main HEAD` **will** be non-empty, and that is correct.

**Correction — the earlier "exactly these five" was wrong, and Phase 2 was right not to stop on
it.** §2A.2 directs a `deadline_seconds` parameter on `train()` and §2A.3 directs renaming a
constant in `limits.py`; both files were added in Phase 1 and now live on `main`. A five-file
allowlist that contradicts two other clauses in the same section is a drafting error, not a
constraint. The real rule is:

> Every modification must trace to an explicit clause in §2. Anything you cannot trace, stop on.

For Phase 2 that resolves to **eight** modified files, and this is the expected set:

```
backend/app/api/router.py            §2A.4  flag-gated include_router
backend/app/config.py                §2A.4  add qml_* settings only
backend/app/workers/celery_app.py    §2A.4  extend include=[...] and add task_routes
backend/app/models/__init__.py       §2A.4  register the two new models
backend/app/quantum/qml_lab/trainer.py     §2A.2  deadline_seconds
backend/app/quantum/qml_lab/limits.py      §2A.3  rename MAX_CONCURRENT_JOBS
backend/tests/test_qml_config.py           §2A.3  follows the rename
docs/qml/DECISIONS.md                      §2A.4  fold in D-013…D-016
```

The alembic migration is a **new** file, not a modification — it belongs in the added list.

New files: `backend/app/api/qml_lab.py`, `backend/app/models/qml.py`,
`backend/app/services/qml_lab.py`, `backend/app/workers/qml_tasks.py`,
`backend/alembic/versions/<new>.py`, and tests.

**Verify the two things that must NOT change:** in `config.py`, `celery_soft_time_limit = 8` and
`celery_hard_time_limit = 15` stay exactly as they are (your additions are new lines, not edits to
those); in `celery_app.py`, the existing `conf.update(...)` entries are untouched and `task_routes`
is added alongside them. Paste both diffs — they are small and they are the proof that §1.1 held.

### 2A.5 The `qml` queue needs a worker that consumes it — and do NOT reuse the existing one

`docker-compose.yml:81` starts the worker as:

```
celery -A app.workers.celery_app.celery_app worker --loglevel=info --concurrency=2
```

There is **no `-Q`**, so it consumes only the default `celery` queue. Once `task_routes` sends QML
tasks to `qml`, **the shipped worker will never execute them** — every experiment sits `queued`
forever with no error anywhere. That is a silent failure at exactly the moment someone turns the
flag on, which is the worst time to discover it.

⚠ **Do not "fix" this by adding `-Q celery,qml --concurrency=1` to the existing worker.** That
would drop simulation concurrency from 2 to 1 and halve the throughput of a shipped feature — the
collateral damage the master prompt's §3 forbids. The QML guarantee must not be bought with an
existing feature's performance.

**Required: a second, dedicated worker service**, additive, with the existing one untouched:

```yaml
  qml-worker:
    profiles: ["qml"]          # does not start unless explicitly enabled
    build:
      context: ./backend
    env_file:
      - path: .env
        required: false
    environment:               # mirror the worker service's variables
      DATABASE_URL: ${DATABASE_URL:-postgresql+psycopg://quantum:quantum@postgres:5432/quantum_learn}
      REDIS_URL: ${REDIS_URL:-redis://redis:6379/0}
    volumes:
      - ./backend:/app
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    command: celery -A app.workers.celery_app.celery_app worker --loglevel=info -Q qml --concurrency=1
```

`profiles: ["qml"]` is what keeps today's behaviour byte-identical: `make up`
(`docker compose -f docker-compose.yml -f docker-compose.gpu.yml up`) does not start it, so nothing
changes while the flag is off. Enabling QML then becomes a two-part, documented action —
`QML_ENABLED=true` **and** `--profile qml` — which belongs in `docs/qml/08-release.md` as the
enablement procedure, with the rollback being the reverse.

No GPU is needed: QML is CPU statevector by decision, so `docker-compose.gpu.yml` should not have
to mention this service at all. Confirm the overlay does not accidentally apply `gpus: all` or
`INSTALL_CUDAQ` to it.

Two follow-ups this creates, both for Phase 2's report rather than new code:

- `qml_artifact_dir` defaults to the **relative** `"artifacts/qml"`. The API and the worker must
  resolve it to the same absolute path or `load_model` will fail on a path the other process wrote.
  In Docker both build from `./backend` with the same workdir, so it holds — but **verify it** and
  say so, and prefer storing the resolved absolute path (or just the experiment id, re-resolved on
  load) in `model_path` so the record cannot go stale if a workdir ever differs.
- `artifacts/` is gitignored (`.gitignore:29`), which is correct for trained models. Confirm no
  artifact is committed.


### 2A.6 Flag delivery to the browser — your `GET /qml/features` is in the wrong place

You asked for a sanity-check on this, and it needs one: **an endpoint that only exists when the
feature is enabled cannot be the thing the UI asks in order to decide whether the feature is
enabled.** That is self-referential, and it makes 404 load-bearing.

Today `GET /features` lives at `backend/app/api/qml_lab.py:96`, inside the router that
`api/router.py` mounts only when `qml_enabled` is true. So with the flag off the nav's source of
truth returns 404 — and **404 is indistinguishable** from a typo'd path, a proxy misconfiguration,
a stripped `/api` prefix, or a backend that failed to boot. The nav would then be deciding
visibility by pattern-matching an error, and any of those unrelated failures would silently hide a
feature that is actually on. Fail-closed is the right default, but it must fail closed *because the
server said so*, not because a request broke.

**Required: split the two concerns.**

1. **Visibility — always-mounted, never 404s.** Add `backend/app/api/features.py` with
   `GET /features` returning `{"qml_enabled": bool}`, and include it in `api/router.py`
   **unconditionally**, next to the existing includes. This route exists whether or not QML is on.
   Precedent: `GET /backends` (`api/jobs.py:45`) is already an always-on, unauthenticated
   capability-discovery endpoint, consumed by `src/api/backends.ts`. A single boolean is less
   sensitive than what `/backends` already publishes, so keep it unauthenticated and consistent —
   that also lets the login screen react if you ever want it to.

   Structure it as a **map of flags**, not a QML-specific payload — `{"qml_enabled": false}` today,
   room for the next feature without a new endpoint:

   ```python
   @router.get("/features")
   def features() -> dict[str, bool]:
       s = get_settings()
       return {"qml_enabled": s.qml_enabled}
   ```

2. **Capability detail — stays gated, 404-when-off is fine.** Keep `/qml/features` (or rename it
   `/qml/capabilities`) inside `qml_lab.py` for the things only a mounted feature can meaningfully
   report: the limits table, the algorithm allow-list, the gradient methods, the dataset names.
   Nothing depends on it for *visibility*, so its 404 is honest — it means "this feature does not
   exist here", which is true.

**Frontend:** `src/api/features.ts` → `api.get<Features>("/features")`, consumed with react-query at
`staleTime: Infinity` (flags do not change within a session). Filter `NAV_ITEMS` in
`components/shell/nav.ts` on it. Three rules:

- **No flash.** While the query is loading, the QML item is **absent** — default to hidden, then
  reveal. Never render it and retract it.
- **Fail closed on error.** A failed `/features` request hides QML; it must not throw, and must not
  be surfaced to the user as an error, because for everyone without the flag this is the normal
  state.
- **The route is gated too, not just the nav.** Hiding a link is not access control. `/qml-lab` must
  render the existing `NotFound` (or a "feature unavailable" state built from `EmptyState`) when the
  flag is off, so a bookmarked or hand-typed URL cannot reach a page whose APIs all 404.

**Test all four states**, because this is the contract four views will rest on: flag off ⇒ no nav
item, `/qml-lab` renders NotFound, `/features` returns `qml_enabled: false`, `/qml/*` returns 404;
flag on ⇒ nav item present, route renders, both endpoints answer. Prove the off state against a
**live server**, as you did in Phase 2 — that is what made the Phase 2 flag proof credible.

This adds one file to §2A.4's expected set: `backend/app/api/features.py` (new) and one more
unconditional `include_router` line in `api/router.py` (already in the set).

---

## 2B. Phase 4 decisions, settled in advance

### 2B.1 Your sandbox is not the target machine — this is the whole problem

The master prompt asks you to benchmark "on this machine" and tune limits from the measurements.
The target machine is an **Intel i5-13450HX, RTX 4050 Laptop, 16 GB RAM, Windows**. Your sandbox is
a Linux container with a different CPU, no GPU and no Docker. **Absolute numbers you measure here
do not transfer**, and limits tuned from them could be wrong in the dangerous direction — a max
config that fits your container's memory can swap a 16 GB laptop to death.

So split the work by what is actually portable:

| Portable — measure here | Not portable — the user must measure |
|---|---|
| **Scaling shape**: how cost grows with qubits, layers, samples | Absolute wall-clock on the target CPU |
| **Gradient-method ratio**: parameter-shift ÷ backprop | Absolute peak RAM |
| **Memory growth law**: 2^n vs 4^n, and the coefficient | The timeout default |
| Determinism and reproducibility across runs | Whether the max config completes without swapping |
| Which configs are *structurally* infeasible | GPU feasibility of any kind |

Your Phase 4 output is therefore **two things**: the scaling laws and provisional limits you can
defend from sandbox data, clearly labelled provisional; and **a script the user runs on their own
laptop** to produce the numbers that actually set the shipped defaults. Do not present sandbox
timings as though they were the target's.

### 2B.2 The deliverable is a script, not a transcript

`backend/scripts/bench_qml.py`, emitting **both** machine-readable JSON and a markdown table, with
a `--quick` mode and a `--full` mode. Wire it into the Makefile or document the exact invocation.
The user must be able to run one command, paste the JSON back, and have the limits fall out of it.
Ad-hoc shell one-liners in a report are not reproducible and do not count.

Record in every run: OS, CPU model, core count, total RAM, Python/numpy/scipy/PennyLane versions,
`shots=None` vs finite shots, and whether measurement was engine-direct or through the API.

### 2B.3 Do the arithmetic before you measure — the bottleneck is not memory

Compute the state memory first: complex128 statevector at n=8 is `2^8 × 16 B = 4 KB`; a density
matrix at n=6 is `4^6 × 16 B = 64 KB`. **Both are negligible.** Raw state size is not the risk at
these qubit counts, and a benchmark report that leads with memory numbers has measured the wrong
thing.

The real cost driver is **gradient method**. Parameter-shift evaluates the circuit **twice per
trainable parameter**. A `StronglyEntanglingLayers`-style ansatz carries roughly 3 parameters per
qubit per layer, so at the current maxima (8 qubits × 4 layers) that is ~96 parameters → **~192
circuit executions per gradient step**. With 1,000 samples at batch 32 that is ~32 batches, × 100
epochs = ~3,200 steps → **~600,000 circuit executions**. Backprop differentiates through the state
once and is orders of magnitude cheaper.

Predict that, then measure it, then report whether the measurement matched. The likely conclusion —
and the one the limits should encode — is:

- **backprop is the default** and must complete the max config inside the timeout;
- **parameter-shift is offered but budgeted**: either a smaller max-qubit/max-layer ceiling when it
  is selected, or an explicit up-front estimate shown to the user before dispatch, or a clean
  rejection above a measured threshold. Pick one and justify it from your numbers.
- Validate this **per gradient method**, not once for the config as a whole. `limits.py` currently
  has one flat ceiling; if the ceiling must depend on `gradient_method`, that is a real design
  change and belongs in `DECISIONS.md`.

### 2B.4 How to derive the timeout, and what must not change

Derive `qml_task_soft_time_limit` from: **measured time for the maximum allowed config under the
default gradient method, on the target machine, × a safety factor you state.** Until the user
supplies target numbers, keep **900 / 1200** and mark them provisional. Per §2A.2 the in-trainer
deadline stays strictly below the soft limit.

- **Tightening a limit with evidence is fine. Loosening one requires my sign-off** — the master
  prompt's "never loosened without evidence" is a floor, not a ceiling.
- **Do not touch the Composer's qubit caps.** static 20 / dynamic 15 / GPU 28 and
  `PREVIEW_MAX_QUBITS = 12` in `src/lib/circuitSimulator.ts` are settled and unrelated to QML.
- `DENSITY_MATRIX_MAX_QUBITS = 6` may be tightened on evidence (4^n grows fast); justify any change.

### 2B.5 GPU is out of scope — and `lightning.qubit` is a proposal, not a change

**Skip the GPU path entirely.** PennyLane's `lightning.gpu` needs CUDA on Linux; the target is
Windows, so it means WSL2, and the repo's existing GPU support is **CUDA-Q via
`docker-compose.gpu.yml`** — a different stack that does not compose with a PennyLane device. Do
not mix them, do not rebuild anything without `-f docker-compose.gpu.yml` (§6), and do not add a
GPU device in Phase 4. Document the reasoning and move on.

Separately: check whether **`lightning.qubit`** (the C++ CPU statevector device, typically several
times faster than `default.qubit`) is *already importable* as a transitive dependency. If it is,
measure it as an alternative device and report the speedup. **If it is not installed, do not add
it** — that is a dependency change under §1.3 and §5.3, and belongs in a proposal with a
`pip install --dry-run` result showing it does not move the `numpy<2` pin. Recording a measured
opportunity you did not take is worth more than an unrequested dependency.

### 2B.6 Measurement discipline — the ways this goes wrong

- **Benchmark the engine directly**, not through the API with `celery_task_always_eager`. Eager mode
  folds in FastAPI, validation and DB writes; that overhead is real but it is a separate
  measurement, and mixing the two makes the scaling curve meaningless.
- **N repetitions, report median and spread.** Never a single run. Five is a reasonable N for the
  quick mode. Exclude a warm-up run — the first PennyLane call pays import and JIT-ish costs.
- **State `shots=None` vs finite shots** on every number. Analytic and sampling execution have
  different costs and different noise.
- **Measure peak RSS, not just elapsed time** (`resource.getrusage(RUSAGE_SELF).ru_maxrss`), and say
  which process it is.
- **Do not tune limits from a run that crashed or was killed.** A config that OOMs is a data point
  about the ceiling, not a timing.
- Every claim in `docs/qml/04-benchmarks.md` needs the command that produced it, per §8.

### 2B.7 What Phase 4 must hand Phase 5

Phase 5 adds five more algorithms, several of which are far more expensive than a VQC — a quantum
kernel builds an **N×N kernel matrix**, so at 1,000 samples that is ~10^6 circuit evaluations before
any SVM runs. Phase 4's job is to establish the *method* (how to measure, how to extrapolate, how to
set a ceiling from a measurement) so Phase 5 can price each new algorithm the same way instead of
inventing a new approach per feature. Say explicitly in the report which of the Phase 5 algorithms
your measured scaling law already lets you bound, and which need their own benchmark.

---

## 3. The UI/UX contract — match this exactly

This is the part most likely to look wrong, so it is specified concretely rather than as
"be consistent".

### 3.1 The design system

- **Tailwind CSS v4**, configured **CSS-first** via `@tailwindcss/vite` (`vite.config.ts:3,33`).
  There is **no `tailwind.config.js`** and you must not add one. Theme lives in CSS.
- **All tokens are CSS custom properties in `frontend/web/src/globals.css`.** Use them; never
  hardcode a hex value, font or spacing scale that duplicates one.

  **There are two token layers, and only one of them produces Tailwind utilities.** Getting this
  wrong is the most likely way your UI silently renders unstyled.

  **Layer 1 — the `@theme` block (`globals.css:4-42`).** These are `--color-*` and `--font-*`,
  and Tailwind v4 turns each into utilities. This is what you use in `className`:

  | Purpose | Utilities that exist |
  |---|---|
  | Surfaces | `bg-bg`, `bg-raised`, `bg-subtle`, `bg-hover`, `bg-active`, `bg-bg-raised`, `bg-bg-subtle` |
  | Text | `text-ink`, `text-ink-2`, `text-ink-3` |
  | Lines | `border-line`, `border-line-soft`, `border-line-focus` |
  | Brand | `bg-accent`, `border-accent`, `text-accent`, `text-accent-ink`, `bg-accent-soft` |
  | Status | `text-ok`, `bg-ok`, `text-warn`, `bg-warn`, `border-warn`, `text-danger`, `bg-danger` |
  | Gate colours | `text-gate-h`, `bg-gate-pauli`, `text-gate-phase`, `bg-gate-param`, `text-gate-multi`, `text-gate-meas` |
  | Type | `font-sans`, `font-mono`, `font-display` |

  Actual usage counts in the existing source, so you can see the house idiom:
  `text-ink-3` 431 · `text-ink` 280 · `border-line` 250 · `text-accent` 168 · `text-ink-2` 143 ·
  `bg-raised` 104 · `bg-subtle` 103 · `border-line-soft` 93 · `bg-accent` 86 · `border-accent` 68 ·
  `bg-hover` 63 · `bg-bg` 45. **Match this distribution** — `text-ink-3` for tertiary labels,
  `text-ink-2` for secondary, `text-ink` for primary, `border-line` for panels,
  `bg-raised`/`bg-subtle` for surfaces.

  **Layer 2 — the `:root, html, body` block (`globals.css:44-92`).** These are bare vars with no
  `--color-` prefix: `--bg`, `--panel`, `--muted`, `--fg`, `--wire`, `--divider`, `--editor-bg`,
  `--endpoint-border`, `--raised`, plus duplicates of the layer-1 names. **These do NOT generate
  Tailwind utilities.** They are only reachable as `var(--panel)` inside a `style` attribute or a
  CSS rule. `--panel`, `--muted`, `--fg`, `--wire` and `--divider` have no `--color-*` twin, so
  `bg-panel` / `text-muted` / `text-fg` **do not exist** — writing them produces nothing.

- ⚠ **`bg-card` is a live trap — do not copy it.** It appears in **10 places across all six Qudit
  Lab files** (`QuditGatePalette.tsx`, `QuditCircuitEditor.tsx`, `DensityMatrixInspector.tsx`,
  `QuditLearnPanel.tsx`, `QuditNoisePanel.tsx`, `QuditLabPage.tsx`), typically as
  `bg-card/60 backdrop-blur-md`. But **`--color-card` is defined nowhere** — not in `@theme`, not
  in the imported composer stylesheet. Tailwind therefore emits no `bg-card` rule and those panels
  get **no background colour at all**; they appear to work only because `border-line` and
  `backdrop-blur-md` are doing the visual work. If you imitate Qudit Lab's markup you will inherit
  this. Use `bg-raised` or `bg-subtle` for card surfaces. **Do not "fix" the existing ten** —
  that is out of scope (§4) and would change how a shipped page looks; just don't propagate it.

- **Verify a utility before you rely on it.** `dist/` is gitignored and ephemeral, so rebuild
  first, then grep the emitted CSS:

  ```bash
  cd frontend/web
  npx vite build
  grep -o "\.bg-raised[^a-z0-9-]" dist/assets/*.css | head -3    # emitted => safe to use
  ```

  The previous campaign's worst defect (QL-001) was a heatmap rendered invisible because
  template-literal class names like `` `bg-[rgba(0,0,0,${a})]` `` are not statically extractable,
  so Tailwind emitted **zero** matching rules and every cell was transparent.

- **Dark is the only theme. Do not build a light mode.** `globals.css` sets
  `color-scheme: dark` and hardcodes `html, body { background-color: #07090e }`, and contains
  **no light-theme selector at all** — there is no `html.light` or `body.light` rule anywhere in
  the file. `src/state/theme.ts` defaults to `theme: "dark"` and toggles `html.dark`/`html.light`
  classes, but nothing in the CSS responds to `.light`. That is pre-existing and **out of scope**:
  do not add light-theme tokens, do not add `dark:` variants, do not wire up or "fix" the toggle.
  Design every QML view against the dark palette only, and screenshot it in the state the app
  actually ships in.

### 3.2 The QL-001 rule — never interpolate a Tailwind class

```tsx
// FORBIDDEN — Tailwind cannot see this, the rule is never emitted, the cell renders transparent
<div className={`bg-[rgba(56,189,248,${mag})]`} />

// REQUIRED — computed value in an inline style
<div style={magStyle(mag)} />          // e.g. { backgroundColor: `rgba(56,189,248,${mag})` }

// ALSO FINE — literal strings in a ternary; both branches are statically extractable
className={active ? "border-accent bg-accent-soft" : "border-line bg-bg-raised"}
```

If you need a data-driven colour, compute it in JS and use `style`. If you need a fixed variant,
write both class strings literally. This is a hard rule, and there is a regression harness for it.

### 3.3 Reuse, in priority order

1. **Existing components.** `src/components/shell/` (`AppShell`, `TopBar`, `Sidebar`,
   `BackendBadge`, `ErrorBoundary`, `NarrowViewportNotice`, `CommandPalette`, `nav.ts`),
   `src/components/results/CircuitDiagram.tsx` (for Phase 3 view B — the master prompt requires
   reusing the circuit visualisation; this is it), `src/components/qudit/*` (panels, inspector,
   editor — the closest structural analogue to what you are building), `src/components/noise/NoiseLabView.tsx`
   and `src/components/smart_composer/SmartComposerPanel.tsx` (a large panel with tabs, forms and
   results — read these two before designing your layout).
2. **Existing primitives.** Radix UI is installed: `@radix-ui/react-dialog`, `react-select`,
   `react-tooltip`. Icons: **`lucide-react`**. Class merging: **`clsx`**. Use these; do not add
   `@radix-ui/*` packages beyond the three, and do not add another icon set.
3. **Existing data layer.** `@tanstack/react-query` for fetching/caching, **`zustand`** for
   client state (see `src/state/theme.ts`, `src/state/session.ts`). Polling for job status
   already exists for simulation jobs — find it and copy the shape, including its cleanup.
4. **The API client.** `src/api/client.ts` is *"one thin fetch wrapper for the whole app"*; it
   throws `ApiError{status,detail}` and formats FastAPI's three `detail` shapes (string /
   pydantic list / `{errors:[...]}`) through `readableError()`. Add `src/api/qml.ts` on top of
   it. **Never** write a raw `fetch` with your own token handling — the token comes from the
   session store so that a 401 always means the same thing.

⚠ **Correction — there IS a shared primitive library, and this section previously said there was
not.** `frontend/web/src/components/ui.tsx` is **798 lines** of exactly the primitives Phase 3
needs. There is no `ui/` *directory* — it is one file — but it is the house component layer, and
hand-rolling equivalents of any of these is how new UI ends up looking foreign.

**Use these, in this order, before writing anything new:**

| You need for Phase 3 | Already exported from `components/ui.tsx` |
|---|---|
| Class merging | `cn(...)` (a `clsx` wrapper) — line 20 |
| Buttons, incl. Start / Cancel | `Button` (`forwardRef`, `ButtonProps`) — 32 |
| Text fields, numbers, textareas | `Input` 69 · `Textarea` 82 · `Label` 98 |
| Panels / cards | `Card` 107 · `Separator` 146 |
| Status chips (queued/running/failed…) | `Badge` 116 |
| Loading + skeleton states | `Spinner` 150 · `Skeleton` 177 |
| Inline error display | `ErrorNote` 165 |
| Algorithm / dataset / optimizer pickers | `Select` 195 · `SelectItem` 263 · `SelectOption` 189 |
| **The four views A–D** | `Tabs` 304 · `TabsList` 331 · `TabsTrigger` 344 · `TabsContent` 375 |
| Confirming a destructive Cancel | `ConfirmModal` 465 (plus the `Dialog*` family, 398-453) |
| Help text on limits | `Tooltip` 525 (plus `TooltipProvider/Root/Trigger`) |
| Transient notices | `ToastProvider` 556 |
| **Empty states** (no experiment yet) | `EmptyState` 580 |
| Config-beside-results layout | `SplitPane` 621 |
| **The predictions table** | `DataTable<T>` 747 with `ColumnDef<T>` 740 |

`DataTable` and `EmptyState` are the two that matter most: the master prompt asks for a predictions
table and for empty states, and both already exist and already match the theme. Do not build a
`<table>` from scratch.

If you genuinely need a primitive that is not in that list, put it in `src/components/qml/` and
build it from `cn()` plus the §3.1 tokens — and say in the phase report which existing primitive
was insufficient and why.

⚠ **`cn()` is plain `clsx` (`ui.tsx:20`) — there is no `tailwind-merge`.** So a utility you pass
does **not** override the same-family utility baked into the primitive; both land in the class list
and the winner is whichever appears later in the generated stylesheet, which is not something you
control. `className="p-4"` on a `Card` whose own classes include `p-6` is a **collision, not an
override**. Do not add `tailwind-merge` to fix it — that is a new dependency and would silently
change the cascade for every existing screen. Either accept the primitive's spacing, wrap it in a
sizing container, or read the primitive's own classes before choosing yours.

⚠ **Read a primitive's signature before calling it.** `ErrorNote` takes `children`, not
`title`/`message`. Phase 3 wrote three wrong call sites this way and only `tsc` caught them.

⚠ **Derive fixture payloads from a real response, never from the type you intended to write.**
Phase 3's render fixture invented `learning_rate`, `noise`, `test_fraction` and `seed` keys that
`/qml/describe` does not return, so the harness was testing a contract that does not exist. Start a
server, capture the actual JSON, commit that as the fixture.

**Polling: copy this exact idiom, do not write `setInterval`.** `ChallengesPage.tsx:966-976` and
`GamesPage.tsx:287` already do it:

```tsx
const outcome = useQuery({
  queryKey: ["attempt", attemptId],
  queryFn: () => getAttempt(attemptId as number),
  enabled: attemptId !== null,
  refetchInterval: (query) =>
    query.state.data?.status === "graded" || query.state.data?.status === "failed" ? false : 500,
  staleTime: 0,
});
```

The function form of `refetchInterval` **is** the no-leak pattern the master prompt demands: it
returns `false` on terminal statuses, and react-query tears the interval down on unmount, so there
is no cleanup to forget. Your terminal set is
`completed | failed | cancelled | timed_out`. `api/assessments.ts:21` documents the same
"poll until it settles" contract.

**API paths:** `API_BASE = "/api"` (`src/api/client.ts:57`) and the proxy **strips** `/api` before
forwarding to the FastAPI root (`vite.config.ts:20-21,52-56`, mirrored in
`frontend/web/nginx.conf`). So `api.get("/qml/features")` reaches FastAPI's `/qml/features`.
`main.py:75` mounts `api_router` with **no prefix** — do not add one.

### 3.4 Responsiveness and accessibility

- Target **1280–1920 px** first, degrade to 390 px. The app has a **900 px declared minimum**
  surfaced by `NarrowViewportNotice` — respect it rather than fighting it.
- Follow the fixes the last campaign made, because they are now the house standard: containers
  that can shrink get `min-w-0` + `shrink-0` on the things that must not (`TopBar.tsx`), long
  labels wrap rather than overflow (`QuditGatePalette.tsx`), interactive tiles are
  keyboard-reachable (`QuditCircuitEditor.tsx`), and overlays are ordered so nothing paints over
  a control (`AppShell.tsx` drawer: close button **above** the sidebar, `z-30` over `z-10`).
- Gate: `npx tsx scripts/a11y-check.mts` must stay at **0 criticals**. Labels, focus rings,
  contrast against the dark palette, and no control hidden beneath another (hit-test it, do not
  eyeball it —
  QL-008 and QL-014 were invisible in every screenshot and only showed up under hit-testing).

---

## 4. Allowed touch points in existing files

Everything else is **new files in new directories**. An edit outside this list needs a written
justification in the phase report, and anything structural is a §5 stop.

| File | Permitted edit |
|---|---|
| `backend/app/config.py` | **Add** `qml_*` settings. Do not modify existing fields — especially not `celery_soft_time_limit` / `celery_hard_time_limit` (§1.1). |
| `backend/app/api/router.py` | Add `qml_lab` to the import tuple and one `include_router` call, flag-gated. |
| `backend/app/workers/celery_app.py` | Extend `include=[...]` with the new task module. Do not change `conf.update(...)`. |
| `backend/app/workers/tasks.py` | Add the QML task, **or** put it in a new module listed in `include` (preferred — keeps the diff off a hot file). |
| `backend/app/models/__init__.py` | Add one import line for the new model (§1.6). |
| `backend/alembic/versions/<new>.py` | New additive migration only. |
| `backend/requirements.txt` | Only if §1.3's dry-run passes. Never touch the numpy/scipy pins. |
| `frontend/web/src/components/shell/nav.ts` | One `NavItem` in the `"build"` section, flag-gated. Do not reorder existing items. |
| `frontend/web/src/App.tsx` | One lazy import + one `<Route path="/qml-lab">` inside `RequireAuth` › `AppShell`, before the `*` catch-all. |
| `frontend/web/package.json` | `scripts` entries for new harnesses only. No new dependencies without §5. |
| `frontend/web/scripts/link-shared.mjs` | Only if you add a shared package that needs linking. |
| `docker-compose.yml` | **Add** the `qml-worker` service per §2A.5. Do **not** edit the existing `worker` service's `command` — its `--concurrency=2` is a shipped feature's throughput. |

`backend/app/api/features.py` (§2A.6) and `backend/app/api/qml_lab.py` are **new** files, not
modifications; the only existing file §2A.6 adds to the modified set is the one extra
`include_router` line in `api/router.py`, already listed above.

**Do not touch:** `frontend/web/src/pages/ComposerPage.tsx`, `QuditLabPage.tsx`,
`src/components/qudit/*`, `src/components/noise/*`, `src/components/smart_composer/*`,
`src/lib/circuitSimulator.ts`, `backend/app/quantum/**` (read freely, edit not at all),
`backend/app/curriculum.py`, `backend/app/seed.py`, existing tests, existing migrations,
`src/globals.css` (add tokens only if genuinely missing, and justify each).

The qubit caps are settled and are not yours to change: **static 20 / dynamic 15 / GPU 28**,
with the Composer **preview** capped at `PREVIEW_MAX_QUBITS = 12` in `src/lib/circuitSimulator.ts`.

---

## 5. Stop conditions specific to this repo

Stop and ask — do not guess, do not work around it:

1. The working tree is dirty at start, or `git rev-parse HEAD != git rev-parse origin/main`.
2. Any §4 "do not touch" file appears to need editing.
3. The torch/numpy resolution (§1.3) wants `numpy>=2`, or any dependency wants to move
   `numpy`, `scipy`, `pennylane`, `cirq-core` or `qiskit` pins.
4. Alembic head is not linear, or your migration would touch an existing table.
5. A baseline gate is already red in a way §0 does not predict (e.g. pytest ≠ 818/5, or harness
   FAILs ≠ 57). Report the actual numbers and ask whether to proceed — do not silently adopt a
   new baseline.
6. Making a gate pass seems to require weakening, skipping, mocking-out or deleting an existing
   test. **Never do this.** It is the single most common way an agent manufactures a green build.
7. Per-task Celery limits (§1.1) turn out not to work on the target OS, and the only remaining
   option is changing the global limits.
8. Anything about the GPU path: CUDA-Q is built via `docker-compose.gpu.yml` and is easy to
   destroy by rebuilding without it. Treat GPU as **optional and out of scope unless asked**.

---

## 6. Environment facts

- **OS:** Windows (Intel i5-13450HX, RTX 4050 Laptop, 16 GB RAM). Real path
  `C:\Users\laksh\quantum-learning-platform`.
- **PowerShell is v5 — `&&` is a parser error.** Use `;`, one command per line, and repeat `cd`
  on every step. Use `cd X; command`, never `cd Xcommand`.
- **Git in PowerShell, not WSL.** WSL `git status` under `/mnt/c/…` false-positives ~360 modified
  files. WSL is only for `docker`, `nvidia-smi`, `curl`.
- **`docker compose` must run from PowerShell**, with Docker Desktop fully started first, and
  **always pass `-f docker-compose.gpu.yml`** — omitting it rebuilds with `INSTALL_CUDAQ="false"`
  and deletes CUDA-Q. Services: `postgres`, `redis`, `api`, `worker`, `web` (+ `pgdata` volume).
  Overlays: `docker-compose.gpu.yml`, `docker-compose.webdev.yml`.
- **Celery on Windows:** `prefork` is unsupported. Use `--pool=solo` (or `threads`), or run the
  worker under WSL2. Verify before building Phase 2.
- **Local API without Docker:** `DATABASE_URL="sqlite:///./local.db"`. The default is Postgres.
  `celery_task_always_eager=True` runs tasks inline without a broker — useful for tests, and it
  is the reason the eager path must be tested too.
- **`GEMINI_API_KEY`** may be absent; `backend/app/ai/gemini_client.py:90-101` already degrades
  gracefully, and `ai/chat.py:114-118` shows the house style for the user-facing message. Copy
  that pattern for Phase 6 — never crash, never leak the key, never log a full payload.
- **`vite preview` 403s** the sandbox/proxy host unless `VITE_ALLOWED_HOSTS=` is set.

---

## 7. Reuse map — read these before designing anything

| You need | Read this |
|---|---|
| Job lifecycle, statuses, idempotency | `backend/app/models/job.py` (`SimulationJob`), `backend/app/api/jobs.py`, `backend/app/workers/tasks.py:57-127` |
| The duplicate-submission guard the master prompt asks for | **Already exists as a pattern**: `SimulationJob.run_hash` (`models/job.py:22`) + the cache lookup at `api/jobs.py:154-170`. Copy it; don't invent an idempotency-key system. |
| Auth | `backend/app/deps.py` → `get_current_user`, `require_roles`. Every new route that writes needs it. Ownership checks: `api/jobs.py:200-206` (`404` then `403 "Not your job"`). |
| Error shape | `HTTPException(422, {"errors": [...]})` for validation (`api/jobs.py:120`), mirrored client-side by `readableError()` in `src/api/client.ts`. |
| Settings | `backend/app/config.py`, `pydantic_settings.BaseSettings`, `@lru_cache get_settings()`. |
| Quantum engine | `backend/app/quantum/backends/` (`pennylane_sim.py`, `cudaq_sim.py`), `quantum/inspect.py`, `qudit_lab/`, `noise_lab/`, `smart_composer/`. |
| Validator style | `backend/app/quantum/qudit_lab/validator.py`, `noise_lab/validator.py` — allow-lists, ranges, typed errors. |
| Panel layout with tabs/forms/results | `components/noise/NoiseLabView.tsx` (883 lines), `components/smart_composer/SmartComposerPanel.tsx` (431) |
| Circuit view for Phase 3-B | `components/results/CircuitDiagram.tsx` |
| SVG plotting without a library | `components/grover/GroverLab.tsx`, `components/results/InteractiveBlochSphere.tsx` |
| Polling + cleanup | the simulation-job status polling in `src/pages/ComposerPage.tsx` / `src/api/jobs.ts` |
| Backend tests to imitate | `backend/tests/test_qudit_lab_comprehensive.py` (21), `test_noise_lab_comprehensive.py` (20), `test_smart_composer_comprehensive.py` (20) |

⚠ **Nested-config trap.** `noise_lab/models.py` `NoiseConfig` nests every group
(`decoherence`, `stochastic`, `coherent`, `readout`, `correlated`) and **each defaults to
`enabled: False`**, so a flat payload is silently ignored and returns a plausible wrong answer.
Design the QML schema so that a wrong shape is **rejected loudly**, never silently defaulted.
Malformed payloads returning sensible-looking numbers is a known failure mode here.

---

## 8. Evidence standards — how you will be judged

The last campaign was audited line by line against the repo. Expect the same.

- **Every gate needs pasted command output**, not a claim. "Tests pass" is not evidence;
  `818 passed, 5 skipped in 109.21s` is.
- **Every defect needs a measured root cause.** The good ones cited grep counts (`0 occurrences
  of the utility in dist/`), coordinates (`sign-out button painted at x=471 on a 390 px
  viewport`), and computed values (`rgba(0,0,0,0)`). "Looks wrong" is not a finding.
- **Prove the fix survives the production bundle.** Grep `dist/` for the emitted CSS/JS, not just
  the source. Source-level fixes have been lost to Tailwind extraction before.
- **Say when you cannot verify something.** "0.8480 was not reproducible; I did not find its
  origin" earned more credit than an invented explanation. Never fabricate a number, a
  benchmark, a test result or a file's contents.
- **Distinguish fidelity from purity.** Depolarising `E(ρ) = (1-p)ρ + (p/d)I` gives fidelity
  `(1-p) + p/d` but purity `(1-p)² + 2p(1-p)/d + p²/d`. For d=3, p=0.35 those are 0.7667 and
  0.6150. Label which one you mean. An auditor will recompute it.
- **Report internal consistency.** Contradictory counts (44 runs vs 46; 517 vs 53 assertions)
  were noticed and cost credibility. Count once, from the artifacts.
- **Automate what you find by hand.** Standing rule: every manually-discovered defect gets a
  script that catches it next time, wired into `package.json`, and proven able to fail.

Write `docs/qml/phase-N-report.md` per phase, `docs/qml/DECISIONS.md` running,
`docs/qml/00-audit.md` and `docs/qml/ui-audit.md` in Phase 0, `docs/qml/04-benchmarks.md` in
Phase 4, `docs/qml/07-verification.md` in Phase 7, `docs/qml/08-release.md` in Phase 8.
All under `docs/qml/` — tracked, never under `artifacts/`.

---

## 9. Phase-order amendment

Keep the master prompt's eight phases and their exit gates. Three adjustments:

- **Phase 0** additionally produces: the baseline table from §0 reproduced from your own runs;
  confirmation that `HEAD == origin/main` and the tree is clean; and the §1.3 dependency dry-run
  result. If any §0 number does not match, stop (§5.5).
- **Phase 2** additionally proves the §1.1 per-task time-limit isolation in both directions.
- **Phase 8** is amended: since you are already on `main`, "prepare the merge" becomes
  **"confirm `main` is deployable with the flag off, and document how to turn it on"**. There is
  no merge step. There is still a rollback procedure, and it must include the alembic
  `downgrade()` you proved in §1.6.

---

## 10. Definition of done

- `main` is green: 818/5, tsc 0, build PASS, harnesses 284/57 (or better), goldens 4,300 @ 1e-9,
  a11y 0 criticals — all re-run by you, all pasted.
- With `qml_enabled=False`, the app is **behaviourally identical to today**: same nav, same
  routes, QML routes 404. Proven, not asserted.
- With `qml_enabled=True`, all nine QNN acceptance criteria in the master prompt hold,
  demonstrated by tests that run **real circuits and real gradients** — no mocked qnode, no
  stubbed gradient, no fixture standing in for the thing under test.
- Tracked file count grew only by files you added deliberately; none of the §2.3 forbidden paths
  exist; nothing under `artifacts/` is committed; no stray `.db`, `dist/`, debug prints or
  unrelated diffs.
- Every existing file you modified is in §4's table, or justified in writing.
- Every claim in your final report is traceable to a command you ran in this session.

Begin with Phase 0. Stop at the first §5 condition instead of guessing.
