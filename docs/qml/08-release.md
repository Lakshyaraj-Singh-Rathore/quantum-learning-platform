# 08 — QML Lab release notes

**Scope: how to turn the QML Lab on, how to turn it off again, what has been
verified, and what has not.**

This document does **not** claim all gates are green. The pre-existing harness
suite ends this phase red by 57 assertions (§8), and parts of the production
surface have never been exercised (§7). Both are stated here rather than in a
footnote, because an operator deciding whether to enable this feature needs
them more than they need the passing figures.

---

## 1. Enabling the feature — two parts, both required

Enabling the QML Lab is **two independent actions**. Doing one without the
other does not half-enable the feature; it produces a broken state.

```bash
# 1. the API must publish the flag and mount the routes
QML_ENABLED=true          # on the `api` service

# 2. a worker must exist to consume the queue
docker compose --profile qml up -d
```

`docker-compose.yml:104` puts the `qml-worker` service behind
`profiles: ["qml"]`, so `make up` does not start it. That is deliberate — it is
what keeps the default deployment **behaviourally** identical to the pre-QML one.
(Not *byte*-identical: §6 of this document measures +1613 B of JS and +923 B of
CSS versus pre-QML `46576c8`, all of it dormant routing metadata. Phase 7
withdrew byte-identity as unsatisfiable, because the gating mechanism §2A.6
requires is itself the difference.)

**What each half-configuration actually does:**

| `QML_ENABLED` | `--profile qml` | Result |
| --- | --- | --- |
| `false` | either | Feature absent. `/features` returns `{"qml_enabled": false}`, every `/qml/*` route 404s, the nav entry is not rendered. **This is the default.** |
| `true` | **not** started | **The UI works and every run fails.** The lab renders, the form submits, the API accepts the experiment and returns `201 Created` — and the job is never consumed. |
| `false` | started | A worker idles against a queue nothing writes to. Harmless, useless. |
| `true` | started | The intended configuration. |

**Observed, not inferred.** Running the API with `QML_ENABLED=true` and no
worker, a browser submission produced an experiment row that went to
`status=failed` with
`Could not enqueue experiment: No module named 'memory'`. That particular
message came from an invalid broker URL in the verification environment; with a
*valid* broker and no worker the row stays in its initial state instead, and
the user sees a run that never progresses. **Both failure modes are the same
operational mistake, and neither is self-explanatory from the UI.** Check the
worker before blaming the model.

---

## 2. Rollback

Rollback is also two parts, and the order matters: **stop the worker first**, so
no job is mid-flight when the schema moves.

```bash
docker compose --profile qml down     # 1. stop consuming
QML_ENABLED=false                     # 2. hide the feature; routes 404 again
alembic downgrade i4d7e0f3a6b9        # 3. only if the schema must go back
```

Steps 1 and 2 are reversible and lossless. **Step 3 is not.**

> ### `j5e8f1a4b7c2` destroys data on downgrade
>
> `downgrade()` runs:
> ```sql
> DELETE FROM qml_epoch_metrics WHERE train_accuracy IS NULL
> ```
> Those are **every epoch row written by a regression run**. Regression
> experiments have no `train_accuracy`, so they cannot satisfy the restored
> `NOT NULL` constraint. The migration deletes them rather than backfilling
> `0.0`, because inventing an accuracy for a regressor is the exact lie the
> migration was written to prevent (Phase 5b; D-038).
>
> **The deliberate choice is to lose the rows.** If regression history matters,
> export `qml_epoch_metrics` before downgrading. The up→down→up cycle was
> exercised and returns to a single head, `j5e8f1a4b7c2` — but "the schema
> returns" is not "the data returns".

Steps 1 and 2 alone are sufficient to withdraw the feature from users. Step 3
is only for removing the tables.

---

## 3. Pre-enablement checks, in order

From `MANUAL_TEST_REGISTER.md`. These four are **blocking** and are ordered so
that each one's failure makes the next meaningless:

| Order | ID | Checks | Why it is first/next |
| ---: | --- | --- | --- |
| 1 | **MT-004** | Timeouts and cancellation under the real broker | Everything downstream assumes a job can be stopped. **It is also the only sanctioned source of timeout numbers.** |
| 2 | **MT-001** | A full training run end to end on the target host | Until a run completes on real hardware, no metric below means anything |
| 3 | **MT-006** | Regression reports MAE/RMSE in target units and a signed R², **and no classifier metric** | The failure mode is a regressor displaying an accuracy, which looks plausible and is meaningless |
| 4 | **MT-010** | Concurrency limit under genuine parallel load | Only observable once 1–3 hold |

Non-blocking: MT-002, MT-003, MT-007, MT-008, MT-009. **MT-005 is a
declared non-goal** — it is GPU-specific and the QML Lab is CPU-only by
decision (D-030).

