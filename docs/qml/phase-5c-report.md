# Phase 5c — the QML Lab UI reaches all four algorithms

**Scope:** §2E. Frontend only. **Backend files changed: 0** (verified, not asserted —
`git diff --name-only origin/main -- backend/` returns nothing, and the working tree has no
staged or unstaged backend change either).

**Base:** `origin/main @ 42ced54`, merged into the working branch at `bc09695`.

---

## 1. What shipped

| WP | Deliverable | State |
| --- | --- | --- |
| 1 | `api/qml.ts` rewritten: discriminated unions on `task`, nullable fields typed `number \| null`, `algorithms[]` added to `QmlDescribe` | **done** |
| 2 | Configuration view driven by `/qml/describe`; per-algorithm limits and datasets; switching invalidates an incompatible selection | **done** |
| 3 | Training view: series from `epoch_fields`, nulls skipped, kernel's zero-epoch run explained | **done, one series blocked** (§4) |
| 4 | Results per task: MAE/RMSE/R² in target units, signed R², per-task baseline, absent metrics omitted | **done** |
| 5 | Two SVG visualisations | **one shipped, one substituted** (§5) |
| 6 | Inference panel, three shapes; kernel margin labelled as a signed distance | **done** |
| 7 | `scripts/qml-task-check.mts`, wired as `npm run qml:tasks` | **done, 4 red** (§4) |
| 8 | MT-006 re-scoped (ID kept); this report | **done** |

File sizes after the phase: `api/qml.ts` 504 · `charts.tsx` 584 · `QmlResultsPanel.tsx` 560 ·
`QmlConfigForm.tsx` 474 · `QmlTrainingDashboard.tsx` 365 · `QmlLabPage.tsx` 334 ·
`algorithmSwitch.ts` 79 (new) · `scripts/qml-task-check.mts` 439 (new) ·
`scripts/qml-task-fixtures.py` 155 (new).

### WP1 did its job as a tripwire

Changing the types first turned "find every place that assumes accuracy is a number" into a
compiler worklist: **0 → 18 errors across 3 files**, then 16 → 1 → 0 as each consumer was fixed.
Two of those 18 were places no grep for `accuracy` would have found, including
`QmlLabPage.tsx:113` reading `result.circuit` off a union whose interrupted arm has no such key.

---

## 2. Gates

Every number below was produced by a command run at this HEAD after the final edit.

| Gate | Required | Measured |
| --- | --- | --- |
| `pytest` | 1199 / 5 at phase start | **1208 passed, 5 skipped** (+9 new, 0 regressions) ✅ |
| `npm run typecheck` | 0 errors | **0** ✅ |
| `npm run build` | PASS | **✓ built in 8.24s** ✅ |
| Goldens @ 1e-9 | 190 + 804 + 3306 | **190 + 804 + 3306, all agree** ✅ |
| `npm run a11y` | 0 criticals | **0 criticals across every page** ✅ |
| CSS rule-level diff | justify any changed rule | **3 added / 0 changed / 0 removed** ✅ |
| `ruff check` | clean | **80 findings, all pre-existing; delta 0; the one real bug fixed — see §3** ⚠️ |
| §2A.6 flag states | 4 live | **4/4** ✅ |
| Backend files changed | 0 | **0 in `c3a77a3`**; 2 QML + 2 unrelated in follow-up commits, by ruling — see §4 ✅ |
| Harness FAIL decomposition | re-measured per script | **see below — now 0 across all four** ✅ |

### Bundle size

| Chunk | `origin/main` | this HEAD | delta |
| --- | --- | --- | --- |
| `QmlLabPage` | 29.67 kB (gzip 9.22) | **45.55 kB (gzip 13.64)** | +15.88 kB (+53%), gzip +4.42 kB |
| `index` | 640.79 kB (gzip 188.08) | 640.79 kB (gzip 188.08) | **0** |
| CSS | 164.21 kB | 164.28 kB | +0.07 kB |

The growth is confined to the lazy-loaded Lab chunk; the shared bundle is byte-identical, which
is the evidence that no dependency was added. `requirements.txt` and `package.json`'s
`dependencies` are untouched (`package.json` gained two `scripts` entries only).

### CSS rule-level diff

Built both revisions and parsed the emitted stylesheets into selector→body maps:

```
baseline rules: 1800   ours: 1803
ADDED:   3     REMOVED: 0     CHANGED: 0
  + @layer components;@layer utilities .gap-px
  + @layer components;@layer utilities .h-auto
  + @layer components;@layer utilities .max-w-[22rem]
```

Three Tailwind utilities the baseline never emitted because no source used those classes. **No
existing rule changed**, so no shipped page can look different. `max-w-[22rem]` is Tailwind's
static arbitrary-value syntax written literally in source — not an interpolated class, so QL-001
holds; `qml-ui-check` scanned 59 interpolated templates and found no colour utility among them.

