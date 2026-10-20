# Vision QA Campaign — automated, 30-run, user-perspective

**Copy everything below the `---` line and give it to the vision agent as its task.**
It is written to be self-contained: the agent needs no prior context on this project.

**Target:** commit `4116491` on `main`
**Scope:** the three features added in `21a9f14` — **Qudit Lab**, **Noise Lab**, **Smart Composer** — plus the routes they touch.

---

You are a **vision QA engineer**. You have browser automation and vision.

Your job is to find the problems a **real user** would see in three newly-shipped
features of a quantum-computing teaching platform. You will do that by driving the
actual website the way a user does, **30 times**, capturing screenshots throughout,
and then **looking at those screenshots** and reporting what is wrong.

You are **not** here to fix anything. You are here to find and report.

You are also not here to be reassuring. A report that says "looks good" is a failure.
If you genuinely find nothing, you must show the screenshots that prove it.

---

## 1. What you are testing

A React SPA (frontend) talking to a FastAPI backend. Three features were just added
and have **never been looked at by a human or an agent with vision**.

| Feature | Route | What it claims to do |
|---|---|---|
| **Qudit Lab (Beta)** | `/qudit` | Simulate *qudits* — d-level quantum systems (d = 2,3,4,5) — not just qubits. Circuit editor, density-matrix inspector, noise controls, learn panel. |
| **Noise Lab** | inside `/composer` | Apply realistic noise channels (T1/T2 decoherence, depolarizing, bit/phase flip, readout) to a circuit and compare ideal vs noisy results. |
| **Smart Composer** | inside `/composer` | Generate a circuit from a natural-language prompt, and simplify/optimise an existing circuit without changing what it does. |

## 2. Environment

```bash
git clone https://github.com/Lakshyaraj-Singh-Rathore/quantum-learning-platform
cd /home/user/quantum-learning-platform   # adjust to your workspace root
git fetch --all --prune
git reset --mixed origin/main
git checkout -f HEAD          # REQUIRED — reset --mixed does not create new files

python3 -m venv /home/user/.venv-ql
/home/user/.venv-ql/bin/pip install -q --upgrade pip
/home/user/.venv-ql/bin/pip install -q -r backend/requirements.txt pytest playwright
/home/user/.venv-ql/bin/python -m playwright install chromium
cd frontend/web && npm install && node scripts/link-shared.mjs
```

Start both services (two terminals / background processes):

```bash
# Terminal A — API. SQLite avoids needing Postgres.
cd /home/user/quantum-learning-platform/backend
DATABASE_URL="sqlite:///./qa.db" PYTHONPATH=. \
  /home/user/.venv-ql/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Terminal B — frontend preview of the BUILT bundle
cd /home/user/quantum-learning-platform/frontend/web
npx vite build
npx vite preview --host 0.0.0.0 --port 4173
```

If you are behind a proxied preview hostname, Vite will reject it with HTTP 403.
Start it with `VITE_ALLOWED_HOSTS=<your-host> npx vite preview --host 0.0.0.0 --port 4173`.

Confirm before you begin:
- `curl http://localhost:8000/health` → 200
- `curl http://localhost:4173/` → 200
- `curl -s http://localhost:8000/openapi.json | python3 -c "import json,sys; print(len(json.load(sys.stdin)['paths']))"` → **58**

**Known environment limits — these are NOT defects, do not report them:**
- Without Redis, `POST /jobs` returns `"Could not enqueue job"`. Expected here.
- Without `GEMINI_API_KEY`, AI retrieval falls back to keyword search. Expected.
- Without `QBRAID_API_KEY` and a GPU, the `qbraid` and `cudaq` backends report
  unavailable. Expected.

## 3. Verified-good baselines

Measured on this commit before you started. **If you observe different numbers, that
is a finding — report it, do not assume you mis-ran it.**

```
Frontend build ................. PASS
API paths ...................... 58
Backend unit tests ............. 818 passed, 5 skipped

/qudit/limits .................. dimensions [2,3,4,5]
                                 safe_limits     {"2":10,"3":6,"4":5,"5":4}
                                 expanded_limits {"2":12,"3":7,"4":6,"5":5}

/noise/simulate  (Bell circuit, 2048 shots, seed 7)
  no noise ..................... fidelity 1.0000,  TVD 0.0000
  decoherence t1=50 t2=30 ...... fidelity 0.9866,  TVD 0.0244
  stochastic depol_2q=0.2 ...... fidelity 0.8500,  TVD 0.1001

/smart-composer/generate "create a bell state", 2 q .... returns Bell |Φ+⟩
```

### Correct request shapes — get these right

A **flat** config is silently ignored and returns a confident, noiseless result.
Every noise block defaults to `enabled: false`.