### Timeouts are provisional

`celery_soft_time_limit=8` / `celery_hard_time_limit=15` are the **pre-existing
platform limits and are not QML's**; they are untouched. QML tasks use
`qml_task_soft_time_limit=900` / `qml_task_hard_time_limit=1200`.

Those two QML numbers were chosen from simulator runs, not from production
measurement. **Tightening them is fine at any time. Loosening them requires
sign-off, and MT-004 is the only source of evidence that may be cited** — not a
local run, not a benchmark, not this document.

---

## 4. What was verified in this phase

Measured on `arena/63ae45b4-quantum-learning-platform` at the commit that adds
this file.

| Gate | Result | Note |
| --- | --- | --- |
| `pytest` | **1304 passed, 5 skipped** (383 s) | Gate ≥1230. The +74 over Phase 7 comes from adopting `main @ 045b966`, not from this phase — 0 Python files differ from that base |
| `ruff` | **118**, identical on HEAD and `origin/main` | **0 new.** The "79" baseline was measured on the older pre-merge tree; it is stale, not breached |
| Typecheck | **0 errors** | |
| Build | **PASS** | |
| Shared bundle | **640 809 B** (gate cites 640 793) | **+16 B**, all from §5's `bg-card`→`bg-raised` rename: the class name is two characters longer in 7 places |
| `QmlLabPage` chunk | **49 355 B** (gate cites 49 363) | **−8 B**, from deleting `step={50}` (§6) |
| CSS bundle | **168 319 B** | Larger than Phase 7's 164 325 because the adopted tree is larger; not a QML delta |
| a11y | **0 criticals** | |
| Goldens | **190 + 804 + 3306** @ 1e-9 | Unchanged |
| QML harnesses | `qml:render`, `qml:circuit` (49 assertions / 7 circuits), `qml:tasks`, `qml:ui` (57 guards) all pass | |
| Browser harnesses | **7 launch, 4 pass, 3 fail** | The 3 are the pre-existing `d = 2` expectation; see §8 |
| **`qml-browser-check`** | **13 assertions, all pass** | New. See §5 |
| Migration | up→down→up, single head `j5e8f1a4b7c2` | Lossy by design; §2 |
| Safety invariants | `celery==5.4.0`, soft/hard **8/15** unchanged · `qml_enabled: bool = False` · `requirements.txt` unmodified · `numpy==1.26.4` · no torch, no scikit-learn · `ai/rag.py` unmodified · **0 artifacts tracked** | All hold |

---

## 5. The QML Lab has now been rendered in a browser

Until this phase, **no part of this project had ever opened the QML Lab in a
browser.** All 24 pre-existing harnesses are `renderToString` harnesses, which
cannot see anything a browser decides at runtime.

`frontend/web/scripts/qml-browser-check.mts` makes 13 assertions that SSR
cannot, and all pass against a live stack:

- all four views render — Configuration · Circuit · Training · Results;
- a Radix `Select` **actually opens** and portals its options — 0 before, 4
  after: Variational classifier, Hybrid QNN, Quantum kernel (LSSVM), Quantum
  regression — and `Escape` closes it;
- the options are confirmed to be portalled **outside the form subtree**, which
  is the structural reason SSR could never see them;
- every numeric field's default passes browser constraint validation (§6);
- an experiment is created, reaches `completed`, and Results renders
  **accuracy 85.0 %**, matching the API's `0.85`;
- **polling stops**: the detail endpoint is requested once and never again
  across a 12 s window. Asserted in two halves — that polling happened, then
  that it ceased — because "zero requests" alone is also what a run that never
  started looks like.

Three of these assertions were unsound when first written and were corrected
before being relied on: scanning the page body for `/completed|failed/` matched
a *stale badge belonging to a different experiment* in the Recent rail, so it
passed during a run that created nothing at all. Every assertion is now scoped
to the id the server returned for that run.

---

## 6a. Phase 8D — defects found and fixed

| id | defect | fix | proof |
|---|---|---|---|
| — | `GamesPage.tsx` lost **20 assertions' worth** of teaching copy to `effdc6b` while keeping every control | `963c158` restores it | `render:games` 12/20 → **32 PASS / 0 FAIL**; 7 mandated strings each mutation-tested, 1 FAIL apiece, **no survivors** |
| **QL-019** | the samples field's `max` was the global limit, not the dataset's cap, so `checkValidity()` returned **true** on a value the server rejects, and the over-cap state was enforced by **silently disabling Train** | `17bafa0` | `max` 1000 → **100**, `checkValidity()` true → **false**, hint `20–1000` → **20–100**, and an `ErrorNote` naming the cap and the rejected value |
| **QL-005** | populations, probabilities and coherences rounded to 6dp **at computation** | `196c80f` moves it to the serialisation boundary | wire output byte-identical (`0.333333`); in-process now `0.3333333333333334`; 142 tests unchanged |
| **QL-017** | diagonal cells displayed `∠ρ = 0π rad` — a phase for a population, which is not defined | `053064e` suppresses it on the diagonal only | both the tooltip and the inspector panel, so they cannot contradict each other |
| — | two assertions were wrong about the **bytes** (`rho` vs `ρ`; a trailing period) | `4ea0c11` under the closed exception **D-060** | product mutation still fails both (2→3, 19→20) |

