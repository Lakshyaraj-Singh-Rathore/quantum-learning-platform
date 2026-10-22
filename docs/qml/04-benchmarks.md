# Phase 4 — QML Lab benchmarks

**Status: provisional. The numbers in §3 were measured on a sandbox that is not the target
machine, and no limit has been changed on the strength of them.**

Every claim below names the command that produced it (§8). The measuring instrument is
`backend/scripts/bench_qml.py`, which imports the real engine — a benchmark of a
reimplementation measures the reimplementation.

---

## 1. How to run it

`artifacts/` is gitignored, which is where the raw output belongs.

POSIX:

```bash
cd backend
PYTHONPATH=. python scripts/bench_qml.py --quick --json ../artifacts/bench-quick.json --md ../artifacts/bench-quick.md
PYTHONPATH=. python scripts/bench_qml.py --full  --json ../artifacts/bench-full.json  --md ../artifacts/bench-full.md
```

Windows PowerShell 5 — `&&` is a parser error there (§6), so these are separate statements:

```powershell
cd backend
$env:PYTHONPATH = "."
python scripts\bench_qml.py --full --json ..\artifacts\bench-full.json --md ..\artifacts\bench-full.md
```

Flags: `--quick` (2–6 qubits, ~3 min) and `--full` (up to the allowed maxima, ~40 min on the
sandbox) are mutually exclusive; `--reps N` overrides the repetition count; `--reproject FILE`
recomputes the projections from a saved results JSON without re-measuring anything.

**It is not wired into the `Makefile`, deliberately.** Every existing Makefile target shells
into Docker Compose (`$(COMPOSE) exec api …`), so a `make bench` would measure the *container*,
which is precisely the machine §2B.1 says not to measure. `Makefile` is also absent from §4's
allowed-touch-points table, and the target OS is Windows, where `make` is usually not installed.
§2B.2 permits either wiring or an exact documented invocation; this is the documented invocation.

### Measurement discipline (§2B.6)

| Rule | How it is met |
|---|---|
| Engine-direct, not through the API | `make_gradient_step()` builds a `VQC` and calls `qml.grad` on the trainer's own `square_loss ∘ decision_values`. No FastAPI, no Celery, no DB. Recorded as `measured_through` in every artifact. |
| Warm-up discarded | `time_it()` runs the callable once untimed before the timed repetitions. |
| N reps with spread | Default `reps=5`; the JSON carries median, min, max and stdev per cell. |
| `shots=None` vs finite | `shots=None` (analytic) throughout; recorded in `environment.shots`. |
| Peak RSS | `resource.getrusage(RUSAGE_SELF).ru_maxrss` — **the benchmark process**, not the worker. |
| Never tune from a crashed run | A cell whose single untimed probe exceeds the budget is recorded `over-budget` with the probe time and its repetitions skipped; an unsupported device/method pair is recorded `unsupported`. Neither is used as a timing. |

Nothing was killed or OOMed in any run reported here, so there are no ceiling data points to
report — only timings.

---

## 2. The arithmetic, done before measuring (§2B.3)

With `P` the number of **circuit** parameters and `B` the batch size:

```
P = 2 · n_qubits · n_layers          limits.py:106-113 (RY+RZ per wire per layer)
```

The trainable bias is classical, lives outside the QNode, and costs no circuit evaluations.

| Gradient method | Executions per gradient step |
|---|---|
| `backprop` | `B` |
| `parameter-shift` | `B · (2P + 1)` |

Two corrections to the premise in §2B.3, both load-bearing:

1. **The ansatz is 2 parameters per qubit per layer, not 3.** At the maximum configuration
   `P = 2 · 8 · 4 = 64`, not 96.
2. **Batch size multiplies everything.** `vqc.py:99-102` is
   `[self.expectation(row, theta) for row in x]` — a Python loop with **no parameter
   broadcasting**. §2B.3's per-step figure omits this, so its ~600,000-execution estimate for a
   full run is low by more than an order of magnitude.

### Maximum allowed configuration

