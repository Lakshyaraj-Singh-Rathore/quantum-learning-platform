# Phase 7 — Verification

**Base:** `main @ 853d0f6`, **614 tracked files**. Working tree byte-identical to `origin/main`
before this phase's doc edits (`git diff --stat origin/main` → empty).

**This is an audit, not a build.** Zero product-code changes. Every number below was produced by a
command run in this phase, from a clean state. Where a figure could not be reproduced, it says so.

---

## 0. Headline

**Nine gates re-measured, all hold. Four carried figures settled. Four findings.**

The findings, in order of how much they should change what the owner does:

1. **The flag-off "byte-identical bundle" claim is false, and cannot be true.** The shipped JS is
   **+1613 bytes** against a pre-QML baseline. *Behavioural* identity is proven; byte identity is
   not achievable for any flag-gated lazy route, because the gate itself has to ship. §3.
2. **The 57-FAIL decomposition that Phase 5 could not reproduce, reproduced exactly:**
   `9 + 20 + 20 + 8`. These are 57 real, currently-failing assertions on `main`, in non-QML areas.
   §2.
3. **The fourth flag state is asserted by a regex over source text, not by rendering.** §4.
4. **`bg-card` emits no CSS at all, and all ten uses are in the files the owner is editing.** §7.

---

## 1. Gates, re-measured

| Gate | Command | Result |
| --- | --- | --- |
| Backend suite | `python -m pytest -q` | **1230 passed, 5 skipped** in 344.44 s ✅ |
| Tests collected | `pytest --collect-only -q` | 1235 = 1230 + 5 ✅ |
| ruff | `ruff check . --output-format=concise` | **79** — no new vs `main`'s 79 ✅ |
| typecheck | `npm run typecheck` | **0 errors** ✅ |
| build | `npm run build` | **✓ built in 10.93 s** ✅ |
| Shared chunk | `stat -c%s dist/assets/index-*.js` | **640793 B** — matches Phase 6 exactly ✅ |
| CSS bundle | `stat -c%s dist/assets/index-*.css` | **164325 B** ✅ |
| `QmlLabPage` | `stat -c%s dist/assets/QmlLabPage-*.js` | **49363 B** ✅ |
| a11y | `npx tsx scripts/a11y-check.mts` | **0 criticals across every page** ✅ |
| Goldens | `golden:quantum` / `:demos` / `:grover` | **190 + 804 + 3306** @ 1e-9 ✅ |
| Flag states | live uvicorn, both states | **4/4** ✅ (§4 qualifies the fourth) |
| Tracked files | `git ls-files \| wc -l` | **614**, +2 this phase (§9) |

Phase 6's three bundle figures reproduced to the byte on a clean rebuild. That is the one
cross-phase check that could have exposed a stale transcription, and it did not.

---

## 2. The four carried figures, settled

### 2.1 The harness FAIL decomposition — **reproduced, contrary to Phase 5**

Phase 5 could not reproduce `57 = 9+20+20+8` and said so. Running all 24 harnesses individually:

| Script | PASS | FAIL |
| --- | ---: | ---: |
| `render:codelab` | 6 | **9** |
| `render:p5` | 14 | **20** |
| `render:games` | 12 | **20** |
| `render:results` | 39 | **8** |
| | | **57** |

`9 + 20 + 20 + 8 = 57`. **Phase 1's figure was correct all along**; what Phase 5 lacked was the
per-script split, because the aggregate is only visible by running each script separately.

**These are not environmental.** None of the four reads `API_TARGET`; they fail against static
fixtures. Sample failures: `FAIL the build button is offered` (codelab), `FAIL every quiz is
selectable` (p5), `FAIL the objective is shown` (games), `FAIL a noiseless run says so on the
fidelity gauge` (results). **57 assertions about CodeLab, lesson content, Games and the results
fidelity gauge fail on `main` today.** All four areas are outside QML; no QML phase caused or
touched them. Phase 1 correctly characterised 57 as the regression gate — the number to not make
worse — and it has not moved.

