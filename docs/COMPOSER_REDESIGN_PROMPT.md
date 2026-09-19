# Circuit Composer redesign brief — IBM Quantum Composer layout

Paste everything below the line into your AI coding agent.

---

# Task: rebuild the circuit composer UI to match IBM Quantum Composer

You are the design engineer on **QuantumLearn**. The drag-and-drop circuit
composer is a custom React/TypeScript component embedded in a Streamlit page.
It works correctly but looks like a prototype: a toolbar, then a row of gate
chips, then the circuit grid, all stacked vertically down the page.

Rebuild it to look and feel like **IBM Quantum Composer**: a three-column
application shell with a docked gate palette on the left, the circuit canvas in
the middle with its own toolbar, and a live code pane on the right.

**This is a layout and styling task.** All circuit logic, drag-and-drop
behaviour, IR handling and Streamlit communication must survive unchanged.

---

## Target layout

```
┌──────────────┬──────────────────────────────────────┬──────────────┐
│ Operations   │  ↶ ↷   Left alignment ▾   ◯ Inspect  │  OpenQASM  ▾ │
│ 🔍  ☰  ⇤     ├──────────────────────────────────────┤              │
│              │                                      │ 1 OPENQASM 3 │
│ [H][⊕][⊖]... │  q[0] ──────────────────────────◯    │ 2 include    │
│ [T][S][Z]... │                                      │ 3            │
│ [RZ][⌁][|0⟩] │  q[1] ──────────────────────────◯    │ 4 qubit[4] q │
│ [for][while] │                                      │ 5 bit[4] c   │
│ [RY][◕]      │  q[2] ──────────────────────────◯    │ 6            │
│              │                                      │ 7            │
│              │  q[3] ──────────────────────────◯    │              │
│              │   c4  ═══════════════════════════    │              │
└──────────────┴──────────────────────────────────────┴──────────────┘
```

Reference details to reproduce:

- **Left rail, "Operations"** — a docked panel with a small header row
  (search icon, list-view icon, collapse icon), then gate tiles laid out in a
  dense grid roughly 6 per row. Tiles are small rounded squares, colour-coded
  by family, showing the gate symbol only. Hovering reveals a tooltip with the
  full name.
- **Centre, canvas** — its own toolbar containing undo, redo, an alignment
  dropdown, and an "Inspect" toggle switch. Below it, the circuit: qubit labels
  `q[0]`, `q[1]`, … in a fixed left gutter, horizontal wires running the full
  width, a classical register drawn as a **double line** labelled `c4`, and
  terminal measurement symbols as circles at the right end of each wire.
- **Right, code pane** — a collapsible panel headed "OpenQASM" with a dropdown,
  showing gutter line numbers and syntax-highlighted QASM 3 that updates as the
  circuit changes.
- **Overall** — dark theme, thin 1px separators between the three regions, no
  rounded outer card. The whole thing reads as one application surface, not
  three stacked widgets.

---

## The codebase

```
frontend/circuit_composer/frontend/src/
  Composer.tsx     509 lines   top-level: toolbar, palette, state, commit
  Grid.tsx         301 lines   the circuit canvas (absolute-positioned)
  BlockEditor.tsx  353 lines   nested if/for/while/box editor
  ir.ts            254 lines   IR manipulation helpers
  types.ts         173 lines   PALETTE definitions and types
  index.tsx         66 lines   mount + Streamlit handshake.  DO NOT TOUCH
  styles.css       409 lines   all styling — expect to rewrite this
```

Build with:

```
cd frontend/circuit_composer/frontend && npm ci && npm run build
```

Vite emits into `build/`, which `frontend/circuit_composer/__init__.py` serves
to Streamlit. **`npm run build` runs `tsc --noEmit` first, so the TypeScript
must type-check or there is no build.**

### Everything you need already exists

Do not invent new gates. `types.ts` already defines the full palette, and every
symbol visible in the reference screenshot maps to an existing entry:

