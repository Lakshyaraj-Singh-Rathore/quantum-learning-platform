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

---

## D-011b — The 531-vs-530 question is closed (shallow-clone artifact)

**Decision.** Withdrawn. D-011 rested on a false premise.

**Evidence.** `12d33df` was never a root commit; the clone was depth-1, so its parent was simply
absent. After `git fetch --deepen=300`, `git rev-parse --is-shallow-repository` returns `false`,
`origin/main` has a full history and the merge-base with this branch is `a805f30`. Counts are now
taken against a complete history and reconcile exactly.

**Rule.** Check `git rev-parse --is-shallow-repository` before drawing any conclusion from
`git log`, `git ls-tree` or a missing parent.

---

## D-013 — Loss function: squared loss on ±1 targets, not log-loss on probabilities

**Decision.** The VQC trains against `square_loss(decision_values, y_pm1)`, with labels mapped to
±1, rather than binary cross-entropy over `p = (1 + <Z> + bias) / 2`.

**Why — measured, not assumed.** The log-loss version produced a gradient norm of **199.96**
concentrated in a single parameter, and the loss *rose* across training (0.6601 → 0.6612) with a
degenerate confusion matrix `[[9, 0], [9, 0]]`. Root cause: `<Z>` saturates at exactly ±1, which is
precisely where `dL/dp ≈ 1/ε` for cross-entropy, so the gradient explodes at the boundary the
circuit naturally reaches. Squared loss on ±1 targets is bounded there. After the change all four
verification configs learn (see D-014).

---

## D-014 — Ansatz, and the single source of truth for parameter count

**Decision.** RY+RZ per wire per layer, then a CNOT entangler, giving
`n_params = n_layers * n_qubits * 2 + 1` (the `+1` is the bias, kept last in the flat vector).
`limits.n_parameters()` is the only place that formula is written; the circuit builder, the
persistence layer and the tests all call it.

**Supporting detail.** The ring entangler skips the wrap-around CNOT at `n_qubits == 2`, where it
would duplicate the first one. Z-encoding applies **H before RZ**, because `RZ` on `|0>` only
changes a global phase (see D-016). Verified learning (backprop, seed 7, 120 samples, batch 16,
lr 0.1, 15 epochs): moons/2q 0.250 → 0.905 train / 0.833 test; moons/4q → 0.893 / 0.833;
circles/2q → **1.000 / 1.000**; iris_binary/4q → 0.986 / **1.000**.

---

## D-015 — Vendored iris.csv (accepted by the senior; conditions already met)

**Decision.** `backend/app/quantum/qml_lab/data/iris.csv` is vendored: 2,734 bytes, 151 lines,
sha256 `f13ffa8f…d1449`, extracted from the official scikit-learn wheel and verified by hash.
scikit-learn itself is **never installed** (§1A).

**Status.** Accepted. The senior imposed two conditions and then withdrew them on inspection,
because Phase 1 already satisfied both: provenance (Fisher 1936, public domain, wheel path,
sha256) is recorded at `datasets.py:30-34`, and `_IRIS_CSV` is the only runtime path — nothing
reads the wheel. The pinned hash in `test_qml_datasets.py:207` was independently recomputed by the
senior and matched.

---

## D-016 — Compare density matrices, not states, when testing encodings

**Decision.** Encoding tests assert on `qml.density_matrix(wires=...)`, not `qml.state()` and not
`qml.probs()`.

**Why — found by mutation testing, not by reasoning.** Deleting the Hadamard from the Z-encoding
path left the test **passing**. `probs` is blind to a Z-rotation entirely; `state` *is* sensitive,
but only through a global phase, which is unobservable and therefore not a legitimate thing to
assert on — the test was green for a reason that had nothing to do with correctness. The density
matrix quotients out the global phase, so it distinguishes exactly what is physically
distinguishable. This is the backend twin of the QL-001 lesson: a green test is not evidence until
you have seen it fail.

---

## D-017 — Two tables: normalise the time series, blob the document

**Decision.** `qml_experiments` (config and result as JSON) **plus** `qml_epoch_metrics`
(append-only rows, `UniqueConstraint(experiment_id, epoch)`).

**Supersedes** my Phase 2 proposal of a single table with a JSON `history` column, which the senior
rejected on a stronger argument than the one I had: **SQLAlchemy does not detect in-place mutation
of a JSON column**, so appending an epoch and committing would silently persist nothing unless
every write called `flag_modified()`. The symptom — a progress bar that never advances — looks like
a frontend bug and would have cost a day. Rows have no such failure mode, make polling incremental
(`WHERE epoch > :seen`), and because `task_acks_late=True` makes Celery at-least-once, the unique
constraint turns a redelivered task into a no-op instead of a duplicated point on the loss curve.

**Verified:** removing the constraint from the model makes both redelivery tests fail (MUT-F).

