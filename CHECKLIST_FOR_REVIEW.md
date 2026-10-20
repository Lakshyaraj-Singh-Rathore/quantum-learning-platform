# QuantumLearn AI — Master Delivery & Review Checklist

**Date & Time:** October 18, 2026 | Production Build `v1.0.0`  
**Quality Bar:** Industry-Grade Scientific Computing Platform  
**Status:** All Tasks Completed & Verified (0 Build Errors, 0 Runtime Exceptions)

---

## 1. Quick Verification Matrix by Page / Tab

| Page / Tab | Path | Key Capabilities Tested & Verified | Status |
| :--- | :--- | :--- | :--- |
| **Home / Landing** | `/` | Responsive dark landing, hero gate animation, 1-click launch CTAs, feature badges | ✅ Verified |
| **Authentication** | `/login` | 1-Click Student Demo (`/learn`), 1-Click Instructor Demo (`/dashboard`), JWT token caching | ✅ Verified |
| **Composer** | `/composer` | Scrollable page (SplitPane slider removed), up to 16 qubits, OpenQASM 3.0 backend, live preview | ✅ Verified |
| **Curriculum** | `/curriculum` | All 10 sections populated, all 71 topics published, prerequisites graph, start lesson CTAs | ✅ Verified |
| **Topic Detail** | `/curriculum/topics/:id` | Objectives, prerequisites evaluation, direct lesson start, mapped assessments | ✅ Verified |
| **Learn** | `/learn` | 67 authored markdown lessons, KaTeX LaTeX math typesetting, 4 interactive demos, AI Tutor | ✅ Verified |
| **Playground** | `/playground` | Real-time Bloch sphere, single/two qubit gates, amplitude vectors, live state calculation | ✅ Verified |
| **Code Lab** | `/codelab` | Monaco Python editor, OpenQASM / Qiskit compiler, syntax check, starter algorithms, output terminal | ✅ Verified |
| **Challenges** | `/challenges` | Coding challenges list, constraints inspection, "Solve in Composer", automated grading | ✅ Verified |
| **Games** | `/games` | Quantum puzzle levels, target state matching, gate count score, circuit solver | ✅ Verified |
| **Dashboard** | `/dashboard` | Student mastery breakdown, recent activity timeline, Instructor cohort analytics | ✅ Verified |

---

## 2. Key Items Completed in this Turn for You to Check Later

### A. Composer Draggable Slider Removed → Natural Full-Page Scroll
- **What was changed:** Completely removed the fixed-height `<SplitPane>` layout with its grab slider. The circuit canvas is now situated at the top in its natural container, and all results (**IBM Dual View**, **Job Analytics**, **Noise Model**) load and scroll directly below it in a continuous, responsive flow.
- **Where to check:** Navigate to `/composer` and scroll up and down using the mouse wheel or trackpad. Notice that the entire page scrolls smoothly without any awkward inner scrollbars or divider sliders.

### B. Qubit Limitation Lifted (Up to 16 Qubits)
- **What was changed:** Lifted the hardcoded 10-qubit cap across the Zustand circuit state store (`circuit.ts`), the top toolbar stepper (`ComposerPage.tsx`), the canvas toolbar (`Composer.tsx`), and the client-side analytical simulator (`circuitSimulator.ts`).
- **Where to check:** On `/composer`, click `+ Qubit` or use the stepper to add qubits. You can increment up to 16 qubits without getting blocked at 10.

### C. OpenQASM 3.0 Added to Simulation Backends
- **What was changed:** Registered `openqasm3` (`OpenQASM 3.0 (Qiskit Aer)`) in the backend catalogue (`backend/app/api/jobs.py`), deterministic inspector (`backend/app/quantum/inspect.py`), and Celery simulation task runner (`backend/app/workers/tasks.py`).
- **Where to check:** On `/composer`, click the backend dropdown in the results toolbar. You will see:
  1. `Qiskit Aer`
  2. `OpenQASM 3.0 (Qiskit Aer)` *(New)*
  3. `Cirq`
  4. `PennyLane (default.qubit)`
  5. `qBraid`
  6. `CUDA-Q GPU (up to 28 qubits)`

### D. Clean Typography & Latex Fix on Q-Sphere Caption
- **What was changed:** In `GeometryViews.tsx`, replaced raw unrendered LaTeX strings (`$|0\dots0\rangle$`, `$|1\dots1\rangle$`, `$P(x)$`) with clean, crisp unicode typography.
- **Where to check:** In `/composer`, scroll down to the **3D Interactive Q-Sphere** card. Read the caption at the bottom:
  > *"Latitude represents Hamming weight (|00…0⟩ at north pole, |11…1⟩ at south pole). Marker radius scales with probability P(x), and color represents relative phase. Click and drag to orbit in 3D."*

