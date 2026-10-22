# QML Lab — Phase 0 UI Audit

**Commit:** `648dec4` (tree identical to `origin/main @ 12d33df`)
**Scope:** establish the visual and structural contract the QML Lab must satisfy so it is
indistinguishable from the rest of the product. No UI code written in Phase 0.

Companion to [`00-audit.md`](./00-audit.md). Governing rules: `docs/prompts/QML_LAB_VISION_AGENT.md` §3.

---

## 1. Styling system

**Tailwind v4, CSS-first.** There is **no `tailwind.config.js`** and none may be added. The theme is
declared in `src/globals.css`:

- `@theme { … }` (lines 4–42) — **only these generate utility classes.**
- `:root { … }` (lines 44–92) — plain CSS variables for hand-written CSS. They do **not** generate utilities.

### 1.1 The 31 tokens that generate utilities

Extracted from `globals.css` lines 4–42:

```
--color-bg          --color-raised      --color-bg-raised   --color-subtle
--color-bg-subtle   --color-hover       --color-bg-hover    --color-active
--color-bg-active   --color-line        --color-line-soft   --color-line-focus
--color-ink         --color-ink-2       --color-ink-3       --color-accent
--color-accent-2    --color-accent-ink  --color-accent-soft --color-ok
--color-warn        --color-danger      --color-gate-h      --color-gate-pauli
--color-gate-phase  --color-gate-param  --color-gate-multi  --color-gate-meas
--font-display      --font-sans         --font-mono
```

### 1.2 Utilities that do **not** exist

Verified in source **and** in the built CSS (`dist/assets/*.css` after `npx vite build`):

| Class | Files using it | Rules emitted in `dist` |
|---|---:|---:|
| `bg-panel` | 0 | **0** |
| `text-muted` | 0 | **0** |
| `text-fg` | 0 | **0** |
| `bg-card` | **6** | **0** |
| `bg-raised` | 102 | 1 |
| `bg-subtle` | 100 | 1 |
| `text-ink-3` | 425 | 1 |

`bg-panel`, `text-muted` and `text-fg` are plausible-sounding names that would silently do nothing.
**Do not use them.**

### 1.3 The live `bg-card` trap

`--color-card` **is not defined anywhere** in `globals.css`. Yet `bg-card` is used **10 times across 6
files**:

```
components/qudit/DensityMatrixInspector.tsx
components/qudit/QuditCircuitEditor.tsx
components/qudit/QuditGatePalette.tsx
components/qudit/QuditLearnPanel.tsx
components/qudit/QuditNoisePanel.tsx
pages/QuditLabPage.tsx
```

The class compiles to **nothing** — `grep -c "\.bg-card{" dist/assets/*.css` → **0** — so those panels
render with no background at all. This is a real, shipped defect in the Qudit Lab.

**Two rules follow, both from §3:** never use `bg-card` in QML code, and **do not fix the existing ten** —
`components/qudit/*` and `QuditLabPage.tsx` are on the do-not-touch list (§4). Use `bg-raised` or
`bg-subtle`.

### 1.4 House token distribution

Counted first-hand over `src/**/*.tsx` with a word-boundary regex
(`grep -rhoE "(^|[\"' \`])<token>([\"' \`/]|$)"`):

| Token | Count | Token | Count |
|---|---:|---|---:|
| `text-ink-3` | 425 | `border-line-soft` | 89 |
| `border-line` | 246 | `bg-accent` | 74 |
| `text-ink` | 209 | `border-accent` | 53 |
| `text-accent` | 150 | `bg-bg` | 45 |
| `text-ink-2` | 142 | `bg-hover` | 22 |
| `bg-raised` | 102 | `bg-subtle` | 100 |

These are slightly below the amendment's §0 figures (e.g. `text-ink-3` 425 vs 431, `bg-hover` 22 vs 63)
because this regex counts **bare** occurrences only and excludes variant-prefixed uses such as
`hover:bg-hover` and `md:bg-raised` — which is most of `bg-hover`'s usage. The **ranking and shape are
identical**, and that is what "match the house distribution" means in practice:

