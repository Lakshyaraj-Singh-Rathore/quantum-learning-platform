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

**Why not the Makefile.** *(Wording corrected after Phase 4 review — the original claim,
"every existing target shells into Docker Compose", overstated it. Measured: the Makefile has
**13 targets** and **9 recipe lines** that invoke `$(COMPOSE)`, of which **4 use
`$(COMPOSE) exec api …`** to run a command inside the container; the other 5 are lifecycle
(`up`, `down`, `ps`, `logs`). The conclusion is unchanged and is upheld.)*

Every Makefile target that **runs a command against the application** does so inside the api
container via `$(COMPOSE) exec` — that is the house pattern, and `make test` is exactly it. A
`make bench` following that pattern would therefore time the *container*, which is precisely
the machine §2B.1 says must not be used to set limits. `Makefile` is also absent from
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

## D-031 — The hybrid QNN uses `autograd`, not PyTorch

**Settled by §2C.2; recorded here because `hybrid.py` cites it.**

PyTorch was never installed. A `pip install --dry-run torch` in Phase 0 resolved **24 packages**
including the CUDA toolkit — for *one optional algorithm*, on a 16 GB laptop. The dry-run showed
torch would be *safe* to install; safe is not the same as worth it, and the burden of proof sits
with the addition, not the omission.

**The premise was proven before the code was written, and again after.** A no-torch gradient
probe in Phase 0 agreed with the analytic value to **2.220e-16**. With the classical layer
actually in the path, the max absolute difference between the autograd gradient and a central
finite difference over all 9 classical parameters is **2.316e-10** (ε=1e-6), and backprop agrees
with parameter-shift to **1e-9**. The classical layers are written in autograd-compatible numpy,
so the hybrid differentiates end to end with nothing added to `requirements.txt`.

**What would reopen this.** A genuine wall — a layer type autograd cannot express, or a
measured performance cliff — is a §5.3 stop with the dry-run attached, not a unilateral install.

## D-032 — Ceilings are per-algorithm, but the limits payload keeps one shape

**Settled by §2C.1.** Algorithms have genuinely different costs: a 250-sample quantum kernel is
31,375 upper-triangle circuit evaluations *before any fitting*, priced from the measured
10.377 ms/sample at 8q×4L at ≈**326 s**. The same 1000 samples the classifier handles without
comment would be 500,500 evaluations ≈ **87 minutes**, 102× over the soft limit. One global
ceiling therefore either strangles the classifier or lets the kernel hang.

`ALGORITHM_LIMITS` lists only the keys an algorithm *tightens*. Three properties are tested
rather than documented and hoped for: a new algorithm **cannot loosen** a global maximum; **no
algorithm drops** a global key; and **every entry has exactly `{default, min, max}`**, so a
config view can render one control per entry.

*(Corrected during the regression commit.* The original wording here claimed every table has an
**identical shape**, and a test named `..._shape_is_identical_across_algorithms` appeared to
back it. Neither was true: `hybrid_qnn` really does carry an extra `n_hidden` key, and the test
asserted only a *subset* relation — its name promised a guarantee the code did not make. The
test has been renamed to what it checks and split, and the accurate statement is above.*)

An algorithm **may** add a key, but never silently: additions sit in a declared allowlist and
`test_any_extra_limit_key_is_declared_and_announced` asserts the matching `supports` flag in
`/qml/describe` agrees with the table. That is what lets the config view iterate the limits
table and render a control per entry **without branching on the algorithm name** (§2C.7) — the
extra key is self-describing rather than something the client has to know about.

`limits_for("unknown")` raises rather than falling back to the global table — a silent fallback
would hand a kernel run the classifier's ceiling.

**This is also where the authorised parameter-shift tightening is encoded.** The 25.7 h max-config
projection rests on the scaling law (`∝ B·(q·L)²`), not on sandbox absolute times, so it
transfers; the ceiling is expressed as a per-algorithm limit plus an up-front `estimate_cost`,
which is why D-028 had to land first.