**Retire** `57` as an unexplained aggregate. The authoritative statement is the table above.

### 2.2 Full harness inventory

`package.json` has **35 scripts**: 24 verification harnesses, 7 fixture generators (not run —
they rewrite fixtures), and `dev`/`build`/`preview`/`typecheck`.

| Script | PASS | FAIL | | Script | PASS | FAIL |
| --- | ---: | ---: | --- | --- | ---: | ---: |
| `smoke:auth` † | 13 | 0 | | `render:composer` | 36 | 0 |
| `render:check` | 65 | 0 | | `curriculum` | 58 | 0 |
| `a11y` | 9 | 0 | | `qml:render` | 34 | 0 |
| `states` | 31 | 0 | | `qml:tasks` | 55 | 0 |
| `smoke:composer` † | 10 | 0 | | `qml:ui` ‡ | 58 | 0 |
| `render:learn` | 37 | 0 | | `qml:circuit` ‡ | 49 | 0 |
| `render:playground` | 20 | 0 | | `golden:quantum` ‡ | 190 | 0 |
| `render:grover` | 27 | 0 | | `golden:demos` ‡ | 804 | 0 |
| `render:content` ‡ | pass | 0 | | `golden:grover` ‡ | 3306 | 0 |
| `push:overlay` ‡ | pass | 0 | | `test:demos` ‡ | pass | 0 |
| **`render:codelab`** | 6 | **9** | | **`render:p5`** | 14 | **20** |
| **`render:games`** | 12 | **20** | | **`render:results`** | 39 | **8** |

† Needs a live API. Previously recorded as blocked; **this phase started one and ran them — both
pass, 23 assertions recovered from "unmeasurable".**
‡ Reports a prose total rather than `PASS` lines.

`qml:ui` prints `BLOCKED` if `dist/` is absent — it reads the built CSS. **`BLOCKED` is not
`FAIL`**; run it after `npm run build`.

### 2.3 `qml:tasks` — gate restated

Specified as a fixed **48**; measures **55**. Per §2G.2 the gate is restated as:

> **No pre-existing `qml:tasks` assertion may regress; growth is reported with its cause.**

Current: **55 PASS / 0 FAIL** = 48 pre-existing + 7 added by Phase 6.

### 2.4 The Makefile compose count — **all three previous answers were right**

```
$ grep -cE "docker[ -]compose" Makefile          → 6     (literal mentions)
$ grep -cE '\$\(COMPOSE\)' Makefile              → 9     (variable expansions)
```

The confusion was never arithmetic — it was three different definitions of "invocation":

| Count | What it measures |
| ---: | --- |
| **2** | direct `docker compose` calls in a recipe body (lines 35, 40) |
| **9** | `$(COMPOSE)` expansions (lines 24, 30, 43, 46, 49, 52, 55, 58, 61) |
| **6** | lines literally containing the string (4 of which are a conditional, a variable, a definition and a comment) |
| **11** | **total runtime invocations = 2 direct + 9 via the variable** |

**Authoritative: 11 runtime invocations**, and the definition is now attached to the number so it
cannot drift again. `COMPOSE := docker compose $(GPU_FILES)` at line 16 is the indirection that
made a plain `grep` under-count.

---

## 3. §2G.3 — the flag-off identity claim

### What is proven

**API surface — exact.** Two live servers, same DB, differing only in `QML_ENABLED`:

| | flag OFF | flag ON |
| --- | ---: | ---: |
| OpenAPI paths | **59** | **66** |
| paths containing `qml` | **0** | 7 |
| occurrences of `qml` anywhere in `openapi.json` | **0** | — |

```
ADDED by the flag (7):   /qml/describe · /qml/experiments ·
  /qml/experiments/{experiment_id} · …/cancel · …/explain · …/inference · …/result
REMOVED by the flag (0)
every added path is under /qml/:        True
the OFF path set is a strict subset:    True
non-qml paths whose SPEC differs:       0
```

