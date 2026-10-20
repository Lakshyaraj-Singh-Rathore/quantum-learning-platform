# Test list — vision/execution agent

**Written:** 2026-10-20 · **Target commit:** `21a9f14` ("Qudit Lab (Beta), Noise Lab, Smart Composer")
**Companion to:** `docs/HANDOFF_VISION_AGENT.md` (roles, constraints, traps — read that first)

## ⚠ First: your predecessor's work was NOT overwritten

Checked before writing this. The earlier perf fix is present **and functional** in
`21a9f14`:

| Check | Result |
|---|---|
| `PREVIEW_MAX_QUBITS` in `circuitSimulator.ts` | present (2 refs), enforced at `:138` |
| `preview_truncated` in `api/jobs.ts` | present |
| truncation banner in `ComposerPage.tsx` | present, live at `:787` |
| `docs/HANDOFF_VISION_AGENT.md`, `docs/REVIEW_EFFDC6B.md` | both present |

**Do not re-do it.** If you find the preview slow again, measure first — see T-P1.

---

## 0. Verified baseline (measure against this)

All measured on `21a9f14`, 2026-10-20. If you get different numbers, **you have found
something** — report it, don't assume you mis-ran it.

| Gate | Baseline |
|---|---|
| Backend pytest | **818 passed, 5 skipped** (~112 s) |
| API paths (OpenAPI) | **58** |
| Frontend typecheck | **exit 0** |
| `vite build` | **PASS** — index 638.08 kB / gzip 187.17 kB |
| Frontend harnesses | **284 PASS / 57 FAIL** |
| Golden numerics vs numpy | **4,300 values @1e-9** (quantum 190 + demos 804 + grover 3306) |
| a11y harness | **0 criticals** |

The 57 failures are **known-stale copy assertions** in exactly four scripts:
`render-games` (20), `render-p5` (20), `render-results` (8), `render-codelab` (9).
They are T-A4 below. Treat any *other* failing script as a new defect.

### Known-good API behaviour

```
/qudit/limits  -> supported_dimensions [2,3,4,5]
                  safe_limits     {"2":10,"3":6,"4":5,"5":4}
                  expanded_limits {"2":12,"3":7,"4":6,"5":5}
                  memory_formula "M = 16 * D^2 bytes (complex128)"

/qudit/simulate  qutrit D=3, wires [q0,q1] both dim 3, X on wire 0
              -> probabilities {"|1,0⟩": 1.0}  (all 8 others 0.0)

/noise/simulate  Bell, noise_config {}                      -> fidelity 1.0000, TVD 0.0000
/noise/simulate  Bell, decoherence{t1:50,t2:30}             -> fidelity 0.9866, TVD 0.0244
/noise/simulate  Bell, stochastic{depolarizing_2q:0.2}      -> fidelity 0.8500, TVD 0.1001

/smart-composer/generate  {"prompt":"create a bell state","n_qubits":2}
              -> circuit named "Bell |Φ+>", keys: circuit, metrics,
                 task_spec, passed_tests, assumptions, repair_attempts, explanation

/smart-composer/simplify  H·H on 1 qubit -> job_id "simp_…"
```

---

## 1. Setup

### ⚠ Work from `main` only — user decision, 2026-10-20

**The branch `arena/01a0d874-…` is no longer a push target.** Push target is
`origin HEAD:main` and nothing else.

Background: `main` is an orphan root, so branch and main can never be merged
normally, and keeping both in sync required a fragile patch-and-apply dance. On
2026-10-20 the user chose **main only**.

What this means in practice:

- The local branch name still exists (the session harness tracks it), but it is
  **pointed at `main`'s content** and its upstream is `origin/main`, so plain
  `git push` targets main.
- Verify with `git rev-parse HEAD` and `git rev-parse origin/main` — they should
  be equal. If they are not, **stop and ask**; do not push.
- `origin/arena/01a0d874-…` is left at `da00136` and is now **stale — do not push
  to it and do not read it as current.** Content-wise nothing was lost: main
  contains every file the branch had (zero deletions across the switch).
- Never force-push, and never push to the branch ref.

```bash
cd /home/user/quantum-learning-platform
git fetch --all --prune
git reset --mixed origin/main
git checkout -f HEAD            # REQUIRED — reset --mixed does not create new files
python3 -m venv /home/user/.venv-ql
/home/user/.venv-ql/bin/pip install -q -r backend/requirements.txt pytest
cd frontend/web && npm install && node scripts/link-shared.mjs
```

