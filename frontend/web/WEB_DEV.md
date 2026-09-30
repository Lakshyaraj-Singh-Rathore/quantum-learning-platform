# Working on the new web UI (phase P0)

The React SPA in this folder is the replacement front end described in
`docs/UI_REDESIGN_PLAN.md`. **P0 delivers the shell only**: routing, auth, the
design tokens, and the seven page placeholders. The Streamlit app on `:8501`
remains the real UI until the parity cutover (P8) — nothing has been switched
over and no page has been rebuilt yet.

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
```

## Honest status of P0

- Verified here: TypeScript compiles, the bundle builds (≈234 kB, 75 kB gzipped),
  tokens resolve to the intended CSS variables, the auth flow works against a
  real FastAPI instance, protected routes leak nothing when signed out, and the
  served bundle proxies `/api` correctly.
- **Not** verified here: the Docker build (no Docker in the authoring sandbox)
  and real-browser interaction. Run `make upd` locally and the two URLs above
  are the check.
