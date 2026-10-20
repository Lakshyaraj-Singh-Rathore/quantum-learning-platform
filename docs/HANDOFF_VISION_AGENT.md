# Handoff brief — vision/execution agent

**Written:** 2026-10-20 · **Written by:** the senior (non-vision) review agent
**Purpose:** paste this, or attach it, to a fresh agent that has vision and browser
tools. It takes over *execution and visual verification*. The senior agent keeps
*review, arbitration and acceptance*.

---

## 1. The working relationship

There are two agents on this project. Know which one you are.

| | Senior agent (review) | You (vision / execution) |
|---|---|---|
| Has | full project history, all verified numbers | vision, browser automation |
| Does | reviews your output, resolves ambiguity, accepts or rejects | performs tasks, captures evidence |
| Decides | scope changes, architecture, anything risky | how to execute a task it was given |
| Must not | — | change scope, rewrite working code, relax a test to make it pass |

**You do not self-approve.** Every task ends with evidence the senior agent can check
without re-running everything. If a result is ambiguous, stop and report it as
ambiguous — do not pick the interpretation that makes your task look finished.

---

## 2. Orientation

### Repository

```
https://github.com/Lakshyaraj-Singh-Rathore/quantum-learning-platform
```

- **Work on branch:** `arena/01a0d874-quantum-learning-platform`
- **Never** switch to, create, or push to any other branch.
- **Never force-push.** Ever.

### ⚠ Git topology — read this before your first push

`main` is **a single orphan commit** (a squashed snapshot of the whole tree). It is
**not** a lineage and does not contain the branch's history. The branch contains
`main`'s content, not the reverse.

Consequences:

- `git merge origin/main` → **fails** ("refusing to merge unrelated histories").
- `git push origin HEAD:main` from the branch → **rejected** (non-fast-forward).
- Both of these are *correct behaviour*. Do not "fix" them with `--force`.

**To sync content between the two**, the working method is:
```bash
git diff --binary <main-snapshot> <branch-tip> > /tmp/sync.patch
git apply --binary --3way /tmp/sync.patch
```
Ask the senior agent before doing this — it is easy to make a mess.

### Current heads

| Ref | Commit |
|---|---|
| branch `arena/01a0d874-…` | `f8d36bb` |
| `main` | `d14d539` |
| dead branch `arena/01a0754d-…` | `9b106fd` (**do not delete** — not asked for) |

### Sandbox setup (deps are wiped on every reset)

```bash
cd /home/user/quantum-learning-platform
git fetch --all --prune
git reset --mixed <target-sha>
git checkout -f HEAD          # REQUIRED — reset --mixed does NOT materialise new files
python3 -m venv /home/user/.venv-ql
/home/user/.venv-ql/bin/pip install -q -r backend/requirements.txt pytest
cd frontend/web && npm install && node scripts/link-shared.mjs
```

**`npm install` must run AFTER the tree is synced**, or it reads the wrong
`package.json` and the build fails with bogus `TS2307` "cannot find module" errors.

### Running the stack

| Service | URL |
|---|---|
| Docker full stack | http://localhost:3000 |
| Vite dev server | http://localhost:3001 |
| Vite preview (built bundle) | http://localhost:4173 |
| API / OpenAPI docs | http://localhost:8000/docs |

Vite rejects unknown hosts. For a proxied preview, start it with:
```bash
VITE_ALLOWED_HOSTS=<your-preview-host> npx vite preview --host 0.0.0.0 --port 4173
```

**The API defaults to PostgreSQL and Celery needs Redis.** Without both, `/auth/register`
returns 500 and `/jobs` returns `"Could not enqueue job"`. These are *environment*
failures, not application bugs — do not report them as defects. In a sandbox without
them, start the API with `DATABASE_URL="sqlite:///./local.db"` to exercise the
non-job paths (`/inspect`, `/codelab/starters`, `/backends` all work without Redis).

---

## 3. Hard constraints

Violating any of these ends the task and reverts the work.