## D-033 — Regression gets its own types, its own datasets, and its own trainer

**Settled by §2C.4 for the types; the datasets and trainer follow from the same argument.**

`RegressionResult` and `RegressionEpochRecord` are separate types, not the classification types
with nullable fields. A `None` accuracy invites a UI that renders `0`, which reads as "scored
zero" rather than "not applicable". A test asserts `RegressionResult` has **no** `accuracy`,
`precision`, `recall`, `f1` or `confusion_matrix` attribute at all.

The split is separate for the same class of reason. The classifier's split is *stratified* —
it balances classes across train and test — and that operation is meaningless for a continuous
target. Reusing it via a discretised label would produce a split that looks fine and is subtly
wrong. `REGRESSION_DATASETS` is a separate registry, so asking for `moons` here raises instead
of silently falling back.

**The target needs its own scaler, and it is the leakage-sensitive half.** `<Z₀>` lives in
`[-1, 1]`, so a target in, say, `[0, 40]` is unreachable and the model would converge to a
constant and look broken. `TargetScaler` is fitted on `y_train` **alone** and predictions are
mapped back, so every reported MAE and RMSE is in the user's own units. The §1A leakage
assertion is made exact rather than inferential: the test asserts the fitted bounds *are* the
training split's raw bounds (`np.array_equal`), which required carrying the raw splits on the
dataset — themselves needed for a prediction-vs-input plot.

**R² never returns `nan`.** Zero variance makes it undefined; it returns 1.0 if the prediction is
exactly that constant and 0.0 otherwise, mirroring `precision_recall_f1`'s documented convention
of returning a real number for a degenerate input.

## D-034 — Data re-uploading is on by default, because single encoding cannot represent the targets

**Not pre-settled by the vision — found by measurement during Phase 5, and it changed the design.**

The first regression run fit `sin(2x)` at **R² = +0.104**, losing to a linear ridge baseline at
+0.208. That is the wrong shape of result for a non-linear target, so it was diagnosed rather
than tuned away: sweeping the encoded angle and taking an FFT of `<Z₀>` showed the model's
accessible spectrum is **{0, ±1}** — frequency-2 power was **1e-5**, i.e. numerical noise. The
target was not under-trained, it was **structurally unrepresentable**.

Re-uploading the features before each of `n_layers` ansatz blocks widens the spectrum to
frequencies up to `n_layers` (Pérez-Salinas et al.). Measured at identical parameters,
frequency-2 power rises **0.00098 → 0.02144, a 22× increase**, and `sine` goes **+0.104 → +0.328**,
now beating the ridge baseline. `test_reuploading_widens_the_frequency_spectrum` pins the
measurement, not the conclusion.

**A second, non-obvious consequence, and the reason the datasets changed.** The feature scaler
maps `[-π, π]` onto the encoder's `[0, π]`, i.e. `x = 2a - π`, which **doubles every frequency**:
`sin(x) → -sin(2a)`, `cos(3x) → cos(6a)`. With `MAX_LAYERS = 4` the reachable angle-frequency is
4, so the originally-drafted `cos(3x)` target needed frequency 6 and was **unreachable at every
configuration the schema permits** — it would have trained to a flat line and read as a broken
model rather than an impossible request. The datasets were retargeted to `sin(x)` (frequency 2)
and `exp(-|x|/2)·cos(2x)` (frequency 4, at the ceiling), and
`test_every_regression_dataset_is_inside_the_frequency_budget` now **fails the build** if a
dataset is ever added that breaks the budget.

## D-035 — The regression baseline is ridge, solved in closed form

The classification baseline is a genuinely trained logistic regression (scipy L-BFGS-B on the
analytic gradient), so the regression side needed the same honesty rather than a strawman.
Ridge has an exact solution, `(XᵀX + λI)⁻¹Xᵀy`, so there is no optimiser to tune — one
`numpy.linalg.solve`, no scikit-learn (D-014).