> body text `text-ink-3` → headings `text-ink` / `text-ink-2` → borders `border-line` (soft variant for
> inner dividers) → `text-accent` for emphasis → surfaces `bg-raised` / `bg-subtle` on a `bg-bg` page.

Semantic colours `--color-ok`, `--color-warn`, `--color-danger` carry status only — never decoration.

### 1.5 Dark theme only

`grep -cE "html\.light|body\.light|@media \(prefers-color-scheme: light\)" globals.css` → **0**.
There is no light mode. **Do not build one and do not add `dark:` variants** (§3).

---

## 2. QL-001 — the hard rule on dynamic colour

The most expensive defect of the previous QA campaign: a heatmap rendered **colourless** because its class
name was interpolated. Tailwind scans source text statically; a constructed class name never reaches the
compiler, so **zero rules are emitted** — exactly the `bg-card` failure mode, but self-inflicted at runtime.

**Forbidden**

```tsx
<div className={`bg-${color}-500`} />
<div className={`text-${level > 0.5 ? "ok" : "danger"}`} />
```

**Required**

```tsx
// data-driven colour → inline style, never a class
<rect style={{ fill: `color-mix(in oklab, var(--accent) ${pct}%, transparent)` }} />

// fixed variants → complete literal class strings in a ternary
<span className={ok ? "text-ok" : "text-danger"} />
```

Every QML component that paints from data — confusion matrix, loss curve, probability bars, decision
boundary — **must** use inline `style` with `var(--accent)` / `--ok` / `--warn` / `--danger` / `--line`.

**Verification is mandatory, not optional (§8):** after building, grep the emitted CSS for each utility the
new code relies on. A class that emits no rule is a defect regardless of how the component looks in a
screenshot.

---

## 3. Charts: hand-rolled SVG

No charting library is installed (`recharts`, `chart.js`, `d3`, `victory`, `nivo`, `visx` → **0** hits in
`package.json`) and **none may be added** (§1.4). Every QML visualisation is hand-written SVG.

Existing precedents to copy rather than invent:

| Component | Path | What to take |
|---|---|---|
| Circuit diagram | `src/components/results/CircuitDiagram.tsx` | SVG layout grid: `CELL = 58`, `LEFT = 56`, `TOP = 26`; `GATE_COLORS` map; `export function CircuitDiagram({ ir }: { ir: CircuitIR })` — **reused directly by the P3 Circuit View** |
| Bloch sphere | `src/components/results/InteractiveBlochSphere.tsx` | hand-rolled 3-D projection in SVG |
| Density matrix | `src/components/qudit/DensityMatrixInspector.tsx` | `magStyle()` — the fixed pattern for data-driven cell colour via inline style (read-only reference; **do not edit this file**) |
| Grover panel | `src/components/grover/GroverLab.tsx` | probability-bar rendering |
| Noise Lab | `src/components/noise/NoiseLabView.tsx` (883 lines) | the house pattern for a large multi-panel lab (read-only reference) |

---

## 4. Component and data reuse order (§3.3)

Work down this list; only move to the next rung when the one above genuinely cannot serve.

1. **Existing components** — `shell/*`, `qudit/*`, `noise/*`, `smart_composer/*`, `results/*` (read-only for
   the latter three; reuse by importing, never by editing).
2. **Installed primitives** — `@radix-ui/react-dialog`, `@radix-ui/react-select`,
   `@radix-ui/react-tooltip` (**only these three**), `lucide-react` icons, `clsx`.
3. **State/data** — `@tanstack/react-query` for server state, `zustand` for local state
   (session store key: `ql-session`).
4. **Network** — `src/api/client.ts` (`request<T>`, `api`, `ApiError`, `API_BASE = "/api"`), with a new
   `src/api/qml.ts` layered on top. **Never a raw `fetch`.**

There is **no `src/components/ui/` directory**. New shared QML primitives go in `src/components/qml/`.

---

## 5. Shell, navigation and routing

