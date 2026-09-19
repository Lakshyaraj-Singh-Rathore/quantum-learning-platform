# UI redesign brief — QuantumLearn

Paste everything below the line into your AI coding agent.

---

# Task: redesign the QuantumLearn interface to professional product quality

You are the design engineer on **QuantumLearn**, a quantum computing learning
platform built with Streamlit and FastAPI. The engineering is finished and
correct — **516 tests pass** (324 backend, 192 frontend). What lets it down is
the interface: it looks like default Streamlit with emoji headings bolted on.

Your job is to make it look like a product someone would pay for, **without
changing a single behaviour**. Treat all computation, every plot, and every API
call as read-only infrastructure.

Reference points for the standard expected: **IBM Quantum Composer**, **Linear**,
**Vercel dashboard**. Restrained palette, deliberate typography, generous
whitespace, obvious visual hierarchy, nothing decorative for its own sake.

---

## Stack facts, already verified — do not re-derive these

- Python 3.11, **Streamlit 1.41.1** (pinned), Plotly, a custom React/TypeScript
  drag-and-drop component, FastAPI over HTTP.
- **Streamlit 1.41.1 supports exactly six `[theme]` keys.** Anything else in
  `[theme]` is silently ignored, so do not invent keys:

  ```
  base  primaryColor  backgroundColor  secondaryBackgroundColor  textColor  font
  ```

  There is **no** `borderColor` and **no** font-size key in this version. All
  other styling must come from injected CSS.
- `font` accepts only `"sans serif"`, `"serif"` or `"monospace"`. To use a real
  typeface (Inter, IBM Plex Sans, Space Grotesk) you must `@import` it in your
  CSS and set `font-family` on `html, body, [class*="st-"]`.
- These `data-testid` selectors are **confirmed present in this exact build** —
  I checked the shipped JS bundles. Prefer them over `st-emotion-cache-*`
  classes, which are hashed and change between releases:

  ```
  stAppViewContainer   stSidebar        stHeader       stToolbar
  stMainBlockContainer stVerticalBlock  stHorizontalBlock
  stTabs               stExpander       stMetric       stButton
  stTextInput          stSelectbox      stSlider       stAlert
  stMarkdownContainer
  ```

## Repository map

```
frontend/
  Home.py                 98 lines   landing page
  pages/
    1_Learn.py           116 lines   lesson reader + AI tutor chat
    2_Composer.py        487 lines   circuit editor, run, results, exports
    3_Challenges.py      163 lines   coding challenges
    4_Dashboard.py       189 lines   student + instructor dashboards
    5_Code_Lab.py        275 lines   write code, build a circuit, run it
  lib/
    viz.py              1236 lines   ALL plots.        DO NOT TOUCH
    api_client.py        320 lines   HTTP + caching.   DO NOT TOUCH
    bootstrap.py          36 lines   sys.path shim.    DO NOT TOUCH
    composer.py          638 lines   Python grid editor + palette
    timeline_strip.py    117 lines   step-through transport bar
    auth.py              108 lines   login/register/sidebar
  circuit_composer/                  React component.  DO NOT TOUCH
.streamlit/config.toml               theme lives here
```

---

## Hard constraints — violating any of these breaks the product

### 1. `frontend/lib/viz.py` is off-limits entirely

Every visualisation lives here, and each is verified against analytic physics.
The Bloch sphere alone has 23 tests pinning exact values (`|0>` at theta = 0,
`T|+>` at phi = 45 degrees, Bell qubits collapsing to the origin). These are
instruments, not decoration: a cosmetic change can silently teach wrong physics
to a student.

Do not restyle, recolour, resize or "modernise" any of:

```
histogram              probability_table   phase_disk       qsphere
amplitude_table        bloch_sphere        circuit_diagram  backend_badge
gauge                  metric_meters       ideal_vs_noisy   born_vs_shots
density_matrix         statevector_ket     phase_table
reduced_density_matrix bloch_vector        bloch_angles
```

You **may** change which column, tab or container a chart is placed in.
You **may not** change what it draws.

Corollary: do not add global CSS that reaches inside Plotly, for example
`[data-testid="stPlotlyChart"] svg { ... }`. Style the container, never the
figure.

