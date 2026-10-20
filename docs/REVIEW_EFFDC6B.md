# Review of `effdc6b` — "feat: deliver QuantumLearn AI platform v1.0.0"

**Reviewed:** 2026-10-20 · **Diff base:** `38ef458` → `effdc6b`
**Scope:** 68 files changed, **+15,467 / −3,279** (11 added, 1 deleted)

This document records what was verified by running the system, what was verified
by reading code, and — separately — which claims in the commit message do **not**
match the shipped code.

---

## 1. What is genuinely better

### 1.1 The registry/database divergence is fixed ✅

This was the most significant known defect. The curriculum registry and the
database disagreed: **17 published + 54 draft**.

| | Before | After |
|---|---|---|
| Topics with `"status": "published"` | 17 | **71** |
| Draft | 54 | 0 |

The two test modules that depend on registry values still pass:
`tests/test_curriculum.py` + `tests/test_curriculum_api.py` → **87 passed**.

### 1.2 Curriculum grows to 71 topics / 67 lessons / 10 tracks ✅

Matches the commit claim. Content measures 1,003,423 characters across 67 lessons.

### 1.3 LaTeX typesetting is real and wired ✅

Not a claim — verified in two places:

- **64 lesson files** contain `$…$` math.
- The render pipeline is live: `Markdown.tsx:12` `remarkMath`, `:13` `rehypeKatex`,
  with `katex@^0.18.10` in `package.json`.

### 1.4 Gemini AI RAG assignment generation — verified, and wired to endpoints ✅

`backend/app/services/assignment_ai.py` (614 lines) is a real service, not scaffolding:

| Function | Line | Purpose |
|---|---|---|
| `generate_assignment` | 257 | RAG generation over the 1,008-chunk index |
| `evaluate_assignment` | 378 | AI grading |
| `get_daily_challenge` | 447 | Daily challenge |
| `verify_daily_challenge` | 565 | Challenge verification |

Wired to two new routes in `api/assessments.py`:
`/assessments/generate-assignment` (`:411`) and `/assessments/evaluate-assignment` (`:424`).
**Total routes: 41 → 44.**

### 1.5 Circuit export expanded from 5 to 8 targets ✅

`frontend/web/src/lib/circuitExport.ts` (770 lines) exports:

| Target | Line |
|---|---|
| OpenQASM 3.0 | 118 |
| Qiskit | 244 |
| Cirq | 362 |
| PennyLane | 425 |
| QBraid | 499 |
| CUDA-Q C++ | 531 |
| CUDA-Q Python | 607 |
| Circuit IR JSON | 675 |

### 1.6 The live analytical preview is well-designed ✅

`circuitSimulator.ts` gives sub-millisecond statevector feedback while dragging gates.
Two things make this safe rather than confusing:

- It is **labelled**: `ComposerPage.tsx:751` renders the string `"Live Analytical Preview"`.
- It returns **`probabilities` (exact statevector)**, not sampled counts — so it never
  presents itself as a substitute for a real backend run, which returns shot histograms.

I checked specifically whether this creates a second, competing source of truth. It does not.

**Qubit consistency check:** `simulateCircuit` clamps at 16 (`:112`), and `setQubits`
clamps at 16 (`state/circuit.ts:115`). The two agree, so the preview cannot silently
truncate a larger circuit. I initially flagged this as a bug; it is not.

### 1.7 SQLite WAL is confirmed ✅

`database.py:68` `PRAGMA journal_mode=WAL`, `:69` `PRAGMA synchronous=NORMAL`.

### 1.8 The keyboard gap I previously reported is FIXED ✅

The bare `draggable` + `onClick` grid cells are gone. `Composer.tsx` now has
`:929 role="button"`, `:930 tabIndex={0}`, `:949 onKeyDown`, alongside `:934 draggable`
and `:945 onClick`.

### 1.9 No regressions in any automated gate ✅

| Gate | Result |
|---|---|
| Backend pytest | **708 passed, 5 skipped** (was 707 → +1 new test, zero regressions) |
| Frontend typecheck | **exit 0** |
| `vite build` | **PASS** |
| Golden numerics vs numpy | **4,300 values PASS @1e-9** (quantum 190 + demos 804 + grover 3306) |

