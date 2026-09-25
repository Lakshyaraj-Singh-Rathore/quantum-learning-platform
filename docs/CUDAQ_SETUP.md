# CUDA-Q GPU backend — setup on Windows with WSL2

For an RTX 4050 Mobile (6 GB VRAM). Work through this **one command at a
time** and check the verification output before moving on — each step depends
on the previous one actually having worked.

CUDA-Q has no native Windows build. GPU acceleration is Linux-only, so on
Windows it runs inside WSL2. That is fine: Docker Desktop already uses the
WSL2 backend, so you are extending what you have rather than replacing it.

---

## Before you start

| Requirement | Why |
| --- | --- |
| Windows 11, or Windows 10 build 19044+ | GPU passthrough to WSL2 |
| Latest NVIDIA driver, installed on **Windows** | never install a driver inside WSL |
| **Python 3.12 (or 3.11)** inside WSL | see the warning below — Ubuntu 24.10+ ships 3.13/3.14 only |
| ~20 GB free disk | WSL distro, CUDA toolkit, Python packages |

**The Python version is a hard requirement, and newer Ubuntu is the trap.**
The backend pins `numpy==1.26.4` (cirq-core 1.4.x needs numpy<2), and numpy
1.26 publishes no wheels for Python 3.13+: `pip install -r
backend/requirements.txt` then tries to *compile* numpy from source, fails on
"cc not found", and would still fail with gcc because numpy 1.26 cannot build
against 3.13+ headers. Do not "fix" it with `apt install build-essential` —
get a 3.12 interpreter instead. Ubuntu's own apt has none on 24.10+, so use
`uv`, which fetches a standalone one:

```
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.local/bin/env
uv python install 3.12
```

Everything in steps 5 and 8 then happens inside a 3.12 venv created with
`uv venv --seed --python 3.12 .venv` (see step 5).

**The one rule that breaks everything if ignored:** install the NVIDIA driver
on Windows only. NVIDIA's documentation is blunt about this — the Windows
driver is projected into WSL as `libcuda.so`, and installing a Linux driver
inside WSL overwrites that stub and kills GPU access.

---

## Step 1 — Install WSL2

In PowerShell **as Administrator**:

```
wsl --install
```

Then:

```
wsl --update
```

Reboot when prompted.

**Verify** — this should print a kernel version of 5.10.16 or newer:

```
wsl cat /proc/version
```

---

## Step 2 — Confirm the GPU is visible inside WSL

Open a WSL shell (type `wsl` in PowerShell), then:

```
nvidia-smi
```

**Expected:** a table naming your RTX 4050. If you get "command not found",
your Windows driver is too old — update it from nvidia.com and reboot.

Note that temperature and power fields are often blank here. That is the known
"Limited Feature Set" of `nvidia-smi` under WSL2 and is not a problem; the
platform's thermal guard falls back to the Windows binary automatically.

**Verify the fallback works:**

```
nvidia-smi.exe --query-gpu=temperature.gpu --format=csv
```

This calls the Windows binary through WSL interop and *should* report a real
temperature.

---

## Step 3 — Install Python tooling inside WSL

```
sudo apt update && sudo apt install -y python3-pip python3-venv git
```

**Verify** — CUDA-Q needs pip 24.0 or newer:

```
python3 -m pip --version
```

If it is older:

```
python3 -m pip install --upgrade pip
```

---

## Step 4 — Clone the project into the WSL filesystem

**This matters for performance.** Clone into your Linux home directory, not
into `/mnt/c/`. Cross-filesystem I/O through `/mnt/c` is roughly ten times
slower, which turns a two-minute test run into twenty.

```
cd ~
```
```
git clone https://github.com/Lakshyaraj-Singh-Rathore/quantum-learning-platform.git
```
```
cd quantum-learning-platform && git checkout arena/01a0754d-quantum-learning-platform
```

---

## Step 5 — Create the venv and install CUDA-Q

From inside the clone (the project dir, not `/mnt/c`), with `uv` from the
warning above:

```
uv venv --seed --python 3.12 .venv
source .venv/bin/activate
python --version
```

**Verify:** `python --version` must print **3.12.x** (3.11 works too). If it
says 3.13/3.14, the venv was built from the system interpreter and
`pip install -r backend/requirements.txt` will fail on numpy later. The
`--seed` flag is what gives the venv a `pip`.

```
pip install "cudaq==0.16.*"
```

