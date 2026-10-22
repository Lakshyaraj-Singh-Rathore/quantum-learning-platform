# 08 — Assertion proposals (Phase 8, Stage 3)

**Status: OPEN. 57 assertions fail. 0 were changed. 34 are tabled below for the
owner's decision; 23 are recorded as uncategorised or unconfirmed, with their
evidence.**

This document exists because the alternative — reporting a green suite — would
require changing assertions whose meaning I am not entitled to change. Nothing
here has been applied. Every row is a request, not a record.

---

## 1. What was measured, and how to reproduce it

From `frontend/web`, on `arena/63ae45b4-quantum-learning-platform` at the commit
that adds this file:

```
npm run render:results    # 39 PASS /  8 FAIL
npm run render:codelab    #  6 PASS /  9 FAIL
npm run render:p5         # 14 PASS / 20 FAIL
npm run render:games      # 12 PASS / 20 FAIL
                          # ----------------
                          #          57 FAIL
```

57 reproduces exactly as Phase 7 recorded it (`07-verification.md` §2G.2). The
four counts are unchanged, so nothing in Phases 1–8 moved this number in either
direction. The other 20 scripts in the sweep are green and are not discussed
here.

**These 57 pre-date the QML Lab.** They fail on `main` at `045b966`, they fail
with `QML_ENABLED` unset, and none of them loads a QML module. They are in
scope for Phase 8 only because §2I.3 asked for them to be triaged, not because
QML caused them.

---

## 2. The rule applied

The line is **whether the assertion's meaning changes** — not whether the
product or the test is "at fault", which is the same claim wearing two hats.

*Plumbing, which I may fix and commit:* a browser path, a port or base URL, a
race or ordering dependency, re-pointing a selector after a rename **while
targeting the same element**, making a vacuous test actually assert.

*Meaning, which only the owner may change:* an expected value, number or
string; weakening a `.toBe`; narrowing the cases covered; inspecting a
different element; deleting a test — including the deletions in costume
(`.skip`, `xit`, `todo`, commenting out, `if (false)`, an early `return`,
"redundant", a swallowing `try/catch`).

Every one of the 57 turned out to sit on the meaning side or to be
undecidable without a judgement call. **That is why the fixed count is zero.**

---

## 3. The 57, accounted for

Classification is mechanical: extract the string each failing assertion
expects, then ask whether that string exists anywhere under `frontend/web/src`.

| Class | Count | What it means |
| --- | ---: | --- |
| **Expected copy absent from the product entirely** (plain literal) | **34** | The UI has no such text. Any fix changes the expected string. **Tabled in §4.** |
| Expectation is interpolated (`${...}`) | 6 | The classifier cannot resolve it; needs a render dump per case. §5. |
| Assertion has no string literal (structural/array checks) | 7 | Needs reading per case. §5. |
| Mixed — some expected strings present, some absent | 5 | Partially drifted. §5. |
| Expected string **is** in `src/` but is not rendered on the path under test | 5 | Possibly plumbing, possibly a conditional-render regression. §6. |
| **Total** | **57** | |

**The classifier's limits, stated so they are not mistaken for findings.** It
matches literal substrings against a concatenation of `src/**/*.{ts,tsx}`. It
cannot see template interpolation, it cannot tell a comment from JSX, and a
string present in `src/` is not necessarily reachable on the route under test.
The 34 in §4 are the subset where it is reliable, and each was spot-checked by
hand against the component that should carry the text.

---

## 4. Proposals — 34 rows

Columns are: **(1)** harness and line · **(2)** the assertion verbatim ·
**(3)** what I propose · **(4)** the behaviour it protects today · **(5)**
evidence of the change · **(6) what regression would go undetected if this were
approved** · **(7)** my recommendation.

**On field (5) — CORRECTED BY THE REVIEWER. The requirement stands; it was
never unsatisfiable.**

