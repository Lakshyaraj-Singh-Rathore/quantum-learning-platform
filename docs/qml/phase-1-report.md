# Phase 1 Report — Backend QML Engine

**Phase:** 1 — engine only. No API, no Celery task, no migration, no frontend.
**Base:** `origin/main @ 46576c8`
**Branch:** `arena/63ae45b4-quantum-learning-platform` (session-pinned; the senior ports to `main` at
phase boundaries — nothing was pushed to `main`).
**Instruction set:** `docs/prompts/QML_LAB_VISION_AGENT.md` @ `46576c8`, §0 / §1A / §2.1 / §2.3 re-read
before starting.

Every number below came from a command run in this session.

---

## 1. Scope compliance

The hard limit was **modify zero existing files**.

```
$ git diff --diff-filter=MD --name-only origin/main HEAD
[0 entries]
```

**22 files added, 0 modified, 0 deleted.** Every one sits under `backend/app/quantum/qml_lab/` or
`backend/tests/`:

| Engine (13) | Tests (9) |
|---|---|
| `__init__.py`, `errors.py`, `limits.py`, `models.py`, `datasets.py`, `encoder.py`, `circuit.py`, `vqc.py`, `trainer.py`, `evaluator.py`, `persistence.py`, `baseline.py`, `data/iris.csv` | `test_qml_config.py`, `test_qml_datasets.py`, `test_qml_circuit.py`, `test_qml_gradients.py`, `test_qml_trainer.py`, `test_qml_persistence.py`, `test_qml_evaluator.py`, `test_qml_baseline.py`, `test_qml_acceptance.py` |

3,227 lines of Python across the two groups.

**Tracked file count: 535 + 23 = 558.** The 23rd added file is this report, in `docs/qml/`. That is one
file outside the two named directories; it is added rather than modified, it is the deliverable §10 and the
master prompt both require, and it is flagged here rather than slipped in. **`docs/qml/DECISIONS.md` was
deliberately *not* edited** — it already exists on `main`, and editing it would have broken the additive
check. The four new decisions are in §7 below, ready to be folded into it at the port.

Deferred to Phase 2 exactly as instructed: router registration, `models/__init__.py`, the migration,
`celery_app.py`, `package.json`.

### 1.1 Isolation, verified not asserted

```
$ grep -rnE "^\s*(import|from)\s+(celery|fastapi|sqlalchemy|sklearn|torch|pickle)" app/quantum/qml_lab/
  none — engine is pure
```

The engine is a library. That is what lets cancellation be tested without a broker, and it is why the
Phase 2 worker can re-use it unchanged.

---

## 2. Gates

| Gate | Baseline (§0) | Measured | Verdict |
|---|---|---|---|
| Backend tests | 818 passed, 5 skipped | **971 passed, 5 skipped** (146.50 s) | PASS — 818 + 153 new, zero regressions |
| Typecheck | 0 errors | **0 errors** (`npm run typecheck`, exit 0) | PASS |
| Build | PASS, ~2090 modules | **PASS, 2090 modules**, 639.18 kB | PASS |
| Goldens | 190 + 804 + 3306 @1e-9 | **190 + 804 + 3306 @1e-9** | PASS |
| Harness FAILs | 57 = 9+20+20+8 | **57 = 9+20+20+8** | PASS |
| Harness PASSes | 284 | **307** with `API_TARGET`, **284** without | explained in §2.1 |
| a11y | 0 criticals | **0 criticals** | PASS |

Phase 1 touched no frontend code, and the build output proves it: the emitted bundle is
`dist/assets/index-CoImnjWX.js` at 639.18 kB — **the same filename hash as Phase 0**. A content hash is a
stronger statement than "the build passed": the frontend is byte-identical.

### 2.1 The 284 vs 307 PASS discrepancy — measured, explained, not absorbed

§0 records 284 PASS. With `API_TARGET=http://127.0.0.1:8000` set as §0 itself now instructs, the loop
returns **307**. Both numbers were reproduced back to back:

```
WITHOUT API_TARGET : PASS=284 FAIL=57
  smoke-auth     : PASS=0
  smoke-composer : PASS=0
WITH    API_TARGET : PASS=307 FAIL=57
delta = 13 + 10 = 23;  284 + 23 = 307
```

