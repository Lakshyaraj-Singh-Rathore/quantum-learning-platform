# Feature Traceability Matrix

Status of every feature requested by the master implementation prompt, verified
against commit `7ee6c01`. Locations are real paths in this repository.

**Status values:** Not started · In progress · Implemented · Testing · Verified · Blocked

---

## A. Curriculum content

| # | Feature | Status | Location | Verification |
|---|---|---|---|---|
| A1 | Quantum Mechanics | **Not started** | — | no lesson exists |
| A2 | Qubits | **Partial** | `content/01_qubits.md`, `13_classical_bit_vs_qubit.md` | duplicated across two files (audit §4) |
| A3 | Dirac Notation | **Not started** | — | used in `01_qubits` but never taught |
| A4 | Tensor Products | **Not started** | — | absent |
| A5 | Inner Product | **Not started** | — | absent |
| A6 | Superposition | **Partial** | within `01_qubits.md` | no dedicated lesson |
| A7 | Bell States | **Partial** | `content/11_bell_states.md`, `03_entanglement.md` | sequenced 8 lessons after general entanglement |
| A8 | Basic Quantum Gates | **Partial** | `content/02_gates.md`, `10_gates_bootcamp.md` | duplicated; no unitarity/reversibility/no-cloning lesson |
| A9 | Circuits and Results | **Partial** | `content/12_control_flow.md` | no prediction-exercise lesson |
| A10 | Teleportation | **Not started** | — | absent |

## B. Qiskit

| # | Feature | Status | Location | Verification |
|---|---|---|---|---|
| B1 | Composer | **Implemented** (tool) · **Not started** (lessons) | `frontend/circuit_composer/frontend/src/`, `frontend/web/src/pages/ComposerPage.tsx` | `render:composer` 36 checks pass |
| B2 | Sampler | **Not started** | — | no lesson; primitives not exposed to Learn |
| B3 | Estimator | **Not started** | — | absent |
| B4 | Bloch Sphere | **Implemented** (visualisation) · **Not started** (lesson) | `frontend/web/src/components/results/ResultsViews.tsx` | used as run output only |
| B5 | Histograms | **Implemented** (visualisation) · **Not started** (lesson) | results suite | bit-ordering toggle not yet a lesson feature |
| B6 | Quantum Noise | **Partial** | `content/09_quantum_noise.md` (1081 w) | **no interactive component**; sequenced after VQE, which inverts the dependency |

## C. Algorithms

| # | Feature | Status | Location | Verification |
|---|---|---|---|---|
| C1 | Deutsch–Jozsa | **Partial** | `content/05_deutsch_jozsa.md` | theory only; no learner-defined oracle, no query-complexity comparison |
| C2 | Grover | **Verified** | `content/06_grover.md`, `frontend/web/src/lib/grover.ts`, `src/components/grover/GroverLab.tsx`, `frontend/lib/grover_lab.py` | `golden:grover` 3306 values at 1e-9; `render:grover` 27 checks; over-rotation property asserted |
| C3 | Shor | **Not started** | — | prerequisites (QFT, phase estimation) also absent |
| C4 | QKD | **Not started** | — | absent |

## D. Missing foundations

| Section | Status | Notes |
|---|---|---|
| Mathematical Foundations | **Not started** | no complex numbers, linear algebra, probability, or group theory anywhere |
| Core Quantum Theory | **Partial** | measurement exists; density matrices, POVMs, channels, no-cloning absent |
| Advanced Gates and Circuits | **Partial** | dynamic circuits and control flow exist; transpilation, universality, resource estimation absent |
| Advanced Algorithms | **Not started** | QFT, phase estimation, BV, Simon, walks, amplitude estimation, HHL all absent |
| Variational and NISQ | **Partial** | `07_vqe_qaoa.md` exists; ansatz, optimiser loops, parameter-shift, barren plateaus, QML absent |
| Error Correction and Fault Tolerance | **Not started** | entirely absent, including mitigation |
| Hardware and Ecosystem | **Not started** | entirely absent |
| Communication and Simulation | **Not started** | entirely absent |

## E. Platform capabilities