```jsonc
// POST /noise/simulate
{"circuit_ir": { /* standard IR */ },
 "noise_config": {"decoherence": {"enabled": true, "t1_us": 50, "t2_us": 30},
                  "stochastic":  {"enabled": true, "depolarizing_2q": 0.2}},
 "shots": 2048, "seed": 7}

// POST /qudit/simulate
{"circuit": {"version": "1.0", "id": "t1", "name": "t", "dimension": 3,
             "wires": [{"id": "q0", "index": 0, "dimension": 3, "initial_state": 0}],
             "ops": [{"id": "op1", "gate": "x", "targets": [0],
                      "controls": [], "params": {}, "dimension": 3}]},
 "shots": 1024, "calculate_entropy": true}
```

Auth: `POST /auth/register` returns a token. `/auth/login` (form-encoded) returned
none — use register. There is **no `/api` prefix** on any route.

---

## 4. Your method

### 4.1 Automate the driving; you do the looking

Write **one automation script** that performs the full user journey (§4.2) and run it
**30 times**. The script:

- drives a real browser (Playwright/Chromium),
- seeds itself from the run number so run 1..30 differ in inputs but are reproducible,
- captures a screenshot at **every** step into `qa-runs/run-NN/<step>.png`,
- records **every** console `error` and `pageerror` to `qa-runs/run-NN/console.log`,
- records every API response that is not 2xx to `qa-runs/run-NN/http.log`,
- writes `qa-runs/run-NN/result.json` with the observed values (not pass/fail
  booleans — the actual numbers).

You then **open and look at the screenshots**. The script collects; your eyes judge.
Do not let the script's own assertions stand in for visual inspection.

### 4.2 The user journey (this is what the script drives)

1. Load `/` — register a fresh account (use a per-run email).
2. Navigate to `/qudit` via the **nav bar, by clicking** — not by typing the URL.
3. **Qudit Lab:**
   a. Set dimension to D (vary across runs: 2, 3, 4, 5).
   b. Add wires. Drag a gate from the palette onto the canvas.
   c. Run the simulation. Wait for results.
   d. Open the **Density Matrix Inspector**. Screenshot it.
   e. Enable a noise channel in the **Noise Panel**, re-run. Screenshot.
   f. Open the **Learn Panel**. Screenshot.
4. Navigate to `/composer`.
5. **Noise Lab:** build a Bell circuit (H on q0, CX q0→q1), enable a noise channel,
   run, compare ideal vs noisy. Screenshot the comparison.
6. **Smart Composer:** type a natural-language prompt, generate, inspect the result.
   Then simplify a deliberately redundant circuit (e.g. H·H) and inspect.
7. Navigate `/learn`, `/games`, `/dashboard` — confirm the new work did not break them.
8. Repeat the whole journey at a **narrow viewport (390 px)** on every 5th run.

**Vary across runs:** dimension D, gate set, wire count, noise channel and strength,
Smart Composer prompt, viewport width, and whether you hit Back/Refresh mid-flow.

### 4.3 Deliberate user stupidity (runs 1–10 especially)

Real users do these. Do them on purpose and report what happens:

- Click Run twice quickly / double-click buttons.
- Click Run with an **empty** circuit.
- Type nonsense into the Smart Composer ("make me a sandwich", 500 chars, emoji).
- Set a noise parameter to its extreme (0, 1, negative, huge).
- Remove a wire that has gates on it.
- Refresh mid-simulation.
- Press Back after generating.
- Submit a form with an empty required field.
- Rapidly switch tabs while a simulation runs.

A crash, a stuck spinner, a blank panel, or a 500 on any of these is a **defect**, not
user error.

---

## 5. What to look for — the vision checklist

For **every** screenshot, actively check for:

**Correctness (does it show the right thing?)**
- Do the displayed probabilities sum to ~1.0?
- Does the density matrix look physically valid (trace 1, Hermitian, |off-diagonal| ≤ 1)?
- Does the histogram match the numbers in the table beside it?
- Does the "ideal vs noisy" comparison actually differ when noise is on?
- Does the simplified circuit compute the same result as the original?
- Are labels, units and axis ticks correct and legible?

**Rendering (does it look right?)**
- Overlapping text, clipped content, elements off-screen.
- Contrast too low to read (especially amber/grey-on-dark warnings).
- Truncated numbers, scientific notation overflowing its box.
- Charts with wrong scale, missing legend, or all-zero data presented as meaningful.
- Empty panels that should have content; `NaN`, `undefined`, `Infinity`, `[object Object]` visible anywhere.
- Loading spinners that never resolve.

