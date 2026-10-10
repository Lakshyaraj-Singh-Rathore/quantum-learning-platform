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

### Batch 4 - IN PROGRESS

Scope: quantum-algorithms, advanced-gates-circuits, variational-nisq.
26 tracker items resolving to **18 distinct new lessons** plus the mandated
barren-plateau depth fix.

| # | Lesson | Topic | Status | KaTeX | RAG | Commit |
|---|---|---|---|---|---|---|
| - | `07_vqe_qaoa.md` (depth fix) | `nisq.parameterized_circuits` | done | 68/68 | 21 | `a533459` |
| 38 | `38_multi_controlled.md` | `adv.multi_controlled_gates` | done | 84/84 | 23 | `b29e906` |
| 39 | `39_two_qubit_gates.md` | `adv.parameterized_two_qubit` | done | 87/87 | 24 | `16e2d4b` |
| 40 | `40_circuit_identities` | `adv.circuit_identities` | not started | | | |
| 41 | `41_multipartite_entanglement` | `adv.multipartite_entanglement` | not started | | | |
| 42 | `42_compilation` | `adv.compilation` | not started | | | |
| 43 | `43_resource_estimation` | `adv.resource_estimation` | not started | | | |
| 30 | `30_bernstein_vazirani` | `algo.bernstein_vazirani` | not started | | | |
| 31 | `31_qft` | `algo.qft` | not started | | | |
| 32 | `32_phase_estimation` | `algo.phase_estimation` | not started | | | |
| 33 | `33_shors_algorithm` | `algo.shors` | not started | | | |
| 34 | `34_simon` | `algo.simon` | not started | | | |
| 35 | `35_quantum_walks` | `algo.quantum_walks` | not started | | | |
| 36 | `36_amplitude_estimation` | `algo.amplitude_estimation` | not started | | | |
| 37 | `37_hhl` | `algo.hhl` | not started | | | |
| 68 | `68_quantum_cryptography` | `comm.cryptography` | not started | | | |
| 45 | `45_optimization_loops` | `nisq.optimization` | not started | | | |
| 46 | `46_approximation_ratios` | `nisq.approximation_ratios` | not started | | | |
| 47 | `47_quantum_machine_learning` | `nisq.qml` | not started | | | |

Validator is now at **30/30**.

#### The barren-plateau depth gap is FIXED (commit `a533459`)

The review carried this in as a known content-depth defect:
`nisq.parameterized_circuits` owned the objective while `07_vqe_qaoa` covered
it in one paragraph. The section is now substantive and every number is
measured.

Verified, hardware-efficient ansatz of two layers, 300 random parameter
vectors, observable $\langle Z^{\otimes n}\rangle$: the standard deviation
falls `0.438 -> 0.250 -> 0.134 -> 0.0683 -> 0.0350` for `n = 2,4,6,8,10`, a
factor of about `0.73 ~ 1/sqrt(2)` per qubit, so the variance halves per qubit
and scales as $2^{-n}$. Gradient variance via parameter shift (200 inits,
3 layers) falls by `0.457, 0.542, 0.504, 0.494` per qubit from n=4 to n=8.

**A caveat is stated inside the lesson**: our experiments at fixed qubit
number did NOT reproduce a clean collapse as layers were added, so the depth
axis is presented as established theory rather than as demonstrated here.

**Two negative results found while testing, deliberately kept out of the
lesson** and recorded here:

- An **RY-only** ansatz produces real amplitudes and never approaches a
  2-design, so no depth scaling can appear. If you try to demonstrate depth
  scaling this way it will silently fail.
- An **L=1 ring-of-CNOTs** ansatz with the global $Z$ observable is
  degenerate: a ring of CNOTs preserves total parity, so $\langle
  Z^{\otimes n}\rangle$ is identically $+1$ and the gradient is zero. The
  apparent "plateau" at L=1 (variance ~1e-33) is an artifact, not physics.

#### Eighth sandbox rebuild recovered

`git reset --mixed origin/arena/...` had left HEAD at `9b106fd` with the
whole tree staged as untracked/modified. Recovered safely: fetched, verified
all **370** remote-tip files were present and byte-identical (0 missing,
0 differing), then reset --mixed. Nothing lost. Venv and node deps rebuilt.

Caution for next time: `git diff --stat <commit>` against a stale index
reported 152 files as pure deletions, which was misleading. Byte-comparing
`git show <commit>:<file>` against the file on disk is the reliable check.

### Current verified baselines