The Phase 8 agent reported that `git rev-list --count origin/main` is **1** and
concluded the repository is a single squashed commit with no "before" to cite,
recommending the requirement be withdrawn. **That measurement was an artefact of
a shallow clone, not a property of the repository.** Both the agent's sandbox and
the reviewer's were provisioned at depth 1:

```
$ git rev-parse --is-shallow-repository   # -> true      <-- the tell
$ git rev-list --count origin/main        # -> 1         <-- meaningless while shallow
$ git fetch --deepen=400 origin
$ git rev-list --count origin/main        # -> 253       <-- the real history
```

**A commit count of 1 from a shallow clone is the most dangerous number in a
report: it is a true measurement of the wrong thing.** `--is-shallow-repository`
must be checked before any conclusion is drawn from history. This is a known
failure mode in this project and it recurred here.

Field (5) is therefore **satisfiable and is now supplied for the rows where it
changes the verdict.** `git log -S` resolves the strings directly:

```
$ git log --oneline --all -S"Nothing runs until you press Build" -- frontend/web/src
effdc6b feat: deliver QuantumLearn AI platform v1.0.0
5a04a17 P3: Code Lab editor in the new UI
```

### 4.0 RECLASSIFICATION: some of these rows are product regressions, not stale tests

This matters more than the field itself. §2I.3's **allowed** column is "real
product defect — fix the product, the assertion was right." Rows that were tabled
as needing an expected-string change belong there instead **if the string was
removed from a feature that still exists.** The history answers that question,
and for Code Lab it answers it decisively:

| | `38ef458` (`effdc6b`'s parent) | `origin/main` today |
|---|---|---|
| `"Nothing runs until you press Build"` | **present**, `CodeLabPage.tsx:305` | **absent** |
| `"treat it as a starting point, not an answer"` | **present**, `:306` | **absent** |
| The AI drafting feature itself | present | **still present** — `AI Code Assistant`, `Draft Code into Editor`, Gemini writes into the editor |

`effdc6b` (2026-10-20) **rewrote** `CodeLabPage.tsx` — 329 insertions, 282
deletions — so this was a redesign, not a deletion of the page. But the redesign
kept the AI feature and dropped its two safety sentences. What the card says now
is only:

> Describe a circuit algorithm and Gemini will draft code into the editor.

The sentences that told a student *the draft does not execute until you build it*
and *it is a starting point, not an answer* are gone, from a live feature that
writes AI-generated code into a learner's editor. **The assertion was right and
the product regressed.** The Phase 8 agent reached this suspicion on its own —
"investigate those as product regressions, not retiring them" — but could not
prove it without history. It is now proven.

**Consequence for the owner:** these rows should move out of the proposal table
and into the fix queue under §2I.3's allowed column, restoring the copy (or its
current-design equivalent) rather than rewriting the assertion to expect less.
The same test must be applied to the remaining rows, and each needs the same
question asked: *does the feature still exist?* Where it does, the assertion is
right. Where the feature was genuinely removed, the row stays tabled.

### 4.0a Adjudication of the sixteen — corrected, with two of the reviewer's own errors

The reviewer's original scan reported "16 strings present at `38ef458` and absent
from `main`." **That figure was wrong in two places, both from the scan rather
than the repository.** `git grep -F` is byte-exact, so it silently mis-reported:

| string as scanned | what the product actually contains | real verdict |
|---|---|---|
| `"F(ideal, noisy rho)"` | `"F(ideal, noisy ρ)"` — **Greek rho**, `ResultsViews.tsx:268`, `:542` | **not missing.** Encoding drift in the assertion. |
| `"No simulations yet."` | `"No simulations yet"` — **no trailing period**, `DashboardPage.tsx:372` | **not missing.** Punctuation drift in the assertion. |

So **fourteen** were genuinely absent, not sixteen. Both false negatives are the
same trap in a new costume: a byte-exact search reports absence for a string that
is present modulo one character, and an agent that trusts it files a defect
against working code. **Normalise before concluding a string is gone.**