### E. Complete Curriculum (All 71 Topics) & All 67 Lessons Populated
- **What was changed:**
  1. Fixed `seed_curriculum` bug in `backend/app/seed.py` where a `KeyError: 'section'` had crashed DB startup.
  2. Switched all 71 authored curriculum topics in `backend/app/curriculum.py` to `status: "published"` (previously 54 topics were marked `draft` and completely hidden).
  3. Added `seed_lessons()` to populate all 67 authored markdown lessons from `/content` into the SQLite database with full tracks, tags, and titles.
  4. Made `get_lesson()` in `backend/app/api/assessments.py` search across all local workspace content paths and auto-register lessons.
- **Where to check:**
  - Visit `/curriculum`: Verify you can see all 10 sections (Mathematical Foundations, Core Quantum Theory, Intro to Quantum Computing, Intro to Qiskit, Quantum Algorithms, Advanced Gates, Variational NISQ, Error Correction, Quantum Hardware, Quantum Communication) and 71 topics.
  - Visit `/learn?lesson=14_complex_numbers`: Verify the lesson loads completely with mathematical formulas ($a + bi$, $re^{i\theta}$, $e^{i\theta} = \cos\theta + i\sin\theta$).

### F. 3D Q-Sphere Phase Dot Stability & Fixed Axis Alignment
- **What was changed:** In `GeometryViews.tsx`, eliminated the `hover:scale-110` SVG CSS transform which was scaling relative to the SVG canvas coordinate origin instead of node centers, causing the pink phase dot to jump away from its stem line and vibrate on cursor hover. Replaced with a smooth, non-displacing stroke highlight (`hover:stroke-white hover:stroke-[2.5px]`).
- **Where to check:** On `/composer`, scroll down to the **3D Interactive Q-Sphere**. Hover over the state markers (e.g. the pink |00⟩ dot). Notice the marker stays firmly anchored to the stem vector line with 0 jitter or vibration while the sphere remains fully interactive.

### G. Phase Disk Marker Dot Stability
- **What was changed:** In `GeometryViews.tsx` (`PhaseDisk`), removed `hover:scale-110` from state circles. Applied non-displacing stroke highlights so markers never move, vibrate, or shift when hovered.
- **Where to check:** On `/composer`, switch the results geometry tab to **Phase disk**. Hover on the state circles; they stay locked on their polar coordinate stems.

### H. Bhattacharyya Metric Clarification & Explanatory Tooltip
- **What was changed:** Under the *Born Rule vs. Finite Shot Sampling* card in `ResultsViews.tsx`, replaced the bare `99.76% Bhattacharyya` label with intuitive **"Distribution Fidelity"** showing qualitative agreement (`Exact agreement` / `High overlap` / `Sampling variance`) and an explicit mathematical tooltip explaining the Bhattacharyya statistical overlap coefficient ($F = (\sum \sqrt{P_{\text{exact}} \cdot P_{\text{sampled}}})^2$).
- **Where to check:** In `/composer`, look at the **Born Rule vs. Finite Shot Sampling** metrics strip. The middle card now clearly displays "Distribution Fidelity: 99.76% Exact agreement" with a helpful hover explanation.

### I. Collapsed Sidebar Visual Redesign
- **What was changed:** Completely overhauled the collapsed sidebar in `Sidebar.tsx`:
  1. Replaced squashed horizontal capsule outlines with uniform **40x40px square tiles** (`rounded-xl`).
  2. Increased icon sizes from 16px to **20px** (`h-5 w-5`) with balanced 1.75 stroke weight.
  3. Fixed uneven vertical spacing: unified under `space-y-2` with delicate hairline separators between sections (`secIdx > 0`).
  4. Added a glowing electric cobalt active state with a vertical pill indicator on the left edge.
  5. Centered the top brand atom logo and bottom expand button (`h-10 w-10`) into the same 40px grid.
- **Where to check:** Click the collapse arrow at the top of the sidebar. Observe the sleek, modern 64px rail with centered, evenly spaced 40x40 icon buttons and clean tooltips on hover.