Push with: `git push origin HEAD:main`

```bash
# API (SQLite; no Postgres/Redis needed for these paths)
cd backend && DATABASE_URL="sqlite:///./qa.db" PYTHONPATH=. \
  /home/user/.venv-ql/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Frontend
cd frontend/web && VITE_ALLOWED_HOSTS=<host> npx vite preview --host 0.0.0.0 --port 4173
```

Auth: `POST /auth/register` → token. (`/auth/login` form-encoded returned none.)
**`/jobs` needs Redis** — without it you get `"Could not enqueue job"`. That is an
environment limit, not a defect; do not report it.

---

## 2. Suite A — baseline regression

| ID | Test | Expected | Evidence |
|---|---|---|---|
| A1 | `pytest -q` in `backend/` | **818 passed, 5 skipped** | pytest tail |
| A2 | `npx tsc --noEmit` | exit 0 | output |
| A3 | `npx vite build` | PASS | build tail |
| A4 | All harness scripts | **284 PASS / 57 FAIL**, failing set = exactly the 4 known scripts | per-script table |
| A5 | 3 golden scripts | 4,300 values @1e-9 | script tails |
| A6 | `npm run a11y` | 0 criticals | script tail |
| A7 | `curl /openapi.json \| paths` | **58** | count |

**A8 — the perf regression guard (new).** Run the preview at 2/5/8/10/12/14/16/18/20
qubits, median of 30 runs with JIT warmup. Record `preview_truncated`.
Expected: every size ≤ ~7 ms median, worst case ≤ ~7 ms, and `truncated = true` for
>12. If 20 qubits exceeds ~50 ms, the `PREVIEW_MAX_QUBITS` cap has been bypassed —
report as S2.

---

## 3. Suite B — Qudit Lab (new)

6 endpoints, 8 backend modules, 21 unit tests. Correct request shapes (I verified
these; the flat form is silently ignored):

```jsonc
// POST /qudit/simulate
{"circuit": {"version":"1.0","id":"t1","name":"x","dimension":3,
             "wires":[{"id":"q0","index":0,"dimension":3,"initial_state":0}],
             "ops":[{"id":"op1","gate":"x","targets":[0],"controls":[],
                     "params":{},"dimension":3}]},
 "shots":1024, "calculate_entropy":true}
```

| ID | Test | Expected | Sev |
|---|---|---|---|
| B1 | `GET /qudit/limits` | dims [2,3,4,5]; safe/expanded limits as in §0 | S2 |
| B2 | `GET /qudit/catalogue` | 200, non-empty gate list per dimension | S2 |
| B3 | `GET /qudit/presets` | 200, valid circuits | S3 |
| B4 | `POST /qudit/validate` — valid circuit | no errors | S2 |
| B5 | `POST /qudit/validate` — gate on `dimension` 6 | **rejected** (le=5) | S2 |
| B6 | `POST /qudit/validate` — op targeting a non-existent wire | **rejected** | S2 |
| B7 | `POST /qudit/validate` — wire count over safe limit | rejected, or accepted with an explicit warning naming the limit | S2 |
| B8 | `POST /qudit/simulate` — qutrit X on \|0⟩ | `{"\|1,0⟩": 1.0}` | **S1** |
| B9 | `POST /qudit/simulate` — qudit X on D=4, D=5 | X\|0⟩ = \|1⟩ each | **S1** |
| B10 | Two-qudit `sum` (CX analogue) → Bell-like state | correct two-qudit amplitudes | **S1** |
| B11 | `calculate_entropy: true` on a product state | entropy ≈ 0 | S2 |
| B12 | `calculate_entropy: true` on a maximally entangled 2-qudit state | entropy ≈ log2(D) | S2 |
| B13 | Depolarizing noise enabled | probabilities spread; purity < 1 | S2 |
| B14 | Dephasing noise enabled | populations ~unchanged, **coherences shrink** | S2 |
| B15 | Relaxation noise enabled | population migrates toward \|0⟩ | S2 |
| B16 | `POST /qudit/slice` | returns the requested matrix slice, correct dims | S3 |
| B17 | **Mixed dimensions** — wire0 D=2, wire1 D=3 | simulates; total_dim = 6 | **S1** |
| B18 | Mixed-dim `sum` gate across different D | rejected **or** documented — must not silently mis-simulate | **S1** |
| B19 | Circuit with 0 ops | returns \|0…0⟩ at 1.0, no crash | S3 |
| B20 | Circuit at the safe limit for D=2 (10 qudits) | completes or refuses **explicitly** — never a silent wrong answer | S2 |
| B21 | Circuit **over** the limit | clean refusal naming the limit, not a timeout/OOM | S2 |
| B22 | `POST /qudit/simulate` with a **flat/incorrect** config | **see T-G3** — currently silently ignored | S2 |
| B23 | Numerical check: simulate 3+ known qutrit circuits, compare to an independent numpy reference | agree to 1e-9 | **S1** |