Not one existing route's schema changes between flag states. Every `/qml/*` path returns **404**
on GET and POST with the flag off; `GET /features` answers **200 `{"qml_enabled":false}`**
unauthenticated.

**Nav and route — proven by the render harness:**

```
PASS  nav: entry absent when the flag is off
PASS  nav: entry absent while the flag is unresolved (no flash)
PASS  nav: existing entries unaffected by the flag
PASS  nav: the gated entry is the ONLY difference between on and off — on=11790 off=10459
PASS  route: 404 body when the flag is off
```

### FINDING 1 — the bundle is **not** byte-identical, and cannot be

§2G.3 asks for "the shared bundle byte-identical to a pre-QML baseline". Built the pre-QML
baseline (`46576c8`, the parent of the first QML commit; its only `qml` files are five docs) in a
scratch worktree:

| | pre-QML `46576c8` | `main @ 853d0f6` | delta |
| --- | ---: | ---: | ---: |
| shared `index-*.js` | 639180 B | 640793 B | **+1613** |
| `index-*.css` | 163402 B | 164325 B | **+923** |

**The delta is 100 % attributable to QML.** Only three commits in that range touch
`frontend/web/src`, and all three are QML (`ab0b252`, `f022407`, `2f7ed2d`).

**What is in the shared chunk**, extracted from the bundle:

1. `Y3=v.lazy(()=>yr(()=>import("./QmlLabPage-4AZOQxV5.js"),[]))` — the lazy declaration
2. `const w2={qml_enabled:!1}` — the fail-closed default
3. the `useFeatures`/`useQmlEnabled` hook
4. `{to:"/qml-lab",label:"Quantum ML Lab",icon:$j,section:"build",flag:"qml_enabled"}` — the nav entry, carrying its own gate
5. `<Route path="/qml-lab" element={<Y3/>}/>`

**This is unavoidable.** A lazily-loaded, flag-gated route must ship the import declaration, the
flag read and the gated nav entry in the shared chunk — that is the mechanism by which the gating
works. The only way to a byte-identical bundle is to not build the feature, or to strip it at
build time with a compile-time flag, which is a different architecture from the one §2A.6
specified.

**Recommendation:** restate §10's requirement as **behavioural** identity, which is met and
proven, and drop "byte-identical shared bundle" as the test — it is unsatisfiable by the design
the spec itself mandates. The honest summary for a release note is: *with the flag off the API
surface is unchanged, the nav is unchanged, `/qml-lab` renders the 404 body, and the browser
downloads 1.6 kB of dormant routing metadata it never executes.*

### CSS, rule-level, vs pre-QML

The diff against `origin/main` is **empty by construction** — this tree *is* `origin/main` — so
it proves nothing. The informative comparison is against the pre-QML baseline:

```
pre-QML rules 1789   now 1804
ADDED 15   CHANGED 1   REMOVED 0
```

**No hand-written rule was altered.** The single "changed" rule is Tailwind's own generated
`@layer properties` defaults block, which gained `--tw-border-spacing-x/y` because QML introduced
`border-separate` and `border-spacing-1`. The 15 additions are all new utilities
(`.whitespace-pre-wrap`, `.gap-x-4`, `.max-w-[22rem]`, …). **0 removed.**

---

## 4. §2A.6 — the four flag states

| State | How it is proven | Verdict |
| --- | --- | --- |
| **ON** | live server: 66 paths, nav entry present, lab renders | ✅ rendered + live |
| **OFF** | live server: 59 paths, all `/qml/*` 404, nav absent, route renders 404 body | ✅ rendered + live |
| **Unresolved** | `PASS route: neither lab nor 404 while unresolved (no flash)` | ✅ rendered |
| **Error (fail closed)** | `qml-ui-check.mts:253` — `/query\.data \?\? FEATURES_CLOSED/.test(src)` | ⚠️ **FINDING 2** |

### FINDING 2 — the fourth state is asserted against source text, not behaviour