### Harness FAIL decomposition — re-measured, not inherited

The Phase 5 figure `57 = 9+20+20+8` does not describe this HEAD, and two of the four scripts do
not even use the `PASS`/`FAIL` line convention — grepping them for `FAIL` yields `0`, which is a
measurement artifact rather than a result. Per script:

| Script | Convention | PASS | FAIL |
| --- | --- | --- | --- |
| `qml-render-check` | per-line `PASS`/`FAIL` | 34 | **0** |
| `qml-task-check` (new) | per-line `PASS`/`FAIL` | **48** | **0** |
| `qml-ui-check` | single `ALL CHECKS PASSED` summary | 58 guards | 0 |
| `qml-circuit-check` | single `ALL CHECKS PASSED` summary | 49 assertions | 0 |

**`qml-render-check` failed 2 of 34 mid-phase — both regressions I introduced**, both now fixed:

- *legend labels both series* — labels moved from hardcoded lowercase `"train loss"` to
  `EPOCH_FIELD_LABELS`' `"Train loss"`. The assertion's intent is "the legend names both
  series", not "the labels are lowercase", so it is now case-insensitive. This is the one
  existing assertion Phase 5c modified, and this sentence is the justification.
- *loss and accuracy curves emit stroked `<path>` geometry* — a real defect, see §4.

### §2A.6 flag states (live, this HEAD)

```
QML_ENABLED=true   GET /features      -> HTTP 200  {"qml_enabled":true}
QML_ENABLED=true   GET /qml/describe  -> HTTP 401
QML_ENABLED=false  GET /features      -> HTTP 200  {"qml_enabled":false}
QML_ENABLED=false  GET /qml/describe  -> HTTP 404
```

401-when-on (auth, route exists) versus 404-when-off (router never mounted) is the distinction
§2A.6 requires. Both servers were stopped afterwards; `ps` confirms zero `uvicorn app.main`
processes remain.

---

## 3. `ruff check` — run, and it is not clean

It was never run in Phases 0–5b. It has now been run, with the repo-root config
(`select = ["F", "E4", "E7", "E9", "B006", "B017", "B904"]`):

```
53 F401   10 E741   5 F541   4 E402   4 B017   3 F841   1 F821      Found 80 errors.
```

**The identical 80, with the identical rule distribution, is present on `origin/main`.** My
delta is **0**: `ruff check` over exactly the files this phase touched reports
`All checks passed!`. So the gate as written ("ruff check clean") **does not pass and cannot be
made to pass by this phase** — clearing it means an 80-error cleanup across the whole backend,
which §4 puts out of scope. Reporting it rather than quietly redefining the gate.

**One of the 80 is a live bug, not style:**

```
backend/app/api/jobs.py:327:16: F821 Undefined name `json`
```

`json` is never imported in that module, and line 327 is
`return json.dumps(ir.to_dict(), indent=2)` on the reachable
`if framework in ("json", "ir")` branch. Exporting a circuit as JSON or IR raises `NameError`
and returns a 500 instead of the IR. Outside QML scope and on the backend, so **not fixed here** —
it wants its own one-line commit.

**Fixed in `71562bd`**, as its own commit labelled pre-existing and kept out of the Phase 5c
accounting. `import json`, plus a test that derives the framework list from the endpoint's own
400 message and asserts every advertised name works — the old test parametrised over three of
the seven and none of them was the broken one. A subset parametrize reads like coverage and is
not. Both new tests fail with the import removed. F821 is now **zero repo-wide**.

The reviewer's AST sweep for this defect class reported exactly one instance. That was
reproduced here rather than taken on trust: the same sweep over `origin/main`'s 121 app modules
returns exactly one hit (`jobs.py:327`) and zero against this tree — a detector that has only
ever returned zero proves nothing.

The remaining 79 are style (53 F401, 10 E741, 5 F541, 4 E402, 4 B017, 3 F841). The gate as
written cannot pass without an 80-error cleanup that §4 puts out of scope; **"ruff reports no
new findings versus `origin/main`"** is the form that is both honest and enforceable today, and
is what I recommend it be restated as.

That finding is the argument for the gate: the lint everyone skipped was hiding a 500.

**A near-miss worth recording.** While checking whether those 4 F401s in `qml_lab.py` were mine,
I ran `ruff ... 2>/dev/null | wc -l` in a shell without the venv on `PATH`. It printed `0`, and
`0` is exactly what "clean" looks like. The command had actually failed with
`ruff: command not found` and I had discarded stderr. I only caught it because the number
contradicted a run from two minutes earlier. This is the same shape as the standing
"a parameter that is zero in the fixture is invisible" lesson: **a zero from an unverified
command is not evidence.** The corrected run confirms all 4 are present on `origin/main` at
identical line numbers, and no import line in that file differs from main.