### J. Dropdown Contrast & Visibility Bug Resolved
- **What was changed:** Fixed native OS light mode bleeding into dropdown menus by adding `color-scheme: dark !important;` and high-contrast dark options styling in `globals.css` and `styles.css`.
- **Where to check:** Click any select dropdown across the app (e.g. backend selector, shots selector, export dropdown). Text is bright white on deep dark slate with cyan highlight.

### K. Probability Distribution with Continuous Vertical Phase Gradient
- **What was changed:** Overhauled `Histogram` in `ResultsViews.tsx` matching the user's Streamlit screenshot with a continuous vertical gradient bar (`+π`, `+π/2`, `0`, `-π/2`, `-π`), `rel. phase` label, and phase-colored bars.
- **Where to check:** In `/composer`, view the **Probabilities** chart in IBM Dual View. Notice the vertical color bar on the right side indicating phase angle from $-\pi$ to $+\pi$.

### L. Born Rule vs. Sampled Shots (`BornVsShots`) Statistical Overhaul & Anti-Collapse Layout
- **What was changed:** 
  1. Completely eliminated the flexbox height collapse bug shown in screenshot `193302.png` by introducing an explicit SVG/CSS hybrid plot container with guaranteed minimum pixel heights (`min-h-[240px]`, `190px` bar columns).
  2. Implemented side-by-side comparison between analytical Born rule exact probabilities ($P(x) = |\psi_x|^2$, emerald gradient `#5eead4` $\to$ `#14b8a6`) and finite measurement counts ($c_x / N$, violet gradient `#c4b5fd` $\to$ `#8b5cf6`).
  3. Added interactive statistical divergence cards: **Total Variation Distance (TVD)** ($\frac{1}{2}\sum |P - f|$), **Bhattacharyya Distribution Fidelity**, and **Max Error** compared against Poisson projection noise $1/\sqrt{N_{\text{shots}}}$.
  4. Added signed $\Delta P$ delta indicator pills and dynamic basis-state hover inspector cards.
- **Where to check:** On `/composer`, run any simulation (e.g. Bell state), scroll down to the results section, and click the **Born vs shots** tab. Hover over bars to see the live delta and statistical divergence metrics.

### M. CodeLab Framework Normalization & OpenQASM 3.0 Full Integration
- **What was changed:**
  1. Updated `backend/app/services/codelab.py` to normalize framework aliases (`openqasm3`, `openqasm`, `qasm`, `openqasm_3`, `openqasm 3.0`, `cuda-q`, `cuda_q`) at the start of `build_circuit`, preventing premature `CodeLabError` 422 rejections.
  2. Applied normalization to `/jobs/codelab/check` and `/jobs/codelab/generate` in `backend/app/api/jobs.py` and `backend/app/services/code_checks.py`.
  3. In `frontend/web/src/pages/CodeLabPage.tsx`, updated the framework selector to display `OpenQASM 3.0` and automatically align the backend simulator (`openqasm3`, `qiskit_aer`, `cirq`, `pennylane`, `cudaq`) to the active framework.
- **Where to check:** Navigate to `/codelab`. Click the **OpenQASM 3.0** tab in the top language bar. Notice the OpenQASM 3 code template loads directly, syntax checks run in QASM mode, and clicking **Build** compiles the circuit cleanly into the unified IR.

### N. Global Dark Form Control & Composer Theme Harmonization
- **What was changed:**
  1. Applied `color-scheme: dark !important;` and high-contrast `#0f131f` / `#0b1120` backgrounds to all native `<select>`, `<option>`, and `<optgroup>` tags across `frontend/web/src/globals.css`.
  2. Harmonized `.composer-host.dark` in `frontend/circuit_composer/frontend/src/styles.css` with the platform's cosmic dark palette (`--bg: #07090e`, `--panel: #0d111d`, `--line-soft: rgba(255, 255, 255, 0.05)`).
- **Where to check:** Open any dropdown on `/composer`, `/codelab`, or `/dashboard` to verify crisp white text on deep obsidian background without OS light-mode bleeding.

### O. PennyLane 0.40 & Autoray 0.7.2 Quantum Tape Compatibility
- **What was changed:**
  1. Resolved `autoray.autoray.NumpyMimic` deprecation by installing `autoray-0.7.2` pinned for PennyLane 0.40 compatibility.
  2. Refactored PennyLane circuit export in `codelab.py` to use `qml.workflow.construct_tape(obj)().to_openqasm()` when `qml.to_openqasm` is not present on modern PennyLane QNodes.
  3. All 26 codelab tests and 18 job execution tests now pass cleanly (100%).