Phase 8C then restored **seven** of the fourteen (`da5dd30`, `beaa468`,
`999fbfc`, `81972ee`, `b17e993`), across `CodeLabPage.tsx`, `GeometryViews.tsx`
and `ResultsViews.tsx`. While restoring the fidelity label it found a **live
defect that neither Phase 8 nor this reviewer had seen**: `ResultsViews.tsx:263`
read

```tsx
subtitle={noisy ? "F(ideal, noisy ρ)" : "F(ideal, noisy ρ)"}
```

— a ternary with **identical branches**, so a *noiseless* run was labelled as
fidelity against a noisy density matrix. That is the product-side twin of a
vacuous test: a conditional that cannot change its output. Present on `main` at
`51b9c26`, introduced by `effdc6b`, now `noisy ? "F(ideal, noisy ρ)" : "no noise
applied"`.

**Nine strings remain unadjudicated, and seven of them are one component.** All
live in files that still exist:

| string | component | does the feature survive? |
|---|---|---|
| `Controls are the left characters` | `GamesPage.tsx` | **yes** — games, shots and grading all still render |
| `Drag a gate from the palette` | `GamesPage.tsx` | **yes** |
| `Graded on state fidelity` | `GamesPage.tsx` | **yes** — `Graded` appears 6× but `fidelity` 0× |
| `Measurement outcomes` | `GamesPage.tsx` | **yes** — `Measurement` 1×, `outcomes` 0× |
| `Shots — fewer scores higher, but you must stay within tolerance` | `GamesPage.tsx` | **yes** — `Shots` 6×, `tolerance` 0× |
| `Two different states can produce this same histogram` | `GamesPage.tsx` | **yes** |
| `costs a single simulation` | `GamesPage.tsx` | **yes** |

`effdc6b` rewrote `GamesPage.tsx` at **480 insertions / 341 deletions** and kept
every control while stripping the explanatory copy. The pattern is identical to
Code Lab's, and these seven are most of `render:games`'s 20 failures — **the
largest single block of the 57.** The most consequential is *"Two different
states can produce this same histogram"*, the only sentence stopping a student
concluding that a matching histogram proves a matching state; and *"Shots — fewer
scores higher, but you must stay within tolerance"*, which is the scoring
contract the game grades against.

The two drift rows above are **not** regressions and do not belong in the fix
queue. Correcting an assertion to expect `ρ` instead of `rho`, or to drop a
trailing period, is an expected-string change — but it is not a weakening,
because the product's text is correct and the assertion was always wrong about
the bytes. Recorded as a narrow exception rather than silently applied.

### 4.0b Resolved by product fix — Phase 8D

The field-5 question (*does the feature still exist?*) put every row below in
the allowed column: the feature survived, the copy did not, so the assertion
was right and the product regressed.

| rows | component | commit | evidence |
|---|---|---|---|
| **20** | `GamesPage.tsx` | `963c158` | `effdc6b` rewrote the file 480+/341− keeping every control. `Graded` 6× but `fidelity` 0×; `Shots` 6× but `tolerance` 0×. `render:games` **12 PASS / 20 FAIL → 32 PASS / 0 FAIL**. |

The seven mandated strings were each mutation-tested by replacing them with a
plausible paraphrase: **every one produced exactly 1 FAIL and no mutant
survived**, so each is uniquely load-bearing rather than incidentally present.

A second group inside that commit failed on a **systematic Title Case restyle**
with no feature loss — `Clear Circuit`, `All Games`, `Level Complete`,
`Not Yet Completed`, `Measurement Histogram`, `Reset to Starter`. These were
reverted to the bytes the assertions pin rather than the assertions being
relaxed, because the information is identical either way and there is nothing
to trade. `Reset to Starter` was the exception that mattered: the control
resets to the *broken* circuit, so the restyle had also made it less accurate.

### 4.0c Resolved by assertion correction — Phase 8D

Two rows only, under the closed exception recorded as **D-060**. Neither is a
regression; both assertions were wrong about the bytes. Commit `4ea0c11`.

