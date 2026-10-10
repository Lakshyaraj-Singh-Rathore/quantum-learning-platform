# M4 Implementation Ledger

Running record of the M4 implementation. Updated as work proceeds, so a
sandbox reset can be recovered from this file plus the pushed remote history
rather than by repeating completed work.

**Architecture approval reference:** `c8f7144` (Gate 1, accepted as design).

## 1. Authorization (effective 2026-10-10)

| Gate | Scope | Status |
|---|---|---|
| 1 | Architecture approval (design only) | **Approved** at `c8f7144` |
| 2 | Registry, topics, mappings, prerequisites, migration code | **Approved** |
| 3 | Migration execution — disposable local DBs only (SQLite / isolated local PG) | **Approved with limits** |
| 4 | Production migration | **NOT authorised** |
| 5 | Lesson authoring for all 54 approved topics | **Approved** |
| P8/P9 | Streamlit → React cutover | **Blocked** pending owner UI parity review |

Gate 3 limits: newly created, disposable local databases with synthetic data
only. Never shared staging, production, or any pre-existing database. The
database identifier is recorded below before each execution.

## 2. Verified baselines (measured, not assumed)

Measured at `c8f7144`, tree clean, before any code change:

| Suite | Command | Result |
|---|---|---|
| Backend | `cd backend && python -m pytest -q` | **595 passed, 5 skipped** |
| Frontend (Python) | `python -m pytest frontend/tests -q` | **418 passed, 77 skipped** |
| React unit tests | — | **none exist**; validation is the `render:*` / `a11y` / `states` / `curriculum` scripts, which need a live API |

Note: the React SPA (`frontend/web`) has no vitest suite and no `test`
script. Any "512 frontend tests" figure from earlier reports does **not**
correspond to a suite present in this repository.

Environment note: installing `frontend/requirements.txt` pulls a pyarrow
requiring NumPy ≥ 2.0 while the backend pins NumPy 1.26.4. Pinning
`pyarrow<17` resolves it. Without that pin, 11 Streamlit visualisation tests
fail for environment reasons, not code defects.

## 3. Repository facts verified against source

| Fact | Verified |
|---|---|
| Registered topics | **17**, all `published` |
| Namespaces / sections | **10 / 10** |
| Rewritten lessons in `content/` | **13**, all `verified` in the tracker |
| Existing lesson→topic mappings (`all_lesson_topics()`) | **24** |
| Alembic head | `a2b3c4d5e6f7` |
| Existing prerequisite edges (registry) | 18 |

## 4. Prerequisite edge reconciliation (source, not summary)

The historical reports disagreed: one said 73 edges, another 73 proposed plus
18 existing. Resolved by counting from source:

| Measure | Count |
|---|---:|
| Existing edges in the current registry | 18 |
| Proposed new edges (from `effective_proposal()`) | 73 |
| **Final merged graph** | **91** |

The two figures were measuring different things. 73 is the *proposed* set; 91
is the merged total. Both are recorded so the discrepancy cannot recur.

## 5. Gaps found during implementation (to be corrected)

| # | Gap | Why it matters | Fix |
|---|---|---|---|
| G1 | `build_curriculum()` applies **no status filter** — it returns every topic row | Adding 54 `draft` topics would expose empty modules to learners, violating the "no inaccessible modules" rule | Filter to `published` in `build_curriculum`; `test_only_published_topics_reach_learners` already asserts this |
| G2 | `TopicPrerequisite` has **no rationale column** | The approved architecture carries a rationale on every edge and requires it preserved | Add `rationale` column in the migration |

## 6. Batch progress

| Batch | Scope | Status |
|---|---|---|
| 1 | Registry, topics, mappings, prerequisites, migration code, tests | **Complete** |
| 2 | Migration + data-preservation verification on disposable DBs | **Complete** (SQLite + PostgreSQL 16.2 verified) |
| 3 | Lessons: math, core, intro QC, Qiskit | Pending |
| 4 | Lessons: algorithms, advanced circuits, variational/NISQ | Pending |
| 5 | Lessons: error correction, hardware, communication, ecosystem | Pending |
| 6 | Integration, rendering, RAG, tracker, final validation | Pending |

## 7. Database test identifiers (Gate 3)

Recorded before each migration execution. Never a shared or pre-existing
database.

| Date | Backend | Identifier | Disposable? | Result |
|---|---|---|---|---|
| 2026-10-10 | SQLite | `m4test_sqlite_20261010_054816` | Yes — new file under `/tmp`, created for this test | upgrade / downgrade / re-upgrade clean; learner data preserved; guard verified |
| 2026-10-10 | PostgreSQL 16.2 | `m4test_pg_20261010_0555` | Yes — created `DROP IF EXISTS` + `CREATE` immediately before use, isolated Unix-socket server via `pgserver` | upgrade / downgrade / re-upgrade clean; learner data preserved |

Migration `g2a5b8c1d4e7` verified on that database:

| Check | Result |
|---|---|
| Fresh migrate to head | pass (all 6 revisions) |
| Topics after upgrade | 71 (17 published + 54 draft) |
| Prerequisite edges | 91 (61 required / 30 recommended), 73 with rationale |
| Lesson-topic associations | 78 (24 existing + 54 new) |
| Dangling references / self-deps / duplicates | 0 / 0 / 0 |
| Acyclicity | 71/71 topological order |
| Downgrade | back to exactly the original 17 topics; learner rows untouched |
| Re-upgrade | identical counts; learner data intact |
| Destructive-downgrade guard | refuses with a count when `topic_mastery` references an M4 topic |
| Service-layer load | `build_curriculum` returns 17 topics (drafts hidden), 10 sections, 4 empty as designed |

## 8. Remaining tasks / genuine blockers

- React rendering / RAG verification deferred to Batch 6, since it needs a
  live API and authored lesson content.
- The 54 new topics are `draft`. Each is published as its lesson is authored.

## 9. Decisions taken during implementation

| # | Decision | Rationale |
|---|---|---|
| D1 | New topics registered as `status = "draft"` | The approved architecture says drafts must not appear as finished modules. Publishing happens per topic once its lesson is validated. |
| D2 | `all_prerequisites()` keeps its 3-tuple contract; rationale added via a separate `all_prerequisites_with_rationale()` | The already-applied migration `a2b3c4d5e6f7` unpacks 3 values. Changing the signature would break a fresh migrate. |
| D3 | Existing mapping confidences left at `medium` where they were | The architecture flagged raising them to `high` as needing its own approval. Not explicitly required, so preserved unchanged. |
| D4 | `test_every_existing_lesson_is_mapped` relaxed to a subset check, with a new `test_no_published_topic_points_at_a_missing_lesson` | The equality form incidentally asserted something now false by design (draft topics map to not-yet-written lessons). The real safety property — no *published* topic with a missing lesson — is now asserted explicitly and is stricter. |
| D5 | The four Phase 1 guard tests replaced with post-implementation invariants | Their intent was to prevent unapproved implementation. Implementation is now authorised, so the inverse invariants apply: every approved topic is registered, matches the architecture, and the original 17 are preserved. |