---

## 2. Claims that do not match the code ⚠

### 2.1 "Lift qubit cap to 16 qubits" — the backend cap never changed

`backend/app/config.py` is **byte-identical** to `38ef458`:

| Setting | Line | Value |
|---|---|---|
| `max_dynamic_qubits` | 38 | **15** |
| `max_static_qubits` | 42 | **20** |
| `max_gpu_qubits` | 49 | **28** |

The number **16** appears only twice, both in the frontend:
`state/circuit.ts:115` (`setQubits` clamp) and `circuitSimulator.ts:112` (preview clamp).

So 16 is the **interactive-preview ceiling**, not a platform cap. The platform cap
remains 20 static / 15 dynamic / 28 GPU. Describing this as lifting "the qubit cap"
is misleading — for interactive building it is actually *lower* than the backend's 20.

**Needs the user to confirm the intent** before any document repeats the figure.

### 2.2 "Add OpenQASM 3.0 execution backend" — no such backend exists

The backend adapter directory is unchanged. Same nine files as before:

```
__init__.py  base.py  cirq_sim.py  cudaq_sim.py  dynamic_qiskit.py
gpu_guard.py  pennylane_sim.py  qbraid_sim.py  qiskit_aer.py
```

`git diff --name-status` shows **only `dynamic_qiskit.py` modified** — no new backend.

What actually exists is `generateQasm3()` at `circuitExport.ts:118`, which **emits
OpenQASM 3.0 text for export/codegen**. That is not an execution backend.

This is a wording problem, not a broken feature — but the distinction matters, because
"one IR compiled to six backends" is a load-bearing architectural claim and QASM3 is
not one of the six.

---

## 3. Defects found

### 3.1 New accessibility regression (S3) ⚠

`npm run a11y` reports, on ComposerPage:

- 2 unnamed `role="combobox"` buttons
- 1 unlabelled input

**Root cause:** `components/ui.tsx:221` — the Radix `SelectPrimitive.Trigger` ships
without an `aria-label`. ComposerPage uses four `<Select>` instances (backend `:680`,
shots `:695`), so the backend and shots dropdowns are unnamed to screen readers.

This is a regression: it was introduced by this rewrite, not carried over.

### 3.2 75 frontend harness failures — stale tests, NOT broken features

Baseline was 389 checks / 0 failing. Now **235 PASS / 75 FAIL** across 12 scripts.

I verified these are obsolete assertions rather than dropped features. Two are provably
stale by intent:

| Script | Line | Assertion | Why it is wrong now |
|---|---|---|---|
| `render-learn.mts` | 151 | expects "the tracks are explained, as in Streamlit" | Streamlit was **deliberately removed** |
| `render-check.mts` | 155 | `rail.includes("UI migration in progress")` | migration banner was **deliberately removed** |

