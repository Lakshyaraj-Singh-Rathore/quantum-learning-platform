
## M4 — content and tooling findings (2026-10-04)


### M4-1: RAG tag inference matches substrings, so ordinary English produces false tags

`infer_tags()` in `backend/app/ai/rag.py` tags a lesson when any keyword from
`TAG_KEYWORDS` appears as a *substring* of the text. Several keywords are common
English words, so incidental prose triggers unrelated tags:

| Keyword | Fires on | Example false positive |
|---------|----------|------------------------|
| `while`, `conditional` | the word "while" | `01_qubits` — no dynamic circuits in it |
| `algorithm` | "why quantum algorithms work" | `01_qubits`, `04_measurement`, `09_quantum_noise` |
| `search` | "research", "searched" | any lesson using those words |

Measured: **9 of 13** lessons carry at least one tag that does not describe
their content. This is pre-existing, not introduced by the M4 rewrite; the
rewrite of `01_qubits` added one (`algorithms`) and inherited `dynamic`.

**Impact.** Moderate. Tags filter RAG retrieval, so noise here degrades
retrieval precision. Curriculum *placement* is unaffected — that uses the topic
registry, not tags. No lesson content is wrong.

**Proposed minimal fix (not yet applied, needs approval).** Add a per-lesson tag
override using the same HTML-comment mechanism already used for
`<!-- track: circuit -->`, e.g. `<!-- tags: qubit, superposition -->`. This is
additive, needs no front-matter parser, and keeps the keyword fallback for
lessons that do not opt in. A word-boundary regex alone would *not* fix this,
because `algorithm`, `gate` and `measure` genuinely appear as words.

**Status:** DOCUMENTED, not fixed. Deliberately out of scope for Batch 1
(content rewrite); flagged so it is not mistaken for content error.

### M4-2: The RAG chunker split lessons inside fenced code blocks

`chunk_markdown()` split on `\n(?=#{1,3}\s)`. A Python comment such as
`# run the circuit` matches that pattern, so any lesson containing commented
code was cut mid-block, leaving unbalanced fences and a truncated snippet.
Confirmed on the rewritten `01_qubits`: chunk 10 ended at
`from qiskit import Qu`.

**Status:** FIXED. `split_on_headings()` now tracks fence state. Regression test
`test_chunking_never_splits_inside_a_code_block` added. Verified: 0 unbalanced
chunks across all 13 lessons.

### M4-3: `10_gates_bootcamp` used raw HTML that the renderer escapes

The self-check answers were wrapped in `<details><summary>Answers</summary>`.
The renderer is `react-markdown` with `remark-gfm`, `remark-math` and
`rehype-katex` but **no `rehype-raw`**, so the tags were escaped and learners saw
literal `<details>` text instead of a collapsible block. Confirmed by rendering
the file through the production component.

**Status:** FIXED during the rewrite — replaced with a plain `### Answers`
heading, and `validate_lesson.py` now rejects raw HTML so it cannot return.

### M4-4: `05_deutsch_jozsa` documented an example that gave the wrong answer

The previous text said its 2-qubit example returns `1` every time. It returns
`0`. The oracle's target was prepared in $|+\rangle$, which is a $+1$ eigenstate
of X, so $X|+\rangle = +|+\rangle$ and no phase is kicked back; the state stayed
$|+\rangle|+\rangle$ and every function looked constant. Verified: after
`H, H, CNOT` all four amplitudes are exactly 0.5.

**Status:** FIXED. The lesson now prepares $|-\rangle$ with `x(1)` before `h(1)`
and explains why the eigenstate choice is what makes kickback work.

### M4-5: "Purity bottoms out at 0.5" is only true for pure dephasing

The noise lesson claimed a fully decohered single qubit has purity 0.5. That is
correct for **dephasing** (verified: 0.5000 at $T_2 = 0.01\,\mu$s with T1 huge),
but strong **T1 relaxation** drives the qubit to $|0\rangle$, which is pure — so
purity returns to 1.0 while fidelity falls to 0.5.

**Status:** FIXED. The lesson now shows both regimes in a table, since reading
purity and fidelity together is what distinguishes mixing from relaxation.

### M4-6: `format_lesson.py` initially merged unrelated display-maths blocks

Its collapse regex was `\$\$\n(.*?)\n\$\$`, which also matches the *closing*
delimiter of an already single-line block. This swallowed everything up to the
next block, merging unrelated maths and flattening headings into body text.

**Status:** FIXED. Delimiters are now anchored to whole lines
(`^\$\$\s*$\n(.*?)^\$\$\s*$`). The one damaged file was repaired, and the
validator gained a rule rejecting headings merged with body text.

### M4-7: `06_grover` bit-order convention mismatch (self-corrected)

My first version of the Grover helper indexed its `marked` string in qubit order
while Qiskit bitstrings are qubit-0-rightmost, so `grover(2, "01", 1)` returned
`{'10': 2048}` rather than the `{'01': 2048}` I had claimed in the answers.
Caught by executing the code rather than reading it.

**Status:** FIXED. The helper now takes the marked string in Qiskit display
order, and the empty-X-list case is guarded.

### M4-8: `format_lesson.py` merged unrelated blocks (self-corrected)

Its collapse regex `\$\$\n(.*?)\n\$\$` also matched the *closing* delimiter of an
already single-line block, merging unrelated display maths onto one line and
flattening headings into body text.

**Status:** FIXED. Delimiters are anchored to whole lines. The validator now
rejects headings merged with body text, so the damage cannot pass silently.

### M4-9: Tracker progress must be recorded per physical lesson

A target row's status is driven by its primary `lesson_slug`. Marking rows by
`additional_existing_lessons` would falsely report a lesson as rewritten — for
example `05_deutsch_jozsa` appears as an additional lesson on M4-B06, whose
primary is `13_classical_bit_vs_qubit`.

**Status:** RESOLVED. Progress is recorded per physical lesson in a
`lesson_progress` map, carried across regeneration and checked by
`test_rewritten_lessons_pass_the_authoring_standard`.

### M4-10: Still open after Batch 1

- **82 of 97 target items have no registered topic.** Not addressed: creating
  them is the separate topic-expansion phase, deliberately not started.
- **Inferred-tag defect (M4-1)** remains unfixed pending a separate decision.
  Rewrites were written to avoid adding misleading tags where avoidable, but the
  substring matcher still fires on ordinary English in 9 of 13 lessons.

### M4-11: Adding a topic requires a migration, not just a registry edit

`app/curriculum.py` is imported only by Alembic migrations, tests and scripts.
There is **no runtime sync** from the registry into the database, so adding an
entry to `TOPICS` changes nothing for a running service until a new Alembic
revision inserts the row.

**Status:** DOCUMENTED in the topic-gap analysis. Relevant to any future
approval: approving the topic architecture is a separate decision from
approving the migration that implements it.

### M4-12: The target list double-counts quantum cryptography

`Quantum Key Distribution` (section E, algorithms) and `Quantum Cryptography`
(section J, communication) describe the same subject. The target list therefore
holds 96 distinct subjects across 97 items, so any coverage percentage computed
against 97 is marginally pessimistic.

**Status:** FLAGGED, not silently merged. Deduplicating the target list is a
curriculum decision, not a documentation one. The proposal assigns both to a
single `comm.cryptography` topic and records the discrepancy.
