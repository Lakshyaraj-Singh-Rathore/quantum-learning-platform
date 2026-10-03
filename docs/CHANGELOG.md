# Changelog

## M3 Verification & Finalization

Status: **M3 verified and finalized.** No M4 content authoring was started.

### The 6-sections vs 10-sections discrepancy — resolved

The M3 live check reported "17 topics / 6 sections". Both numbers were correct
and the discrepancy had a single cause: at `c759dd0`, `build_curriculum`
contained `if not topics_out: continue`, which **dropped empty sections from the
API response**.

```text
Canonical roadmap sections:  10   (the registry defines all 10, A-J)
API-returned sections:       10   (after M1; was 6 at c759dd0)
Populated sections:           6   (17 topics live here)
Empty sections:               4   (mathematical-foundations, error-correction,
                                  hardware-ecosystem, communication-simulation)
```

The 4 empty sections are **intentionally deferred**, not accidentally omitted.
They are authored in M4. No topics or lessons were invented to inflate the
count. A second contributor was also fixed: the superseded registry defined an
`advanced-theory-circuits` section that the current registry drops, leaving an
orphan row that rendered as a nameless, letterless entry colliding at position
6. The migration now retires sections that are absent from the registry and
have no topics referencing them.

### Frontend Celery/Redis failure — classified and resolved

`tests/test_games_levels_render.py::test_a_win_stays_visible_while_the_circuit_is_unchanged`
was reported as a known pre-existing failure. It was reproduced at `c759dd0`
(the M3 base) and the file contains zero curriculum references, so it is not an
M3 regression.

Root cause, confirmed by direct API probe:

```text
Simulation failed: Could not enqueue job: Error -2 connecting to redis:6379
```

The test posts a circuit to a live API and polls for the grade; with no Redis
broker the job fails and the attempt grades `passed: False`. This is purely
environmental. Setting the existing config flag `CELERY_TASK_ALWAYS_EAGER=true`
runs the task in-process, and the same correct Bell circuit then grades
`passed: True, score: 1.0`.

With that flag the full frontend suite is **512 passed / 7 skipped / 0 failed**.
No test was weakened, deleted, or silently skipped, and no application
architecture was changed.

### Verified

- Curriculum integrity: 10 sections, 17 topics, 13 lessons, 24 lesson-topic
  links, 18 prerequisite edges, 0 orphans, 0 circular or self-referential
  prerequisites. Namespaced IDs unchanged.
- Many-to-many mapping intact: 9 lessons belong to more than one topic; 5 topics
  have more than one lesson. No reintroduced flat `topic_slug` assumption.
- API contract: anonymous and authenticated `/curriculum`, topic detail (valid,
  unknown, malformed -> 404), `/curriculum/next`, prerequisite-blocked topics,
  and malformed `evidence` as a JSON string all behave correctly.
- Prerequisites: required blocks; recommended is advisory only and never blocks.
- `PrereqList` is rendered by `TopicCard` (was previously dead code).

### Known limitations

- **Browser-level visual verification was not performed.** No browser binary, no
  Playwright or Puppeteer, and no way to install one (no root, `apt`
  unavailable). Automated render/state/a11y verification was completed instead.
  Desktop, narrow-screen and theme appearance remain unverified.
- **`/curriculum/next` returns `slug`, not `topic_slug`.** Phase 4 of the
  verification spec expected `topic_slug`. The API and frontend are internally
  consistent and both use `slug`; renaming would be a breaking change and adding
  a redundant alias was rejected as an unnecessary change. Flagged for a
  decision rather than silently altered.


## M1 — Non-Destructive Curriculum Integration and UI Implementation

Status: **complete except PostgreSQL staging validation, which is unavailable in
this environment and is reported as pending rather than faked.**

### Changed behaviour

- **Empty sections are now rendered instead of hidden.** The earlier build
  omitted sections with no published topics; the M1 spec requires them to
  render. `build_curriculum` emits all 10 sections, and the UI shows "No topics
  in this section yet." Hiding them made the curriculum look smaller than the
  roadmap promises and concealed the authoring gap.
- **Retired sections are cleaned up.** The superseded registry defined an
  `advanced-theory-circuits` section that the current registry drops. Upserting
  the current set left that orphan in place, where it rendered as a nameless,
  letterless entry colliding at position 6. The migration now removes sections
  that are absent from the registry **and** have no topics referencing them, so
  real content can never be stranded.
- **Downgrade no longer loses a lesson.** The old flat schema holds one
  `topic_slug` per lesson, so lessons belonging to two topics lost their
  secondary placement and lessons with no primary topic were left unplaced
  (12 of 13). Secondary placements are now written to an additive
  `additional_topics` column that pre-migration code never reads, and
  re-upgrading restores them. Verified: **13 of 13 lessons placed, 24 of 24
  placements survive a downgrade/upgrade round-trip.**
- **PostgreSQL compatibility fix.** The downgrade used `INSERT OR IGNORE`,
  which is SQLite-only and would fail outright on PostgreSQL. Replaced with
  `ON CONFLICT ... DO NOTHING`, supported by PostgreSQL 9.5+ and SQLite 3.24+.
  Found by static review, not execution — see the gap below.