8 qubits × 4 layers, 1000 samples, `test_fraction` 0.3 → 700 train, batch 32, 100 epochs.

| Component | backprop | parameter-shift |
|---|---|---|
| Gradient executions (`epochs · n_train · per_sample`) | 70,000 | 9,030,000 |
| Per-epoch evaluation of both splits (`epochs · n_samples`) | 100,000 | 100,000 |
| **Total** | **170,000** | **9,130,000** |

Ratio per gradient step: **129×** (`2P + 1`). Ratio over a whole run: **54×** — lower, because
the evaluation pass is method-independent and dominates backprop's total.

**Memory is not the bottleneck, exactly as §2B.3 asserted.** A `complex128` state vector at 8
qubits is `2⁸ · 16 = 4,096 bytes`; a density matrix at `DENSITY_MATRIX_MAX_QUBITS = 6` is
`4⁶ · 16 = 65,536 bytes`. Both are kilobytes. Peak RSS of the whole `--full` run was
**397.8 MiB**, which is the Python interpreter plus PennyLane plus NumPy, not the states.

### Prediction vs measurement

**Measured execution counts matched the closed form exactly, in all 45 cells of the full grid
and all 39 of the quick grid** (`execution_law_verified: true`, counted with `qml.Tracker`).
Not approximately — exactly, e.g. 8q/4L/B32 parameter-shift predicted and measured 4,128.

---

## 3. Measured results — **sandbox numbers, not target numbers**

```
os          Linux 6.1.158+              python      3.11.2
cpu_model   Intel(R) Xeon(R) @ 2.60GHz  numpy       1.26.4
cpu_count   2                           scipy       1.17.1
total_ram   3.85 GiB                    pennylane   0.44.1
shots       None                        lightning   0.45.0
```

Target is an i5-13450HX / 16 GB / RTX 4050 laptop on Windows: 10 physical cores against 2, and a
much higher clock. **Every second below is this container's. Only the shape transfers.**

### 3.1 Qubit scaling (2 layers, batch 16, one gradient step, median of 5)

| qubits | backprop s | p-shift s (`default.qubit`) | p-shift s (`lightning.qubit`) | p-shift execs | µs/exec default | µs/exec lightning |
|---|---|---|---|---|---|---|
| 2 | 0.1360 | 0.4562 | 0.1975 | 272 | 1,677 | 726 |
| 3 | 0.2083 | 0.9520 | 0.2932 | 400 | 2,380 | 733 |
| 4 | 0.3969 | 1.6573 | 0.4453 | 528 | 3,139 | 843 |
| 5 | 0.4589 | 2.3112 | 0.6842 | 656 | 3,523 | 1,043 |
| 6 | 0.5252 | 3.3256 | 0.8904 | 784 | 4,242 | 1,136 |
| 7 | 0.6075 | 4.3909 | 1.1476 | 912 | 4,815 | 1,258 |
| 8 | 0.6841 | 5.6467 | 1.4888 | 1,040 | 5,430 | 1,432 |

Across 2→8 qubits the state vector grows **64×** but the cost per execution grows **3.2×**.
In this range the simulator is not paying for `2ⁿ` amplitudes; it is paying per *gate*, and the
gate count grows linearly in qubits. The exponential term has not engaged by 8 qubits.

### 3.2 Layer scaling (8 qubits, batch 16)

| layers | backprop s | p-shift s (default) | p-shift s (lightning) | execs | µs/exec default |
|---|---|---|---|---|---|
| 1 | 0.2529 | 1.5834 | 0.4412 | 528 | 2,999 |
| 2 | 0.6526 | 5.8161 | 1.5289 | 1,040 | 5,592 |
| 3 | 0.9199 | 12.0620 | 3.0521 | 1,552 | 7,772 |
| 4 | 1.2023 | 21.0697 | 5.1335 | 2,064 | 10,208 |

Backprop is **linear** in depth (4.75× over 4× layers). Parameter-shift is **quadratic**
(13.3× over 4× layers), because executions grow linearly in `L` *and* each execution grows
linearly in `L`.