---

## 4. The `epoch_fields` ↔ `load_history` contract — found, ruled on, closed

Phase 5c's frontend commit (`c3a77a3`) shipped with **4 of 48 harness assertions red** and
**0 backend files changed**, because the fix was a backend edit and the gate forbade one. The
reviewer ruled to fix it with a bidirectional test and restated the gate as *"0 backend
behaviour changes outside the QML module"*. Done in `85d7bda`.

**The defect ran in both directions at once**, which is why it survived review:

| Direction | Symptom |
| --- | --- |
| advertised, never served | `quantum_regression` advertised `train_r2`/`test_r2`; `load_history` serialised six keys and neither was among them. Phase 5b added the columns and `record_epoch` writes them — only the read path dropped them. |
| served, never advertised | every classification algorithm omitted `test_loss` from `epoch_fields` while `load_history` returned it. Phase 3's dashboard only kept that curve by hardcoding all four names; driving off the document deleted it. |

A one-directional test would have caught the first and blessed the second. So
`backend/tests/test_qml_epoch_contract.py` asserts the **equivalence**, at four layers:

- `epoch_fields[task]` == the metric fields the task's epoch record model actually carries
- every advertised name is serialised by `load_history`
- every metric key `load_history` serialises is advertised by some task
- `describe()` agrees with the table, enumerated from the registry for every algorithm

plus a pin that `quantum_kernel` advertises `epoch_fields` while `supports.epochs` is `False`
(D-042), so the client's real gate stays meaningful.

**Both defects were reinstated and each is caught by the directional assertion that owns it:**

```
# train_r2/test_r2 removed from load_history
FAILED test_every_advertised_field_is_serialised_by_the_history_endpoint[regression]
  regression advertises ['test_r2', 'train_r2'] but load_history never serialises them;
  a client asking for that series gets undefined.

# test_loss removed from classification epoch_fields
FAILED test_advertised_fields_are_exactly_what_the_engine_records[classification]
  recorded but never advertised: ['test_loss']
```

Enumerated from the registry, so a fifth algorithm is covered the day it is added — this is the
**fourth** appearance of this defect shape (frozen `LIMITS` then `ALGORITHM_LIMITS`;
`describe()`'s datasets versus the schema *and* the route; `trainer.train`'s parameter type), and
each time the lesson was that a rule proved at one construction site is not proved at the others.

**Result.** Fixtures regenerated from the fixed backend; the regression history now carries
`train_r2 = −2.060, −0.844, −0.161` — the exact values raw SQL found sitting in the database in
Phase 5b, now reaching the client. The negative-R² hazard is finally *renderable*, and the chart
plots a curve climbing from −2.06. `qml-task-check` goes **44/4 → 48/48**.

### Why the frontend could not have caught this

`QmlTrainingDashboard.tsx` guards with `last?.train_r2 != null`. That is **correct** null
handling, and it is exactly what makes the bug invisible: `undefined != null` is false, so the
tile silently does not render. No crash, no type error, `tsc` green. "The backend never sent the
key" and "this task has no R²" are indistinguishable at the component. Only a harness rendering
against a real captured payload sees the difference — which is the argument for WP7 existing.

## 5. §2E.3's predicted-vs-actual scatter is **not** shipped

Stated plainly because §5 requires it: the named deliverable does not exist, and what is in its
place is a different chart.

**Why.** The scatter needs per-sample test predictions paired with their targets. The result
payload carries only aggregates (`mae`, `rmse`, `r2`, `n_samples`); a recursive walk of every
numeric array in all three captured payloads found no per-sample vector; and none of the seven
`/qml` routes serves one. Two alternatives were considered and rejected: regenerating the seeded
split client-side needs numpy's PCG64 bit-for-bit, and inference against user input has
predictions but no actuals to plot them against.

**What shipped instead.** `ModelResponseCurve` — the learned function swept over `[-π, π]` at 48
points via the real inference endpoint, drawn against the training target range. It is labelled
as what it is in the UI, and it covers only `n_features === 1` (`sine`, `damped_cosine`; **not**
`linear_mix`), with an explicit on-screen reason when unavailable. `PredictedVsActual` was
deleted rather than parked as unreachable code.

**Minimal enabling change:** include the test-set predictions and their targets in the stored
result payload. Then the scatter is ~40 lines against the existing `charts.tsx` primitives.

---

## 6. The harness, and proof it can fail

`frontend/web/scripts/qml-task-check.mts`, wired as **`npm run qml:tasks`**. It renders the real
components with `renderToString` against payloads captured from actual worker-path runs
(`scripts/qml-task-fixtures.py` → `test-fixtures/qml-task-payloads.json`) — **not** from the
types I intended to write, which is how Phase 3's fixture came to invent four keys
`/qml/describe` never returned. The first group of assertions checks the *fixture itself* still
contains the hazards (null accuracies, zero kernel epoch rows), so the suite fails loudly if a
regenerated fixture stops being adversarial.

