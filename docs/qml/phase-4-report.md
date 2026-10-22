# Phase 4 report — benchmarks, limits, and a method for Phase 5

**Deviation, repeated as required.** Work is on the Arena session branch
`arena/63ae45b4-quantum-learning-platform`, not on `main`. I never push to `main`; the senior
ports at each phase boundary. `main` remains the source of truth and this branch was merged up
from `origin/main @ 20589f4` before any Phase 4 work began. No `--force` of any kind was used.

---

## 1. Gates

| Gate | Required | Measured | Verdict |
|---|---|---|---|
| `cd backend; PYTHONPATH=. pytest -q` | 1034 passed / 5 skipped | **1034 passed, 5 skipped in 135.39s** | PASS |
| `npm run typecheck` | 0 errors | **0** | PASS |
| `npm run build` | PASS | **✓ built in 7.60s** | PASS |
| Harness loop FAIL total | 57 = 9+20+20+8 | **57 = 8+9+20+20** | PASS |
| `golden:quantum` | 190 @ 1e-9 | **190 agree with numpy (1e-9)** | PASS |
| `golden:demos` | 804 @ 1e-9 | **804 agree with numpy (1e-9)** | PASS |
| `golden:grover` | 3306 @ 1e-9 | **3306 agree with numpy (1e-9)** | PASS |
| a11y | 0 criticals | **0 a11y criticals across every page** | PASS |
| `qml:circuit` / `qml:ui` / `qml:render` | 49 / 58 / 34 | **49 / 58 / passed all flag states** | PASS |

Harness loop, per script (counting only per-assertion `^FAIL` lines, with
`API_TARGET=http://127.0.0.1:8000`):

```
render:results       per-assertion FAIL=8
render:codelab       per-assertion FAIL=9
render:p5            per-assertion FAIL=20
render:games         per-assertion FAIL=20
---------------------------------------------
TOTAL per-assertion FAIL = 57   (gate: 57 = 9+20+20+8)
```

Same multiset as Phase 0 and Phase 3. No pre-existing failure was fixed, introduced, or
re-counted.

**Phase 4 changed no engine behaviour**, so the "if it changes engine behaviour, re-run the QML
suite" clause does not bite — but the full backend suite was re-run anyway and is unchanged at
1034/5.

### Additive check

START of phase (against merge commit `2859f2a`):

```
$ git diff --diff-filter=MD --name-only origin/main HEAD
(empty)
$ git diff --diff-filter=A  --name-only origin/main HEAD
(empty)
$ git ls-files | wc -l
587        (= 587 on main @ 20589f4)
```

END of phase — see §5 for the exact output. **One file is modified and it is deliberate:**
`docs/qml/DECISIONS.md`, which the phase brief explicitly instructs Phase 4 to append to. It is
flagged here rather than buried, because the standing rule is that the `MD` filter should be
empty and any modification must be justified.

---

## 2. What was delivered

| Path | Kind | What it is |
|---|---|---|
| `backend/scripts/bench_qml.py` | **new**, 737 lines | The §2B.2 deliverable: `--quick` / `--full`, JSON **and** markdown output, `--reps`, `--reproject`. |
| `docs/qml/04-benchmarks.md` | **new** | The measurements, the laws, the limits analysis, every claim with its command. |
| `docs/qml/phase-4-report.md` | **new** | This file. |
| `docs/qml/DECISIONS.md` | **modified** (append only, 437 → 534 lines) | D-026 … D-030. |

No engine file, no API, no frontend source, no migration, no dependency was touched.
`requirements.txt` is byte-identical to `origin/main` and **no `pip install` was run** —
`lightning.qubit` turned out to be already present (D-029).

Raw benchmark output lives in `artifacts/` (gitignored, §2.3) and is **not** committed:
`artifacts/bench-full.json`, `artifacts/bench-full.md`.

---

## 3. The three findings that matter

### 3.1 The execution law was predicted and then measured exactly

`P = 2·n_qubits·n_layers`; backprop costs `B` executions per gradient step, parameter-shift
costs `B·(2P+1)`. Counted with `qml.Tracker`, **measured equals predicted in all 45 cells of
the full grid and all 39 of the quick grid** — e.g. 4,128 predicted and 4,128 measured at
8q/4L/B32.