The fail-closed path is **implemented correctly**: `useFeatures.ts:42` returns
`query.data ?? FEATURES_CLOSED` and treats an error as resolved (`resolved: !query.isPending`),
so a failed `/features` hides the nav *and* lets the route guard show 404 rather than hanging.

But the only guard on it is a **regular expression matching the source string**. That guard:

- **fails on a correct refactor** — `query.isError ? FEATURES_CLOSED : query.data` is behaviourally
  identical and would break the test;
- **passes on a real regression** — keep the text, change `resolved` to `!query.isPending &&
  !query.isError`, and the route guard hangs forever on a backend outage while the guard stays
  green.

The other three states are proven by rendering a tree and asserting on the output. This one is
proven by `grep`. Not a defect in the product; a hole in the evidence, and the one place in §2A.6
where "proven, not asserted" is not yet met.

**What would close it:** render the shell with a `QueryClient` whose `/features` query is seeded
to an error state, and assert the nav lacks the entry and `/qml-lab` shows the 404 body. The
render harness already constructs a `QueryClient`, so this is small — but it is product-adjacent
test code and §2G.7 forbids writing it in this phase.

---

## 5. §2G.4 — the nine acceptance criteria

**I do not have the master prompt's text.** It is not in this repository — `docs/prompts/` holds
only `QML_LAB_VISION_AGENT.md` and `VISION_QA_CAMPAIGN.md`, neither of which states the nine. Per
§2G.4 I am saying so rather than reconstructing them.

What exists are **two in-repo restatements**, and they are mapped below from
`phase-1-report.md:94` and the test names in `backend/tests/test_qml_acceptance.py`. All ten tests
pass inside the 1230.

| # | Criterion (per `phase-1-report.md`) | Test | Passing |
| ---: | --- | --- | :-: |
| 1 | Valid parameterised circuit executes | `test_criterion_1_a_valid_parameterised_circuit_executes` | ✅ |
| 2 | Predictions derived from measurements | `test_criterion_2_predictions_are_derived_from_measurements` | ✅ |
| 3 | Real training loss | `test_criterion_3_the_training_loss_is_real_and_decreases` | ✅ |
| 3b | It actually learns | `test_criterion_3b_the_model_learns_rather_than_merely_running` | ✅ |
| 4 | Gradients via a supported method | `test_criterion_4_gradients_come_from_a_supported_method` | ✅ |
| 5 | Parameters updated | `test_criterion_5_parameters_are_updated` | ✅ |
| 6 | Completes within limits | `test_criterion_6_the_run_completes_within_its_limits` | ✅ |
| 7 | Save / reload | `test_criterion_7_and_8_save_reload_and_identical_predictions` | ✅ |
| 8 | Identical predictions after reload | *(same test)* | ✅ |
| 9 | **see discrepancy below** | `test_criterion_9_the_evaluation_is_coherent` | ✅ |
| — | Reproducible from the seed alone | `test_the_whole_run_is_reproducible_from_the_seed_alone` | ✅ |

All ten share **one real training run** (moons, 80 samples, 2 qubits, 2 layers, 10 epochs,
seed 7), so the evidence is internally coherent rather than ten unrelated fixtures. Nothing is
mocked.

**Two discrepancies, recorded rather than resolved — I cannot adjudicate without the source text:**

1. **"Nine" criteria, ten rows.** Criterion 3 is split into 3 and 3b. Whether the master prompt
   had nine items and Phase 1 added the "it actually learns" split, or the prompt itself
   distinguished them, is not determinable from the repo. The split is substantive and worth
   keeping either way: a circuit that runs but does not learn passes 3 and fails 3b.
2. **Criterion 9 means two different things in two places.** `phase-1-report.md` row 9 reads
   *"Automated tests pass — 153 new tests, 0 failures"*; the test named `criterion_9` asserts the
   **evaluation is coherent** (confusion matrix sums to `n_samples`, accuracy agrees with the
   predictions, the diagonal over the total equals the accuracy). Both are reasonable ninth
   criteria. Only the master prompt can say which is the real one.

