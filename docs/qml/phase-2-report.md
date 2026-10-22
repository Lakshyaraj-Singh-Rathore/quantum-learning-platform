# Phase 2 — API, Celery/Redis, persistence

Branch `arena/63ae45b4-quantum-learning-platform`, built against `origin/main @ feb21c7`
(558 tracked files). Every number below comes from a command run this session.

**Branch deviation, repeated per standing instruction.** Arena pins this session to
`arena/63ae45b4-quantum-learning-platform`. I never push to `main`; the senior ports at each phase
boundary. No `--force` was used.

---

## 1. Headline

| Gate | Baseline | Measured | Verdict |
|---|---|---|---|
| Backend tests | 971 passed, 5 skipped | **1030 passed, 5 skipped** (142.13 s) | PASS — 971 + 59 new |
| Typecheck | 0 errors | **0 errors** | PASS |
| Build | 2090 modules, `index-CoImnjWX.js` | **2090 modules, `index-CoImnjWX.js` 639.18 kB** | PASS — byte-identical bundle |
| Goldens | 190 + 804 + 3306 @1e-9 | **190 + 804 + 3306** | PASS |
| Harness FAIL | 57 = 9+20+20+8 | **57 = 9+20+20+8** | PASS |
| Harness PASS | 284 / 307 | **377** (reconciled in §7) | PASS — no script changed behaviour |
| a11y | 0 criticals | **0 criticals** (9 PASS) | PASS |
| Migration | — | up → **down** → up, single linear head | PASS |
| Additive gate | exactly the allowlist | **8 M, 0 D, 9 A, 567 tracked** — 3 code M beyond §2A.4, see §2 | **FLAGGED** |

The frontend bundle hash is unchanged from Phase 0 and Phase 1, which is the strongest available
evidence that Phase 2 changed nothing a browser can see.

---

## 2. ⚠ The one thing needing your decision: §2A.4 contradicts §2A.2 and §2A.3

**§2A.4** says the modified-file set is *exactly* five and "any modification beyond those five is a
§5.2 stop". But two sections earlier the same document instructs me to modify two Phase 1 files
that are now on `main`:

- **§2A.2** — "add a cooperative `deadline_seconds` on `train()`" → modifies
  `backend/app/quantum/qml_lab/trainer.py`
- **§2A.3** — "rename the constant to `MAX_CONCURRENT_JOBS`" → modifies
  `backend/app/quantum/qml_lab/limits.py`

Both files were purely additive in Phase 1 and became part of `main` when you ported it, so
touching them now registers as a modification. I did **not** treat this as a §5.2 stop, because
stopping on instructions the same document gives two pages earlier would be perverse. I
implemented both and am flagging the conflict instead.

**Actual modified set — 8 files, each traceable to an explicit authorisation:**

| File | Authorised by | Change |
|---|---|---|
| `backend/app/api/router.py` | §2A.4 | one flag-gated `include_router` |
| `backend/app/config.py` | §2A.4 | four `qml_*` settings, nothing else |
| `backend/app/workers/celery_app.py` | §2A.4 | `include=[...]` + `task_routes` |
| `backend/app/models/__init__.py` | §2A.4 | register the two new models |
| `backend/app/quantum/qml_lab/limits.py` | **§2A.3** | constant rename + global scoping |
| `backend/app/quantum/qml_lab/trainer.py` | **§2A.2** | `deadline_seconds` parameter |
| `backend/tests/test_qml_config.py` | consequence of §2A.3 | one assertion follows the rename |
| `docs/qml/DECISIONS.md` | **§2A.4** | append D-011b and D-013…D-019 |

`test_qml_config.py` is a mechanical follow-through — `assert limits.MAX_CONCURRENT_JOBS == 1`. No
assertion was weakened or removed.

Counting the two documentation files, the full gate reads **8 modified, 0 deleted, 9 added,
567 tracked** (558 + 9). `DECISIONS.md` is explicitly unblocked by §2A.4; only three *code* files
sit outside the §2A.4 list.

**Deletions: zero.** Suggested amendment: §2A.4 should read "exactly these five *pre-existing
application* files, plus whatever §2A.2/§2A.3 explicitly direct".

---

## 3. What was built

**New files (9):**

```
backend/app/models/qml.py                                  QmlExperiment + QmlEpochMetric
backend/app/services/qml_lab.py                            orchestration shared by API and worker
backend/app/api/qml_lab.py                                 8 routes (named for noise_lab/qudit_lab)
backend/app/workers/qml_tasks.py                           the per-task-limited Celery task
backend/alembic/versions/i4d7e0f3a6b9_add_qml_experiments.py
backend/tests/test_qml_api.py                              32 tests
backend/tests/test_qml_tasks.py                            18 tests
backend/tests/test_qml_migration.py                        9 tests
docs/qml/phase-2-report.md                                 this file
```

