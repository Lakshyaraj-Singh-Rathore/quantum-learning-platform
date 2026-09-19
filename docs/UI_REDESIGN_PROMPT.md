# UI redesign brief for QuantumLearn

Paste everything below the line into Antigravity.

---

## Context

You are restyling the user interface of **QuantumLearn**, a Streamlit + FastAPI
quantum computing learning platform. The application is finished and working:
**516 tests pass**. Your job is **presentation only**. Treat every computation,
plot and API call as read-only infrastructure you must not disturb.

Stack: Python 3.11, Streamlit 1.41.1, Plotly, a custom React/TypeScript
drag-and-drop component, FastAPI backend reached over HTTP.

Repository layout that matters to you:

```
frontend/
  Home.py                 98 lines   landing page
  pages/
    1_Learn.py           116 lines   lesson reader + AI tutor
    2_Composer.py        487 lines   circuit editor, run, results, exports
    3_Challenges.py      163 lines   coding challenges
    4_Dashboard.py       189 lines   student + instructor dashboards
    5_Code_Lab.py        275 lines   write code, build circuit, run
  lib/
    viz.py              1236 lines   ALL plots.        DO NOT TOUCH
    composer.py          638 lines   Python grid editor + palette
    timeline_strip.py    117 lines   step-through transport bar
    api_client.py        320 lines   HTTP calls.       DO NOT TOUCH
    auth.py              108 lines   login/register/sidebar
    bootstrap.py          36 lines   sys.path shim.    DO NOT TOUCH
  circuit_composer/                  React component.  DO NOT TOUCH
.streamlit/config.toml               theme lives here
```

---

## Absolute constraints — breaking any of these breaks the product

### 1. Do not modify `frontend/lib/viz.py` at all

Every visualisation lives here and each one is verified against analytic
physics. The Bloch sphere alone has 23 tests pinning it to exact values
(`|0>` at theta=0, `T|+>` at phi=45 degrees, Bell qubits collapsing to the
origin). These are **not** decorative charts; a cosmetic change can silently
teach wrong physics.

Do not touch, restyle, recolour, resize or "modernise" any of:

```
histogram            probability_table    phase_disk        qsphere
amplitude_table      bloch_sphere         circuit_diagram   backend_badge
gauge                metric_meters        ideal_vs_noisy    born_vs_shots
density_matrix       statevector_ket      phase_table
reduced_density_matrix   bloch_vector     bloch_angles
```

You may change **where a chart is placed** on the page (which column, tab or
container it sits in). You may not change **what it draws**.

### 2. Do not modify `frontend/lib/api_client.py`

Read-only endpoints are memoised with `@st.cache_data`; mutating ones
(`submit_job`, `save_circuit`, `import_qasm`) are deliberately **not** cached,
because caching a job submission would re-spend real qBraid credits. Adding or
removing a decorator here causes either a stale UI or a billing bug.

### 3. Do not modify `frontend/circuit_composer/`

The React drag-and-drop component. It took several attempts to stop it
rendering as a blank white iframe. Two failure modes you must not reintroduce:

- **Element-path remounting.** Streamlit addresses a custom component by its
  position in the element tree. If the number of widgets *above* the component
  changes, Streamlit destroys and recreates the iframe, the component misses
  Streamlit's one-shot RENDER event, and it paints blank white with no console
  error. `2_Composer.py` therefore allocates `timeline_slot`, `divider_slot`
  and `composer_slot` as containers **before** filling them, and fills the
  composer first. **Keep that pattern.** If you add anything above the
  composer, it must go inside `timeline_slot`, not before it.
- **React.StrictMode.** Never wrap the component in it. StrictMode double-mounts,
  the RENDER listener is torn down mid-delivery, and the iframe stays blank.

### 4. Preserve every `st.session_state` key exactly

Renaming any of these loses user state or breaks cross-page flows:

```
token  user  access_token
circuit  last_job_id  last_job_circuit  last_job_qubits
timeline  timeline_signature  tl_step
codelab_code  codelab_framework  codelab_built  codelab_job_id
```

### 5. Preserve every widget `key=` value

There are 64 of them and the test suite and session state both depend on them.
Examples: `react_composer`, `noise_t1`, `noise_t2`, `noise_ro`, `noise_on`,
`tl_reset`, `tl_prev`, `tl_next`, `tl_end`, `hist_phase`, `hist_prob`,
`codelab_code`, `codelab_ai_prompt`, `nested_*`.

You may change a widget's **visible label**. You may not change its **key**.

### 6. Do not touch any backend file

Nothing under `backend/`, and no change to `docker-compose.yml` or either
`Dockerfile`. This is a frontend-only task.

### 7. Structural rules the tests enforce