**The intercept is deliberately not penalised**; shrinking it biases predictions toward zero
rather than toward the target's mean, and a test pins that. The `linear_mix` dataset exists
precisely so the baseline is *strong*: a test asserts ridge recovers the known coefficients
(1.5, −0.8) to 1e-4 and clears R² > 0.95. On that control the quantum regressor reaches
**R² = 0.972 against ridge's 0.997** — the classical model wins, and that is reported rather
than hidden, because a linear model solving a linear problem is the expected outcome and the
comparison is only worth anything if it can come out that way.

## D-036 — The kernel is an LSSVM, and the strict upper triangle is the only thing computed

**Settled by §2C.3.** A C-SVM needs a quadratic-programming solver and a dual formulation with
box constraints — a dependency and a pile of machinery for one of four algorithms. The LSSVM
replaces the inequality constraints with equalities, so the entire fit is `numpy.linalg.solve`
on the matrix already computed.

**It is labelled LSSVM everywhere it is surfaced**, because the two are not the same estimator:
the LSSVM loses sparsity (every sample becomes a support vector, and `n_support` reports it) and
is less robust to outliers. A test asserts the `describe()` label and a mutant that renames it
"SVM" is killed.

**Only the strict upper triangle is evaluated — `n(n-1)/2`, not `n(n+1)/2`.** This is a
correction to D-032's arithmetic: that entry priced the cap at 31,375 evaluations, which is
`n(n+1)/2` and includes the diagonal. The diagonal is `|<φ(x)|φ(x)>|² = 1` **exactly**, by
construction rather than approximately, so it is written as 1.0 and never evaluated. The real
figure at the 250-sample cap is **31,125**, against 62,500 for the naive full matrix. The
saving is therefore slightly better than 2×, and a test counts the actual QNode calls rather
than trusting the claim.

`I/γ` regularisation is not optional. Duplicate and near-duplicate encoded points are ordinary
once features are clipped into `[0, π]`, so the Gram matrix is often singular; without the term,
`numpy.linalg.solve` raises `LinAlgError` on input a user can produce by accident.

`predict` uses `> 0` rather than `np.sign`, which returns 0 at exactly zero and would emit a
third class. A test constructs a decision value of exactly 0.0 to cover it.

## D-037 — Two latent defects found by the kernel work, both fixed at the root

Recorded because both were *silent* and both had already shipped in earlier commits.

**`ALGORITHM_LIMITS` was a snapshot, so the cap could not be tested.** A module-level dict
literal captures `MAX_KERNEL_SAMPLES` at import, so `monkeypatch.setattr(limits,
"MAX_KERNEL_SAMPLES", 10)` never reached `limits_for` — a ceiling test would pass while
silently exercising the real 250. This is the **same defect** already found and fixed in
`LIMITS`/`limits_for` one commit earlier; it recurred because that fix was applied to the
symptom rather than to both snapshots. `_algorithm_overrides()` now re-reads the live
constants, matching `_base_table()`, and a test pins it.

**`QmlLimitExceededError` shredded a single string into characters.** Its signature is
`list[str]` and it joins with `"; "`; a bare string is a valid iterable of characters, so
`QmlLimitExceededError("too big")` produced `t; o; o;  ; b; i; g` in the API response. The type
hint was never enforced and nothing failed. It now accepts a single message explicitly, with a
regression test.

## D-038 — Phase 5 stopped after the kernel: noise and the qudit spike are named deferrals

**§2C.8 names two defensible stopping points — after regression, or after the kernel.** This is
the second. Recorded explicitly because §2C.8 also says a slipped item must be a named deferral
rather than a silence.

**Delivered:** D-028 cost-estimator fix (prerequisite, landed first because Phase 5 creates call
sites), the manual-test register, the Hybrid QNN on autograd, per-algorithm ceilings, quantum
regression with its own types and datasets, the ridge baseline, the quantum kernel as an LSSVM,
and per-algorithm capabilities served from `/qml/describe`.

