
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
