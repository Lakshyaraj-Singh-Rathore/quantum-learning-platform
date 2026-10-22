# Phase 5 — algorithms: hybrid, regression, kernel

Branch `arena/63ae45b4-quantum-learning-platform`, from `main @ 6138cb3` (590 tracked files).

Stopped at the **second** of the two stopping points §2C.8 names — after the kernel. Noise
(§2C.5) and the qudit spike (§2C.6) are named deferrals in **D-038**, not silences.

---

## 1. Gates

| Gate | Target | Result |
|---|---|---|
| `cd backend; PYTHONPATH=. pytest -q` | 1034/5 + new | **1145 passed / 5 skipped** in 274.0 s (**+111**) |
| `npm run typecheck` | 0 | **0** |
| `npm run build` | PASS | **PASS**, 6.63 s |
| `npm run golden:quantum` | 190 @1e-9 | **190** |
| `npm run golden:demos` | 804 @1e-9 | **804** |
| `npm run golden:grover` | 3306 @1e-9 | **3306** |
| `npm run a11y` | 0 criticals | **0 criticals** |
| harness FAIL 57 = 9+20+20+8 | unchanged | **unchanged by construction** — see below |
| CSS rule-level diff | 12 added / 0 changed / 0 removed | **unchanged by construction** — see below |

`qml:circuit` 49 assertions across 7 circuits · `qml:ui` 58 contract guards over 12 sources ·
`qml:render` 34 PASS, all flag states · `render:check`, `states`, `curriculum` (29) all pass.

**On the last two rows, stated honestly.** `git diff --name-only origin/main -- frontend/`
returns **0 files**. No `.mts`, no `package.json`, no CSS was touched this phase, so the harness
FAIL decomposition and the CSS rule diff cannot have moved. I did not re-derive the
`9+20+20+8` split from a measurement — running the harnesses gives assertion counts
(49 / 58 / 34) that do not decompose that way, so rather than invent a matching number I am
reporting the stronger fact: **the inputs to that gate are byte-identical to `main`.**

---

## 2. Tracked files: 590 → **598** (+8, 0 deleted)

| | Path |
|---|---|
| A | `backend/app/quantum/qml_lab/hybrid.py` |
| A | `backend/app/quantum/qml_lab/kernel.py` |
| A | `backend/app/quantum/qml_lab/regression.py` |
| A | `backend/app/quantum/qml_lab/regression_data.py` |
| A | `backend/tests/test_qml_hybrid.py` |
| A | `backend/tests/test_qml_kernel.py` |
| A | `backend/tests/test_qml_regression.py` |
| A | `docs/qml/MANUAL_TEST_REGISTER.md` |

Modified (7): `errors.py` · `limits.py` · `models.py` · `services/qml_lab.py` ·
`tests/test_qml_config.py` · `docs/qml/04-benchmarks.md` · `docs/qml/DECISIONS.md`.
(This report adds a 9th file, `docs/qml/phase-5-report.md`.)

---

## 3. §8A split — **111 automated, 4 newly deferred**

Automated: +111 backend tests (`pytest`), being 27 hybrid, 51 regression, 31 kernel, 2 D-028.
Deferred: **MT-006, MT-007, MT-008, MT-009**. The register now holds **9** rows, append-only.
MT-006 (regression must never render an accuracy field) is flagged **blocks release**; the
other three do not.

---

## 4. What was built, and the three things that changed the design

### 4.1 Hybrid QNN on `autograd` (§2C.2, D-031)

`x → W₁,b₁ affine → tanh → (h+1)·π/2 ∈ [0,π] → angle-encode → ansatz → <Z₀> + bias`. Trains
through the **unmodified** trainer, which is duck-typed on `decision_values`.

The no-torch premise was **proved, not assumed**: max |autograd − central finite difference|
over all 9 classical parameters is **2.316e-10**, and backprop agrees with parameter-shift to
1e-9 *with the classical layer in the path*. PyTorch would have been 24 packages including a
CUDA toolkit for one of four algorithms.

### 4.2 Regression with its own types (§2C.4, D-033) — and a capacity bug found by measuring

Separate `RegressionResult` / `RegressionEpochRecord`; a test asserts they have **no**
`accuracy`/`precision`/`recall`/`f1`/`confusion_matrix` attribute at all, so a UI cannot read a
zeroed accuracy off the payload — it would have to invent one.

**The first run looked like a weak model and was actually an impossible task.** `sin(2x)` fit at
**R² = +0.104**, losing to a linear ridge baseline at +0.208 — the wrong *shape* of result for a
non-linear target, so I diagnosed instead of tuning. Sweeping the encoded angle and taking an
FFT of `<Z₀>` showed the accessible spectrum is **{0, ±1}**: frequency-2 power was **1e-5**,
i.e. numerical noise. The target was **structurally unrepresentable**, not under-trained.

Data re-uploading is now the default. Frequency-2 power rises **0.00098 → 0.02144 (22×)** and
`sine` goes **+0.104 → +0.328**, beating the baseline.

