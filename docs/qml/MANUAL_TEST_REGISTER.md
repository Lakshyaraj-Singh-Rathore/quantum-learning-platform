# QML Lab — manual test register

**Standing instruction (§8A, project owner):** manual testing is done by the owner explicitly,
after all phases are complete. Until then every check has exactly two outcomes — **automated**
(a named script) or **registered here**. There is no third. A check that is neither does not
exist.

This is one running file for the whole project, **append-only and sorted by ID**. IDs are never
reused or renumbered. When a later phase automates a registered item, its row is **not deleted**
— the status becomes `AUTOMATED by <phase/commit>` and names the script, so this stays a
complete history of everything that was ever deferred.

| Status | Meaning |
|---|---|
| `OPEN` | still needs the owner to run it by hand |
| `AUTOMATED by <phase/commit>` | a later phase replaced it with a script; kept for history |
| `NON-GOAL` | deliberately not done; recorded so the absence is never mistaken for an oversight |

---

## MT-001 — Full browser round trip: submit → train → monitor → cancel → results → inference

- **Status:** OPEN
- **Deferred by:** Phase 2 (`e5e0b4b`), carried through Phases 3–5
- **Blocks release?** **Yes — Phase 8 cannot close without it.** This is the only check that
  exercises the product as a user meets it.
- **What to do:**
  1. From a clean checkout: `make upd` (or `docker compose up -d`) so Redis, Postgres, the API
     and the `qml` worker are all running — the QML worker needs its profile:
     `docker compose --profile qml up -d`.
  2. Enable the flag: as an authenticated staff user, set `qml_enabled` true (§1.7) and reload.
  3. Navigate to **QML Lab** in the sidebar. Configure a small experiment: `moons`, 4 qubits,
     2 layers, 200 samples, 20 epochs, `backprop`.
  4. Submit. Watch the progress view update per epoch.
  5. Submit a second, larger experiment and press **Cancel** mid-run.
  6. Open the completed first experiment's **Results**, then run a single **inference** from the
     saved model.
- **Expected:** step 4 reaches `completed` with a loss curve that descends and accuracy above
  the baseline floor; step 5 reaches `cancelled` within one batch, never `failed`; step 6 shows
  a confusion matrix whose four cells sum to the test-split size, and inference returns a class
  with a probability in `[0, 1]`.
- **Why not automated:** the sandbox has **no Redis and no Celery worker**. A real `POST`
  returns `201` and then `status: "failed"` with
  `Could not enqueue experiment: Error -2 connecting to redis:6379.` — which exercises the
  error path only. The happy path cannot be reached in-process; `task_always_eager` covers the
  engine but not the browser, the polling, or the cancel race.

## MT-002 — `qml-worker` Compose service actually starts and is isolated

- **Status:** OPEN
- **Deferred by:** Phase 3 (`096c855`)
- **Blocks release?** No — but it is the only proof the queue isolation works.
- **What to do:**
  1. `docker compose --profile qml up -d`, then `docker compose ps`.
  2. `docker compose exec qml-worker celery -A app.workers.celery_app inspect active_queues`
  3. `docker compose exec worker celery -A app.workers.celery_app inspect stats`
  4. Bring the stack up *without* `--profile qml` and confirm `qml-worker` does not appear.
- **Expected:** `qml-worker` consumes **only** the `qml` queue at `--concurrency=1`; the
  pre-existing `worker` still reports `--concurrency=2` and does **not** consume `qml`; without
  the profile flag `qml-worker` is absent while the rest of the stack is unchanged.
- **Why not automated:** **no `docker` binary in the sandbox.** The service definition was
  verified by inspection of `docker-compose.yml` only; nothing proves the daemon honours
  `profiles: ["qml"]` or the queue routing at runtime.

## MT-003 — Per-task Celery time limits under Windows `--pool=solo`

- **Status:** OPEN
- **Deferred by:** Phase 2 (`264c3ef`)
- **Blocks release?** No — but a silent failure here means a runaway job on the target OS.
- **What to do:** on the Windows target, start the worker with
  `celery -A app.workers.celery_app worker --pool=solo -Q qml --concurrency=1`; submit an
  experiment engineered to exceed `qml_task_soft_time_limit`; watch the worker log.
- **Expected:** the task raises `SoftTimeLimitExceeded`, the experiment lands in `failed` with a
  timeout message, and **the global `celery_soft_time_limit` is not consulted** — other queues
  keep their own limits. The in-trainer cooperative deadline should fire *first*, strictly below
  the soft limit, so the usual path is a clean `cancelled`/`failed` rather than a killed worker.
- **Why not automated:** the sandbox is **Linux with the default prefork pool**. Both directions
  of the limit were proven here, but `--pool=solo` has different signal behaviour on Windows and
  that difference is the entire risk.

## MT-004 — `bench_qml.py --full` on the target machine

- **Status:** OPEN
- **Deferred by:** Phase 4 (`954b9d2`)
- **Blocks release?** **Yes — Phase 8 cannot close without it.** It is the only source of the
  numbers that set the shipped timeout.
- **What to do:** on the i5-13450HX / RTX 4050 / 16 GB / Windows target, from a clean checkout
  with the backend venv active (PowerShell 5 — `&&` is a parser error, so these are separate
  statements):

  ```powershell
  cd backend
  $env:PYTHONPATH = "."
  python scripts\bench_qml.py --full --json ..\artifacts\bench-full.json --md ..\artifacts\bench-full.md
  ```

  Return `artifacts/bench-full.json`. Run it on mains power with no other heavy process, and do
  not interrupt it — a killed run is a ceiling data point, not a timing (§2B.6).