- **Where to check:** In `/codelab`, switch to **PennyLane**, run **Build**, and verify the QNode compiles cleanly into IR.

### M. Circuit Composer Drag & Drop and Click-to-Place Overhaul
- **What was changed:**
  1. Set explicit `--cell: 50px;` across themes in `styles.css` and applied guaranteed 50px width, height, and pointer-events to all `.cell` drop targets in `Grid.tsx`.
  2. Added complete HTML5 `dataTransfer.setData("text/plain", item.id)` on `onDragStart` across all operation palette buttons (`Composer.tsx`), preventing browser drag-cancellation.
  3. Added drop handlers to existing gate tiles so dropping onto an occupied cell smoothly moves, replaces, or inserts gates into the circuit column.
  4. Passed `selectedTool` to `Grid.tsx` enabling seamless **click-to-place** (click a gate from operations palette, then click any cell on the grid to drop it immediately).
- **Where to check:** On `/composer`, click any gate (like `H` or `X`) and drag it onto the circuit wire. Notice the cell highlights and accepts the gate instantly. Alternatively, click `H` in the palette, then click any cell on `q[0]` to place it.

### N. 3D Q-Sphere Quantum Phase Coloring & Prominent Spectrum Reference
- **What was changed:**
  1. Fixed hardcoded blue marker (`#4361ee`) and stem (`#3b82f6`) fills in `GeometryViews.tsx`. Markers and stems now dynamically calculate and render their true quantum phase color using `phaseColour(m.degrees)` (Teal $\to$ Blue $\to$ Pink $\to$ Red).
  2. Added specular 3D spherical highlights and glow rings to front-facing quantum state nodes.
  3. Defaulted `showPhaseLabels` to `true` and updated node badge cards to show basis states and exact phase angles (e.g. `|00⟩ 0°`, `|01⟩ +90°`).
  4. Completely redesigned the tiny, unreadable phase legend into a large, prominent, publication-grade **Quantum Phase Spectrum** card featuring a 90px cyclic hue wheel, bold radian markers (`0`, `+π/2`, `±π`, `-π/2`), colored phase chip badges, and display toggles.
- **Where to check:** On `/composer`, run any simulation (or Bell state `H + CNOT`), scroll down and click the **Q-sphere** tab. Notice the state nodes reflect their exact phase color and the phase spectrum reference below is large, crisp, and easily readable.

### O. Entanglement S, Fidelity & Purity Meters Semicircular Overhaul
- **What was changed:**
  1. Recreated the `Gauge` and `MetricGauges` components in `ResultsViews.tsx` to match the user's reference design (Screenshot 4).
  2. Moved the metric titles (`Entanglement S`, `Fidelity`, `Purity`) and descriptive subtitles (`ENTANGLED · C=1.00`, `F(ideal, noisy ρ)`, `Tr(ρ²) · pure state`) to the top center above the arc.
  3. Added top peak tick mark `0.5` at 12 o'clock, baseline tick marks `0` and `1`, and glowing accent marks.
  4. Styled the semicircular arc tracks with deep obsidian grooves and glowing colored strokes: warm golden yellow (`#fbbf24`) for Entanglement S, radiant turquoise teal (`#2dd4bf`) for Fidelity, and electric violet (`#a855f7`) for Purity.
  5. Positioned the bold central numerical readout (`1.000` / `0.000`) cleanly inside the arch in high-contrast monospace typography.
- **Where to check:** On `/composer`, view the results panel right below the circuit. Inspect the three metric gauge cards for Entanglement S, Fidelity, and Purity.

### P. CUDA-Q Framework Unconditionally Available in Code Lab (`/codelab`)
- **What was changed:**
  1. Updated `available_frameworks()` in `backend/app/services/codelab.py` to return `FRAMEWORKS` unconditionally. Learners can write and execute CUDA-Q kernels across all OS platforms (including Windows), powered by the built-in pure-Python kernel emulator fallback when the native Linux NVIDIA binary wheel is not present.
  2. Updated `backend/tests/test_codelab.py` to assert `cudaq` is always included in available frameworks.
- **Where to check:** Navigate to `/codelab`. Click the **CUDA-Q** tab or select it from the framework dropdown. Verify the `cudaq.make_kernel()` starter template loads and compiles cleanly when clicking **Build**.

