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
    pip install psutil
    $env:PYTHONPATH = "."
    python scripts\bench_qml.py --full --json ..\artifacts\bench-full.json --md ..\artifacts\bench-full.md
    ```

    **`pip install psutil` is not optional cosmetics.** `total_ram_gib()` reads `/proc/meminfo`,
    which does not exist on Windows, and falls back to `psutil` (`bench_qml.py:89-101`). `psutil` is
    **not** in `requirements.txt` — it is a benchmark-only dependency and does not belong there — so
    without it the run completes but records `total_ram_gib: null`. Peak RAM is one of the
    measurements §2B.1 says does not transfer from the sandbox and must come from this machine, so a
    null there is a hole in the only report that can fill it. Do not add it to `requirements.txt` to
    fix this; install it into the venv.

    Return `artifacts/bench-full.json`. Run it on mains power with no other heavy process, and do
    not interrupt it — a killed run is a ceiling data point, not a timing (§2B.6). Note that
    `artifacts/` is gitignored, so the file will not commit itself; it has to be sent back
    deliberately.

    **It will not take 25 hours.** That figure from Phase 4 is a *projection the script outputs*,
    not something it measures. `--full` times a **single gradient step** in each of **45 cells**
    (7 qubit-scaling + 4 layer-scaling + 4 batch-scaling tuples, × 2 gradient methods × 2 devices,
    minus the 15 lightning+backprop cells that are skipped because a C++ statevector cannot
    differentiate), 5 reps each, and then extrapolates. Every cell carries a `budget_s = 120.0` cap,
    so a slow cell is recorded with a non-`ok` status rather than hanging the run.
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

- **Status:** DEFERRED — **re-scoped by Phase 5c to its visual half.** ID retained deliberately:
  the risk it names (a regression run wearing a classifier's clothes) is unchanged; what shrank
  is the portion a human still has to look at.
- **Deferred by:** Phase 5 (regression commit). Re-scoped Phase 5c (UI commit).
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

### What Phase 5c automated (the structural half — no longer manual)

`frontend/web/scripts/qml-task-check.mts` renders the real components server-side against
payloads captured from an actual worker-path run and asserts, against the regression payload:

| Assertion | What it rules out |
| --- | --- |
| no tile headed `Train acc` / `Test acc` exists in the markup | the zeroed-classifier failure itself |
| the string `0.0%` never appears | `null` coerced to `0` by `*100` |
| no `—` appears under an accuracy heading | a placeholder implying the metric merely went missing |
| `finiteSeries` returns 0 points for `train_accuracy` over 3 null epochs | a flat line at 0% under an "accuracy" legend |
| `finiteSeries` emits no `value === 0` for those rows | the same bug via a different route |
| MAE/RMSE render with the `y` unit suffix, never `%` | a target-unit error read as a percentage |
| the VQC payload *still* shows an accuracy tile and no R² | an over-broad fix that hides real accuracies |

Both halves are mutation-proven: reinstating the Phase 3 behaviour (plot nulls as-is, render the
tile unconditionally) turns two assertions red, and making `finiteSeries` coerce `null → 0` turns
two different ones red. The failing output is pasted in `docs/qml/phase-5c-report.md`.

### What remains manual, and why it is now narrow

Three things only, all of which need eyes on a running browser:

1. **R²'s sign is legible at a glance** — the harness asserts a `+`/`−` character is emitted next
   to the value; it cannot judge whether a negative score *reads* as negative to a person, or
   whether the colour chosen for "worse" reinforces or fights the sign.
2. **MAE/RMSE units are believable in context** — the harness asserts the literal suffix ` y`;
   only a human can confirm that a 0.595 next to a target ranging over `[-1.099, 1.014]` is
   presented so the reader understands it is an error in target units, not a fraction.
3. **The R² epoch curve reads as a curve, not a glitch** — the series now arrives
   (`load_history` was fixed in `85d7bda`; the captured regression history carries
   `train_r2 = -2.060, -0.844, -0.161`) and `qml-task-check` asserts the points are plotted
   with their signs and that no null becomes a zero. What a human still has to judge is
   whether a curve that *starts below the axis at -2.06 and climbs* reads as a model
   improving from worse-than-the-mean, rather than as a rendering fault.

- **Missing capability:** no browser automation against a running stack in this environment.
  (The Phase 5 note "no UI exists for the regression algorithm yet" is **obsolete** — the config,
  training and results views all landed in Phase 5c.)

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

## MT-010 — The Gemini explanation against a real key

- **Status:** OPEN
- **Deferred by:** Phase 6 (AI commit)
- **Blocks release?** **Yes** — the configured path has never executed. Everything automated in
  Phase 6 runs against a fake transport or the unconfigured branch.
- **Why it cannot be automated here:** `GEMINI_API_KEY` is absent in the sandbox and
  `is_configured()` (`gemini_client.py:88`) additionally requires an importable
  `google.generativeai`. There is no way to exercise a live call, and stubbing one into looking
  like it worked would be worse than leaving it open. Note the platform **already** carries an
  untested live Gemini path (the tutor, Code Lab, Smart Composer); this row adds a fourth caller,
  it does not add the first risk.
- **Steps (cold-executable):**
  1. Set `GEMINI_API_KEY` in `.env` and confirm `pip show google-generativeai` returns a version.
  2. `make up`, open the QML Lab, run any experiment to completion.
  3. On the Results tab press **Explain**.
  4. Repeat for one run of each task: a `vqc` run on `moons` and a `quantum_regression` run on
     `sine`.
- **Expected result:**
  - Prose appears within ~10 s, in two or three short paragraphs, with no markdown headings.
  - **Every number in the prose also appears in the "Measured" table directly beneath it.**
    Any figure in the prose that is not in that table is a confabulation and the test fails.
  - The regression explanation mentions **no** accuracy, precision, recall, F1 or confusion
    matrix; the classification explanation mentions **no** R², MAE or RMSE.
  - A negative R² is described as worse than predicting the mean, not as a small positive score.
  - No claim of quantum advantage.
  - The server log contains no API key and no full prompt payload.
- **What is already automated, so the gap is narrow:** `tests/test_qml_ai.py` (14) asserts the
  prompt carries the exact stored figures, that the system instruction forbids inventing values,
  that over-length input is rejected rather than truncated, that the unconfigured path returns a
  useful body and never a 500, and that no key is echoed. `tests/test_qml_api.py` adds the
  route's 401/403/404/409/503 behaviour and the flag-off 404. What remains is purely **whether
  the model obeys the instruction**, which no amount of local testing can establish.