### 3.3 Batch scaling (8 qubits, 4 layers) — the per-sample loop, visible

| batch | backprop s | ms/sample | p-shift s | ms/sample |
|---|---|---|---|---|
| 4 | 0.3745 | 93.6 | 5.1407 | 1,285.2 |
| 8 | 0.6101 | 76.3 | 10.3631 | 1,295.4 |
| 16 | 1.4094 | 88.1 | 20.8726 | 1,304.5 |
| 32 | 2.6819 | 83.8 | 42.0665 | 1,314.6 |

Parameter-shift cost per sample is flat to **2.3% across an 8× change in batch size**. That is
the direct experimental signature of `vqc.py:99-102`: there is no vectorisation to amortise, so
a batch of 32 costs exactly 32 batches of 1. **Increasing the batch size buys no speed here** —
it only changes the gradient's statistics.

### 3.4 The scaling laws (portable)

Per-execution cost ∝ gate count ∝ `q · L`. Combining with the execution law:

| Method | Wall clock per gradient step | Confirmed by |
|---|---|---|
| `backprop` | `∝ B · q · L` — **linear** in circuit size | §3.1, §3.2, §3.3 |
| `parameter-shift` | `∝ B · (q · L)²` — **quadratic** | §3.2 (13.3× over 4× layers) |

**The 129× execution ratio is not a 129× time ratio.** At 8q/4L/B16 the full grid measures that
cell twice, from two different families: parameter-shift costs **14.8×** and **17.5×** backprop
per step, and **12.6×** over a full run — because a backprop step does
one forward *and* one backward pass per sample, so its per-execution cost is far higher than a
plain forward execution. Execution count is the right *scaling* model and the wrong *timing*
model. A report that converts 129× executions into 129× seconds is wrong by an order of
magnitude.

### 3.5 `lightning.qubit` (§2B.5)

**Nothing needs installing.** `pennylane-lightning 0.45.0` is already importable — it arrives
**transitively** with PennyLane and is **absent from `requirements.txt`**. No `pip install` was
run and no pin moved.

- Agrees with `default.qubit` to 15 decimal places: `<Z₀> = 0.955336489125606` on both.
- Supports `parameter-shift` and `adjoint`; **does not support `backprop`** —
  `qml.device("lightning.qubit", …)` with `diff_method="backprop"` raises
  `QuantumFunctionError`. The grid skips that pair by design rather than recording 15 failures.
- Speedup on parameter-shift: **2.3× at 2 qubits rising to 4.1× at 8 qubits / 4 layers**. It
  helps most exactly where the cost is worst.

Since `backprop` is the default, lightning is relevant only to the expensive path — where it is
worth roughly a 4× rescue. **`adjoint` is the larger opportunity**: it returns a gradient
identical to backprop's (`-0.479425539`) at `O(1)` executions, and lightning supports it. That
is a Phase 5 design question, not something to adopt unilaterally here.

**GPU remains out of scope and nothing GPU-related was run.** `lightning.gpu` needs CUDA on
Linux (target is Windows ⇒ WSL2), and this repo's GPU support is CUDA-Q via
`docker-compose.gpu.yml` — a different stack that does not compose with a PennyLane device.

### 3.6 Correctness invariants, re-confirmed under benchmark conditions

| Invariant | Result |
|---|---|
| Same seed ⇒ bit-identical gradient | **true**, max delta `0.0` |
| Different seeds ⇒ different gradient | **true** |
| `backprop` vs `parameter-shift` agree | max delta **4.253e-16**, agree to 1e-9 |

---

## 4. A defect found while measuring: `limits.estimate_cost` understates the real cost

`estimate_cost` (`limits.py:116-146`) charges **one** evaluation pass:

```python
eval_execs = config.dataset.n_samples   # "one forward pass over everything at the end"
```

`trainer.train` evaluates **both splits at the end of every epoch** (`trainer.py:220-221`), which
is `epochs · n_samples` forward executions. The estimator is short by `(epochs − 1) · n_samples`.

