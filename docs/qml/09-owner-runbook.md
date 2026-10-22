# 09 — Owner runbook: the three checks no agent can run

**Audience: the project owner, on the target machine.** Cold-executable — every
command is complete and nothing assumes a previous session.

Phase 8D is the last *code* phase. After it, every item in the defect ledger is
closed and nothing left in the backlog is a bug. What remains is three rows of
`MANUAL_TEST_REGISTER.md` that are **structurally impossible to automate**,
because each needs something no sandbox has: your CPU, your GPU, your Docker
daemon, or your API key.

Run them in this order. **MT-004 → MT-001 → MT-010.**

| Row | Needs | Blocks | Why it is first / last |
|---|---|---|---|
| **MT-004** | your CPU + a native venv | the shipped timeouts | It is the **only** source of the numbers behind `qml_task_soft_time_limit = 900` / `hard = 1200`. Everything downstream assumes those are survivable. |
| **MT-001** | Docker + Redis + Celery | the happy path | The only check that exercises the product as a user meets it. Needs a real broker, which no sandbox has. |
| **MT-010** | `GEMINI_API_KEY` | the live AI path | Narrowest gap, and it needs MT-001's stack already running. Last. |

**Do not skip ahead.** Running MT-001 before MT-004 means a run that exceeds the
provisional timeout gets killed by a limit nobody has validated, and you will not
know whether the limit or the product is at fault.

---

## Conventions used below

- **PowerShell is v5. `&&` is a parser error.** Every multi-command line uses `;`.
- **`cd` on every step.** Paths are absolute so a step works from anywhere.
- **Git and Docker from PowerShell, not WSL.** WSL `git status` on `/mnt/c/…`
  false-positives (~360 modified files). WSL is for `nvidia-smi` and `curl` only.
- **Docker Desktop must be fully running first** — the whale icon steady, not
  animating.
- **`artifacts/` is gitignored** (`.gitignore:29`). Anything written there will
  **not** commit itself and must be sent back deliberately.
- **Never** `git reset --hard`, `git clean -fd`, or force-push.

---

## Pre-flight — once, before any of the three

### P1. Sync to the final build

```powershell
cd C:\Users\laksh\quantum-learning-platform
git status --short
```

**If that prints anything, stop.** Do not stash or reset over work that has not
been reviewed. If it is empty:

```powershell
cd C:\Users\laksh\quantum-learning-platform
git fetch origin --prune
git checkout main
git merge --ff-only origin/main
git rev-parse --short HEAD
(git ls-files).Count
```

`--ff-only` refuses rather than creating a merge commit if anything diverged —
that refusal is information, not an obstacle. Record both numbers.

### P2. Confirm the history is not truncated

```powershell
cd C:\Users\laksh\quantum-learning-platform
git rev-parse --is-shallow-repository
git rev-list --count origin/main
```

Want `false` and a number in the hundreds. **A count of 1 means the clone is
shallow and every conclusion drawn from history is wrong** — this has bitten the
project twice. Fix with:

```powershell
cd C:\Users\laksh\quantum-learning-platform
git fetch --deepen=400 origin
```

### P3. `.env` exists and has the two keys these checks need

```powershell
cd C:\Users\laksh\quantum-learning-platform
Copy-Item .env.example .env -ErrorAction SilentlyContinue
Select-String -Path .env -Pattern "QML_ENABLED|GEMINI_API_KEY"
```

Both must be present. Values are set per-check below — **do not set
`QML_ENABLED=true` yet.** MT-004 does not want it, and leaving it off is how you
confirm the default deployment is unaffected.

### P4. Docker sees the GPU (only needed for the `-f docker-compose.gpu.yml` form)

```powershell
cd C:\Users\laksh\quantum-learning-platform
docker run --rm --gpus all ubuntu nvidia-smi
```

Want a table listing the RTX 4050. If this fails, Docker Desktop is not on a WSL2
backend or the NVIDIA driver is below 515 — **MT-001 can still run without the
GPU override** (see its step 1), but MT-005 stays a non-goal either way (D-030).

---

## MT-004 — `bench_qml.py --full` on the target machine

**What it settles:** the shipped timeouts. Phase 4 measured the *scaling shape*
in a 2-core container (backprop linear in circuit size, parameter-shift
quadratic) and that shape transfers. **The constants do not.** A limit tuned from
the container would be wrong in the dangerous direction.