- **Registry fix.** `13_classical_bit_vs_qubit` had `is_primary=False` for both
  of its topics, leaving it with no primary topic and `core.quantum_interference`
  with no primary lesson. It is now the primary lesson for
  `core.quantum_interference`, which its content supports directly
  ("The decisive experiment", "Now break the interference").

### Added

- `backend/scripts/curriculum_reports.py` — generates both reports from the
  registry and the real lesson files. Run rather than hand-edit.
- `docs/CURRICULUM_MAPPING.md` and `docs/CURRICULUM_MAPPING.json` — 24 mappings
  (17 high, 7 medium, 0 low; 13 primary, 11 secondary), each with recorded
  evidence drawn from actual lesson content, plus legacy assessment-tag
  mappings and the flagged `algorithms -> algo.grover` inference.
- `docs/CONTENT_GAP_REPORT.md` — coverage against the 97-item target
  curriculum: 7 existing, 8 partial, 82 missing, with an M4 authoring order.
  It names what is missing; it does not author it.
- Mapping-integrity tests: every mapping carries evidence, only known
  confidence levels are used, low-confidence mappings can never grant mastery,
  every lesson has exactly one primary topic, and the downgrade round-trip
  preserves every placement.

### Not done — PostgreSQL staging

PostgreSQL is **not installed** in this environment: no server binary, no
Docker, and no way to install one (no root, `apt` unavailable). The migration
has therefore still only been exercised on SQLite. This is reported as
**pending**, not as verified. The `INSERT OR IGNORE` fix above is a static-review
finding and must be confirmed by a real staging run before production.



Significant implementation changes, newest first. Kept deliberately short —
per-milestone detail lives in `IMPLEMENTATION_MASTER_PLAN.md`,
`FEATURE_TRACEABILITY.md` and `MASTERY_MIGRATION_REPORT.md`.

---

## M3 — React curriculum UI

**Commit: pending.** Makes the curriculum hierarchy reachable in the actual
application. Before this, the structure existed in the database and the API but
appeared nowhere a learner could see it.

**Added**
- `frontend/web/src/api/curriculum.ts` — typed client and hooks for the three
  curriculum endpoints.
- `frontend/web/src/components/curriculum/CurriculumBrowser.tsx` — expandable
  sections, topic cards, prerequisite presentation, state indicators.
- `frontend/web/src/pages/CurriculumPage.tsx` — overview, progress card, resume
  learning.
- `frontend/web/src/pages/TopicDetailPage.tsx` — topic detail at
  `/curriculum/topic/:topicId`, keyed on the stable namespaced id.
- Routes `/curriculum` and `/curriculum/topic/:topicId`, plus a sidebar entry.
- `scripts/curriculum-check.mts` (`npm run curriculum`) — 26 SSR checks in both
  anonymous and authenticated modes.

**Changed**
- `LearnPage` accepts `?lesson=<slug>` so the curriculum can deep-link into the
  existing lesson reader. Lesson URLs are unchanged.
- `GET /curriculum/topics/{id}` now returns `lessons`; `GET /curriculum/next`
  now returns `lesson_slug`. Both additive and backward compatible.
- a11y and states harnesses now cover 8 pages (was 7).

**Fixed**
- `topic_mastery()` assumed `evidence` was always a dict. One row holding a JSON
  string returned HTTP 500 for `/curriculum` for every learner. Now coerced
  defensively; a bad value costs an attempt count, not the page.

**Not done**
- Visual verification: no headless browser in this environment.
- Resume returns the first lesson of the recommended topic, not the learner's
  furthest position — that needs per-lesson completion data.

## M0 — Stable topic identifiers and mastery migration

**Commit `5f15db1`.** Replaced provisional flat topic slugs with permanent
namespaced identifiers (`qc.qubits`, `algo.grover`), converted lesson→topic to
many-to-many with confidence ratings, and split mastery into `user_mastery`
(raw legacy history), `topic_mastery` (derived, with provenance) and
`lesson_completions`.

Verified on an isolated database copy: 13 lessons placed, 0 orphans, legacy
rows byte-identical afterwards, merging tags averaged rather than duplicated,
unmappable tags preserved but never counted. Downgrade restores the prior schema.

**Not applied to production.** See `MASTERY_MIGRATION_REPORT.md`; awaits
approval.

Also fixed a latent bug: migration `f1a2b3c4d5e6` imported live data from
`app.curriculum`, so changing the registry broke `alembic upgrade head` from
scratch. The data it needs is now inlined and frozen inside the migration.

## M0 (superseded) — Curriculum hierarchy

**Commits `b6c5ce2`, `b219f7c`.** First pass: flat topic slugs, one topic per
lesson, mastery stamped onto `user_mastery.topic_slug`. Superseded by the
revision above, which the owner's M0 spec required.

## P0–P7 — Web UI redesign

Seven milestones rebuilding the React front end alongside the existing
Streamlit application. Complete except the cutover gates.

**P8 (personal UI testing) and P9 (cutover) remain gated** and must not be
marked complete by automated testing.