Measured by running the real trainer end-to-end under `qml.Tracker`
(`estimator_validation()`, config 2q/1L/B16/3 epochs/60 samples):

| method | measured | `estimate_cost` | matches | corrected closed form | matches |
|---|---|---|---|---|---|
| backprop | 306 | 186 | **false** | 306 | **true** |
| parameter-shift | 1,314 | 1,194 | **false** | 1,314 | **true** |

Shortfall is exactly 120 = `(3−1) · 60` in both cases, and the corrected form
`epochs·n_train·per_sample + epochs·n_samples` reproduces the Tracker count exactly.

**Severity at the maximum configuration:** backprop true total 170,000 against an estimate of
71,000 — understated **2.39×**. The per-epoch evaluation is **59% of all backprop executions**
and only 1.1% of parameter-shift's.

**Impact today: none.** `grep -rn "estimate_cost" --include=*.py app/` returns no call sites —
nothing in the application uses it. The only consumer is
`tests/test_qml_config.py:144-158`, which asserts `dear > cheap` and the per-sample counts, all
of which survive the correction.

**Not fixed in Phase 4, deliberately.** Phase 4's scope is a script and a document, and the
standing additive gate requires `git diff --diff-filter=MD` against `origin/main` to be empty.
Editing `limits.py` would break that. The fix is one line and is proposed in `DECISIONS.md`
D-028 for senior sign-off — it must land before anything wires this estimator into the UI
warning its docstring promises.

---

## 5. Limits (§2B.4) — what changed: **nothing**

### 5.1 Projected full runs at the maximum configuration, on the sandbox

From `--full`, 5 independent projections per combination (one per grid family/batch size):

| method / device | median | min | max | × the 900 s soft limit |
|---|---|---|---|---|
| `backprop` / `default.qubit` | **121.8 min** (7,308 s) | 109.9 | 132.4 | **8.1×** |
| `parameter-shift` / `lightning.qubit` | **377.9 min** (22,674 s) | 369.4 | 380.2 | **25.2×** |
| `parameter-shift` / `default.qubit` | **1,539.3 min** (25.7 h) | 1,516.4 | 1,553.1 | **102.6×** |

Evaluation accounts for 17.5–20.2% of backprop's wall clock and ~1.1% of parameter-shift's. A
projection built from gradient steps alone understates backprop by ~1.25×, which is why the
script measures a forward-only pass per cell.

### 5.2 The default configuration is comfortably inside the limit

4 qubits, 2 layers, 200 samples, 20 epochs, batch 16:

| method | projected total | × soft limit |
|---|---|---|
| backprop | **86.6 s** | 0.10× |
| parameter-shift | **303.8 s** | 0.34× |

So the common case is not in danger even on this slow container. The problem is confined to the
top of the allowed range.

### 5.3 What this does and does not license

**`qml_task_soft_time_limit` / `hard` stay at 900/1200 and stay marked provisional.** §2B.4 is
explicit: the number must come from the max config under the default method **on the target**,
times a stated safety factor. I do not have the target. Tightening on evidence is permitted;
**loosening needs senior sign-off**, and the honest reading of §5.1 is that 900 s is *too small*
for the max config, not too large — on this container by 8.1× under the default method. Even if
the target laptop is 4× faster, backprop at max config lands near 1,830 s, still twice the
current soft limit. That is a loosening question, so it is the senior's and the user's, not
mine.

**No Composer cap was touched** (20/15/28, `PREVIEW_MAX_QUBITS = 12`).

**`DENSITY_MATRIX_MAX_QUBITS = 6` is unchanged and I have no evidence to tighten it.** Phase 1
is state-vector only; no density-matrix path exists to benchmark yet. 65,536 bytes is not a
reason to move it. It stays provisional for whichever phase introduces noise.

**`MAX_QUBITS`, `MAX_LAYERS`, `MAX_SAMPLES`, `MAX_EPOCHS`, `MAX_BATCH_SIZE` unchanged.** Every
candidate tightening I could justify would be derived from a 2-core container, which §2B.1
forbids.

### 5.4 Recommended design, for sign-off rather than unilateral action

