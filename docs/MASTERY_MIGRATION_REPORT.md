# Mastery Migration Report

**Status: implemented and verified on a database copy. NOT applied to production.**

This report supports the M0.4 verification gate. No production learner record
has been migrated. The production migration command is given at the end and
requires explicit approval before it is run.

All counts below are measured outputs from the migration runs described, not
projections.

---

## 1. Previous schema

`UserMastery` was the only mastery store:

```
user_mastery(id, user_id, tag, score, attempts, updated_at)
```

`tag` was written by `services/recommendations.py` from `quiz.tags` and
`challenge.tags` — hand-authored values in `backend/app/seed.py`, not the
keyword-inferred tags on lessons. The authored vocabulary is nine tags:
`entanglement, noise, measurement, gates, grover, qubit, dynamic, algorithms,
decoherence`.

`Lesson` had no curriculum fields at all. There was no topic entity, no
prerequisite relation and no difficulty.

## 2. New schema

```
curriculum_sections(id, slug, letter, title, position)
curriculum_topics(id, title, namespace, module, section_slug, position,
                  difficulty, description, learning_objectives, status,
                  revision, assessments, visualizations)
topic_prerequisites(id, topic_id, prerequisite_id, kind)
lesson_topics(id, lesson_slug, topic_id, confidence, is_primary)
topic_mastery(id, user_id, topic_id, mastery_level, status, source,
              evidence, last_activity, created_at)
lesson_completions(id, user_id, lesson_slug, completed_at)
```

Three separations that did not exist before:

- **`user_mastery` is untouched.** It remains exactly as it was: the raw
  history of tag-keyed outcomes.
- **`topic_mastery` is derived.** Every row carries `source` and an `evidence`
  JSON listing the originating `user_mastery` rows with their scores.
- **`lesson_completions` is separate.** Finishing a lesson no longer implies
  mastery of the topics it mentions.

## 3. Stable topic identifier convention

```
<namespace>.<topic>
```

| Namespace | Section | Letter |
|---|---|---|
| `math.` | Mathematical Foundations | A |
| `core.` | Core Quantum Theory | B |
| `qc.` | Introduction to Quantum Computing | C |
| `qiskit.` | Introduction to Qiskit | D |
| `algo.` | Quantum Algorithms | E |
| `adv.` | Advanced Gates and Circuits | F |
| `nisq.` | Variational and NISQ Algorithms | G |
| `qec.` | Error Correction and Fault Tolerance | H |
| `hw.` | Quantum Hardware and Ecosystem | I |
| `comm.` | Quantum Communication and Simulation | J |

The id is the primary key of `curriculum_topics`, so two rows cannot claim the
same identity. It depends on no filename, title, prose or position.

17 topics are registered, all `published`, each owning at least one lesson.

## 4. Mapping approach

Lessons are mapped to topics **explicitly**, in `backend/app/curriculum.py`,
with a confidence rating. Keyword inference no longer determines mastery.

Each mapping records `(lesson_slug, topic_id, confidence, is_primary)`.
Confidence is `high`, `medium` or `low`. Only `high` permits existing mastery
to be carried onto a topic.

24 lesson–topic links cover all 13 existing lessons. The mapping is
many-to-many: `01_qubits` teaches both `qc.qubits` (primary) and
`qc.superposition`; `qc.basic_gates` is taught by both `02_gates` and
`10_gates_bootcamp`.

Legacy tag → topic mapping, with the evidence recorded in
`LEGACY_MAPPING_EVIDENCE`:

| Tag | Topic | Evidence |
|---|---|---|
| `qubit` | `qc.qubits` | quiz `basics` |
| `gates` | `qc.basic_gates` | quiz `basics`, gate challenges |
| `measurement` | `core.measurement_theory` | quiz `entanglement-measurement` |
| `entanglement` | `qc.entanglement` | quizzes `entanglement-measurement`, `bell-states-quiz` |
| `noise` | `qiskit.quantum_noise` | quiz `quantum-noise` |
| `decoherence` | `qiskit.quantum_noise` | same quiz, co-occurs with `noise` |
| `grover` | `algo.grover` | quiz `grover` |
| `algorithms` | `algo.grover` | only co-occurs with `grover`; no other algorithms quiz exists |
| `dynamic` | `adv.dynamic_circuits` | dynamic-circuit challenges |

`algorithms` is the least secure of these and is flagged for review: it is
mapped to Grover on the grounds that Grover is currently the only algorithms
quiz. If a second algorithms quiz is authored, that inference stops holding.

## 5. Migration results

Run on an isolated SQLite copy, seeded with the real 13 lessons and 7 legacy
mastery rows chosen to exercise the difficult cases.

