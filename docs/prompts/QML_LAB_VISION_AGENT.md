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

The real cost driver is **gradient method**. Parameter-shift evaluates the circuit twice per
trainable parameter; backprop differentiates through the state once and is far cheaper.

⚠ **This section's original arithmetic was wrong twice, and Phase 4 corrected it from the code.
The corrected figures are below — do not re-derive the old ones.**

1. **The ansatz carries 2 parameters per qubit per layer, not 3.** `circuit.py:70` is
   `n_parameters = n_layers * n_qubits * 2` — `RY(θ)` and `RZ(φ)` on every wire, then a CNOT
   pattern (`circuit.py:46-55`). Three-per-qubit is the `StronglyEntanglingLayers` convention,
   which this repo deliberately does not use; its own docstring explains that a single axis plus
   CNOTs is a common reason a QNN plateaus at chance. At 8 qubits × 4 layers, **P = 64**, not 96.
2. **`vqc.py:101` loops per sample** — `values = [self.expectation(row, theta) + theta[-1] for row in x]`,
   with no batching or broadcasting. **Batch size therefore multiplies every execution count.**
   Costing a step as one gradient evaluation understates a maximal run by more than an order of
   magnitude: the real figure is **~9,130,000** executions, not ~600,000.

The repo's own `limits.estimate_cost` already had the per-sample loop right; it was this prose that
was wrong. **Read the code before estimating.**

⚠ **And execution count is not a timing model.** The measured execution ratio between the two
gradient methods is **129×**, but the wall-clock ratio is only **12.6×** — a backprop step does a
forward *and* a backward pass per sample, so its executions are individually more expensive.
Converting an execution ratio into a seconds ratio would have been wrong by an order of magnitude
and would have set the timeout dangerously. Report both numbers, separately, and never substitute
one for the other.

The portable laws Phase 4 established, to be reused rather than re-derived: **backprop cost is
linear in circuit size; parameter-shift is quadratic.** Predicted execution counts matched
`qml.Tracker` exactly in all 45 full-grid cells, which is what makes the laws trustworthy.

The conclusion the limits should encode:

- **backprop is the default** and must complete the max config inside the timeout;
- **parameter-shift is structurally infeasible at the current maxima** — not merely slow. Phase 4
  projected ~25.7 h in a 2-core container and ~6.3 h even on `lightning.qubit`. So it needs a lower
  ceiling when selected, an up-front estimate before dispatch, or a clean rejection above a measured
  threshold. Validate **per gradient method**, not once for the config.
- ⚠ **`limits.estimate_cost` is known-wrong and must be fixed before anything consumes it.** It
  charges one evaluation pass (`limits.py:138`, *"one forward pass over everything at the end"*) but
  `trainer.py:220-221` evaluates **both** splits **every epoch**. It therefore undercounts by
  `(epochs − 1) · n_samples` — proven by running the shipped trainer under `qml.Tracker`: 306
  measured vs 186 claimed, short by exactly `(3−1)·60`. At max config it understates backprop
  **2.39×**, and per-epoch evaluation is **59% of backprop's executions** (though only ~27% of its
  time — again, executions are not seconds). It has no call sites in app code today, so nothing is
  broken yet; the exact patch is recorded as **D-028**. **Wire nothing to it until D-028 lands.**

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

## 2C. Phase 5 decisions, settled in advance

Six deliverables, each with a decision that would otherwise cost you a stop-and-ask. Build to these.

### 2C.0 Land D-028 first, before any UI consumes a cost estimate

`limits.estimate_cost` undercounts by `(epochs − 1) · n_samples` (§2B.3, proven at 306 measured vs
186 claimed, **2.39× low at max config**). Phase 4 correctly deferred it because it had no call
sites. **Phase 5 creates call sites** — the kernel and noise views both need an up-front cost
warning — so the patch lands *first*, as its own commit, with a test that reproduces the
`(epochs − 1) · n_samples` shortfall and then closes it. Wiring a UI to a knowingly-wrong estimator
is how a user gets a "should take 2 minutes" toast on a 25-hour job.

### 2C.1 One flat ceiling cannot serve five algorithms

`limits.py` currently has a single set of maxima sized for a VQC. Phase 5 needs **per-algorithm
ceilings**, and this is a real design change: record it in `DECISIONS.md` and keep
`estimate_cost`'s output shape stable so the UI does not branch on algorithm.

The reason it cannot stay flat is that the algorithms have different cost *laws*, not just different
constants — Phase 4 established backprop linear and parameter-shift quadratic. A quantum kernel is
worse than both: it is **O(N²) in samples** before any model fits.

### 2C.2 Hybrid QNN — use `autograd`, do NOT add PyTorch

The master prompt says "PyTorch plus PennyLane", but it also says *"PyTorch interface **where
appropriate**"*, and here it is not appropriate.

**`autograd` is already present** as a PennyLane dependency, and Phase 1 proved
`interface="autograd"` works — parameter-shift and backprop agreeing to 2.22e-16. Write the classical
layers in autograd-compatible numpy and the whole hybrid differentiates end-to-end through
`qml.grad`/`autograd.grad` with no new machinery. You already hand-rolled Adam and a
scipy logistic-regression baseline; a one-hidden-layer MLP in the same idiom is a smaller job than
either.

**Do not install torch.** The Phase 1 dry-run showed it would not move the `numpy<2` pin, so it is
*safe* — but it pulls ~24 packages including the entire CUDA toolkit onto a 16 GB Windows laptop, for
one optional algorithm, on a learning platform. Safe and worth it are different questions.
`qml.qnn.TorchLayer` is the only thing you'd gain and it is a thin wrapper around what you can write
directly.

If you hit a genuine wall — a requirement autograd cannot express — that is a **§5.3 stop** with the
dry-run output attached, not a silent install.

### 2C.3 Quantum kernel — least-squares SVM, and a separate hard sample cap

Two decisions, both forced by the absence of sklearn (§1A):

**Use least-squares SVM (LSSVM), not C-SVM.** A kernel C-SVM needs a QP solver and a dual
formulation; LSSVM reduces to one `numpy.linalg.solve` on the kernel matrix you already computed. It
is closed-form, deterministic, needs no iterative solver to tune, and is a well-established method
in its own right. **Label it LSSVM everywhere it is surfaced** — calling it "SVM" without
qualification would misrepresent what the learner is looking at, and this is a teaching platform.

**Cap kernel samples separately and hard.** At the global `MAX_SAMPLES = 1000` the kernel matrix is
~10^6 circuit evaluations *before* anything fits. Price it from Phase 4's measured laws, set a
ceiling the target machine can actually reach (order 200–300 samples — decide from your numbers, and
say which), and reject above it with a readable message rather than starting a job that cannot
finish. The kernel matrix is symmetric, so **compute the upper triangle only** — that is a free 2×.

Show the kernel matrix in the UI as required, but as a heatmap built from `DensityMatrixInspector`'s
inline-style approach (§3.2), never an interpolated Tailwind class.

### 2C.4 Quantum regression — do not reuse the classification metrics

Continuous targets need a different loss (MSE), different metrics (**MAE, RMSE, R²** — accuracy,
precision, recall, F1 and a confusion matrix are all meaningless), and a different result schema.

- Keep them **separate types**, not one union with nullable fields. A result object whose `accuracy`
  is `None` for regression invites a UI that renders "—" or, worse, `0` — and `0` reads as "the model
  scored zero", which is a lie of a different kind.
- The encoder must map continuous features into `[0, π]` (`ANGLE_MIN`/`ANGLE_MAX`) using the same
  fit-on-train-only scaler discipline, and the §1A leakage assertion applies again.
- The prediction output is continuous, so the Results view needs a numeric column and a
  predicted-vs-actual plot — hand-rolled SVG per §1.4, reusing `charts.tsx`.

### 2C.5 Noise experiments — reuse the noise vocabulary, but not its defaults

`backend/app/quantum/noise_lab/` already exists with `models.py`, `noise.py`, `metrics.py` and a
`validator.py`. **Read it and reuse its vocabulary** — a second, incompatible set of noise names
would be exactly the competing-system problem the master prompt's §5 forbids.