`services/qml_lab.py` is not in your list of new files. It exists so the router stays thin and the
Celery task is wiring only — and so the whole run is exercisable in a test without a broker, which
is how the worker tests run.

**Routes** (`/qml`, all behind the flag): `GET /features`, `GET /describe`, `POST /experiments`,
`GET /experiments`, `GET /experiments/{id}`, `GET /experiments/{id}/result`,
`POST /experiments/{id}/cancel`, `POST /experiments/{id}/inference`.

---

## 4. Evidence for each §2A requirement

### 4.1 Flag off ⇒ absent, not merely hidden

Against the live server (`uvicorn`, default settings):

```
GET  /qml/features                -> 404      GET  /qml/experiments/1/result    -> 404
GET  /qml/describe                -> 404      POST /qml/experiments             -> 404
GET  /qml/experiments             -> 404      POST /qml/experiments/1/cancel    -> 404
GET  /qml/experiments/1           -> 404      POST /qml/experiments/1/inference -> 404
GET  /health                      -> 200      GET  /openapi.json                -> 200
qml paths in the live OpenAPI schema : 0
total paths in the live OpenAPI schema: 58      (Phase 0 baseline: 58)
```

Route-table diff:

```
flag OFF : 56 APIRoute paths
flag ON  : 63 APIRoute paths
delta    : 7 added, 0 removed
non-qml routes identical: True
default qml_enabled: False
```

### 4.2 Migration — additive, linear, and actually reversed

```
$ alembic heads
i4d7e0f3a6b9 (head)                      <- single head

$ alembic upgrade head
Running upgrade h3c6d9e2f5a8 -> i4d7e0f3a6b9, Add qml_experiments and qml_epoch_metrics...
table present? ['qml_experiments']

$ alembic downgrade -1
Running downgrade i4d7e0f3a6b9 -> h3c6d9e2f5a8, Add qml_experiments and qml_epoch_metrics...
table gone? DROPPED
other tables intact? 21 tables

$ alembic upgrade head
i4d7e0f3a6b9 (head)
```

`test_qml_migration.py` repeats this per-test and additionally asserts the upgrade adds **exactly**
`{qml_experiments, qml_epoch_metrics}`, that downgrade restores the table set precisely, that each
table's columns match its ORM model, and that a duplicate `(experiment_id, epoch)` raises
`IntegrityError` at the database level.

### 4.3 Per-task time limits — both directions

```
qml  soft/hard : 900 / 1200          <- its own decorator limits
sim  soft/hard : None / None         <- inherits the globals
conf soft/hard : 8 / 15              <- globals unchanged
```

Four tests cover this, including `test_the_two_tasks_have_genuinely_different_budgets`. Raising
`celery_soft_time_limit` to 900 makes three of them fail (MUT-E).

### 4.4 The cooperative deadline

```
deadline 1s   -> status=timed_out  epochs=3  elapsed=1.13s  history=3 records
deadline 600s -> status=completed  epochs=2
cancel        -> status=cancelled            (not conflated with timeout)
no deadline   -> status=completed            (backward compatible)
```

Partial history survives a timeout, and no model artifact is written for an interrupted run —
a half-trained file that looks loadable is worse than none.

### 4.5 Queue routing

```
route for app.workers.qml_tasks.run_qml_experiment -> queue 'qml'
route for app.workers.tasks.run_simulation         -> queue 'celery'
```

### 4.6 Cancel semantics

Idempotent (two cancels → 200, 200), 409 on a terminal experiment with the result left untouched,
`404` then `403 "Not your job"` matching `api/jobs.py:205` verbatim.

---

## 5. ⚠ Operational consequence of the `qml` queue — read before enabling the flag

`docker-compose.yml:81` starts the worker as:

```
celery -A app.workers.celery_app.celery_app worker --loglevel=info --concurrency=2
```

There is **no `-Q`**, so that worker consumes the default `celery` queue only. With `task_routes`
sending QML tasks to the `qml` queue, **the shipped worker will not execute them** — experiments
would sit `queued` indefinitely.

I did not change `docker-compose.yml`: it is outside the allowlist and is deployment
configuration. Since the flag is off by default nothing is broken today, but turning it on
requires a worker consuming that queue, and `--concurrency=1` is what actually delivers the
concurrency guarantee (the pre-dispatch 409 only explains it):

```
celery -A app.workers.celery_app.celery_app worker -Q qml --concurrency=1            # Linux/Docker
celery -A app.workers.celery_app.celery_app worker -Q qml --concurrency=1 --pool=solo  # Windows
```

This belongs in `docs/qml/08-release.md` at Phase 8; flagged now so it is not discovered later.

---

## 6. Mutation testing — nine mutations, two caught vacuous tests

Phase 1's campaign found a vacuous test, so I repeated it. Every mutation was auto-reverted and
the restore verified by `diff`.