### Before

| Table | Rows |
|---|---|
| `lessons` | 13 |
| `user_mastery` | 7 |

### After

| Table | Rows |
|---|---|
| `lessons` | 13 |
| `user_mastery` | 7 (unchanged) |
| `topic_mastery` | 4 (derived) |
| `lesson_topics` | 24 |
| `curriculum_topics` | 17 |
| `topic_prerequisites` | 18 |

### Derived rows

| Topic | Level | Status | Aggregation | From |
|---|---|---|---|---|
| `algo.grover` | 0.6000 | mapped | mean | `grover`=0.7, `algorithms`=0.5 |
| `qc.entanglement` | 0.9000 | mapped | single | `entanglement`=0.9 |
| `qc.qubits` | 1.0000 | mapped | single | `qubit`=1.0 |
| `qiskit.quantum_noise` | 0.5000 | mapped | mean | `noise`=0.6, `decoherence`=0.4 |

Two tags landing on one topic produce **one averaged row, not two competing
ones**, and the `evidence` JSON records both contributing rows.

### Preserved, not mapped

`obsolete-tag` (score 0.85, 4 attempts) has no mapping. It is retained in
`user_mastery` unchanged and produces **no** `topic_mastery` row. It is
counted nowhere and satisfies no prerequisite.

### Integrity checks

| Check | Result |
|---|---|
| Legacy `user_mastery` rows unchanged | 7/7, scores and attempts identical |
| Orphan `lesson_topics` (topic missing) | 0 |
| Orphan `topic_prerequisites` | 0 |
| Lessons with no topic | 0 |
| Duplicate topic ids | 0 |
| Prerequisite cycles | 0 |

### Idempotency and rollback

Re-running the upgrade after a downgrade produces the same counts (4 / 24 /
17 / 18) with no duplicates.

Downgrade restores the prior schema: `topic_mastery` and `lesson_completions`
dropped, `lessons.topic_slug` and `user_mastery.topic_slug` re-added, all 13
lessons and all 7 mastery rows intact with identical scores and attempts.

## 6. Known limitations

1. **One lesson's placement does not fully round-trip.** On downgrade, 12 of
   13 lessons get `topic_slug` restored. `13_classical_bit_vs_qubit` does not,
   because it is a secondary lesson on `qc.qubits` and the flat schema had no
   way to express "secondary on a merged topic". It is not lost — it remains
   in `lessons` — but its provisional placement is not reconstructed. This
   affects only the downgrade path on a schema that is itself being replaced.

2. **The `algorithms` mapping is inferred, not certain.** See §4.

3. **SQLite and PostgreSQL differ.** The topic table is rebuilt via
   create/copy/rename because SQLite cannot alter a primary key. On PostgreSQL
   the same code path is used for portability, but `batch_alter_table` renders
   differently. The migration has **not** been executed against PostgreSQL in
   this environment; that is a prerequisite for production.

4. **Averages are not weighted.** Where two legacy rows merge, the mean is
   unweighted by attempts. With the current data the difference is immaterial,
   but attempt-weighting would be more defensible as history accumulates.

5. **No mastery decay.** The pre-existing `ALPHA = 0.4` exponential moving
   average is unchanged. Decay over time is not implemented and was not
   requested.

## 7. Proposed production migration

**Not executed. Requires explicit approval.**

Prerequisites:

1. Take a full backup and verify it restores.
2. Run against PostgreSQL in a staging environment first.
3. Confirm `alembic current` reports `f1a2b3c4d5e6`.

Procedure:

```powershell
# 1. verify starting revision
cd backend
alembic current

# 2. dry run: show the SQL without applying it
alembic upgrade f1a2b3c4d5e6:a2b3c4d5e6f7 --sql

# 3. apply
alembic upgrade head

# 4. verify
alembic current
```

Rollback:

```powershell
alembic downgrade f1a2b3c4d5e6
```

Rollback is non-destructive to `user_mastery` and `lessons`. Only derived
tables are dropped, and they are reproducible by re-running the upgrade.

Expected impact on learners: none immediately. `topic_mastery` is written but
no UI reads it yet, and no existing endpoint changes behaviour. Progress
display switches to the new model only when the frontend integration lands.

## 8. Test record

Backend suite: **552 passed, 5 skipped.** Baseline before this work was 511
passed, 5 skipped. The increase of 41 is the new `test_curriculum.py` (23) and
`test_curriculum_api.py` (18); no existing test was modified to pass.

Frontend suite and build were not re-run in this session — the venv and
`node_modules` were rebuilt during it and only the Python suites were
exercised. They are unaffected by these changes (backend-only), but that is an
assertion, not a measurement, and should be confirmed before merge.