**This runs natively on Windows, not in Docker** — it is measuring *your* CPU.

### Step 1 — a native backend venv with the real dependencies

The stack normally runs in containers, so this venv may not exist yet. It needs
PennyLane and everything in `requirements.txt`:

```powershell
cd C:\Users\laksh\quantum-learning-platform\backend
python -m venv .venv-bench
.\.venv-bench\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If `Activate.ps1` is blocked by execution policy, run this once and retry:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

### Step 2 — `psutil`, which is **not** optional cosmetics

```powershell
cd C:\Users\laksh\quantum-learning-platform\backend
pip install psutil
pip show psutil
```

`total_ram_gib()` (`bench_qml.py:89-101`) reads `/proc/meminfo`, which does not
exist on Windows, and **falls back to `psutil`**. `psutil` is deliberately **not**
in `requirements.txt` — it is a benchmark-only dependency and does not belong
there. Without it the run still completes but records `total_ram_gib: null`, and
peak RAM is one of the measurements that can only come from this machine. **A
null there is a hole in the only report that can fill it.**

**Do not add it to `requirements.txt` to fix this.** Install it into the venv.

### Step 3 — the run

**Smoke-test the venv first.** `--quick` is a small grid, ~2 minutes, and it fails
fast if a dependency is missing or `psutil` did not install — much cheaper to
discover that than 20 minutes into `--full`:

```powershell
cd C:\Users\laksh\quantum-learning-platform\backend
$env:PYTHONPATH = "."
python scripts\bench_qml.py --quick
```

If that completes, run the real thing:

```powershell
cd C:\Users\laksh\quantum-learning-platform\backend
$env:PYTHONPATH = "."
python scripts\bench_qml.py --full --json ..\artifacts\bench-full.json --md ..\artifacts\bench-full.md
```

**On mains power, nothing else heavy running, and do not interrupt it.** A killed
run is a ceiling data point, not a timing (§2B.6).

**It will not take 25 hours.** That Phase 4 figure is a *projection the script
prints*, not something it measures. `--full` times a **single gradient step** in
each of **45 cells** (7 qubit-scaling + 4 layer-scaling + 4 batch-scaling tuples,
× 2 gradient methods × 2 devices, minus the 15 lightning+backprop cells skipped
because a C++ statevector cannot differentiate), 5 reps each, then extrapolates.
Every cell carries `budget_s = 120.0`, so a slow cell is recorded with a non-`ok`
status rather than hanging the run.

**Expect roughly 10–40 minutes.**

### Step 4 — read the three things that matter

```powershell
cd C:\Users\laksh\quantum-learning-platform
Select-String -Path artifacts\bench-full.md -Pattern "execution_law_verified"
```

1. **`execution_law_verified` must be `true`.** If it is `false`, that is a
   **finding, not a flaky run** — it means the predicted execution counts did not
   match `qml.Tracker`, which they did in all 45 cells in the container.
2. **`total_ram_gib` must not be `null`** — if it is, step 2 did not take.
3. **The number that sets the timeout:** the `projections` entry for
   **`8q/4L/B32/backprop/default.qubit`**. Its `projected_seconds` is the measured
   maximum that `qml_task_soft_time_limit` must exceed by a stated safety factor.

### Step 5 — send it back

`artifacts/` is gitignored, so:

```powershell
cd C:\Users\laksh\quantum-learning-platform
Get-Item artifacts\bench-full.json, artifacts\bench-full.md | Select-Object Name, Length
```

Then attach **both files** to the conversation. Do not paste the JSON inline — it
is large, and the file is what gets analysed.

### What the result decides

| Outcome | Consequence |
|---|---|
| `projected_seconds` comfortably under 900 | The timeouts stand. Record the safety factor. |
| `projected_seconds` between 900 and 1200 | **The soft limit is wrong.** Tightening is allowed; **loosening needs your explicit sign-off** (§2B.4). |
| `projected_seconds` above 1200 | The maximum configuration is not runnable within the limits. Either the limits move (your call) or `MAX_QUBITS`/`MAX_LAYERS` move (a capacity decision, also yours). **This is the one outcome that reopens code work.** |
| `execution_law_verified: false` | Stop and report. Do not tune a timeout against a model that does not hold. |

---

## MT-001 — full browser round trip

**What it settles:** the product as a user meets it — submit → train → monitor →
**cancel** → results → **inference**. Phase 8C automated submit → train → results
in a real browser, but with `CELERY_TASK_ALWAYS_EAGER`, because `memory://` is not
a broker. **Cancel and inference are not covered, and no real broker, prefork
pool or signal-based time limit has ever been exercised.**