**On the "153 new tests" figure:** not reproducible as stated, because nothing distinguishes
"new in Phase 1" in the tree today. What is measurable now: **405 QML tests across 19 files**
(`test_qml_regression.py` 51, `test_qml_api.py` 43, `test_qml_dispatch.py` 34, `test_qml_persistence.py`
32, `test_qml_kernel.py` 31, `test_qml_config.py` 29, `test_qml_hybrid.py` 27, `test_qml_datasets.py`
23, `test_qml_circuit.py` 21, `test_qml_tasks.py` 18, `test_qml_ai.py` 14, `test_qml_trainer.py` 14,
`test_qml_migration.py` 13, `test_qml_dispatch_db.py` 12, `test_qml_acceptance.py` 10,
`test_qml_evaluator.py` 10, `test_qml_baseline.py` 9, `test_qml_epoch_contract.py` 7,
`test_qml_gradients.py` 7), against **830 non-QML**, totalling the collected **1235**.

---

## 6. §2G.5 — the unverified surface

Stated in the plain words used for `.apply()` in Phase 5b, because this is what the owner acts on.

### 6.1 No browser has ever rendered the QML Lab

Every frontend claim in Phases 3, 5c and 6 — and every `PASS` in §2.2 above — comes from
**server-side rendering a component tree and asserting on the HTML string**. That means:

- no layout has been computed; nothing is known about whether anything overlaps, wraps or clips
- no CSS cascade has been applied; the harness reads class *names*, and §7's `bg-card` entry is
  exactly the defect that survives that
- no Radix portal has been seen open — portalled content is absent from SSR entirely, so every
  `Select` dropdown in the config form is unverified
- `refetchInterval` is asserted by **reading the code**, not by observing a second request. The
  polling-stops-on-terminal behaviour, which §2E and `ui-audit.md:212` both call an explicit
  acceptance criterion, has never been watched happening
- no hover, focus, keyboard trap, or scroll behaviour has been exercised

**What would exercise it:** MT-001 and MT-006, on a real browser.

### 6.2 The live Gemini call has never executed

`GEMINI_API_KEY` is absent here and `is_configured()` (`gemini_client.py:88`) also requires an
importable `google.generativeai`. Every configured-path test substitutes a transport named as a
fake. They prove prompt construction, reply handling and failure translation. **They do not prove
Gemini answers well, and nothing in the codebase checks the reply against the grounding data.**
The platform already carried an untested live Gemini path before this work; Phase 6 added a fourth
caller — measured below — not the first risk.

**Caller count, corrected.** Phase 6 said "three real callers". **It is five pre-existing plus
one new.** Resolved by AST — binding each module's local alias for `gemini_client.generate` and
counting calls through it, because two call sites use a *function-local aliased import* that no
`gemini_client.generate` grep can find:

| Call site | How it is bound | `temperature` passed |
| --- | --- | --- |
| `app/ai/chat.py:101` | `from … import generate` | no → default 1.0 |
| `app/quantum/smart_composer/generator.py:155` | `import generate as gemini_generate` (inside the function) | no → default 1.0 |
| `app/quantum/smart_composer/simplifier.py:106` | `import generate as gemini_generate` (inside the function) | no → default 1.0 |
| `app/services/assignment_ai.py:326` | `gemini_client.generate` | no → default 1.0 |
| `app/services/codelab_ai.py:92` | `gemini_client.generate` | no → default 1.0 |
| `app/services/qml_ai.py:285` | `gemini_client.generate` | **yes — `EXPLAIN_TEMPERATURE`** |

**The Phase 6 safety claim survives the correction**: all five pre-existing callers pass no
`temperature` and are bit-identical. The count was wrong; the conclusion was not.

### 6.3 `bench_qml.py --full` has never run on the target machine