**B23 is the important one.** The 21 shipped unit tests are self-consistent. Qudit Lab
has **no independent numerical reference** — the qubit side has 4,300 golden values,
the qudit side has none. Write `scripts/golden-qudit.mts` against numpy.

---

## 4. Suite C — Noise Lab (new)

5 endpoints, 7 backend modules, 20 unit tests.

```jsonc
// POST /noise/simulate  — NOTE: nested, and every block defaults to enabled:false
{"circuit_ir": {...},
 "noise_config": {"decoherence":{"enabled":true,"t1_us":50,"t2_us":30},
                  "stochastic":{"enabled":true,"depolarizing_2q":0.2}},
 "shots":2048, "seed":7}
```

| ID | Test | Expected | Sev |
|---|---|---|---|
| C1 | `GET /noise/catalogue` | 200; channels with id, category, formula, valid_range | S3 |
| C2 | `GET /noise/presets` | 200, valid configs | S3 |
| C3 | `POST /noise/validate` — T2 > 2·T1 | **rejected** (unphysical; `t_phi_us` becomes null) | **S1** |
| C4 | `POST /noise/validate` — negative T1 | rejected | S2 |
| C5 | `POST /noise/validate` — probability > 1 | rejected | S2 |
| C6 | `POST /noise/simulate` — all disabled | `ideal == noisy`, fidelity 1.0, TVD 0.0 | S2 |
| C7 | decoherence t1=50, t2=30 | fidelity ≈ **0.9866**, TVD ≈ **0.0244** | S2 |
| C8 | stochastic `depolarizing_2q`=0.2 | fidelity ≈ **0.8500**, TVD ≈ **0.1001** | S2 |
| C9 | **Monotonicity**: depolarizing 0.0→0.1→0.2→0.4 | fidelity decreases monotonically | **S1** |
| C10 | **Seed reproducibility**: same seed twice | byte-identical counts | **S1** |
| C11 | Different seeds | different counts, same distribution | S3 |
| C12 | `readout` error only | odd-parity leakage on Bell; **no** coherence loss | S2 |
| C13 | `coherent` (over/under-rotation) | targeted deviation, not random spread | S2 |
| C14 | `correlated` noise | correlated errors, not independent | S2 |
| C15 | All channels at max | no crash; result stays a valid distribution (sums to 1) | **S1** |
| C16 | `POST /noise/sweep` | returns one point per parameter value | S2 |
| C17 | Sweep monotonicity | metric trends monotonically in the swept parameter | S2 |
| C18 | `simulation_method` explicit: density_matrix / statevector / stabilizer | each produces a valid result | S2 |
| C19 | Method `automatic` picks a sane method | `method_used` is reported and appropriate | S3 |
| C20 | Large circuit + noise | completes or refuses explicitly | S2 |
| C21 | Purity/trace of the returned density matrix | trace = 1.0 ± 1e-9; purity ≤ 1 | **S1** |
| C22 | **Numerical check** vs an independent numpy/Qiskit Aer reference | agree to 1e-9 | **S1** |

---

## 5. Suite D — Smart Composer (new)

4 endpoints, 9 backend modules, 20 unit tests.