But two things must differ:

- ⚠ **Do not inherit its default-off trap.** §7: `NoiseConfig` nests every group and each defaults
  to `enabled: False`, so a flat payload is silently ignored and returns a plausible wrong answer.
  Your QML noise config uses `extra="forbid"` (§1A) and makes enabling **explicit**, so a malformed
  request is rejected loudly.
- **Noise requires finite shots.** Depolarising and dephasing channels are not analytic in general,
  so `shots=None` is not available — state the shot count on every noisy number and treat shot noise
  as a *source of variance* in the benchmark, not an error. Density matrix is `4^n`, so
  `DENSITY_MATRIX_MAX_QUBITS = 6` is the binding cap; tighten it on evidence if ideal-vs-noisy
  comparison needs two runs.

The deliverable is the **side-by-side comparison** — same config, ideal vs noisy, same seed — which
means the run must be reproducible enough that the difference is attributable to the noise and not
to shot variance. Report the variance.

### 2C.6 Trainable qudit models — a time-boxed spike, and the document is the deliverable

Verify whether `backend/app/quantum/qudit_lab/` supports differentiable gates, measurements and
gradients. Read `simulator.py`, `gates.py` and `metrics.py`; it is a purpose-built density-matrix
simulator with no autodiff wiring, so the likely answer is **no**, and that is a *fine* answer.

**Time-box it.** The output is `docs/qml/qudit-feasibility.md` stating what exists, what is missing
(autodiff-compatible gate parameterisation, a differentiable expectation, a gradient rule for
qudit channels), and what it would take. **Do not implement a fake version** — the master prompt is
explicit, and a stub that returns zero gradients would poison every later phase that trusts it.
A spike that concludes "not feasible without X" is a complete, successful deliverable.

### 2C.7 UI wiring for five more algorithms

Same four views, same flag, same primitives (§3.3). The Configuration view must show **only valid
options per algorithm** — gradient methods that the device supports, sample caps that the algorithm
allows — driven by `/qml/describe`, not hardcoded in the client. Remember `cn()` has no
tailwind-merge, read a primitive's signature before calling it, and derive fixtures from captured
responses (§3.3).

Each algorithm gets its own `.mts` harness (§1.5), wired into `package.json`, and **mutation-tested**
— Phases 1–4 each found vacuous tests this way, and five new algorithms is five new chances to write
a check that passes for the wrong reason.

### 2C.8 Order, and what may be deferred

Build in the master prompt's order: Hybrid QNN → baseline polish → regression → kernel → noise →
qudit spike. **One algorithm per commit set**, each with its tests green and the baseline unchanged
before you start the next, so a failure is always attributable to the thing you just built.

If you run out of room, the defensible stopping points are **after regression** (three algorithms, a
complete classification-and-regression story) or **after the kernel**. The noise comparison and the
qudit spike are the two that can slip without leaving anything broken — but a slipped item goes in
`docs/qml/MANUAL_TEST_REGISTER.md` or `DECISIONS.md` as a named deferral, never silently (§8A).

---

## 2D. Phase 5b — execution dispatch for the three algorithms that already landed

### 2D.0 The premise of this section was wrong, and the gap is deeper than "no UI"

Phase 5 landed engines, tests and a capability endpoint. It did **not** connect them. The service
layer is still VQC-only end to end:

| Layer | Location | State |
|---|---|---|
| Dataset boundary | `models.py:24` `DatasetName = Literal["moons","circles","iris_binary"]` | **rejects `sine`/`damped_cosine`/`linear_mix` with a 422** |
| Dataset builder | `datasets.py:256-262` | dispatches on those three only; never consults `regression_data.REGRESSION_DATASETS` (`:45`) |
| Training | `services/qml_lab.py:284` | `model = VQC(...)` — **no dispatch on `config.algorithm`** |
| Inference | `services/qml_lab.py:431` | `model = VQC(...)`; returns `{predictions, probabilities, …}` — classification-only |
| Persistence | `persistence.py:99` `save_model(..., params: Parameters, ...)` | takes `vqc.Parameters`; writes `parameter_shape: {n_qubits, n_layers}` |

So `algorithm: "hybrid_qnn"` is **accepted by the schema, capped by `limits`, advertised by
`describe()` — and then silently trains a VQC.** That is worse than a missing feature: it is a
wrong answer that looks like a right one.

The three engines deliberately do not subclass `vqc.Parameters` (`hybrid.py:72` says so
explicitly). They carry `HybridParameters`, `RegressionParameters` and `LSSVMFit`, so persistence
cannot store any of them unchanged — and `LSSVMFit` is not parameters at all, it is dual
coefficients plus the training data the Gram matrix was built from.

**One thing is already correct — do not spend time re-verifying it.** `check()` (`limits.py:192`)
does `algorithm = getattr(config, "algorithm", DEFAULT_ALGORITHM)` then `table =
limits_for(algorithm)`, and `enforce()` calls `check()`. The §2C.1 per-algorithm ceilings *are*
enforced at the boundary. The policy layer is complete; the execution layer is entirely VQC.

**There is a live inconsistency on `main` right now.** `describe()` advertises the regression
datasets (`services:540-542`) that `DatasetConfig` rejects. A client built to "drive everything
from `/qml/describe`" would render three datasets that always fail with a 422. This is the decisive
argument for dispatching before building UI: the UI spec is unbuildable against the current
backend.

Phase 5 stopped at §2C.8's second stopping point, and the master prompt's Phase 5 exit gate is *"its
tests pass, **UI works**, baseline unchanged"* — so **both** the dispatch and the UI are remaining
Phase 5 scope, not a new phase and not a deferral. They are split into 5b (this section, backend
dispatch) and 5c (§2E, UI), in that order, and both come before Phase 6.

**Why not build the UI first, or in parallel?** The backend work does not get cheaper by deferring
it, but it does get *riskier*: once a Results view renders `METRICS_BY_TASK`, changing result and
persistence shapes underneath it means changing both at once. And a partially-built selector where
two of three options 422 violates §8 — never present unbuilt work as shipped.

**Hybrid goes first inside 5b, as a seam-proving slice.** `HybridQNN` already exposes
`initialise(rng)`, `predict(x, params)`, `predict_proba(x, params)` and `draw(features, params)` —
the same surface as `VQC`, which is why it trained through the unmodified trainer in Phase 5. Its
dispatch is close to a constructor swap, so it establishes the pattern cheaply before regression
(needs `TargetScaler` threaded through persistence and inference) and kernel (a different artifact
type and a no-epoch path). The slice is a *sequencing device*, not the phase deliverable: 5b is not
done until all three run through the API.

### 2D.1 Sequence

1. **Make the gap loud with an invariant, not by suppressing it.** Add a test asserting that every
   dataset `describe()` advertises is accepted by `DatasetConfig`, and every algorithm it advertises
   is actually runnable. It fails today and passes at the end of the phase. Do **not** delete the
   regression datasets from `describe()` to make it pass — that hides the gap and forces the
   capability contract to be edited twice. Fix the class, not the instance.
2. **One registry for datasets.** Widen `DatasetName` and make `build_dataset` consult the same
   source as `REGRESSION_DATASETS`. Derive the Literal *from* the registry, or assert they agree in
   a test — hand-editing both is how the frozen-dict drift happened in Phase 5.
3. **Hybrid dispatch end to end**, including `save_model`/`load_model` accepting `HybridParameters`,
   proven through the API with a smoke test.
4. **Regression dispatch.** Thread `TargetScaler` through persistence — inference must reload the
   *same* train-fitted scaler, not refit. The inference response is a value **in the user's units**
   (`RegressionDataset` already carries both scaled and real `y`), never `probabilities`.
5. **Kernel dispatch.** `LSSVMFit` needs its own artifact shape. There is no epoch loop —
   `describe()` already pins `epochs` to 1 and hides `diff_method` (`:570-571`) — so do **not** emit
   synthetic epochs to satisfy a persistence path that expects them. Give the no-epoch case its own
   honest progress contract.