| row | expected | product | mutation check |
|---|---|---|---|
| `render-results.mts:67` | `F(ideal, noisy rho)` | `F(ideal, noisy ρ)` | product mutation: 2 FAIL → 3 |
| `render-p5.mts:191` | `No simulations yet.` | `No simulations yet` | product mutation: 19 FAIL → 20 |

### 4.0d The new K

| harness | Phase 8 | Phase 8C | **Phase 8D** |
|---|---|---|---|
| `render:codelab` | 8 | 3 | **3** |
| `render:results` | 9 | 3 | **2** |
| `render:p5` | 20 | 20 | **19** |
| `render:games` | 20 | 20 | **0** |
| **K** | **57** | **46** | **24** |

**The table does shrink substantially: 57 → 24, and 20 of the 33 closed came
from one component.** What remains is dominated by `render:p5`'s 19, which is
not a copy problem: those rows drive Radix `Select` and portalled listboxes
that SSR does not render at all, so whole sections fail together
(*every quiz is selectable*, *there is a submit control*, *every student is
listed*). That is the plumbing group identified in Phase 8 Stage 3 and it is
still **allowed but not implemented** — closing it needs the harness moved into
a browser, not more product copy. `render:codelab`'s 3 are the same family plus
one genuine naming question (the product renders **Build & Run**, the assertion
expects a build button), which is left tabled rather than guessed at.

### 4.1 `render-codelab.mts` — 8 rows

The Code Lab assertions are not cosmetic. Six of them guard **promises the UI
makes to a student about an AI-generated draft**. If that copy is gone from the
product, these are not stale tests; they are a regression in the safety framing
of an AI feature, and the correct response is to restore the UI, not to retire
the test.

| # | Assertion (verbatim) | Proposed | Protects today | Evidence | **(6) Regression that would go undetected** | Rec. |
| --- | --- | --- | --- | --- | --- | --- |
| C1 | `check("a reset-to-example control is offered", html.includes("Reset to example"));` | **None — investigate first** | A student who has broken their code can get back to a working example | `"Reset to example"`: 0 hits in `src/`. No equivalent control found on `CodeLabPage.tsx` | The escape hatch disappearing entirely. If this row is retired without finding the replacement control, nothing asserts a student can recover a broken editor | **Investigate as a product regression** |
| C2 | `check("the one rule is stated", body.includes("assign your circuit to a variable named"));` | **None — investigate** | The single contract the student's code must satisfy is stated in the UI | 0 hits. No substitute phrasing found | The Code Lab silently requiring a convention it never states. Every submission fails and the student is told nothing | **Investigate as a product regression** |
| C3 | `check("the AI box says the draft is not executed until you build it", body.includes("Nothing runs until you press Build"));` | **None — investigate** | The student is told AI output is inert until they act | 0 hits | An AI draft that looks like it already ran. This is the row whose loss is least visible and most consequential | **Investigate — treat as safety copy** |
| C4 | `check("the AI draft is called a starting point, not an answer", body.includes("treat it as a starting point, not an answer"));` | **None — investigate** | Calibrates trust in AI output | 0 hits | AI output presented as authoritative, with no hedge in the UI | **Investigate — treat as safety copy** |
| C5 | `check("the list of importable libraries is kept", body.includes("networkx") && body.includes("sympy"));` | **None — investigate** | The sandbox's actual capability is discoverable | `"networkx"`: 0 hits | A student guessing at imports. Also hides the case where the sandbox's library set shrank and the UI was updated to match, which is a backend change worth knowing about | **Investigate** |
| C6 | `check("the concrete-angles rule is kept", body.includes("Angles must be concrete numbers"));` | **None — investigate** | A documented constraint of the builder | 0 hits | Symbolic angles failing at build time with no prior warning | **Investigate** |
| C7 | `check("the stdout promise is kept", body.includes("print()"));` | **None — investigate** | `print()` output is promised to be shown back | 0 hits of the literal `print()` in `src/` | Students losing their only debugging channel with no UI statement that it exists | **Investigate** |
| C8 | `check("the build button is offered", body.includes("Build circuit"));` | `body.includes("Build & Run")` | A control exists that builds the circuit | `CodeLabPage.tsx` labels the control **`"Build & Run"`**. `"Build circuit"` occurs once in `src/`, not as this button | Almost nothing: the renamed control is still asserted to exist, and removing the button would fail the new form too. This is the cheapest and safest row in the document | **Approve** |

