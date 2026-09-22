# QuantumLearn — UI audit

Prepared for review with a senior engineer. Every number below was measured by
driving the real pages, not estimated.

**Commit audited:** the state after the duplicate-control and game-integrity
fixes described in "Issues found and fixed".

---

## 1. Control inventory, measured per page

Counts come from rendering each page with a real login and inspecting the
widget tree. "Dupes" counts repeated button *labels* on one screen.

| Page | Buttons | Sliders | Selects | Expanders | Tabs | Dupes | Errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Home | 1 | 0 | 0 | 1 | 0 | 0 | 0 |
| Learn | 4 | 5 | 1 | 0 | 4 | 0 | 0 |
| **Composer** | **11** | **7** | **9** | **6** | **7** | 0 | 0 |
| Challenges | 3 | 0 | 2 | 0 | 2 | 0 | 0 |
| Dashboard | 1 | 0 | 1 | 0 | 2 | 0 | 0 |
| Code Lab | 4 | 0 | 1 | 3 | 0 | 0 | 0 |
| Games (catalogue) | 11 | 0 | 0 | 0 | 0 | 9\* | 0 |
| Playground | 3 | 10 | 0 | 0 | 7 | 0 | 0 |

\* Ten **Play** buttons, one per level, each with a distinct key. Repeated
label, not a duplicated control. Not a defect.

### Reading of the numbers

**The Composer is the outlier and is genuinely overloaded.** On one screen:
11 buttons, 9 selects, 7 sliders, 7 tabs and 6 expanders — 40 interactive
elements. Seven of those tabs are code exports (QASM, Qiskit, Cirq, PennyLane,
qBraid, Import, Save), which a first-time student does not need in order to
build a Bell pair.

**Everything else is reasonable.** Learn, Challenges, Dashboard and Code Lab
sit between 1 and 8 controls. The Playground's 10 sliders are the point of the
page — each one is a demonstration.

---

## 2. Issues found and fixed

### Critical — a wrong circuit could win a game level

`autograder.PASS_THRESHOLD` is `0.8`. That is right for a coding challenge with
partial credit, but a game level is a puzzle with exactly one answer, so a
0.75–0.99 score was reported as **Level complete**. On *Open the Vault* a
circuit that satisfied 6 of 8 truth-table rows scored 0.75 and would clear any
threshold below that.

**Fix.** Added `GAME_PASS_THRESHOLD = 1.0`. Any challenge carrying `game_meta`
is now only "solved" at a perfect score. Partial credit is still reported and
still feeds mastery tracking, and the message is explicit:

> Not solved yet — scored 0.75, and this level needs a perfect 1.00.

Ordinary coding challenges keep partial credit at 0.8.

### Critical — duplicated toolbar, and buttons that silently undid themselves

The React canvas draws **Qubits, Measure All, Normalize, Compact, Clear** along
its top edge. `composer.render()` then drew a second identical set below it.

The duplication was the visible half. The functional half was worse: the Python
copies mutated the session circuit and called `st.rerun()`, but the React
component was keyed on the constant string `"react_composer"`, so on the next
run Streamlit replayed the value the component had last sent — the circuit as
it was *before* the button press — and `set_circuit()` overwrote the change.

That single race explains all four reported symptoms: Clear, Reset to broken,
Measure All and Delete "not working".

**Fix.**
- `composer.render(secondary=True)` no longer draws the toolbar. One control,
  one owner.
- Added a grid epoch. Any Python-side edit bumps it, and the component is keyed
  `react_composer_{epoch}`, so it remounts seeded from the new circuit instead
  of replaying a stale one.
- Updates coming *from* the grid pass `from_grid=True` and do not bump the
  epoch, so dragging a gate does not remount the component mid-interaction.

Verified by driving the page: Delete takes 3 ops to 2, Clear takes it to 0,
Reset to broken restores the starter circuit exactly.

### High — the editor only reported mistakes after Build

`st.text_area` has no diagnostics, so a typo surfaced only after pressing Build
and waiting for the sandbox.

**Fix.** `lib/code_checks.py` runs on every keystroke and never executes the
program. It reports, with line and column:

- Python syntax errors
- imports the sandbox blocks (`os`, `subprocess`, `socket`, …)
- a missing `circuit` variable
- `qbraid.runtime`, which spends credits and is blocked
- QASM: missing header, missing qubit register, unknown gate names,
  undeclared registers, missing semicolons

Results are shown **by default**, above the editor, with a green "No problems
found" when the program is clean. The highlighted view auto-expands when there
is something to see and marks the offending lines.

Twenty tests cover it, including that valid Qiskit and valid QASM produce
**zero** findings — a checker that cries wolf gets ignored.

---

## 3. Remaining recommendation: the Composer

Not a bug, so not changed without your call. Three options, cheapest first.

**A. Move the export tabs behind one expander.** Seven tabs become
"Export & share". Removes 7 tabs from the default view. Roughly an hour.

**B. Split run configuration from the editor.** Run settings, noise model and
circuit analysis move into a right-hand column or a single "Advanced" panel,
leaving build → run → results as the visible path. Half a day.

**C. Progressive disclosure by lesson progress.** Beginners see the grid, Run
and the histogram; exports and noise unlock later. Best result, largest change,
and it needs a product decision about what a beginner should not see.

My recommendation is **A now, B before the demo**. A newcomer currently has to
scan 40 controls to find "Run".

---

## 4. Screenshots

The sandbox this was developed in cannot download a browser, so capture runs on
your machine:

```
docker compose up -d --build
pip install playwright && playwright install chromium
python scripts/ui_screenshots.py
```

Writes `reports/screenshots/01_home.png` … `09_game_level.png`, covering every
page plus one game level. `scripts/ui_screenshots.py` signs in with the seeded
instructor account and walks the navigation.

---

## 5. How to verify the fixes

```
cd backend  && PYTHONPATH=. ../.venv/bin/python -m pytest -q
cd frontend && PYTHONPATH=../backend:. ../.venv/bin/python -m pytest -q
```

Specific guards:

| Test file | Guards |
| --- | --- |
| `test_ui_integrity.py` | no duplicate toolbar; epoch keying; delete persists |
| `test_code_checks.py` | live diagnostics; no false positives on valid code |
| `test_quantum_games.py` | 100% required; buttons cannot solve a level |

By hand, on a game level: place a gate, press **Delete** — it goes. Press
**Clear circuit** — the grid empties. Press **Reset to broken** — the starter
returns. Submit a partly-correct circuit — it reports "Not solved yet" with the
score.
