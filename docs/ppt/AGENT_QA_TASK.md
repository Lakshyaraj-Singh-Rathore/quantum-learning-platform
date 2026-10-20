# QA Task Specification — QuantumLearnAI

**Assignee:** vision-capable agentic AI
**Objective:** produce an evidence-backed status report of the platform as it actually
behaves. This is a finding mission, not a sign-off mission.

---

## 0. Ground rules — read before starting

**You are not being asked to confirm the platform works.** You are being asked to find
out whether it does, and to say so plainly when it does not.

Non-negotiable:

1. **A test you did not run is not a pass.** Never mark anything green because it
   "should" work, because the code looks right, or because a related test passed.
2. **A screenshot is required for every UI claim.** No screenshot, no claim. If you
   cannot capture it, write `NOT CAPTURED` and say why.
3. **Reproduce before reporting.** If something fails once, try again from a clean
   state. Then report it with the exact steps.
4. **Prefer an ugly truth to a tidy guess.** "I could not determine this" is an
   acceptable and useful answer. "Looks fine" is not.
5. **Do not fix anything.** You are observing. Note defects with severity and repro
   steps; a human decides what to fix.
6. **Record what you skipped and why.** A silent gap is the worst outcome.

**Severity scale — use it consistently:**

| Level | Meaning |
|---|---|
| S1 Blocker | Feature unusable, data loss, or wrong results presented as correct |
| S2 Major | Feature broken but a workaround exists |
| S3 Minor | Cosmetic, confusing, or inconsistent |
| S4 Observation | Not a defect; worth noting |

**Status values — only these four:**
`PASS` · `FAIL` · `PARTIAL` (works but with a defect) · `NOT TESTED` (with reason)

---

## 1. Preconditions

Before any testing:

1. Record the commit under test (`git rev-parse HEAD`) and the branch. Put it at the
   top of the report.
2. Confirm the stack is running: all five containers `Up` / `Up (healthy)`.
3. Capture the backend list from `GET /backends` and record which engines report
   available versus disabled **and the disabled reason string**.
4. Create a fresh test account. Do not reuse an account with existing state.
5. State the environment: OS, browser and version, viewport size, GPU present or not,
   and whether `GEMINI_API_KEY` and `QBRAID_API_KEY` are set.

If any precondition fails, stop and report that rather than testing a broken stack.

---

## 2. Phase 1 — UI inventory and interaction

**Goal: every control on every page is touched at least once.**

For each of the pages — Login, Learn, Curriculum, Topic detail, Composer, Challenges,
Code Lab, Games, Playground, Dashboard:

1. **Enumerate.** List every interactive element: buttons, links, inputs, selects,
   checkboxes, toggles, sliders, tabs, dropdowns, modals, tooltips, keyboard shortcuts,
   context menus, drag handles.
2. **Interrogate each one.** For every element, record:
   - What it does when activated
   - Whether the result matches its label or affordance
   - Whether it has a visible focus state when tabbed to
   - Whether it is reachable by keyboard alone
   - Whether it has an accessible name (screen-reader label)
   - What happens on invalid or empty input
3. **Settings:** open every settings/configuration surface (theme, backend selector,
   shot count, noise parameters, viewport, any preferences panel). For each control,
   set it to its minimum, maximum, and a mid value, and record the observed behaviour
   each time.

**Specific things likely to be wrong — check these deliberately:**

- **Composer palette keyboard access.** The drag tiles historically had `draggable` and
  `onClick` but no `role`, `tabIndex` or `onKeyDown`. Verify whether this is still
  true. Try to place a gate using only the keyboard. If you cannot, that is an S2.
- **Phase-colour toggle.** It is a checkbox labelled "Colour bars by relative phase" in
  the results panel. It requires a statevector. Toggle it on, screenshot; toggle off,
  screenshot. Confirm bar heights are identical and colours differ. This is the single
  most important visual claim in the project — verify it or disprove it.
- **Backend selector.** For each of the six engines, select it and record whether it is
  offered, disabled with a reason, or silently missing.
- **Error states.** Trigger at least three error conditions deliberately (invalid
  circuit, oversized circuit, unauthenticated request) and confirm the message is
  human-readable rather than a stack trace or a blank panel.
- **Empty states.** Visit each page with no data and confirm something sensible
  renders.
- **Loading states.** Note any control that gives no feedback while working.

---

## 3. Phase 2 — Circuit construction (drag and drop)

**Goal: establish that circuits built by dragging behave the same as circuits defined
in code.**

### 3.1 Single-gate sweep — exhaustive

For each of the 15 base gates (`h x y z s sdg t tdg sx id swap p rx ry rz`) and each of
the 11 controlled aliases (`cx/cnot ccx/toffoli mcx cz cy cp crz cswap/fredkin`):

1. Drag the gate from the palette onto the grid.
2. Confirm it lands where dropped.
3. Run at 2048 shots.
4. Record the counts.

**Check:** for the gates with known closed forms, verify against expectation:
- `h` on `|0⟩` → ~50/50 on 0/1
- `x` on `|0⟩` → all `1`
- `s²` must equal `z`; `t²` must equal `s`; `sx²` must equal `x`
- `cx` with control `|1⟩` flips the target; with control `|0⟩` does not

Any deviation beyond shot noise is an **S1** — a wrong quantum result presented as
correct is the worst possible defect in this product.

### 3.2 Collision behaviour

Drop a gate onto an occupied cell. Verify the global auto-insert-column policy: the
existing operation shifts right and nothing is overwritten. Test at layer 0, a middle
layer, and the last layer.

### 3.3 Two-qubit combinations — bounded exhaustive

