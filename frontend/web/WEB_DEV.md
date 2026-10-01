# Working on the new web UI (phase P0)

The React SPA in this folder is the replacement front end described in
`docs/UI_REDESIGN_PLAN.md`. **P0 delivered the shell** (routing, auth, design
tokens), **P1 rebuilt the Composer** (grid, run settings, noise, job lifecycle)
and **P2 delivered the result suite** (gauges, histogram, tables, comparisons,
density matrix, Bloch). Three views from Streamlit's result tabs are not yet
ported — phase disk, Q-sphere and the circuit diagram — and say so in the tab
strip's absence. The other six pages are still placeholders. The Streamlit app
on `:8501` remains the real UI for everything else until the parity cutover
(P8).

## Run it

```powershell
# Windows PowerShell, in the repo root
make upd          # detached stack; rebuilds images, including `web`
docker compose ps # web should be "running" on 0.0.0.0:3000
```

Then open <http://localhost:3000>. Streamlit is still on <http://localhost:8501>.

| URL | What |
| --- | --- |
| <http://localhost:3000> | New SPA (nginx: static bundle + `/api` proxy) |
| <http://localhost:3001> | Vite dev server with HMR (`make web-dev`) |
| <http://localhost:8501> | Frozen Streamlit app (unchanged) |
| <http://localhost:8000/docs> | FastAPI |

```powershell
make web-dev      # HMR iteration; needs `make upd` running first
make web          # rebuild just the SPA image (fast: layer-cached npm install)
```

`web-dev` runs Node in a container — **no Node installation on the host**. The
source tree is bind-mounted; `node_modules` lives in a named volume so it never
lands in the repo.

## How the API is reached

The browser only ever calls **relative `/api/*`**. nginx (production) and Vite
(dev) strip the prefix and forward to `api:8000`, so the app is same-origin
everywhere and CORS is a development convenience rather than a deployment
requirement. `VITE_PROXY_TARGET` overrides the dev target; it defaults to
`http://localhost:8000`.

## The grid is shared with Streamlit, not copied

`frontend/circuit_composer/frontend/src` is the single implementation of the
drag-and-drop grid and is compiled into **both** UIs — Streamlit through
`streamlit.tsx` (which wires `setComponentValue` / `setFrameHeight`), and this
app through `ComposerInner` with plain props. `Composer.tsx` itself imports no
`streamlit-component-lib`, so the SPA ships none of it.

Two consequences worth knowing:

* **One React only.** The grid's directory sits outside this app, so
  `scripts/link-shared.mjs` (run automatically by `dev`/`build`) points
  `frontend/node_modules/{react,react-dom,@types}` at this app's copies. `npm
  install` inside the component creates a *second* React; Vite's `dedupe`
  keeps the bundle correct, but plain Node would pick the wrong one and
  `npm run render:check` would fail — the script warns if it sees it.
* **The grid's CSS is scoped.** Its stylesheet used to set `--bg`/`--line`
  on `:root`, which would have hijacked this app's palette. Those two blocks
  are now `.composer-host`, and the page supplies that class, so the grid
  keeps its own colours inside its card.

## Layout

```
src/
  api/         client.ts (fetch + JWT + error shaping), auth.ts, backends.ts, types.ts
  state/       session.ts, theme.ts  (zustand, persisted to localStorage)
  components/  ui.tsx (primitives), shell/ (Sidebar, TopBar, AppShell), RequireAuth.tsx
  pages/       LoginPage.tsx, PlaceholderPage.tsx
