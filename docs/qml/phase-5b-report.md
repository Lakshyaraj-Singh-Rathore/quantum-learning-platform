# Phase 5b — execution dispatch (backend only)

Governed by §2D of `docs/prompts/QML_LAB_VISION_AGENT.md`. No UI work; that is §2E / Phase 5c.

## Headline

Before this phase, three of the four algorithms in the selector could not be run. `describe()`
advertised six datasets; the schema rejected three of them; and `services/qml_lab.py` built a
`VQC` unconditionally, so picking `hybrid_qnn` would have silently trained a VQC and reported it
as a hybrid. All four algorithms now dispatch, persist, reload and serve inference through their
own engines, and the capability document agrees with the create endpoint on all twelve advertised
pairs.

## Gates

| Gate | Phase 5 | Phase 5b | |
|---|---|---|---|
| `pytest` | 1145 passed / 5 skipped | **1199 passed / 5 skipped** (389.1 s) | +54 |
| Frontend files changed vs `origin/main` | 0 | **0** | unchanged |
| Tracked files | 599 | **603** | +4 |
| Alembic heads | 1 (`i4d7e0f3a6b9`) | 1 (`j5e8f1a4b7c2`) | linear |

**0 frontend files changed** is measured, not assumed:
`git diff origin/main --name-only -- frontend/ | wc -l` → `0`. Phase 5's by-construction argument
therefore carries: bundle hash identical, harness FAIL count unchanged, CSS rule-level diff empty,
because no input to any of them was touched.

### Tracked files: 599 → 603, itemised

| File | |
|---|---|
| `backend/app/quantum/qml_lab/algorithms.py` | the dispatch seam |
| `backend/alembic/versions/j5e8f1a4b7c2_qml_regression_epoch_metrics.py` | the one additive migration |
| `backend/tests/test_qml_dispatch.py` | 23 tests — invariants, engines, artifacts |
| `backend/tests/test_qml_dispatch_db.py` | 9 tests — DB round-trips, inference contract |

Modified, no new files: `api/qml_lab.py`, `models/qml.py`, `qml_lab/__init__.py`, `datasets.py`,
`limits.py`, `models.py`, `persistence.py`, `regression_data.py`, `trainer.py`,
`services/qml_lab.py`, `tests/test_qml_api.py` (+2), `tests/test_qml_migration.py` (+4),
`docs/qml/DECISIONS.md` (D-039…D-045). This report is the 604th file.

## §2D.3 — three terminal-status runs through the real worker path

Run via `run_qml_experiment.apply(args=[id])`, which executes the Celery **task body** — its
re-validation, its DB session handling, its terminal-status write — against a SQLite database
migrated to head. All four are shown; the gate asked for the three new ones.

```
algorithm           task result  db status   task            epochs  headline metric
--------------------------------------------------------------------------------------------
vqc                 completed    completed   classification  3       accuracy=0.7778
hybrid_qnn          completed    completed   classification  3       accuracy=0.7222
quantum_regression  completed    completed   regression      3       r2=+0.1582
quantum_kernel      completed    completed   classification  0       accuracy=0.7778
```

Epoch rows, read back with raw SQL:

```
vqc                  epoch=1  train_accuracy=0.6428571428571429 train_r2=None
vqc                  epoch=2  train_accuracy=0.8095238095238095 train_r2=None
vqc                  epoch=3  train_accuracy=0.8333333333333334 train_r2=None
hybrid_qnn           epoch=1  train_accuracy=0.6666666666666666 train_r2=None
hybrid_qnn           epoch=2  train_accuracy=0.7857142857142857 train_r2=None
hybrid_qnn           epoch=3  train_accuracy=0.8571428571428571 train_r2=None
quantum_regression   epoch=1  train_accuracy=None     train_r2=-2.060221715934504
quantum_regression   epoch=2  train_accuracy=None     train_r2=-0.8437804438388303
quantum_regression   epoch=3  train_accuracy=None     train_r2=-0.16142764191490855
quantum_kernel       -- no rows --
```

Those three negative R² values are the senior's hazard made concrete. Stored in `train_accuracy`,
epoch 1 would render as −206% accuracy. The D-033 test guards the Pydantic model, not the column,
so it would have passed the whole time.

