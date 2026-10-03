# Implementation Master Plan

Sequenced from `docs/IMPLEMENTATION_AUDIT.md` (commit `7ee6c01`). Read that first:
several milestones below exist specifically to fix things the audit found.

Two governing constraints, both human gates, neither negotiable:

- **P8 (personal UI testing) is not started and cannot be done by an agent.**
- **P9 (cutover) is blocked on P8.** Nothing here touches default routing,
  Streamlit removal, or the cutover markers until P8 is signed off.

---

## Why the order below differs from the master prompt's phase list

The master prompt sequences P8 → P9 → curriculum. P8 is a human gate, so an
agent cannot execute it. Rather than idle, the plan front-loads the curriculum
restructuring, which is **independent of the cutover**: it touches the FastAPI
content model, the `content/` corpus and the Learn page, none of which are
affected by which front end is the default landing.

This is safe only because the restructuring is additive to the data model. If it
required changing what Streamlit reads, it would have to wait for P9.

---

## M0 — Stable topic identifiers (do this first)

**Why first:** mastery is keyed by tag, and tags are keyword-inferred noise
(audit §3.3). Every later milestone that gates, sequences or measures progress
depends on this being right. Building prerequisites on the current tags would
produce a graph that is confidently wrong.

**Scope**
- Add a `Topic` table: stable slug, title, section, difficulty, ordered position.
- Add an authored `topic_slug` foreign key to `Lesson`; keep `tags` intact for
  backwards compatibility with RAG and recommendations.
- Add `Lesson.prerequisites` — a self-referential many-to-many, or an
  association table with a `kind` (`required` / `recommended`).
- Add `difficulty` (`beginner` / `intermediate` / `advanced`) and
  `learning_objectives` (JSON list).
- Alembic migration that backfills `topic_slug` for the existing 13 lessons and
  **migrates existing `UserMastery` rows** onto the new identifiers rather than
  discarding them.

**Exit gate:** all 13 lessons carry a stable topic; existing mastery rows survive
with their scores intact; backend suite still green.

**Status: COMPLETE (commit pending).** 12 topics across 6 sections, 13
prerequisite edges, 10 sections seeded, all 13 lessons placed, zero unplaced.
Mastery rows stamped; unmapped tags left NULL rather than guessed. Verified
against a database seeded with the real 13 lessons and real mastery rows, and
the downgrade was run to confirm it restores the prior schema with every row
and score intact.

**Risk:** this is the one irreversible step. Get the migration right and test it
against a copied database before running it on real data.

## M1 — Curriculum hierarchy and resequencing

- Model the ten sections as curriculum modules; place topics within them by
  prerequisite order, not by original filename.
- Give every lesson an explicit `order_index` within its topic, replacing the
  filename-derived ordering.
- Fix the three sequencing inversions the audit found, in this order:
  1. Move `09_quantum_noise` **before** `07_vqe_qaoa` — VQE's motivation is
     device noise.
  2. Consolidate `03_entanglement` with `11_bell_states` — teach the concrete
     Bell case before or alongside the general concept, not eight lessons later.
  3. Consolidate `02_gates` / `10_gates_bootcamp` and
     `01_qubits` / `13_classical_bit_vs_qubit`, preserving every example and
     interactive activity from both.
- Classify anything that will not fit as supplementary or advanced rather than
  deleting it.

**Exit gate:** every one of the 13 existing lessons is mapped to a section and
topic, or explicitly classified as supplementary. No lesson is dropped.

## M2 — Lesson → resource linkage moves into content

- Move `DEMOS_FOR_LESSON` out of `LearnPage.tsx` and into the content model, so
  adding a lesson can attach a simulation without a front-end change.
- Link the three currently unattached lessons (07, 08, 09) to existing demos;
  `09_quantum_noise` is the longest lesson in the corpus and has no interactive
  component, which is the worst of the three.
- Extend linkage to cover playgrounds, assessments and reference material, not
  only demos.

## M3 — Curriculum navigation in the Learn page

- Section → module → topic → lesson hierarchy, expandable.
- Completion and mastery indicators per topic.
- Prerequisite warnings when a learner opens a topic without the foundations,
  with diagnostic-based skipping where a placement check supports it.
- Recommended next lessons, derived from the dependency graph.
- Search and filter by topic, difficulty and objective.
- Resume-learning, and a way to browse the whole curriculum without losing place.

**Exit gate:** prerequisite warnings demonstrably fire for a learner without the
required background, and do not fire for one who has it.

## M3 — Curriculum navigation in the Learn page

**Status: largely complete (commit pending).** Shipped as a React curriculum
section wired to the real API: overview, expandable sections, topic detail by
stable slug, prerequisite presentation, resume learning, and lesson deep links.

Two additive backend fields were needed because existing endpoints could not
support required UI states: `GET /curriculum/topics/{id}` now returns its
`lessons`, and `GET /curriculum/next` now returns a `lesson_slug` so resume can
open a lesson rather than only a topic.

Not done: visual verification (no headless browser in this environment), and
true resume-from-furthest-position, which needs per-lesson completion data.

## M4 — Content authoring for the seven empty sections

Authoring, not restructuring, and deliberately separate so it never blocks M0–M3.

Priority order, by dependency (audit §5):
1. **Mathematical foundations** — complex numbers, linear algebra, probability.
   Highest leverage: nearly every later topic assumes them.
2. **Core quantum theory** — density matrices, POVMs, interference, phase,
   channels, no-cloning.
3. **QFT and phase estimation** — prerequisites for Shor.
4. **Bernstein–Vazirani** before Deutsch–Jozsa where pedagogically useful.
5. Then: Qiskit lessons, remaining algorithms, NISQ, error correction, hardware,
   communication.

## M5 — Assessment, modes and analytics

- Topic quizzes and multi-part assessments, with explanations after answering.
- Practice mode (unlimited attempts, hints) and exam mode (timed, no hints,
  limited attempts) as genuinely distinct products.
- Concept checkpoints that gate progression; spaced repetition.
- Progress dashboard, experiment history, saved circuits and projects.

## M6 — Reference library and comparison tools

- Searchable glossary, formula library, gate reference.
- Reuse the five result visualisations as teaching components rather than only
  as run output.
- Algorithm comparison (query count, gate count, depth, resources) and
  classical-vs-quantum comparison with equivalent problem definitions.

## M7 — P8, then P9

**P8 is a human task.** When it is done, the acceptance evidence goes in
`docs/` and the cutover markers come down as part of P9.

---

## Standing rules for every milestone

- All displayed numbers come from the engine or from verified maths. Never
  hardcoded results.
- Existing slugs are never renamed; they are foreign keys into attempts,
  recommendations and chat history.
- Each milestone keeps the app runnable and the suites green
  (backend 511/5, frontend 418/77, plus the render, golden, a11y and states
  harnesses).
- Nothing is marked complete because its UI exists.

## Known blockers

- **Celery/Redis unavailable in this sandbox.** Graded challenge and game passes
  cannot be verified here; only the contract and the failure rendering are
  tested.
- **Lighthouse/axe not runnable.** `npm run a11y` is a WCAG 4.1.2 check, not a
  substitute for axe in a browser.
- **P8 is a human gate.** Cannot be executed or claimed by an agent.
