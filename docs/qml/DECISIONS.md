# QML Lab — Decision Log

Running log of consequential decisions, each with its reason and the evidence behind it.
Append-only: superseded entries are struck through and replaced, never deleted.

| ID | Phase | Decision | Status |
|---|---|---|---|
| D-001 | 0 | Work on the session branch, which carries `main`'s exact tree | Active (deviation, declared) |
| D-002 | 0 | All QML evidence lives in tracked `docs/qml/`, never `artifacts/` | Active |
| D-003 | 0 | Do **not** install torch | Active |
| D-004 | 0 | `parameter-shift` is the production diff method; `backprop` is the test oracle | Active |
| D-005 | 0 | QML Lab gets its own route, unlike Noise Lab / Smart Composer | Active |
| D-006 | 0 | Every QML schema is `extra="forbid"` with required nesting | Active |
| D-007 | 0 | Cancellation is cooperative via a DB flag, not Celery `revoke` | Active |
| D-008 | 0 | Per-task time limits go on the QML task decorator only | Active |
| D-009 | 0 | Density-matrix qubit cap proposed at 6, to be re-tuned from P4 data | Provisional |
| D-010 | 0 | `push-overlay-check` recorded as BLOCKED, not PASS or FAIL | Active |
| D-011 | 0 | Tracked file count 531 reported, not adopted as a new baseline | Open question |
| D-012 | 0 | Charts are hand-rolled SVG; no new runtime dependency of any kind | Active |

---

## D-001 — Branch: session branch carrying `main`'s tree

**Decision.** All work happens on `arena/63ae45b4-quantum-learning-platform`, whose tree is byte-identical
to `origin/main @ 12d33df`. Commits and pushes go to the session branch. **Nothing is pushed to `main`.**

**Why this is a deviation.** The user instructed: *"You are meant to work in main branch — your side branch
was deliberately destroyed and the main features were transferred to main branch."* The amendment (§2)
agrees `main` is the base and forbids `feature/quantum-ml`.

**Why it is unavoidable.** The session is pinned to this branch by the platform and tracked by its name;
work committed elsewhere is not associated with the session, and the branch cannot be renamed.

**How the conflict was resolved without losing anything.** The prior side-branch history was destroyed
upstream: `git fetch origin arena/63ae45b4-…` → `fatal: couldn't find remote ref`, and commit `20dab0c` is
not a valid local object. Rather than `reset --hard` (forbidden), the stale pre-sync state was first
committed as a recoverable snapshot (`8770440`), then `git read-tree -u --reset origin/main` adopted main's
exact tree (`648dec4`). `git diff origin/main` is empty; `git status` is clean. Before adopting, all 88
then-untracked files were checked against `origin/main` and confirmed already present there — the only
local-only delta was a stale Streamlit comment block in the root `requirements.txt`.

**Consequence.** The branch name differs from `main` but the *content* lineage is exactly main's. Every
phase report repeats this deviation. Merging to `main` is the user's call; P8 produces no merge step (§8
amendment).

---

## D-002 — Evidence in `docs/qml/`, never `artifacts/`

**Decision.** Every report, measurement and log for this task is committed under `docs/qml/`.

**Why.** `artifacts/` is gitignored. The previous campaign's 43 MB evidence package was force-added there
and **did not survive** the clone reset — it is permanently gone, while the source fixes it justified
survive in `main`. Evidence that cannot be re-read is evidence that does not exist. Amendment §2.3 forbids
`git add -f` under `artifacts/`; this log records *why* that rule is correct.

---

## D-003 — No torch

**Decision.** torch will not be installed. `requirements.txt` is expected to need **no change at all**.

**Evidence.** `pip install --dry-run torch` would install **24 packages** — torch 2.14.1, triton, and the
full CUDA toolkit (`cuda-toolkit-13.0.3.0`, `nvidia-cudnn-cu13`, `nvidia-nccl-cu13`, …).

**Important nuance, stated precisely:** the resolver did **not** request `numpy>=2`. `numpy==1.26.4` and
`scipy==1.17.1` are untouched by it, so the §1.3 STOP condition did **not** fire. The refusal is therefore
a **choice, not a constraint**: multi-GB of GPU runtime for a CPU-only simulation feature, when the
alternative is already installed and proven (D-004). Not installing it also keeps the §1.3 pin wall
trivially intact.

---

## D-004 — `parameter-shift` in production, `backprop` as the oracle

**Decision.** The P1 engine uses `qml.device("default.qubit")` with `interface="autograd"` and
`diff_method="parameter-shift"`. Tests additionally compute the same gradient with `diff_method="backprop"`
and assert agreement.

**Evidence (run in Phase 0, not assumed).** A 2-qubit `AngleEmbedding` + `BasicEntanglerLayers` QNode
differentiated both ways: `max|ps − bp| = 2.220e-16`, agreement at 1e-9 **True**, `torch` absent from
`sys.modules`, numpy still 1.26.4.

**Why it matters.** This satisfies the master prompt's "gradients via a supported method" and
"backprop vs parameter-shift agreement" criteria using only installed packages, and it is the reason D-003
costs nothing.

**Recorded risk (no action).** PennyLane 0.44.1 emits
`PennyLaneDeprecationWarning: … dropped maintainence support for NumPy < 2.0.0`. It works today. A future
PennyLane upgrade would force `numpy>=2`, which `cirq-core 1.4.1` cannot accept. The pins do not move
under this task (§1.3); the tension is logged so it is a known future decision rather than a surprise.

---

## D-005 — QML Lab is a route, not an embedded panel

**Decision.** `/qml-lab` is a top-level route with its own nav entry in the `build` section.

