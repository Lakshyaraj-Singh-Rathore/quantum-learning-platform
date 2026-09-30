# QuantumLearn UI Redesign — Detailed Plan

Replacing the Streamlit front end with a minimalist, ChatGPT-grade React web
app. Decisions locked with the owner (2026-09-30):

| Decision | Choice |
| --- | --- |
| Fidelity of the new UI | **Full React rewrite** — Streamlit is retired at the end, not themed |
| Day-one scope | **All 7 pages + auth + instructor view** (feature-complete, big-bang cutover) |
| Theme | **Dark-first** (ChatGPT night), light mode behind a toggle |
| Transition | **Both stacks run in parallel** on separate ports until parity, then Streamlit goes away |

Standing constraints inherited from how this platform is operated:

* Docker Compose is the primary workflow; `make up` stays the one command.
* Data lives in the `pgdata` volume — this redesign touches **zero** database
  schema and **zero** Celery task semantics.
* The "no fake demonstrations" rule applies to the UI too: every pixel shows
  numbers the API returned; nothing is embellished or stubbed client-side.
* Bind-mount workflow: frontend code changes must survive `git pull` +
  container restart, no image rebuild during development.

---

## 1. What exists today (verified inventory)

```
frontend/
├── Home.py                     # auth gate + landing          98 lines
├── pages/                                                ~2,089 lines total
│   ├── 1_Learn.py              # lessons + inline demos
│   ├── 2_Composer.py           # canvas + run panel + result tabs + noise
│   ├── 3_Challenges.py         # graded circuits vs target distributions
│   ├── 4_Dashboard.py          # learner progress + instructor overview
│   ├── 5_Code_Lab.py           # sandboxed code editor (6 frameworks)
│   ├── 6_Games.py              # gate golf, reversal, etc.
│   └── 7_Playground.py         # free-form experiments
├── lib/
│   ├── api_client.py           # requests + bearer token wrapper
│   ├── auth.py / bootstrap.py  # session plumbing, sys.path shim
│   ├── viz.py                  # ~1,236 lines: ALL result views (plotly)
│   ├── composer.py             # canvas payload → CircuitIR (+param exprs)
│   ├── code_checks.py          # static diagnostics for Code Lab
│   ├── grover_lab.py, grover_ui.py, lesson_demos.py, playground.py,
│   └── timeline_strip.py       # in-process teaching widgets (numpy math)
├── circuit_composer/frontend/  # React 18 + Vite + TS bundle (drag-drop canvas)
├── live_bloch/frontend/        # React 18 + Vite + TS bundle (animated demo)
└── tests/                      # 26 pytest files guarding UI intent

backend/app/api/                # 35 REST endpoints, JWT bearer, CORS middleware
                                # already present and configurable via WEB_ORIGINS
```

Key facts that shape the plan:

1. **The two hardest components are already React.** `circuit_composer` and
   `live_bloch` are plain Vite/React/TS apps mounted through
   `streamlit.components.v1`. In the new app they become ordinary React
   packages — no rewrite, just a different mount point and props wiring.
2. **All quantum execution already goes through REST.** Pages never call the
   simulation engines; they POST `/jobs` and poll. The in-process Python
   (`from app.quantum.ir import CircuitIR`, numpy in `grover_lab`) is
   *translation and validation*, not execution — small, pure logic that ports
   to TypeScript with the backend kept as the authority via `POST /inspect`.
3. **`viz.py` is the real body of work.** ~1,200 lines of plotly chart
   builders and table renderers that must be re-expressed in React. The
   numbers come from the job result JSON unchanged; only the drawing moves.

---

## 2. Target architecture

```
Browser :3000 ── nginx (static SPA + /api proxy)
                    │
                    ▼
              FastAPI :8000 ──► Postgres / Redis / Celery worker(s)
                                      │
                                      └─ engines: Aer · Cirq · PennyLane · CUDA-Q(GPU)
```

