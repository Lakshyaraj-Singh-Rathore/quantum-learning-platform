# Phase 0 Report — Audit and Baseline

**Phase:** 0 — audit and baseline. **No feature code was written.**
**Commit audited:** `648dec4`, tree byte-identical to `origin/main @ 12d33df`.
**Branch deviation (D-001):** work is committed to `arena/63ae45b4-quantum-learning-platform`, which
carries `main`'s exact tree. Nothing is pushed to `main`. Reason and resolution in
[`DECISIONS.md`](./DECISIONS.md#d-001--branch-session-branch-carrying-mains-tree).

**Deliverables:** [`00-audit.md`](./00-audit.md) · [`ui-audit.md`](./ui-audit.md) ·
[`DECISIONS.md`](./DECISIONS.md) · this report.

---

## 1. Gate evidence

Every gate below was executed in this session. Output is pasted, not paraphrased.

### Backend tests — PASS (matches baseline)

```
$ cd backend && PYTHONPATH=. python -m pytest -q
818 passed, 5 skipped in 117.75s (0:01:57)
```

### Typecheck — PASS (matches baseline)

```
$ cd frontend/web && npm run typecheck
> node scripts/link-shared.mjs && tsc --noEmit
[link-shared] react -> ../web/node_modules/react
[link-shared] react-dom -> ../web/node_modules/react-dom
[link-shared] @types -> ../web/node_modules/@types
[link-shared] skipped streamlit-component-lib: not installed in frontend/web
GATE_EXIT=0
```

0 errors. **Must be run as `npm run typecheck`** — bare `npx tsc --noEmit` skips `link-shared.mjs` and
produces spurious `TS2307 Cannot find module 'react'` errors in `circuit_composer`. That is an invocation
artefact, not a defect (`00-audit.md` §2.2).

### Production build — PASS (matches baseline)

```
$ cd frontend/web && npx vite build
✓ 2090 modules transformed.
dist/assets/index-DBP-lwNT.css   163.40 kB │ gzip:  30.94 kB
dist/assets/index-CoImnjWX.js    639.18 kB │ gzip: 187.58 kB
✓ built in 9.87s
```

### Goldens — PASS (matches baseline, 1e-9)

```
$ npm run golden:quantum   → ALL CHECKS PASSED — 190 values agree with numpy (1e-9)
$ npm run golden:demos     → ALL CHECKS PASSED — 804 demo values agree with numpy (1e-9)
$ npm run golden:grover    → ALL CHECKS PASSED — 3306 Grover values agree with numpy (1e-9)
```

### a11y — PASS (matches baseline)

```
$ npm run a11y
0 a11y criticals across every page.
```

### Harness loop — PASS (matches baseline: 284 / 57)

20 scripts, tallied per script in `00-audit.md` §2.1.

```
TOTAL   PASS=284   FAIL=57
```

The 57 are exactly `render-codelab` (9) + `render-games` (20) + `render-p5` (20) + `render-results` (8).
Pre-existing; not to be fixed or counted as regressions. The forward gate is **the same four scripts with
the same counts and no new failing script**.

`push-overlay-check` is **BLOCKED (environment)**, not failing — see D-010. `smoke-auth` (13 PASS) and
`smoke-composer` (10 PASS) require `API_TARGET=http://127.0.0.1:8000`; their default target is port 8123.

### API surface — PASS (matches baseline)

```
all routes      : 62
APIRoute only   : 58
built-ins       : ['/docs', '/docs/oauth2-redirect', '/openapi.json', '/redoc']
qml paths       : none (expected at baseline)
```

The documented 58 counts `APIRoute` objects; the raw 62 includes FastAPI's four built-in doc routes.
Counting method, not a discrepancy.

### Entry conditions — PASS

```
HEAD:        648dec4
origin/main: 12d33df
trees identical: YES
dirty files: 0
tracked file count: 531
```

No deleted Streamlit path has been resurrected (all six confirmed absent).

### Migration chain — PASS

`alembic upgrade head` applied all 8 revisions in order on a fresh SQLite DB, confirming the chain is
linear with head `h3c6d9e2f5a8`:

```
b5f10b499a50 → c7a2e4d19b30 → d8b3f6c02a11 → e9c4a7d31b22
→ f1a2b3c4d5e6 → a2b3c4d5e6f7 → g2a5b8c1d4e7 → h3c6d9e2f5a8
```

---

## 2. Summary

| Gate | Baseline | Measured | Verdict |
|---|---|---|---|
| Backend tests | 818 / 5 skipped | 818 / 5 skipped | MATCH |
| Typecheck | 0 errors | 0 errors | MATCH |
| Build | PASS ~2090 modules | PASS 2090 modules | MATCH |
| Harnesses | 284 / 57 | 284 / 57 | MATCH |
| Goldens | 190 + 804 + 3306 | 190 + 804 + 3306 | MATCH |
| a11y | 0 criticals | 0 criticals | MATCH |
| API routes | 58 | 58 | MATCH |

**All seven gates match. No §5.5 stop condition fires. Phase 1 is clear to start.**

---

## 3. Findings beyond the baseline

Four things were **proven by execution** rather than assumed, because each one determines a Phase 1 design
decision:

1. **The no-torch path works.** parameter-shift vs backprop gradients agree to **2.220e-16**, `torch` not
   imported, numpy still 1.26.4. → D-003, D-004.
2. **The §7 nested-config trap is real.** A flat `NoiseConfig` payload is silently accepted and every noise
   group comes back `enabled: False` — a plausible wrong answer with no error. → D-006 (`extra="forbid"`).
3. **The `bg-card` trap is real in the shipped bundle.** Used in 6 files, it emits **0** rules in
   `dist/assets/*.css`, while `bg-raised`, `bg-subtle` and `text-ink-3` each emit 1. → `ui-audit.md` §1.3.
4. **There is no cancellation precedent.** No Celery `revoke`, no cancel endpoint anywhere in the backend.
   → D-007 (cooperative cancellation designed from scratch).

A fifth item is recorded but **not acted on**: PennyLane 0.44.1 warns that it has dropped maintenance
support for numpy < 2.0, while `cirq-core 1.4.1` requires numpy < 2. The pins do not move under this task.

---

## 4. Stated limits of this phase

1. **Per-task Celery limits are unverified on Windows `--pool=solo`.** This sandbox is Linux; the target
   machine is Windows + PowerShell 5. P2 will prove the Linux half and say so explicitly.
2. **No Redis or Celery worker was run.** The API ran with `CELERY_TASK_ALWAYS_EAGER=true`. P2 must cover
   both the eager path and a real broker.
3. **`push-overlay-check` could not be executed meaningfully** (D-010).
4. **The 531 vs 530 file count is unexplained by `git`** because `12d33df` is a root commit (D-011).
5. **No GPU/CUDA-Q work** was attempted — out of scope unless asked.

---

## 5. Next — Phase 1 (backend QML engine, no API, no UI)

In order, each with tests alongside and the full baseline re-run before commit:

1. `config.py` — strict schema, `extra="forbid"`, all limits from `00-audit.md` §5.3.
2. `datasets.py` — seeded moons / circles / binary-iris; **scaler fitted on the train split only**.
3. `encoding.py`, `circuits.py` — angle encoder and variational ansatz.
4. `model.py` — VQC predicting from real measurements.
5. `trainer.py` — minibatch loop, real loss, progress + cancel callbacks, fully seeded.
6. `evaluator.py`, `baseline.py`, `manager.py` (JSON + npz, **never pickle**), `resources.py`.

Phase 1 exits only when all nine QNN acceptance criteria are demonstrated with pasted output — including
save → reload → **identical** predictions, and backprop/parameter-shift gradient agreement on a real
circuit.