Two corrections to §2B.3's premise, both of which I must report rather than inherit:

- the ansatz is **2** parameters per qubit per layer, not 3 (`P = 64` at the maximum, not 96);
- far more consequentially, §2B.3's per-step figure **omits the per-sample loop**.
  `vqc.py:99-102` iterates `for row in x` with no parameter broadcasting, so batch size
  multiplies everything. Its ~600,000-execution estimate for a full run is low by >10×; the
  real figure is **9,130,000** under parameter-shift.

The repo's own `limits.estimate_cost` already had this right — it is the prose premise that was
wrong, not the code.

**But execution count is not a timing model.** The 129× execution ratio is only a **12.6×**
wall-clock ratio over a full run, because a backprop step does a forward *and* a backward pass
per sample and so costs far more per execution. Converting 129× executions into 129× seconds
would have been wrong by an order of magnitude. Measured laws: backprop `∝ B·q·L` (linear in
circuit size), parameter-shift `∝ B·(q·L)²` (quadratic).

Memory was confirmed to be a non-issue exactly as §2B.3 said: 4,096 bytes of state vector at 8
qubits, 65,536 bytes of density matrix at the cap, against 397.8 MiB peak RSS that is almost
entirely interpreter and libraries.

### 3.2 A real defect: `limits.estimate_cost` undercounts by `(epochs − 1)·n_samples`

The estimator charges one evaluation pass (`limits.py:137`); `trainer.train` evaluates **both
splits at the end of every epoch** (`trainer.py:220-221`). Proven by running the shipped
trainer end-to-end under `qml.Tracker`: measured **306** backprop and **1,314**
parameter-shift against the estimator's **186** and **1,194** — short by exactly
`120 = (3−1)·60` in both cases, with the corrected closed form reproducing the Tracker count
exactly.

At the maximum configuration it understates backprop **2.39×** (71,000 claimed, 170,000 real),
because the per-epoch evaluation is **59% of all backprop executions**.

**Not fixed here, on purpose.** It is a one-line change to `limits.py`, which would break the
additive gate, and Phase 4's scope is a script and a document. Impact today is nil — the
function has **no call sites in `app/`** — but its docstring promises it to the UI and D-027
proposes building dispatch-time rejection on it, so it must be corrected before either lands.
Recorded as **D-028** with the exact fix.

### 3.3 Parameter-shift at the maximum configuration is structurally infeasible

Projected full runs at 8q/4L/1000 samples/100 epochs, median of 5 projections, **on the
sandbox**:

| method / device | median | × the 900 s soft limit |
|---|---|---|
| `backprop` / `default.qubit` | 121.8 min | **8.1×** |
| `parameter-shift` / `lightning.qubit` | 377.9 min | **25.2×** |
| `parameter-shift` / `default.qubit` | 1,539.3 min (25.7 h) | **102.6×** |

The default configuration, by contrast, is comfortable: **86.6 s** under backprop (0.10× the
limit) and 303.8 s under parameter-shift. The problem is confined to the top of the allowed
range.

---

## 4. Limits: nothing was changed, and why that is the correct outcome

- **`qml_task_soft_time_limit` / `hard` stay 900 / 1200 and stay marked provisional.** §2B.4
  requires the number to come from the max config under the default method *on the target*,
  times a stated safety factor. I do not have the target. Note the direction: the evidence says
  900 s is **too small**, not too large — which is a *loosening* question and therefore needs
  senior sign-off, not my unilateral edit.
- **Composer caps untouched** (20 / 15 / 28, `PREVIEW_MAX_QUBITS = 12`).
- **`DENSITY_MATRIX_MAX_QUBITS = 6` unchanged — I have no evidence to tighten it.** Phase 1 is
  state-vector only; there is no density-matrix path to benchmark yet. 65,536 bytes is not a
  reason to move it.
- **No ceiling tightened.** Every tightening I could justify would be derived from a 2-core
  container, which §2B.1 explicitly forbids.