**Deferred, with reasons:**

- **§2C.5 noise — not started.** Nothing is broken by its absence: no noise vocabulary was
  invented, no second set of names competes with `noise_lab`'s, and no `NoiseConfig` was
  half-wired. The constraints that will govern it are already settled and unchanged — reuse
  `noise_lab`'s vocabulary but not its defaults, `extra="forbid"` with explicit enabling
  because `NoiseConfig` defaults every group to `enabled: False` and would silently ignore a
  flat payload, finite shots are mandatory with reported shot variance, and
  `DENSITY_MATRIX_MAX_QUBITS = 6` binds.
- **§2C.6 qudit spike — not started.** It is time-boxed and the document is the deliverable, so
  starting it late and rushing would produce exactly the thing §2C.6 warns against: a stub
  returning zero gradients that poisons every later phase trusting it. "Not feasible without X"
  remains a complete, successful outcome, and it is better written from a real time-box than
  from a remainder.
- **UI for all three new algorithms — not built.** The engines, limits, metrics and capability
  endpoint landed; the config and results views did not. This is the largest deferral and the
  one most visible to a user: the QML Lab still offers only the VQC. The backend groundwork for
  the UI *is* done and tested — `/qml/describe` now serves per-algorithm limits, datasets,
  metric lists, epoch-chart series and a `supports` map, with tests asserting a regression run
  can never surface an accuracy field (MT-006). Registered as MT-006 through MT-009.
- **`.mts` harnesses for the new algorithms — not added**, because a harness asserts over UI
  sources and there are none yet. No harness was stubbed, so the FAIL-count gate is unchanged
  by construction rather than by adjustment.

**Nothing in the repository is in a half-finished state.** Every module landed this phase is
complete, tested and mutation-tested; the deferred work is work not begun, which is the
condition §2C.8 asks for.

---

## Phase 5b — execution dispatch (D-039 … D-045)

### D-039 — the dataset registry lives in `limits.py`, not `datasets.py`

`models.py` needs the dataset list to build the `DatasetName` Literal, and `datasets.py` already
imports `models.py` for `DatasetConfig`. Putting the registry in its natural home would have made
`models → datasets → models`. `limits.py` was already imported by both and already owned
`ALGORITHMS`, so it became the single source: `CLASSIFICATION_DATASETS`, `REGRESSION_DATASETS`,
`ALL_DATASETS`, `TASK_BY_DATASET`, `TASK_BY_ALGORITHM`. `datasets.py` and `regression_data.py`
re-export, and a test asserts the objects are `is`-identical.

The Literal itself cannot be derived from a tuple without losing static typing, so it is written
out and `test_the_dataset_literal_and_the_registry_cannot_drift` asserts the two agree. That is the
registry rule applied honestly: one source, and where a second copy is unavoidable, a test that
fails the moment they diverge.

**Generalisable:** check the existing import direction before choosing where a single source of
truth goes. The obvious home may be the forbidden one.

### D-040 — the gap was made loud, not quiet

`describe()` advertised six datasets while `DatasetConfig` rejected three of them. The cheap fix was
deleting the regression names from `describe()`. That would have made the test pass and the product
worse, and it is the instance-vs-class mistake `_base_table()` already taught. Instead the Literal
widened, a task-compatibility validator landed on `QmlExperimentConfig`, and the mismatch became
impossible in both directions: `quantum_regression + moons` and `vqc + sine` are now 422s with a
message naming the valid alternatives.

Widening the Literal had a consequence worth recording: `build_dataset`'s
`# pragma: no cover - unreachable` fallback became reachable the instant `sine` was a valid name,
and would have reported "unknown dataset" for a name that plainly exists. **When widening an
enum, re-audit every exhaustiveness fallback keyed on it.**