Two qubits, three layers, gates drawn from `{h, x, z, s, t, rx(π/2), cx}`. That is
7³ = 343 ordered sequences. **Run all 343.** Verify each against a hand-computed or
independently-derived expectation. Record any mismatch.

### 3.4 Larger circuits — sampled

For 3–5 qubits: run at least 40 circuits mixing single-qubit and two-qubit gates,
including at least five with gates on non-adjacent qubits and five with measurement in
a non-final layer. Compare against Qiskit computed independently.

### 3.5 Parameterised gates

Enter parameters: valid (`pi/2`, `pi`, `-pi/4`, `pi*2`, `pi/4 + pi/2`), invalid
(`theta`, `x`, empty, `pi/`). Confirm valid ones execute and invalid ones are rejected
with a clear message rather than silently defaulting.

### 3.6 Dynamic circuits

Build each of: an `if` block, a `for` block, a `while` block, and one nested block.
Confirm each runs, and confirm the `while` cap (32 iterations) is enforced — try to
exceed it and record what happens.

### 3.7 Undo, clear, save, reload

Place several gates. Undo repeatedly. Clear. Save a circuit, reload the page, confirm
it persists. Delete it, confirm it is gone.

---

## 4. Phase 3 — Backend verification

**Goal: verify the backend independently of the test suite.**

Do **not** stop at "the test suite passes." Run `pytest`, record the result, and then
verify the following by hand.

### 4.1 Cross-backend agreement

Run the same Bell circuit on every available engine at 2048 shots. Record counts.

**Pass criterion:** only `00` and `11` appear, roughly 50/50, on every engine. Any
appearance of `01` or `10` beyond shot noise is an S1.

Note explicitly in the report that this is **agreement between simulators of the same
physics**, not validation against hardware.

### 4.2 Noise model

For each of: clean, mild (T1=50, T2=30), harsh (T1=2, T2=1, readout 0.05) — record
`P(odd parity)` on a Bell state. Expect approximately 0.000, 0.047, 0.210.

Then verify the **T2 clamp**: set T1=10, T2=100. T2 must clamp to **20** (2·T1), not
to 10, and the reason must be surfaced to the user.

### 4.3 Degradation

With credentials absent, confirm qBraid and CUDA-Q disable themselves **with an
explanatory message** rather than disappearing or throwing. Record the exact wording.

### 4.4 AI / RAG

With an API key set: ask a question and verify the answer cites curriculum sources.
Without a key: confirm the keyword fallback engages and Code Lab shows its
"AI generation is unavailable" notice with `aria-describedby`.

Confirm the AI **has no simulation tool** — attempt to get it to produce a measurement
result for a circuit that was never run, and record whether it refuses.

### 4.5 Games and autograding

For all 4 games across all 10 levels: attempt each level, submit a correct answer and
confirm pass; submit a deliberately wrong answer and confirm fail with useful feedback.

Verify the specific claims:
- Bell Builder grades on **fidelity**, not counts — submit `|Φ+⟩` where `|Φ−⟩` is
  expected and confirm it fails despite identical histograms
- Find the Bug counts edits correctly
- Grover Lab shows amplitude growing over iterations

### 4.6 Code Lab

For each of the 4 languages, run a valid program and confirm output. Then attempt:
a blocked import, a syntax error, a missing `circuit` variable, and an unsupported
gate. Confirm each is caught with a clear message.

### 4.7 Auth and roles

Register, log in, log out. Confirm an unauthenticated request to a protected endpoint
is rejected. If you can access instructor-only data as a student, that is an **S1**.

### 4.8 Limits

Attempt to exceed: 20 static qubits, 15 dynamic qubits, 4096 shots, the while cap.
Record whether each is refused cleanly and what the user sees.

---

## 5. Phase 4 — Cross-cutting

- **Responsive:** test at 1280, 768 and 375 px wide. Note anything unusable.
- **Keyboard-only:** navigate the whole app without a mouse. Note every dead end.
- **Console:** keep the browser console open for the entire session. Record every
  error and warning, with the action that triggered it.
- **Network:** record any request that fails, and any that leaks credentials or
  returns data the user should not see.

---

## 6. Report format

**Every finding must carry:** ID, severity, status, exact repro steps, observed
behaviour, expected behaviour, and evidence (screenshot or captured output).

Structure:

```
1. Environment and commit under test
2. Preconditions (all five, pass/fail)
3. Executive summary — counts by severity, and the five worst defects
4. Phase 1 — UI inventory and interaction
5. Phase 2 — Circuit construction
6. Phase 3 — Backend verification
7. Phase 4 — Cross-cutting
8. Defect register (table: ID, severity, area, title, status)
9. What could not be tested, and why
10. Honest overall assessment
```

Section 10 must answer, in plain language:

- Is the platform demoable end to end right now?
- Are the quantum results correct?
- Which headline claims hold up, and which do not?
- If you had to present this tomorrow, what would you be afraid of a judge clicking?

---

## 7. Anti-laziness clauses — enforce these on yourself

1. If a phase feels long, that is the point. Do not compress it by sampling what was
   meant to be exhaustive.
2. If you catch yourself writing "appears to work" or "seems correct", replace it with
   the observed value or mark it `NOT TESTED`.
3. If a control is hard to reach, that is itself a finding. Do not quietly skip it.
4. If ten things pass in a row, actively look for the eleventh that fails. A run of
   clean passes usually means you are testing the wrong thing.
5. Never report a number you did not observe. If you quote a count, it came from a run
   you performed in this session.
6. If you cannot complete a phase, say so explicitly and report partial results rather
   than implying completion.