---

## D-018 — Two timeout layers; the cooperative one is primary

**Decision.** `train(deadline_seconds=...)` checked in the same two places as `should_cancel`
(before every batch, and at each epoch boundary), **plus** `soft_time_limit`/`time_limit` on the
QML task decorator only. The engine deadline is `qml_task_soft_time_limit - 30`, so the cooperative
path always wins and the user sees `timed_out` with partial history rather than a
`SoftTimeLimitExceeded` traceback.

**Why both.** Celery's soft limit is implemented with **SIGALRM, which does not exist on Windows**,
and its hard limit kills a prefork child that `--pool=solo` does not have. On the stated target
platform *neither* Celery limit is reliable, and no Linux test can show otherwise. The cooperative
deadline is pure Python and works everywhere. §5.7 is discharged by documenting this, not by
testing it.

**`timed_out` is its own status**, distinct from `failed`: it is a resource outcome the user can
act on by shrinking the config, and collapsing it into `failed` would throw away the only
actionable advice available. Verified: `deadline_seconds=1.0` on a 50-epoch run yields
`status=timed_out`, 3 epochs completed, 1.13 s elapsed, 3 history records retained.

---

## D-019 — Concurrency is capped globally, and epoch columns keep the engine's names

**Decision (a).** `MAX_CONCURRENT_JOBS` (renamed from `MAX_CONCURRENT_JOBS_PER_USER`), counted
across **all** users. The protected resource is the single worker slot on one machine, not a
per-user quota. Per-user scoping would let a second user pass the check, enqueue, and then wait
silently behind the first job instead of being told immediately. Verified: scoping the guard to the
current user makes the cross-user test fail (MUT-B).

**Decision (b).** `qml_epoch_metrics` uses `test_loss` / `test_accuracy`, not `val_*`. This is a
deliberate, reported deviation from the column names sketched in §2A.1: the engine evaluates on the
held-out split it calls `test` (`Dataset.x_test`), `EpochRecord` already uses those names, and
there is no third split in Phase 1. Naming the columns `val_*` would require a translation layer
between the ORM and the engine whose only purpose is to rename two floats.

---

## D-020 — `/qml/features` is removed; the flag lives on an always-mounted `/features`

**Decision.** A single unauthenticated `GET /features` returns the flag **map**
`{"qml_enabled": bool}`, mounted unconditionally in `router.py` right after `auth.router`.
`GET /qml/features`, which §2A.6 asked to keep, is **deleted**.

**Why the deletion.** A flag endpoint behind the flag cannot answer the only question worth
asking. With the feature off, `/qml/features` 404s, and a 404 cannot distinguish "the server says
off" from "the request never arrived" — so the client would have to treat both identically and the
endpoint earns nothing. The capability payload §2A.6 described is already `/qml/describe`, verbatim;
keeping a second gated route would have made three names for one thing. `GET /backends`
(`api/jobs.py:45`) is the precedent for an unauthenticated capability read.

**Deviation, reported.** §2A.6 says to keep `/qml/features`. This removes it.

## D-021 — The nav gate needs `Sidebar.tsx` and `CommandPalette.tsx`, not just `nav.ts`

**Decision.** `nav.ts` gains a `flag?: keyof Features` field on `NavItem` and exports
`useNavItems()`, which filters gated entries. `Sidebar.tsx` and `CommandPalette.tsx` switch from
`NAV_ITEMS` to `useNavItems()`. `TopBar.tsx` keeps reading `NAV_ITEMS` and is **not** touched.

**Why it cannot be confined to `nav.ts`.** §4 permits touching only `nav.ts` for the nav item, but
`NAV_ITEMS` is a static `const` evaluated at module load, while the flag arrives asynchronously
over react-query. No change confined to `nav.ts` can hide an entry from a consumer that has
already read the array. The three consumers are `Sidebar.tsx:95`, `TopBar.tsx:17` and
`CommandPalette.tsx:70`.

**Why `TopBar.tsx` is left alone.** It reads `NAV_ITEMS` only to derive a page title
(`currentItem?.label ?? "Overview"`). It renders no link and offers no way to reach the route, so
it cannot leak the feature. Leaving the entry visible to it means the title reads "Quantum ML Lab"
when the flag is on; the cost is that a hand-typed `/qml-lab` with the flag **off** shows that
title above a 404 body. That is cosmetic, and strictly better than the alternative, which is
"Overview" on a legitimately enabled lab.

**Deviation, reported.** Two files outside the §4 allowlist are modified. Both are modified for
one reason: without them the sidebar and the command palette advertise a feature this deployment
has switched off.

## D-022 — The flag has three states, and the third is the one that breaks

**Decision.** `useFeatures()` returns `{ features, resolved, isError }`. Consumers hide gated UI
unless `features.qml_enabled === true`; the route additionally waits for `resolved` before
rendering its 404 branch.

