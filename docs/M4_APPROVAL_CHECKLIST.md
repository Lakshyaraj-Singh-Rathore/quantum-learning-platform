# M4 Curriculum Architecture — Approval Checklist

> **Authorization update (2026-10-10).** The owner has since approved
> **Gate 2** (implementation), **Gate 3** (migration execution, restricted to
> newly created disposable local databases with synthetic data) and **Gate 5**
> (lesson authoring). **Gate 4 (production) remains NOT authorised**, and
> **P8/P9 Streamlit cutover remains blocked.** Gate 1 was approved at
> `c8f7144`. This record is updated in the first substantive implementation
> commit rather than in a separate approval-only commit; the approved
> architecture itself is unchanged. See
> [`M4_IMPLEMENTATION_LEDGER.md`](./M4_IMPLEMENTATION_LEDGER.md) for progress.

**Status: Gates 1, 2, 3 (limited) and 5 authorised. Gate 4 not authorised.**

**Approval in M4 is five separate gates.** Each requires its own explicit,
separately stated authorisation. Approval of an earlier gate must never be
read as approval of a later one.

| Gate | Name | What it authorises | Status |
|---|---|---|---|
| **1** | Architecture approval | Accepting the 54-topic architecture and prerequisite design **as a design only** | **Approved** at `c8f7144` |
| **2** | Implementation authorisation | Creating topic IDs, updating curriculum mappings and prerequisites, writing the required migration | **Approved** |
| **3** | Non-production migration execution | Running that migration against an identified non-production environment | **Approved with limits** — new disposable local DBs + synthetic data only |
| **4** | Production migration | Running any migration against production learner data | **NOT authorised. Not requested.** |
| **5** | Phase 3 lesson authoring | Writing and validating the remaining lesson content | **Approved** |

---

## Gate 1 — Architecture approval *(requested now)*

**Scope.** Approving Gate 1 authorises **acceptance of the architecture
described in
[`M4_CURRICULUM_ARCHITECTURE_REVIEW.md`](./M4_CURRICULUM_ARCHITECTURE_REVIEW.md)
as a design**, and nothing more.

**Gate 1 explicitly does NOT authorise:**

- creating any topic ID in `app/curriculum.py`
- updating any lesson→topic mapping or prerequisite
- writing or running an Alembic migration
- authoring or rewriting lesson content
- touching any database, in any environment

Those are Gates 2–5. Concretely: if you approve Gate 1 and say nothing
else, the registry stays exactly as it is and no further work begins.

**What Gate 1 asks you to confirm:**

| # | Decision | Note |
|---|---|---|
| D1 | **54 new topics** (61 originally proposed, 5 withdrawn, 2 deferred) | Section 3 of the review |
| D2 | **6 items satisfied by existing topics**, not new ones | Section 2 of the review |
| D3 | **2 items deferred** and reported as unresolved | Section 5 of the review |
| D4 | **5 proposals withdrawn** as duplicating existing topics | Section 1 of the review |
| D5 | **`adv.compilation` rescoped** — Transpilation moves to `adv.quantum_universality` | Section 1 of the review |
| D6 | **Cryptography**: both target-list rows kept (history preserved), one topic covers all three items | Review, Q0 |
| D7 | **Estimator** as an additive `qiskit.estimator`; `qiskit.sampler` **not** renamed | Review, Q3 |
| D8 | **Hardware**: five separate platform topics + `hw.platform_comparison` | Review, Q4 |
| D9 | **Group theory** is `recommended`, never `required` | Review, Q6 |
| D10 | The prerequisite graph and its `required`/`recommended` split | Section 6 of the review |

Gate 1 approves the **design** of the prerequisite graph. It does not
authorise writing those edges into the registry — that is Gate 2.

---

## Gate 2 — Implementation authorisation *(approved)*

Separate, explicit authorisation will be requested before any of:

- creating the 54 topic IDs in `app/curriculum.py`
- implementing primary/secondary lesson mappings
- adding prerequisites to the registry
- writing the Alembic revision that inserts the topics

**Gate 2 will not be inferred from Gate 1.** It will be requested as its own
decision, with its own review of the diff.

---

## Gate 3 — Non-production migration execution *(approved, limited)*

Running the migration — even on a local or staging database — requires its
own clearly stated authorisation and **must identify the environment by
name**.

Nothing has been run. When Gate 3 is requested it will state:

- the exact environment (for example: local SQLite file, or the named
  PostgreSQL staging instance)
- the exact revision to be applied
- the rollback path and how it was verified

Per your standing instruction: *migration tested is not migration approved.*
A green test run against a database copy does not itself authorise Gate 3.

---

## Gate 4 — Production migration *(not authorised, not requested)*

**Running a migration against production learner records is not authorised
and is not being requested.** It remains out of scope for M4.

