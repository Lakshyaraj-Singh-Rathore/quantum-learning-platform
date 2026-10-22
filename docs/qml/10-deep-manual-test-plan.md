# 10 — Deep manual test plan: the QML Lab and its QNN

**Audience: the project owner.** Complements `09-owner-runbook.md`, which covers
the three registered MT rows that block release. This document goes deeper: it
tests the *engine*, the *contract*, and the one algorithm that has never been
driven through the live stack.

Work through it in order. Parts 1–3 need no Docker. Parts 4–7 need the stack.

Each test has an ID (`DT-nn`) so results can be recorded the way MT rows are.
**A test you did not run does not count as passed** — record `NOT RUN` rather
than leaving a blank.

---

## Part 0 — what you are testing, in one page

The QML Lab trains **real quantum circuits** on **real gradients**. There are no
mocked qnodes anywhere in the path.

**Four algorithms** (`limits.py:110-115`, `TASK_BY_ALGORITHM`):

| Algorithm | Task | What it is |
|---|---|---|
| `vqc` | classification | A pure variational quantum classifier. Angle-encode features → variational ansatz → measure `⟨Z⟩` on wire 0. The class probability is `(1 + ⟨Z⟩ + bias)/2`. **The measurement is the prediction**; nothing fabricates a score from parameters. |
| **`hybrid_qnn`** | classification | **The QNN.** See below. |
| `quantum_kernel` | classification | Estimates a kernel matrix on the quantum device, then trains an LSSVM **classically in closed form**. It has **no epoch loop** — `has_epoch_loop()` is false — so it writes no epoch rows. |
| `quantum_regression` | regression | Variational circuit predicting a continuous target. Reports **MAE, RMSE and a signed R²**, never a classifier metric. |

**Six datasets** (`limits.py:115-116`): classification `moons`, `circles`,
`iris_binary`; regression `sine`, `damped_cosine`, `linear_mix`.

**How the QNN works** (`hybrid.py`):

A classical layer learns *what to feed the circuit*. Raw features pass through
one trainable affine map and a `tanh`; the result is rescaled into the encoder's
`[0, π]` window so the classical block can never emit an angle the encoder would
silently wrap; only then is it angle-encoded and pushed through **the same
variational ansatz the pure VQC uses**.

The decisive design point: **the classical weights and the circuit weights live
in one flat parameter vector and are updated by the same optimiser step.**

```
[ W1 : n_features × n_hidden ][ b1 : n_hidden ][ circuit : 2·n_qubits·n_layers ][ bias : 1 ]
```

So the classical layer is genuinely learning a representation *for* the quantum
model — it is not a fixed preprocessor. The ordering matters because
`persistence.py` stores the vector verbatim and `HybridParameters` is the only
thing that knows how to read it.

**There is no PyTorch** (D-031). `autograd` is already a PennyLane dependency and
`interface="autograd"` differentiates straight through the QNode into the
classical weights. `qml.qnn.TorchLayer` is the only thing torch would add, and it
is a wrapper around exactly this.

**Two differentiation methods**, both exact on a state-vector simulator
(`models.py:34`, `DiffMethod = Literal["backprop", "parameter-shift"]`):
`backprop` differentiates through the simulation and is the default, because
`parameter-shift` costs `1 + 2·n_parameters` circuit executions per gradient
step. Phase 4 measured the consequence: **backprop is linear in circuit size,
parameter-shift is quadratic** — 0.136→0.684 s versus 0.456→5.65 s across
q=2→8.

---

## Part 1 — the automated baseline (10 minutes, no Docker)

Run these first. If any fails, stop — everything below assumes a green baseline.

```powershell
cd C:\Users\laksh\quantum-learning-platform\backend
.\.venv-bench\Scripts\Activate.ps1
$env:PYTHONPATH = "."
pytest -q
```

**Want: 1304 passed, 5 skipped.** Record the actual number.

Then the QML subset alone:

```powershell
cd C:\Users\laksh\quantum-learning-platform\backend
$env:PYTHONPATH = "."
pytest -q tests/ -k "qml"
```

**Want: ~405 passed across 19 files.**

| ID | Test | Expected |
|---|---|---|
| DT-01 | full `pytest -q` | 1304 passed / 5 skipped |
| DT-02 | `pytest -k qml` | ~405 passed, 19 files |

---

## Part 2 — is training *real*? The engine-level proofs (15 minutes)

These are the tests that separate a genuine quantum trainer from something that
looks like one. Run each individually and **read the output**, do not just check
the exit code.

### DT-03 — the two gradient methods agree to 1e-9

```powershell
cd C:\Users\laksh\quantum-learning-platform\backend
$env:PYTHONPATH = "."
pytest -q tests/test_qml_gradients.py -v
```

`backprop` and `parameter-shift` are computed by completely different machinery.
If they agree to 1e-9 the gradients are exact, not approximated. **This is the
single strongest piece of evidence that the training is real.**

### DT-04 — the QNN's classical gradient matches a finite difference

```powershell
cd C:\Users\laksh\quantum-learning-platform\backend
$env:PYTHONPATH = "."
pytest -q tests/test_qml_hybrid.py::test_classical_gradient_matches_finite_differences -v
```

Compares the autograd gradient of the **classical block** against a central
finite difference taken **through the real circuit**. This is what proves the
no-PyTorch decision did not cost correctness — the classical layer receives a
true gradient from the quantum model, not a detached or approximated one.

### DT-05 — training moves BOTH blocks of the QNN

```powershell
cd C:\Users\laksh\quantum-learning-platform\backend
$env:PYTHONPATH = "."
pytest -q tests/test_qml_hybrid.py::test_training_moves_both_blocks_and_improves_the_loss -v
```

The failure mode this catches: a "hybrid" model where the classical layer is
frozen and only the circuit trains — which would make it a VQC with extra steps.
**Both blocks must move, and the loss must improve.**

### DT-06 — all four algorithms complete and report their own task

```powershell
cd C:\Users\laksh\quantum-learning-platform\backend
$env:PYTHONPATH = "."
pytest -q tests/test_qml_dispatch.py::test_every_algorithm_completes_and_reports_its_own_task -v
```

Parametrised over all four. Each must reach `status == "completed"` and report
the metrics of **its own** task — the regression algorithm must not report
accuracy, the classifiers must not report R².

### DT-07 — the whole hybrid suite

```powershell
cd C:\Users\laksh\quantum-learning-platform\backend
$env:PYTHONPATH = "."
pytest -q tests/test_qml_hybrid.py -v
```

**27 tests.** Read the names — each one is a specific way a hybrid model could be
fake, closed off: the parameter vector ordering, that `HybridParameters` is
deliberately *not* a `vqc.Parameters` subclass, that the classical output stays
inside the encoder window, that the classical layer actually depends on its
weights, that predictions come from the measurement, that `n_hidden` above
`n_qubits` is rejected, that `n_hidden` on a non-hybrid algorithm is rejected.

### DT-08 — the cost estimator matches a real training run

```powershell
cd C:\Users\laksh\quantum-learning-platform\backend
$env:PYTHONPATH = "."
pytest -q tests/ -k "estimate_cost" -v
```

`test_estimate_cost_matches_a_real_training_run` pins `estimate_cost` against
`qml.Tracker` on an actual run. This is the test that caught **D-028** — the
estimator charging one evaluation pass when the trainer evaluates both splits
every epoch, short by exactly `(epochs − 1) · n_samples`.

| ID | Test | Expected |
|---|---|---|
| DT-03 | `test_qml_gradients.py` | backprop ≡ parameter-shift at 1e-9 |
| DT-04 | classical gradient vs finite difference | match |
| DT-05 | training moves both blocks | both move, loss improves |
| DT-06 | every algorithm completes | 4/4 `completed`, own task's metrics |
| DT-07 | `test_qml_hybrid.py` | 27 passed |
| DT-08 | cost estimator vs `qml.Tracker` | match |