| # | Mutation | Result |
|---|---|---|
| A | `qml_enabled` defaults to `True` | 9 failed ✓ |
| B | concurrency scoped per-user (the §2A.3 bug) | 1 failed ✓ |
| C | `timed_out` collapsed into `failed` | 1 failed ✓ |
| D | `limits.enforce` removed from the worker | **passed ✗ → fixed → fails ✓** |
| E | global `celery_soft_time_limit` raised to 900 | 3 failed ✓ |
| F | `UniqueConstraint` removed from the epoch model | **passed ✗ → fixed → 2 fail ✓** |
| G | `task_routes` deleted | 1 failed ✓ |
| I | `db.expire` removed from `CancelPoller` | **passed ✗ → fixed → fails ✓** |
| J | trainer deadline never fires | 1 failed ✓ |

**Three findings worth keeping:**

**D — `limits.enforce` was untestable as written.** `limits.check()` mirrors the Pydantic field
bounds exactly, so no config can violate it without failing schema validation first. My test used
`n_qubits=64` and passed for the wrong reason (a `ValidationError`, not a limit breach). Split into
two tests: one asserting the schema rejects a corrupted stored row (`error.startswith
("ValidationError:")`), and one that monkeypatches `MAX_QUBITS` down to 1 so a *schema-valid*
config becomes illegal — the only scenario that actually exercises `limits.enforce`, and the
scenario the code exists for.

**I — SQLAlchemy's identity map holds weak references.** My cancel test primed the map with
`worker_db.get(...)` and discarded the result, so the object was garbage-collected and the next
`get()` silently re-queried the database — the test passed even with `db.expire` removed. The real
worker holds `experiment` in a local for the whole run. A standalone probe confirmed the hazard is
real:

```
worker initial cancel_requested : False
WITHOUT expire, worker re-reads : False   <- stale
WITH expire,    worker re-reads : True
```

The test now holds a strong reference, as the worker does, and asserts the staleness precondition
explicitly.

**F — my first mutation was itself wrong.** Shifting `epoch` by a constant still collided, so it
proved nothing. The sound mutation is removing the `UniqueConstraint` from the model (conftest
recreates the schema per run), which makes both redelivery tests fail.

---

## 7. Harness PASS 377 vs the recorded 284/307 — reconciled, baseline not adopted

FAIL is **57**, and the breakdown is **exactly** `render-codelab 9 + render-games 20 +
render-p5 20 + render-results 8`. No script flipped in either direction.

The PASS difference is a **counting-methodology** difference, not a behaviour change. The §0
baseline table counted one invocation per `.mts` file; two npm scripts chain several:

| Script | §0 table | npm script | Why |
|---|---:|---:|---|
| `render-check` | 24 | **65** | npm runs it 3× (default, `--anon`, `--staff`) |
| `curriculum-check` | 29 | **58** | npm runs it 2× (default, `--auth`) |

Proven by running the bare files:

```
npx tsx scripts/render-check.mts      -> 24 PASS   [§0 table: 24]
npx tsx scripts/curriculum-check.mts  -> 29 PASS   [§0 table: 29]
```

Every other script matches its baseline exactly, including `smoke-auth` 13 and `smoke-composer` 10
once the API server has a working database. `377 = 284 + 23 (smoke pair) + 29 + 41`.

**Reported, not adopted.** Recommended §0 correction: state whether the harness figure counts npm
scripts or bare `.mts` invocations, since the two legitimately differ by 70.

One real trap worth recording: started with default settings the API silently falls back to
PostgreSQL and fails every auth call (`psycopg.OperationalError: Name or service not known`),
which scores `smoke-auth` 0/0 rather than failing loudly. It needs
`DATABASE_URL=sqlite:///...` to be a valid harness target.

---

## 8. What I could not verify

- **Windows / `--pool=solo`.** Documented, not tested, exactly as §2A.2 directs. The Linux half is
  proven; the cooperative deadline is the platform-independent mechanism and needs no SIGALRM.
- **A real broker.** All Celery execution here is `task_always_eager=True`. Routing is asserted
  through `celery_app.amqp.router`, not by observing a worker drain the `qml` queue.
- **Redelivery under a real worker.** Simulated by invoking the task twice against the same row.
  The database constraint is the guarantee and it is verified directly; what is untested is
  Celery's redelivery itself.
- **Concurrency under true parallelism.** The 409 is tested with a planted non-terminal row, not
  two simultaneous requests. The structural guarantee is `-Q qml --concurrency=1`, which needs the
  worker described in §5.
- **Timing at scale.** Phase 4's job. The 900 s soft limit and the 30 s margin are provisional.

---

## 9. Decisions recorded

`docs/qml/DECISIONS.md` now carries **D-011b** (the shallow-clone correction) and
**D-013…D-019**, as §2A.4 permits. D-017 and D-018 explicitly record that your two-table and
two-layer-timeout rulings superseded my single-table and no-trainer-change proposals, and why your
arguments were better. D-019(b) records the one deviation I chose: `test_loss`/`test_accuracy`
rather than `val_*`, so the ORM and the engine cannot drift.