- **Recommended design recorded, not implemented** (D-027): an up-front estimate before
  dispatch using the *corrected* formula with clean rejection, backed by a
  gradient-method-dependent ceiling. Validation must be **per gradient method** — today
  `limits.check()` does not distinguish them, and a config that is fine under backprop is 129×
  worse under parameter-shift.

**`lightning.qubit` (§2B.5): nothing was installed.** `pennylane-lightning 0.45.0` is already
importable as a transitive dependency of PennyLane; the "if not installed, do NOT add it"
branch never triggered, so no `--dry-run` was needed and no pin moved. It agrees with
`default.qubit` to 15 dp, speeds parameter-shift up **4.1×** at the maximum configuration, and
**cannot do `backprop`**. `adjoint` is flagged as the larger opportunity (backprop-identical
gradient at `O(1)` executions) for Phase 5 to decide on. **GPU: skipped entirely** (D-030).

---

## 5. Repository state

```
$ git diff --diff-filter=MD --name-only origin/main HEAD
docs/qml/DECISIONS.md          <- the one deliberate modification (append-only)

$ git diff --diff-filter=D --name-only origin/main HEAD
(empty)

$ git diff --diff-filter=A --name-only origin/main HEAD
backend/scripts/bench_qml.py
docs/qml/04-benchmarks.md
docs/qml/phase-4-report.md

$ git ls-files | wc -l
590        (587 on main @ 20589f4, + 3 additions)

$ git diff --shortstat origin/main HEAD
 4 files changed, 1458 insertions(+)
```

**Zero deletions across the whole phase.** That is the proof that the one modified file was
appended to and nothing in it was rewritten or removed.

**1 M · 0 D · 3 A · 590 tracked.** Every addition is itemised above; the single modification is
the `DECISIONS.md` append the phase brief required.

---

## 6. What Phase 4 cannot close, and what I need from you

**Phase 4 cannot be completed from this sandbox, by design**, and I am not going to pretend
otherwise. The deliverable §2B.1 asks for is "provisional limits clearly labelled + a script
the user runs on their own laptop". That is what is here.

**Please run this on the target machine** (i5-13450HX / RTX 4050 / 16 GB / Windows) and send
back `artifacts/bench-full.json`:

```powershell
cd backend
$env:PYTHONPATH = "."
python scripts\bench_qml.py --full --json ..\artifacts\bench-full.json --md ..\artifacts\bench-full.md
```

It takes roughly 40 minutes on a 2-core container and should be considerably faster on ten
cores. With that file I can set `qml_task_soft_time_limit` from a measured maximum times a
stated safety factor, and close D-027 with real constants instead of a recommendation.

### Not verified, stated plainly

- **No target-machine numbers.** Everything measured here is a 2-core Xeon container with
  3.85 GiB RAM; absolute seconds do not transfer and no limit was tuned from them.
- **No through-the-API measurement** — engine-direct only, which is what §2B.6 asked for; the
  FastAPI/Celery/DB overhead remains unmeasured.
- **No Redis or Celery worker in the sandbox**, so no end-to-end job was ever timed.
- **No GPU, no `docker` binary.**
- **No density-matrix measurement** — no such code path exists yet.
- **Nothing crashed or was OOM-killed**, so there are no ceiling data points, only timings. No
  limit was derived from a killed run.
- `pennylane-lightning 0.45.0` is an **unpinned transitive dependency** sitting at a higher
  minor version than PennyLane 0.44.1 — a real drift risk, flagged in D-029, not fixed
  unilaterally.

### For Phase 5 (§2B.7)

The measured laws already bound anything that reuses the same forward pass: more ansatz
variants, more datasets, more epochs, different batch sizes (batch is strictly linear — and
note that **raising the batch size buys no speed**, only different gradient statistics).

They do **not** bound a quantum kernel. A kernel matrix is `N²/2` circuit evaluations before
any SVM fitting — at the 1,000-sample ceiling that is ~500,000 evaluations ≈ **87 minutes on
this container**, and it is quadratic in `N` where everything measured here is linear. The
existing `n_samples` ceiling was chosen for a linear-in-N trainer and must not be reused for a
kernel without its own benchmark. Density-matrix/noise paths, `adjoint` at scale, and
multi-output heads are likewise unmeasured.