---

## Part 3 — the contract, without a browser (10 minutes)

> **About the URLs.** The FastAPI routes are mounted at the **root** —
> `api_router = APIRouter()` carries no prefix (`router.py:20`) and
> `app.include_router(api_router)` adds none (`main.py:75`), so the real path is
> **`/qml/describe`**. The *browser* calls **`/api/qml/describe`**, because the
> proxy strips `/api` before forwarding (`vite.config.ts:20-22`, `:53-56`; nginx
> does the same in compose) — that is what keeps the SPA same-origin so CORS
> never enters the picture.
>
> **So: `curl` against `localhost:8000` uses `/qml/…`; devtools in the browser
> will show `/api/qml/…`. Both are correct.** If a curl 404s, check this first.

Start only the API (no worker needed for `/describe`):

```powershell
cd C:\Users\laksh\quantum-learning-platform
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d api
```

### DT-09 — flag OFF means the routes do not exist

```powershell
cd C:\Users\laksh\quantum-learning-platform
curl.exe -s -o NUL -w "%{http_code}" http://localhost:8000/qml/describe
curl.exe -s http://localhost:8000/features
```

**Want `404`, then `{"qml_enabled":false}`.** `/features` is *always* mounted
(`router.py:22-24`) — it returns `false` when off, it does not 404. That
asymmetry is deliberate: the browser must always be able to ask.

### DT-10 — flag ON, unauthenticated, means 401 not 404

Turn the flag on and restart:

```powershell
cd C:\Users\laksh\quantum-learning-platform
Add-Content .env "`nQML_ENABLED=true"
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d api
curl.exe -s -o NUL -w "%{http_code}" http://localhost:8000/qml/describe
```

**Want `401`.** The distinction between 404-when-off and 401-when-on is what
stops the flag from leaking the feature's existence.

### DT-11 — `/describe` advertises only what the API will accept

Authenticated, read the payload:

```powershell
cd C:\Users\laksh\quantum-learning-platform
curl.exe -s -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/qml/describe > artifacts\describe.json
python -c "import json;d=json.load(open('artifacts/describe.json'));[print(a['name'],a['task'],a['limits'],a['supports']) for a in d['algorithms']]"
```

**Check all four algorithms appear**, each with `limits`, `datasets[]`,
`metrics[]`, `epoch_fields[]`, `supports{n_hidden, epochs, diff_method,
data_reuploading}` and `baseline`.

**This is a known defect class in this project**: a capability endpoint once
advertised something the API then rejected. So pick one advertised limit and
**deliberately violate it** — request `n_qubits: 9` against `MAX_QUBITS = 8` —
and confirm the API rejects it with a legible error rather than accepting and
failing later.

```powershell
cd C:\Users\laksh\quantum-learning-platform
curl.exe -s -X POST -H "Authorization: Bearer YOUR_TOKEN" -H "Content-Type: application/json" -d "{\"algorithm\":\"vqc\",\"dataset\":{\"name\":\"moons\",\"n_samples\":60},\"circuit\":{\"n_qubits\":9,\"n_layers\":2},\"training\":{\"epochs\":2,\"batch_size\":16,\"learning_rate\":0.1}}" http://localhost:8000/qml/experiments
```

**Want a 4xx naming `n_qubits` and the limit of 8.** Not a 500, not a 201.

| ID | Test | Expected |
|---|---|---|
| DT-09 | flag off | `describe` → **404**, `/features` → `{"qml_enabled":false}` |
| DT-10 | flag on, no auth | **401** |
| DT-11 | `/describe` vs enforcement | 4 algorithms; `n_qubits: 9` rejected with a legible 4xx |

---

## Part 4 — the live stack, all four algorithms (45 minutes)

**This is the most important part, and it closes a real gap.**

Bring up the whole stack including the worker:

```powershell
cd C:\Users\laksh\quantum-learning-platform
docker compose -f docker-compose.yml -f docker-compose.gpu.yml --profile qml up -d --build
docker compose -f docker-compose.yml -f docker-compose.gpu.yml --profile qml ps
```

**`qml-worker` must be listed and running.** Enabling the Lab is two independent
actions — flag *and* profile — and doing only one gives a UI that works while
every run silently fails.

Then, in the browser, sign in and open **Quantum ML Lab**. Run each of these to
completion and record what you see.

### DT-12 — `vqc` on `moons` *(already automated; confirm by eye)*

Config: **4 qubits, 2 layers, 200 samples, 20 epochs, `backprop`**.

**Want:** status reaches `completed`; the progress view updates **per epoch**; the
loss curve **descends**; accuracy is **above the baseline floor** shown beside it;
the confusion matrix's **four cells sum to the test-split size**.

### DT-13 — **`hybrid_qnn` on `moons` — NEVER RUN IN A BROWSER BEFORE**

> **This is the gap.** The QNN is proven at engine level by 27 unit tests and by
> the dispatch test, but the browser fixtures Phase 8C/8D created were a
> **classifier, a regression and a kernel** — the browser harnesses contain no
> algorithm name at all and use whatever the API defaults to. **`hybrid_qnn` has
> therefore never been driven through the live API, worker and UI.**

Config: **`hybrid_qnn`, `moons`, 4 qubits, 2 layers, `n_hidden` 3, 200 samples,
20 epochs, `backprop`**.

Check, in this order:

1. **`n_hidden` appears in the form only for this algorithm.** Switch to `vqc` —
   it must disappear. `supports.n_hidden` is false for the other three, and
   `test_n_hidden_on_a_non_hybrid_algorithm_is_rejected` pins the backend half.
2. **`n_hidden` cannot exceed `n_qubits`.** Try `n_hidden` 5 with 4 qubits — the
   form or the API must refuse. (`test_n_hidden_above_n_qubits_is_rejected_by_the_schema`.)
3. **It reaches `completed`** and produces epoch rows like the VQC.
4. **Compare its accuracy to DT-12's VQC on the same dataset and seed.** The QNN
   should be at least competitive. **If the hybrid is materially worse than the
   pure VQC, that is a finding** — it would suggest the classical block is
   hurting rather than helping, which the unit tests cannot see because they
   check that it *moves*, not that it *helps*.
5. **Run inference from the saved model** and confirm a class with a probability
   in `[0, 1]`.

Record the accuracy, and whether the parameter count reported matches
`n_features × n_hidden + n_hidden + 2·n_qubits·n_layers + 1`.

### DT-14 — `hybrid_qnn` with `parameter-shift`

Same config, but `diff_method` = **`parameter-shift`**.

**Want:** it completes, and the result is **close to DT-13's** but not identical.
**Expect it to be visibly slower** — Phase 4 measured parameter-shift as
quadratic against backprop's linear. This is the user-facing consequence of the
`1 + 2·n_parameters` cost, and seeing it once is worth more than reading the
number.

### DT-15 — `quantum_regression` on `sine`

Config: **4 qubits, 2 layers, 200 samples, 20 epochs**.

**Want:** **MAE and RMSE in target units**, and **R² with its sign**. Then the
negative case — this is the one that matters:

- **No accuracy, F1, precision, recall or confusion matrix anywhere on the page.**
- Switch the dataset to `damped_cosine` and `linear_mix`. If any produces a
  **negative R²**, confirm it is displayed **as negative** and described as
  *worse than predicting the mean*. History carries real negatives
  (**−2.060 / −0.844 / −0.161**), and Phase 8C asserted a fixture at
  **−3.804**. A renderer that clamps, hides or `abs()`es a negative R² tells the
  reader the **opposite of the truth**.

### DT-16 — `quantum_kernel` on `moons`

Config: **4 qubits, 200 samples**.

**Want:** it completes **with no epoch rows** — the kernel solves an LSSVM in
**closed form**, so there is no epoch loop (`has_epoch_loop()` is false). The UI
must show the **closed-form outcome, not an empty chart or a spinner that never
resolves.** Then check the **heatmap renders with real colours** — Phase 8C proved
400/400 cells carry computed inline `background-color`, because the defect class
being guarded is `bg-card`: a class name that emits no CSS at all.

### DT-17 — the sample cap (QL-019, fixed in Phase 8D)

Select **`iris_binary`** (cap **100**) from a form sitting at **200 samples**.

**Want all four:**
1. the input's `max` becomes **100**, not a stale 1000
2. `checkValidity()` reports invalid — in practice: the form will not submit
3. the hint reads **`20–100`**, not `20–1000`
4. a **legible error names the cap**

Before Phase 8D, `max` stayed stale at 1000 so `checkValidity()` returned **true**
on an over-cap value, and the only thing preventing a rejected run was a Train
button that was disabled **without saying why**. (The button was in fact disabled
by a *different* check — `tooFewQubits`, since iris has 4 features — so the UI was
explaining the wrong thing.)

### DT-18 — cancel mid-run

Submit a **larger** experiment (6 qubits, 4 layers, 500 samples, 40 epochs) and
press **Cancel** partway through.

**Want:** status reaches **`cancelled` within one batch**, and **never `failed`**.

This exercises the cooperative `deadline_seconds`, which sits strictly below the
soft limit because Celery's `SIGALRM` revocation is absent on Windows and
`time_limit` kills a prefork child that `--pool=solo` does not have. **If cancel
lands as `failed`, the cooperative mechanism does not work on your platform** — a
real finding, not a flake.

### DT-19 — polling actually stops

Leave a completed experiment open with devtools Network tab filtered to `XHR`.

**Want:** requests occur while running, then **stop** after the terminal status.
Phase 8C had to fix its own assertion here: *"0 polling requests after terminal"*
is indistinguishable from *a run that never started*. Confirm you saw polling
happen **and then cease**.

| ID | Test | Expected |
|---|---|---|
| DT-12 | `vqc` / `moons` | completed, loss descends, accuracy above baseline floor |
| **DT-13** | **`hybrid_qnn` / `moons`** | **completed, `n_hidden` gated to this algorithm only, competitive with DT-12** |
| DT-14 | `hybrid_qnn` + parameter-shift | completed, close to DT-13, visibly slower |
| DT-15 | `quantum_regression` / `sine` | MAE+RMSE in units, **signed R²**, zero classifier metrics |
| DT-16 | `quantum_kernel` / `moons` | completed, **no epoch rows**, closed-form shown, heatmap painted |
| DT-17 | sample cap | `max`→100, invalid, hint `20–100`, legible error |
| DT-18 | cancel mid-run | `cancelled`, never `failed` |
| DT-19 | polling | observed to happen, then stop |

---

## Part 5 — adversarial and negative tests (20 minutes)

A feature that only works on the happy path is not finished. Each of these should
produce a **legible** failure, never a blank page, a spinner or a 500.

| ID | Do this | Want |
|---|---|---|
| DT-20 | `n_qubits` 9 (max 8) | rejected, error names the limit |
| DT-21 | `n_layers` 5 (max 4) | rejected, error names the limit |
| DT-22 | `n_samples` 1001 (max 1000) | rejected |
| DT-23 | `epochs` 101 (max 100) | rejected |
| DT-24 | `batch_size` 33 (max 32) | rejected |
| DT-25 | a **regression** dataset with a **classifier** algorithm | rejected — `TASK_BY_DATASET` must not be bypassable |
| DT-26 | `n_hidden` on `vqc` | rejected — hybrid-only field |
| DT-27 | Submit with the **worker stopped** (`docker compose … stop qml-worker`) | `201 Created`, then **`failed`** with *"Could not enqueue experiment"* — **not** a hung `pending`. This is the half-enabled state; confirm it is loud rather than silent. |
| DT-28 | Navigate to `/qml-lab` with the **flag off** | the **404 body**, and **no nav entry** |
| DT-29 | Kill the API while the Lab is open, then reload | the nav entry **disappears** and `/qml-lab` shows 404 — it **fails closed**. Phase 8A replaced a regex-over-source guard with a rendered assertion for exactly this. |
| DT-30 | Two experiments at once | concurrency is **global**, not per user (§2A.5) — the second should queue or be refused with an explanation |

---

## Part 6 — the benchmark (MT-004, 10–40 minutes)

**See `09-owner-runbook.md`, MT-004.** This is the only source of the numbers
behind `qml_task_soft_time_limit = 900` / `hard = 1200`, and it must run natively
on Windows, not in Docker — it is measuring *your* CPU.

The short version, with the step most often skipped:

```powershell
cd C:\Users\laksh\quantum-learning-platform\backend
.\.venv-bench\Scripts\Activate.ps1
pip install psutil
$env:PYTHONPATH = "."
python scripts\bench_qml.py --quick
python scripts\bench_qml.py --full --json ..\artifacts\bench-full.json --md ..\artifacts\bench-full.md
```

`psutil` is **not** optional: `total_ram_gib()` reads `/proc/meminfo`, absent on
Windows, and falls back to `psutil`, which is deliberately not in
`requirements.txt`. Without it the run completes and records `total_ram_gib:
null` — a hole in the only report that can fill it.

| ID | Check | Want |
|---|---|---|
| DT-31 | `execution_law_verified` | **`true`** — if false, that is a finding, not a flake |
| DT-32 | `total_ram_gib` | **not null** |
| DT-33 | `projections` for `8q/4L/B32/backprop/default.qubit` | `projected_seconds` **under 900**. Over 1200 ⇒ stop and escalate |

---

## Part 7 — the AI explanation (MT-010, 15 minutes)

**See `09-owner-runbook.md`, MT-010.** Needs `GEMINI_API_KEY` set *and*
`google-generativeai` importable — `is_configured()` (`gemini_client.py:88`)
requires both, so a key with no SDK looks identical to a missing key.

| ID | Check | Want |
|---|---|---|
| DT-34 | Press **Explain** on a `vqc` result | prose in ~10 s, 2–3 short paragraphs, **no markdown headings** |
| DT-35 | **Every number in the prose appears in the "Measured" table beneath it** | **any figure not in that table is a confabulation and the test fails** — this is the whole point of the grounded builder and the check that cannot be faked |
| DT-36 | Press **Explain** on a `quantum_regression` result | mentions **no** accuracy, precision, recall, F1 or confusion matrix |
| DT-37 | Classification explanation | mentions **no** R², MAE or RMSE |
| DT-38 | Explain a **negative R²** run | described as **worse than predicting the mean**, not as a small positive score |
| DT-39 | Read the whole explanation | **no claim of quantum advantage** |
| DT-40 | `Select-String -Path artifacts\mt-010.log -Pattern "AIza\|GEMINI_API_KEY"` | **zero matches** — a leak outranks every other result here |

---

## Recording

| ID | Result | Notes |
|---|---|---|
| DT-01 … DT-40 | `PASS` / `FAIL` / `NOT RUN` | |

**Anything that fails goes in `docs/qml/DECISIONS.md` or the defect ledger with a
QL-nnn ID, not in a chat message.** A defect that is only reported verbally does
not exist six weeks later — this project has a register precisely because it does.

## Known gaps this plan does not close

- **MT-005** — the GPU/CUDA-Q path. A declared non-goal (D-030).
- **MT-007** — the data-reuploading frequency budget for a human-chosen
  configuration. Covered by none of the three blocking MT rows, and not covered
  here either. It needs a `data_reuploading` run configured deliberately.
- **A real prefork pool and signal-based time limits.** DT-18 exercises the
  cooperative deadline under `--pool=solo`, which is what Windows gives you. The
  signal path Celery would use on Linux is still unexercised.
- **`render:p5`'s 19 failures** remain — Radix portals that SSR never renders.
  That needs the harness moved into a browser, which is code work, not manual
  testing.
