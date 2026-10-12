# Getting the latest working build, and running it with CUDA-Q

Latest verified commit: **`ecc80cf`** — present on both `main` and
`arena/01a0d874-quantum-learning-platform`.

---

## Part 1 — Pull the latest

### ⚠️ Do this first: check where you actually are

The sandbox lost three commits during this session, so **do not assume your local
branch matches GitHub.** Look before you pull.

**PowerShell** — run each line separately:

```powershell
cd C:\Users\laksh\quantum-learning-platform
cd C:\Users\laksh\quantum-learning-platform; git fetch origin
cd C:\Users\laksh\quantum-learning-platform; git status
cd C:\Users\laksh\quantum-learning-platform; git log --oneline -3
```

**WSL / Git Bash** — run each line separately:

```bash
cd /mnt/c/Users/laksh/quantum-learning-platform
cd /mnt/c/Users/laksh/quantum-learning-platform && git fetch origin
cd /mnt/c/Users/laksh/quantum-learning-platform && git status
cd /mnt/c/Users/laksh/quantum-learning-platform && git log --oneline -3
```

**What you want to see:** `git status` says *"Your branch is up to date"* or *"nothing
to commit, working tree clean"*, and `git log` shows `ecc80cf` at the top.

| If you see | Do this |
|---|---|
| `ecc80cf` already at top, tree clean | **Done.** Skip to Part 2. |
| "branch is behind" | Pull (below) |
| "have X and Y different commits" | **Stop.** See "Diverged" below |
| Uncommitted changes | Commit or stash them first |

### Case A — you're behind (the normal case)

**PowerShell:**

```powershell
cd C:\Users\laksh\quantum-learning-platform; git pull --ff-only origin main
```

**WSL / Git Bash:**

```bash
cd /mnt/c/Users/laksh/quantum-learning-platform && git pull --ff-only origin main
```

If you're on the arena branch rather than `main`:

**PowerShell:**

```powershell
cd C:\Users\laksh\quantum-learning-platform; git pull --ff-only origin arena/01a0d874-quantum-learning-platform
```

**WSL / Git Bash:**

```bash
cd /mnt/c/Users/laksh/quantum-learning-platform && git pull --ff-only origin arena/01a0d874-quantum-learning-platform
```

`--ff-only` refuses to create a merge commit. If it refuses, you're in the diverged case.

### Case B — diverged

Your local has commits GitHub doesn't. **Do not force anything.**

**PowerShell:**

```powershell
cd C:\Users\laksh\quantum-learning-platform; git log --oneline origin/main..HEAD
```

**WSL / Git Bash:**

```bash
cd /mnt/c/Users/laksh/quantum-learning-platform && git log --oneline origin/main..HEAD
```

That lists what's local-only. If those are the three lost Streamlit-removal commits
(`21a253c`, `7c75cfd`, `bbbb591`), they are **already superseded** by what's on GitHub —
reset to the remote instead of merging:

**PowerShell:**

```powershell
cd C:\Users\laksh\quantum-learning-platform; git reset --hard origin/main
```

**WSL / Git Bash:**

```bash
cd /mnt/c/Users/laksh/quantum-learning-platform && git reset --hard origin/main
```

⚠️ `--hard` discards local commits and any uncommitted work. Confirm with
`git log --oneline origin/main..HEAD` (above) that you have nothing to keep first.

### Verify the pull worked

**PowerShell:**

```powershell
cd C:\Users\laksh\quantum-learning-platform; git log --oneline -1
cd C:\Users\laksh\quantum-learning-platform; Test-Path frontend\Home.py
cd C:\Users\laksh\quantum-learning-platform; Test-Path docs\ppt\MARKETING_DECK_SOURCE.md
```

**WSL / Git Bash:**

```bash
cd /mnt/c/Users/laksh/quantum-learning-platform && git log --oneline -1
cd /mnt/c/Users/laksh/quantum-learning-platform && ls frontend/Home.py 2>/dev/null || echo "Home.py gone (correct)"
cd /mnt/c/Users/laksh/quantum-learning-platform && ls docs/ppt/MARKETING_DECK_SOURCE.md
```

Expected: top commit `ecc80cf`, `Home.py` **absent** (Streamlit removed),
`MARKETING_DECK_SOURCE.md` **present**.

---

## Part 2 — Running with CUDA-Q

### The honest summary first

CUDA-Q needs **an NVIDIA GPU** and, on Windows, **WSL2 with GPU passthrough**. It will
not work on a laptop without an NVIDIA card, and it will not work in plain PowerShell.
Without it, **nothing else breaks** — the backend self-disables and tells you why, and
the other five engines give identical results.

The full walkthrough is `docs/CUDAQ_SETUP.md` (verified current — no stale Streamlit
references). What follows is the critical path plus the traps.

### Two paths

#### Path 1 — Docker (simplest, if you have Docker Desktop + WSL2 backend)

**PowerShell:**

```powershell
cd C:\Users\laksh\quantum-learning-platform
cd C:\Users\laksh\quantum-learning-platform; docker run --rm --gpus all ubuntu nvidia-smi
cd C:\Users\laksh\quantum-learning-platform; docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build
```

The first `docker run` is the **pass/fail gate** — if it doesn't print your GPU table,
stop; passthrough isn't set up and the build will waste 10 minutes.