* **App**: Vite + React 18 + TypeScript SPA (no SSR). `react-router` v6,
  `@tanstack/react-query` for server state, `zustand` for the three pieces of
  genuine client state (session, theme, composer draft).
  *Why not Next.js*: this is a logged-in tool, not a content site — static
  export costs nothing at runtime, boots instantly on a laptop, and keeps
  the compose stack container-light.
* **New compose service** `web`: `nginx:alpine` serving the built bundle,
  `/api/*` proxied to `api:8000`. Same-origin in production → the CORS
  setting only matters for `vite dev`. GPU mode never touches `web`.
* **Monorepo layout** (npm workspaces):

```
frontend/web/
├── package.json                 # workspace root
├── packages/
│   ├── circuit-composer/        # moved from frontend/circuit_composer/frontend
│   └── live-bloch/              # moved from frontend/live_bloch/frontend
├── src/
│   ├── app/                     # router, providers, shell (sidebar/topbar)
│   ├── features/
│   │   ├── auth/  composer/  results/  learn/  challenges/
│   │   ├── dashboard/  codelab/  games/  playground/  grover/
│   ├── components/              # shared primitives (shadcn/ui generated)
│   ├── lib/ir/                  # TS port of composer translation + param eval
│   └── api/                     # generated client (see §5)
└── nginx.conf                   # SPA fallback + /api proxy
```

* Dev flow: `make web-dev` → Vite server on :3001 with proxy to :8000,
  HMR, bind-mounted like everything else. Prod flow: `make web-build` inside
  the workspace (or CI) → `nginx` serves `dist/`.

---

## 3. Design system — "quiet professional, dark-first"

The ChatGPT look is not a component library, it is **restraint**: one
background tone, hairline borders, generous whitespace, a single accent,
text hierarchy doing the work that color would. Tokens:

| Token | Dark (default) | Light |
| --- | --- | --- |
| `--bg` | `#0d0d0f` (near-black, 1 step above pure) | `#fafafa` |
| `--bg-raised` | `#17171a` (cards, inputs, popovers) | `#ffffff` |
| `--bg-hover` | `#1f1f23` | `#f0f0f1` |
| `--border` | `#26262b` (hairline, 1px) | `#e4e4e7` |
| `--text` | `#ececee` | `#1a1a1a` |
| `--text-muted` | `#9a9aa3` | `#6b6b74` |
| `--accent` | `#10a37f`-adjacent teal (keep current TEAL as brand) | same, −10% luminance |
| `--danger` / `--warn` | coral / amber, desaturated to sit calmly on dark | same hues, darker |

Rules:

* **Typography**: system sans (`ui-sans-serif, Inter` fallback), 15px body,
  13px meta; page titles 20–22px semibold — no hero text anywhere.