`qml_task_soft_time_limit = 900` and `hard = 1200` are **provisional and untuned**. No
target-machine numbers exist: no GPU, no docker, nothing OOM-killed, Linux not Windows.
**MT-004.**

### 6.4 No real broker, prefork pool, or signal-based time limit

The suite runs Celery eagerly; `.apply()` executes the task body **in-process**. It proves the
task body, not the broker. Never exercised: Redis transport, serialisation across a process
boundary, prefork worker behaviour, `SIGTERM`-based soft time limits, revocation of a running
task, concurrency limits under real contention. **MT-002 and MT-003.**

> Phase 6 added one observation worth carrying: eager Celery makes some states *unreachable in
> tests*. The explain route's 409 test originally asserted inside `if still running:`, which never
> executed, because the task always completes before `POST` returns. Any test guarding an
> assertion behind a non-deterministic condition is vacuous until proven otherwise.

---

## 7. §2G.6 — defect ledger

| ID | Where | Blocks release? | Catching script? |
| --- | --- | --- | --- |
| **QL-005** | `qudit_lab/simulator.py` — `round(…, 6)` at **lines 140, 151, 160** (re-measured today; file is 244 lines). d=3 distribution sums to 0.999999 while `trace = 1.0` | No — P3, open as an API-contract decision | **No** |
| **QL-015** | Toasts anchor bottom-right over live result content | **Closed** in Phase 9A (`a1429c5`) — worse than filed: at 1920 the default position covered the **Run Simulation button itself** | **Yes** — `npm run viewport`, 3 viewports |
| **QL-016** | Preset card titles truncate at ≤1366 px | **Closed** in Phase 9A (`a1429c5`) — 6 of 9 titles clipped at 1366, each losing the operator being taught | **Yes** — `npm run viewport`, asserts at 1366×768 permanently |
| **QL-017** | Diagonal cells keep the "pop" sub-label in the phase view | No — P4, teaching-design call | **No** |
| **QL-018** | `QmlConfigForm.tsx` Samples field: `step={50}` with `min={20}` made the default 200 fail HTML constraint validation — the form could not be submitted in any browser | **Did** — fixed in Phase 8 Stage 4.1 (`96b4320`) | **Yes, now** — `qml-browser-check.mts` asserts every numeric default passes `checkValidity()` |
| **QL-020** | `QmlConfigForm.tsx` n_hidden: the form advertised `max=8` (`MAX_HIDDEN_UNITS`, a static per-algorithm ceiling) while the binding rule is `n_hidden <= n_qubits` (`hybrid.py:143`). `checkValidity()` returned **true** for a config the backend 422s every time | **No** — P3; the error path is legible, but the user is told the value is fine and only finds out after a round-trip | **Yes** — `npm run qml:vision` asserts the ceiling tracks `n_qubits` |
| **`bg-card`** | 10 uses / 6 files, **all Qudit Lab** | No — cosmetic, but see below | **No** — and `qml:ui` would not catch it |

**QL-005 line numbers re-measured, as §2G.6 asked**, since the owner is editing that file: `round(clamped_pop, 6)` at **140**, `round(normalized_probs[i], 6)` at **151**, `round(mag, 6)` at
**160**. (`round(elapsed_ms, 2)` at 199 is timing, not probability — not part of QL-005.)

### FINDING 4 — `bg-card` emits nothing, in the files being edited right now

| Measurement | Result |
| --- | --- |
| `bg-card` occurrences in `src/` | **10**, across 6 files |
| `.bg-card` / `.bg-card\/60` / `\/40` rules in the built CSS | **0** |
| `--color-card` token defined | **0** |
| `.border-line` rules, for contrast | **19** |

So on `<div className="rounded-xl border border-line bg-card/60 …">` the border renders and the
background silently does not. Not a QML defect and **not fixed here** — §2G.6 says record.

**Two things make it more interesting than a cosmetic nit.** First, `bg-card` is a *plausible*
token name that fails silently — Tailwind emits nothing for an undefined colour and no tool
complains, which is why it has survived. Second, **all ten uses are in
`src/components/qudit/` and `QuditLabPage.tsx`** — precisely the files the owner has unpushed work
in. Worth checking against that changeset before anyone fixes it here.