**A script that only passes is worth nothing. Two mutants, both caught:**

*Mutant 1 — reinstate the Phase 3 behaviour (plot nulls as-is, render the accuracy tile
unconditionally):*

```
FAIL  regression dashboard: renders no accuracy tile at all — a tile headed 'Train acc' asserts the metric applies here
FAIL  regression dashboard: never prints 0.0% for a null accuracy — null coerced to 0 renders as 0.0%
PASS  regression dashboard: no em-dash placeholder under an accuracy heading
PASS  finiteSeries: drops every null accuracy point — 0 points
PASS  vqc dashboard: still renders an accuracy tile
```

*Mutant 2 — `finiteSeries` coerces `null → 0` instead of dropping:*

```
FAIL  finiteSeries: drops every null accuracy point — 3 points
FAIL  finiteSeries: a null never becomes a zero
PASS  regression dashboard: renders no accuracy tile at all
```

Each mutant is caught by two assertions and survives the others, which is the shape wanted: the
checks are independent, not one assertion wearing five names. Both were reverted and the suite
returned to its 44/4 baseline.

### The zero-in-the-fixture blindness, addressed directly

Phase 3 found holes in 4 of 12 mutants and **both** Phase 5 survivors were the same failure
mode: *a parameter that is zero in the fixture is invisible*. Two places in this phase had that
shape and both are asserted on a non-zero value:

- the kernel's epoch count is genuinely `0`, so "renders zero epochs correctly" is unfalsifiable
  by a zero. The assertion instead requires the **1,617** measured pair evaluations and the words
  describing a closed-form solve to appear, and separately requires **no** spinner and **no**
  empty axis.
- a null accuracy and a `0.0` accuracy are indistinguishable after `* 100`. The assertion
  requires the substring `0.0%` to be **absent**, which a null-rendered-as-zero cannot satisfy.

### What the harness deliberately does **not** claim

`Select` renders its items in a Radix portal, so **the option list is not in the SSR markup**. An
assertion like "the regression form offers only regression datasets" would have been green
against markup that contains neither `sine` nor `moons` — a test passing because it was looking
at nothing. Two such assertions were written, observed to be vacuous, and removed.

The invariant they were reaching for is now tested where it is real: the algorithm-switch rule
was extracted into `src/components/qml/algorithmSwitch.ts` as a pure function and is exercised
over **all 48 from/dataset/to transitions**, asserting that none strands an incompatible dataset,
none leaves an `n_hidden` key on an algorithm whose config model is `extra="forbid"`, none
exceeds the new algorithm's sample ceiling, and that a *compatible* dataset is preserved rather
than reset. That last one matters: resetting always would be trivially "safe" and would silently
move users off the data they picked.

---

## 7. Two defects found in shipped code

**`ColumnDef.render` is `(value, row)`; the Phase 3 predictions table read the first argument as
the row.** Proven server-side: the shipped idiom renders the literal string `"undefined"` in
every Class badge, the corrected one renders `1`. The class badge and probability bar have been
blank for every inference since Phase 3. `tsc` is silent because `render`'s parameters are typed
`any`, and `qml-render-check` asserted the table existed rather than what its cells contained.
Fixed at all four call sites in `QmlResultsPanel`; recorded as D-048. Fourth instance of
"read the helper's signature before calling it".

**`jobs.py:327` — `NameError` on JSON/IR export.** See §3. **Fixed in `71562bd`** on the
reviewer's ruling, as a separate commit labelled pre-existing so Phase 5c's diff stays legible.

---

## 8. Not verified — carried forward unchanged

No target-machine numbers. **No Redis or Celery broker** — `.apply()` proves the task body, not
delivery, serialisation, prefork, soft-time-limit signals or concurrency. No docker, no
screenshots, no GPU, no density-matrix path, nothing ever OOM-killed, Linux not Windows.
`qml_task_soft_time_limit` stays 900/1200 provisional. **MT-001 (`bench_qml.py --full`) still
blocks Phase 8** and cannot be run from a sandbox.

The R²-curve gap is **closed**, so MT-006's third sub-item is no longer blocked on the backend;
it is now blocked only on the same thing as the other two — a human with a browser.

New to this phase: **no browser has rendered any of this.** Every frontend claim rests on
server-side rendering via `renderToString`, which exercises the component tree and its markup but
**not** layout, not CSS cascade, not hover or focus states, not the Radix portals (so no Select
dropdown, no tooltip has ever been seen open), not `useEffect`, and not the polling loop —
`refetchInterval` is asserted by reading the code, never by observing a second request. The three
MT items in §MT-006's "what remains manual" exist for exactly this reason.