### Step 1 — bring up the whole stack *including* the QML worker

Enabling the QML Lab is **two independent actions**, and doing one without the
other produces a broken state rather than a half-enabled feature.

```powershell
cd C:\Users\laksh\quantum-learning-platform
docker compose -f docker-compose.yml -f docker-compose.gpu.yml --profile qml up -d --build
```

The first GPU build downloads ~1.5 GB of CUDA wheels (cuBLAS alone is 439 MB), so
expect minutes. **If P4 failed and you do not need CUDA-Q**, the plain form works
for this check:

```powershell
cd C:\Users\laksh\quantum-learning-platform
docker compose -f docker-compose.yml --profile qml up -d --build
```

`--profile qml` is **mandatory**. `docker-compose.yml:103` puts `qml-worker`
behind `profiles: ["qml"]`, so a plain `up` does not start it — and then the UI
works, every run fails, and it looks like a product bug.

### Step 2 — confirm all six services plus the worker are up

```powershell
cd C:\Users\laksh\quantum-learning-platform
docker compose -f docker-compose.yml -f docker-compose.gpu.yml --profile qml ps
```

**`qml-worker` must be listed and running.** If it is absent, step 1 lost the
profile flag.

### Step 3 — turn the flag on and restart the API

`qml_enabled` is a `pydantic_settings.BaseSettings` field — env-overridable, so
one image can be flipped without a rebuild.

