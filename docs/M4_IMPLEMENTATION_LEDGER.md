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

## Batch 3 — lesson authoring

### Completed lessons (verified, tracker updated)

| # | Lesson | Topic | KaTeX | RAG chunks | Commit |
|---|---|---|---|---|---|
| 14 | `14_complex_numbers.md` | `math.complex_numbers` | 141/141 | 22 | `9d68277` |
| 15 | `15_linear_algebra.md` | `math.linear_algebra` | 107/107 | 26 | `352fe99` |
| 16 | `16_eigen_and_operators.md` | `math.eigen_and_operators` | 145/145 | 26 | `742a9e9` |
| 17 | `17_probability_and_statistics.md` | `math.probability_and_statistics` | 85/85 | 20 | `ca05149` |
| 18 | `18_group_theory.md` | `math.group_theory` | 97/97 | 23 | `033161f` |

Math foundations block (14-18) is complete. All five authored against the
authoring standard, all code blocks executed before writing, all RAG chunking
fence-balanced.

### Authoring pipeline (run per lesson, in order)

1. Execute the Python block; diff every stated number against real output. On
   mismatch, fix the **content**, never the expected output.
2. `cd backend/scripts && /home/user/.venv-ql/bin/python validate_lesson.py`
3. `node /tmp/katex_check.mjs content/<slug>.md`
4. `split_on_headings` RAG check: chunk count, unbalanced fences, fence parity.
5. `/home/user/.venv-ql/bin/python backend/scripts/m4_mark_lesson.py <slug> <topic_id> verified "<notes>"`
6. `git add` + `git commit` + `git push -q origin arena/01a0d874-quantum-learning-platform`

### Supporting changes during Batch 3

- `backend/scripts/m4_mark_lesson.py` — new helper (committed `9d68277`).
- `backend/scripts/validate_lesson.py` — `MEASURABLE_VERBS` extended with
  assessable verbs (represent, multiply, transform, determine, recognise,
  simulate, design, prove, justify, combine, estimate, solve, find,
  maximise/minimise, translate, express, expand, factor, sketch). Guard
  re-proven: a temp file using "Understand"/"Appreciate" still warns.

### Content defect found and fixed (lesson 14)

Prose claimed the global-phase rows print `0.640000`; the real value is
`1.000000` because the chosen amplitude had unit norm (`0.6^2 + 0.8^2 = 1`),
which makes the invariance claim vacuous. Fixed the *content*: amplitude
changed to `0.3 + 0.4j` so `|z|^2 = 0.25` exactly, prose reworded to
`0.250000`. Re-executed and confirmed.

### Credentials, sandbox rebuild and recovery (2026-10-10)

**Push blocked, then unblocked.** `git push` began failing with
`fatal: could not read Username for 'https://github.com'`; `gh auth status`
reported the `GH_TOKEN` no longer valid. The token is injected into the
sandbox environment by the platform (there is no `~/.config/gh` and no
credential helper), so it cannot be refreshed from inside. The user
re-authorised GitHub from their side and `gh auth status` went green again.

**A sandbox rebuild followed.** `git reflog` showed the repository had been
re-cloned at 06:27:48 (`clone: from https://github.com/...`), leaving HEAD at
the base commit `9b106fd`. All six local commits were unreachable.

Recovery, in order, without any destructive command:

1. `git ls-remote` confirmed the remote branch still held `ca05149` (all of
   Batch 1-2 plus lessons 14-17). **Nothing except the two unpushed commits
   was ever at risk.**
2. Backed up the three files holding unpushed work to `/home/user/m4_backup/`,
   outside the repository.
3. `git diff` initially reported 140 files as pure deletions, which looked
   like mass data loss. It was an artefact: the index was stale (218 entries
   against 358 files on disk). Confirmed by direct comparison that
   `backend/app/curriculum.py`, `backend/tests/test_curriculum.py` and
   lessons 14 and 17 were byte-identical to the remote versions.
4. `git reset --mixed origin/arena/01a0d874-quantum-learning-platform`
   refreshed the index only, leaving the working tree untouched. The genuine
   delta was then exactly the two unpushed commits.
5. Recommitted as `e99ee29` and pushed.

**Root cause of the stale remote-tracking ref:** `remote.origin.fetch` was
narrow (`+refs/heads/main:refs/remotes/origin/main`), so plain `git fetch`
never updated the arena branch. Set to `+refs/heads/*:refs/remotes/origin/*`.

**Rebuilt environment.** The venv and `node_modules` (excluded from
snapshots) were gone. Recreated the venv, reinstalled `backend/requirements.txt`
and `frontend/requirements.txt`, and ran `npm install` in `frontend/web`.
The KaTeX checker had lived in `/tmp` and was lost; it is now at
`/home/user/katex_check.mjs`, which persists.

### Regression found by re-running the suite after the rebuild

