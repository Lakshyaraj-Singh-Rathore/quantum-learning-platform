# 11 — Handoff to local: pull, and finish the testing

**Written for a cold start.** Whoever reads this — the owner, or an agent running
in Antigravity on `C:\Users\laksh\quantum-learning-platform` — has none of the
context from the sandbox where Phases 0 through 9A were built. Everything needed
is here or is pointed to from here.

**State at the time of writing: `main @ 4ac3e5f`, 665 tracked files.**

---

## A. Get the code

PowerShell v5. **`;` separates statements — `&&` is a parser error.**

```powershell
cd C:\Users\laksh\quantum-learning-platform
git fetch origin --prune
git status
git merge --ff-only origin/main
git rev-parse --short HEAD
git ls-files | Measure-Object -Line
```

**Want `4ac3e5f` (or later) and 665 lines.** If `git status` shows local changes,
stop and look at them before merging — do not discard work you have not read.

```powershell
cd C:\Users\laksh\quantum-learning-platform
git rev-parse --is-shallow-repository
git rev-list --count HEAD
```

**Want `false` and several hundred.** A count of 1 means a shallow clone, and then
*every historical conclusion is a measurement of the wrong thing.* This has
produced a formally-written request to withdraw a valid spec requirement, three
times. If it prints `true`: `git fetch --unshallow origin`.

Recovery tag, if anything ever goes wrong: **`qml-phase7-verified` @ `47fab49`**.
Use `tools/recover.sh`; do not write a replacement.

---

## B. Environment rules — these are all hard-won