The backend is written against CUDA-Q **0.16**, whose wheel warns that the
`sample`/`observe` primitives will change in a future release. Pin
`cudaq==0.16` until the adapter (`backend/app/quantum/backends/cudaq_sim.py`)
is ported to the new API, or expect a silent breakage on the next upgrade.

**Verify** — this should print a list including `nvidia` **and** a device
count of at least 1:

```
python3 -c "import cudaq; print([t.name for t in cudaq.get_targets()]); print(cudaq.num_available_gpus())"
```

Note the two checks are not redundant: `get_targets()` lists what was
*compiled into the wheel* — even a machine with no GPU prints `nvidia` there.
`num_available_gpus()` is what reports the hardware, and the backend gates
availability on it, not on the target list.

If `nvidia` is missing, or the count is `0` while `nvidia-smi` works in the
same shell, CUDA-Q cannot see the GPU. Go back to step 2.

---

## Step 6 — Prove the GPU actually simulates

```
python3 -c "
import cudaq
cudaq.set_target('nvidia', option='fp32')
k = cudaq.make_kernel(); q = k.qalloc(24)
k.h(q[0])
for i in range(23): k.cx(q[i], q[i+1])
print(cudaq.sample(k, shots_count=100))
"
```

**Expected:** roughly half the shots on 24 zeros and half on 24 ones — a GHZ
state. If this runs in about a second, the GPU is working.

Watch the temperature in a second WSL shell while it runs:

```
watch -n 1 nvidia-smi.exe --query-gpu=temperature.gpu,utilization.gpu --format=csv
```

---

## Step 7 — Cap WSL2's memory

WSL2 claims up to half your RAM by default — 8 GB of your 16. Create
`C:\Users\laksh\.wslconfig` in **Windows** (Notepad is fine):

```
[wsl2]
memory=10GB
processors=8
```

Then from PowerShell:

```
wsl --shutdown
```

It restarts on next use with the new limits.

---

## Step 8 — Run the platform

```
pip install -r backend/requirements.txt -r frontend/requirements.txt
```

Start the API:

```
cd backend && PYTHONPATH=. DATABASE_URL=sqlite:///./dev.db CELERY_TASK_ALWAYS_EAGER=true uvicorn app.main:app --host 0.0.0.0 --port 8000
```

And in a second WSL shell, the UI:

```
cd frontend && PYTHONPATH=../backend:. API_BASE_URL=http://localhost:8000 streamlit run Home.py
```

Open <http://localhost:8501> from **Windows** — WSL2 forwards the port
automatically.

**Verify:** in the Composer, the backend dropdown should now offer
**CUDA-Q GPU (up to 28 qubits)** without a "unavailable" note.

---

## Thermal settings

Defaults are in `backend/app/config.py` and all are environment-overridable:

| Setting | Default | What it does |
| --- | --- | --- |
| `MAX_GPU_QUBITS` | 28 | 2.5 GB at fp32 including workspace; fits fp64 too |
| `GPU_TEMP_LIMIT_C` | 80 | refuse new GPU work above this; 0 disables |
| `GPU_COOLDOWN_SECONDS` | 3 | minimum gap between GPU jobs |

Why 28 rather than 29: measured on a mobile RTX 4050 the card reports 6141 MiB
total with only 84 MiB used, because an Optimus laptop drives the desktop from
the Intel iGPU. 29 qubits would fit fp32 but not fp64, so 28 keeps both usable.

**The workload is burstier than you might expect.** A 26-qubit, 100-gate
circuit moves about 107 GB through VRAM — roughly half a second. The Celery
hard limit of 15 s caps any single job, so the real risk is repeated
submissions, which is what the cooldown addresses.

Outside the software: elevate the back of the laptop, set your OEM utility
(Lenovo Vantage / MSI Center / Armoury Crate) to a balanced rather than
performance profile, and never run it on a bed or cushion.

---

## Optional — run EVERYTHING in Docker, GPU included

If one `docker compose up` is the workflow you actually want, the Compose GPU
override makes containers the native case too: it bakes `cudaq` into the
api/worker images and hands the container your card. Docker Desktop on WSL2
passes GPUs through (Windows driver >= 515 series; nothing to enable on
recent versions).

```
# one-time passthrough proof (prints the RTX 4050 table):
docker run --rm --gpus all ubuntu nvidia-smi

make up        # auto-detects the GPU and includes this override itself
# (no make? the explicit form:)
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build
```

