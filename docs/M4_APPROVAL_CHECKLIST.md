# M4 Curriculum Architecture — Approval Checklist

**Status: awaiting owner approval.** Nothing in this phase has been
implemented. No topic ID created, no mapping changed, no migration written,
no lesson rewritten.

**What you are approving:** the topic architecture described in
[`M4_CURRICULUM_ARCHITECTURE_REVIEW.md`](./M4_CURRICULUM_ARCHITECTURE_REVIEW.md).
Approving this document authorises **Phase 2** (implementation of the topic
architecture). It does **not** authorise content authoring, which is Phase 3.

---

## 1. What has been verified

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

---

## 2. Decisions you are being asked to confirm

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

---

## 3. Items explicitly NOT covered (reported, not hidden)

| Item | Section | Status |
|---|---|---|
| Quantum Mechanics | C | **Deferred.** No objective not already owned by `core.quantum_postulates`, `qc.superposition` or `qc.qubits`. |
| Dequantization Critiques | G | **Deferred.** Advanced critique that depends on `nisq.qml` and `algo.grover` existing first. |

Neither is counted as complete. Both remain in the target list pending a
decision.

---

## 4. Known risks carried forward

| Risk | Severity | Mitigation |
|---|---|---|
| **Authoring volume** — 54 new lessons is the bulk of remaining work | High | Phase 3 works in dependency-ordered batches; tracker updated per verified lesson |
| **Hardware section is the most expensive** — 10 topics, 5 lessons before the comparison topic is meaningful | Medium | Sequence platforms first, comparison last |
| **Barren plateaus depth** — `nisq.parameterized_circuits` owns the objective but `07_vqe_qaoa` covers it in one paragraph | Medium | **Content defect, not structural.** Carried into Phase 3 as a lesson-depth task |
| **Targets are unpublished** — new topics land as `status = "draft"` so learners never see an empty module | Low | Publish individually as lessons appear |
| **Lesson slugs are placeholders** — must not collide with the 13 existing slugs, which are FK-referenced | Medium | Slug collision check before file creation in Phase 3 |

---

## 5. What approval does NOT authorise

- Creating the topic IDs in `app/curriculum.py`
- Writing or running an Alembic migration
- Changing any existing lesson→topic mapping
- Authoring lesson content (that is Phase 3)
- Any migration against production learner data

---

## 6. Out of scope (unchanged from M4 scope)

- No architecture redesign
- No production migrations
- No Streamlit changes
- No P8 or P9
- **The inferred RAG-tag defect (M4-1) is deliberately not fixed here.** It
  stays a separate decision and remains documented in
  [`REVIEW_REQUIRED.md`](./REVIEW_REQUIRED.md).

---

## 7. How to respond

Reply with one of:

- **"Approved"** — I begin Phase 2 (topic architecture implementation).
- **"Approved with changes: …"** — I update the review document, re-run
  validation, and come back for approval of the identified revision.
- **"Rejected: …"** — I stop and await direction.

Approval must apply to an identified version of the document. If you approve,
please quote the commit so the approved architecture is unambiguous.

---

## 8. Reproducing this review

From the repository root:

```bash
# WSL / macOS / Linux
backend/.venv/bin/python backend/scripts/topic_gap_analysis.py

# Windows PowerShell
backend\.venv\Scripts\python.exe backend\scripts\topic_gap_analysis.py
```

This regenerates both documents and prints the validation result. It writes
documentation only; it never touches the registry or the database.
