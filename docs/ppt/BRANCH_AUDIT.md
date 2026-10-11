# Branch Audit

**Method.** `git ls-remote --heads origin` for the authoritative remote list,
then `git fetch` per branch and `git rev-list --count` / `git merge-base
--is-ancestor` for relationships. All three branches were inspected; there are
no others.

> **Access caveat.** Push is blocked (`GH_TOKEN` expired). `git ls-remote` and
> `git fetch` still work over public HTTPS, so branch tips and commit contents
> are accurate. I could not use `gh` for PR/issue metadata.

---

## 1. Branch inventory — all branches, complete

| Branch | Tip | Date | Relationship to `main` | Inspected |
| --- | --- | --- | --- | --- |
| `main` | `53cf53e` | 2026-09-06 | — (baseline) | ✅ |
| `arena/01a0754d-quantum-learning-platform` | `9b106fd` | 2026-09-25 | +1 commit | ✅ |
| `arena/01a0d874-quantum-learning-platform` | `55d66f2` | 2026-10-11 | +126 commits | ✅ |

`origin/HEAD → origin/main`. There is **no** `develop`, no release branch, and
no feature branch. All development happened on the two Arena branches.

### Relationships (measured)

```
main (53cf53e)
  └── +1 ──► arena/01a0754d (9b106fd)
                └── +125 ──► arena/01a0d874 (55d66f2)   ← ours
```

- `git rev-list --count main..9b106fd` = **1**
- `git rev-list --count 9b106fd..55d66f2` = **125**
- `git rev-list --count main..55d66f2` = **126**
- `git merge-base --is-ancestor 9b106fd 55d66f2` → **true**

---

## 2. Branch comparison table

| | `main` | `arena/01a0754d` | `arena/01a0d874` (baseline) |
| --- | --- | --- | --- |
| **Latest commit** | `53cf53e` Add files via upload | `9b106fd` Raise the GPU ceiling to 28 qubits from real hardware measurements | `55d66f2` Add a self-booting browser check for the sidebar push/overlay contract |
| **Relation to baseline** | 126 commits behind | 125 commits behind; **fully merged into baseline** | — |
| **Unique features** | Initial upload only | GPU ceiling raise (28 qubits) | Everything else (see §3) |
| **Quantum execution** | — | CUDA-Q qubit ceiling, `.env.example` GPU vars, `docker-compose.gpu.yml` | 6 backends, noise model, QASM3, dynamic circuits, codegen ×4 |
| **AI / RAG** | — | — | Gemini client, pgvector RAG, keyword fallback |
| **Curriculum** | — | — | 71 topics, 67 lessons, mastery, prerequisites |
| **APIs** | — | — | 34 endpoints across 7 routers |
| **Frontend** | — | Streamlit only | **React SPA (all routes) + Streamlit (now removed)** |
| **Integrated into baseline?** | Yes (ancestor) | **Yes — no branch-only work remains** | — |
| **Status** | Superseded | **Superseded / merged** | **Active** |

### Key finding: there is no orphaned branch-only functionality

`arena/01a0754d` differs from `main` by exactly one commit, and that commit is
an ancestor of our branch. Its only substantive content is the CUDA-Q ceiling
work — still present in `backend/app/quantum/backends/cudaq_sim.py`
(**326 insertions / 28 deletions** between `9b106fd` and `55d66f2`).

**Do not claim any feature is "branch-only" or "experimental on another
branch."** Everything on both Arena branches is integrated.

---

## 3. What our branch added (125 commits after the split)

Grouped by theme, newest first.

### UI / SPA (2026-10-11) — the last 8 commits
| Commit | Change |
| --- | --- |
| `55d66f2` | Self-booting browser check for the sidebar push/overlay contract (`push:overlay` harness) |
| `a805f30` | Explain a disabled AI Generate instead of leaving it silent |
| `2a12a78` | Push the sidebar on reading pages, keep the overlay on the Composer |
| `48d448f` | Honour a deep-linked lesson even when the track filter hides it |
| `994a800` | Make the 344 cross-lesson links navigable instead of dead |
| `c88c5de` | UI/UX QA handoff brief for external review agents |
| `d68409e` | Reproducible Chromium setup script (`tools/browser-setup.sh`) |
| `2ca7ddd` | Sidebar rail, code highlighting, and four more reported defects |

### Curriculum M4 (2026-10-10)
`c08e8d9` (publish the 54 validated M4 topics), `f8002c7` (content render check
guarding cross-lesson links), `3bb5080` (fix 33 broken cross-lesson links),
plus a run of per-lesson content commits: lessons 53–70 covering the threshold
theorem, logical/physical qubits, error mitigation (ZNE/PEC/readout correction),
superconducting qubits, trapped ions, photonics, neutral atoms, spin qubits,
calibrated noise models, NISQ limitations, BQP/P/NP/BPP, benchmarking, the
quantum ecosystem, teleportation, and more.

---

## 4. Working tree vs. baseline — three commits not yet committed

These exist **only as uncommitted working-tree changes** (the sandbox re-cloned
and lost the local commits; push was blocked by the expired token).

| Was | Change | Files |
| --- | --- | --- |
| `21a253c` | Remove the Streamlit app; the React SPA is the only UI | 87 files, −14,508 lines |
| `7c75cfd` | Finish the cutover: docs, harnesses, last dangling references | 111 files total, −14,665 |
| `bbbb591` | Point leftover scripts and docs at the SPA instead of the dead port | — |

**Consequence for the PPT:** GitHub at `55d66f2` still *contains* the Streamlit
app. If a reviewer clones the branch today they will see two frontends. Commit
and push before presenting, or describe the SPA as "the intended single UI" and
disclose that the removal is committed locally but not yet pushed.

---

## 5. What could not be inspected

- **PR / issue metadata** — `gh` authentication failed; branch contents were
  verified via `git`, but no PR review history was read.
- **Any branch not listed above** — `git ls-remote --heads` returned exactly
  three, so none exist. This is comprehensive, not a partial survey.
- **The audit's `artifacts/ui-audit/`** — absent from this repository (see
  dossier §0).