| ID | Test | Expected | Sev |
|---|---|---|---|
| D1 | `GET /smart-composer/rules` | 200; rules with id, formula, category (e.g. `R01_INV_CANCEL`) | S3 |
| D2 | `POST /generate` — "create a bell state", 2q | returns Bell \|Φ+⟩; `passed_tests` non-empty | **S1** |
| D3 | `POST /generate` — GHZ, 3q | correct GHZ | **S1** |
| D4 | `POST /generate` — nonsense prompt | **fails gracefully**; no fabricated circuit presented as valid | **S1** |
| D5 | `POST /generate` — asks for more qubits than allowed | clean refusal | S2 |
| D6 | `POST /simplify` — H·H | cancels to identity | **S1** |
| D7 | `POST /simplify` — X·X, CX·CX | cancels | S2 |
| D8 | `POST /simplify` — circuit with **no** reducible pairs | returns essentially unchanged; says so | S2 |
| D9 | `POST /simplify` — already-optimal circuit | no false "improvement" | S2 |
| D10 | **Semantic equivalence**: simplify 10 circuits, run original vs simplified on all 4 working backends | identical distributions within sampling error | **S1** |
| D11 | `POST /simplify` — verify against deterministically generated random circuits | equivalence holds | **S1** |
| D12 | `GET /jobs/{job_id}` | returns the job; unknown id → clean 404 | S3 |
| D13 | `GET /jobs/{bad_id}` | 404, not 500 | S3 |
| D14 | Generate then immediately simplify | pipeline composes | S2 |
| D15 | `explanation` field | non-empty, matches what was actually done | S3 |
| D16 | `assumptions` field | lists assumptions rather than hiding them | S3 |
| D17 | RAG path with `GEMINI_API_KEY` unset | keyword fallback; result still valid, degradation disclosed | S2 |
| D18 | Deterministic mode vs RAG mode | both produce **valid** circuits | S2 |
| D19 | Round-trip: generate → validate → simulate → simplify | no state corruption | S2 |
| D20 | **Adversarial**: circuit the verifier *should* reject | rejected, not silently accepted | **S1** |

**D10/D11 are the load-bearing tests.** The Smart Composer's whole claim is that it
rewrites circuits *without changing what they do*. Unit tests on hand-picked cases
cannot establish that; differential execution can.

---

## 6. Suite E — visual / UI (vision-only; nobody has ever looked at this app)

Routes: `/`, `/learn`, `/curriculum`, `/playground`, `/composer`, `/qudit`, `/code-lab`,
`/challenges`, `/games`, `/dashboard`. (`/qudit` is new.)

For **every** route:

| ID | Test | Expected | Sev |
|---|---|---|---|
| E1 | Load in a real browser | HTTP 200, React mounts (non-trivial body text) | **S1** |
| E2 | Capture console | **zero** `error` / `pageerror` | **S1** |
| E3 | Screenshot at 1440 px | full-page capture saved | S3 |
| E4 | Screenshot at 390 px | layout survives; no horizontal overflow | S2 |
| E5 | **Look at it** | report overlap, clipping, unreadable contrast, empty panels, wrong data | S2 |
| E6 | Loading/empty/error states | not blank; a message is shown | S3 |

Route-specific:

| ID | Test | Expected | Sev |
|---|---|---|---|
| E7 | `/qudit` — build a qutrit circuit in the editor | palette, editor, results all render | **S1** |
| E8 | `/qudit` — `DensityMatrixInspector` | matrix/heatmap legible; magnitudes and phases distinguishable | **S1** |
| E9 | `/qudit` — `QuditNoisePanel` | controls map to backend noise params | S2 |
| E10 | `/qudit` — `QuditLearnPanel` | explanatory content renders (LaTeX via KaTeX) | S3 |
| E11 | `/composer` — build >12 qubits | amber truncation banner visible, names both counts | **S1** |
| E12 | `/composer` — ≤12 qubits | **no** banner | S2 |
| E13 | `/composer` — Noise Lab tab | renders, simulates, plots | **S1** |
| E14 | `/composer` — Smart Composer panel | renders; generate/simplify usable | **S1** |
| E15 | `/learn` — LaTeX | renders as maths, not raw `$…$` | S2 |
| E16 | Results views — histogram, Q-sphere, phase colour | all render with real data | S2 |
| E17 | Existing screenshots in `reports/screenshots/` | regenerate; confirm they match reality. `01_home` and `01_landing` are both from `/login` and near-identical in size — **confirm and report whether one is redundant** | S3 |

Two browser-verify scripts already exist
(`scripts/browser-verify-qudit-lab.mjs`, `scripts/browser-verify-matrix-view.mjs`) —
**run them, and report whether they are genuine verification or tautological**, in the
manner of `verify-all-demos.mts`.

---

## 7. Suite F — accessibility