```powershell
cd C:\Users\laksh\quantum-learning-platform
Add-Content .env "`nQML_ENABLED=true"
docker compose -f docker-compose.yml -f docker-compose.gpu.yml --profile qml up -d api qml-worker
```

Confirm the API publishes it:

```powershell
cd C:\Users\laksh\quantum-learning-platform
curl.exe -s http://localhost:8000/features
```

Want `{"qml_enabled":true}`. `/features` is **always mounted** — it returns
`false` when off, it does not 404.

### Step 4 — the round trip

Open the app, sign in as a staff user, and take **QML Lab** from the sidebar.

1. **Configure small:** `moons`, **4 qubits, 2 layers, 200 samples, 20 epochs,
   `backprop`**. Submit.
2. **Watch the progress view update per epoch.** This is the polling path that has
   only ever been asserted by reading `refetchInterval`.
3. **Submit a second, larger experiment and press Cancel mid-run.**
4. **Open the first experiment's Results**, then run a single **inference** from
   the saved model.

### Step 5 — what "pass" means, precisely

| Step | Expected |
|---|---|
| 2 | Reaches **`completed`**, loss curve **descends**, accuracy **above the baseline floor** |
| 3 | Reaches **`cancelled` within one batch**, and **never `failed`** |
| 4 | Confusion matrix whose **four cells sum to the test-split size**; inference returns a class with a probability in **[0, 1]** |

Step 3 is the one to watch. The cancel path uses a **cooperative
`deadline_seconds` strictly below the soft limit**, because Celery's `SIGALRM`
revocation is absent on Windows and `time_limit` kills a prefork child that
`--pool=solo` does not have. **If cancel lands as `failed` instead of
`cancelled`, the cooperative mechanism is not working on your platform** — that is
a real finding, not a flaky test.

### Step 6 — capture the log if anything fails

```powershell
cd C:\Users\laksh\quantum-learning-platform
docker compose -f docker-compose.yml -f docker-compose.gpu.yml --profile qml logs --tail=200 api qml-worker > artifacts\mt-001.log
```

Attach `artifacts\mt-001.log`. **The server log must contain no API key and no
full prompt payload** — if it does, that is itself a finding worth reporting.

---

## MT-010 — the Gemini explanation against a real key

**What it settles:** the configured AI path, which has **never executed**.
Everything automated in Phase 6 runs against a fake transport or the unconfigured
branch. Note the platform already carries three untested live Gemini paths (tutor,
Code Lab, Smart Composer) — this adds a fourth caller, not the first risk.

Keep MT-001's stack running.

### Step 1 — set the key and confirm the SDK is importable

```powershell
cd C:\Users\laksh\quantum-learning-platform
Add-Content .env "`nGEMINI_API_KEY=your-real-key-here"
docker compose -f docker-compose.yml -f docker-compose.gpu.yml --profile qml exec api pip show google-generativeai
```

`is_configured()` (`gemini_client.py:88`) requires **both** the key **and** an
importable `google.generativeai`. A key with no SDK still reports unconfigured,
which looks identical to a missing key.

```powershell
cd C:\Users\laksh\quantum-learning-platform
docker compose -f docker-compose.yml -f docker-compose.gpu.yml --profile qml up -d api qml-worker
```

### Step 2 — two runs, one per task

In the QML Lab, run to completion:

- a **`vqc`** run on **`moons`** (classification)
- a **`quantum_regression`** run on **`sine`** (regression)

On each Results tab press **Explain**.

### Step 3 — the checks, in order of importance

1. **Every number in the prose also appears in the "Measured" table directly
   beneath it.** Any figure in the prose that is not in that table is a
   **confabulation and the test fails.** This is the whole point of the grounded
   prompt builder, and it is the check that cannot be faked.
2. **The regression explanation mentions no** accuracy, precision, recall, F1 or
   confusion matrix. **The classification explanation mentions no** R², MAE or
   RMSE. (D-033: task-discriminated payloads.)
3. **A negative R² is described as worse than predicting the mean**, not as a
   small positive score. History carries real negatives (**−2.060 / −0.844 /
   −0.161**), so this is reachable, not theoretical.
4. Prose appears within **~10 s**, in two or three short paragraphs, **no markdown
   headings**.
5. **No claim of quantum advantage.**
6. **No API key and no full prompt payload in the server log.**

```powershell
cd C:\Users\laksh\quantum-learning-platform
docker compose -f docker-compose.yml -f docker-compose.gpu.yml --profile qml logs --tail=300 api > artifacts\mt-010.log
Select-String -Path artifacts\mt-010.log -Pattern "AIza|GEMINI_API_KEY"
```

**Want zero matches.** Any match is a leak and outranks every other result here.

### Step 4 — send back

Attach `artifacts\mt-010.log` plus **a screenshot of each explanation with its
Measured table visible** — check 1 cannot be verified from the log alone.

---

## Afterwards — turn the feature back off

Unless you are deliberately shipping it enabled:

```powershell
cd C:\Users\laksh\quantum-learning-platform
(Get-Content .env) -replace 'QML_ENABLED=true','QML_ENABLED=false' | Set-Content .env
docker compose -f docker-compose.yml -f docker-compose.gpu.yml --profile qml up -d api qml-worker
curl.exe -s http://localhost:8000/features
```

Want `{"qml_enabled":false}`, the nav entry gone, and `/qml-lab` rendering the 404
body. **`GEMINI_API_KEY` is shared with the tutor, Code Lab and Smart Composer —
do not remove it** unless you mean to disable those too.

To tear down:

```powershell
cd C:\Users\laksh\quantum-learning-platform
docker compose -f docker-compose.yml -f docker-compose.gpu.yml --profile qml down
```

---

## What closing these three does to the register

| Row | After |
|---|---|
| MT-004 | Closes. The timeouts become **measured** rather than provisional, with a stated safety factor. |
| MT-001 | Closes. The happy path, the cancel race and inference are exercised for the first time. |
| MT-010 | Closes. The configured AI path has executed. |
| **MT-002** | Closes as a side effect — MT-001 step 2 *is* the check that `qml-worker` starts and is isolated. |
| **MT-003** | Substantially advanced — MT-001 step 3 exercises the per-task limits under Windows `--pool=solo`. Record what the cancel actually did. |
| **MT-007** | **Not covered by any of the three.** It needs a *data-reuploading* configuration run by a human choice, which none of these checks configures. Still open, still yours. |
| MT-005 | **Stays a non-goal** (GPU path, D-030). |
| MT-006/008/009 | Already automated by Phases 8/8C/8D. |

When all three close, `docs/qml/08-release.md` §7 ("Not verified") shrinks to the
honest remainder, and the QML Lab is releasable on your sign-off — **you are the
P8/P9 human gate, and no agent can stand in for it.**