The entire difference is `smoke-auth` (13) and `smoke-composer` (10), which abort with
`ApiError: Cannot reach the API` when the target port is wrong and contribute **0 PASS and 0 FAIL** — they
crash before printing any assertion line, so they deflate PASS rather than inflating FAIL as §0 predicts.

**The recorded 284 is therefore the count with those two harnesses unable to reach the API.** No test
changed in Phase 1. I have not adopted 307 as the baseline; both figures are reported, and §0's number is
reproducible on demand by unsetting `API_TARGET`. **Suggested correction for the senior:** §0 should read
*307 PASS / 57 FAIL with `API_TARGET` set, 284 without*. The FAIL count — the actual regression gate — is
57 either way.

---

## 3. The nine QNN acceptance criteria

All nine are discharged by `tests/test_qml_acceptance.py`, which shares **one real training run**
(moons, 80 samples, 2 qubits, 2 layers, 10 epochs, seed 7) so the evidence is internally coherent rather
than nine unrelated fixtures.

| # | Criterion | How it is demonstrated |
|---|---|---|
| 1 | Valid parameterised circuit executes | `qml.draw` output contains the real `RY`/`RZ` ansatz; `<Z>` lands in [-1, 1] |
| 2 | Predictions derived from measurements | asserts `decision == measured_expval + bias` exactly, and the label is the sign of that |
| 3 | Real training loss | loss falls across epochs **and** the reported value is recomputed independently to 1e-9 |
| 3b | It actually learns | train accuracy ≥ 0.75, test ≥ 0.70 — a circuit that merely runs fails this |
| 4 | Gradients via a supported method | backprop and parameter-shift both non-zero and agreeing < 1e-9 |
| 5 | Parameters updated | ‖Δθ‖ > 1e-3 with ≥ 3 individual parameters moved |
| 6 | Completes within limits | `limits.enforce` passes; wall clock well inside the proposed 900 s soft limit |
| 7 | Save / reload | round-trips through JSON + `.npz`, config compares equal |
| 8 | Identical predictions after reload | `np.array_equal` on both probabilities and labels — not `allclose` |
| 9 | Automated tests pass | 153 new tests, 0 failures |

Measured learning across datasets (backprop, 15 epochs, 120 samples, seed 7):

| Dataset | qubits | train loss | train accuracy | test accuracy |
|---|---:|---|---|---:|
| moons | 2 | 1.9457 → 0.3448 | 0.250 → 0.905 | 0.833 |
| moons | 4 | 0.5470 → 0.3481 | 0.833 → 0.893 | 0.833 |
| circles | 2 | 1.0837 → 0.5395 | 0.667 → 1.000 | 1.000 |
| iris_binary | 4 | 0.6193 → 0.3152 | 0.871 → 0.986 | 1.000 |

---

## 4. Defects found and fixed during the phase

### 4.1 A genuinely deprecated PennyLane API — in my own code

§1A asked which API is deprecated. Phase 0 probed PennyLane's public surface and found **zero**
deprecation warnings from `AngleEmbedding`, `BasicEntanglerLayers`, `qnode`, `expval` or `PauliZ`; the only
warning was emitted at **import time** by `pennylane/__init__.py:212` because numpy is pinned below 2.0.
That conclusion was correct but incomplete — writing the trainer surfaced a real one:

```
pennylane/_grad/grad.py:259: PennyLaneDeprecationWarning:
argnum in qml.grad has been renamed to argnums to match jax and catalyst.
```

Fixed by using `argnums`. Verified afterwards: a full `train()` now emits **exactly one** deprecation
warning, the environmental numpy one, which cannot be removed without moving a pin that §1.3 forbids.

### 4.2 The loss function was wrong, and the symptom looked like "the model just doesn't learn"

The first implementation used binary cross-entropy over `p = (1 + <Z> + bias) / 2`. Measured result:

```
loss 0.6601 -> 0.6612 over 6 epochs      (worse, not better)
train accuracy 0.476 -> 0.500
confusion matrix [[9, 0], [9, 0]]        (every sample predicted class 0)
```

Rather than tuning the learning rate, I measured the gradient:

```
decision values: min -0.999 max 1.000    (the measurement saturates, as it must)
grad norm: 199.95763  max|g|: 199.95625  (one parameter carrying all of it)
```

**Root cause:** `<Z>` is a measured expectation value and saturates at exactly ±1, so the linear link maps
samples onto probabilities of exactly 0 and 1 — precisely where the log-loss derivative is `1/ε`. With
`ε = 1e-7` that is a gradient of order `1e7`, and Adam's per-parameter normalisation converts it into a
full-size step every iteration, so the optimiser thrashed.

**Fix:** squared error against `{-1, +1}` targets, which has bounded gradients across the whole range of a
measurement and is the standard objective for this classifier. The reasoning and the measured numbers are
recorded in the `square_loss` docstring so the next person does not re-litigate it. Results after the fix
are in §3.

This is the difference between a model that "runs and returns measurements" and one that classifies — the
exact failure mode the master prompt says does not count.

### 4.3 Mutation testing caught a vacuous test of mine

Three deliberate mutations, each reverted immediately:

| Mutation | Test | Result |
|---|---|---|
| Fit the scaler on train **+ test** | `test_scaler_statistics_come_from_the_train_split_only` | **failed** ✓ |
| Delete the epoch-boundary cancel check | `test_cancellation_is_checked_at_the_epoch_boundary_too` | **failed** ✓ |
| Remove the Hadamard before `RZ` encoding | `test_every_rotation_axis_actually_encodes_the_data` | **passed** ✗ |

The third was my bug. The assertion compared `qml.state()`, and `RZ(θ)|0>` versus `RZ(θ')|0>` differ by a
**global phase** — which the state vector carries but no measurement can observe. The test would have
passed even though a Z-axis encoding without its Hadamard discards the data entirely and trains on
nothing. Switched to `qml.density_matrix`, which quotients out global phase. The mutation now fails
correctly and the unmutated suite still passes.

Recorded because it is the backend twin of the QA campaign's H-4/H-6 lesson: an assertion that cannot fail
is worse than no assertion, because it reports success.

---

## 5. Dependencies: nothing added

`requirements.txt` is **unchanged**. No torch (Phase 0 proved the no-torch path at 2.22e-16) and no
scikit-learn, per §1A.

What that obliged, and how each obligation was met:

| §1A obligation | Evidence |
|---|---|
| Datasets verified, not assumed | shape, class balance, bit-for-bit reproduction under seed; `circles` proven separable by radius; `moons` proven **not** separable by any single-feature threshold (best < 0.95) yet genuinely two-clustered |
| Scaler leakage is my responsibility | `test_scaler_statistics_come_from_the_train_split_only` asserts the fitted min/max equal the **train split's** and explicitly **differ from the full dataset's**; mutation-proven to fail when leaked |
| Baseline must be a real trained model | L-BFGS-B logistic regression via `scipy.optimize.minimize` on the analytic gradient; asserted ≥ 0.95 on separable blobs, coefficient shift > 0.5 from initialisation, both classes predicted, and **< 0.98 on moons** so the comparison stays informative |
| Metrics hand-computed | a fixed 10-sample vector with TN/FP/FN/TP = 2/2/2/4 worked out in the test file's comments; accuracy 0.6, precision = recall = F1 = 4/6, plus an asymmetric case separating precision from recall |

### 5.1 One addition that needs sign-off: the bundled Iris file

`iris_binary` needs real Iris measurements. Transcribing 150 rows from memory would have risked
fabricated data, so I extracted `sklearn/datasets/data/iris.csv` from the scikit-learn **wheel downloaded
to `/tmp`** and vendored it at `backend/app/quantum/qml_lab/data/iris.csv` (2,734 bytes, sha256
`f13ffa8f…d1449`, 150 rows × 4 features × 3 classes).

- **scikit-learn was never installed.** Verified after the download: `import sklearn` →
  `ModuleNotFoundError`. `pip download` was used, not `pip install`; the venv and `requirements.txt` are
  untouched.
- Fisher's Iris (1936) is public-domain reference data, not code.
- A test pins the file's sha256, so truncation or an accidental edit fails loudly.