| Suite | Result |
|---|---|
| Backend | 629 passed, 5 skipped (before Batch 4; re-run due) |
| Frontend | 418 passed, 77 skipped (not re-run this session) |

### Remaining

- Batch 4: 16 new lessons (40, 41, 42, 43, 30-37, 68, 45, 46, 47).
- Batch 5, then Batch 6 integration and final validation.

### Current verified baselines (post-rebuild)

| Suite | Command | Result |
|---|---|---|
| Backend | `cd backend && python -m pytest -q -p no:cacheprovider` | **609 passed, 5 skipped** |
| Frontend | `python -m pytest frontend/tests -q -p no:cacheprovider` | **418 passed, 77 skipped** |

React has no unit-test suite; the `render:*`/`a11y`/`states`/`curriculum`
tsx scripts need a live API and remain deferred to Batch 6.

### Batch 3 - Qiskit block COMPLETE (Batch 3 finished)

| # | Lesson | Topic | KaTeX | RAG | Commit |
|---|---|---|---|---|---|
| 28 | `28_composer_guide.md` | `qiskit.composer` | 17/17 | 27 | `c37c447` |
| 29 | `29_primitives.md` | `qiskit.estimator` | 121/121 | 27 | `e17ceb7` |

**Batch 3 is complete: 15 of 15 lessons (14-29, excluding the unassigned 25).**
18/18 lessons now pass validation.

#### Lesson 28 was written against the implementation, not from memory

Every fact was read from source: the 15-gate set and alias table from
`app/quantum/ir.py`, the backend catalogue from `app/api/jobs.py`, the qubit
and shot limits from `app/config.py` (static 20, dynamic 15, GPU 28, dynamic
shots 4096, while cap 32, for cap 1024), and the bit-order convention from
the run metadata itself, which reports
`bit_order: qiskit (qubit 0 = rightmost)` - independently confirming what
lesson 27 asserts.

Running a Bell circuit with the default noise model puts **5.57% of shots on
outcomes the ideal circuit cannot produce**, reported as `shot_leakage`. For a
circuit whose ideal answer has zero weight on some outcomes, that leakage is
a direct readout of how noisy the run was.

The lesson also documents that Z/S/T/RZ are virtual and pick up no thermal
error - not a simulation shortcut but how real superconducting hardware
behaves.

#### Lesson 29 states plainly that this project has no Estimator

There is no Estimator class in this codebase; only a Sampler-style counts
interface. The lesson says so at the top and builds everything from counts,
rather than documenting an API that does not exist here.

#### Tracker reconciliation (commit `5d8f4c8`)

Row `M4-D03` still held the pre-rename id `qiskit.primitives`. The
architecture review resolved Q3 by keeping this as an additive topic named
`qiskit.estimator` (renaming the stable `qiskit.sampler` id was not
authorised), and the registry records `qiskit.estimator`.

Because the row held the old id, marking lesson 29 verified updated **zero**
rows - the tracker had silently lost the association. The id was updated and
the rename recorded in the row's review notes. Same target item, one row,
corrected identifier.

Verified afterwards:
- All **54** M4 draft topics now have a tracker row (was 53).
- The **7** tracker ids with no registry entry are exactly the 5 documented
  withdrawals (`core.phase`, `qiskit.bloch_sphere`, `qiskit.reading_histograms`,
  `nisq.barren_plateaus`, `nisq.ansatz`) plus the 2 deferrals.
- Both deferrals (`qc.quantum_mechanics_primer`, `nisq.dequantization`) remain
  `not_started` / `missing` and are **not** marked complete.

#### Supporting

- `MEASURABLE_VERBS` extended with `configure` and `select`; the VAGUE_VERBS
  guard re-proven with a probe file.
- Lesson 28's draft said depth 2; the real depth with measurements is 3.
  Caught by executing the code and comparing against the prose.

### Current verified baselines

| Suite | Result |
|---|---|
| Backend | **629 passed, 5 skipped** |
| Frontend | 418 passed, 77 skipped (not re-run this batch) |

### Remaining: Batches 4, 5, 6

- **Batch 4** - algorithms, advanced circuits, variational/NISQ. The barren
  plateaus depth gap in `nisq.parameterized_circuits` must be genuinely
  corrected; the review flagged 07_vqe_qaoa as covering it in one paragraph.
- **Batch 5** - error correction, fault tolerance, hardware, communication,
  ecosystem, simulation. The hardware platform comparison must meaningfully
  compare, not list.
- **Batch 6** - integration and final validation: navigation, rendering, RAG,
  tracker, full suites, fixes.
