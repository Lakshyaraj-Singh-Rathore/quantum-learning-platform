# UI/UX QA handoff — Quantum Learning Platform

A self-contained brief for handing this project to a review agent that has
vision. Everything needed to boot the stack, log in and judge the UI is here;
the agent needs no prior context.

---

You are doing an in-depth UI/UX quality pass on a quantum-computing teaching platform. **You have vision — use it.** Screenshot constantly and actually look at the results. Your job is to find problems, not to reassure me that things work.

## 1. What this product is

A quantum-computing learning platform with three front ends:

- **`frontend/web`** — a React 18 + Vite + Tailwind v4 SPA. This is the **new UI**, a redesign in progress. **This is your primary testing target.**
- **`frontend/`** (Streamlit) — the **old UI**, still the default landing. Screenshot it for comparison, but **never modify its code.**
- **`backend/`** — FastAPI + Postgres + Redis + Celery. Serves `/api/*`.

Simulations run through Qiskit Aer, Cirq, PennyLane and qBraid. Curriculum content lives in `content/*.md` (67 lessons, LaTeX-heavy) and is ingested at startup.

## 2. Environment setup

```bash
git clone https://github.com/Lakshyaraj-Singh-Rathore/quantum-learning-platform
cd quantum-learning-platform
git checkout arena/01a0d874-quantum-learning-platform
git pull origin arena/01a0d874-quantum-learning-platform
```

Branch should be at or after commit `d68409e`.

Copy `.env.example` to `.env` **without changing the bootstrap credentials** — you need them to log in.

### Browser (important — read this before wasting time)

Every browser CDN is firewalled here. `npx playwright install` **will fail** with ECONNRESET, and `apt` cannot install the shared libraries Chromium needs. There is a committed script that works around this using only npm:

```bash
bash tools/browser-setup.sh
```

It installs `@sparticuz/chromium` (which ships the browser binary and Amazon Linux shared libs inside its npm tarball), unpacks them, and prints the `executablePath`, `LD_LIBRARY_PATH` and launch args you need. Launch with `--no-sandbox --disable-dev-shm-usage --disable-gpu`.

If you are working outside this sandbox and have normal network access, just use `npx playwright install chromium` instead.

## 3. Boot the stack

```bash
make upd GPU=0        # builds and starts everything
make ps               # confirm all services are up
```

The api container's entrypoint runs `alembic upgrade head` automatically on start — **do not skip this**, the curriculum is empty without it.

Service ports:

| Service | URL | Notes |
|---|---|---|
| **React SPA** | http://localhost:3000 | **primary target** |
| Vite dev server | http://localhost:3001 | `make web-dev`, has HMR |
| API | http://localhost:8000 | FastAPI, `/docs` for OpenAPI |
| Streamlit (old UI) | http://localhost:8501 | comparison only |
| Postgres | localhost:5432 | |
| Redis | localhost:6379 | |

There are existing check harnesses in `frontend/web` — run them first to establish a baseline, and re-run after any change you make:

```bash
cd frontend/web
npm install && node scripts/link-shared.mjs
npm run curriculum && npm run render:learn && npm run render:check \
  && npm run render:content && npm run a11y && npm run states
```

## 4. Logins

Two seeded accounts (from `.env.example`):

- `admin@local.dev` / `admin123` — role `admin`
- `instructor@local.dev` / `instructor123` — role `instructor`

There is **no seeded student account** — register one through the UI to test the student view. Test at least admin and student, since role gating changes what renders (the `render:check` harness runs anon/instructor/staff variants).

## 5. Pages to cover

All eight routes in the sidebar nav:

`/learn` · `/curriculum` · `/composer` · `/challenges` · `/dashboard` · `/codelab` · `/games` · `/playground`

Sidebar labels say which are "live": Curriculum and Composer are marked live; the rest are still landing phase by phase. Judge them all anyway, but note that a rough edge on a phase page is less severe than on a live one.

## 6. Known defects — verify these fixes actually landed

These were reported by the owner and fixed in commit `2ca7ddd`. **Verify each one on screen and say clearly whether it is fixed or still broken.**