### 4.2 `render-results.mts` — 7 rows

| # | Assertion (verbatim) | Proposed | Protects today | Evidence | **(6) Regression that would go undetected** | Rec. |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | `check("Q-sphere explains latitude and phase", sphere.includes("Latitude is Hamming weight"));` | `sphere.toLowerCase().includes("latitude is hamming weight")` | The Q-sphere tells the reader how to read it | Product says: `"3D Interactive Q-sphere: click and drag to rotate, latitude is Hamming weight, colour is relative phase"` — **the explanation is present; only the capital L differs** | Very little. A case-insensitive match still fails if the explanation is deleted or the semantics change. It stops protecting the sentence-initial position of the phrase, which no requirement states | **Approve** |
| R2 | `check("Q-sphere warns it is not a Bloch sphere", sphere.includes("cannot show a mixed state"));` | **None — investigate** | The reader is warned the Q-sphere is not a Bloch sphere and cannot depict mixed states | 0 hits. The nearest text is `"Enable noise to see purity of the mixed state and shot leakage."`, which is a different claim | A noisy, mixed-state run rendered on a visualisation that cannot represent it, with the caveat gone. This is a correctness-of-teaching issue, not copy | **Investigate** |
| R3 | `check("a noiseless run says so on the fidelity gauge", html.includes("no noise applied"));` | **None — investigate** | A fidelity of 1.0 is explained as "no noise", not as a perfect result | 0 hits | A gauge reading 1.00 that a student reads as an achievement. §2G.6's existing QL entry on the fidelity gauge is the same area | **Investigate** |
| R4 | `check("a noisy run labels fidelity against the ideal state", noisyHtml.includes("F(ideal, noisy rho)"));` | **None — investigate** | The fidelity's two arguments are named, so the number is interpretable | 0 hits | An unlabelled fidelity number. Fidelity against *what* is the whole content of the metric | **Investigate** |
| R5 | `check("histogram offers the probability toggle", html.includes("Show probability instead of counts"));` | **None — investigate** | The counts/probability toggle is discoverable | 0 hits | The toggle vanishing, or losing its label | **Investigate** |
| R6 | `check("histogram offers the phase-colour toggle", html.includes("Colour bars by relative phase"));` | **None — investigate** | The phase-colour toggle is discoverable | 0 hits; `"relative phase"` appears 3× in `src/` but not as this control's label | Same as R5 for the phase channel | **Investigate** |
| R7 | `check("born-vs-shots compares exact and sampled", html.includes("exact \|psi\|²") && html.includes("1024 shots"));` | **None — investigate** | The Born-rule panel labels both series | Mixed: one operand present, one absent | The comparison losing the label that says which series is exact — the one thing that makes the panel a teaching artefact rather than two lines | **Investigate** |

### 4.3 `render-games.mts` — 14 rows

Three distinct shapes, each needing a different decision.

**(a) Emoji-prefixed headings — 1 row.** `G1` `render-games.mts:139`
`check("the objective is shown", body.includes("🎯 Objective") && body.includes(vault.prompt.slice(0, 40)));`
Proposed: `body.includes("Objective")`. Protects: each level states its
objective, and the objective shown is the one the API returned. Evidence:
`"🎯 Objective"` has 0 hits; the emoji convention appears to have been dropped.
**(6)** Dropping the emoji from the expectation loses nothing a requirement
states; but note the assertion has a **second operand** (`vault.prompt`) that
must be kept — approving a rewrite that drops it would stop checking that the
objective rendered is the API's objective and not a hard-coded string.
**Recommendation: approve, provided the second operand survives.**