**What `.apply()` does not prove.** It runs the task function in-process and synchronously. It
does not exercise broker delivery, message serialisation, the prefork pool, soft-time-limit signal
delivery, or concurrent execution. There is still no Redis in this sandbox
(`Error -2 connecting to redis:6379`), so those remain unverified. This is a stronger claim than
Phase 5's engine-level call and a weaker one than a real worker; it should be read as exactly
that.

## §2A.6 — four flag states, live servers

Two uvicorn processes, `QML_ENABLED` true then false:

```
flag     endpoint               status     body / meaning
--------------------------------------------------------------------------
ON       /features              200        {"qml_enabled":true}   (always mounted)
ON       /qml/describe          401        mounted, auth-gated - NOT 404
OFF      /features              200        {"qml_enabled":false}  (same route, no 404)
OFF      /qml/describe          404        router not mounted - honest 404
```

Visibility never depends on a 404: `/features` answered 200 in both states.

## The invariant that only the live server caught

The §2D.1 gap was proven falsifiable twice before any fix: the suite failed with
`ImportError: cannot import name 'algorithms'`, which proves nothing on its own, so the headline
invariant was re-run standalone against the unmodified backend —

```
advertised datasets: ['circles','damped_cosine','iris_binary','linear_mix','moons','sine']
REJECTED BY SCHEMA:  [('damped_cosine','ValidationError'),('linear_mix','ValidationError'),('sine','ValidationError')]
assert not rejected -> FAILS
```

After the registry and validator landed, the schema-level and engine-level invariants both passed.
**The API still returned 422 for all three regression datasets.** `POST /qml/experiments`
pre-flight-probes with `service.datasets.build_dataset` — a third construction site that neither
test touched. Found by posting all twelve advertised pairs at a live server:

```
  advertised pairs -- must NOT be 422:
    quantum_regression   sine            HTTP 422   <-- GAP
    quantum_regression   damped_cosine   HTTP 422   <-- GAP
    quantum_regression   linear_mix      HTTP 422   <-- GAP
```

After routing the probe through the dispatcher, all fifteen checks agree:

```
  advertised pairs -- must NOT be 422:
    vqc / hybrid_qnn / quantum_kernel  x  moons, circles, iris_binary   HTTP 201  (9/9 ok)
    quantum_regression  x  sine, damped_cosine, linear_mix              HTTP 201  (3/3 ok)
  task mismatches -- MUST be 422:
    vqc + sine, quantum_regression + moons, quantum_kernel + linear_mix HTTP 422  (3/3 ok)
```

This is now pinned by `test_every_advertised_pair_is_accepted_by_the_create_endpoint`, which was
run against the reinstated bug and fails with the three rejections named.

## Defect found in Phase 5's own work

`trainer.train` rebuilt its return value as `vqc.Parameters` regardless of the type passed in.
`hybrid.py:69` documents that `HybridParameters` is deliberately not a subclass because
`Parameters` reads `theta[:-1]` as circuit weights, which for a hybrid vector is the classical
block, and would "reshape into silent nonsense". The engine made the mistake impossible; the
trainer reintroduced it on the way out. Phase 5's tests compared `params.theta` numerically, which
is identical either way.

Fixed with `dataclasses.replace`. See D-043.

## §8A split

**111 automated + 54 new = 165 automated this phase**, 4 deferred, unchanged by ID:
MT-006, MT-007, MT-008, MT-009. The register still has 9 rows.

MT-006's re-scope stays in §2E.4: it needs both dispatch (done) and UI (not begun), so it remains
deferred rather than becoming newly automatable.

## Not verified — carried forward unchanged

No target-machine numbers; no Redis/Celery broker, so no true worker run, no broker-level
redelivery or time-limit-signal evidence; no docker; no screenshots; no GPU; no density-matrix
path; nothing has ever been OOM-killed, so the ceilings remain timings rather than capacity
measurements; Linux, not Windows. `qml_task_soft_time_limit` stays 900/1200 provisional. The
laptop benchmark (MT-001 / `--full`) still blocks Phase 8 and cannot be run from a sandbox.
