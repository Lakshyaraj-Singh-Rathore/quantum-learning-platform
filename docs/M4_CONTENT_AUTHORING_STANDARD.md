# M4 Content Authoring Standard

The quality bar every lesson must meet, and the mechanical constraints the
repository actually imposes. Written against the code as it is, not as it
might ideally be.

---

## 1. How lesson content actually works

Verified against the current implementation.

| Concern | Reality |
|---|---|
| Storage | Plain Markdown files in `content/<slug>.md` |
| Lesson slug | The filename stem. `content/01_qubits.md` → `01_qubits` |
| Title | The first `#` heading. There is no front-matter parser |
| Ingestion | `app/ai/rag.py::ingest_content_folder`, idempotent, runs at API startup |
| Chunking | Split on `#`/`##`/`###`, packed to `CHUNK_TARGET_CHARS` = 1200 |
| Tags | **Inferred** from keywords (`TAG_KEYWORDS`), not declared. Vocabulary: `qubit`, `gates`, `measurement`, `entanglement`, `noise`, `decoherence`, `grover`, `algorithms`, `dynamic` |
| `track` | Optional `<!-- track: circuit -->` HTML comment; defaults to `theory` |
| Objectives | Read from the **topic** registry, not the lesson file |
| Difficulty | Read from the topic registry |
| Renderer | `react-markdown` + `remark-gfm` + `remark-math` + `rehype-katex` |
| Math | KaTeX 0.18. `$…$` inline, `$$…$$` display. **Not** MathJax |
| Code | Fenced blocks, styled but **not syntax-highlighted** |
| Exercises | No first-class exercise object. Authored as Markdown sections |

### Consequences you must respect

- **Do not add YAML front-matter.** There is no parser; it would render as
  literal text at the top of the lesson.
- **Changing a filename changes a stable slug.** Rename only with approval.
- **Headings matter twice** — they structure the lesson *and* define RAG chunk
  boundaries. One giant section produces one giant chunk, which degrades AI
  retrieval. Prefer several focused `##` sections.
- **KaTeX is not LaTeX.** Avoid commands KaTeX 0.18 lacks (no `\require`,
  limited `\newcommand`, no `align*` environment — use `aligned` inside
  `$$…$$`). `rehype-katex` is configured with `throwOnError: false`, so an
  unsupported command renders as **red error text rather than failing loudly**.
  Always proof-read rendered maths.
- **Code blocks are not highlighted.** A language tag on the fence is good
  practice for readers but produces no colouring today.

---

## 2. Required lesson structure

```markdown
# Lesson Title

<!-- track: theory -->        <- optional; only if this is a hands-on lesson

One-paragraph orientation: what this is, why it matters, what the reader will
be able to do, and how it connects to what came before.

## Learning objectives
- Define …
- Calculate …
- Construct …

## <Concept 1>
### Intuition
### Formal definition
### Mathematics
### Worked example

## <Concept 2>
…

## Common misconceptions

## Exercises

## Summary

## References
```

Not every lesson needs every heading — omit what is genuinely irrelevant
rather than padding. Every lesson **does** need a title, an orientation
paragraph, at least one worked example or practical demonstration, exercises,
a summary, and references.

---

## 3. Learning objectives

- **3–6 per lesson.**
- Measurable verbs: *define, explain, calculate, compare, construct,
  interpret, implement, analyse*.
- Avoid vague verbs: *understand, appreciate, learn about, know*.
- Every objective must be satisfied by content that is actually present, and
  exercised by at least one question in the exercises section.

---

## 4. Core theory

Order the exposition:

1. **Intuition** — what is going on, in plain language.
2. **Formal definition** — precise and unambiguous.
3. **Mathematical representation** — with notation explained on first use.
4. **Step-by-step reasoning** — show the intermediate steps.
5. **Interpretation** — what the mathematics means physically.
6. **Limitations and assumptions** — where this breaks down.
7. **Connections** — how it links to earlier and later lessons.

Rules:

- Explain every symbol when it first appears.
- For mathematics, show derivations where they genuinely aid understanding;
  do not dump algebra for its own sake.
- Distinguish a **definition** from an **interpretation** from an **analogy**.
- If you use a classical analogy, state explicitly where it stops working.

---

## 5. Worked examples

For numerical work, always show:

1. The given values.
2. The relevant formula.
3. **Why** that formula applies here.
4. Substitution.
5. Intermediate calculation steps.
6. The result.
7. What the result *means*.