**WSL / Git Bash:**

```bash
cd /mnt/c/Users/laksh/quantum-learning-platform
cd /mnt/c/Users/laksh/quantum-learning-platform && docker run --rm --gpus all ubuntu nvidia-smi
cd /mnt/c/Users/laksh/quantum-learning-platform && docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build
```

**Expect:** first build downloads **~1.5 GB** of CUDA wheels (cuBLAS alone is 439 MB).
Minutes, not seconds. Cached afterwards until `backend/requirements.txt` or the
Dockerfile changes.

#### Path 2 — Native WSL2 (no Docker)

Follow `docs/CUDAQ_SETUP.md` steps 1–8. The parts people get wrong:

**1. Clone into the WSL filesystem, not `/mnt/c`.**
Cross-filesystem I/O makes the venv crawl.
`/mnt/c/Users/laksh/quantum-learning-platform` is fine for *reading*; work from
`~/quantum-learning-platform`.

**2. Python 3.12, not 3.13/3.14.**

```bash
cd ~/quantum-learning-platform
cd ~/quantum-learning-platform && uv venv --seed --python 3.12 .venv
cd ~/quantum-learning-platform && source .venv/bin/activate
cd ~/quantum-learning-platform && python --version
```

Must print **3.12.x** (3.11 also works). On 3.13+, `numpy` install fails.

**3. Pin CUDA-Q to 0.16.**

```bash
cd ~/quantum-learning-platform && pip install "cudaq==0.16.*"
```

The adapter (`backend/app/quantum/backends/cudaq_sim.py`) is written against the 0.16
`sample`/`observe` API. Newer majors will break it **silently**.

**4. Two verification checks, and they are not redundant.**

```bash
cd ~/quantum-learning-platform && python3 -c "import cudaq; print([t.name for t in cudaq.get_targets()]); print(cudaq.num_available_gpus())"
```

- `get_targets()` shows what was **compiled into the wheel** — even a GPU-less machine
  prints `nvidia` there
- `num_available_gpus()` reports **actual hardware** — the backend gates on this, not
  the target list

You need `nvidia` in the list **and** a count ≥ 1.

**5. Run it.**

```bash
cd ~/quantum-learning-platform/backend && PYTHONPATH=. DATABASE_URL=sqlite:///./dev.db CELERY_TASK_ALWAYS_EAGER=true uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Second shell:

```bash
cd ~/quantum-learning-platform/frontend/web && npm install && npm run dev
```

Open **http://localhost:3001** from Windows — WSL2 forwards the port automatically, and
the dev server proxies `/api` to :8000.

---

## Part 3 — Confirm CUDA-Q is actually live

In the Composer, the backend dropdown should offer **CUDA-Q GPU (up to 28 qubits)**
with **no** "unavailable" note.

If it's greyed out, the UI shows the real reason, taken verbatim from
`cudaq_sim.py:is_available()`:

| Message | Meaning |
|---|---|
| "CUDA-Q is not installed" | Not in the venv. On Windows it needs WSL2 |
| "exposes no GPU target" | Wheel lacks the CUDA runtime |
| "sees no CUDA-capable GPU (0 devices)" | Driver not visible — on Windows that means the **Windows-side** driver plus WSL2 passthrough |

### The limits

| Setting | Default | Source |
|---|---|---|
| `MAX_GPU_QUBITS` | **28** | `backend/app/config.py:49` |
| `GPU_TEMP_LIMIT_C` | 80 | refuses GPU work above this; 0 disables |
| `GPU_COOLDOWN_SECONDS` | 3 | minimum gap between GPU jobs |
| `NOISE_MAX_QUBITS` | **11** | `cudaq_sim.py` — density-matrix engine |

**Why 28 and not 29:** measured on a mobile RTX 4050 (6141 MiB), 28 qubits is 2.5 GB at
fp32 including workspace. 29 does not fit.

**Note the noise ceiling is 11, not 28.** Noisy CUDA-Q runs use the density-matrix
engine, which is far more memory-hungry. A 28-qubit *noiseless* run is fine; a 28-qubit
*noisy* run will be refused.

---

## Part 4 — If it doesn't work

**Both checks pass but the dropdown still says unavailable.** The API process was
probably started before the venv had CUDA-Q, or it's running in a different
interpreter. Restart the API.

**`nvidia-smi` works but `num_available_gpus()` is 0.** Inside WSL2, `nvidia-smi` has a
"Limited Feature Set" — the code accounts for this (`gpu_guard.py` tries both
`nvidia-smi` and `nvidia-smi.exe`). Usually means the **Windows** driver is too old;
you need ≥ the 515 series.

**Older Docker Compose rejects `gpus: all`.** Use the long form — it's already
commented at the bottom of `docker-compose.gpu.yml`.

**Everything else failing?** Don't fight it. Run without CUDA-Q:

**PowerShell:**

```powershell
cd C:\Users\laksh\quantum-learning-platform; docker compose up --build
```

**WSL / Git Bash:**

```bash
cd /mnt/c/Users/laksh/quantum-learning-platform && docker compose up --build
```

Five of six backends work credential-free, and the CUDA-Q results are identical to
theirs — it's an accelerator, not a different simulator.