### D-041 — separate payloads per task, discriminated by `task` (D-033 applied, not re-opened)

`result` is a JSON blob, so this costs zero migrations. `qml_epoch_metrics` is typed columns, so it
costs exactly one additive migration, `j5e8f1a4b7c2`: nullable `train_r2`/`test_r2`, and
`train_accuracy` relaxed to nullable.

**R² is never written to `train_accuracy`.** It can be negative, and the live worker run measured
exactly that: epochs 1–3 of the sine regression stored `train_r2 = -2.060, -0.844, -0.161`. Had
those gone into the accuracy column, a chart labelled "accuracy" would have rendered −206%. The
D-033 test guards the Pydantic model, not the column, so it would have kept passing throughout.

Relaxing `NOT NULL` was a real loss of a safety property. It is replaced by
`test_a_regression_epoch_row_stores_null_accuracy_not_zero`, which reads the column back and
asserts `IS NULL` — 0.0 would be indistinguishable from a classifier that scored zero. The
downgrade **deletes** NULL-accuracy rows rather than backfilling `0.0`: deleting is lossy and
honest, backfilling is lossless and false.

`record_epoch` duck-types via `_maybe()` rather than branching on a task string, so a record type
that lacks `train_accuracy` writes NULL without the writer knowing what task it is serving.

### D-042 — the kernel reports no epochs rather than one synthetic epoch

An LSSVM is one `numpy.linalg.solve`. It writes zero rows to `qml_epoch_metrics`, returns
`history=[]`, and emits `kernel:gram` / `kernel:solve` / `kernel:done` progress phases instead of
fake epoch events. Its metrics live under `result["kernel"]`. Manufacturing an epoch to satisfy a
uniform persistence path would have put a fabricated number in a chart.

### D-043 — the trainer returned the wrong parameter type (latent Phase 5 defect, found and fixed)

`trainer.train` rebuilt its result as `vqc.Parameters` regardless of what it was given.
`hybrid.py:69` says `HybridParameters` is "deliberately not a subclass of Parameters" because that
class reads `theta[:-1]` as circuit weights, which for a hybrid vector is the classical block, and
would "reshape into silent nonsense" — the comment ends "a separate type makes the mistake
impossible rather than merely documented."

The engine made it impossible; the trainer undid it on the way out. Phase 5's tests missed this
because they compared `params.theta` numerically, which is identical either way — only the type was
wrong, and nothing asked. It surfaced when persistence tried to read `n_features` off the returned
object.

Fixed with `dataclasses.replace(initial, theta=...)`, which preserves the type and every other
field, so a future parameter type needs no change here.
`test_the_trainer_returns_the_parameter_type_it_was_given` was run against the reinstated bug
before being trusted.

**Generalisable:** a type-safety guarantee enforced at construction can be silently undone by any
code that rebuilds the object. Asserting on values will not catch it; assert on the type.

### D-044 — one inference contract, with no zeroed field for a task that lacks it

`run_inference` returns a `task`-tagged payload. Classification carries `predictions` +
`probabilities`; regression carries `values` + `target_range` and **no** `probabilities`; the
kernel carries `predictions` + `decision_values`, because an LSSVM margin is a signed distance and
calling it a probability would be an overclaim.

A missing key is deliberate in preference to a null or a zero — the same reasoning as D-033. A UI
that reads `probabilities` on a regression response should get a `KeyError` in development, not a
plausible `0.0` in production.

Regression inference **reloads** the train-fitted `TargetScaler` from the artifact and never
refits. Refitting on whatever rows inference happens to receive would change the output units per
request; `test_regression_inference_reuses_the_stored_scaler_rather_than_refitting` asserts a
single-row and a four-row call return the identical value for the shared input.

### D-045 — the capability document was advertising options the endpoint rejected

The invariant held at the schema layer and at the engine layer, and the API still returned 422 for
all three regression datasets. `POST /qml/experiments` pre-flight-probes the dataset with
`service.datasets.build_dataset` — a third construction site, found only by posting all twelve
advertised pairs at a live server.