**Why.** A flag is on, off, or *not yet answered*. Code that reads `data?.qml_enabled` collapses
the third into the second, so a user who **has** the feature sees a 404 flash on every hard
refresh before the lab appears. Hiding-then-revealing is correct in both directions: nothing is
ever rendered and then retracted, and nothing is ever offered that cannot be opened.

An error is treated as a resolved "off" — fail closed, and silently. For every deployment without
the feature, off is the normal state, so surfacing it as an error would be noise.

## D-023 — The circuit preview is checked against a real PennyLane tape, not a restatement

**Decision.** `scripts/qml-circuit-fixtures.py` builds the genuine ansatz with
`apply_angle_encoding` + `apply_ansatz`, captures `tape.operations`, and writes
`test-fixtures/qml-circuit-golden.json`. `scripts/qml-circuit-check.mts` rebuilds each case in
TypeScript and compares.

**Why not a positional diff.** PennyLane emits Z-encoding as `H(0),RZ(0),H(1),RZ(1)` while the IR
builder groups the Hadamards first. Single-qubit gates on disjoint wires commute, so that is not a
defect — but an index-by-index comparison would fail on it permanently and get deleted. The
harness instead compares the per-wire operation sequence (with control and target roles
distinguished), the ordered two-qubit pairings, and the backend's own parameter counts. Agreement
on all three means the circuits differ at most by reordering gates on disjoint wires.

**`parameterCount` excludes the bias.** `limits.n_parameters` is `n_layers * n_qubits * 2`; the
trainable bias is classical and counted separately (`limits.py:106-113`). An earlier draft added
`+ 1` and would have reported a drift against the server on every run.

## D-024 — Three `.mts` harnesses, twelve mutants, and two of them initially survived

**Decision.** `npm run qml:circuit`, `npm run qml:ui`, `npm run qml:render` — 49, 58 and 33
assertions. Every one was mutation-tested.

**What the campaign actually bought.** Four of twelve mutants exposed defects in the *tests*:

- Two mutants (QL-001 interpolation, a non-existent class) appeared to be caught but had never
  applied — they targeted a `className="…"` literal that does not exist, because those classes
  live inside `cn(…)`. Validating the mutant itself revealed that the guard only scanned
  `className="…"` attributes and had never looked inside `cn()` at all. Both checks now scan every
  string literal in the comment-stripped source: 16 colour utilities and 36 interpolated templates,
  up from a handful.
- Blanking every chart line left the harness green, because the gradient *area* path still carried
  `M…L…L` geometry. The check now counts only `fill="none"` stroked paths.
- Transposing the confusion matrix left it green, because `[[23,4],[3,30]]` transposed contains the
  same four numbers. The check now reads cell positions out of the markup in document order.
- Flattening the y-scale (every curve a horizontal line) left it green. The check now requires each
  curve to span a range of y values.

Lesson, consistent with Phase 1 and 2: a passing assertion is not evidence until something has been
broken underneath it, and a mutant that "is caught" must be confirmed to have applied.

## D-025 — The render fixture is captured from the live server, never hand-written

**Decision.** `test-fixtures/qml-describe.json` is a recorded `GET /qml/describe` response.

**Why.** The first draft of the render harness hand-wrote the capability payload and invented
`learning_rate`, `noise`, `test_fraction` and `seed` limits. The server publishes none of them — it
publishes `batch_size, concurrent_jobs, density_matrix_qubits, epochs, n_layers, n_qubits,
n_samples`. The harness was therefore testing a contract that does not exist. Those four form
fields now read "validated on submit" instead of a bound, which is the truth: the server still
rejects an out-of-range value, but it does not advertise the range.

## D-026 — The benchmark measures the engine directly, and is not wired into the Makefile

**Decision.** `backend/scripts/bench_qml.py`, run by hand from a documented invocation
(`docs/qml/04-benchmarks.md` §1), not `make bench`.

**Why not the Makefile.** Every existing target in it shells into Docker Compose
(`$(COMPOSE) exec api …`). A `make bench` would therefore time the *container*, which is
exactly the machine §2B.1 says must not be used to set limits. `Makefile` is also absent from
§4's allowed-touch-points table, and the target OS is Windows, where `make` is usually not
installed. §2B.2 accepts "wired into the Makefile **or** with the exact invocation documented";
the second branch is the one that measures the right machine, and it keeps Phase 4 additive.

**Why engine-direct.** The script builds a `VQC` and differentiates the trainer's own
`square_loss ∘ decision_values`. Measuring through the API with `celery_task_always_eager`
would fold in FastAPI validation, session handling and DB writes, and would have attributed
them to the simulator.

## D-027 — Parameter-shift at the maximum configuration is structurally infeasible; the ceiling should depend on the gradient method