**Why this is a departure.** Noise Lab and Smart Composer are *not* routes — both are embedded in
`ComposerPage.tsx` (imports `:60-61`, mounted `:584` and `:824`).

**Why depart anyway.** The QML Lab has four distinct views, long-running asynchronous jobs, a polling
lifecycle and a cancel control. Embedding it in another page would couple its lifecycle to that page's
mount state and would require editing `ComposerPage.tsx` — a do-not-touch file (§4). A route keeps the
feature entirely in new files and makes flag-gating a clean 404.

---

## D-006 — Strict schemas: `extra="forbid"`, required nesting

**Decision.** Every QML Pydantic model sets `model_config = ConfigDict(extra="forbid")`, requires explicit
nesting, and has a test asserting that a flat or misshapen payload returns **422** rather than a success.

**Evidence — the trap reproduced in Phase 0.** `NoiseConfig(depolarizing=0.35, amplitude_damping=0.1,
t1=50.0)` is **accepted**; `model_config.extra` is the Pydantic default `ignore`; all five groups come back
`enabled: False`. A caller sending a plausible flat payload silently receives a noiseless result that looks
like a real answer. Nothing raises.

**Rule.** A wrong-shaped QML config must fail loudly. Silence is the defect.

---

## D-007 — Cooperative cancellation via a DB flag

**Decision.** Cancel sets a column on the experiment row; the trainer checks it **between minibatches** and
exits cleanly, recording partial progress and a `cancelled` terminal state. No Celery `revoke`,
no `SIGTERM`.

**Evidence that there is no precedent to copy.** `grep -rn "revoke\|terminate" backend/app --include=*.py`
returns only unrelated hits in `app/services/codelab.py` (sandbox capability revocation). `api/jobs.py` has
**no cancel endpoint**. This is greenfield, so the design is stated here rather than inherited.

**Why cooperative.** `revoke(terminate=True)` kills the worker process mid-write and cannot run cleanup;
a flag check between batches gives a deterministic, testable cancellation point and preserves partial
results. It also behaves identically under `task_always_eager`, which the Windows/eager path needs (§6).

---

## D-008 — Per-task time limits on the decorator only

**Decision.** Add `qml_task_soft_time_limit: int = 900` and `qml_task_hard_time_limit: int = 1200` to
`config.py` and apply them **only** on the QML task decorator:
`@celery_app.task(bind=True, soft_time_limit=settings.qml_task_soft_time_limit, time_limit=settings.qml_task_hard_time_limit)`.

**Why the global values must not move.** `celery_app.py:20-21` applies `celery_soft_time_limit` (**8 s**)
and `celery_hard_time_limit` (**15 s**) to *every* task via `conf.update`. Worse,
`workers/tasks.py:96` *derives* a value from it:
`budget = max(5.0, get_settings().celery_soft_time_limit - 1.0)` — the qBraid remote-wait budget. Raising
the global limit to suit QML would silently extend qBraid's wait on a paid remote queue. This is the
concrete harm §1.1 exists to prevent.

**Proof obligation (P2).** Both directions must be demonstrated: a QML task is allowed to exceed 8 s, and a
non-QML task is **still** killed at the old limits. Verified on Linux; see the §6 OS caveat in
`00-audit.md` — the Windows `--pool=solo` half cannot be proven from this sandbox.

---

## D-009 — Density-matrix cap of 6 (provisional)

**Decision.** Propose a density-matrix qubit cap of **6**, against a state-vector cap of 8.

**Why provisional.** The master prompt asks for 4–6 and requires limits to be tuned from measured data.
P4 benchmarks will either confirm 6 or lower it. It will not be **raised** without measurements.
Existing caps (static 20 / dynamic 15 / GPU 28 / `PREVIEW_MAX_QUBITS = 12`) are settled and untouched.

---

## D-010 — `push-overlay-check` is BLOCKED

**Decision.** Record it as **BLOCKED (environment)** in every baseline table — never PASS, never FAIL.

**Evidence.** It is the only real Playwright harness. It seeds a fabricated token
(`scripts/push-overlay-check.mts:115`) into `localStorage.ql-session`; the live API rejects it, the shell
redirects to `/login`, and it times out on `waitForSelector('aside')`. With no API running it instead
prints 6 ECONNREFUSED proxy errors. Either way it contributes **0 PASS**, which is exactly why the
documented 284/57 reconciles without it.

**Rule.** It is not evidence for or against any QML change. Separately, `scripts/verify-all-demos.mts`
must **never** be cited as evidence — its assertions at lines 119-123 are tautological (§1.5).

---

## D-011 — File count 531 vs 530 (open)

**Decision.** Report **531** as measured; do **not** adopt it as a corrected baseline.

**Evidence.** `12d33df` is a root commit — `git ls-tree -r --name-only 12d33df^` fails with
`fatal: Not a valid object name`, so the extra file cannot be identified by diffing a parent.
`git ls-files | wc -l` minus `docs/prompts/QML_LAB_VISION_AGENT.md` is exactly **530**, which is consistent
with the amendment doc itself being the +1 — arithmetic consistency, not proof.

**Status.** Flagged for the senior agent. All seven *gates* match exactly, so this does not block Phase 1.

---

## D-012 — No new runtime dependencies; SVG by hand

**Decision.** No package is added to `package.json` or `requirements.txt` for this feature.

**Why.** No charting library exists (0 hits for `recharts`/`chart.js`/`d3`/`victory`/`nivo`/`visx`) and
§1.4 forbids adding one. Only three Radix packages are installed and only those three may be used. Loss
curves, accuracy curves, confusion matrices and probability bars are hand-written SVG using
`var(--accent)`, `--ok`, `--warn`, `--danger`, `--line`, with data-driven colour applied via inline `style`
per QL-001 (D-013 territory — see `ui-audit.md` §2).