Do not skip steps in beginner material.

---

## 6. Code and simulation

- Every code sample must run against **this repository's** pinned
  dependencies. Check `backend/requirements.txt` before writing an import.
- Do not introduce new dependencies, and never upgrade a project package just
  to make an example work.
- This repository pins **Qiskit 1.2.4** and **qiskit-aer 0.16.0**
  (`backend/requirements.txt`). Target those versions; note that Qiskit 1.x
  removed several 0.x APIs (`QuantumCircuit.bind_parameters`, `execute()`,
  `qiskit.Aer`), so older tutorial code will not run as written.
- **Every numerical result must be genuine.** Run it. If you cannot run it,
  either present the result as a theoretical value with its assumptions
  stated, or label it explicitly as pending verification.
- Fix random seeds when reproducibility matters, and say so.
- Label the backend (`statevector`, `qasm_simulator`, noise model, real
  device) for every result.
- Distinguish **simulated** results from **hardware** results.

---

## 7. Misconceptions

Include a misconception **only where it is actually relevant** to that lesson.
Repeating the same warning in every lesson is noise.

High-value distinctions, to be used where they belong:

- Superposition vs. classical uncertainty
- Measurement probability vs. a single measurement outcome
- Global phase vs. relative phase
- Entanglement vs. classical correlation
- Ideal simulation vs. noisy hardware execution
- Quantum speedup vs. universal superiority

---

## 8. Exercises

There is no grading object in the lesson schema, so exercises are Markdown.
**Do not claim an exercise is graded when it is not.** Where a quiz or
challenge exists for the topic, link to it; otherwise say answers are provided
below.

Provide a mix appropriate to the lesson:

- Conceptual questions
- Numerical questions
- Circuit interpretation
- Coding exercises
- Debugging questions

Every exercise needs a worked answer and an explanation. An exercise without
an answer is not an exercise.

---

## 9. References

Only real sources you have verified:

- Peer-reviewed papers
- Official documentation (Qiskit, NVIDIA CUDA-Q, IBM Quantum)
- Recognised textbooks
- University course material from a known institution

**Never fabricate** a URL, edition, page number, publication date, or author.
If you cannot verify a reference, omit it.

---

## 10. Topic mapping rules

- Use registered topic IDs only.
- Every lesson has **exactly one** primary topic.
- Add a secondary mapping only when the lesson materially teaches that topic.
- A topic may legitimately have several primary lessons; a lesson may not have
  several primary topics.
- Do not create orphan topics or orphan lesson rows.
- Do not change prerequisites to control display order.

---

## 11. Review gates

Each lesson needs **two** distinct reviews before it may be marked `verified`.

### Technical review
- Mathematical correctness, including normalisation and probability sums
- Gate matrices and state transformations
- Measurement probabilities and basis assumptions
- Circuit correctness, **including qubit-ordering convention**
- Code executes and produces the stated output
- Simulation results are genuine and attributed
- Algorithm complexity claims state their comparison basis
- References are real

### Instructional review
- Objectives are measurable and satisfied
- Difficulty matches the label
- Logical progression, no unexplained leaps
- Terminology consistent with the rest of the curriculum
- Examples are complete, with intermediate steps
- Exercises match the objectives and have answers
- Summary bridges to the next lesson

If independent reviewers are unavailable, the tracker records that the review
was performed by the implementation agent. It does **not** claim independent
peer review.

A lesson with a known unresolved critical issue must not be marked `verified`.

---

## 12. Definition of done

A lesson is done when all of the following hold:

- [ ] File is `content/<slug>.md`, slug unchanged (or approved change)
- [ ] Title is the first `#` heading
- [ ] No front-matter
- [ ] Sections present per §2
- [ ] 3–6 measurable objectives, all taught and exercised
- [ ] All maths renders under KaTeX (proof-read, not assumed)
- [ ] All code runs on the pinned dependencies, or is labelled unverified
- [ ] All numerical results are genuine and attributed
- [ ] Misconceptions section only if genuinely relevant
- [ ] Exercises have answers
- [ ] References verified
- [ ] Mapping: one primary topic, valid secondaries
- [ ] Prerequisites unchanged unless justified
- [ ] Retrievable by slug through the API
- [ ] Renders in the curriculum UI
- [ ] Tracker row updated with honest validation states