1. **Composer doesn't fill the screen.** The sidebar was a fixed 240px. It is now a 60px rail that expands to 240px on hover/focus as an *overlay*. Check: the rail is ~60px at rest; hovering expands it; expanding does **not** reflow or stutter the circuit canvas underneath; the composer visibly uses the reclaimed width.
2. **"Preserve spacing" control overlapping the composer.** The circuit toolbar was a fixed 48px with no wrapping, so its controls spilled out once the column narrowed. Now it wraps. Check at narrow widths especially.
3. **Bloch sphere invisible.** It rendered but was drawn in `--line` (`#2a2a30`) and `--line-soft` (`#202024`) on a `#17171a` card — roughly 1.1:1 contrast. Now uses `--ink-3`. Check it's clearly visible in **both** dark and light themes.
4. **Tab highlighting.** Two bugs. (a) Playground's active tab was `bg-accent/10` with no colour change — near-invisible. Now accented text + underline. (b) Learn's "Try it yourself" tabs were keyed on the wrong state variable, so the *first* tab looked unselected until you clicked a different one and came back. **Reproduce (b) specifically: load a lesson fresh and look at the first tab before clicking anything.**
5. **Lesson track panel scrolls away.** Learn's left nav is now sticky from `lg` up. Scroll a long lesson and confirm the Track/Lessons panel stays reachable.
6. **No syntax highlighting.** Code blocks now use highlight.js with python/bash/json. Check colours are legible on dark *and* light, and that a plain ```` ``` ```` fence (no language) stays uncoloured rather than being mis-guessed.
7. **Empty curriculum sections.** Four sections rendered empty. Root cause: `build_curriculum` only serves topics with `status == "published"`, and 54 of 71 topics sat at `draft` with no publish step anywhere. Fixed by migration `h3c6d9e2f5a8`. **Check `/curriculum` shows all 10 sections populated** — if any are still empty, the migration did not run.

## 7. Full sweep — find things not on this list

Go beyond the seven. Specifically hunt for:

**Layout & responsive** — test at 1920, 1440, 1280, 768 and 375 wide. Look for: overflow, clipped text, horizontal scrollbars that shouldn't be there, elements colliding, content hidden behind the fixed sidebar, broken stacking/overlap of modals and dropdowns.

**Visual & theming** — dark is the default; there is a light toggle. Check **every** page in **both** themes. Look for: hardcoded colours that don't invert, text or icons that vanish on one theme, focus rings, hover states, disabled states, KaTeX maths legibility.

**Navigation** — the sidebar auto-hide rail; the command palette (there's a search button in the top bar and a keyboard shortcut); breadcrumbs; active-route indication; browser back/forward; deep links like `/learn?lesson=<slug>`.

**Interactive** — the Composer's drag-and-drop gate grid (drag a gate, undo/redo, the Inspect toggle, Show code panel, alignment select); Playground's seven tabs; Learn's lesson switching and track filter; the AI chat panel; forms and validation.

**Data & backend** — open DevTools. Watch the **console for errors** and the **network tab for failed or slow API calls** on every page. Try simulation runs on the local backends. Note anything that errors, hangs, or returns a 500. Do **not** submit to qBraid — it spends real credits.

**States** — empty, loading and error states for each page. Break the backend on purpose (stop the api container) and confirm the UI degrades honestly instead of showing a blank screen or a spinner forever.

**Accessibility** — keyboard-only traversal of each page, visible focus, form labels, alt text, heading order, colour contrast. Note: the existing `a11y` harness already reports a known issue — composer gate tiles are `div`s with no button role and no keyboard path. That is **tracked for the cutover, not a new finding**; confirm it and move on.

## 8. Hard constraints — do not

- **Never modify anything under `frontend/` Streamlit.** Screenshot it for comparison only. React SPA work is fine.
- **Never touch `backend/app/curriculum.py`'s `status` fields.** 54 topics are deliberately `draft` in the registry while the database says `published`. Two legitimate tests depend on the registry values; changing them breaks a Gate 1 architecture guard. This divergence is an open decision for the owner — **report on it, don't fix it.**
- **Never remove the `data-cutover-gate="pending-personal-ui-testing"` marker** in `frontend/web/src/components/shell/Sidebar.tsx`. It gates the P8 cutover and must survive until the owner personally signs off.
- **Do not run production migrations or modify production data.**
- **Do not weaken a real test to make it pass.** If a test fails, fix the code or report the failure.
- **Do not submit jobs to qBraid** — real credits.

## 9. Report format

Give me:

1. **Fix verification table** — the seven defects, each marked FIXED / STILL BROKEN / PARTIAL, with a screenshot for each.
2. **New issues**, ranked by severity, each with: page, viewport, theme, reproduction steps, and a screenshot.
3. **Backend observations** — console errors and failed API calls, grouped by page.
4. **Accessibility findings** — separate from visual issues.
5. **Screenshots saved somewhere I can browse**, named by page + viewport + theme (e.g. `composer-1440-dark.png`).

Be blunt. If something looks bad, say so — I would rather hear about twenty problems than be told everything is fine. Where you can measure something objectively (contrast ratio, element width, overlap), include the number rather than an impression.