**(b) Copy absent from the product — 11 rows.** Each expects a string with 0
hits in `src/`: `G2:146` `"Drag a gate from the palette"` · `G3:153`
`"Shots — fewer scores higher, but you must stay within tolerance"` · `G4:162`
`"Reset to broken"` · `G5:187` `"Level complete"` · `G6:197` `"Input |c…t⟩"` ·
`G7:198` `"Controls are the left characters"` · `G8:214` `"How the error shrinks
with more shots"` · `G9:220` `"costs a single simulation"` · `G10:221`
`"Measurement outcomes"` · `G11:222` `"Not yet"` · `G12:237` `"Edits used"`.
Proposed: **none** — investigate as a group. **(6)** These are the game's
rules, its scoring feedback and its result labels. Retiring them as a block
would leave the Games surface with assertions on its catalogue (which pass) and
none on what a level actually tells the player: a level could render with no
rules, no score and no pass/fail wording and the suite would stay green.
**Recommendation: investigate as one unit before deciding any of them.**

**(c) Teaching caveats — 2 rows.** `G13:256` `"Graded on state fidelity"` and
`G14:257` `"Two different states can produce this same histogram"`.
Proposed: **none**. **(6)** G14 is the sentence that stops a student concluding
that a matching histogram proves a matching state. If it is gone from the
product, the game is teaching something false by omission, and retiring the
assertion makes that permanent and invisible. **Recommendation: investigate;
this is the row I would least like to see approved silently.**

### 4.4 `render-p5.mts` — 5 rows

| # | Assertion (verbatim) | Proposed | Protects today | Evidence | **(6) Regression that would go undetected** | Rec. |
| --- | --- | --- | --- | --- | --- | --- |
| P1 | `check("there is a submit control", quizText.includes("Submit answers"));` (also at :135 for challenges) | **None — investigate** | A quiz can be submitted | `"Submit answers"`: 0 hits | A quiz with no submit path. Counted once here though it fails twice | **Investigate** |
| P2 | `check("the concepts line is kept", quizText.includes("Concepts:"));` | **None — investigate** | Each quiz names the concepts it covers | 0 hits | The concepts line disappearing | **Investigate** |
| P3 | `check("it points at the Composer to build", ...includes("Build your solution in the Composer"));` | **None — investigate** | The challenge tells the student where to do the work | 0 hits | A challenge with no stated route to attempting it | **Investigate** |
| P4 | `check("the shared circuit is shown", ...includes("Current circuit: 2 qubits, depth 3, static"));` | **None — investigate** | The circuit carried into the challenge is described | 0 hits | The student not being shown which circuit they are being asked about | **Investigate** |
| P5 | `check("recent simulations has an honest empty state", ...includes("No simulations yet."));` | **None — investigate** | An empty list says it is empty rather than rendering an empty box | 0 hits | An empty panel indistinguishable from a failed load — the exact failure mode the assertion was written to prevent | **Investigate** |
| P6 | `check("a learner can be inspected", ...includes("Inspect a learner"));` | **None — investigate** | The instructor view offers per-learner drill-down | 0 hits | The drill-down disappearing from the instructor surface | **Investigate** |

*(P1 covers two failing lines, so §4.4 is 6 rows over 7 failures; the arithmetic
in §3 counts failures, not rows.)*

---

## 5. Uncategorised, with evidence — 18

Recorded rather than guessed. Each needs a render dump and a reading; none can
be decided from a substring match, and deciding them by eye is how a meaning
change gets waved through.