§2B.3 asks for one of {lower ceiling when parameter-shift is selected, up-front estimate before
dispatch, clean rejection above a measured threshold}, justified from numbers. The numbers say
parameter-shift at the maximum configuration is **not merely expensive, it is structurally
infeasible**: 25.7 h on this container, 6.3 h even on `lightning.qubit`. A machine ten times
faster still leaves 2.6 hours, far outside any interactive timeout.

Recommendation, recorded as **D-027** and awaiting the target measurement:

1. **An up-front estimate before dispatch**, using the *corrected* cost formula, rejecting
   cleanly with the estimate in the error when it exceeds the soft limit. This is honest at any
   hardware speed because the threshold is time, not a hardcoded qubit count.
2. **A gradient-method-dependent ceiling** as the backstop — a real `limits.py` design change,
   which §2B.3 says must be recorded in `DECISIONS.md`. It is recorded; it is not implemented,
   because the constant that makes it correct is a target-machine measurement I do not have.

**Validation must be per gradient method, not once for the config** — a configuration that is
fine under backprop can be 129× worse under parameter-shift, and today's `limits.check()` does
not distinguish them.

---

## 6. What Phase 5 can and cannot reuse (§2B.7)

**Bounded by the laws measured here** — these reuse the same `VQC` forward pass, so
`∝ B · q · L` per execution and the `B·(2P+1)` parameter-shift law apply directly:

- More ansatz variants / entanglement patterns at the same qubit and layer counts.
- More datasets, more epochs, different batch sizes — batch is strictly linear (§3.3).
- Anything that changes only the *number* of forward passes.

**Needs its own benchmark before anyone promises it:**

- **Quantum kernel / QSVM.** A kernel matrix is `N²/2` circuit evaluations *before* any SVM
  fitting. At the 1,000-sample ceiling that is ~500,000 evaluations at ~10.4 ms each
  (§3.3 forward cost at 8q/4L) ≈ **87 minutes on this container**, and it is `O(N²)` so it
  degrades far faster than anything measured here. The existing `n_samples` ceiling was chosen
  for a linear-in-N trainer and does **not** transfer to a quadratic-in-N kernel.
- **Any density-matrix / noise path** — `4ⁿ` not `2ⁿ`, and never measured.
- **`adjoint` differentiation** — promising (§3.5) but unmeasured at scale.
- **Multi-class or multi-output heads** — more observables per sample multiplies the forward
  cost by a factor nobody has measured.

---

## 7. What is not verified here

- **No target-machine numbers.** Everything in §3 and §5.1 is a 2-core container.
- **No through-the-API measurement.** §2B.6 permits it as a separate measurement; it was not
  done. FastAPI validation, DB writes and Celery overhead are unmeasured.
- **No Redis or Celery worker in the sandbox**, so no end-to-end job timing exists.
- **No GPU**, by design.
- **No density-matrix measurement** — no such path exists yet.
- `pennylane-lightning 0.45.0` is an **unpinned transitive dependency** against PennyLane
  0.44.1. It was not added and not pinned; flagged as drift risk in D-029.

---

## 8. Commands run for this document

```bash
# environment
cd backend; export PATH=/home/user/.venv-ql/bin:$PATH

# quick grid (39 cells)
PYTHONPATH=. python scripts/bench_qml.py --quick --json /tmp/bench-quick.json --md /tmp/bench-quick.md

# full grid (45 cells) — the source of every number in §3 and §5
PYTHONPATH=. python scripts/bench_qml.py --full \
  --json ../artifacts/bench-full.json --md ../artifacts/bench-full.md

# projections recomputed from the saved run, no re-measurement
PYTHONPATH=. python scripts/bench_qml.py --reproject ../artifacts/bench-full.json \
  --md ../artifacts/bench-full.md

# §4 call-site check
grep -rn "estimate_cost" --include=*.py app/
grep -rn "estimate_cost" --include=*.py tests/
```

Raw artifacts: `artifacts/bench-full.json`, `artifacts/bench-full.md` (gitignored, per §2.3).