`make up` runs the same Docker probe on every invocation: GPU usable → the
compose GPU file is added; not usable → the plain CPU stack. One command,
correct on every machine; `make gpu-check` prints which one you are about to
get.

The first build pulls ~1.5 GB of CUDA wheels (cuBLAS alone is 439 MB) on top
of the usual image; cached afterwards, until `backend/requirements.txt` or
the Dockerfile changes. The image base is Python 3.11, so the pinned numpy<2
stack installs exactly as in this guide's venv steps -- no 3.13/3.14 trap,
nothing to pin by hand.

**Verify:** <http://localhost:8501> → Composer dropdown offers **CUDA-Q GPU
(up to 28 qubits)**. The `/backends` availability check runs *inside the api
container*, so "0 devices" there means Docker's GPU passthrough -- not WSL --
is the thing to recheck.

One difference from the native setup: temperature reading. Containers get an
`nvidia-smi` from the runtime toolkit, which usually does report
`temperature.gpu` on WSL2, but if it doesn't, the thermal guard fails open
(job runs, gate inert) -- the concurrency lock and cooldown still apply.

---

## What every result tab reads on a CUDA-Q run

Up to the state-payload ceiling (20 qubits; 21–28-qubit runs stay
counts-only by design) each Composer tab is backed by this engine's own
numbers — nothing is borrowed from another backend:

| Tab | Source on CUDA-Q |
| --- | --- |
| Histogram, Probabilities, Born vs shots | `cudaq.sample` on the `nvidia` target |
| Statevector, Phase disk, Q-sphere, Bloch sphere | `cudaq.get_state` on the `nvidia` target |
| Density matrix | built from that statevector (view caps at 5 qubits on every engine) |
| Ideal vs noisy | the noisy run below: two samplings, both from CUDA-Q |

## Noise on CUDA-Q

The noise panel's knobs (T1, T2, readout, pulse times) do real work here —
in CUDA-Q's own formalism, not a Qiskit reinterpretation:

* the GPU statevector engine cannot carry Kraus channels (noise turns a pure
  state into a density matrix — physics, not software), so the noisy half of
  a run executes on **CUDA-Q's own `density-matrix-cpu` target**, capped at
  11 qubits; the GPU still supplies the ideal state views and the histogram
  baseline;
* thermal errors are CUDA-Q's built-in `AmplitudeDampingChannel(1−e^(−t/T1))`
  and `PhaseFlipChannel`, attached to every pulse gate — the same damping
  `thermal_relaxation_error` means on Aer, including virtual-Z gates costing
  nothing;
* readout error is a CUDA-Q `BitFlipChannel` attached to the kernel's `mz`
  operations themselves;
* the ideal twin histogram comes from sampling the same kernel without the
  model, so the two bars of "Ideal vs noisy" are one engine talking to itself.

Fidelity/purity gauges are deliberately absent on noisy CUDA-Q runs: 0.16's
`get_state` refuses a noise model, and this platform never shows a number it
did not simulate. Qiskit Aer renders both.

## Code Lab: CUDA-Q as a language, not just a backend

The Code Lab has a **CUDA-Q** tab when the wheel is installed (it ships with
`make gpu`): you write `cudaq.make_kernel()` builder code, and the platform
converts the kernel by parsing `str(kernel)` — CUDA-Q's own Quake MLIR
printer output, the very IR its JIT consumes. Controlled gates read back from
`quake.x [%c] %t` exactly as CUDA-Q compiled them. Decorated
`@cudaq.kernel` functions, `for_loop`s and conditional measurement are
refused with an instruction, not silently approximated.

---

## If something breaks

| Symptom | Cause |
| --- | --- |
| `nvidia-smi` not found in WSL | Windows driver too old; update and reboot |
| GPU access blocked by the operating system | a Linux NVIDIA driver got installed inside WSL — remove it |
| `import cudaq` works, no `nvidia` target | CUDA runtime not visible; recheck step 2 |
| **CUDA-Q GPU** marked unavailable after `pip install cudaq` | the API process sees 0 CUDA devices — the target list is compiled into the wheel and lies about hardware; check `cudaq.num_available_gpus()` in the *same* shell that runs uvicorn |
| Everything is very slow | the project is on `/mnt/c` — move it to `~` |
| Out of memory during a run | lower `MAX_GPU_QUBITS` (precision is already fp32 by default) |

The backend degrades gracefully throughout: if CUDA-Q is missing or the GPU is
unavailable, the selector shows **CUDA-Q GPU** greyed out with the reason, and
every other backend keeps working exactly as before.
