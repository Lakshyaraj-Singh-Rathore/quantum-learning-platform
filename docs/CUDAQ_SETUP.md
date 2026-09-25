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
| ~20 GB free disk | WSL distro, CUDA toolkit, Python packages |

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

## Step 5 — Install CUDA-Q

```
python3 -m venv .venv && source .venv/bin/activate
```
```
pip install cudaq
```

**Verify** — this should print a list including `nvidia`:

```
python3 -c "import cudaq; print([t.name for t in cudaq.get_targets()])"
```

If `nvidia` is missing but the import worked, CUDA-Q cannot see the GPU. Go
back to step 2.

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
**CUDA-Q GPU (up to 26 qubits)** without a "unavailable" note.

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

## If something breaks

| Symptom | Cause |
| --- | --- |
| `nvidia-smi` not found in WSL | Windows driver too old; update and reboot |
| GPU access blocked by the operating system | a Linux NVIDIA driver got installed inside WSL — remove it |
| `import cudaq` works, no `nvidia` target | CUDA runtime not visible; recheck step 2 |
| Everything is very slow | the project is on `/mnt/c` — move it to `~` |
| Out of memory during a run | lower `MAX_GPU_QUBITS`, or switch to fp32 |

The backend degrades gracefully throughout: if CUDA-Q is missing or the GPU is
unavailable, the selector shows **CUDA-Q GPU** greyed out with the reason, and
every other backend keeps working exactly as before.