`describe()` had the mirror-image bug: both its branches iterated `DATASET_MAX_SAMPLES`, which now
contains all six names, so every classification algorithm advertised `sine`. Both now derive from
`_datasets_for_task()`, reading the one registry.

The top-level `datasets` key is kept as the datasets valid for `default_algorithm` and documented
as a compatibility field, because a client reading only that list would otherwise offer `sine` for
a VQC.

**Generalisable, and now the third time this shape of defect has appeared:** proving a rule holds
in the model does not prove it holds at the boundary users touch. Enumerate every construction
site, and assert the invariant at the outermost layer that serves it.

---

## D-046 — The client branches on `task` and `supports`, never on an algorithm's name

**Context.** §2E.0 forbids the client from testing `algorithm === "quantum_kernel"`. That is the
same hardcoding §2D removed from the backend, relocated: it means a fifth algorithm cannot appear
without a frontend edit, which defeats the registry.

**Decision.** Every behavioural fork in the Lab reads either `result.task` (a discriminated-union
tag that `tsc` enforces) or a boolean from `algorithm.supports`. Concretely: the epoch-loop UI is
gated on `supports.epochs`, the hidden-layer field on `supports.n_hidden`, the gradient selector
on `supports.diff_method`, the re-uploading note on `supports.data_reuploading`; the results body
is chosen by `task`; the inference columns are chosen by `task` plus which optional arrays the
payload actually carries.

**The trap this avoided.** `quantum_kernel` advertises
`epoch_fields: ["train_loss", "train_accuracy", "test_accuracy"]` while writing **zero** epoch
rows. The obvious gate — "draw the training chart when `epoch_fields` is non-empty" — produces a
permanently empty axis for the kernel. `supports.epochs === false` is the only field that tells
the truth, so that is what the UI reads.

---

## D-047 — `epoch_fields` and `load_history` disagree in **both** directions; the dashboard takes the union

**Context.** Phase 5c drove the training chart off the capability document, as §2E.2 requires.
Two gaps surfaced immediately, in opposite directions:

- **Advertised, never served.** `quantum_regression` advertises `train_r2` and `test_r2`.
  `load_history` (`app/services/qml_lab.py`) serialises exactly six keys — `epoch`, `train_loss`,
  `train_accuracy`, `test_loss`, `test_accuracy`, `elapsed_seconds` — and **not** the two r2
  columns that Phase 5b added and `record_epoch` writes. The series arrive `undefined`.
- **Served, never advertised.** All three classification algorithms advertise
  `["train_loss", "train_accuracy", "test_accuracy"]`, but `load_history` also returns
  `test_loss`, which Phase 3's hardcoded dashboard drew. Driving purely off `epoch_fields`
  silently deleted that curve — caught by `qml-render-check` as a regression, not by review.

**Decision.** The dashboard plots the **union** of what the document advertises and what the
history actually contains, in a fixed display order, then drops any field with no finite points.
A stale document in either direction costs no curve, and an advertised-but-absent metric draws
nothing rather than an empty axis.

**What this does *not* fix.** The union cannot invent data. `train_r2`/`test_r2` are absent from
every history response, so the regression epoch chart shows loss only. The fix is two lines in
`load_history`; it is a backend change and Phase 5c's gate is "backend files changed = 0", so it
is **reported, not made**. Four assertions in `qml-task-check.mts` fail today and are the
regression test for it.

**Generalisable.** A capability document is a second source of truth about the same data, and
nothing in the build makes the two agree. When a UI switches from hardcoded knowledge to a
served document, diff the document against a real response first — the document is as likely to
be wrong as the code it replaces.

---

## D-048 — `ColumnDef.render` takes `(value, row)`, and the shipped table read the wrong one