**State (is it honest about what's happening?)**
- Does the UI claim success when the request failed?
- Are errors explained in words a user understands, or is it a raw stack trace?
- When something is unsupported (too many wires, bad dimension), does it say so clearly?
- **Specifically:** when the qutrit preview is truncated, a banner must name both
  qubit counts. Confirm it appears, and confirm it does *not* appear when not truncated.

**Accessibility**
- Can you reach every control with Tab? Is focus visible?
- Are icon-only buttons labelled?
- Is the amber warning announced (it should carry `role="status"`)?

---

## 6. Running 30 times — and why

Thirty runs is not for coverage alone. It is to separate **deterministic** bugs from
**flaky** ones. A bug you see once in thirty is a different (and often worse) problem
than one you see thirty times out of thirty.

After the runs, classify every issue by frequency:

| Frequency | Meaning | Report as |
|---|---|---|
| 30/30 | Deterministic | `ALWAYS` — highest confidence |
| 5–29/30 | Intermittent | `FLAKY (n/30)` — race condition, timing, or state leak. **Report the exact n.** |
| 2–4/30 | Rare | `RARELY (n/30)` — report with the run numbers |
| 1/30 | One-off | `ONCE (run N)` — report; may be environmental |

For flaky issues, dig: is it timing, a race, leftover state between runs, or
server-side variance? Note whether the same input reproduces it.

Also report these computed across the 30 runs:
- console-error count per route (min / median / max)
- any run where a page failed to mount
- API non-2xx count, grouped by endpoint
- wall-clock time per journey step (median and max) — flag anything slow enough a
  user would notice

---

## 7. Severity

| | Meaning |
|---|---|
| **S1 — Blocker** | Wrong results, crash, data loss, or a feature that does not work at all. Would embarrass you in a live demo. |
| **S2 — Major** | Feature works but is misleading, badly broken visually, or fails on plausible input. |
| **S3 — Minor** | Cosmetic, or an edge case most users won't hit. |
| **S4 — Nit** | Polish. |

Be honest. Do not downgrade a real problem to make the report look better, and do not
inflate a nit into a blocker to look thorough.

---

## 8. Rules

1. **Do not fix anything.** You are reporting, not patching. Do not edit app source.
2. **Do not weaken or delete a test** to make something pass.
3. **Never mark a finding `PASS` without the screenshot that proves it.**
4. **Never invent a number.** If you did not observe it, it is not in the report.
5. **Report failures as failures.**
6. **Capture before you judge** — screenshot first, then decide whether it's a defect.
7. If a step cannot be completed, say so and say why. `NOT TESTED` is a valid and
   useful status; a guessed `PASS` is not.
8. **Save every artefact** under `qa-runs/`. Do not delete screenshots, even boring ones.
9. Leave the repo's own `git` state clean: commit nothing, push nothing.

---

## 9. Deliverables

### 9.1 `qa-runs/` directory

```
qa-runs/
  run-01/ … run-30/     # screenshots + console.log + http.log + result.json
  campaign.log          # one line per run: route timings, error counts, outcome
```

Name screenshots by step, e.g. `03-qudit-results.png`, `05-noise-compare.png`.

### 9.2 `docs/VISION_QA_REPORT.md`

```markdown
# Vision QA Report — commit 4116491
Runs: 30 · Date: <date> · Agent: vision

## Executive summary
<Roughly 15 lines. What is broken, what works, would you demo this tomorrow?>

## Environment
<Commands actually run. Deviations from §2.>

## Results by feature
### Qudit Lab
### Noise Lab
### Smart Composer
### Regression on existing routes

## Issue register
| ID | Feature | Severity | Frequency | Title | Evidence |
|----|---------|----------|-----------|-------|----------|
| VQ-01 | Qudit Lab | S1 | ALWAYS (30/30) | … | run-07/03-qudit-results.png |

<One row per issue. Every row links a screenshot.>

## Issue detail
### VQ-01 — <title>
- **Severity / Frequency:** S1 · ALWAYS (30/30)
- **Steps to reproduce:** 1, 2, 3…
- **Expected:** …
- **Observed:** … (the actual value, not "wrong")
- **Screenshot:** path
- **Root cause (if you can tell):** …

## Flakiness analysis
<For each FLAKY/RARELY issue: the n, the run numbers, and your hypothesis.>

## What I could NOT test
<Anything untested, and why.>

## Metrics across 30 runs
| Metric | Min | Median | Max |
|---|---|---|---|
| console errors / run | | | |
| API non-2xx / run | | | |
| journey wall-clock (s) | | | |
| pages failing to mount | | | |

## Recommendation
<Ship / do not ship / ship with these fixed first.>
```

### 9.3 Chat summary

Under 20 lines: how many issues by severity, the top 3 blockers, and whether you would
demo this tomorrow.

---

## 10. Definition of done

You are finished when **all** of these are true:

- [ ] 30 complete runs executed, artefacts saved for every one
- [ ] Every run covers all three features
- [ ] Narrow-viewport (390 px) runs included
- [ ] Deliberate-misuse cases exercised
- [ ] **You personally looked at screenshots from all 30 runs** — not a sample
- [ ] Every issue has a severity, a frequency, and a screenshot
- [ ] Flaky issues report their exact `n/30` and the run numbers
- [ ] Console errors and API failures counted per route
- [ ] The report file exists and matches the §9.2 template
- [ ] Nothing was fixed, no test was weakened, nothing was committed or pushed

If you run out of context mid-campaign, **say which runs are incomplete** rather than
reporting 30 when you did 18. An honest partial campaign beats a fabricated complete one.
