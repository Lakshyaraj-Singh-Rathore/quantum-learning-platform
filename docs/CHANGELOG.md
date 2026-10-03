# Changelog

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