- `PALETTE` — H, X, Y, Z, I, S, S†, T, T†, √X, P(λ), RX(θ), RY(θ), RZ(θ)
- `MULTI_PALETTE` — CNOT, Toffoli, MCX, SWAP, Control+
- `STRUCTURAL_PALETTE` — Measure, Reset, Barrier
- `BLOCK_PALETTE` — If/Else, For, While, Box

Each item already carries `label`, `hint` and `color`. Your job is to present
them as a dense tile grid instead of a wrapped row of pill chips, and to group
them sensibly.

---

## Hard constraints — violating these breaks a working product

### 1. Do not touch `src/index.tsx`

It contains the Streamlit handshake, which took four attempts to get right:

- `Streamlit.setFrameHeight` is wrapped to clamp every reported height to
  `MIN_FRAME_HEIGHT = 560`. The library calls it with no argument, which
  defaults to `document.body.scrollHeight`; before layout settles that is `0`,
  Streamlit collapses the iframe, and the component renders as a **blank white
  box with no console error**.
- The component is deliberately **not** wrapped in `React.StrictMode`.
  StrictMode double-mounts, the RENDER listener is torn down mid-delivery, and
  the iframe stays blank forever.
- A watchdog polls `root.childElementCount` and re-announces readiness if the
  component is ever blank.

If you change the layout to something taller or shorter, adjust
`MIN_FRAME_HEIGHT` **only**, and leave the rest alone.

### 2. Keep the component's contract with Python identical

`Composer.tsx` receives `args.value` (a CircuitIR dict) and `args.nQubits`, and
returns the edited IR via `Streamlit.setComponentValue`. The Python side
(`frontend/circuit_composer/__init__.py`, unchanged) passes
`value=ir.to_dict(), n_qubits=..., key="react_composer"`.

- The IR shape must not change. Keys: `name`, `n_qubits`, `n_clbits`, `ops`,
  and per-op `id`, `kind`, `gate`, `qubits`, `controls`, `clbits`, `params`,
  `body`, `else_body`, `layer`.
- **Keep the 250 ms debounce** on `setComponentValue`. Every call triggers a
  full Streamlit rerun; committing on each click made the qubit buttons feel
  laggy. Measured: 9 HTTP calls and 708 ms per interaction before, 1 call and
  62 ms after.
- **Keep the `n_clbits` logic.** `requiredClbits()` must not fold in the current
  `ir.n_clbits`; doing so makes the register a one-way ratchet, and a circuit
  taken from 2 → 11 → 2 qubits keeps printing 11-character bitstrings.
  `measureAllAppend` must size the register from the circuit *including* the
  measurements it just added.

### 3. Preserve every behaviour in the current component

- Drag a gate from the palette onto a cell, **or** click to arm a tool then
  click a cell.
- MCX flow: drop the gate on the target qubit, then click control qubits in the
  same column.
- Collision policy is **global auto-insert-column**: if a cell is occupied,
  every op at `layer >= t` shifts right. Not local shifting.
- Nested block editing via `BlockEditor.tsx` for if/else, for, while and box.
- Parameter entry accepts only `pi`, numbers and `+ - * / ( )`.
- "Measure All (Append)" never deletes; "Normalize Terminal Measurement" is
  top-level only and must never touch measurements inside nested blocks.
- Qubit count is capped at 15.

### 4. Theme

The component reads `theme.base` from Streamlit and toggles a `dark` class on
`document.body`. Keep that. The palette in `styles.css` is currently
`:root { --bg: #ffffff }` with `body.dark { --bg: #0e1117 }` — keep the CSS
variable structure so both themes still work, even though dark is the default.

### 5. No new dependencies

React 18, TypeScript 5.7 and Vite 6 are available. Do not add a component
library, an icon package or a CSS framework. Icons in the reference are simple
enough to draw as inline SVG. Adding packages inflates a bundle that is already
349 kB and must load inside a Streamlit iframe.

### 6. Do not touch anything outside `frontend/circuit_composer/frontend/src/`

Specifically not `frontend/pages/2_Composer.py`, whose container ordering
(`timeline_slot`, `divider_slot`, `composer_slot`) is what stops Streamlit
remounting the iframe, and not `frontend/lib/viz.py`, which holds
physics-verified plots.

---

## What to build

### The three-column shell