6. **One inference contract for all tasks.** Decide once: task-tagged payload or per-task shapes.
   Either way the response must **not** carry a zeroed field for a task that lacks it — §2C.4's
   hazard, surfacing at the API instead of the UI.

### 2D.2 Persisting results that are not classification results

**D-033 already settled this — do not re-open it.** `RegressionResult` exists as a separate
`extra="forbid"` type (`models.py:201`) and a test asserts it has **no** `accuracy`, `precision`,
`recall`, `f1` or `confusion_matrix` attribute. Nullable fields on one payload is the design D-033
explicitly rejected. So: **separate payloads per task, discriminated by `task`.**

But the cost is not where it looks. There are two persistence layers and they behave oppositely:

**`qml_experiments.result` is a `JSONType` blob** (migration `i4d7e0f3a6b9:52`), written as a plain
dict at `services:330` and `:365`. `EvaluationResult` never reaches the DB as a typed column — it is
produced in-process by `evaluator.py:59` and serialised. **So the discriminated union needs no
migration at all here.** `config` is also JSON and already carries `algorithm`, so `task` is
derivable; store it explicitly in `result` anyway, so an old row can be read without knowing the
algorithm→task mapping that was current when it was written.

**`qml_epoch_metrics` is typed columns**, and this is where the migration genuinely is:

```
train_accuracy = Column(Float, nullable=False)   # models/qml.py:134 — no default
test_accuracy  = Column(Float, nullable=True)    # :140
```

A regression epoch has no accuracy, so one additive migration is required: add nullable
`train_r2`/`test_r2` **and** relax `train_accuracy` to nullable. Use those exact names — `describe()`
already promises them in `HISTORY_KEYS_BY_TASK` (`services:483`), so any other name makes the
capability document lie a second time.

**Do not store R² in the `train_accuracy` column.** It is the D-033 hazard relocated to storage, and
it is worse there for two reasons: R² **can be negative** (Phase 5 measured `sin(2x)` at R²=+0.104,
losing to a linear baseline), so a column every consumer assumes is a `[0,1]` accuracy would hold
`-0.4`; and the existing D-033 test guards the *Pydantic model*, not the column, so it would keep
passing. A chart labelled "accuracy" reading `0.328` is a lie that survives review.

**Note what you are giving up.** `train_accuracy` being `nullable=False` with **no default** is
currently a safety property: a regression epoch that tries to write it fails loudly instead of
silently storing `0.0`. Relaxing it makes "NULL vs 0.0" a live hazard, so pair the migration with a
round-trip test — run a regression experiment through the real DB path and assert the persisted JSON
contains no accuracy key anywhere **and** that `train_accuracy` is `NULL`, not `0.0`.

**Kernel writes no epoch rows.** `epochs` is pinned to 1 and `diff_method` is hidden
(`services:570-571`); there is no loop to report. Emit one honest terminal event, or none — do not
manufacture an epoch to satisfy a persistence path that expects one. Kernel reaches the same
conclusion independently: with `train_accuracy` NOT NULL, a single synthetic kernel row would have
to either fail or lie.

**If a fourth task looks likely** (noise, qudit), the alternative is keeping only the universal
columns typed (`epoch`, `train_loss`, `elapsed_seconds`) and moving task-specific metrics into a
per-row JSON `metrics` column validated by a per-task Pydantic model on read. That is defensible
because the original argument against a JSON column — recorded in the migration docstring at
`i4d7e0f3a6b9:21` — was about *read-modify-write of a growing blob* that SQLAlchemy cannot detect
in-place mutation on. A per-epoch row is **insert-once**, so that objection does not apply. It does
weaken the DB-level guarantee, so take it only with a concrete fourth task in hand; otherwise the
two extra columns are the smaller change.

### 2D.3 Gates for 5b

Backend-only, so Phase 5's by-construction argument still holds: **0 frontend files changed**,
bundle hash identical, harness FAIL count unchanged, CSS rule-level diff empty. `pytest` must grow
by the dispatch tests; the four flag states (§2A.6) must still hold against a live server, and with
the flag **on**, a `hybrid_qnn`/`quantum_regression`/`quantum_kernel` experiment must each reach a
terminal status through the real worker path.

---

## 2E. Phase 5c — UI wiring, against a backend that honours the selection

§2D is complete and on `main`. Everything below still stands; §2E.0 adds what the finished backend
now obliges the UI to handle.

**Three engines with no UI are dead code from a user's perspective**, and MT-006 blocks release.

### 2E.0 The as-built contract, and two hazards that did not exist when §2E was drafted

`_describe_algorithms()` (`services:584`) serves one **identical key shape** per algorithm, and
D-032 guarantees every `limits_for` table has the same keys. So:

```
{ name, label, task, summary, limits, datasets[], metrics[], epoch_fields[],
  supports: { n_hidden, epochs, diff_method, data_reuploading }, baseline }
```

**Never branch on algorithm name in the client.** Branch on `task`, or read `supports`. The payload
is shaped so that a new algorithm needs no client change — `supports.epochs === false` already means
"do not render an epoch slider", and `epoch_fields` is the chart's series list. Branching on
`"quantum_kernel"` would throw that away and is the client-side twin of the hardcoded `VQC(...)`
that §2D removed.

**Hazard 1 — `train_accuracy` is now nullable, and the frontend type says it is not.**
`frontend/web/src/api/qml.ts:98` declares `train_accuracy: number;`. The DB column is
`nullable=True` and a regression epoch stores `NULL`. TypeScript does not enforce this at runtime,
so the value arrives as `null` and any `value * 100` or `.toFixed(1)` renders `0` — **the D-033
hazard relocated a third time, now to the type layer**, and invisible to every backend test. The
epoch type must become `number | null`, the chart must skip null points rather than plot them at
zero, and a type-level assertion should record that a regression epoch's accuracy is `null`, not
`0`. `Evaluation` (`:104`), `Baseline` (`:113`) and `InferenceResult` (`:157`) are
classification-shaped too and need the same treatment.

**Hazard 2 — the kernel writes zero epoch rows.** `has_epoch_loop()` is false for it, so the
Training view receives an **empty history**. The existing dashboard assumes a curve exists. It must
show something honest for a closed-form fit — the single solve's outcome and its cost — and must not
spin, render an empty axis, or imply the run is still in progress. `after_epoch` incremental merge
(`api/qml.ts:187`) must also tolerate a run that never produces a row.

**Inference is task-tagged with three shapes** (`run_inference`, `services:408`), and no payload
carries a zeroed field for a task that lacks it:

| task | keys beyond the common `{task, algorithm, feature_names, n_features}` |
|---|---|
| classification | `predictions`, `probabilities` |
| regression | `values` (**user units**), `target_range` |
| kernel | `predictions`, `decision_values` (**signed margin — not a probability; label it as a margin**) |

Regression predictions come from the **stored** `target_scaler`; the endpoint raises
`QmlPersistenceError` rather than silently answering in scaled units. Surface that error as an
error, not as a zero.

### 2E.1 Extend the existing four views — do not fork a page per algorithm

One Lab, one route, the same Configuration / Circuit / Training / Results views, with the algorithm
selector driving what each shows. Five parallel pages would fragment the theme and multiply the
maintenance surface. `Tabs`, `Select`, `DataTable`, `EmptyState`, `SplitPane` and `ConfirmModal` are
all already in `components/ui.tsx` (§3.3).

### 2E.2 Drive everything from `/qml/describe` — this is the whole point of Phase 5's last commit

`services/qml_lab.py:444` now serves, per algorithm: a label, a `task` (`classification` |
`regression`), a description, its limits table, its datasets and its gradient methods. It also
serves **`METRICS_BY_TASK`** (`regression → mae, rmse, r2`) and **`HISTORY_KEYS_BY_TASK`**
(`regression → train_loss, test_loss, train_r2, test_r2`).

So the client must **not** contain a hardcoded algorithm list, metric list, dataset list or limit.
Read them from the payload. This is what makes §2C.4 structurally enforced rather than a matter of
care: a Results view that renders `METRICS_BY_TASK[result.task]` *cannot* show an accuracy for a
regression run, because the server never offers one. A view that hardcodes `accuracy` can, and will
render `0` — which reads as "the model scored zero".