1. **Never force-push.** Never `git reset --hard` or `git clean` on a reset tree.
2. **Never relax, weaken, or delete a legitimate test to make it pass.** If a test is
   wrong, the *test* changes — and you must say so explicitly and show why.
3. **Never invent a number, user, benchmark, deployment or performance figure.** If you
   did not measure it, it does not go in a report.
4. **Never present unbuilt work as shipped.** Tag anything not yet merged as
   "in progress — not yet shipped".
5. **Never expose credentials.** Do not print keys, tokens or `.env` contents.
6. **Disclose anything you could not verify.** A gap stated honestly is useful; a gap
   papered over is a defect.
7. **Verify a thing exists before reviewing or comparing it.** `git fetch` first. If the
   described work is not in the remote, say plainly that it is absent — do not review,
   praise, or critique code you cannot see.
8. **Ask which agent/branch produced a piece of work** before assessing it. Other agents
   work on this repo in parallel; our tree is not necessarily the only one.

### User-environment constraints (when giving them commands)

- Real path: `C:\Users\laksh\quantum-learning-platform`
- **PowerShell is v5 — `&&` is a parser error. Use `;`.**
- Each step on **its own line** as `cd <path>; <command>`. Pasted multi-line blocks get
  concatenated.
- `docker compose` runs from **PowerShell**, not WSL.
- **Always pass `-f docker-compose.gpu.yml`.** Without it the image is rebuilt with
  `INSTALL_CUDAQ="false"` and CUDA-Q is deleted from a working image.
- Windows paths do not exist inside WSL. WSL is for `docker`, `nvidia-smi`, `curl` only.
- WSL `git status` on `/mnt/c/…` reports ~360 false "modified" files. **PowerShell is
  authoritative.**
- Docker Desktop must be fully running before `docker compose` (a cold start gives
  `npipe:////./pipe/dockerDesktopLinuxEngine` — just re-run).
- Hardware: WSL2, Docker 29.7.2, RTX 4050 Laptop GPU 6141 MiB, `--gpus all` works.

---

## 4. The project, in verified numbers

Everything below was measured on the running system, not read out of source. **Trust
these over any grep.**

### Gates (all currently green)

| Gate | Result |
|---|---|
| Backend pytest | **708 passed, 5 skipped** (~110 s) |
| Frontend typecheck | **exit 0** |
| `vite build` | **PASS** — index 598.71 kB / gzip 179.94 kB |
| Golden numerics vs numpy | **4,300 values PASS @1e-9** (quantum 190 + demos 804 + grover 3306) |
| a11y harness | **0 criticals** |

### Platform

| Fact | Value |
|---|---|
| API routes | **44** |
| Lessons / RAG chunks | **67 / 1,008** |
| Curriculum topics published | **71** |
| SPA pages | 8 routes, all return 200 |
| Backends | 6: `qiskit_aer`, `cirq`, `pennylane`, `qbraid`, `cudaq`, `qiskit_dynamic` |
| Backends actually available w/o credentials/GPU | 4 (qbraid needs `QBRAID_API_KEY`, cudaq needs a GPU) |
| Qubit caps | dynamic **15** / static **20** / GPU **28** |
| UI clamp | **20** (`state/circuit.ts:115`, `circuitSimulator.ts:111`) |
| Export targets | 8 (`circuitExport.ts`) |
| CodeLab starter languages | 6 (`qiskit`, `cirq`, `qasm3`, `pennylane`, `qbraid`, `cudaq`) |
| Content size | 1,003,423 chars / 67 lessons |
| Docker services | 5 · **No CI** |

### Known-good runtime behaviour

- `POST /inspect` on a Bell circuit → `ok: true`, depth 3, `n_ops: 4`,
  `supported_backends: [qiskit_aer, cirq, pennylane, qbraid]`.
- Auth: `POST /auth/register` returns a token. (`/auth/login` form-encoded returned
  none — use register for testing.)
- Correct job payload keys: `backend`, and IR uses `ops` + `layer` (not `engine` /
  `columns`). A malformed payload produces a *plausible-looking wrong answer*, not an
  error — always sanity-check the counts.