**Measured** (`--full`, 2-core sandbox, median of 5 projections at 8q/4L/1000 samples/100 epochs):
backprop 121.8 min, parameter-shift on `lightning.qubit` 377.9 min, parameter-shift on
`default.qubit` 1,539.3 min (25.7 h). Against the provisional 900 s soft limit that is 8.1×,
25.2× and 102.6×.

**Decision.** Record the design, do **not** implement it in Phase 4.

The recommended shape is (1) an up-front estimate before dispatch using the *corrected* cost
formula, rejecting cleanly with the estimate included in the error, plus (2) a
gradient-method-dependent ceiling as the backstop. §2B.3 names this a real `limits.py` design
change and requires it to be recorded here, which is what this entry is.

**Why not implement now.** The constant that makes a ceiling correct is a wall-clock
measurement on the target machine (i5-13450HX / 16 GB / Windows). Deriving it from a 2-core
container would be a limit tuned "wrong in the dangerous direction" in §2B.1's exact words.
`limits.check()` today validates a configuration once, not per gradient method; that is the
structural gap, and it is the senior's call plus one measurement away from being closable.

**Corollary, measured.** Increasing `batch_size` buys no speed: `vqc.py:99-102` loops per
sample with no broadcasting, and parameter-shift cost per sample is flat to 2.3% across an 8×
batch change. Batch size is a statistics knob here, not a throughput knob.

## D-028 — `limits.estimate_cost` undercounts by `(epochs − 1) · n_samples`; proposed fix, not applied

**Found by measurement.** `estimate_cost` (`limits.py:116-146`) charges one evaluation pass
(`eval_execs = config.dataset.n_samples`, line 137). `trainer.train` evaluates **both splits at
the end of every epoch** (`trainer.py:220-221`). Counting a real training run with
`qml.Tracker` (2q/1L/B16, 3 epochs, 60 samples): measured 306 backprop / 1,314 parameter-shift
against the estimator's 186 / 1,194 — short by exactly 120 = `(3−1)·60` in both cases. The
corrected form `epochs·n_train·per_sample + epochs·n_samples` reproduces the Tracker count
exactly.

At the maximum configuration the estimator says 71,000 backprop executions; the truth is
170,000 — **understated 2.39×**, because the per-epoch evaluation is 59% of all backprop
executions.

**Decision.** Report and propose; do not apply in Phase 4. The additive gate requires
`git diff --diff-filter=MD` against `origin/main` to be empty, and Phase 4's scope is a script
and a document. The change is one line (`eval_execs = config.training.epochs *
config.dataset.n_samples`).

**Risk if left.** None today — `grep -rn "estimate_cost" --include=*.py app/` finds no call
sites. But its own docstring says it is "used by the UI to warn before submission", and D-027
proposes building a dispatch-time rejection on it. It must be corrected **before** either of
those lands, or both will be wrong by 2.4× for the default gradient method.

## D-029 — `lightning.qubit` is already available and was measured; nothing was installed

**Finding.** `pennylane-lightning 0.45.0` is importable without any change to
`requirements.txt` — it arrives **transitively** with PennyLane 0.44.1. §2B.5's conditional
("if not installed, do NOT add it") therefore never triggered: no `pip install` was run, no
`--dry-run` was needed, and no pin moved.

**Measured.** Agrees with `default.qubit` to 15 dp (`<Z₀> = 0.955336489125606`). Speeds up
parameter-shift by 2.3× at 2 qubits rising to **4.1× at 8 qubits / 4 layers**. **Cannot do
`backprop`** — `QuantumFunctionError` — so any device × method grid must skip that pair rather
than record it as a failure. Since backprop is the default, lightning only helps the expensive
path, but that is where it is needed.

**Unresolved, flagged deliberately.** `pennylane-lightning` is an **unpinned transitive
dependency** at a *higher minor version* (0.45.0) than PennyLane itself (0.44.1). It is not in
`requirements.txt`, so a future clean install could resolve a different version and silently
change benchmark numbers or device behaviour. Not pinned unilaterally — adding a line to
`requirements.txt` is a §1.3 dependency decision and needs the dry-run discipline plus
sign-off.

**`adjoint` is the larger opportunity.** On `lightning.qubit` it returned a gradient identical
to backprop's (`-0.479425539`) at `O(1)` executions rather than `O(P)`. Unmeasured at scale,
and not adopted here; raised as a Phase 5 design question.

## D-030 — GPU was skipped entirely, as instructed

No GPU work was attempted. `lightning.gpu` requires CUDA on Linux and the target is Windows
(⇒ WSL2); this repo's GPU support is CUDA-Q via `docker-compose.gpu.yml`, a separate stack that
does not compose with a PennyLane device. The sandbox has no GPU and no `docker` binary, so
even an exploratory check was impossible. Recorded so no later phase reads the silence as an
oversight.