- **Streamlit forbids nested expanders.** `lib/composer.py` works around this
  with `_palette_structural(..., nested=True)`, which swaps per-op expanders
  for a selectbox. Any new section inside a collapsed palette must follow the
  same pattern. `test_no_nested_expanders.py` checks this.
- `timeline_strip.py` must contain **no** `st.expander` and **no** `st.button`.
  The timeline builds automatically; the old "Build / refresh timeline" button
  is what used to blank the composer.
- The Operations list must never be collapsed.
- Every page must keep `st.set_page_config(..., layout="wide")`. Streamlit only
  honours it in the script it runs, and each page can be opened directly — a
  missing call makes that page render in a narrow column.

---

## What you should change

Everything cosmetic. Be ambitious here.

### Visual language

Design a coherent dark theme appropriate to a quantum computing platform. The
current look is default Streamlit with ad-hoc emoji headings and inconsistent
spacing. Aim for something closer to IBM Quantum Composer or a modern developer
tool: restrained palette, deliberate typography, generous whitespace, clear
hierarchy.

Set the palette in `.streamlit/config.toml` under `[theme]` and inject any
additional CSS with a single `st.markdown(..., unsafe_allow_html=True)` block
in a shared helper so it is defined once, not per page.

**Constraint:** the theme must stay **dark-based** (`base = "dark"`). The React
composer reads `theme.base` and toggles a `dark` CSS class; a light theme would
leave it visually inconsistent with the rest of the page.

### Per page

- **`Home.py`** — currently a plain title and a paragraph. Make it a real
  landing page: a hero that says what the platform does, cards linking to the
  five sections, and a short "start here" path for a first-time student.
- **`1_Learn.py`** — lesson reader beside an AI tutor chat. Improve reading
  comfort: line length, heading rhythm, visible separation between the lesson
  text and the chat. Make the chat look like a chat.
- **`2_Composer.py`** — the densest page and the one judges will look at
  longest. It currently stacks: timeline, editor, palette, run settings, noise
  settings, analysis, results tabs, seven export tabs. Impose hierarchy so a
  newcomer sees *build → run → results* and the advanced controls recede.
  **Respect the container ordering described in constraint 3.**
- **`3_Challenges.py`** — make the challenge list scannable: difficulty,
  concept tags, and whether the user has passed.
- **`4_Dashboard.py`** — student progress and the instructor view. Make the
  metrics legible at a glance and the instructor roster easy to scan.
- **`5_Code_Lab.py`** — code editor, AI generation panel, build, run. Make it
  feel like an IDE pane rather than a form.

### Cross-cutting

- Consistent page headers so every page announces itself the same way.
- A clearer sidebar: who is logged in, their role, where they are.
- Replace scattered emoji headings with a consistent icon treatment.
- Consistent spacing scale and button hierarchy (primary vs secondary).
- Empty states that guide rather than just saying nothing is here.
- Error and warning styling that is calm and readable, not alarming.

---

## Method

1. Read `frontend/pages/2_Composer.py` and `frontend/lib/composer.py` fully
   before editing anything. The Composer is the most constrained page.
2. Introduce a shared `frontend/lib/theme.py` exposing something like
   `inject_css()`, `page_header(title, subtitle, icon)` and `section(title)`.
   Call it from each page instead of repeating markup.
3. Work one page at a time. After each page, run the tests below.
4. Prefer layout primitives (`st.columns`, `st.container`, `st.tabs`) and CSS
   over restructuring logic. If a change needs a control-flow rewrite, stop and
   reconsider — the goal is presentation.
5. Do not add dependencies. `streamlit`, `plotly`, `pandas`, `numpy`,
   `matplotlib` and `pydantic` are already available; anything else breaks the
   deployment budget.

---

## Verification — run after every page

```
cd backend && PYTHONPATH=. ../.venv/bin/python -m pytest -q
cd frontend && PYTHONPATH=../backend:. ../.venv/bin/python -m pytest -q
```

Expected: **324 backend, 192 frontend, 0 failures**. A frontend failure almost
always means a `key=`, a container ordering, or an expander rule was broken.

Then check by eye, with the stack running:

```
docker compose up -d --build
```

- `http://localhost:8501` — every page renders, none in a narrow column.
- **Composer**: the drag-and-drop grid is visible and **not a blank white box**.
  This is the single most important check. If it is blank, you changed the
  element ordering above the component.
- Raise qubits to 5, drop back to 2 — the grid keeps working.
- Run a Bell pair on Qiskit Aer — the histogram shows roughly 50/50 on `00`
  and `11`, and every results tab still renders.
- Bloch, Q-sphere, phase disk and density matrix look **exactly** as before.

---

## Deliverable

A restyled interface where the underlying behaviour is byte-for-byte identical.
If you are ever unsure whether something is presentation or behaviour, leave it
alone and say so in your summary.