If it is ever considered, it requires its own separate authorisation after
review of: the PostgreSQL validation result, the mapping review, the
downgrade review and the migration report.

---

## Gate 5 — Phase 3 lesson authoring *(approved)*

Authoring the remaining lesson content stays gated **until Phase 2
implementation and its validation are complete**, unless you explicitly
authorise it earlier as a separate decision.

Gate 1 approval does not start Phase 3. Gates 2 and 5 have since been
authorised separately.

---

## What has been verified for Gate 1

| # | Check | Result |
|---|---|---|
| 1 | Every reported figure recalculated from live source | **pass** (97 / 96 / 17 / 82 / 36 / 46) |
| 2 | Every pending item assigned to exactly one category | **pass** — 6 reused + 74 proposed + 2 deferred = 82 |
| 3 | No item counted in two categories | **pass** |
| 4 | No pending item omitted | **pass** |
| 5 | No proposed ID collides with a registered topic | **pass** |
| 6 | All 54 topics have description, difficulty and ≥3 objectives | **pass** (162 objectives) |
| 7 | All prerequisites resolve to a real topic | **pass** — no dangling references |
| 8 | No cycles, no self-dependencies | **pass** |
| 9 | Valid topological order | **pass** — 71/71 nodes |
| 10 | Every edge has a substantive rationale | **pass** — 73/73 edges |
| 11 | `required` vs `recommended` distinguished on every edge | **pass** — 44 required / 29 recommended |
| 12 | Registry untouched | **pass** — `app/curriculum.py` has no uncommitted change |
| 13 | Phase 0 baseline document still reproducible | **pass** |
| 14 | Backend curriculum tests | **pass** — 54 passed, 0 failed |
| 15 | No migration exists for the new topics | **pass** — no new Alembic revision |

---

## Items explicitly NOT covered (reported, not hidden)

| Item | Section | Status |
|---|---|---|
| Quantum Mechanics | C | **Deferred.** No objective not already owned by `core.quantum_postulates`, `qc.superposition` or `qc.qubits`. |
| Dequantization Critiques | G | **Deferred.** Advanced critique that depends on `nisq.qml` and `algo.grover` existing first. |

Neither is counted as complete. Both remain in the target list pending a
decision.

---

## Known risks carried forward

| Risk | Severity | Mitigation |
|---|---|---|
| **Authoring volume** — 54 new lessons is the bulk of remaining work | High | Phase 3 works in dependency-ordered batches; tracker updated per verified lesson |
| **Hardware section is the most expensive** — 10 topics, 5 lessons before the comparison topic is meaningful | Medium | Sequence platforms first, comparison last |
| **Barren plateaus depth** — `nisq.parameterized_circuits` owns the objective but `07_vqe_qaoa` covers it in one paragraph | Medium | **Content defect, not structural.** Carried into Phase 3 as a lesson-depth task |
| **Topics land unpublished** — new topics land as `status = "draft"` so learners never see an empty module | Low | Publish individually as lessons appear |
| **Lesson slugs are placeholders** — must not collide with the 13 existing slugs, which are FK-referenced | Medium | Slug collision check before file creation in Phase 3 |

---

## Out of scope (unchanged from M4 scope)

- No architecture redesign
- No production migrations (Gate 4)
- No Streamlit changes
- No P8 or P9
- **The inferred RAG-tag defect (M4-1) is deliberately not fixed here.** It
  stays a separate decision and remains documented in
  [`REVIEW_REQUIRED.md`](./REVIEW_REQUIRED.md).

---

## How to respond

Reply with one of:

- **"Gate 1 approved"** — the architecture is accepted as a design.
  *(Issued 2026-10-10, at `c8f7144`.)*
- **"Gate 2 approved"** — implementation of the registry, mappings,
  prerequisites and migration. *(Issued 2026-10-10.)*
- **"Gate 3 approved with limits"** — migration execution against disposable
  local databases with synthetic data. *(Issued 2026-10-10.)*
- **"Gate 5 approved"** — lesson authoring. *(Issued 2026-10-10.)*
- **"Gate 4 approved"** — production migration. **Not issued, not requested.
  Any production migration still requires separate explicit authorisation.**

Approval must apply to an identified version. If you approve, please quote
the commit so the approved architecture is unambiguous.

**This document is not a request for Gates 2–5.** They are listed so the
boundaries are explicit, not so they can be approved in passing.

---

## Reproducing this review

From the repository root:

```bash
# WSL / macOS / Linux
backend/.venv/bin/python backend/scripts/topic_gap_analysis.py

# Windows PowerShell
backend\.venv\Scripts\python.exe backend\scripts\topic_gap_analysis.py
```

This regenerates both generated documents and prints the validation result.
It writes documentation only; it never touches the registry or the database.
This checklist is maintained by hand and is not generated.