`609 passed, 5 skipped` after fixing two failures, both caused by correct
progress rather than by the rebuild:

1. **`test_downgrade_places_every_lesson_and_preserves_secondary_placements`**
   — a genuine defect. The M4 downgrade deletes `lesson_topics` rows for M4
   topics (it must: `topic_id` has a foreign key to the topic table). The
   thirteen pre-M4 lessons survive that because placements are restored from
   the rows that remain, but lessons 14-18 are placed *only* against M4
   topics, so they finished the downgrade with `topic_slug` NULL. Fixed in
   `a2b3c4d5e6f7`'s downgrade: an unplaced lesson falls back to the primary
   topic the registry names. Verified 18/18 placed (was 13/18), round-trip
   identical at 78 placements. Commit `671a469`.
2. **`test_tracker_counts_reconcile_with_the_gap_report`** — a stale frozen
   snapshot (`existing=7, partial=8, missing=82`). Authoring lessons moves
   rows to `existing`, so the real split is now `16/8/73`; the +9 is exactly
   the five new lessons (1+3+2+2+1 rows). Replaced the magic numbers with
   derived invariants, including `existing + partial == rows whose lesson
   file is on disk`. Negative control confirmed the new assertion still
   fails on tampering. Commit `e01f1e6`.

### Current verified baselines (post-rebuild)

| Suite | Command | Result |
|---|---|---|
| Backend | `cd backend && python -m pytest -q -p no:cacheprovider` | **609 passed, 5 skipped** |
| Frontend | `python -m pytest frontend/tests -q -p no:cacheprovider` | **418 passed, 77 skipped** |

React has no unit-test suite; the `render:*`/`a11y`/`states`/`curriculum`
tsx scripts need a live API and remain deferred to Batch 6.

### Batch 3 - core quantum theory block COMPLETE

| # | Lesson | Topic | KaTeX | RAG | Commit |
|---|---|---|---|---|---|
| 19 | `19_quantum_postulates.md` | `core.quantum_postulates` | 78/78 | 22 | `2d785c2` |
| 20 | `20_density_matrices.md` | `core.density_matrices` | 96/96 | 26 | `82a6bf8` |
| 21 | `21_entanglement_measures.md` | `core.entanglement_measures` | 86/86 | 25 | `4098dde` |
| 22 | `22_no_cloning.md` | `core.no_cloning` | 76/76 | 30 | `5495215` |
| 23 | `23_dirac_notation.md` | `qc.dirac_notation` | 101/101 | 28 | `220e251` |
| 24 | `24_tensor_products.md` | `qc.tensor_products` | 98/98 | 29 | `cec6643` |
| 26 | `26_teleportation.md` | `qc.teleportation` | 50/50 | 21 | `fc7ae81` |
| 27 | `27_reading_results.md` | `qc.reading_results` | 62/62 | 25 | `52922f1` |

Lesson 25 is not the primary lesson of any topic in the registry, so it is
not authored. Registry order was verified topologically against *required*
prerequisite edges.

#### Two authoring errors caught before shipping

1. **Lesson 22's proof was initially vacuous.** The inner-product argument
   used |+> and |->, which are orthogonal, so both sides were zero and the
   "contradiction" proved nothing while looking correct. Reworked with the
   genuinely non-orthogonal pair |0> and |+>, giving 0.707 against 0.5.
2. **Lesson 26's first simulation omitted the Hadamard** that creates the
   Bell pair, producing fidelities of 0.36 and 0.64. Caught because the
   printed numbers contradicted the claim being made about them.

#### Practices that keep catching real problems

- **Execute the code and diff every number against the prose.** Both errors
  above were visible only in the executed output.
- **Keep inline `$...$` on one line.** `test_content_markdown.py` checks
  delimiters line by line; the KaTeX checker does not. Hit four times on
  lesson 22.
- **Split long `## Practical example` sections with `###` subheadings** so
  RAG chunks stay near the 1200-character target.
- **Run lesson code under `-W error::Warning`.** Lesson 24 initially cast
  complex arrays straight to `int`, emitting a ComplexWarning.

#### Tooling

- `backend/scripts/check_lesson_math.mjs` (commit `1101e73`) - compiles every
  LaTeX expression with KaTeX across all lessons. Lives in the repository
  because the sandbox is periodically rebuilt and only committed files
  survive. Current status: all 26 lessons, 1741 expressions, 0 failures.
- `validate_lesson.py` - `MEASURABLE_VERBS` extended with `demonstrate` and
  `reproduce`; the raw-HTML check now skips inline code spans as well as
  fenced blocks (both render as code, so a tag inside them is program text
  such as bra-ket output, not markup). Both guards re-proven with probe
  files.

### Current verified baselines

| Suite | Result |
|---|---|
| Backend | **625 passed, 5 skipped** |
| Frontend | 418 passed, 77 skipped (not re-run this batch) |