A second consequence fell out of the same analysis and is the more dangerous one: the feature
scaler maps `[-π, π]` onto `[0, π]`, so `x = 2a − π` and **every frequency doubles**. The
drafted `cos(3x)` target therefore needed angle-frequency **6** against `MAX_LAYERS = 4` — it
was unreachable at *every configuration the schema permits* and would have shipped as a dataset
that trains to a flat line and reads as a broken model. Datasets were retargeted, and
`test_every_regression_dataset_is_inside_the_frequency_budget` now **fails the build** if one
ever exceeds the budget. (D-034.)

### 4.3 Kernel as LSSVM (§2C.3, D-036)

One `numpy.linalg.solve`, no QP solver, no new dependency; labelled **LSSVM** wherever
surfaced, with `n_support` reporting the lost sparsity. 91.7% test accuracy on moons.

Only the **strict** upper triangle is evaluated, and a test *counts QNode calls* rather than
trusting the claim. This corrected D-032's arithmetic: it priced the 250-sample cap at 31,375,
which is `n(n+1)/2` and includes the diagonal — but the diagonal is `|<φ(x)|φ(x)>|² = 1`
*exactly*, by construction, so it is written rather than computed. The real figure is
**31,125** against 62,500 naive.

### 4.4 `/qml/describe` now drives the config view (§2C.7)

Per-algorithm limits, task-appropriate datasets, the metric list, the epoch-chart series and a
`supports` map — additive, with a test pinning every pre-existing key so the Phase 3 UI cannot
break. Serving the metric list is the server-side half of MT-006.

---

## 5. Defects found in my own work, and fixed at the root

Four, all silent, three of them already committed in earlier Phase 5 commits:

1. **`limits.py` raised `QmlConfigError` while importing only `QmlLimitExceededError`.** The
   edit reported success; the defect was invisible until something executed it.
2. **`limits_for()` froze `LIMITS` at import**, so `monkeypatch.setattr(limits, "MAX_QUBITS", 1)`
   stopped reaching `check()` — disabling the exact property the worker's second enforcement
   pass exists for. The failing test was right and was not weakened.
3. **The same defect recurred in `ALGORITHM_LIMITS`** one commit later, because fix 2 addressed
   the symptom rather than both snapshots. The kernel cap could not be monkeypatched: a ceiling
   test would pass while silently exercising the real 250. Both now live-read. (D-037.)
4. **`QmlLimitExceededError` shredded a single string into characters.** Its signature is
   `list[str]` and it joins with `"; "`; a bare string is a valid iterable of characters, so
   one message rendered as `t; o; o;  ; b; i; g` in the API response. Nothing enforced the hint
   and nothing failed. (D-037.)

**And one overstated guarantee, corrected.** A test named
`..._shape_is_identical_across_algorithms` asserted only a *subset* relation, and D-032 repeated
the claim in prose — but `hybrid_qnn` genuinely carries an extra `n_hidden` key. A reader would
have taken a guarantee the code does not make. The test is renamed to what it checks and split
in two; the real guarantee (no algorithm drops a key, every entry is exactly
`{default, min, max}`, any extra key is declared and must agree with its `supports` flag) is now
what is asserted and what D-032 says.

---

## 6. Mutation campaigns — 24 mutants, 2 survivors, both closed

| Module | Mutants | Survived |
|---|---|---|
| `hybrid.py` | 5 | **H3** — delete the output bias |
| `regression.py` / `regression_data.py` | 9 | none |
| `services/qml_lab.py` (describe) | 5 | none |
| `kernel.py` | 10 | **K7** — delete the LSSVM bias |

**Both survivors are the same blindness, and it recurred after I had already seen it once.** A
parameter that is zero in the test fixture is invisible. H3: the hybrid's output bias
initialises to `0.0`, and the prediction test compared `predict()` against the same
`decision_values()` it derives from — self-consistent and therefore blind. K7: the obvious LSSVM
fixture is balanced ±1 labels on an identity Gram, whose bias is **exactly 0.0** by symmetry.

Each is closed by forcing the parameter non-zero and asserting the **exact** downstream shift,
and each mutant was re-run against the new test to confirm the kill. Both files verified
byte-identical after the campaigns.

One further process note: a mutation script of mine failed with a quoting `SyntaxError`, so the
file was never mutated and the run reported "51 passed". That is a **void mutant, not a
survivor**, and it was re-run properly rather than counted. Mutants now assert their target
string is present before writing.

---

## 7. Unchanged and still not verified

No target-machine numbers. No through-the-API measurement. No Redis/Celery worker (a real POST
still returns 201 then `failed` with `Error -2 connecting to redis:6379`). No docker, so
`qml-worker` is inspection-verified only. No screenshots, no GPU, no density-matrix path.
**Nothing has ever crashed or been OOM-killed, so there are still no ceiling data points, only
timings.** Linux, not Windows/PowerShell.

`qml_task_soft_time_limit` remains **900/1200 and provisional**. The authorised parameter-shift
tightening is encoded as a per-algorithm ceiling plus the up-front `estimate_cost` fixed by
D-028, which is why D-028 had to land first.