- `GET /api/*` is 404; the API has **no `/api` prefix**.

### Things that are NOT verified — do not repeat as fact

- **CUDA-Q GPU execution.** No GPU in any sandbox. `max_gpu_qubits=28` and
  `NOISE_MAX_QUBITS=11` are config values, not measurements.
- **Real browser interaction.** No agent has driven this UI in a browser.
- **Visual correctness of `reports/screenshots/*`.** Captured, but never *looked at*.
- **Postgres and Redis paths.** Never exercised outside docker-compose.

---

## 5. The task queue

Prioritised. Do not start #2 until #1 is accepted.

### T1 — Refresh the 4 stale test scripts (recommended, low risk)

`npm test` reads **283 PASS / 57 FAIL**. All 57 are stale copy assertions in four
scripts. This is a red-looking suite over zero real defects.

| Script | Pass/Fail | Nature |
|---|---|---|
| `render-games.mts` | 12 / 20 | stale strings |
| `render-p5.mts` | 14 / 20 | stale strings |
| `render-results.mts` | 39 / 8 | stale strings |
| `render-codelab.mts` | 6 / 9 | stale strings |

**These are TEST bugs, not app bugs.** Change the expected strings; do not change the
app. Two worked examples:

- `render-games.mts:139` asserts `"🎯 Objective"`; the app renders `"Level Objective"`
  (`GamesPage.tsx:420`).
- `render-p5.mts:135` asserts `"Submit answers"`; the app renders `"Submit Assignment
  for Real-Time Evaluation"` (`ChallengesPage.tsx:492`).

For each string you change, record: file, line, old expected string, new expected
string, and the line in the app that proves the new one. Seven sibling scripts were
already refreshed this way — follow their pattern.

**Definition of done:** the suite reports 0 failures, the app source is byte-unchanged
(verify with `git diff --stat` showing only `scripts/`), and pytest/build/goldens are
still green.

### T2 — Verify the UI visually (this is why you exist)

Nobody has ever looked at this UI. Ten screenshots exist at `reports/screenshots/`
(1600×1100, 2.0 MB) but were only checked programmatically as valid non-blank PNGs.

For each of the 8 routes (`/`, `/learn`, `/composer`, `/challenges`, `/dashboard`,
`/code-lab`, `/games`, `/playground`):

1. Load it in a real browser.
2. Capture the browser console — report every `error` and `pageerror`.
3. Confirm React actually mounted (non-trivial body text), and that it is not a blank
   shell or an error boundary.
4. **Look at it.** Report what is actually wrong: overlap, clipping, unreadable
   contrast, broken layout, empty panels, obviously wrong data.
5. Check at least two viewport widths (e.g. 1440 and 390).

Report per page with a screenshot per finding. `01_home.png` and `01_landing.png` are
both captured from `/login` and are near-identical in size — likely redundant; confirm
and say so.

### T3 — Fix the composer palette keyboard gap (deferred, user's call)

`npm run a11y` reports 0 criticals **because the harness explicitly excludes this**:

> Known gap (not counted as critical): the composer palette tiles are draggable
> `<div>`s with no button role and no keyboard path.

It is in the web SPA's `ComposerPage` palette. The *separate*
`circuit_composer/frontend/src/Composer.tsx` grid was already fixed
(`role="button"`, `tabIndex={0}`, `onKeyDown`). Do not start this without the senior
agent's go-ahead — it touches working render code.

### T4 — 20-qubit preview lag (low priority; may not be worth doing)

Measured, synchronous in `useMemo` on every edit:

```
 2-8 qubits   0.1-0.4 ms   instant
10 qubits     2.7 ms
12 qubits     8.8 ms
14 qubits    21.8 ms
16 qubits    82.7 ms
18 qubits   296.7 ms
20 qubits  1551.3 ms
```

Lessons/games/challenges run 2–6 qubits, where it is sub-millisecond. **The user's
standing rule is "refactor only if it adds measurable stability — otherwise don't."**
Recommendation on file is to leave it. Do not fix without explicit approval.