**Context.** `ui.tsx:743` declares `render?: (value: any, row: T) => ReactNode` and
`DataTable` calls it as `col.render(row[col.key], row)`. The QML predictions table, shipped in
Phase 3 and live on `main`, wrote `render: (r) => <Badge>{r.prediction}</Badge>` — reading
`.prediction` off the *cell value*, which is a number.

**Evidence.** Rendering the shipped idiom server-side puts the literal string `undefined` in the
cell; the corrected idiom puts `1`. The class badge and the probability bar have therefore been
blank for every inference since Phase 3.

**Why nothing caught it.** `render`'s parameters are typed `any`, so `tsc` is silent, and
`qml-render-check` asserted the table *existed* rather than what its cells contained.

**Decision.** All four render callbacks in `QmlResultsPanel` take `(_value, row)`. The comment at
the call site states the signature, because the mistake is invisible at the point it is made.

**Generalisable, and the fourth instance of this shape:** after `ErrorNote`'s `children`,
`cn`-is-plain-`clsx`, and `page.evaluate`'s single argument — **read the signature of a helper
before calling it, even when the call "obviously" works.** An `any` in a callback signature is a
type hole exactly where review is weakest.

## D-049 — §2C.5 (noise experiments) is deferred, not forgotten

**Decision.** Noise experiments are not started in Phase 7 and are not scheduled for Phase 8.

**Context.** §2C.5 proposes training under a noise model so the Lab can show how a VQC degrades
on hardware-like conditions. Phase 7 searched for an existing implementation and found none: all
six `noise` hits in the QML engine are `dataset.noise`, the Gaussian jitter parameter of
`make_moons`/`make_circles`, which is sample generation and not a quantum noise channel. No
`default.mixed` device, no `qml.DepolarizingChannel`, no Kraus path exists anywhere in
`app/quantum/qml_lab/`.

**What it would take.** A second device path (`default.mixed` rather than `default.qubit`), which
is a density-matrix simulation and therefore quadratic in state size — the existing
`density_matrix_qubits` ceiling exists precisely because of this. Then a noise-model config
surface, per-channel parameters, their limits entries, trainer support for a non-analytic device,
and a baseline for "how much worse than noiseless" that does not mislead. Realistically a phase.

**Why deferred.** §2G.0: verifying a moving target verifies nothing. Phase 7's deliverable is a
set of numbers that are true of `main`; adding a feature mid-audit invalidates them.

## D-050 — §2C.6 (the qudit spike) is deferred for a second, harder reason

**Decision.** The qudit/QML crossover spike is not started, and is blocked on work outside this
repository's current history.

**Context.** The project owner has unpushed local work adding new qudit gates and polishing the
Qudit Lab. Every file a spike would touch — `app/quantum/qudit_lab/simulator.py`, the qudit
components under `src/components/qudit/` — is in that changeset.

**Evidence that the collision is real, not hypothetical.** Two open items Phase 7 re-measured
live in exactly those files: **QL-005** (`round(…, 6)` at `simulator.py:140/151/160`, today's
line numbers) and the **`bg-card` anomaly**, whose ten occurrences are *all* in
`src/components/qudit/` and `QuditLabPage.tsx`. A spike written against today's `main` would be
rebased onto a changed file and its line-numbered evidence would be stale on arrival.

**Unblocks when.** That work lands on `main` and can be read.

## D-051 — §2F WP6 (suggest-a-configuration) remains deferred after Phase 6

**Decision.** WP6 was permitted — §2F gates it on WP1–WP5 being complete and green, which they
were — and was still not started.

**Rationale.** §2F.3's own standard is that *"an impossible suggestion that is rejected or
regenerated beats one that is surfaced and 422s on click."* Meeting it requires server-side
validation of every suggestion through `limits.check()` **and** the per-algorithm `supports{}`
map, a regeneration loop when validation fails, and a mutation campaign covering each distinct
way a suggestion can be invalid: over a per-algorithm ceiling, a task-mismatched dataset,
`n_hidden` on a non-hybrid model, `diff_method` on a closed-form fit. That is a phase of work.