### 2. `frontend/lib/api_client.py` is off-limits

Read-only endpoints are memoised with `@st.cache_data`; mutating ones
(`submit_job`, `save_circuit`, `import_qasm`) deliberately are **not**, because
caching a job submission would re-spend real qBraid credits. Adding or removing
a decorator here produces either a stale UI or a billing bug.

### 3. `frontend/circuit_composer/` is off-limits, and the Composer page has a trap

The React drag-and-drop grid took four attempts to stop rendering as a blank
white iframe. Two failure modes you must not reintroduce:

**Element-path remounting.** Streamlit addresses a custom component by its
position in the element tree. If the number of widgets *above* the component
changes, Streamlit destroys and recreates the iframe; the component then misses
Streamlit's one-shot RENDER event and paints blank white **with no console
error**. `2_Composer.py` therefore does this, and you must keep it:

```python
timeline_slot  = st.container()   # line 62
divider_slot   = st.empty()       # line 63
composer_slot  = st.container()   # line 64

with composer_slot:               # filled FIRST
    edited = circuit_composer(...)

with timeline_slot:               # filled SECOND, appears ABOVE
    timeline_strip.render(...)
```

Anything you add above the composer must go **inside `timeline_slot`**, never
before it.

**React.StrictMode.** Never wrap the component in it. StrictMode double-mounts,
the RENDER listener is torn down mid-delivery, and the iframe stays blank.

The theme must also stay **dark-based** (`base = "dark"`). The component reads
`theme.base` and toggles its own `dark` CSS class; a light theme leaves it
visually inconsistent with the page around it.

### 4. Preserve every `st.session_state` key

Renaming any of these loses user state or breaks cross-page flows:

```
token  user  access_token
circuit  last_job_id  last_job_circuit  last_job_qubits
timeline  timeline_signature  tl_step
codelab_code  codelab_framework  codelab_built  codelab_job_id
```

### 5. Preserve all 64 widget `key=` values

The test suite and session state both depend on them: `react_composer`,
`noise_t1`, `noise_t2`, `noise_ro`, `noise_on`, `tl_reset`, `tl_prev`,
`tl_next`, `tl_end`, `hist_phase`, `hist_prob`, `codelab_code`,
`codelab_ai_prompt`, `nested_*`, and the rest.

Changing a widget's **visible label** is fine. Changing its **key** is not.

### 6. Structural rules the tests enforce

- **Streamlit forbids nested expanders.** `lib/composer.py` works around this
  with `_palette_structural(..., nested=True)`, swapping per-op expanders for a
  selectbox. New sections inside a collapsed palette must follow that pattern.
- `timeline_strip.py` must contain **no** `st.expander` and **no** `st.button`.
  The timeline builds automatically; the old "Build / refresh timeline" button
  is exactly what used to blank the composer.
- The Operations list must never be collapsed.
- Every page keeps `st.set_page_config(..., layout="wide")`. Streamlit only
  honours it in the script it runs, and pages can be opened directly, so a
  missing call makes that page render in a narrow column.

### 7. Backend and infrastructure are out of scope

Nothing under `backend/`, and no changes to `docker-compose.yml` or either
`Dockerfile`.

### 8. No new dependencies

`streamlit`, `plotly`, `pandas`, `numpy`, `matplotlib`, `pydantic` are
available. Do not add `streamlit-extras`, `st-styled`, component libraries or
icon packages — they inflate the deployment budget and add failure modes.
Everything below is achievable with CSS and Streamlit's own primitives.

---

## What to build

### Design system first

Create `frontend/lib/theme.py` as the single source of truth. Every page imports
it; no page repeats raw markup. It should expose roughly:

```python
inject_css()                                  # once per page, idempotent
page_header(title, subtitle=None, icon=None)  # consistent page opener
section(title, description=None)              # consistent section heading
card(...)                                     # bordered content container
status_pill(label, tone)                      # ok / warn / error / neutral
```

Define design tokens as CSS custom properties on `:root` — colour ramp, spacing
scale, radii, shadows, type scale — then use those variables everywhere rather
than scattering hex codes. A reviewer should be able to change the accent colour
in one place.