* **Layout**: fixed 240px left rail (icon-only at <1200px, as in ChatGPT),
  top bar 56px with page name + backend badge + user menu; content column
  max-width 1120px (1280px for the Composer's split layout).
* **Surfaces**: `bg-raised` + 1px border + 12px radius; **no drop shadows**;
  dividers instead of nested cards; one level of elevation max (popovers).
* **Controls**: 36px height, 13–14px label; sliders and toggles styled once
  in the primitives layer (Radix under shadcn/ui) so every page inherits.
* **Motion**: 150ms ease-out on state changes, nothing else; `prefers-reduced-motion` respected globally.
* **Charts**: single plotly dark template registered once (`paper_bgcolor`
  transparent, hairline gridlines, muted axis text, same teal); tooltips
  enabled, modebar removed. Light mode re-templates automatically via CSS
  variable read at theme switch.
* **The result views are kept pixel-faithful in meaning** (histogram,
  probability table, Born-vs-shots, statevector ket table, phase disk,
  Q-sphere, Bloch, density matrix, timeline strip, metric gauges, diagram,
  ideal-vs-noisy) — restyled, never reinterpreted.
* Accessibility floor: keyboard-navigable everything (Radix baseline),
  visible 2px focus ring in accent, AA contrast for muted text, `aria-label`
  on gauges with the value as text, form errors announced.

Tech: **Tailwind CSS v4 + shadcn/ui** (generated into `components/`, no
dependency lock-in) + **Radix primitives** + `lucide-react` icons
(thin-stroke, matches the aesthetic) + `plotly.js-dist-min` (lazy-loaded
chunk) + CodeMirror 6 for the Code Lab editor (replaces
`st.code_editor`; grammar packs for Python and OpenQASM; keeps the current
read-only result rendering trivially).

---

## 4. Page-by-page spec (element → destination → acceptance)

### 0. Shell + auth (replaces `Home.py`, `lib/auth.py`)
| Current element | New destination |
| --- | --- |
| login/register forms | centered card on `bg`, email/password, inline errors from API |
| session token in `st.session_state` | `localStorage` + axios/fetch wrapper; 401 → redirect to `/login`, return-to preserved |
| "bootstrap admin" convenience | read from `GET /me`; the seeding itself stays in the API container untouched |
| nav | left rail: Learn · Composer · Challenges · Dashboard · Code Lab · Games · Playground; bottom: user menu (name, role, theme toggle, sign out) |
| backend badge | top-right pill `GET /backends` (available/greyed-with-reason, incl. the CUDA-Q GPU string) |

*Acceptance:* register → login → deep-link refresh all work on hard refresh;
token expiry returns to login with a one-line notice, no lost-form bug
(form state preserved in memory like ChatGPT does).

### 1. Composer (largest page: `2_Composer.py` 498 lines + `lib/composer.py`)
* **Canvas**: the existing React island, embedded as a component; props
  `{initialIr, onChange, onInvalid}` instead of postMessage round-trip
  through Streamlit. Its 15 base gates + 11 controlled aliases, qubit/clbit
  management, grid, context menu: all keep working — this is the same code.
* **Translation layer** (`lib/composer.py` → `lib/ir/`): payload→IR,
  `GATE_PARAMS` table and `eval_param_expr` (the parameter-expression
  mini-language: `pi/2`, `theta*2`) ported to TS. Parity is guaranteed by
  porting the backend-side translation tests as table-driven vitest cases
  and by validating every build through `POST /inspect` (already exists) —
  the server is still the authority, so a client bug can never produce a
  silently-wrong circuit; the UI shows the inspector verdict.
* **Run panel**: shots slider, seed, backend select (with the greyed-out
  reasons), precision dropdown for CUDA-Q, the noise-model expander with all
  six sliders + T2>2T1 live warning + both engine caveats (Aer / CUDA-Q
  density-matrix ≤11 qubits) — copy reused verbatim from the current page.
* **Results**: the full tab strip rebuilt on the result JSON: histogram,
  probabilities, Born vs shots, statevector, phase disk, Q-sphere, Bloch,
  density matrix (≤5q view rule kept), ideal vs noisy (needs
  `metadata.ideal_counts`), metric gauges (entropy/concurrence/fidelity/
  purity/TV/leakage with the CUDA-Q omission rule handled), circuit diagram
  (render `qasm3` via the existing export endpoint + a lightweight QASM
  viewer, or the diagram image the API returns today — whichever
  `viz.py` uses; parity check against `test_bloch_accuracy`-style numeric
  tests), warnings stack, timeline strip (port of `timeline_strip.py`,
  same step-through semantics).
* **Job lifecycle**: submit → optimistic "Queued" row → react-query polls
  `/jobs/{id}` with 400ms→1.5s backoff → on completion the result is cached
  by `run_hash` exactly like `test_api_caching` guards today; stale-result
  guard (`test_stale_results`) re-ported as: results are keyed to the
  request hash, never to the last-completed job.
* Circuit save/load/delete: `/circuits` CRUD via a compact list popover.
* *Acceptance:* the 6 Composer-adjacent streamlit tests' intents re-express
  as e2e specs and pass; agreement runs (Bell/GHZ on all engines) show
  identical numbers to the Streamlit UI for the same seed/shots.

### 2. Learn (`1_Learn.py`, `lesson_demos.py`, `grover_lab/ui`, live_bloch)
* Lesson list + reader column (max-width 720px like ChatGPT prose), markdown
  rendered from `/lessons/{slug}` content; TOC right rail on wide screens.
* **Interactive demos** (the 13 lessons' embedded widgets): each demo becomes
  a React component with the same controls → same math. Two rules:
  (a) anything the platform already runs on the API (a demo that "runs a
  circuit") calls `/jobs`; (b) the pure-numpy teaching math (`grover_lab`:
  amplitude-by-iteration curves, the 1/64 → 99.66% story) ports to TS —
  it is display math, not simulation, and the ported numbers are pinned by
  golden tests generated from the current implementation before the old UI
  freezes. Live-bloch demo: the existing island, mounted inline.
* Quizzes: `GET /quizzes`, submit via existing endpoint, result panel same
  pass/fail copy.
* *Acceptance:* every lesson's demo state set produces byte-identical
  numbers to golden fixtures recorded from today's build.

### 3. Challenges (`3_Challenges.py`)
* Challenge list cards (slug, target description, difficulty, my-best chip);
  detail page = read-only target distribution plot + "Open in Composer with
  this circuit" deep link + submission history table; grading runs entirely
  server-side (unchanged); the pass/fail explanation text is ported verbatim
  including the shot-noise tolerance note. `GET /recommendations` shown as a
  one-line "suggested next" under the nav header.

### 4. Dashboard (`4_Dashboard.py`, `/dashboard`, instructor endpoints)
* Learner view: stat row (runs, circuits, pass rate), recent jobs table with
  backend badges, progress bars per lesson, "run the noise comparison" style
  nudge cards the current page shows. Instructor view (`/instructor`,
  `/students/{id}`): class table, per-student drill-in drawer reusing the
  learner components. Same data, same role gating as today.

### 5. Code Lab (`5_Code_Lab.py` 295 lines + `code_checks.py`)
* Layout: framework tabs (Qiskit · Cirq · PennyLane · OpenQASM 3 · qBraid ·
  **CUDA-Q** — the availability-filtered list comes from `GET
  /codelab/starters` unchanged), CodeMirror editor left / Build+Run actions,
  diagnostics gutter.
* **Static diagnostics** (`code_checks.py`: syntax, blocked imports, missing
  `circuit`, qbraid.runtime warning): exposed via **one new endpoint
  `POST /codelab/check`** rather than a TS reimplementation — it is AST
  Python; the Python checker stays the single source of truth (also covers
  QASM checks). Debounced 400ms in the editor.
* Build → existing `/codelab/build` (returns IR, QASM3, stdout); Run →
  normal `/jobs` flow, so all result components from the Composer page are
  reused here for free; AI draft box (Gemini path) keeps its exact copy
  including the "AI cannot execute" note and the framework rules now
  covering CUDA-Q.

### 6. Games (`6_Games.py`) & 7. Playground (`7_Playground.py`)
* Games: level cards + play field; scoring/validation semantics unchanged
  (the `CircuitIR` uses there are validation-only → same `/inspect`
  authority as Composer). `GET /games` unchanged.
* Playground: gate table + parameter sliders + instant state preview; the
  current in-process numpy previews that don't hit the API are ported to TS
  with golden-number tests (identical policy to Learn demos).

---

## 5. Backend delta (the entire list — small on purpose)

1. `POST /codelab/check` — wraps existing `frontend/lib/code_checks.py`,
   moved into `app/services/` so both the API and tests own it. ~40 lines.
2. Serve-time: none. CORS origins env knob already exists
   (`WEB_ORIGINS` for dev :3001).
3. Optional convenience, same PR as cutover: `GET /meta` returning
   app version + feature flags (frameworks list already covers the rest).
4. **Explicitly not changing:** auth/JWT, jobs/Celery, engines, noise
   semantics, CUDA-Q paths, DB schema, run-hash caching, sandbox. The UI
   rewrite must keep `backend/tests` green with zero test edits; any PR
   that touches a backend file beyond the three above is a plan violation.

API client: hand-written thin `fetch` wrapper (~150 lines, mirrors today's
`api_client.py`) — no codegen dependency, every endpoint response already
typed by FastAPI: export `openapi.json` → `openapi-typescript` **in dev
only**, checked-in types file, regenerated manually. Zero build fragility,
types still enforced.

---

## 6. Testing & parity strategy

* **Keep**: all backend pytest (504 green is the contract), the two island
  packages' own build checks.
* **New app**: vitest for `lib/ir` (golden table ported from
  `test_composer_layout`/`test_clbit_shrink`/`test_cnot_palette` intents),
  component tests for results tabs against recorded result JSON fixtures
  (fixture generator committed alongside — a one-off script that runs today's
  `viz.py` data paths and snapshots the JSON), Playwright e2e per page
  (login, composer→run→tabs, codelab build/run, challenge submit, dashboard
  roles) against `make up` with a seeded test account.
* **Parity gate before cutover** — a checklist where every row of the
  current UI has a recorded behavior + its new-UI test id (the 26
  `frontend/tests/test_*.py` files are each annotated with their new-UI
  equivalent in §4 of this doc as phases land; `test_no_nested_expanders`,
  `test_ui_integrity` etc. become design-lint rules translated to
  the new conventions, e.g. "no modal-in-card" → stylelint rule).
* Streamlit stays **frozen** (bugfixes only, owner-approved) from P0 onward
  so the parity target stops moving.

---

## 7. Operations, deployment, ports

| Service | Port | Notes |
| --- | --- | --- |
| web (nginx static SPA + /api proxy) | **3000** → new primary URL | GPU-agnostic container, ~10 MB image |
| streamlit (frozen) | 8501 | removed at P8 |
| api | 8000 | unchanged |

* `make up` unchanged (compose adds `web` service + `docker-compose.gpu.yml`
  untouched — GPU override still only concerns api/worker).
* `make web-dev` (vite HMR :3001, proxy :8000) / `make web-build` for the
  bundle. node:22 used via Docker on the laptop (no host node install).
* First-run experience after cutover: `http://localhost:3000`.
* Rollback = one compose flag: keep the frozen `streamlit` service in the
  file for one release after cutover, so `make up STREAMLIT=keep` style
  re-entry costs nothing; P9 deletes it.

---

## 8. Phases (each ends demoable; solo-owner pace ≈ 3–6 focused sessions each)

| P | Deliverable | Exit gate |
| --- | --- | --- |
| **P0** | Scaffold: workspace, router, theme tokens, shadcn primitives, nginx service, compose wiring, auth+shell+nav | login/register/me flow works in browser at :3000 |
| **P1** | **Composer**: canvas island mount, TS translation + `/inspect` authority, run panel (backends/shots/seed/precision/noise), jobs polling, result cache | Bell pair on Aer **and** CUDA-Q: same numbers as Streamlit UI |
| **P2** | **Results suite**: all tabs incl. density matrix, Bloch, phase disk, Q-sphere, timeline strip, metric gauges, ideal-vs-noisy, warnings | every fixture-driven chart test green; agreement-battery circuits visually diffed |
| **P3** | **Code Lab**: tabs from `/codelab/starters`, CodeMirror, `/codelab/check`, build/run, AI draft box | all six frameworks' starters build; sandbox stdout shown verbatim |
| **P4** | **Learn**: reader, quizzes, live-bloch island, ported demo math w/ golden tests, Grover lab | 13 lessons + demos pass golden-number fixtures |
| **P5** | **Challenges + Dashboard** (learner & instructor) | grading copy, recommendations, role gating match current text exactly |
| **P6** | **Games + Playground** | level flows + previews golden-tested |
| **P7** | Polish: light mode + toggle, keyboard shortcuts (Ctrl-K style command palette optional), empty/error/loading states audit, mobile-width behavior (>=900px supported, below: read-only warning banner), Lighthouse/axe pass | a11y audit 0 criticals; theme switch re-templates charts |
| **P8** | **Cutover**: web becomes default landing; docs (README screenshots, CUDAQ_SETUP wording) updated; Streamlit marked legacy in compose | owner sign-off on parity checklist |
| **P9** | Removal: streamlit service, pages/lib code, its requirements & tests deleted; plan doc updated with final architecture | backend suite still 504 green; `make up` = 4 services |

Dependency: P1→P2 is the spine; P3–P6 can interleave after P1 once the
results suite exists (they reuse it). Suggested real-world order for demo
value: P0 → P1 → P3 (Code Lab is the most-loved page) → P2 → rest.

---

## 9. Risks & mitigations

| Risk | Mitigation |
| --- | --- |
| TS translation drifts from Python IR rules | `/inspect` is the authority — the UI can only ever submit what the server accepts; golden test tables ported pre-freeze |
| viz reimplementation changes numbers accidentally | charts consume recorded result JSON fixtures; numeric assertions (ket ordering, bit-order "q0 rightmost", 5-qubit dm cap, ≤20 stateview rule) re-asserted in vitest, not eyeballed |
| plotly bundle weight on a laptop | lazy route-chunk (~1MB gz) loaded on results; island charts use the same bundle |
| Streamlit drift while frozen breaks parity checklist | freeze policy in P0 exit note; any Streamlit change needs an owner yes (only the sandbox-reset class of breakage qualifies) |
| token/localStorage XSS posture | same threat model as today (no secrets in cookies; API scope unchanged); CSP header in nginx.conf at P7 |
| WSL file-watch on 9p mount is slow for HMR | dev flow documented: run vite **inside** the mounted container with `CHOKIDAR_USEPOLLING`, or node via nvm inside WSL (both covered in docs/WEB_DEV.md at P0) |
| Scope creep (new features sneak in) | this doc is the contract: UI change only; feature PRs go to the backlog file `docs/UI_BACKLOG.md` created at P0 |

---

## 10. Explicit "everything is kept" map

Nav rail: Learn, Composer, Challenges, Dashboard, Code Lab, Games,
Playground — 7-for-7. Composer: canvas + gate palette + param expressions,
save/load/delete circuits, QASM import/export, all five export targets,
backends incl. CUDA-Q GPU badge + unavailable reasons, shots, seed,
precision, noise panel (all six knobs + clamping warning), auto-measure and
payload-cap warnings, result tabs (diagram, histogram, probabilities,
Born-vs-shots, statevector, phase disk, Q-sphere, density matrix, Bloch,
ideal-vs-noisy), metric gauges incl. the CUDA-Q fidelity/purity omission,
timeline step-through, run-hash result caching, stale-result guard. Learn:
13 lessons, all inline demos (incl. the Grover amplitude lab and live Bloch),
quizzes. Challenges: descriptions, targets, grading copy, shot-noise
tolerance notes, history, recommendations. Dashboard: learner + instructor
views, per-student drill-in. Code Lab: 6 frameworks (incl. CUDA-Q), live
diagnostics, stdout, AI drafting with framework rules, sandbox error copy
verbatim. Games/Playground: all modes and previews. Auth: register/login,
roles (student/instructor/admin-visible surfaces), bootstrap admin flow.

Nothing in that list disappears or gains invented data; everything renders
the API's numbers with the same honesty rules the Streamlit app enforces
today.