- **Expected:** completes in roughly 10–40 minutes and writes both files.
  `execution_law_verified` must be `true`; if it is `false` that is a finding, not a flaky run.
  The number that matters is the `projections` entry for
  `8q/4L/B32/backprop/default.qubit` — its `projected_seconds` is the measured maximum that
  `qml_task_soft_time_limit` must exceed by a stated safety factor.
- **Why not automated:** **the sandbox is not the target machine** (§2B.1) — a 2-core Xeon
  container with 3.85 GiB RAM against a 10-core laptop with 16 GB. Absolute wall-clock and peak
  RAM do not transfer, and a limit tuned from the container would be wrong in the dangerous
  direction. The scaling *shape* was measured here and does transfer; only the constants are
  missing.

## MT-005 — GPU path (CUDA-Q via `docker-compose.gpu.yml`)

- **Status:** **NON-GOAL** — skipped by decision (§2B.5, D-030), not by failure.
- **Deferred by:** Phase 4 (`954b9d2`)
- **Blocks release?** No. Recorded so the absence is never mistaken for an oversight.
- **What it would be:** `make up GPU=1` on a machine with a working NVIDIA runtime, confirming
  CUDA-Q is available and the Composer's 28-qubit GPU ceiling is reachable.
- **Why not automated, and why not done at all:** the sandbox has **no GPU and no `docker`**.
  Beyond that, `lightning.gpu` needs CUDA on Linux while the target is Windows (⇒ WSL2), and
  this repo's GPU support is **CUDA-Q**, a different stack that does not compose with a
  PennyLane device. Mixing them risks rebuilding without `-f docker-compose.gpu.yml` and
  destroying the CUDA-Q image. Out of scope unless the owner asks.

## MT-006 — Regression results render as regression, not as a zeroed classifier

- **Status:** DEFERRED
- **Deferred by:** Phase 5 (regression commit)
- **Blocks release?** **Yes** — this is the exact failure §2C.4 exists to prevent.
- **Steps:**
  1. Start the stack (`make up`), open the QML Lab, choose algorithm **Quantum regression**.
  2. Run `sine` with `n_qubits=4`, `n_layers=3`, 25 epochs.
  3. Read the results panel and the per-epoch chart.
- **Expected result:** MAE, RMSE and R² are shown, each with units or a stated range. **No
  accuracy, precision, recall, F1 or confusion matrix appears anywhere** — not greyed out, not
  as `0`, not as `—`. The epoch chart plots loss and R², not accuracy. MAE and RMSE are in the
  target's own units (so for `sine`, roughly the `[-1, 1]` range of the raw target, **not** the
  scaled one). R² may be negative and must render with its sign.
- **Missing capability:** no browser automation against a running stack in this environment,
  and **no UI exists for the regression algorithm yet** — the engine, metrics, datasets,
  trainer and baseline landed this phase; the config and results views did not.
- **What *is* automated, so the gap is narrow:** `tests/test_qml_regression.py` asserts at the
  type level that `RegressionResult` has **no** `accuracy`/`precision`/`recall`/`f1`/
  `confusion_matrix` attribute, and that `RegressionEpochRecord` has no `train_accuracy`/
  `test_accuracy`. A UI therefore *cannot* read a zeroed accuracy off the payload — it would
  have to invent one. The deferred part is purely what the rendered page shows.

## MT-007 — Re-uploading frequency budget holds for a human-chosen configuration

- **Status:** DEFERRED
- **Deferred by:** Phase 5 (regression commit)
- **Blocks release?** No — the budget is enforced by a build-failing test for every dataset
  shipped; this covers only a user driving the sliders to a bad combination.
- **Steps:** run `damped_cosine` (angle-frequency 4) at `n_layers=1`, then at `n_layers=4`.
- **Expected result:** at `n_layers=1` the fit is visibly flat and R² is near zero or negative;
  at `n_layers=4` it tracks the curve. The UI should warn when `n_layers` is below the
  dataset's required angle-frequency **rather than** letting the user conclude the model is
  broken.
- **Missing capability:** the warning is a UI affordance and there is no regression UI yet.
  `REQUIRED_ANGLE_FREQUENCY` is exported and `/qml/describe` is the intended source for it, so
  the data the warning needs already exists server-side.

## MT-008 — Kernel heatmap renders with inline styles, not an interpolated class

- **Status:** DEFERRED
- **Deferred by:** Phase 5 (kernel commit)
- **Blocks release?** No — the engine is covered; this is purely a rendering rule.
- **Steps:** run a `quantum_kernel` experiment and inspect the Gram-matrix heatmap in devtools.
- **Expected result:** each cell carries an inline `style` with its own computed colour. **No
  dynamically-interpolated Tailwind class** (e.g. `` `bg-blue-${level}` ``) appears — those are
  not in the compiled CSS and render as unstyled cells (§3.2).
- **Missing capability:** no kernel UI exists yet; the engine, LSSVM fit and limits landed this
  phase, the heatmap did not. Also needs a browser to inspect computed styles.
- **What *is* automated:** the Gram matrix is asserted symmetric with an exact unit diagonal,
  and the evaluation count is asserted to be the strict upper triangle by counting QNode calls,
  so the data the heatmap renders is already pinned.

## MT-009 — Kernel sample cap is reachable and the error is legible in the UI

- **Status:** DEFERRED
- **Deferred by:** Phase 5 (kernel commit)
- **Blocks release?** No.
- **Steps:** set the sample slider to its maximum for `quantum_kernel`, then try to exceed it.
- **Expected result:** the slider stops at **250** (not the global 1000), driven by
  `/qml/describe`; if a cap error is ever surfaced it reads as one sentence naming the cap and
  the evaluation count, **not** as `q; u; a; n; t; u; m; ...`.
- **Missing capability:** no kernel UI. The character-shredding failure mode was real and is
  now covered by a unit test (D-037), so this row is about the rendered control, not the text.