Specifics worth getting right:

- **Typography.** One imported family (Inter or IBM Plex Sans) for UI, plus a
  monospace family (JetBrains Mono or IBM Plex Mono) for code, QASM and
  bitstrings. Establish a real type scale; do not leave everything at default
  weight and size.
- **Colour.** A dark neutral ramp with one accent. Quantum-appropriate, but
  restrained — avoid the neon-purple-on-black cliché. Ensure body text hits
  **WCAG AA (4.5:1)**; judges often view on a projector with poor contrast.
- **Density.** Streamlit's defaults are loose and repetitive. Tighten vertical
  rhythm, but keep comfortable reading measure for lesson text.
- **The chrome.** Style `stHeader`/`stToolbar` and the sidebar deliberately
  rather than leaving stock Streamlit furniture on screen.

### Page by page

- **`Home.py`** — currently a title and a paragraph. Make it a genuine landing
  page: a hero stating what the platform does, cards linking to the five
  sections, and a clear "start here" path for a first-time student.
- **`1_Learn.py`** — lesson reader beside an AI tutor. Improve reading comfort:
  measure, heading rhythm, clear separation of lesson text from chat. Make the
  chat actually look like a chat (message bubbles, distinct roles).
- **`2_Composer.py`** — the densest page, and the one judges will study longest.
  It currently stacks timeline, editor, palette, run settings, noise settings,
  analysis, results tabs and seven export tabs with no hierarchy. Impose one, so
  a newcomer immediately perceives **build → run → results** and advanced
  controls recede. **Respect the container ordering in constraint 3.**
- **`3_Challenges.py`** — make the list scannable: difficulty, concept tags, and
  whether the user has already passed.
- **`4_Dashboard.py`** — student progress and instructor view. Metrics legible
  at a glance; roster easy to scan.
- **`5_Code_Lab.py`** — editor, AI generation panel, build, run. Should feel
  like an IDE pane, not a web form.

### Cross-cutting

- Consistent page headers everywhere.
- A sidebar that clearly shows who is signed in, their role, and where they are.
- Replace ad-hoc emoji headings with one consistent icon treatment.
- Button hierarchy: one primary action per view, everything else secondary.
- Empty states that guide the user rather than just stating emptiness.
- Loading and error states that feel intentional, not alarming.

---

## Method

1. Read `frontend/pages/2_Composer.py` and `frontend/lib/composer.py` in full
   before editing. The Composer is the most constrained page.
2. Build `theme.py` first and apply it to `Home.py`. Get one page genuinely
   right, then propagate the pattern.
3. Work one page at a time, running the tests after each.
4. Prefer layout primitives (`st.columns`, `st.container`, `st.tabs`) plus CSS
   over restructuring logic. If a change appears to need a control-flow rewrite,
   stop — the goal is presentation.
5. Inject CSS exactly once per page via the shared helper. Do not sprinkle
   `st.markdown("<style>")` blocks through the pages.

## Verification — run after every page

```
cd backend  && PYTHONPATH=. ../.venv/bin/python -m pytest -q
cd frontend && PYTHONPATH=../backend:. ../.venv/bin/python -m pytest -q
```

Expected: **324 backend, 192 frontend, 0 failures**. A frontend failure almost
always means a `key=`, a container ordering, or the expander rule was broken.

Then check by eye with `docker compose up -d --build`, at
`http://localhost:8501`:

- Every page renders, none in a narrow column.
- **Composer: the drag-and-drop grid is visible and not a blank white box.**
  This is the single most important check. Blank means the element ordering
  above the component changed.
- Raise qubits to 5, drop back to 2 — the grid keeps working.
- Run a Bell pair on Qiskit Aer: histogram shows roughly 50/50 on `00` and `11`.
- Bloch sphere, Q-sphere, phase disk and density matrix look **pixel-identical**
  to before.

## Deliverable

A genuinely professional interface whose behaviour is byte-for-byte unchanged.
In your summary, list what you restyled and explicitly call out anything you
chose to leave alone. If you are ever unsure whether something is presentation
or behaviour, leave it and say so.