scripts/       smoke-auth.mts (live API), render-check.mts (headless render)
```

Design tokens live in `src/globals.css`: dark is the default palette on `:root`,
`html.light` overrides it. Components consume tokens only (`bg-raised`,
`text-ink-2`) — never raw colours — so theming stays a one-place change.

## Checks

```powershell
cd frontend/web
npm install
npm run build            # tsc --noEmit + vite build
npm run typecheck
npm run render:check     # renders the real tree headlessly (student/anon/staff)
```

`smoke-auth.mts` drives the real modules against a **live** API (no mocks) and
asserts the auth contract — registration, login, `/auth/me`, the engine
catalogue, and that FastAPI's own error text reaches the user:

```bash
# from the repo root, with the stack up (WSL/Git Bash)
API_TARGET=http://localhost:8000 npm --prefix frontend/web run smoke:auth
API_TARGET=http://localhost:8000 npm --prefix frontend/web run smoke:composer
```

`smoke:composer` exercises the Composer's data path against a live API: a Bell
state passes `/inspect`, an overlapping layer is rejected with the message the
page shows, a job is created with the chosen backend/shots, and the noise model
is refused on backends the page disables it for. It needs no Celery worker —
unprocessed jobs are asserted, not waited out.

### The result views are checked against real numbers

Two fixtures carry the truth, and both are generated rather than hand-written:

* `test-fixtures/quantum-golden.json` — numpy's answers for the maths in
  `src/lib/quantum.ts` (Bloch vectors, entropy, purity, relative phases).
  Regenerate with `scripts/golden-quantum.py` (run it from the backend venv);
  `npm run golden:quantum` checks the TypeScript agrees to 1e-9. This caught a
  determinant error that produced a purity of 1.375 — impossible, and invisible
  without the fixture.
* `test-fixtures/engine-results.json` — genuine `qiskit_aer.run()` output for a
  Bell state, a 3-qubit GHZ and a noisy Bell. Regenerate with
  `npm run fixtures:engine` (needs the backend venv, for qiskit-aer);
  `npm run render:results` renders every view against them and checks the
  bitstrings, gauge values and refusal messages.

The views themselves are plain SVG/CSS, not plotly: bars, arcs and grids do not
need a megabyte of JavaScript, and this way every view is checkable without a
browser.

## Honest status of P0

- Verified here: TypeScript compiles, the bundle builds (≈274 kB, 87 kB gzipped),
  tokens resolve to the intended CSS variables, the auth flow and the Composer
  data path work against a real FastAPI instance, protected routes leak nothing
  when signed out, and the served bundle proxies `/api` correctly.
- **Not** verified here: the Docker build and real-browser interaction — the
  authoring sandbox has neither Docker nor a downloadable Chromium. Run
  `make upd` locally; the two URLs above are the check. Jobs also cannot
  *complete* in the sandbox (no Redis/Celery), so every run there fails with
  the enqueue error rather than producing counts.

## P3 — Code Lab

The editor page (`src/pages/CodeLabPage.tsx`) replaces the P3 placeholder. It
keeps every element the Streamlit page had: the six-framework language list, the
editor, live problem reporting with a marker view, the sandbox rules, the AI
draft box with its "nothing runs until you build" note, build output, and the
same result views as the Composer.

### The checks moved to the server

`frontend/lib/code_checks.py` is now `backend/app/services/code_checks.py`. The
Streamlit page imports it through a shim (`frontend/lib/code_checks.py`) so the
frozen app and the new UI run one implementation, and the new page calls it over
`POST /codelab/check` (auth required) instead of in-process. The endpoint never
executes the learner's program — it is a syntax/import pass meant to run while
they type, debounced 400 ms.

`backend/tests/test_codelab_check.py` pins that contract (12 tests): findings
are 1-based, a nonsense buffer never 500s, and an anonymous POST never reaches
the checker.

### Two things worth knowing

**The editor is lazily loaded.** CodeMirror is ~163 kB gzipped and only Code Lab
uses it, so the route is a `React.lazy` split. The main chunk stays at ~302 kB
(95.5 kB gzipped) and the editor's 486 kB chunk loads only on visiting `/codelab`.

**`render:codelab` proves less than it looks.** Under `renderToString` effects
never run, so the language is still unselected and the buffer empty; CodeMirror
mounts as `<div class="cm-theme-light">` and fills itself in on the client. The
16 checks therefore cover the part that does not move — the language list from
`GET /codelab/starters`, the sandbox rules, the AI honesty note, and that no
result is claimed before a build. Picking a language, typing, Build and Run are
**browser-only** and still need a real pass.

### Verified here

* `npm run build` — clean; main chunk 302.30 kB / 95.50 kB gzipped,
  `CodeLabPage` 485.59 kB / 162.64 kB gzipped in its own chunk.
* `npm run render:codelab` — 16/16.
* `npm run render:check` — 54/54 across student, anonymous and instructor.
* `npm run golden:quantum` — 190/190. `npm run render:results` — all passed.
* Backend `511 passed, 5 skipped`; frontend `418 passed, 77 skipped`.
* Live API smoke against a running backend: `GET /codelab/starters` returns the
  five frameworks installable here (CUDA-Q is absent because the wheel is — the
  availability filter working as intended); `/codelab/check` returns findings
  and a marker view for a blocked import; `/codelab/build` turns the Qiskit and
  QASM 3 starters into IR (2 qubits, depth 3) and returns 422 for a blocked
  import; an anonymous check gets 401.

### Not verified here

Real-browser interaction (no Chromium in the sandbox): typing in the editor, the
debounced diagnostics firing, Build → Run producing results, and the AI draft
box. Docker is also unavailable, so the built image is untested.

## P4 — Learn

The Learn placeholder is now the real page: a lesson list split into the Theory
and Circuit tracks, the lesson body, the ten interactive demos, and the
curriculum-grounded AI tutor.

### The reader had to carry real markdown

The lessons are LaTeX-heavy (`$|0\rangle$` inline, `$$…$$` display) and use GFM
tables and fenced code. Streamlit's `st.markdown` renders all of it today, so
the reader uses `react-markdown` + `remark-gfm` + `remark-math` + `rehype-katex`
rather than a hand-rolled subset that would quietly delete half the curriculum.
`render:learn` asserts the maths is *typeset* (21 KaTeX spans on 01_qubits) and
that no raw `$$` survives, plus that tables come out as `<table>`.

KaTeX's stylesheet is imported in `main.tsx`, not in `Markdown.tsx`: a CSS
import in that module breaks every Node render harness, which loads the real
components outside a bundler.

The selected lesson is derived, not stored in an effect — a selection outside
the visible track falls back to the first one. That is simpler React, and it is
what lets the SSR harness see the lesson body at all.

### Every demo number is pinned to numpy

`src/lib/demos.ts` is the maths behind the demos, ported from
`frontend/lib/playground.py`. `scripts/golden-demos.py` regenerates
`test-fixtures/demo-golden.json` by calling the **same** `playground.py` the
Streamlit demos call, and `npm run golden:demos` checks the port agrees:
**804 values at 1e-9**.

That caught a real bug: `blochAngles` in `src/lib/quantum.ts` already returns
degrees, and the port converted again, so the gate sandbox reported θ as
15469°. Four further mismatches were all at the poles, where φ is genuinely
arbitrary — numpy and the port wrap it differently and neither is wrong, so the
harness skips φ there rather than papering over it with a tolerance.

`sample` is deliberately **not** pinned: it draws from numpy's PCG64, which
JavaScript cannot reproduce. The lesson it teaches is the distribution, not the
draw.

### `circuit_lab` is a pointer, not the grid

Streamlit embeds the real drag-and-drop composer in the lesson, sharing the
Composer's session circuit. Here the Composer's circuit is page-local state, so
there is nothing to share yet. Rather than draw a grid that looks like the
composer but is not, that demo explains and links to the real one. Lifting the
circuit into a shared store is the follow-up that turns it back into an
embedded editor.

### Verified here

* `npm run build` — clean; main 301.96 kB / 95.33 kB gzipped, LearnPage
  467.49 kB / 140.24 kB and CodeLabPage 485.59 kB / 162.64 kB in their own
  chunks. Both routes are lazily loaded.
* `npm run golden:quantum` 190/190; `npm run golden:demos` 804/804.
* `npm run render:learn` 29/29, `npm run render:codelab` 16/16,
  `npm run render:check` 54/54, `npm run render:results` passed.
* Backend `511 passed, 5 skipped`; frontend `418 passed, 77 skipped`.

### Not verified here

Real-browser interaction (no Chromium): dragging a slider, measuring the qubit,
switching lesson or track, and sending a question. Docker is also unavailable.

## P5 — Challenges and Dashboard

Both placeholders are now the real pages.

### The circuit moved into a shared store

Streamlit kept one circuit in `st.session_state`, so a circuit built inside a
lesson was still there when the learner opened the Composer, and Challenges
could submit "your current circuit". Reproducing that meant lifting the
Composer's circuit out of page-local `useState` into `src/state/circuit.ts`.

That closed the one gap left in P4: `circuit_lab` is now the **real**
drag-and-drop grid inside the lesson (`ComposerInner`, the same component the
Composer uses), not the pointer it had to be when the circuit was private. The
coding-challenge tab shows the same shared circuit and submits it.

### Grading is polled, and a failed job says so

Submitting a challenge enqueues a Celery job, so the attempt is polled every
500 ms until it settles — the same loop Streamlit ran. A job that never ran
(no worker, or an invalid circuit) settles as failed or as graded-with-a-
failure-message; either way the page shows that message instead of sitting on
"Grading…" forever.

### Verified here

* `npm run build` — clean; main chunk 301.91 kB / 95.29 kB gzipped. All four
  new routes are lazily loaded, and Challenges/Dashboard are tiny (2.8 kB and
  2.3 kB gzipped) because the composer grid is already in the main chunk via
  the Composer.
* `npm run render:p5` 31/31 against a fixture captured from a live API:
  5 quizzes, 13 challenges, learner progress and the instructor overview. It
  asserts both the populated state *and* the fresh-cohort state, where every
  section must say it has no data rather than render an empty box.
* `render:check` 54/54, `render:learn`, `render:codelab`, `render:results`,
  `golden:quantum` 190/190, `golden:demos` 804/804.
* Backend `511 passed, 5 skipped`; frontend `418 passed, 77 skipped`.
* Live API smoke: a quiz submit scored 1.0/3.0 with per-question feedback; a
  challenge submit graded with its feedback string; the instructor overview,
  student list and student detail all returned; and a **student gets 403** on
  `/dashboard/instructor`, so the role gate is real.

### Not verified here

Two things behind a click, which renderToString cannot reach: the scored quiz
view and the graded-attempt result. Both were exercised against a live API
instead (above). Slider/select interaction, Docker and real-browser behaviour
remain unverified, as before.

## P6 — Games and Playground

### P6a: Games

The catalogue with per-game progress, and playing a level on the real
drag-and-drop grid with its objective, rules and grading result.

All four grader result panels are covered, because each level's grader reports
differently: the truth table (with its superposed-input warning and the rule
for reading controls), Shot Detective's convergence curve with the subsampling
caveat, Find the Bug's edit budget, and the fidelity note on the state-graded
levels, including why a histogram cannot tell |Φ+⟩ from |Φ−⟩.

A result describes the circuit that was graded, not whatever is on the grid
now. The circuit is stamped (op ids stripped, since they are regenerated on
every edit) and a result is discarded once the grid no longer matches —
otherwise a "Level complete" banner sits beside a circuit the grader never saw.

Both fixtures are generated, not written by hand: `test-fixtures/games.json`
is a live `GET /games` (4 games, 10 levels), and
`test-fixtures/games-results.json` is the platform's **own** `game_graders.py`
running on real Aer counts — a 4/4 truth table and a subsampled curve from
4096 real shots.

### P6b: Playground

Seven tabs. Five of them *are* the lesson demos and are rendered from the same
components — `render:playground` asserts that reuse rather than trusting it.
The other two are Playground-specific: Bit vs Qubit (the simpler form, without
the measure/reset cycle) and Build a Qubit, which dials in a state by
amplitudes or angles and then applies the gates off the **real** grid.

Build a Qubit models one qubit, so `gatesFromIr` reports what it could not
apply rather than silently dropping it: with the shared Bell circuit, H is
applied to q0 and the CNOT and both measurements are reported as skipped, with
a pointer to the Composer where the full simulator runs.

### All seven pages are now real

`PlaceholderPage` is no longer imported anywhere: Learn, Composer, Challenges,
Dashboard, Code Lab, Games and Playground are all live routes. The main chunk
shrank to 299.66 kB (94.64 kB gzipped) now that the placeholder scaffolding is
gone.

### Verified here

* `npm run build` — clean; main 299.66 kB / 94.64 kB gzipped, with LearnPage
  2.90, Dashboard 2.26, Challenges 2.78, Playground 3.06, Games 4.27 and
  CodeLab 162.64 kB gzipped in their own chunks.
* `render:games` 30/30, `render:playground` 20/20, `render:check` 54/54,
  plus `render:p5`, `render:learn`, `render:codelab`, `render:results`,
  `golden:quantum` 190/190 and `golden:demos` 804/804.
* Backend `511 passed, 5 skipped`; frontend `418 passed, 77 skipped`.

### Not verified here

"Run & score" and the polling it starts are behind a click that renderToString
cannot reach, so the result panels were checked by rendering `LevelResult`
directly with real grader output. Tab switching, Docker and real-browser
behaviour remain unverified, as before.