| Feature | Status | Location |
|---|---|---|
| Circuit composer | **Verified** | shared source, both hosts |
| Playground / circuit playground | **Verified** | `src/pages/PlaygroundPage.tsx`, `render:playground` 20 checks |
| Command palette | **Verified** | `src/components/shell/CommandPalette.tsx`; ranking unit-tested in 3 modes |
| Accessibility audit | **Verified** | `scripts/a11y-check.mts` — 0 criticals, 7 pages |
| Empty/error/loading states | **Verified** | `scripts/states-check.mts`; `ErrorBoundary` added at `7ee6c01` |
| Security headers | **Verified** | `frontend/web/nginx.conf` |
| Theme-aware charts | **Verified** | `--accent-2` in `src/globals.css` |
| Responsive <900px notice | **Verified** | `src/components/shell/NarrowViewportNotice.tsx` |
| Structured learning paths | **Not started** | no path model (M0 provides the graph it will run on) |
| Prerequisite graph | **Implemented** | `backend/app/curriculum.py` (canonical data), `models/curriculum.py`, migration `f1a2b3c4d5e6`; 12 topics, 13 edges, cycle-tested |
| Difficulty levels | **Implemented** | `curriculum_topics.difficulty`, mirrored onto `lessons.difficulty` |
| Learning objectives | **Implemented** | `curriculum_topics.learning_objectives`, mirrored onto `lessons.learning_objectives` |
| Topic mastery tracking | **In progress** | `UserMastery.topic_slug` added and backfilled from authored assessment tags; legacy `tag` preserved. Reading/apply logic still pending |
| Placement diagnostics | **Not started** | — |
| Practice mode | **Not started** | — |
| Exam mode | **Not started** | — |
| Project-based learning | **Partial** | challenges exist (`render:p5`); no multi-stage projects |
| Virtual labs | **Partial** | Grover lab is the closest; no hypothesis/procedure/conclusion structure |
| Qiskit playground / sandbox execution | **Not started** | Code Lab executes, but no general Qiskit sandbox |
| Algorithm playground | **Not started** | — |
| Spaced repetition | **Not started** | — |
| Certificates | **Not started** | — |
| Reference library / glossary / formula sheet | **Not started** | — |
| Algorithm comparison tools | **Not started** | — |
| Classical-vs-quantum comparison | **Partial** | Grover lab compares query counts; nothing general |
| Experiment history | **Partial** | run cache exists; no learner-facing history |
| Saved circuits / projects | **Partial** | circuit IR persists in the composer; no named saved projects |
| Learning analytics | **Partial** | instructor dashboard exists (`render:p5`) |

## F. Infrastructure

| Feature | Status | Location |
|---|---|---|
| FastAPI backend | **Verified** | `backend/app/` |
| Multi-backend quantum execution | **Verified** | `backend/app/quantum/backends/` |
| Celery + Redis async | **Implemented** · **Blocked in sandbox** | grading fails with `Error -2 connecting to redis:6379`; graded passes unverified here |
| RAG ingestion | **Verified** | `backend/app/ai/rag.py :: ingest_content_folder` |
| AI tutor | **Implemented** | `src/pages/LearnPage.tsx` + `backend/app/ai/` |
| Rendering / golden harnesses | **Verified** | 190 + 804 + 3306 values at 1e-9 |
| Backend tests | **Verified** | 511 passed, 5 skipped |
| Frontend pytest | **Verified** | 418 passed, 77 skipped |

## F2. M3 — Curriculum UI (React)

| Requirement | Component / integration | API or data source | Test | Status |
|---|---|---|---|---|
| Curriculum overview | `pages/CurriculumPage.tsx` | `GET /curriculum` | `npm run curriculum` | **Verified** |
| Expandable sections | `components/curriculum/CurriculumBrowser.tsx` | canonical `position` from API | curriculum-check: aria-expanded, button semantics | **Verified** |
| Topic cards (title, difficulty, objectives, lesson count, state) | `CurriculumBrowser.tsx` `TopicCard` | `GET /curriculum` topic fields | curriculum-check | **Verified** |
| Topic detail by stable slug | `pages/TopicDetailPage.tsx` at `/curriculum/topic/:topicId` | `GET /curriculum/topics/{id}` | curriculum-check (8 assertions) | **Verified** |
| Required vs recommended prerequisites | `PrereqList`, detail page | `prerequisites[].kind` + `status` | curriculum-check: required/recommended distinct | **Verified** |
| Required prereq blocks with navigation | blocked banner + links | `status.ready`, `missing_required` | curriculum-check | **Verified** |
| Recommended prereq warns without blocking | advisory banner | `status.advisory` | curriculum-check | **Verified** |
| Anonymous browsing without false locks | server returns `unevaluated: true`; UI shows no lock | `build_curriculum(user_id=None)` | `test_anonymous_is_never_gated`, curriculum-check | **Verified** |
| Authenticated access states | topic cards reflect server decision | `status.ready` | `test_topic_detail_gates_authenticated_learner` | **Verified** |
| Progress from real data only | progress card + `StateIndicator` | `progress`, `mastery`, `completed` | `test_progress_percent_reflects_mastery` | **Verified** |
| Resume learning | resume button | `GET /curriculum/next` → `lesson_slug` | `test_next_exposes_a_resume_lesson_slug` | **Verified** |
| Lesson deep link | `/learn?lesson=<slug>` | LearnPage reads `useSearchParams` | manual (browser) | **Implemented, not automated** |
| Empty topic / empty section | neutral copy, not an error | `lessons: []` | curriculum-check | **Verified** |
| Loading / error / retry / not-found | Spinner, ErrorNote, 404 branch | — | `npm run states` (8 pages) | **Verified** |
| Narrow viewport | Tailwind stack, no horizontal scroll | — | source review only | **Not visually verified** |
| Keyboard + screen reader | real `<button aria-expanded>`, `sr-only` labels | — | `npm run a11y` (8 pages, 0 criticals) | **Verified** |