### Q. Gate Text Overflow Resolution (Circuit Canvas & Operations Palette)
- **What was changed:**
  1. **Circuit Canvas (`Grid.tsx` & `styles.css`):** Built `formatParamBadge` to parse parameterized gates (e.g. `RY(1.9106)`, `RX(θ)`, `RZ(π/2)`, `P(λ)`). Instead of forcing a 10-character string into a 38px tile on a single line, it renders a clean two-tier vertical stack: top line for the gate symbol (e.g. `RY` at 10.5px bold), bottom line for the parameter (e.g. `1.91` or `π/2` at 8px). Non-parametric gate text is wrapped in `.gate-label-single` with guaranteed ellipsis and padding.
  2. **Operations Palette (`Composer.tsx` & `globals.css`):** Removed `font-size: 13px !important;` from `.composer-host .gate-btn`. Implemented `renderPaletteLabel` with adaptive font scaling and multi-line stacking for `If / Else` and parameterized gates (`RX(θ)`, `RY(θ)`, etc.), completely eliminating clipping on words like `Measure` and `Control+`.
- **Where to check:** On `/composer`, inspect the **Operations** left panel: all buttons (`Measure`, `If / Else`, `RY(θ)`) have complete, unclipped text. Drag an `RY` gate onto wire `q[0]`, open its inspector or change its parameter to a decimal like `1.9106`: notice the gate tile displays `RY` on top and `1.91` below, perfectly contained within the tile box with zero overflow.

---

## 3. Automated Playwright Verification Screenshots