| ID | Test | Expected | Sev |
|---|---|---|---|
| F1 | `npm run a11y` | 0 criticals | S2 |
| F2 | **The excluded gap**: composer palette tiles are draggable `<div>`s with no button role and no keyboard path. The harness prints this as a "known gap (not counted as critical)". | Confirm still present; **recommend whether to promote it to a real critical** | S2 |
| F3 | Every form control has a label | all named | S2 |
| F4 | Full keyboard traversal of `/composer` and `/qudit` | everything reachable by Tab | S2 |
| F5 | New Qudit/Noise/Smart-Composer panels | labelled controls, keyboard-operable | S2 |
| F6 | Truncation banner | `role="status"`, announced by a screen reader | S3 |

---

## 8. Suite G — cross-cutting / robustness

| ID | Test | Expected | Sev |
|---|---|---|---|
| G1 | Auth required on new endpoints | 401/403 without a token | S2 |
| G2 | Auth on `/qudit/*`, `/noise/*`, `/smart-composer/*` | consistent — **report any that are unprotected** | S2 |
| G3 | **Silent-ignore trap** — send a *flat/incorrect* `noise_config` (e.g. `{"t1_us":100}` at top level) | **Currently: silently ignored → a plausible-looking noiseless result.** I hit this myself. Should error or warn. | **S1** |
| G4 | Same trap on `/qudit/simulate` | same expectation | S2 |
| G5 | Malformed `circuit_ir` | 4xx, not 500 | S2 |
| G6 | `shots` out of range (0, 99999) | 4xx with a clear message | S3 |
| G7 | Concurrent requests | no cross-talk between results | S2 |
| G8 | Very large payload | clean refusal, not a hang | S2 |

**G3 is a genuine finding, not a mis-test.** I initially reported Noise Lab as broken
because of it. A user who typos their noise config gets a confident noiseless answer
with no warning. That is the same failure class as the earlier malformed-job-payload
trap.

---

## 9. Suite H — performance

| ID | Test | Expected | Sev |
|---|---|---|---|
| H1 | Preview 2–20 qubits (T-A8) | all ≤ ~7 ms | S2 |
| H2 | `/qudit/simulate` at each safe limit | completes or refuses explicitly | S2 |
| H3 | `/noise/sweep` with a wide range | completes in reasonable time | S3 |
| H4 | `/smart-composer/generate` | returns promptly; slow path uses the job API | S2 |
| H5 | Page load time per route | report actuals | S3 |
| H6 | Memory at max qudit limit | stated budget (2 GiB default) respected | S2 |

---

## 10. Task queue

| # | Task | Suite | Notes |
|---|---|---|---|
| T-A4 | Refresh the 4 stale test scripts | A4 | **Test bugs, not app bugs.** Change expected strings; never the app. Proof required per change (old string → new string → app line). Seven sibling scripts were already fixed this way. |
| T-B23 | Write `golden-qudit.mts` vs numpy | B23 | Qudit Lab has no independent numerical reference. Highest-value new test. |
| T-D10 | Differential execution for Smart Composer | D10/D11 | Proves simplify preserves semantics. |
| T-E | Full visual pass, all 10 routes | E | The core reason a vision agent exists. |
| T-G3 | Make bad config raise instead of silently passing | G3 | Suggest `model_config = ConfigDict(extra="forbid")` — **ask the senior agent first**, it may break existing clients. |
| T-C22 | Noise Lab numerical reference | C22 | Independent check of the noise channels. |
| T-H | Performance suite | H | Wire into `package.json` with thresholds. |

**Do T-A4 first** — it makes the suite readable, so later regressions are visible.

---

## 11. Automation mandate (recap)

The user does the manual testing. **Your job is to make it unnecessary.**

- Every hand-found defect → a script that catches it next time.
- Every new script → wired into `package.json` (verify the name; don't assume).
- Every new check → **proven able to fail** (break the thing it guards, confirm red, revert).
- Compare against an **independent reference** (numpy, fixture, API) — never against
  your own arithmetic. `verify-all-demos.mts` is the cautionary example: 12,671 passing
  checks, ~30 of them tautological (`:119-123` asserts `states === 2 ** n` having just
  set `states = 2 ** n`), and no external reference anywhere.
- Never weaken an existing test.

## 12. Statuses and reporting

Four statuses only: **PASS** · **FAIL** · **PARTIAL** · **NOT TESTED**.
Every FAIL gets **S1** (blocks release) · **S2** (major) · **S3** (minor) · **S4** (cosmetic).
Every finding cites **file and line**. Every visual finding includes a **screenshot**.

Report per suite, then stop and wait. Do not push to `main`. Do not self-approve.

If you did not run it, it is **NOT TESTED** — not PASS.