### F3. M1 — Non-Destructive Curriculum Integration

| Requirement | Where | Test | Status |
|---|---|---|---|
| Mapping report with confidence + evidence | `backend/scripts/curriculum_reports.py`, `docs/CURRICULUM_MAPPING.md` | `test_every_mapping_has_recorded_evidence` | Complete |
| Mappings derived from content, not filenames | `LESSON_TOPIC_EVIDENCE` cites lesson sections | manual review in the report | Complete |
| `algorithms -> algo.grover` stays flagged | `REVIEW_REQUIRED` | `test_inferred_mappings_are_flagged_for_review` | Complete, still flagged |
| Low confidence never grants mastery | `MASTERY_MAPPABLE_CONFIDENCE = ("high",)` | `test_low_confidence_mappings_cannot_grant_mastery` | Complete |
| Content-gap report | `docs/CONTENT_GAP_REPORT.md` | generated, not authored | Complete |
| UI renders from backend data | `CurriculumPage`/`TopicDetailPage` | `npm run curriculum` (29 checks x 2 modes) | Complete |
| Empty sections render, not hidden | `build_curriculum` | `test_empty_sections_are_still_emitted` + UI check | Complete, behaviour changed |
| Required vs recommended distinguished | `TopicDetailPage` prerequisite lists | 3 curriculum UI checks | Complete |
| Anonymous browsing correct | `status.unevaluated`, empty `missing_*` | anonymous `npm run curriculum` | Complete |
| Progress from real data only | `topic_mastery()` | backend tests | Complete |
| Resume from real backend data | `/curriculum/next` | UI checks | Complete |
| Empty/loading/error/not-found states | `CurriculumBrowser` | `npm run curriculum` + `npm run states` | Complete |
| Responsive + accessibility | — | — | **Unverifiable: no browser in this environment** |
| Downgrade investigated | `additional_topics` column | `test_downgrade_places_every_lesson_and_preserves_secondary_placements` | Complete, 13/13 |
| PostgreSQL staging validated | — | — | **Pending: PostgreSQL unavailable here** |
| Production migration NOT run | — | verified no `alembic upgrade` against production | Held |

## Known gaps

- **Visual verification was not performed.** No headless browser is available
  in this environment, so desktop/narrow/theme rendering was never inspected.
  Layout is asserted only through SSR markup and source review.
- **Authenticated UI is not covered by the SSR harness.** zustand v5 serves
  `getInitialState()` to `getServerSnapshot`, so any component reading the
  session through the hook renders the pre-hydration state under
  `renderToString`. This is a harness limitation only — the app is a
  client-rendered SPA. Covered instead by backend tests and manual checks.
- **`/curriculum/next` returns a topic's first lesson**, not the learner's
  furthest position. True "resume where I left off" needs per-lesson completion
  data, which `lesson_completions` does not yet populate.

## G. Cutover gates

| Gate | Status | Evidence |
|---|---|---|
| **P8 — personal UI testing** | **NOT STARTED — human task** | sidebar banner `data-cutover-gate`, plan doc block, `WEB_DEV.md` block |
| **P9 — cutover** | **BLOCKED on P8** | must not begin until P8 approved; markers stay up |

No agent can claim P8. It has not been performed.