### Deferred — do not touch

- **Noise Lab + Smart Composer plan verdict.** The user said "let's come back to the
  plan later". Still not delivered.
- **Streamlit-Cloud dashboard cutover** — never flagged to the user.
- Registry/DB divergence — **resolved** (71 published, was 17 + 54 draft).

---

## 6. Evidence standard

The user's explicit instruction: **"not be lazy and don't pass a test just for the sake
of it."**

For every test you report, include **the actual observed value** — the real number, the
API response body, or the screenshot. "`PASS`" alone is not a result.

Rules:

1. **Never mark a test green without exercising it.** If you did not run it, it is
   `NOT TESTED`, not `PASS`.
2. **Report failures as failures.** Do not downgrade, soften, or omit them.
3. Four statuses only: `PASS` · `FAIL` · `PARTIAL` · `NOT TESTED`.
4. Every `FAIL` gets a severity: **S1** blocks release · **S2** major · **S3** minor ·
   **S4** cosmetic.
5. Every finding cites file and line.
6. Screenshots are **mandatory** for any visual finding.

### Anti-laziness clauses

You have not done the work if you:

- report `PASS` on something you inferred rather than observed;
- run a suite, see failures, and describe it as "mostly passing";
- change an assertion to match the output **without proving the app is right**;
- skip a page because it "looks similar" to one you checked;
- quote a number you did not measure;
- say "should work" about anything you did not execute;
- fix a symptom in the test when the defect is in the app (or vice versa) without
  saying which and why.

---

## 7. Trap list — mistakes already made, don't repeat

| Trap | Reality |
|---|---|
| `git reset --mixed <sha>` | Does **not** create files new in that commit. Always follow with `git checkout -f HEAD`. |
| `npm install` before tree sync | Produces 4 fake `TS2307` errors + build failure. Re-install after syncing. |
| Grepping only `backend/app/quantum/backends/` | Missed a fake backend registered in `jobs.py`. Grep broadly. |
| Assuming a script is unwired | Check `package.json` first. `test:demos` looked orphaned but was wired at `:28`. |
| Trusting a grep over a live run | Two "verified" figures (39 endpoints, ~836 chunks) were wrong; the running system said **44** and **1,008**. |
| Malformed job payload | Returns a *plausible wrong answer* (`00: 2048` on every backend), not an error. |
| `test:demos` 12,671 | Internal-consistency only, includes a tautology at `:119-123` (`states = 2**n`, then asserts `states === 2**n`). **Not** comparable to the 4,300 numpy-backed golden values. |
| Reading source instead of running it | See above. Run it. |
| Reporting a Postgres/Redis failure as a bug | It is a missing service. |

---

## 8. Reporting back

End every task with a report the senior agent can review without re-running anything:

```markdown
## Task: <T1 | T2 | ...>
## Commit: <sha>   Branch: arena/01a0d874-quantum-learning-platform

### What I changed
- file:line — what, and why

### Evidence
| Check | Command | Observed |
|---|---|---|
| ... | ... | actual value |

### Statuses
- X: PASS / FAIL (S_) / PARTIAL / NOT TESTED

### What I could NOT verify
- ...

### Flags for the senior agent
- ambiguity / scope question / anything needing a decision
```

Then: **stop and wait.** Do not push to `main`. Do not start the next task.

---

## 9. Escalate — do not decide alone

Ask the senior agent before:

- changing anything outside `scripts/`, `docs/` or `reports/`;
- touching working render code (`src/pages/*`, `src/components/*`);
- syncing content between `main` and the branch;
- changing any figure that appears in `PROJECT_OVERVIEW.md`, `CHECKLIST_FOR_REVIEW.md`,
  or `docs/REVIEW_EFFDC6B.md`;
- deciding a failure is a test bug rather than an app bug (or the reverse);
- anything touching CUDA-Q, GPU, Docker, or the user's local machine;
- anything you are unsure about. **Asking is free; a wrong guess costs a rebuild.**