Replace the `flex-direction: column` stack in `.composer` with a CSS grid:

```css
.composer {
  display: grid;
  grid-template-columns: 220px 1fr 300px;
  grid-template-rows: 1fr;
}
```

Both side panels collapse: the left to an icon rail, the right to a thin strip
with a chevron. Below roughly 900 px the grid should fall back to a single
column with the palette above the canvas, because the component is embedded in
a Streamlit page whose width follows the browser window.

### Left rail — Operations

- Header row: title "Operations" plus three icon buttons (search, list view,
  collapse) as inline SVG.
- Search filters tiles live by `label` and `hint`.
- Tiles in a dense grid, around 34 px square, 6 per row, `border-radius: 6px`,
  colour from the palette entry, hover raises slightly, dragging dims.
- Group headings: Gates, Multi-qubit, Operations, Control flow. Sections
  collapsible.
- The whole rail scrolls independently of the canvas.

### Centre — canvas

- Toolbar: undo, redo, alignment dropdown, Inspect toggle. **Undo/redo are new
  UI over existing state** — implement as a bounded history stack of IR
  snapshots (cap it, say 50 entries) in `Composer.tsx`. Do not persist history
  across Streamlit reruns.
- Wires: qubit labels in a fixed gutter, `q[0]` style, monospace. The classical
  register renders as a **double horizontal line** labelled `c4`.
- Terminal measurement circles at the right end of each wire.
- The canvas scrolls horizontally while the gutter stays pinned.
- Keep `Grid.tsx`'s absolute positioning maths (`CELL = 46`, `GUTTER = 62`).
  Restyle the cells; do not rewrite the coordinate system, because block
  rendering and control-line drawing depend on it.

### Right — code pane

- Header "OpenQASM" with a dropdown (OpenQASM 3 is the only live option; the
  dropdown can be a visual affordance).
- Gutter line numbers, monospace, syntax highlighting for keywords, types,
  numbers and comments. Hand-roll it with a small regex tokeniser — do not add
  a highlighting library.
- **Generate the QASM client-side from the IR.** The component must not call
  the backend: it has no API client and adding one would break the Streamlit
  sandbox model. A straightforward serialiser covering the supported gate set is
  enough; label it clearly as a preview, since
  `frontend/pages/2_Composer.py` still offers authoritative server-side export.
- Collapsible to a narrow strip.

---

## Method

1. Read `Composer.tsx`, `Grid.tsx` and `types.ts` in full before editing.
2. Restructure `styles.css` around design tokens on `:root` — colour ramp,
   spacing scale, radii, type scale — then build the shell.
3. Move the palette into the left rail without changing drag handlers.
4. Add the canvas toolbar, then undo/redo.
5. Add the code pane last; it is additive and lowest risk.
6. Run `npm run build` after every step. TypeScript must pass.

## Verification

```
cd frontend/circuit_composer/frontend && npm run build
```

Then rebuild the stack and check at `http://localhost:8501` → Composer
(hard-refresh with Ctrl+Shift+R, because Vite fingerprints the bundle):

- **The grid renders and is not a blank white box.** Most important check. If
  blank, the frame-height clamp or the Streamlit handshake was disturbed.
- Drag H onto q[0]; click-to-place also works.
- CNOT: drop on target, then click a control in the same column.
- Raise qubits to 5 and drop back to 2 — no stale wires, no stale clbits.
- "Measure All (Append)" adds one measurement per qubit.
- Edit a nested if-block via BlockEditor.
- Run a Bell pair from the Streamlit page: histogram shows roughly 50/50 on
  `00` and `11`.
- Undo reverts the last placement; redo reapplies it.
- Narrow the browser to ~800 px: the layout falls back to one column and
  nothing overflows.

Python-side tests must still pass:

```
cd frontend && PYTHONPATH=../backend:. ../.venv/bin/python -m pytest -q
```

Expected: **192 passed, 3 skipped**.

## Deliverable

A circuit composer that looks like professional quantum software, with every
existing behaviour intact. In your summary, state what you restyled, what you
added (undo/redo and the code pane are genuinely new), and anything you chose
to leave alone.