- **Nav** — `src/components/shell/nav.ts:25-46`: 9 items across 4 sections (`study`, `build`, `practice`,
  `insights`). QML Lab goes in **`build`**, next to `Qudit Lab (Beta)`, with a `lucide-react` icon.
  One item, flag-gated.
- **Routes** — `src/App.tsx:68-78`: 11 routes plus `<Route path="*" element={<NotFound />} />`.
  QML adds one lazy import and one route. **With `qml_enabled` false the route is not registered, so the
  catch-all renders `NotFound` — a 404, exactly as §1.7 requires.**
- **Precedent note (deliberate departure, §0):** Noise Lab and Smart Composer are **not routes** — they are
  embedded inside `ComposerPage.tsx` (imports `:60-61`, mounted `:584` / `:824`). QML Lab takes its own
  route anyway: it has four distinct views, long-running jobs and its own polling lifecycle, none of which
  fit inside a tab of another page. Recorded as D-005 in `DECISIONS.md`.

---

## 6. Observed state of the Composer (context only — do not act)

A screenshot of the Composer supplied with the task was reviewed. Visible at ~1362 px wide:

- the editor sits inside a **nested scroll region** with its own scrollbar, leaving a wide empty gutter;
- palette tiles **clip their labels** — "Measur", "Barrier" are cut off mid-word;
- the right-hand "Circuit / 0 ops / empty circuit" panel is sparse relative to the space it occupies.

These are **pre-existing conditions in `ComposerPage.tsx`, a do-not-touch file (§4)**. They are recorded
here for two reasons only: so the QML Lab does **not** copy the nested-scroll layout or fixed-width tile
pattern, and so these symptoms are not later mistaken for QML regressions. **No fix is proposed and none
will be made under this task.**

---

## 7. The four QML Lab views — structural plan

All four live under one route, `/qml-lab`, as sibling panels in the standard shell. No new layout
primitives; the page frame matches the existing labs (`bg-bg` page, `bg-raised` panels, `border-line`
dividers, `text-ink`/`text-ink-3` type scale).

| View | Contents | Reuse |
|---|---|---|
| **Configuration** | dataset / qubits / layers / epochs / batch / learning-rate / seed, each bounded by the same limits the server enforces; live cost estimate; submit | Radix `Select`, existing form idioms, `src/api/qml.ts` |
| **Circuit View** | the encoder + variational ansatz as a real diagram | **`components/results/CircuitDiagram.tsx` directly** |
| **Training Dashboard** | loss curve, accuracy curve, epoch/batch progress, elapsed time, cancel | hand-rolled SVG; `react-query` polling that **stops on terminal status and on unmount** |
| **Results** | confusion matrix, final metrics, classical-baseline comparison, inference panel | hand-rolled SVG matrix with inline-style fills (QL-001) |

**Polling discipline (explicit acceptance criterion):** the dashboard must stop polling when the experiment
reaches a terminal state (`completed`, `failed`, `cancelled`) **and** when the component unmounts. A
harness will assert both, and will be shown failing before it is accepted (§1.5).

---

## 8. UI acceptance checklist for every later phase

1. No interpolated Tailwind class anywhere (QL-001) — data-driven colour uses inline `style`.
2. No `bg-card`, `bg-panel`, `text-muted`, `text-fg`.
3. Every utility the new code depends on **emits a rule in `dist/assets/*.css`** after a production build;
   proven by grep, not by eye.
4. No chart library, no `tailwind.config.js`, no new runtime dependency.
5. No `dark:` variants, no light mode.
6. Token distribution matches §1.4's shape.
7. Flag off ⇒ no nav item, route 404s, zero visual change anywhere else.
8. Interactive controls are **hit-tested** (`elementFromPoint`), not eyeballed — the QL-014 lesson: a dead
   control under an overlay is invisible in every screenshot.
9. Narrow-viewport behaviour checked at 390 px and 768 px (QL-008 and QL-003 both surfaced only there).
10. a11y harness still reports **0 criticals**.