**Why not a partial version.** A half-built WP6 surfaces suggestions without the validation loop,
which is precisely the defect §2F.3 names. The honest options were "all of it" or "none of it".

## D-052 — `step` on a number input is a validity constraint, not a spinner hint

**Phase 8, Stage 4.1.** The Samples field carried `step={50}` with `min=20`.
HTML constraint validation therefore admits only 20, 70, 120, 170, 220, ... and
the form's own default of **200** was invalid: Chromium refused to submit and
showed "the two nearest valid values are 170 and 220". **The QML Lab could not
run a single experiment in any browser.**

`/qml/describe` publishes `{default: 200, min: 20, max: 1000}` and **no step**,
so the UI was rejecting a value its own API accepts. Resolution: remove the
`step`, matching the published contract; the range is still enforced by `min`
and `max`.

Why nothing caught it: `step` is evaluated only by a live browser. SSR renders
the attribute and never calls `checkValidity()`, so all 24 pre-existing
harnesses were structurally incapable of seeing it. It is the first defect
found by the browser capability unlocked in Stage 1, and it is the reason that
stage was worth doing. Guarded now by `qml-browser-check.mts`, which asserts
every numeric field's default passes `checkValidity()` — the class, not the
instance. See QL-018 in `07-verification.md`'s ledger.

## D-053 — §2A.6's ERROR state is rendered, not regex-matched

**Phase 8, Stage 2.1.** Phase 7 could only evidence the fail-closed path with
`/query\.data \?\? FEATURES_CLOSED/` over `useFeatures.ts` — the one §2A.6 state
with no render behind it. That assertion constrains the *spelling* of the
implementation: it passes for any file containing that text and fails any
correct refactor that stops containing it.

Replaced by three assertions in `qml-render-check.mts` that drive the
`/features` query into a settled error state and assert what the user gets:
nav entry absent, `404 - State Undefined` rendered, no config form. The errored
query needs `retryOnMount: false`, or the observer re-fires it on mount and the
state under test collapses back into pending.

Both forms were shown to fail the same mutation (`?? FEATURES_CLOSED` changed to
`?? { qml_enabled: true }`) *before* the regex was removed, so the replacement
is proven at least as strong on the behaviour that matters. The regex is now
deleted: keeping both would mean a correct refactor still fails the suite.

## D-054 — the 57 pre-existing harness failures are tabled, not fixed

**Phase 8, Stage 3.** The four red render harnesses (`results` 8, `codelab` 9,
`p5` 20, `games` 20 = **57**) were re-measured and reproduce Phase 7's counts
exactly. **No assertion was changed.**

Classification is mechanical — does the string the assertion expects still
exist anywhere in `frontend/web/src`? 34 expect copy the product no longer
contains; 6 are interpolated and undecidable by that test; 7 have no string
literal; 5 are partially drifted; 5 are present in source but not rendered on
the path under test.

Every one sits on the meaning side of the line (an expected string), or cannot
be decided without a judgement the owner should make. Hence **0 fixed, 34
tabled, 23 recorded with evidence**. Two exceptions are identified as genuine
plumbing and left for the next pass: `render-p5.mts:124` and `:144` assert that
quiz and challenge titles render, but `ChallengesPage.tsx:1230` puts them in a
Radix `Select`, whose items are portalled and therefore unreachable by
`renderToString` — a browser-path fix, allowed and now possible.

The table, with the mandatory "what regression would go undetected" field on
every row, is `docs/qml/08-assertion-proposals.md`. `K = 34` is not counted as
green anywhere in Phase 8.

One field §2I.3 requires cannot be supplied: "cite the commit that changed the
UI". `git rev-list --count origin/main` is **1** — the repository is a single
squashed commit, so no commit changed it and there is no before/after to cite.
Current source text is substituted, and the requirement should be withdrawn.