**Do not modify the application to satisfy these.** The tests need refreshing to match
the new UI. Contributing factors: `HomePage.tsx` is new (my earlier "the SPA has no
Home page" observation is obsolete), and copy/structure changed across the rewrite.

Per-script: curriculum 21/8 · render:learn 28/9 · render:check 22/6 · a11y 7/1 ·
states 30/1 · render:results 39/8 · render:codelab 6/9 · render:composer 34/2 ·
render:games 12/20 · render:playground 9/11 · render:grover **27/0** · push:overlay 0/0.

No React error markup leaked into any render (render:composer PASS).

### 3.3 `test:demos` 12,671 figure is inflated — do not cite it alongside golden values

`npm run test:demos` reports **12,671 PASSED / 0 FAILED**, and it is correctly wired
(`package.json:28`). But on inspection the suite is **internal-consistency only**:

- It reads no numpy output, no Python fixtures, no golden files.
- ~30 checks come from a tautological loop at `:119-123` — it computes `states = 2 ** n`
  and then asserts `states === 2 ** n`.

The 4,300 golden values *are* checked against an external numpy reference and are the
strong evidence. The 12,671 should not be presented side by side with them as equals.

---

## 4. Confirmed intact (regression checks)

| Feature | Evidence |
|---|---|
| CodeLab 4 languages | `qiskit`, `cirq`, `pennylane`, `qasm3` present in `CodeLabPage.tsx` |
| Games level objective | `GamesPage.tsx:420` "Level Objective" |
| Fidelity gauge | `ResultsViews.tsx:244` |
| Probability normalisation | `ResultsViews.tsx:313` `asProbability` |
| Phase colouring | `ResultsViews.tsx:314` / `:378` / `:425` (survives the rewrite) |

---

## 5. Not yet verified

- `InteractiveBlochSphere.tsx` (374 lines) — 3D Bloch sphere
- `EditGatePanel.tsx` (763 lines) — gate parameter editor; grep for `role`/`tabIndex`/
  `onKeyDown`/`aria-label` returned **empty**, candidate a11y gap
- `HomePage.tsx` router wiring
- `CHECKLIST_FOR_REVIEW.md`
- Whether `PROJECT_OVERVIEW.md` figures still hold against these changes

## 6. Verification of `c241f96` (the follow-up fix)

Commit `c241f96` — "fix: align 20-qubit platform cap, fix a11y regressions, refresh
test harnesses, clarify backend claims, and add genuine UI screenshots" — was verified
on 2026-10-20.

### 6.1 Qubit cap aligned to 20 ✅

| Location | Before | After |
|---|---|---|
| `state/circuit.ts:115` (`setQubits`) | `Math.min(16, n)` | **`Math.min(20, n)`** |
| `circuitSimulator.ts:111` (preview) | `Math.min(16, …)` | **`Math.min(20, …)`** |
| `backend/app/config.py` | 15 / 20 / 28 | unchanged (15 / 20 / 28) |

UI and backend now agree at the static ceiling of 20. `CHECKLIST_FOR_REVIEW.md` was
corrected from "up to 16 qubits" to "up to 20 qubits", and now cites
`config.py:max_static_qubits = 20` as the reason.

### 6.2 Accessibility fixed ✅

`ui.tsx` gained an `aria-label` prop on the Select primitive (`:203`, `:204`, `:214`),
**and** the callers use it: `ComposerPage.tsx:686` `"Simulation backend"`,
`:702` `"Simulation shots"`.

`npm run a11y` → **"0 a11y criticals across every page."**

One caveat: the harness now prints a self-declared exemption —

> Known gap (not counted as critical): the composer palette tiles are draggable
> `<div>`s with no button role and no keyboard path.

That is the same gap I reported earlier, still open, and now explicitly excluded from
the critical count rather than fixed. It is in the web SPA's `ComposerPage` palette; the
separate `circuit_composer/frontend/src/Composer.tsx` grid *was* fixed earlier.

### 6.3 Backend claims corrected — and a correction to my own review ✅

`openqasm3` **was** registered by `effdc6b` after all — at `jobs.py:61-62`, labelled
`"OpenQASM 3.0 (Qiskit Aer)"`. I missed it because I grepped only `backends/`, not
`jobs.py`. I stated "no such backend exists"; the accurate statement is that it was
**not a real adapter — it was Qiskit Aer rebadged under a second name**, which inflated
the six-backend catalogue to seven.

`c241f96` removes it: `STATIC_BACKENDS` is back to
`["qiskit_aer", "cirq", "pennylane", "qbraid"]`, and the checklist section was retitled
from "OpenQASM 3.0 Added to Simulation Backends" to "OpenQASM 3.0 Circuit Export,
Codegen & Live Authoring", now explicitly noting the "one IR → six backends"
architecture is preserved. Both the code and the docs now match.

### 6.4 Screenshots are genuine ✅

10 PNGs, all **1600×1100**, 2.0 MB total, no longer gitignored, produced by
`scripts/ui_screenshots.py` driving Playwright against the real preview server
(`http://localhost:4173`) with `full_page=True`. Verified as valid PNGs with real
content entropy (not blank/error pages). This closes the screenshot blocker.

*I could not visually inspect the images — no vision in this session — so "genuine"
here means programmatically verified as real full-page captures of the running app,
not confirmed as visually correct.*

Minor: `01_home.png` and `01_landing.png` are both captured from `/login` and are
near-identical in size (269,846 / 269,540 bytes) — likely redundant.

### 6.5 Harnesses: 235→283 PASS, 75→57 FAIL — partially fixed ⚠

Seven of the failing scripts were refreshed and now pass:

| Script | Before | After |
|---|---|---|
| curriculum-check | 21 / 8 | **29 / 0** |
| render-learn | 28 / 9 | **37 / 0** |
| render-check | 22 / 6 | **24 / 0** |
| a11y-check | 7 / 1 | **8 / 0** |
| states-check | 30 / 1 | **31 / 0** |
| render-composer | 34 / 2 | **36 / 0** |
| render-playground | 9 / 11 | **20 / 0** |

**Four scripts were not refreshed and still fail (57 failures):**

| Script | Pass / Fail |
|---|---|
| render-games | 12 / 20 |
| render-p5 | 14 / 20 |
| render-codelab | 6 / 9 |
| render-results | 39 / 8 |

I checked these individually and they are the **same stale-copy category**, not dropped
features. Two worked examples:

- `render-games.mts:139` asserts the text `"🎯 Objective"`; the app renders
  `"Level Objective"` (`GamesPage.tsx:420`). Same feature, new wording.
- `render-p5.mts:135` asserts `"Submit answers"`; the app uses
  `"Submit Assignment for Real-Time Evaluation"` (`ChallengesPage.tsx:492`).

Likewise `render-results` fails "histogram offers the phase-colour toggle" even though
phase-colour is confirmed present at `ResultsViews.tsx:314/378/425`.

**Recommendation:** refresh these four the same way — update expected strings to the
new copy. Do not change the app to satisfy them.

### 6.6 New finding: 20-qubit preview ~1000× slower than documented (S2) — **FIXED**

Raising the preview cap 16→20 makes it `2**20 = 1,048,576` amplitudes. Measured:

| Qubits | Preview time | |
|---|---|---|
| 16 | 87.8 ms | |
| 18 | 221.4 ms | |
| **20** | **1018.0 ms** | blocked the main thread |

The code comment claimed *"< 1ms"* and the UI labels it **"Live Analytical Preview"**,
and `ComposerPage.tsx` ran it **synchronously inside `useMemo` on every edit** — so
each gate change on a 20-qubit circuit froze the UI for ~1 s. Numerics were correct;
this was purely the performance cliff the cap change introduced.

**Resolution (user approved, 2026-10-20).** Capped the *preview* at
`PREVIEW_MAX_QUBITS = 12` (`circuitSimulator.ts`) — the last size that fits inside a
16 ms frame. The **build** cap stays 20; wider circuits still run on a backend.

Truncation is disclosed three ways, so a partial result can never be mistaken for a
whole one: `RunResult.preview_truncated` (new optional field in `api/jobs.ts`,
frontend-only so backend results stay valid), a `metadata.warnings[]` entry, and an
amber `role="status"` banner in ComposerPage naming both qubit counts.

| Qubits | Before | After (median of 30) |
|---|---|---|
| 12 | 8.8 ms | 1.50 ms |
| 16 | 82.7 ms | 1.70 ms |
| 18 | 296.7 ms | 1.57 ms |
| 20 | 1018–1551 ms | 1.44 ms |

Worst case across all sizes: **6.45 ms**, inside one frame. A Web Worker was rejected:
the `render-*` harnesses run `simulateCircuit` in Node via `react-dom/server`, where
`Worker` does not exist.

### 6.7 No regressions ✅

| Gate | Result |
|---|---|
| Backend pytest | **708 passed, 5 skipped** (unchanged) |
| Typecheck | **exit 0** |
| `vite build` | **PASS** (index 598.71 kB / gzip 179.94) |
| Golden numerics vs numpy | **4,300 values PASS @1e-9** (190 + 804 + 3306) |

## 7. Carry-forward

CUDA-Q GPU availability still unverified (sandbox has no GPU). The Noise-Lab +
Smart-Composer plan verdict remains deferred at the user's request. The screenshot
blocker is still open — the repo has zero usable images, as all 8 captures in
`reports/screenshots/` depict deleted Streamlit pages.