**One defect class, not two patches.** QL-018 and QL-019 are the same bug from
opposite sides — a constraint attribute disagreeing with the limits
`/qml/describe` publishes. `scripts/qml-constraint-check.mts` now asserts that
property directly: **134 checks over 12 algorithm/dataset pairs**, 3 of which
carry a cap tighter than the global max, and that count is itself asserted so
the sweep cannot pass by never meeting the case. Mutants: reinstating QL-019
→ 3 FAIL, reinstating QL-018 → 12 FAIL, flipping `min()` to `max()` → 5 FAIL.

**D-028 needed no fix: it was already applied.** The per-epoch evaluation term
shipped in `2ee0896` (Phase 5) and `limits.py:357` reads
`epochs * n_samples`, pinned by two tests including one that counts a real run
with `qml.Tracker`. **Only the record was stale** — `DECISIONS.md` still titled
it "proposed fix, not applied". Corrected. The capacity risk the brief flagged
**cannot arise**: `enforce()` calls `check()`, which compares only dimensional
values against the ceilings and **never consults `estimate_cost`**. No
previously-valid configuration becomes rejected, and no limit constant was
touched.

## 6. Defects found and fixed in Phase 8/8C

**QL-018 — the QML Lab could not submit a single experiment in any browser.**
`QmlConfigForm.tsx` set `step={50}` with `min={20}` on the Samples field. HTML
constraint validation therefore admits only 20, 70, 120, 170, 220…, and the
form's own default of **200** was invalid: Chromium refused to submit and
displayed *"the two nearest valid values are 170 and 220"*. `/qml/describe`
publishes `{default: 200, min: 20, max: 1000}` and **no step**, so the UI was
rejecting a value its own API accepts.

It survived seven phases of review because `step` is evaluated only by a live
browser — SSR renders the attribute and never calls `checkValidity()`. Fixed by
removing the step; guarded by an assertion over *every* numeric field, so the
class cannot return. Mutation-tested: reinstating `step={50}` fails 5 of the 13
browser assertions. (D-052)

**`bg-card` emitted no CSS.** Seven uses across five Qudit Lab components
referenced an undefined token, so those panels rendered fully transparent.
Changed to the existing `bg-raised`; no token added. Proven by computed style
in a browser, not by reading source: with the defect reinstated, 11 panels
compute `rgba(0,0,0,0)`; fixed, all 11 compute `oklab(0.188896 −0.000115968
−0.0253414 / 0.6)` — `#0f131f` at 60 %. A class-wide ratchet, `npm run tokens`,
now fails if any colour utility stops emitting a rule. (Phase 8 Stage 2.2)

**§2A.6's ERROR state is now rendered rather than regex-matched.** The
fail-closed path was previously evidenced by a regex over `useFeatures.ts`,
which constrained the implementation's spelling and would fail a correct
refactor. It is replaced by three render assertions that drive `/features` into
a settled error and check what the user gets: nav entry absent, `404 - State
Undefined` shown, no config form. Both forms were shown to fail the same
fail-open mutation before the regex was deleted. (D-053)

---

## 7. Not verified

Stated plainly, because this is the section that matters for a go/no-go.

- **No live Gemini call has ever been executed.** The explain path is exercised
  against a stub only.
- **`bench_qml.py --full` has never run on target hardware.** All performance
  figures anywhere in these documents are simulator figures from this sandbox.
- **No real broker, no prefork pool, no signal-based time limit.** Celery ran
  eager or not at all. `.apply()` proves the task body executes and returns;
  **it does not exercise the broker, serialisation, prefetch, the worker's
  signal handling, or the time limits themselves** — which is precisely what
  MT-004 is for, and why MT-004 is first.
- **No Docker, no GPU, no OOM-kill path.**
- **Concurrency was never tested under genuine parallel load** (MT-010).
- **Identity with the pre-QML build is behavioural, not byte-level.** With the
  flag off: 59 OpenAPI paths, none containing "qml"; with it on, 66 — the 7
  added are all `/qml/*`, 0 removed, 0 non-QML specs differ. The bundle is
  **not** byte-identical (+1613 B JS, +923 B CSS versus pre-QML `46576c8`,
  100 % attributable to QML code). Phase 7 resolved this as behavioural
  identity, and that is the claim being made here — nothing stronger.