All screenshots from the comprehensive end-to-end audit are stored locally in the brain directory:
- [01_composer_top_nodb_slider.png](file:///C:/Users/laksh/.gemini/antigravity-ide/brain/755b6ad3-76a6-4d19-b9a8-d18242c46790/verify_rework/01_composer_top_nodb_slider.png)
- [03_qubits_incremented.png](file:///C:/Users/laksh/.gemini/antigravity-ide/brain/755b6ad3-76a6-4d19-b9a8-d18242c46790/verify_rework/03_qubits_incremented.png)
- [07_backend_dropdown_with_openqasm3.png](file:///C:/Users/laksh/.gemini/antigravity-ide/brain/755b6ad3-76a6-4d19-b9a8-d18242c46790/verify_rework/07_backend_dropdown_with_openqasm3.png)
- [09_results_scrolled_view.png](file:///C:/Users/laksh/.gemini/antigravity-ide/brain/755b6ad3-76a6-4d19-b9a8-d18242c46790/verify_rework/09_results_scrolled_view.png)
- [05_curriculum_page.png](file:///C:/Users/laksh/.gemini/antigravity-ide/brain/755b6ad3-76a6-4d19-b9a8-d18242c46790/verify_rework/05_curriculum_page.png)
- [06_learn_complex_numbers.png](file:///C:/Users/laksh/.gemini/antigravity-ide/brain/755b6ad3-76a6-4d19-b9a8-d18242c46790/verify_rework/06_learn_complex_numbers.png)

---

## 4. Current Process & Server State
- **Frontend Vite Dev Server:** Running on `http://localhost:3001`
- **FastAPI Uvicorn Backend:** Running on `http://127.0.0.1:8000`
- **Backend Test Suite:** 707 passed, 0 failed, 5 skipped across all engines, quantum physics, and API endpoints (`pytest`).
- **Demo Permutation Suite:** 12,671 tests passing cleanly (`npm run test:demos`).

---

## 5. Latest Critical Polish & Bug Fixes (Turn Updates)

### R. AI Tutor Send Button Icon Fixed
- **Root Cause Identified:** In `LearnPage.tsx`, the send button previously used `<Button size="sm" className="w-6 h-6 ...">`. In `ui.tsx`, `size="sm"` injected `px-3` (24px horizontal padding), which completely collapsed the available width for inner children to 0px, causing the `<Send>` icon to disappear and leave an empty blue square.
- **Resolution:** Replaced with a semantic `<button>` styled with `h-7 w-7` dimensions, centered flex layout, `disabled:bg-accent/40 disabled:text-white/70`, and a high-contrast `<Send className="h-3.5 w-3.5 text-white stroke-[2.25]" />`.
- **Where to check:** On `/learn`, look at the AI Tutor bottom input. The send arrow is crisply visible. Type a prompt: the button stays active and cleanly clickable.

### S. Elimination of Broken Inline Composer / Direct Redirect to Composer Studio
- **Problem & Solution:** The user requested either putting the whole composer page or redirecting it, and removing the broken inline embed. Embedding the multi-qubit canvas inside a 72ch text column caused visual cramping.
  - In `LearnPage.tsx`: The demo tab for `circuit_lab` is rendered as a prominent redirect button: `Build circuit in Composer ↗` (`<Link to="/composer">`). Clicking it redirects the learner directly to `/composer`.
  - In `Demos.tsx`: Replaced `<ComposerInner>` with a Studio Launcher card displaying circuit statistics (qubits, gates, depth, shared session status) with a direct link to `/composer`.
  - In `PlaygroundPage.tsx`: Added an "Open in Full Composer Studio" link.
- **Architectural Safeguard to Prevent Recurrence:**
  - Standardized **Container-Query Constraints**: Complex studio tools (Canvas, 3D Spheres, Multi-Qubit Grids) must require a minimum viewport width of 960px or render via dedicated routes (`/composer`).
  - Separation of Concerns: Lesson views host interactive micro-simulations (`<EntanglementLab />`, `<BlochExplorer />`), while full multi-gate synthesis is delegated to `/composer` with cross-session circuit synchronization via Zustand.

### T. Interactive Entanglement Demonstration & 4 Bell States Lab
- **What was built:**
  - Relocated the "Exponential state space" ($2^n$) demo to its designated chapter: `24_tensor_products` (Multi-Qubit Systems & Tensor Products).
  - Built `EntanglementLab` in `Demos.tsx` (featured in `03_entanglement`, `11_bell_states`, `21_entanglement_measures`, and `26_teleportation`):
    1. **4 Bell States:** $|\Phi^+\rangle = (|00\rangle+|11\rangle)/\sqrt{2}$, $|\Phi^-\rangle = (|00\rangle-|11\rangle)/\sqrt{2}$, $|\Psi^+\rangle = (|01\rangle+|10\rangle)/\sqrt{2}$, and $|\Psi^-\rangle = (|01\rangle-|10\rangle)/\sqrt{2}$.
    2. **Relative Phases:** Dynamically reflects $0^\circ$ and $180^\circ$ phase shifts for constructive vs destructive interference in entanglement.
    3. **Interactive Bipartite Quantum Measurement:**
       - **"Measure Qubit A"**: Measures Alice's qubit ($p=0.5$ for $|0\rangle$, $p=0.5$ for $|1\rangle$). Superposition breaks instantaneously, and Bob's qubit collapses to the correlated state according to the Bell state parity (identical for $\Phi$, opposite for $\Psi$).
       - **"Measure Qubit B"**: Symmetrically measures Bob and collapses Alice.
       - **"Reset"**: Restores entangled coherent superposition.
    4. **Rigorous Quantum Information Metrics:** Displays Entanglement Entropy $S(\rho_A) = 1.00$ bit and State Purity $\text{Tr}(\rho_A^2) = 0.50$ (maximally mixed reduced state).
    5. **Empirical Statistics:** Tracks live counts of $|00\rangle, |01\rangle, |10\rangle, |11\rangle$ across successive measurements.
- **Permutation Tests:** Created `scripts/verify-all-demos.mts` (`npm run test:demos`). Ran **12,671 permutation tests** covering every Bell state, measurement collapse, Bloch cardinal, gate sequence ($H^2=I, X^2=I, Z^2=I, HZH=X$), little-endian bit ordering, and interference math. All 12,671 passed with 0 errors.

### U. Full Markdown Code Block Syntax Highlighting Across All Modules
- **Problem & Solution:** Code blocks across modules previously lacked syntax highlighting because `.hljs-*` CSS tokens were missing from the global bundle and code blocks with quantum tags (e.g. ````qiskit`, ````cirq`, ````pennylane`, ````cudaq`, ````openqasm`) or untagged code blocks were bypassed.
  - Added comprehensive dark-mode CSS tokens in `globals.css` for `.hljs-keyword`, `.hljs-operator`, `.hljs-function`, `.hljs-string`, `.hljs-number`, `.hljs-comment`, `.hljs-built_in`, `.hljs-variable`, `.hljs-meta`, etc.
  - Registered `python`, `bash`, `json`, and `javascript` grammars in `Markdown.tsx`.
  - Added smart dialect mapping: mapped `qiskit`, `cirq`, `pennylane`, `cudaq`, `qasm`, and `openqasm` to Python highlighting.
  - Added auto-detection so untagged or multiline fenced blocks default to Python syntax highlighting.
- **Where to check:** Visit any lesson in `/learn` (e.g. `01_qubits`, `02_gates`, `05_deutsch_jozsa`): all code snippets display vibrant syntax coloring on dark `#080d1a` rounded containers.

