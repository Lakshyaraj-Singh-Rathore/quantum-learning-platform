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

## 6. Carry-forward

CUDA-Q GPU availability still unverified (sandbox has no GPU). The Noise-Lab +
Smart-Composer plan verdict remains deferred at the user's request. The screenshot
blocker is still open — the repo has zero usable images, as all 8 captures in
`reports/screenshots/` depict deleted Streamlit pages.