Same for limits: the Configuration view's max for `n_samples` must come from the selected
algorithm's table, so the kernel's lower cap (§2C.3) appears the moment the user picks it, with the
reason visible. Client-side validation must mirror the server's per-algorithm numbers, not the old
flat ones.

### 2E.3 Two new visualisations, both hand-rolled SVG (§1.4)

- **Predicted-vs-actual** for regression — a scatter with the identity line, reusing `charts.tsx`.
  MAE and RMSE must be labelled **in the target's own units**, not the scaled ones, and **R² must
  render its sign** because it can be negative (§2C.4, and MT-006's expected result).
- **Kernel-matrix heatmap** — build it the way `DensityMatrixInspector` does, with a computed
  inline `style` (§3.2). Never an interpolated Tailwind class; that is QL-001 again. Note the matrix
  is symmetric with unit diagonal, so render the truth, not a triangle, and say so.

No chart library. Colour from tokens only; §2B's CSS rule-level diff showed Phase 3 added **no new
colour**, and that should stay true.

### 2E.4 Re-scope MT-006 once the UI lands

MT-006 currently carries two different things in one row: *"no UI exists for regression"* (build
scope, not a manual test) and *"a human must confirm MAE/RMSE/R² render with units and that no
classifier metric appears anywhere"* (a legitimate visual check). When the UI lands, narrow the row
to the second and keep the ID — §8A says rows are never deleted or renumbered. Add whatever new
visual checks the hybrid and kernel views genuinely need, and automate everything that can be
automated by SSR harness first.

### 2E.5 Gates specific to this phase

Phase 5c **does** touch the frontend, so the by-construction argument no longer applies and the
bundle hash will change. Replace it as Phase 3 did: build `origin/main` in a scratch worktree and
diff the compiled CSS at **rule level** — the Phase 3 baseline was 12 added / 0 changed / 0 removed.
Existing rules must not change; if one does, say which and why.

Also re-establish the harness FAIL decomposition by measurement rather than inheriting it. Phase 5
could not reproduce `57 = 9+20+20+8` and correctly refused to invent a matching figure — so measure
it fresh this phase, per script, and record the new authoritative breakdown in §0's place.
`a11y-check.mts` must stay at **0 criticals**, and the four flag states (§2A.6) must still hold
against a live server.

**The nullable-accuracy defect gets a catching script.** It was found by hand, at the type layer,
where no backend test can see it, so per the standing rule it needs a harness under
`frontend/web/scripts/`, wired into `package.json` alongside `render:check` and friends, and
**proven able to fail** by reinstating the bug. It must assert that an epoch payload with
`train_accuracy: null` renders as absent — not as `0`, not as `0%`, not as `—` in a column labelled
accuracy — and that a kernel run with **zero** epoch rows renders its closed-form outcome rather
than an empty chart or a perpetual spinner. A script that only passes is worth nothing; paste the
failing run.

---

## 2F. Phase 6 — Gemini in the QML Lab

The QML Lab has **zero** AI surface today: `git grep gemini` across `backend/app/quantum/qml_lab/`,
`services/qml_lab.py` and `api/qml_lab.py` returns nothing. Everything below reuses the house
pattern rather than inventing one.

### 2F.0 The ruff gate, settled

The gate is **"ruff reports no new findings versus `origin/main`"** — a ratchet, not an absolute.
The repo carries **79** pre-existing findings; demanding zero would block every phase, and demanding
"clean" invites someone to silence findings rather than fix them. Report the count every phase so it
can only move down, and if a phase *adds* one, that is a stop condition (§5), not a note.

Do not fix the pre-existing findings as a side quest. Phase 5c correctly fixed the one that was a
real 500 (`jobs.py` `import json`) and left the four `F401`s alone after confirming they were
identical on `origin/main`. That is the right discrimination: **fix what is a defect, record what is
noise, and never expand scope to make a number prettier.**

### 2F.1 What the sandbox cannot test — plan around it, do not fake it

**`GEMINI_API_KEY` is absent here**, and `is_configured()` (`gemini_client.py:88`) requires both a
key *and* an importable SDK. So the live call **cannot be exercised in this environment at all.**
That is not a reason to stub it into looking like it works.

Split the work accordingly, per §8A:

- **Automate the unconfigured path to exhaustion.** It is the path that will actually run in CI and
  in most checkouts, and it must be useful rather than broken. Assert the status code, the message,
  that no exception escapes, that no key is echoed, and that nothing is logged that shouldn't be.
- **Automate the configured path against a fake transport**, injected at the narrowest seam, and
  label it plainly as a fake in the test name. It proves the prompt is built correctly, the reply is
  handled, and failures are caught — it does **not** prove Gemini answers well.
- **Register the live call as an MT row** with cold-executable steps, marked as blocking release, and
  note that the platform already carries an untested Gemini live path. Do not claim it works.

### 2F.2 Grounding is a structural requirement, not a prompt instruction

The acceptance criteria forbid invented numbers, and an LLM asked to "explain this result" will
happily invent them. So:

- **The prompt must be built from the real stored payload** — config, per-task metrics, baseline, and
  the epoch history — and a test must assert those exact numbers appear in the prompt string. That
  makes grounding a property of the code rather than a hope about the model.
- **The UI must show the real numbers next to the prose**, so a fabrication is visible rather than
  authoritative. Commentary is rendered as commentary, never as a metric, and never in a `Stat`.
- **The system instruction must forbid introducing values not supplied.** Follow `codelab_ai._SYSTEM`
  (`:19`) for shape and tone.
- Cap input with a `MAX_PROMPT_CHARS`-style guard (`codelab_ai.py:17`, currently 2,000) and reject
  over-length rather than truncating silently — truncation would drop the numbers being grounded on.

**Note `generate()` hardcodes `temperature: 1.0`** (`gemini_client.py:249`). That is high for a
feature whose entire risk is confabulation, but changing it in place would silently alter the tutor,
Code Lab and Smart Composer. If you need a lower temperature, **add an optional keyword argument
defaulting to `1.0`** so every existing caller is bit-identical, and say so in the report.

### 2F.3 A suggested config must pass `limits.check()` before the user sees it

If the feature suggests a configuration, the model will eventually suggest one that is impossible —
12 qubits against a cap of 8, or `sine` for a classifier. **Validate every suggestion server-side
with the existing `limits.check(config)` and the per-algorithm `limits_for()` table before offering
it.** Reuse, do not reinvent: this is the same contract `describe()` advertises and the same one
`POST /qml/experiments` enforces.

An invalid suggestion must be rejected or regenerated, **never surfaced**. A UI that lets a user
click "apply" and receive a 422 is worse than no suggestion at all — and it is the exact defect class
Phase 5b closed at three separate construction sites.

Suggestions must also respect `supports{}`: no epoch count for the kernel, no `n_hidden` unless the
algorithm is `hybrid_qnn`, no `diff_method` for a closed-form fit.

### 2F.4 Scope and non-negotiables

- **Flag-gated and authenticated.** Behind `qml_enabled`, using `get_current_user`, with the
  ownership check pattern from `api/jobs.py:200-206` (`404` then `403 "Not your job"`) — an
  explanation endpoint must not let one user read another's experiment.
- **Never crash, never leak the key, never log a full payload** (§6). `GeminiUnavailable`
  (`gemini_client.py:84`) is caught at the route the way `api/jobs.py:426` does it, and the
  unconfigured message follows `ai/chat.py:_offline_reply` — honest, useful, offering the
  alternative that still works.
- **Do not touch `ai/rag.py`.** The fence-aware chunker has a regression test for a reason.
- **No new dependency.** `google.generativeai` is already there; `requirements.txt` must not change.
- **UI: extend the Results view**, per §2E.1 — one panel, existing `ui.tsx` primitives (`Card`,
  `Button`, `Spinner`, `ErrorNote`, `EmptyState`). No new route, no new page, no new library.
- **The unconfigured state is a first-class UI state**, not an error. It needs an `EmptyState` that
  explains what is missing and what still works, because that is the state most reviewers will see.

### 2F.5 Gates

Backend changes are allowed this phase, so the "0 backend files" gate is replaced by: **every
backend file touched is listed in §4's allow-list or justified in writing**, and `celery`'s
**8/15**, `qml_enabled`'s `False` default, and `requirements.txt` are untouched.

pytest grows from **1208 passed / 5 skipped**. `ruff` reports **no new findings** against
`origin/main`'s **79**. The four §2A.6 flag states still hold, and with the flag **off** the new
routes must **404**, not 401 and not 500. `qml:tasks` stays **48/48**; render/ui/circuit stay at
**34/58/49** with 0 fail. Typecheck 0, build PASS, a11y 0 criticals, goldens **190+804+3306 @ 1e-9**,
and the CSS rule-level diff against a scratch-worktree build of `origin/main`.

The `QmlLabPage` lazy chunk is now **45.74 kB** after Phase 5c (+53% on the phase). Report the new
figure and, if it grows again, say what caused it. It is confined to the lazy chunk and the shared
bundle has been byte-identical so far — keep it that way.

**Clarified by Phase 7:** "byte-identical" here means **phase-over-phase against `origin/main`**, and
that is a real gate worth keeping — it catches a phase silently pushing code into the shared chunk,
which is how Phase 6's 9-byte `Info` icon regression was found and traced. It does **not** mean
identical to a pre-QML baseline, which is unsatisfiable (§2G.3, Finding 1).

---

## 2G. Phase 7 — verification, and nothing else

Phase 7 produces **`docs/qml/07-verification.md`**. It is an audit, not a build.

### 2G.0 No new features in this phase

**§2C.5 (noise experiments), §2C.6 (the qudit spike) and §2F's WP6 (suggest-a-config) are all
formally deferred and must not be started here.** Verifying a moving target verifies nothing: every
line of new feature code invalidates the gate numbers you are supposed to be confirming.

**§2C.6 is deferred for a second, harder reason.** The project owner has unpushed local work adding
new qudit gates and polishing the Qudit Lab. A qudit spike started now would collide with changes
nobody can see. It stays deferred until that work lands on `main` and can be read.

Record all three in `DECISIONS.md` with what each would take, so the deferral is a decision rather
than a silence.

### 2G.1 Re-measure; do not transcribe

Every number in `07-verification.md` must come from a command run **in this phase, from a clean
state**. Copying a figure out of `phase-3-report.md` is not verification — it is the thing
verification exists to catch. Where a gate cannot run in your environment, write that it could not
run and why. §8's precedent stands: *"0.8480 was not reproducible; I did not find its origin"*
earned more credit than an invented explanation.

Re-run and record, at minimum: `pytest` · `ruff` (against `origin/main`'s count) · `typecheck` ·
`build` with **both** bundle figures · every harness in `package.json` · the goldens · `a11y` · the
CSS rule-level diff against a scratch-worktree build of `origin/main` · and all four §2A.6 flag
states against a live server.

### 2G.2 Audit the claims, not just the gates

Walk every phase report from 0 to 6 and, for each **numeric** claim, either re-derive it or mark it
unreproducible. This is where the known soft spots get settled rather than carried:

- The harness FAIL decomposition. Phase 5 could not reproduce `57 = 9+20+20+8` and said so; Phase 5c
  and 6 reported render/ui/circuit as **34/58/49** with 0 fail. Establish one authoritative
  breakdown, per script, and retire the old figure explicitly rather than leaving two in circulation.
- `qml:tasks` was specified as a fixed **48** and now reports **55**. A gate stated as a number that
  grows is not a failure, but the *specified* number must be updated or the gate becomes meaningless.
  Restate it as "no pre-existing assertion may regress; growth is reported".
- The Makefile compose-invocation count has now been wrong three times (2, then 9, then a measured
  11). Re-measure it once, with the command shown, and let that be the last word.
- Every bundle figure: shared chunk and `QmlLabPage`, against `main`.

### 2G.3 Prove the flag-off identity claim

§10 requires that with `qml_enabled=False` the app is **behaviourally identical to today** —
"proven, not asserted". Produce the evidence in one place: the route inventory with every `/qml/*`
path absent, the live OpenAPI with zero qml entries, `/features` answering unauthenticated, the nav
unchanged, and the shared bundle byte-identical to a pre-QML baseline. If any of those cannot be
produced, that is a finding.

**RESOLVED by Phase 7, Finding 1 — the last item was my error and is withdrawn.** Byte-identity
against a *pre-QML* baseline is not merely unmet, it is **unsatisfiable**: the shared chunk carries
+1613 bytes and CSS +923, and what it carries is the lazy import declaration, the fail-closed
default, the `useFeatures` hook, the gated nav entry and the route — which **is** the gating
mechanism §2A.6 mandates. You cannot ship a flag-gated lazy route without shipping its gate.

Two distinct gates were being conflated, and only one is real:

- **Behavioural identity vs pre-QML — the actual requirement, and it is met and proven.** 59 vs 66
  OpenAPI paths, 7 added all under `/qml/`, 0 removed, **0 non-QML specs differing**, nav entry
  absent, `/qml-lab` rendering the 404 body. The honest release-note wording: *with the flag off the
  API surface is unchanged, the nav is unchanged, `/qml-lab` renders the 404 body, and the browser
  downloads ~1.6 kB of dormant routing metadata it never executes.*
- **Byte-identity phase-over-phase — a real and useful gate, but a different one.** Phase 6 met it
  exactly (640793, after tracing a 9-byte regression to one extra export alias). It catches a phase
  silently pushing code into the shared chunk. It says nothing about the pre-QML baseline and must
  not be presented as if it did.

Also from Phase 7: a CSS rule-diff of `main` against itself is **empty by construction and proves
nothing**. The informative comparison is against the pre-QML baseline — 15 added, 1 changed,
0 removed, where the single "changed" rule is Tailwind's own generated `@layer properties` block
gaining `--tw-border-spacing` because QML used `border-separate`. **No hand-written rule altered.**

### 2G.4 The nine acceptance criteria

Restate the master prompt's nine QNN acceptance criteria and map each to the code and the test that
prove it — or mark it unproven. **If you no longer have the master prompt's text, say so plainly
rather than reconstructing nine criteria from memory.** An invented criterion that is then marked
"satisfied" is worse than a gap.

### 2G.5 The unverified surface, stated plainly

This is the most important section, because it is what the project owner will act on. Enumerate
everything that has never been exercised, with the reason and what would exercise it:

- **No browser has ever rendered the QML Lab.** Every frontend claim across Phases 3, 5c and 6 is
  server-side rendering. No layout, no CSS cascade, no Radix portal has been seen open, and
  `refetchInterval` is asserted by reading code rather than by observing a second request.
- **The live Gemini call has never executed.** No key in this environment; `is_configured()` also
  needs an importable SDK. The platform already carried one untested live Gemini path and Phase 6
  added a fourth caller.
- **`bench_qml.py --full` has never run on the target machine**, so `qml_task_soft_time_limit = 900`
  and `hard = 1200` remain provisional and untuned.
- **No real broker, prefork pool or signal-based time limit** has been exercised; `.apply()` runs the
  task body in-process only.

Then reproduce the MT register's blocking rows — **MT-001, MT-004, MT-006, MT-010** and any others
marked blocking — as a single ordered list of what the owner must run, with cold-executable steps.
§9 already requires this for `08-release.md`; producing it here means Phase 8 assembles rather than
discovers.

### 2G.6 Defect ledger

One table: every open defect with its ID, where it lives, whether it blocks release, and whether a
catching script exists. Carry forward **QL-005** (`qudit_lab/simulator.py` `round(…, 6)`, whose line
numbers may have moved — the owner is editing that file), **QL-015/016/017**, and the `bg-card`
anomaly (10 uses, 0 CSS rules). Do not fix them in this phase; recording them accurately is the
deliverable.

### 2G.7 Gates

**Zero product-code changes.** The only files this phase may touch are under `docs/qml/`, plus a
harness or test *if* re-measurement exposes a gate that was wrong — and that must be its own commit
with the reason in the message. `pytest` stays at **1230 passed / 5 skipped**; if it moves, explain
why. `ruff` reports no new findings. Tracked files grow only by `07-verification.md` and any
decision-record edits.

---

## 2H. Phase 8 — release readiness, and the two things Phase 7 could not do

Phase 8 produces **`docs/qml/08-release.md`**. Per §9's amendment there is no merge step to prepare —
the work is ported to `main` at every phase boundary — so this phase is *"confirm `main` is
deployable with the flag off, and document how to turn it on."*

### 2H.0 Sequencing: the owner's qudit work lands first

**RESOLVED — it has landed.** `main @ 32e459d` (644 tracked files) contains the owner's qudit work,
merged from `qudit-gates` and verified before the push: all **81 QML files byte-identical**, the
alembic chain still single-headed at `j5e8f1a4b7c2` with no new migration, `package.json` resolved
with **zero scripts lost, zero changed and three added**, and every safety invariant intact
(`celery` 8/15, `qml_enabled=False`, `requirements.txt` untouched, `numpy==1.26.4`, no
torch/sklearn, 0 artifacts tracked). The recovery tag `qml-phase7-verified` → `47fab49` still exists
and should be left alone until Phase 8 closes.

The reasoning is recorded because it still governs any future merge: **do not confirm deployability
of a tree that is about to change.** Measuring `main` deployable and then merging pending work
measures the wrong thing — the same error class as a Makefile target that times the container
instead of the machine.

This is also why **§2C.6 remains deferred** — and now that the qudit code *is* readable, the spike
can be scoped properly if the owner wants it at all. That is the owner's call, not this phase's.

**Phase 8 must re-verify the gates against `32e459d`, not inherit Phase 7's numbers.** The tree has
29 new files and 12 modified, including five new frontend harnesses and two new backend test files.
Phase 7's `1230 passed / 5 skipped` and its harness decomposition were measured on a different tree.

### 2H.1 Close Finding 2 — the fourth flag state must be rendered, not grepped

Phase 7 established that the fail-closed path is **implemented correctly** (`useFeatures.ts:42`,
`query.data ?? FEATURES_CLOSED`, an error counts as resolved) but is asserted only by a regex over
source text at `qml-ui-check.mts:253`. That guard **fails on a behaviourally identical refactor** and
**passes on a real regression**: keep the text, change `resolved` to `!query.isPending &&
!query.isError`, and the route guard hangs forever on a backend outage while the test stays green.

§2G.7 correctly forbade fixing it during a verification phase. **Fix it here.** Render the shell with
a `QueryClient` whose `/features` query is seeded to an error state, and assert the nav lacks the
entry and `/qml-lab` shows the 404 body. The harness already constructs a `QueryClient`, so this is
small. Then **delete the regex guard** — keeping both means the brittle one still fails on a correct
refactor. Prove the new assertion fails against the reinstated regression.

This is the one place §2A.6's "proven, not asserted" is not yet met, and it is the state that matters
most in production: a backend outage is exactly when a fail-closed gate must work.

### 2H.2 The 57 pre-existing harness failures are a decision, not a footnote

Phase 7 reproduced the decomposition Phase 5 could not: **`render:codelab` 9 + `render:p5` 20 +
`render:games` 20 + `render:results` 8 = 57**, none of which reads `API_TARGET`, so all 57 are
genuine failing assertions on `main` today and **none are in QML**.

They predate this project and are not Phase 8's to fix silently. But a release document that says
"all gates green" while 57 assertions fail is not accurate. So `08-release.md` must state the number,
the per-script decomposition, that they are pre-existing and outside QML, and what the owner decides
to do about them. **Do not repair them as a side quest** — that is a separate effort with its own
risk, and it is the owner's call, not a phase's.

**SUPERSEDED as to the repair, in force as to the disclosure.** The owner has since made the call:
these are to be worked in Phase 8A, under the tightened rules of **§2I.3**, which take precedence
over the sentence above. What §2I.3 adds is the distinction this section lacked — most of the 57 may
be fixable, but **any change to an assertion's meaning is the owner's to approve, not the phase's.**
That is why the stage is expected to end partly red. The release-document duty below is unchanged and
must now also report the proposal table's outcome.

### 2H.3 `bg-card` — record, and hand it to the owner

**Updated after the owner's qudit merge: now 7 uses across 5 files, down from 10 across 6.** Their
polish removed three uses, but **`--color-card` is still not defined**, so the remaining seven still
emit **zero CSS** while `border-line` on the same elements emits 19 rules. `border border-line
bg-card/60` renders the border and silently drops the background.

The seven are `DensityMatrixInspector.tsx:134,143`, `QuditGatePalette.tsx:20`,
`QuditLearnPanel.tsx:21`, `QuditNoisePanel.tsx:71`, `QuditLabPage.tsx:273,304`.

Do not fix this in Phase 8 without asking — it is the owner's active surface and the choice between
defining the token and replacing the class is a design decision. Record it in `08-release.md` with
the exact measurement, and note *why* it survived: `bg-card` is a plausible token name that fails
silently, Tailwind emits nothing for an undefined colour, and no tool complains.

**SUPERSEDED as to the fix, in force as to the caution.** The owner has asked: this is to be fixed in
Phase 8A under **§2I.1**, which rules *prefer reusing an existing token over defining `--color-card`*
and requires the choice to be justified and proven in the **compiled** CSS. The caveat above is not
withdrawn — these are the owner's actively developed components, and **other agents work this repo in
parallel on separate branches.** So the change must be **minimal and surgical**: alter only the
offending class or the token block, never restructure, reformat or "tidy" the surrounding component.
The *why it survived* note still belongs in `08-release.md`.

### 2H.4 What `08-release.md` must contain

- **Two-part enablement**, both required: `QML_ENABLED=true` **and** `docker compose --profile qml`
  for the `qml-worker` (§2A.5). Neither alone works, and saying only one is how a deployment silently
  queues jobs nothing consumes.
- **Rollback**, concretely: the alembic `downgrade()` proven in §1.6 — noting that Phase 5b's
  `j5e8f1a4b7c2` downgrade is **deliberately lossy**, deleting epoch rows whose `train_accuracy` is
  NULL before restoring NOT NULL — plus profile removal and D-028's status.
- **Every MT row marked "blocks release" as a pre-enablement check**, in the order Phase 7 assembled:
  **MT-004 → MT-001 → MT-006 → MT-010**, benchmark first because everything downstream assumes
  `900/1200` is survivable. Include the three cheap additions Phase 7 made to MT-001 while a browser
  is finally open: open a Radix `Select` (no portalled content has ever rendered), watch polling
  actually stop on terminal, and look at the `bg-card` panels.
- **The provisional timeouts stated as provisional.** `qml_task_soft_time_limit = 900` and
  `hard = 1200` have never been tuned against the target machine. §2B.4 stands: tightening is fine,
  **loosening needs the owner's sign-off**, and MT-004 is the only source of the numbers.
- **The unverified surface, reproduced from `07-verification.md` §6** — no browser has rendered the
  QML Lab, the live Gemini call has never executed, the benchmark has never run on target hardware,
  no real broker or prefork pool or signal-based time limit has been exercised. A release doc that
  omits this is the thing §8 exists to prevent.
- **Behavioural identity, worded as Phase 7 resolved it** — not byte-identity, which is unsatisfiable
  by the architecture §2A.6 mandates.
- **The state of the pre-existing harness suite, exactly.** State the red count and the per-script
  decomposition, how many were fixed and on what grounds, and link
  **`docs/qml/08-assertion-proposals.md`** for the rows awaiting the owner (§2I.3). **This document
  must not assert "all gates green" or any equivalent** — not "green apart from known pre-existing
  issues", not "all QML gates green" without the count beside it. The sentence that makes the release
  honest is the one that names the number.

### 2H.5 Gates

`pytest` at **1230 passed / 5 skipped** plus whatever 2H.1 adds. `ruff` no new findings vs **79**.
Typecheck 0, build PASS, a11y 0 criticals, goldens **190+804+3306 @ 1e-9**. The harness decomposition
must be restated with 2H.1's change reflected — and if the render harness count moves, say which
assertions moved and why. CSS rule-level diff against the **pre-QML baseline**, not against `main`,
because a diff of `main` against itself is empty by construction and proves nothing.

Product-code changes are permitted this phase **only** for 2H.1, and only in the harness. Everything
else is `docs/qml/`.

---

## 2I. Phase 8A — remediation before release: make the browser real, then fix what it finds

Phase 8 was going to be a documentation phase. It cannot be, because Phase 7's largest caveat — *no
browser has ever rendered the QML Lab* — turns out to be **fixable**, and fixing it changes what
"verified" means for the whole project. So Phase 8 splits: **8A is this remediation**, 8B is the
release document. 8A runs first and must be green before 8B starts.

### 2I.0 The unlock: seven browser harnesses cannot run anywhere

`playwright@^1.64.0` **is** a declared devDependency, and `tools/browser-setup.sh` exists to install
a working Chromium. But **all seven** playwright harnesses hardcode a machine-specific launch path:

```
frontend/web/scripts/browser-verify-matrix-view.mjs:4      EDGE_PATH = C:\Program Files (x86)\...\msedge.exe
frontend/web/scripts/browser-verify-new-features.mjs:31    EDGE_PATH
frontend/web/scripts/browser-verify-qudit-lab.mjs:7,8      EDGE_PATH + ARTIFACT_DIR
frontend/web/scripts/qa-circuit-visual-fix.mjs:5,7         EDGE_PATH + ARTIFACT_DIR
frontend/web/scripts/qa-qudit-master-upgrade.mjs:8         EDGE_PATH
frontend/web/scripts/qa-qudit-user-remediation.mjs:5       EDGE_PATH
frontend/web/scripts/vision-qa-master-suite.mjs:19         EDGE_PATH
```

Two also hardcode `ARTIFACT_DIR` to `C:\Users\laksh\.gemini\antigravity-ide\brain\<session-uuid>` —
an **ephemeral IDE session directory** that no longer exists, so those scripts fail on the owner's
own machine too. And two are wired into `package.json` (`test:new-features:browser`,
`test:vision-qa`), so the published commands crash for anyone who runs them.

Four of the seven predate this project; three arrived with the owner's qudit merge. None is QML's,
and none has ever produced evidence anyone could reproduce. **This is the structural reason every
frontend claim in Phases 3, 5c, 6 and 7 is SSR-only.**

**The fix already exists in this repo — copy it, do not invent one.** `push-overlay-check.mts` is the
only portable browser harness. Its pattern:

- resolve the browser in order, preferring `$UITEST_DIR/bin/chromium` (what `browser-setup.sh`
  produces) and falling back rather than assuming (`:56`, `:19`)
- set `LD_LIBRARY_PATH` before launching (`:61-63`)
- `chromium.launch({ ...(exePath ? { executablePath: exePath } : {}), args: ["--no-sandbox",
  "--disable-dev-shm-usage", "--disable-gpu"] })` (`:96-98`) — note the conditional spread, so it
  uses Playwright's own browser when no explicit path is needed
- write artifacts to a **gitignored, relative or env-configured** directory, never a hardcoded
  absolute user path

Migrate all seven. A harness that cannot run is not a harness; it is an untested claim with a
filename.

### 2I.1 `bg-card` — the fix, and the trap that caused it

**7 uses across 5 files emit zero CSS.** The cause is §3.1's two-layer trap: utilities are generated
only from the `@theme` block (`globals.css:4-42`), and there is **no `--color-card`** there. Putting
one in the `:root`/`html.dark` bare-vars block (`:44-92`) would **still emit nothing** — that layer
does not produce utilities. If a new token is needed it must go in `@theme`.

**Prefer reuse over a new token.** §3.1 forbids duplicating an existing one, and the sites are
`border border-line bg-card/60 backdrop-blur-md` panels — a translucent raised surface, which
`bg-raised` / `bg-subtle` / `bg-bg-raised` may already express. Check first. Add `--color-card` to
`@theme` only if nothing existing fits, and say which and why.

Either way the proof is the built CSS: `.bg-card` (or its replacement) must appear in the compiled
output, and the CSS rule-level diff must show it. "It looks right in the source" is not evidence —
that is precisely how this survived.

Sites: `DensityMatrixInspector.tsx:134,143`, `QuditGatePalette.tsx:20`, `QuditLearnPanel.tsx:21`,
`QuditNoisePanel.tsx:71`, `QuditLabPage.tsx:273,304`.

### 2I.2 The carried defects

- **QL-005** — `qudit_lab/simulator.py:140, 151, 160`, `round(…, 6)`. Confirmed still at those exact
  lines after the owner's merge. Rounding a physical quantity for display purposes at the *computation*
  layer loses precision downstream; decide whether it belongs there or at the presentation boundary.
- **QL-015** toast overlap · **QL-016** preset titles at ≤1366px · **QL-017** diagonal sub-label.
  Each needs a reproduction before a fix, and now that 2I.0 makes browsers runnable, each
  reproduction should be a harness assertion rather than a screenshot someone looked at once.

### 2I.3 The 57 pre-existing harness failures — triage, fix what is safe, *propose* the rest

Phase 7 decomposed them as `render:codelab` 9 + `render:p5` 20 + `render:games` 20 +
`render:results` 8. **Re-measure first** — the tree has since gained 29 files and five harnesses, so
the number may have moved.

**It is correct and expected for this stage to end with failures still red.** A red number plus a
proposal table is the success condition here, not a failure of the stage. Reaching green is *not* the
objective; reaching green *honestly* is, and the honest answer for part of this backlog is "the owner
has to decide."

#### The line is not product-versus-test — it is whether the assertion's meaning changes

Categorising by "is the product wrong or is the test wrong" is the wrong cut, because "the test is
wrong" is the same shape of claim as "the test is stale" and invites the same rationalisation. Cut on
semantics instead:

| | Allowed — commit it | Forbidden — propose it and stop |
|---|---|---|
| **Definition** | The assertion still verifies the same behaviour against the same expectation. Only the plumbing changed. | Anything that alters **what is expected** or **what is observed**. |
| **Examples** | Replacing a hardcoded browser path; fixing a port or a base URL; removing a race or order-dependence; re-pointing a selector after an attribute rename **while still targeting the same element**; making a vacuous test actually assert. | Changing an expected value, number or string; weakening `.toBe` to `.toContain` or `.toBeTruthy`; narrowing the cases checked; changing which element or region is inspected **such that a different thing is verified**; deleting a test. |
| **Also forbidden, explicitly** | | `.skip` / `xit` / `todo` / commenting a test out / `if (false)` / an early `return` — **a skip is a deletion wearing a costume.** So is "this test is redundant." So is wrapping the assertion in a `try/catch` that swallows. |

#### Two passes, in this order

**Pass 1 — triage, read-only.** Categorise **all** of them before changing **any** code. Every
category assignment needs evidence; none may be assigned by assertion alone. The triage table is its
own commit, containing no product or harness change.

**Pass 2 — fix only the allowed column.** Real product defects: fix the product, the assertion was
right. Semantic-preserving harness fixes: fix the harness.

Two traps in Pass 2:

- **When a failure is a stale assertion, do not "fix" the product to satisfy it.** That is a
  regression dressed as a green tick. Revert any such change.
- **A fix that makes one harness green while another goes red is not progress.** Re-run the whole
  sweep after every fix commit.

#### The proposal table — for the owner to approve line by line

Anything in the forbidden column becomes a row here and **stays red**. Each row must carry:

1. harness and line
2. the current assertion, **verbatim**
3. the proposed assertion, **verbatim**
4. what behaviour it protects today
5. why it is stale — **the commit that changed the UI, with the before/after pasted**
6. **what regression would go undetected if this were approved**
7. your recommendation

Field 6 is the one that matters. It forces the accounting that "this is just stale" skips, and it is
how the owner decides rather than ratifies. A row without field 6 is not a proposal.

#### Reporting

Report the count as **fixed = N product defects + M semantic-preserving harness fixes; awaiting
owner approval = K**, and never fold K into a green figure. If a failure cannot be categorised at
all, it goes in K with "uncategorised" and the evidence you gathered — an unexplained red is more
useful than a fabricated green.

One commit per category, with the count before and after in the message.

#### Shrink K legitimately, never by eroding an assertion

The proposal column is the **residual**. Before anything lands in it, the product-side explanation
must have been tried: ask "is the product actually wrong here?" and fix it if so. A meaningful part
of the 57 is likely real defects that no one investigated because the suite has been red long enough
to be background noise. Finding those is the valuable half of this stage.

**Time-box the triage.** If a single failure resists categorisation after a genuine investigation,
record it "uncategorised" with what you learned and move on. Do not spend the phase on one assertion.
An incomplete triage that covers 56 of 57 is worth more than a complete one that never reaches
Stage 4.

#### The table is durable, and it does not block the rest of the phase

Write K to **`docs/qml/08-assertion-proposals.md`** and commit it. A proposal table that exists only
in chat dies with the session, and git is this project's durable store. Cross-reference it from
`DECISIONS.md` under a new decision ID so it cannot be silently forgotten.

**Once Pass 1's triage commit and Pass 2's allowed-column fixes are in, Stages 4 and 5 proceed.** K
does not gate them. The 57 are pre-existing and entirely outside QML; holding the project's release
document hostage to a backlog unrelated to the thing being released is a bad trade, and adjudicating
dozens of rows is not a good use of the owner before the rest of the work exists to look at.

What K *does* gate is the release document's **claims**: `08-release.md` must state the red count and
the per-script decomposition, link the proposals file, and is **forbidden from asserting "all gates
green" or any equivalent**. See §2H.4.

### 2I.4 Explicitly out of scope

**§2C.5 (noise experiments), §2C.6 (qudit spike) and §2F's WP6 (suggest-a-config) stay deferred.**
They are features, not defects, and this phase already carries seven harness migrations, four
carried defects, 57 triaged failures and the release document. Adding feature scope is how a
remediation phase ends up half-done on both halves. They are recorded in `DECISIONS.md` as
post-release candidates; the owner can promote them, but not into this phase.

### 2I.5 What 8A must prove

Real browser evidence, for the first time in this project:

- The QML Lab **renders in a browser** with the flag on: all four views, the algorithm selector
  driving dataset and limit changes, a Radix `Select` actually opening (no portalled content has ever
  been rendered), and the kernel's zero-epoch-row state showing its closed-form outcome rather than
  an empty chart.
- The regression Results view shows **MAE/RMSE in target units and a signed R²**, with no classifier
  metric anywhere — this is MT-006's visual half, and it can now be automated rather than deferred.
- The kernel heatmap renders with computed inline styles (MT-008) and the sample cap error is legible
  (MT-009).
- Polling **actually stops** on a terminal status — observed as the absence of a second request, not
  inferred from reading `refetchInterval`.
- The fail-closed state, per §2H.1: `/features` erroring hides the nav entry and `/qml-lab` shows the
  404 body. **Rendered, not grepped.** Then delete the regex guard at `qml-ui-check.mts:253`.

Anything in MT-001…MT-010 that this closes must be re-marked `AUTOMATED by <phase/commit>` in the
register — append-only, IDs never reused.

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

## 8A. Testing split — automate it, or register it. Never silently skip.

**Standing instruction from the project owner:** *manual testing is done by me explicitly, after all
phases are complete. Until then, automate every test you can; anything you cannot automate, skip it
and mark it as mine to do later.*

So every check you cannot run splits into exactly two outcomes, and there is no third:

1. **Automate it.** This is the default and the preferred answer. The repo's whole testing
   philosophy is that a hand-found defect gets a script so it is caught next time (§1.5, §8). SSR
   harnesses cover far more than you'd expect without a browser — `a11y-check.mts` is
   `renderToString` plus fake localStorage, not Playwright, and Phase 3 verified all four flag
   states that way.
2. **Register it.** If it genuinely cannot be automated in this sandbox, it goes in
   **`docs/qml/MANUAL_TEST_REGISTER.md`** — one running file for the whole project, not per-phase
   notes scattered across reports.

**A check that is neither automated nor registered does not exist**, and claiming a gate passed
without one of the two is the failure mode this section exists to prevent.

### The register's required shape

One row per deferred check, with enough detail that the owner can execute it cold, weeks later,
without reading the phase report:

| Field | What goes in it |
|---|---|
| ID | `MT-001`, `MT-002`, … stable, never reused or renumbered |
| Deferred by | phase and commit that could not automate it |
| What to do | exact clicks / commands, starting from a clean checkout |
| Expected | the observable result that means PASS, stated concretely |
| Why not automated | the specific missing capability, not "hard to test" |
| Blocks release? | yes/no — and if yes, which phase cannot close without it |

Keep it sorted and append-only. When a later phase *does* automate a registered item, do not delete
the row — mark it `AUTOMATED by <phase/commit>` and name the script, so the register stays a
complete history of what was ever deferred.

### Known register entries as of Phase 4

These are already deferred and must be carried forward, not rediscovered:

- **No Redis or Celery worker in the sandbox** → no browser-driven submit → train → monitor →
  cancel → results → inference round trip. A real POST returned 201 then `failed` on the Redis
  connection, which exercises the error path only.
- **No Docker binary** → the `qml-worker` service (§2A.5) is inspection-verified only. Its
  `profiles: ["qml"]` gating, `-Q qml --concurrency=1`, and the untouched `--concurrency=2` on the
  existing worker all need a real `docker compose --profile qml up`.
- **Per-task Celery limits under Windows `--pool=solo`** (§2A.2) — provable on Linux, not on the
  target OS.
- **`bench_qml.py --full` on the i5-13450HX** (§2B.1) — the only source of the numbers that set the
  shipped timeout. **This one blocks Phase 8.**
- **GPU path** — skipped by decision (§2B.5), not by failure; register it as a deliberate non-goal so
  nobody later mistakes the absence for an oversight.

### What this means for how you write phase reports

State the split explicitly in every report: *N checks automated (list the scripts), M deferred to
`MANUAL_TEST_REGISTER.md` (list the IDs).* A report that says "manual smoke test passed" without
either is a report that has not been done.

---

## 9. Phase-order amendment

Keep the master prompt's eight phases and their exit gates. Three adjustments:

- **Phase 0** additionally produces: the baseline table from §0 reproduced from your own runs;
  confirmation that `HEAD == origin/main` and the tree is clean; and the §1.3 dependency dry-run
  result. If any §0 number does not match, stop (§5.5).
- **Phase 2** additionally proves the §1.1 per-task time-limit isolation in both directions.
- **Phase 8** is amended. There is no merge step to prepare: the work is ported to `main` at each
  phase boundary, so Phase 8 becomes **"confirm `main` is deployable with the flag off, and document
  how to turn it on."** The release doc must cover the two-part enablement — `QML_ENABLED=true`
  **and** `docker compose --profile qml` for the `qml-worker` (§2A.5) — and the rollback must include
  the alembic `downgrade()` you proved in §1.6, the profile removal, and D-028's status.
  **`MT` register items marked "blocks release" must be listed in the release doc as pre-enablement
  checks**, not left buried in phase reports.

---

## 10. Definition of done

- `main` is green at the **current** baseline, not the Phase 0 one — §0's table is the starting
  point and each phase moves it. As of Phase 4: **1034 passed / 5 skipped**, typecheck 0, build
  PASS, harness FAILs **57 = 9+20+20+8**, goldens **190+804+3306 @ 1e-9**, a11y **0 criticals** —
  all re-run by you, all pasted.
- `docs/qml/MANUAL_TEST_REGISTER.md` exists, is complete, and every row marked "blocks release" is
  reproduced in `docs/qml/08-release.md` as a pre-enablement check (§8A).
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