| Rule | Why |
|---|---|
| **PowerShell v5: `;` not `&&`** | `&&` is a parser error, not a warning |
| **`cd X; command`, never `cd Xcommand`** | Silently runs in the wrong directory |
| **Git in PowerShell, NOT WSL, for the `C:\` checkout** | WSL `git status` at `/mnt/c/…` false-positives **~360 modified files** |
| **WSL only for `docker`, `nvidia-smi`, `curl`** | Those need the Linux side |
| **`docker compose` from PowerShell**, Docker Desktop **fully running** first | |
| **Always `-f docker-compose.yml -f docker-compose.gpu.yml`** | The GPU overlay is not optional; `--profile qml` additionally for the QML worker |
| **Never `npm install` inside `frontend/circuit_composer/frontend`** | Creates a second React copy and breaks `render:games`. The known fix is a **symlink** |
| **Never force-push** | Two commits this project nearly pushed carried **143,492 deletions**; only non-fast-forward rejection stopped them |
| **`main` is the source of truth** | Push with `git push origin HEAD:main`. Pre-push guard: `git merge-base --is-ancestor origin/main HEAD` |
| **`artifacts/` stays gitignored** | Durable evidence goes in `docs/qa/evidence/` |
| **`psutil` is deliberately NOT in `requirements.txt`** | Needed by `bench_qml.py`'s `total_ram_gib()`, which otherwise falls back to `/proc/meminfo` — absent on Windows — and records `null` |

Target hardware: **i5-13450HX / RTX 4050 / 16 GB / Windows.** The sandbox that
built this was a 2-core Xeon with 3.85 GiB, so **no timing number produced there
transfers**. §2B.1 of the governing doc is explicit that the sandbox is not the
target machine.

---

## C. What is already done

Phases **0 → 8D → 9A** are landed on `main`. The QML Lab is built, flag-gated,
and proven.

**All four QML algorithms have been trained live on target hardware** — the owner
ran them directly on 2026-10-22/23 and Phase 9A then drove them through the real
browser stack:

| Algorithm | Live result |
|---|---|
| `vqc` / moons | 85.33 % train, **92.00 % test**, F1 0.9231, 63.5 s |
| `hybrid_qnn` / moons | 89.33 % train, **90.00 % test**, F1 0.9091, **26 params = 9 + 16 + 1**, 79.0 s |
| `hybrid_qnn` / parameter-shift | identical result, **541.0 s = 6.85×**, corroborating Phase 4's quadratic law |
| `quantum_regression` / sine | **R² +0.7118**, MAE 0.3287, RMSE 0.3961 |
| `quantum_regression` / damped_cosine | **R² −0.1639 rendering as `−0.164`, sign intact** — proven in a browser |
| `quantum_kernel` / moons | **90.00 %** test, **0 epoch rows** by design, 1604 heatmap cells |

**Defect ledger:** QL-005, QL-017, QL-018, QL-019, QL-020 fixed; **QL-015 and
QL-016 closed by Phase 9A** (`a1429c5`). Every fix has a catching script wired
into `package.json` and was mutation-tested.

**Gates last measured (Phase 9A):** pytest **1304 passed / 5 skipped** · ruff
**118 on HEAD = 118 on base, 0 new** · typecheck **0** · tokens **0 new dead** ·
a11y **0 criticals** · goldens **190 + 804 + 3306 @ 1e-9** · migration single head
`j5e8f1a4b7c2` · **K = 24** harness failures, unchanged, still tabled.

**41 npm scripts.** The two newest are `qml:vision` (`qml-vision-check.mts`, 438
lines — all four algorithms live, four flag states rendered, three viewports,
**66 PASS / 0 FAIL**) and `viewport` (`viewport-check.mts`, 209 lines — the
QL-015/016 catches).

---

## D. What remains, in priority order

### D.1 — the three blocking manual rows. **These are the owner's, and they are the release gate.**

`docs/qml/09-owner-runbook.md` (429 lines) is a cold-executable procedure for
exactly these three. **Read it and follow it.** Order: **MT-004 → MT-001 → MT-010.**

| Row | What | Why only the owner can do it |
|---|---|---|
| **MT-004** | `bench_qml.py --full` on target hardware | The sandbox is not the target machine. This is the **only** source of the numbers behind `qml_task_soft_time_limit = 900` / `hard = 1200` |
| **MT-001** | Full round trip: submit → train → monitor → cancel → results → inference | Needs a **real broker and worker**. The sandbox has neither Redis nor Celery |
| **MT-010** | Gemini explanation grounding | Needs a **live `GEMINI_API_KEY`** and importable `google-generativeai` |

**MT-004 decision thresholds** — this is the one outcome that can reopen code work:

- `projected_seconds` for `8q / 4L / B32 / backprop / default.qubit` **under 900** ⇒ the timeouts stand.
- **900–1200** ⇒ the soft limit is wrong; tightening is allowed, **loosening needs owner sign-off** (§2B.4).
- **Over 1200** ⇒ the limits or `MAX_QUBITS` / `MAX_LAYERS` move. Owner's call.
- `execution_law_verified: false` ⇒ **a finding, not a flake. Stop and report.**

Expect **10–40 minutes**, not the 25 hours a naive extrapolation suggests — that
figure is a *projection* from a 2-core container and §2B.1 says so.

Install `psutil` into the bench venv first or `total_ram_gib` records `null`:

```powershell
cd C:\Users\laksh\quantum-learning-platform\backend
.\.venv-bench\Scripts\Activate.ps1
pip install psutil
$env:PYTHONPATH = "."
python scripts\bench_qml.py --quick
python scripts\bench_qml.py --full --json ..\artifacts\bench-full.json --md ..\artifacts\bench-full.md
```

**MT-002 closes as a side effect of MT-001 step 2. MT-003 is substantially
advanced by step 3. MT-007 is covered by none of the three** — it needs a
`data_reuploading` run configured deliberately, and nothing else exercises the
frequency budget.

### D.2 — `docs/qml/10-deep-manual-test-plan.md`: DT-01 … DT-40

The owner already ran **DT-02 through DT-16** at engine level. Phase 9A then
closed several in a browser. **What is still genuinely open:**

| ID | What | Status |
|---|---|---|
| **DT-01** | full `pytest -q` = 1304 / 5 | run it locally to confirm on your machine |
| **DT-09 … DT-11** | flag-off 404 vs flag-on 401; `/describe` doesn't advertise what the API rejects | **9A rendered all four flag states**, but DT-11's "advertise then violate" curl is not recorded |
| **DT-13 UI half** | `n_hidden` shown **only** for hybrid; form refuses `n_hidden > n_qubits` | **Closed by 9A / QL-020.** Verified `max` tracks `n_qubits` at 2→2, 5→5, 7→7 |
| **DT-15 negative half** | negative R² displayed **as negative** | **Closed by 9A.** API −0.1639 → rendered `−0.164` |
| **DT-16 UI half** | heatmap paints; closed-form shows, not an empty chart | 1604 cells confirmed; **the closed-form empty-state check is not recorded** |
| **DT-17 … DT-19** | sample cap, cancel mid-run, polling stops | cap closed by QL-019; **cancel and polling need the real worker** |
| **DT-20 … DT-30** | the 11 adversarial cases | **not run** |
| **DT-31 … DT-33** | = MT-004 | owner |
| **DT-34 … DT-40** | = MT-010 | owner |

⚠ **DT-13 trap, now fixed but worth knowing:** the form's default is
**`n_qubits = 2`** and the backend requires `n_hidden ≤ n_qubits`
(`hybrid.py:143`). Picking Hybrid QNN and typing `n_hidden = 3` without raising
qubits **422s every time** — and this is exactly why `hybrid_qnn` had never
completed a live run in eight phases. Set qubits to 4 first.

### D.3 — Finding DT-F1: do not overclaim the QNN

The head-to-head is **not** the favourable result, and it is recorded so nobody
re-derives it optimistically:

| | train | test |
|---|---|---|
| `vqc` (17 trainable) | 85.33 % | **92.00 %** |
| `hybrid_qnn` (26 trainable) | **89.33 %** | 90.00 % |

**+4.0 pp on train, −2.0 pp on test.** But the test split is 50 samples, so
2.0 pp is **exactly one sample** (46/50 vs 45/50) — statistically
indistinguishable at this size, with mild overfit consistent with the extra
capacity.

**Do not present the QNN as outperforming the VQC.** The defensible and genuinely
interesting claim: *a real jointly-differentiated hybrid whose classical block
provably receives true gradients from the circuit — and on a 200-sample toy set
that capacity does not yet pay for itself.* Separating mild overfit from noise
needs a larger test split or repeated seeds: a legitimate follow-up, not a
release blocker.

### D.4 — Phase 9B: the embedded panels and the 24 failures

**Not started.** Scope, in full, is in the chat prompt that accompanied this
handoff; the short version:

- **Noise Lab** (`/composer` → `bottomView === "noise"`, `ComposerPage.tsx:824`) and **Smart Composer** (`/composer` → `showSmartComposer`, `:584`) have **never had a vision pass** — `vision-qa-master-suite.mjs` targets `/qudit-lab` only. Noise Lab does have 5 SSR assertions in `render-new-features.mts:54,272,278-292`, so extend rather than duplicate.
- **The 24 remaining harness failures** — `render:p5` **19**, `render:codelab` **3**, `render:results` **2** — are one family: **Radix portals `renderToString` never produces.** The fix is to move those assertions into a browser, not to add product copy and not to relax them.
- Rebalance `vision-qa-master-suite.mjs`'s viewports: **37 screenshots at 1440×900 versus 1 each** at 1366×768, 390×844 and 768×1024.
- The OpenAPI route-count delta, the per-constant negative-path sweep, and the **CSS diff against pre-QML `46576c8`** — all three were deferred by 9A.

### D.5 — `bg-card` is **fixed**; twelve other dead tokens are not

**Corrected — an earlier revision of this document said `bg-card` was still open
at 10 uses. That was inherited from `07-verification.md` §7 rather than measured,
and it is wrong.** `git grep bg-card origin/main -- frontend/web/src` returns
**0**. It was fixed in **`b3f7435`** (Phase 8A, Stage 2.2) by switching to
`bg-raised`, and the whole class now has a ratchet guard in
`token-emit-check.mts`.

What *is* still open is the class, with twelve different members. These emit no
CSS at all, because `@theme` in `globals.css:4-42` is the only block that
generates utilities and none of these tokens are defined there:

```
bg-line-focus   bg-surface        border-slate-400   from-accent-hover
from-emerald-500  ring-line-focus   stroke-white      text-ink-1
text-ink-4      text-slate-200    to-sky-500         to-teal-500
```

They are **recorded rather than fixed because each needs a design decision about
which existing token replaces it** — that is a deliberate scope call, not an
oversight. The list is a ratchet exactly like the ruff count: **it may shrink,
never grow.** Adding one requires an explicit decision; removing one is always
welcome. Run `npm run tokens` and confirm **0 regressions against BASELINE**.

Note the guard also prints `FIXED <util>` when a baselined token starts emitting
— if you see that line, remove the token from `BASELINE` in the same commit.

**`07-verification.md:382` and `:391` still claim "10 uses / 6 files".** That is
the stale source this section originally inherited from, and it should be
corrected rather than read. See D.6.

### D.6 — documentation defects to fix

1. **`08-release.md:258-260` and `:291-292` are stale.** They still list QL-015, QL-016 and QL-017 as open. `07-verification.md` §7 correctly records QL-015 and QL-016 as **Closed in Phase 9A (`a1429c5`)**. The release doc is the one a reader trusts — reconcile it.
2. **`07-verification.md:382` and `:391` are stale on `bg-card`** — they claim 10 uses across 6 files; the real count on `main` is **0**, fixed in `b3f7435`. This section inherited that error into an earlier revision of *this* document, which is the clearest possible demonstration of why the standing rule is **measure, never inherit.**
3. **`MANUAL_TEST_REGISTER.md` was not updated by 9A.** MT-006's *regression* half is arguably closed by 9A's browser assertion that MAE/RMSE render in target units with a **signed** R². Verify, then record it — do not assume. Note also that rows MT-006/008/009 carry a `Status:` of `DEFERRED` while `:285-287` says **AUTOMATED**; that internal inconsistency should be resolved rather than left for the next reader to reconcile.
4. **The hackathon deck does not exist.** `docs/ppt/HACKATHON_DECK.md` is absent. `MARKETING_DECK_SOURCE.md` is **74 commits stale** (last touched `1501b12`, 2026-10-12) with **0 QML and 0 qudit mentions**, and claims "11 React SPA pages" against the actual **13 routes / 10 nav items across 4 sections**. Its header rule still binds: nothing claimed that isn't in shipped code; unbuilt = ROADMAP.

### D.7 — is Phase 9B the end? **No.** What "complete" means here

Phase 9B is the last **planned code phase**. It is not the end of the work, and
the three things below are not code.

**The model is already complete.** All four QML algorithms train live on target
hardware with exact gradients — `backprop` and `parameter-shift` agree to 1e-9,
the QNN's classical block is checked against a central finite difference through
the real circuit, and all 405 QML tests pass. Nothing in 9B changes that. **If
the question is "does the QML model work", the answer has been yes since Phase
5b and was proven live on 2026-10-23.**

What remains after 9B, and who owns it:

| # | Item | Owner | Can it reopen code work? |
|---|---|---|---|
| 1 | **MT-004** — `bench_qml.py --full` on target hardware | **owner** | **YES.** Over 1200 s means the limits or `MAX_QUBITS`/`MAX_LAYERS` move |
| 2 | **MT-001** — the full round trip through a real broker and worker | **owner** | Yes, if cancel lands as `failed` rather than `cancelled` |
| 3 | **MT-010** — Gemini explanation against a real key | **owner** | Yes, if a number appears in the prose that is not in the Measured table |
| 4 | **MT-002 / MT-003** | owner | No — they close as side effects of MT-001 steps 2 and 3 |
| 5 | **MT-007** — data-reuploading frequency budget | owner | Possibly — nothing exercises it today |
| 6 | **Twelve dead tokens** (§D.5) | agent + owner | No, but each needs a **design decision** about which token replaces it |
| 7 | **Documentation reconciliation** (§D.6.1–3) | agent | No |
| 8 | **The hackathon deck** (§D.6.4) — does not exist | agent + owner | No |
| 9 | **No CI** — `.github/workflows/` is empty | owner decision | No |
| 10 | **DT-F1 follow-up** — a larger test split or repeated seeds, to separate the QNN's mild overfit from noise | agent | No |
| 11 | **Deferred features, not defects**: §2C.5 noise experiments for QML, §2C.6 the qudit spike, `GET /codelab/ai-status`, the timeline-strip port, §2F WP6 suggest-a-config | owner decision | They are additions, not repairs |
| 12 | **MT-005** — the GPU/CUDA-Q path | **nobody** | Declared **NON-GOAL** by D-030, not skipped by failure |

**So the honest sequence is:** 9B closes the last code phase → the owner runs
MT-004 → MT-001 → MT-010 → **only then is it releasable**, and MT-004 is the one
step that can send work back to the code. The deck and the token decisions are
parallel to that, not after it.

**A claim of "all gates green" is forbidden in the release doc** (§2H.4) until
those three rows are actually run and recorded. The truthful closing statement is
the one `08-release.md` already makes: what is proven, what is provisional, and
what only the owner can prove.

---

## E. Docs to read, in this order

| Doc | Why |
|---|---|
| `docs/prompts/QML_LAB_VISION_AGENT.md` | **The governing deliverable, 22 sections.** Corrects the master prompt and wins on conflict. §2I.0 the browser launcher · §2I.1 the `bg-card` two-layer trap · §2I.3 the assertion rules · §8 evidence · §8A the testing split |
| `docs/qml/09-owner-runbook.md` | **The MT-004 → MT-001 → MT-010 procedure, cold-executable.** PowerShell v5 safe, `cd` on every step |
| `docs/qml/10-deep-manual-test-plan.md` | DT-01 … DT-40, plus the recorded live results and findings DT-F1/DT-F2 |
| `docs/qml/MANUAL_TEST_REGISTER.md` | The 10 MT rows and why each is or is not automatable |
| `docs/qml/DECISIONS.md` | **D-001 … D-063.** Read D-028, D-030, D-031, D-057…D-063 at minimum |
| `docs/qml/07-verification.md` | Phase 7's findings and the **defect ledger** in §7 |
| `docs/qml/08-release.md` | Release state — **but see D.6.1, it is stale on the ledger** |
| `docs/qml/08-assertion-proposals.md` | §4.0 the reclassification, §4.0a the adjudication |
| `docs/qa/VISION_QA_CAMPAIGN_REPORT.md` | Phase 8 and 9A reports |
| `docs/qml/04-benchmarks.md` | Phase 4's scaling laws, which MT-004 exists to confirm |

---

## F. Operational facts — do not re-derive these

Each of these cost a session to learn.

| Fact | Consequence |
|---|---|
| Form inputs use **`id=`, not `name=`** | `setNumber` by name is a **silent no-op** — every run used defaults and looked like it worked |
| The poll URL carries **`?after_epoch=`** | naive URL matching misses it |
| The API status enum is **`completed`**, never `succeeded` | a detector fails on vocabulary, not product |
| React Query retries **`count < 2`** (`main.tsx:15`) = 3 attempts | an error state is **mid-retry at 2.5 s**; wait ~6 s. This looked like a product defect and wasn't |
| `/qml/describe` without an algorithm returns **only classification datasets** | select the **model before the dataset**, always |
| Sonner's `<Toaster>` **mounts lazily** | the anchor reads `null` until a toast fires; `Run on Hardware/Sim` reliably raises one |
| Sonner takes **`position` per toast** (`ToastT.position`) | page-scoped toast fixes need not touch the shared anchor — see D-062 |
| Both labs render an honest **"designed for screens at least 900px wide… editing is not supported"** banner below 900 px | assert the banner at 390 rather than skipping the viewport |
| FastAPI routes mount at the **root** — `api_router = APIRouter()` has no prefix (`router.py:20`) | `curl` uses `/qml/describe`; the **browser** calls `/api/qml/describe` because the proxy strips `/api` (`vite.config.ts:20-22`, `:53-56`) |
| The detail endpoint returns metrics under **`result`**, not `metrics` | a wrong dict key reads as "all metrics are None" |
| **A mutant that fails to compile leaves `dist/` holding the FIXED bundle** | indistinguishable from a survivor. **Probe the served bundle for the mutated behaviour before believing any mutation result** |
| `vite preview` 403s the proxy host without `VITE_ALLOWED_HOSTS=` | Vite 6.4 has no CLI flag for it |
| Real gates are `npm run typecheck` / `npm run build` | both run `link-shared.mjs` first; bare `tsc` fabricates TS2307 |
| `pytest` must run from `backend/` with `PYTHONPATH=.` | |
| Route count 62 vs 58 | the difference is FastAPI's 4 doc routes |
| R² can be **negative** | −2.060, −3.671582235502192, −3.804, −0.1639 are all real measurements |

### The four documented mutant-survival families — all four are still live

1. **An asserted value not unique to the thing under test.** A grounding test stayed green with the evaluation metrics deleted, because the baseline block rendered the same `0.7778`.
2. **An absence indistinguishable from never-having-happened.** "0 polling requests after terminal" passes on a run that never started. A `"spinner"` regex matched the **Training tab label**.
3. **A conditional that cannot change its output.** `ResultsViews.tsx:263` shipped `noisy ? X : X` and survived on main for weeks. A QL-015 check read a container's own text nodes — always `""` — and passed with the defect fully reinstated.
4. **A test that passes because the thing it checks only evaluates in a browser.** QL-018: 405 tests green while the Lab could not submit anything anywhere. QL-016: `truncate` left the element *containing* the full string, so every DOM assertion passed while 6 of 9 titles were unreadable.

**Check your own harnesses for all four, not just the product.**

---

## G. Standing rules

- **Zero regressions.** No edits outside the allow-list (§4).
- **Real circuits, real gradients.** No mocked qnodes. Every gate proven with pasted output.
- **Reuse existing tokens and `components/ui.tsx` primitives.** No new UI or chart library.
- **Dark mode only.** No `dark:` variants, no theme toggle, no `tailwind.config.js`. Light mode was investigated once and explicitly rejected — do not reopen it.
- **Never weaken a legitimate test to reach green.** §2I.3 draws the line: an assertion's *meaning* may move from SSR to a browser; its expected value may not change without an explicit recorded ruling like D-060 or D-063.
- **Re-measure everything; never inherit a number.** A `0` from a command that did not run is the most dangerous number in a report — one was recorded here from a `ruff` invocation that died with `command not found` while stderr was discarded.
- **Engine-level is not product-level.** 27 unit tests and a green dispatch test still left `hybrid_qnn` never having completed a live run.
- **Every hand-found defect gets a catching script**, wired into `package.json`, **proven able to fail.** New IDs from **QL-021** upward.
- **Report what you could not verify**, in the same plain words used for `.apply()` and the live Gemini path.
- **D-061 is closed.** The four `GamesPage.tsx` labels (`Clear circuit`, `Reset to broken`, `Level complete`, `Measurement outcomes`) stay as they are. Do not touch them in either direction, and do not carry them forward as an open question.
- **Untouchable:** `requirements.txt`, every dependency pin, `celery`'s **8/15**, `qml_enabled`'s default (**False**), `ai/rag.py` (fence-aware chunker, has a regression test), the QML limit constants, `components/ui.tsx`'s shared toast anchor.

---

## H. Carry-forward constants

**Limits:** static **20** qubits · dynamic **15** · GPU **28** · `NOISE_MAX_QUBITS = 11` · preview cap **12** · `DENSITY_MATRIX_MAX_QUBITS = 6`.

**QML Lab:** `MAX_QUBITS = 8` · `MAX_LAYERS = 4` · `MAX_SAMPLES = 1000` · `MAX_EPOCHS = 100` · `MAX_BATCH_SIZE = 32` · `DEFAULT_KERNEL_SAMPLES = 150` · `MAX_HIDDEN_UNITS = 8` (but the binding rule is `n_hidden ≤ n_qubits`).

**Shape:** SPA **13 routes / 10 nav items / 4 sections** (Study · Build & Simulate · Practice · Insights) · **6 backends** · **6 Docker services + `qml-worker`** behind `profiles: ["qml"]` · **no CI** — `.github/workflows/` is empty.

**Physics:** backprop is **LINEAR** in circuit size, parameter-shift **QUADRATIC** (0.136→0.684 s vs 0.456→5.65 s across q=2→8; **6.85× confirmed live at q=4**). Predicted execution counts matched `qml.Tracker` in **all 45 full-grid cells**. Execution ratio **129×** versus wall-clock **12.6×** — execution count is not a timing model. `lightning.qubit` is 4.1× faster on parameter-shift but **cannot backprop**.

**Timeouts `900 / 1200` are PROVISIONAL.** Loosening needs owner sign-off (§2B.4). **MT-004 is the only source of truth for them.**

---

## I. First command sequence

```powershell
cd C:\Users\laksh\quantum-learning-platform
git fetch origin --prune ; git merge --ff-only origin/main ; git rev-parse --short HEAD
git rev-parse --is-shallow-repository
cd C:\Users\laksh\quantum-learning-platform\backend
.\.venv-bench\Scripts\Activate.ps1
$env:PYTHONPATH = "."
pytest -q
cd C:\Users\laksh\quantum-learning-platform\frontend\web
npm run typecheck
npm run tokens
```

**Want:** `4ac3e5f` or later · `false` · **1304 passed / 5 skipped** · typecheck **0** · tokens **0 dead**.

If those four hold, the checkout is sound and **MT-004 is next** —
`docs/qml/09-owner-runbook.md`, start to finish.