If vendoring a data file is unwelcome, the alternative is to drop `iris_binary` and offer a third synthetic
generator instead — say the word and it is a small change.

---

## 6. Design decisions worth reviewing

- **Loud failure over silent clamping.** `iris_binary` has 100 usable rows; asking for more raises
  `QmlDatasetError` rather than quietly returning 100. `DATASET_MAX_SAMPLES` exposes the ceiling so
  Phase 2's `/describe` can bound the UI.
- **`extra="forbid"` everywhere**, with a test that pins the Noise Lab contrast so the rationale cannot
  quietly become folklore: that test asserts the Noise Lab *still* silently accepts a flat payload, and
  will fail if it is ever tightened. It is read-only and changes nothing there.
- **Cancellation checks run before each batch and again at each epoch boundary**, so a cancel arriving
  during an epoch's last batch does not start another epoch. `QmlCancelledError` never escapes `train()`;
  a cancelled run is an outcome carrying partial history, not a failure.
- **Two rotations per qubit per layer** (`RY`, `RZ`). A single-axis ansatz cannot move a point anywhere on
  the Bloch sphere and is a common reason a QNN plateaus at chance.
- **Path safety by construction.** The experiment id must parse as a non-negative int or a UUID before it
  becomes a path component, and the resolved directory is re-checked to be inside the root. 14 hostile ids
  are tested, including `../../etc/passwd`, absolute paths, `True`, `None` and `"3; rm -rf /"`.
- **Limits enforced as a pure function** so Phase 2's worker can re-check a config that was queued under
  looser limits. A test uses `model_construct` to bypass the schema and proves `enforce` still catches it.

---

## 7. New decisions — to fold into `DECISIONS.md` at the port

**D-013 — Squared error on ±1 targets, not log-loss.** A measured expectation value saturates at exactly
±1, where the log-loss gradient is `1/ε`; measured 199.96 and a model that predicted one class for
everything. Squared error has bounded gradients over the full range of a measurement. (§4.2)

**D-014 — No scikit-learn; datasets, scaler and baseline hand-written on numpy/scipy.** Binding per §1A.
The verification burden this creates is discharged as tabulated in §5. (§5)

**D-015 — Vendor the public-domain Iris CSV rather than transcribe or depend.** Extracted from a wheel
downloaded to `/tmp`; scikit-learn never installed; sha256 pinned by a test. Needs sign-off. (§5.1)

**D-016 — `qml.grad(argnums=…)`, never `argnum=…`.** The singular spelling is deprecated in PennyLane
0.44 and warns on every call. The only remaining warning in the engine is the import-time numpy one, which
cannot be fixed without moving a pin §1.3 protects. (§4.1)

---

## 8. Limits of this phase

Stated plainly rather than glossed:

1. **Nothing is wired up.** No route, no task, no table, no UI. The engine is unreachable from the running
   application, which is the intended Phase 1 end state.
2. **Per-task Celery limits remain unproven**, on Linux and on Windows alike — Phase 2's work.
3. **Timings are indicative, not benchmarks.** 15 epochs × 120 samples on 2 qubits took ~17 s with
   backprop; parameter-shift costs `1 + 2·n_parameters` executions per sample and was not timed at scale.
   Phase 4 measures this properly and tunes the timeout from the data.
4. **No noise, no density-matrix path.** `DENSITY_MATRIX_MAX_QUBITS = 6` is defined as a single source of
   truth but is unused and unvalidated in Phase 1 (D-009 remains provisional).
5. **Accuracy figures are from one seed.** They demonstrate learning; they are not a claim about typical
   performance across seeds.

---

## 9. Next — Phase 2

API, Celery task, persistence table and the feature flag: create/status/cancel/results/list/describe/
inference; `run_hash` duplicate-submission guard copied from `api/jobs.py:150-166`; per-task time limits on
the QML decorator only, proven in **both** directions; limits re-validated inside the worker; the additive
migration pre-authorised by §1.6 with a `downgrade()` that is actually run; `qml_enabled = False` gating
the router.

Open question for the senior, raised now rather than at the gate: **the migration shape and the per-task
limit mechanism** — if you want to settle those before I start, that removes the only two places Phase 2
would otherwise have to stop and ask.
