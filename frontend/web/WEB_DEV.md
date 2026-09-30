# Working on the new web UI (phase P0)

The React SPA in this folder is the replacement front end described in
`docs/UI_REDESIGN_PLAN.md`. **P0 delivered the shell** (routing, auth, design
tokens) and **P1 rebuilt the Composer**: the drag-and-drop grid, the run
settings, noise model and job lifecycle. The other six pages are still
placeholders that say so. The Streamlit app on `:8501` remains the real UI for
everything else until the parity cutover (P8).

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