**Interpolated expectations (6)** — the expectation is built from the fixture,
so "absent from `src/`" is meaningless for them:
`render-p5.mts:126` `` `${i + 1}. ${q.prompt}` `` ·
`render-p5.mts:155` `` `${key}=${String(value)}` `` ·
`render-games.mts:141` `` `Checked over all ${2 ** ((vault.n_controls ?? 0) + 1)} basis inputs` `` ·
`render-games.mts:157` `` `Tolerance: ${shots.epsilon}` `` ·
`render-games.mts:188` `` `Test cases passed ${table.testcases_passed}/${table.testcases_total}` `` ·
`render-games.mts:199` `` `${Math.round(row.certainty * 100)}%` ``.

**Structural assertions with no string literal (7)** —
`render-p5.mts:124` *every quiz is selectable* ·
`render-p5.mts:144` *every challenge is selectable* ·
`render-p5.mts:175` *all four headline metrics are shown* ·
`render-p5.mts:202` *common errors are listed* ·
`render-p5.mts:211` *every student is listed* ·
`render-p5.mts:229` *a fresh cohort gets honest empty states* ·
`render-games.mts:215` *every curve point is tabulated*.

> **One of these is already understood and is not copy drift.**
> `render-p5.mts:124` *every quiz is selectable* asserts that every fixture quiz
> title appears in the rendered HTML. `ChallengesPage.tsx:1230` renders those
> titles as `<SelectItem>` children of a Radix `Select`. **Radix portals its
> items to the document body on open, so `renderToString` can never emit them**
> — the assertion is unobservable by construction under SSR, regardless of
> whether the product is correct. The same applies to `:144` for challenges.
> This is the one group in the document that is **plumbing, not meaning**: §2I.3
> lists "browser path" as an allowed fix, and Stage 1 has made a browser
> available. Porting these two assertions to a browser harness is the correct
> fix and is **not done here** — it is the first thing I would pick up next.

**Partially drifted (5)** — some expected operands present, some absent:
`render-p5.mts:181` `"Concept mastery"` · `render-p5.mts:199` and `:246`
`"Simulation jobs"` · `render-games.mts:147` `"Clear circuit"` ·
`render-results.mts:124` (also listed as R7).

---

## 6. Present in `src/` but not rendered — 5, unconfirmed

`render-codelab.mts:105` and `:110`, `render-p5.mts:200` and `:201`,
`render-results.mts:125`. The expected string exists in the product, so the
failure is either a conditional-render path the fixture does not reach
(plumbing — fixable) or a component that stopped rendering text it still
contains (a product regression — reportable). **Both are consistent with the
evidence I have, and I did not resolve which.** They are listed here rather
than being split between §4 and a fix commit on a guess.

---

## 7. What would legitimately shrink this number

Not editing any row above. The honest routes are:

1. **Resolve §6's five.** If they are conditional-render plumbing, they become
   fixes. If they are regressions, they become defects — which is the better
   outcome.
2. **Port the two Radix-portal assertions to the browser** (§5). Allowed as a
   browser-path fix, and now possible for the first time.
3. **Investigate the Code Lab AI copy (C2–C7) and the Games caveats (G13–G14)
   as suspected product regressions.** If the copy was removed by accident,
   restoring it turns eight proposals into zero without touching a test.

Phase 8's experience supports (3) being worth doing. The one defect this phase
found in the QML Lab — **QL-018**, a `step={50}` that made the form's own
default fail browser validation and left the feature unable to submit a single
experiment — had been invisible for the same reason these have: no one had
executed the thing being asserted about. A suite that has been red long enough
becomes background noise, and genuine bugs hide in it.

---

## 8. Honest statement of what this phase did to the 57

- **Changed: 0.** No assertion in these four harnesses was edited, re-pointed,
  skipped, deleted or weakened.
- **Fixed: 0.**
- **Tabled for decision: 34.**
- **Uncategorised with evidence: 18.** **Unconfirmed: 5.**
- The suite is **red, and ends this phase red.** `K = 34` is not folded into any
  green figure anywhere in Phase 8's reporting, and `08-release.md` is written
  on the basis that these 57 are open.

Cross-referenced from `DECISIONS.md` as **D-054**.