- **Open defect ledger:** QL-005 (`round(…, 6)` at `simulator.py:140,151,160` —
  computation-vs-presentation still undecided), QL-015 (toast anchoring),
  QL-016 (preset truncation ≤1366 px), QL-017 (phase-view sub-label). None
  blocks release; none has a catching script.
- **D-028 stands unapplied:** `limits.estimate_cost` undercounts by
  `(epochs − 1) · n_samples`. The quoted cost of a run is lower than the run.
  The fix is specified and deliberately not applied.

---

## 8a. Phase 8D — gates, every number measured in this session

| gate | measured |
|---|---|
| `pytest` | **1304 passed, 5 skipped** (388.8 s), 0 regressions |
| `ruff` | **118 on HEAD = 118 on base `6414263`**, 0 new |
| `npm run typecheck` | **0 errors** |
| `npm run build` | PASS; shared **641 361 B** on HEAD **= 641 361 B** on base; `QmlLabPage` **49 740 B** vs **49 355 B** (+385 B, the QL-019 error and cap logic) |
| CSS | **168 319 B**, byte-identical to base including the content hash ⇒ **0 rule-level diff** (both fixes reuse existing tokens) |
| `qml-browser-metrics.mts` | **16 / 16**, mutation-tested |
| `qml-constraint-check.mts` | **134 / 134** over 12 pairs, 3 mutants killed |
| `qml:circuit` | 49 assertions, PASS |
| `qml:ui` | 57 contract guards, PASS |
| token ratchet | PASS — 107 utilities scanned, **0 new dead** |
| migration | single head **`j5e8f1a4b7c2`** |
| **K (the 57)** | **24** — codelab 3, results 2, p5 19, games **0** |

**Not re-measured this session, and therefore not claimed:** a11y criticals,
the 190/804/3306 goldens, the CSS diff against pre-QML `46576c8` (the diff
above is against `6414263`), the 1366×768 viewport, and the `celery` 8/15
safety count. Phase 8C's report carried Phase 8's numbers for these; this one
does not carry them at all rather than restating a figure it did not take.

**Still open in the ledger: QL-015 and QL-016 were not attempted.** QL-015
(toast occlusion, local fix only) and QL-016 (preset-card truncation at
1366×768) remain exactly where they were. Neither was started, so nothing about
them has changed and no claim is made about either.

## 8. The pre-existing harness suite, exactly as it stands

**The suite is red. 57 assertions fail. This phase changed none of them.**

| Script | PASS | FAIL |
| --- | ---: | ---: |
| `render:results` | 39 | **8** |
| `render:codelab` | 6 | **9** |
| `render:p5` | 14 | **20** |
| `render:games` | 12 | **20** |
| | | **57** |

The other 20 scripts in the sweep pass. These 57 reproduce Phase 7's counts
exactly, fail on `main @ 045b966`, fail with `QML_ENABLED` unset, and load no
QML module. **They pre-date the QML Lab and are not caused by it** — but they
are also not fixed by it, and an operator reading a "green suite" claim
elsewhere should treat it as wrong.

**Fixed on their merits: 0. Tabled for the owner: 34. Recorded as
uncategorised or unconfirmed, with evidence: 23.**

Every one of the 57 would require changing an expected string, or a judgement
that belongs to the code owner. None was changed. The full table — each row
carrying the mandatory *"what regression would go undetected if this were
approved"* field — is **`docs/qml/08-assertion-proposals.md`** (D-054).

Two of the 57 are identified as genuine plumbing and are the first thing to
pick up next: `render-p5.mts:124` and `:144` assert that quiz and challenge
titles render, but those titles are Radix `SelectItem`s — portalled, and so
unreachable by `renderToString` no matter how correct the product is. That is a
browser-path fix, now possible for the first time.

**Three browser harnesses also fail**, all on the same pre-existing
expectation: `browser-verify-qudit-lab`, `browser-verify-new-features:121` and
`vision-qa-master-suite` expect four dimension buttons (`d = 2, 3, 4, 5`).
`QuditLabPage.tsx:208` renders `[3, 4, 5]` — there is no `d = 2`, deliberately,
because d=2 is a qubit. Changing `4` to `3` would change an expected value, so
it was not done.

---

## 9. Summary for the person deciding

The QML Lab is feature-complete, flag-gated, off by default, and provably
inert when off. It has now been driven end to end in a real browser for the
first time, which immediately surfaced a defect that made the feature unusable
and that seven phases of source review had missed.

What stands between here and production is **MT-004 → MT-001 → MT-006 →
MT-010** on real infrastructure, and a decision on the 34 tabled assertions.
Neither is a code change. Both are judgements someone other than the author
should make.