---

## 8. §2G.5 — the blocking manual tests, as one ordered list

Register holds **MT-001…MT-010**, all IDs unique, none reused. Four block release. MT-005 is a
**NON-GOAL** (GPU, skipped by decision per D-030), not an open gap.

**Run in this order. 1 and 2 are prerequisites for the rest.**

| # | MT | What to run | Why it is first |
| ---: | --- | --- | --- |
| 1 | **MT-004** | `python backend/scripts/bench_qml.py --full` on the target machine; record wall-clock per algorithm | Everything downstream assumes the 900/1200 s limits are survivable. If they are not, the limits change and the UI timings change with them |
| 2 | **MT-001** | `make up` with `QML_ENABLED=true`; full browser round trip: submit → train → watch the dashboard → read results | The only proof any of the UI works. Also the first time a browser has rendered the Lab at all |
| 3 | **MT-006** | In the same session, run a **regression** experiment and confirm it renders as regression — MAE/RMSE/R², **no** accuracy, no confusion matrix | The §2E.1 failure mode the type lie at `api/qml.ts:98` would produce. Cannot be closed by anyone without a browser |
| 4 | **MT-010** | Set a real `GEMINI_API_KEY`, press **Explain** on one classification and one regression result | The configured AI path has never executed. Pass criterion: **every number in the prose also appears in the table beneath it** |

**Non-blocking, same session if there is time:** MT-002 (worker service actually starts),
MT-003 (per-task time limits under Windows), MT-007 (frequency budget), MT-008 (kernel heatmap),
MT-009 (kernel sample cap).

**Three checks to add to MT-001 while a browser is finally open**, because they are the §6.1 gaps
and cost nothing extra once logged in:

- open a `Select` in the config form — **no portalled content has ever been rendered**
- watch the network panel during a run and confirm polling **stops** when the status goes
  terminal — `refetchInterval` has only ever been read, never observed
- glance at the Qudit Lab panels for the missing `bg-card` background (§7)

---

## 9. Phase accounting

**Tracked files: 614 → 615.** Exactly one new file — this report. `DECISIONS.md` was *modified*,
not added, so it does not move the count. Measured with `git ls-files | wc -l` after the final
`git add -A`.

| Change | Files |
| --- | --- |
| `docs/qml/07-verification.md` | **new** |
| `docs/qml/DECISIONS.md` | +3 entries, **D-049/050/051** (45 unique IDs, 0 duplicates) |

**Zero product-code changes.** `git diff --stat origin/main -- backend frontend` is empty.
No harness or test was modified: §2G.7 permits it *if* re-measurement exposes a wrong gate, and
the two candidates (§2.3 `qml:tasks`, §4 the error state) are a **specification** fix and a
**new** test respectively — neither is a wrong gate needing repair, and writing the latter is
product-adjacent work this phase forbids.

> **D-011 / D-011b are not a duplicate ID.** A suffix-stripping `grep` reported one; they are
> distinct entries, both pre-existing on `main`. Noted because the ID scheme permits letter
> suffixes and a naive uniqueness check will keep flagging it.

---

## 10. What this phase did not verify

- **Nothing in §6 changed.** No browser, no live Gemini, no target hardware, no broker. Phase 7
  re-measured what can be measured here and the unverified surface is the same size as before.
- **The master prompt's nine criteria could not be read**, only two in-repo restatements that
  disagree about criterion 9 (§5).
- **`153 new tests` is not reproducible** — nothing marks a test as "new in Phase 1". Replaced
  with a measurable figure (405 QML tests) rather than an invented reconciliation.
- **The 57 failing assertions were not investigated.** They are reproduced, decomposed and
  attributed to four non-QML harnesses; *why* each fails is outside this phase's scope and would
  be product work.
- **No defect in §7 was fixed**, per §2G.6.
