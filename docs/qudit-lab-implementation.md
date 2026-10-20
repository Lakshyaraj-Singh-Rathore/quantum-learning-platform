# QuantumLearnAI: Qudit Lab (Beta) — Implementation Report & Documentation

## 1. Executive Summary

**Qudit Lab (Beta)** is a dedicated, mixed-dimensional quantum computing and density-matrix learning environment built for **QuantumLearnAI**. Unlike two-level qubit simulators that only track pure statevectors $|\psi\rangle$, Qudit Lab models discrete quantum systems with local dimensions $d \in \{2, 3, 4, 5\}$ and executes full quantum density-matrix evolution throughout circuit execution:

$$\rho \in \mathbb{C}^{D \times D}, \quad D = \prod_{i=0}^{n-1} d_i$$

$$\rho' = U \rho U^\dagger \quad \text{(Unitary gate evolution)}$$

$$\rho' = \sum_{i} K_i \rho K_i^\dagger \quad \text{(Open quantum system Kraus noise evolution)}$$

The feature is implemented as a completely separate environment with its own route (`/qudit-lab`), visual circuit builder, gate palette, density-matrix inspector, noise channels, educational theory guide, backend API, resource validation policies, and test suite, keeping the existing Qiskit-based qubit Composer and Noise Lab fully untouched and functional.

---

## 2. Architecture & Engine Selection

### Primary Simulation Engine: Google Cirq `DensityMatrixSimulator`

Cirq (installed version `1.4.1`) was chosen as the primary computational engine due to its native dimension-aware primitives (`cirq.Qid`, `cirq.NamedQid`), protocol-driven custom gates (`_qid_shape_`, `_unitary_`, `_kraus_`), and genuine mixed-state `DensityMatrixSimulator(dtype=np.complex128)`.

- **Numerical Precision:** `np.complex128` (16 bytes per matrix element).
- **No Statevector Shortcut:** The simulation state is a density matrix at every stage of execution. No statevector-to-density-matrix conversions are performed.
- **Mixed-State Representation:** Handles pure states ($\text{Tr}(\rho^2) = 1$), statistical mixtures, and open quantum systems ($\text{Tr}(\rho^2) < 1$).

---

## 3. Mathematical Gate Catalogue

All gates are mathematically defined, dimension-aware, and verified to be unitary ($U^\dagger U = I$) across all supported dimensions $d \in \{2, 3, 4, 5\}$:

### 3.1 Generalized Cyclic Shift Gate $X_d$
Cyclically increments the computational basis state:
$$X_d |j\rangle = |(j+1) \bmod d\rangle$$
- **Dimension:** $d \times d$
- **Unitarity & Cyclic Property:** $X_d^\dagger X_d = I_d$, and $X_d^d = I_d$.
- **Qubit Specialization ($d=2$):** Standard Pauli-X (NOT) gate.

### 3.2 Generalized Phase Gate $Z_d$
Applies dimension-dependent phase factors:
$$Z_d |j\rangle = \omega^j |j\rangle, \quad \omega = \exp\left(\frac{2\pi i}{d}\right)$$
- **Matrix:** $\text{diag}(1, \omega, \omega^2, \dots, \omega^{d-1})$
- **Unitarity & Identity:** $Z_d^\dagger Z_d = I_d$, and $Z_d^d = I_d$.
- **Qubit Specialization ($d=2$):** $\omega = -1 \implies \text{diag}(1, -1) = \text{Pauli-Z}$.

### 3.3 Generalized Quantum Fourier Transform $F_d$
Creates an exact, equal superposition across all $d$ computational levels:
$$F_d |j\rangle = \frac{1}{\sqrt{d}} \sum_{k=0}^{d-1} \omega^{jk} |k\rangle$$
- **Unitarity:** $F_d^\dagger F_d = I_d$.
- **Action on $|0\rangle$:** $\frac{1}{\sqrt{d}} \sum_{k=0}^{d-1} |k\rangle$, yielding uniform Born probability $P(k) = 1/d$.
- **Qubit Specialization ($d=2$):** $F_2 = H$ (standard Hadamard gate).

### 3.4 Generalized Controlled-Addition Gate $\text{SUM}_d$
Controlled modular addition on two qudits of dimension $d$:
$$\text{SUM}_d |a, b\rangle = |a, (a+b) \bmod d\rangle$$
- **Dimension:** $d^2 \times d^2$
- **Unitarity:** $(\text{SUM}_d)^\dagger \text{SUM}_d = I_{d^2}$.
- **Entanglement Preparation:** When applied to $(F_d \otimes I) |0, 0\rangle$, it produces the canonical maximally entangled generalized Bell state:
$$|\Phi_d\rangle = \frac{1}{\sqrt{d}} \sum_{j=0}^{d-1} |j, j\rangle$$
- **Qubit Specialization ($d=2$):** Standard CNOT gate.

### 3.5 Controlled-Phase Gate $\text{CP}_d$
Applies conditional phases:
$$\text{CP}_d |a, b\rangle = \exp\left(\frac{2\pi i a b}{d}\right) |a, b\rangle = \omega^{ab} |a, b\rangle$$
- **Qubit Specialization ($d=2$):** Controlled-Z (CZ) gate.

### 3.6 Generalized $\text{SWAP}_d$
Exchanges states of two equal-dimension qudits:
$$\text{SWAP}_d |a, b\rangle = |b, a\rangle$$
- **Involutory:** $(\text{SWAP}_d)^2 = I_{d^2}$.

### 3.7 Subspace Rotation Gate $R_{jk}(\theta, \phi)$
Selective $\text{SU}(2)$ rotation between computational levels $j$ and $k$ ($0 \le j < k < d$), acting as identity on all other levels:
$$R_{jk}(\theta, \phi) = \begin{pmatrix} \cos(\theta/2) & -e^{-i\phi}\sin(\theta/2) \\ e^{i\phi}\sin(\theta/2) & \cos(\theta/2) \end{pmatrix}_{\{|j\rangle, |k\rangle\}} \oplus I_{\text{rest}}$$

---

## 4. Generalized Qudit Noise Models

The noise subsystem provides three dimension-aware quantum channels implemented via Kraus operators $K_i$ satisfying the completeness relation $\sum_i K_i^\dagger K_i = I_d$:

### 4.1 Generalized Depolarizing Channel
Isotropically drives any input state toward the maximally mixed state $\frac{1}{d} I_d$:
$$\mathcal{E}(\rho) = (1-p)\rho + \frac{p}{d} I_d$$
- **Kraus Representation:** $d^2$ operators using the generalized Weyl-Heisenberg / Pauli basis $\{X_d^j Z_d^k / \sqrt{d}\}$:
  - $E_{0,0} = \sqrt{1 - p + \frac{p}{d^2}} I_d$
  - $E_{j,k} = \sqrt{\frac{p}{d^2}} X_d^j Z_d^k \quad \text{for } (j, k) \neq (0, 0)$
- **Completeness:** Verified $\sum_{j,k} E_{j,k}^\dagger E_{j,k} = I_d$ to machine precision.

### 4.2 Generalized Pure Dephasing Channel
Selectively suppresses off-diagonal coherences without altering diagonal populations:
$$\mathcal{E}(\rho)_{jj} = \rho_{jj}, \quad \mathcal{E}(\rho)_{jk} = (1 - \gamma)\rho_{jk} \quad (j \neq k)$$
- **Kraus Operators:**
  - $K_0 = \sqrt{1 - \frac{d-1}{d}\gamma} I_d$
  - $K_m = \sqrt{\frac{\gamma}{d}} \sum_{j=0}^{d-1} \omega^{jm} |j\rangle\langle j| \quad (m = 1, \dots, d-1)$

### 4.3 Multi-Level Cascade Relaxation Channel
Models downward energy relaxation $|j\rangle \to |j-1\rangle$ with decay rate $\gamma_j = \gamma \frac{j}{d-1}$:
- **Kraus Operators:**
  - $A_j = \sqrt{\gamma_j} |j-1\rangle\langle j| \quad (j = 1, \dots, d-1)$
  - $A_0 = \sum_{j=0}^{d-1} \sqrt{1 - \gamma_j} |j\rangle\langle j|$
- **Completeness & Positivity:** Trace-preserving and completely positive for all $\gamma \in [0, 1]$.

---

## 5. Physical Invariants, Diagnostics & Reduced Subsystems

For every simulation run, the backend verifies and reports:

1. **Unit Trace:** $\text{Tr}(\rho) = 1.0$ ($|\text{Tr}(\rho) - 1.0| < 10^{-5}$).
2. **Hermiticity:** $\rho = \rho^\dagger$ ($\max |\rho - \rho^\dagger| < 10^{-5}$).
3. **Positive Semidefiniteness:** $\lambda_{\min} \ge -10^{-5}$.
4. **Purity:** $\gamma = \text{Tr}(\rho^2) = \sum_i \lambda_i^2 \in [1/D, 1.0]$.
   - $\gamma = 1.0 \implies$ Pure quantum state.
   - $\gamma < 1.0 \implies$ Mixed state.
   - $\gamma = 1/D \implies$ Maximally mixed state.
5. **Von Neumann Entropy:** $S(\rho) = -\sum_{\lambda_i > 10^{-12}} \lambda_i \log_2 \lambda_i$ (in bits).
6. **Subsystem Partial Trace:** Dimension-aware tensor contraction computing the reduced density matrix $\rho_w = \text{Tr}_{\text{rest}}(\rho)$ for any individual wire $w$. For entangled states such as $|\Phi_d\rangle$, this proves that local subsystems are in mixed states while the global state remains pure.

---

## 6. Resource Limits & Admission Control

Simulating dense density matrices in `complex128` requires:
$$M_{\rho} = 16 \cdot D^2 = 16 \cdot d^{2n} \text{ bytes}$$

To ensure rock-solid stability on standard development machines (such as 16 GB RAM), the backend enforces the following pre-execution safety caps:

| Dimension $d$ | System Type | Safe Max Qudits | State Space $D$ | Raw Matrix Size $M_\rho$ | Est. Peak ($6\times$) |
|---|---|---|---|---|---|
| **$d = 2$** | Qubits | **10** | 1,024 | 16.0 MiB | ~96 MiB |
| **$d = 3$** | Qutrits | **6** | 729 | 8.1 MiB | ~48.6 MiB |
| **$d = 4$** | Ququarts | **5** | 1,024 | 16.0 MiB | ~96 MiB |
| **$d = 5$** | 5-level qudits | **4** | 625 | 6.0 MiB | ~36.0 MiB |

- **Per-Job Budget:** 2 GiB hard cap.
- **Browser Protection Threshold:** If $D \le 64$, the full interactive matrix is sent to the client; for larger $D$, compact summaries and paginated matrix slices are returned via `/qudit/slice`.

---

## 7. Educational Presets

Qudit Lab includes five verified educational presets:
1. **Cyclic Basis Shift ($X_d$):** Demonstrates modular increment $|0\rangle \to |1\rangle$.
2. **Fourier Superposition ($F_d$):** Demonstrates uniform superposition with equal probabilities $1/d$.
3. **Phase Gate Interference ($Z_d$):** Demonstrates that phase rotations preserve diagonal populations while rotating off-diagonal coherences.
4. **Two-Qudit Bell State ($|\Phi_d\rangle$):** Demonstrates generalized entanglement, global purity $\gamma=1$, and subsystem mixedness $\gamma=1/d$.
5. **Decoherence & Mixed States:** Applies depolarizing and dephasing noise to illustrate purity degradation.

---

## 8. File-Level Change Summary

| File | Role |
|---|---|
| `backend/app/quantum/qudit_lab/models.py` | Pydantic schemas: `QuditWire`, `QuditOp`, `QuditCircuit`, `SimulationRequest`, `SimulationResult`, `ComplexVal`, `StateValidation`, `ResourceEstimate` |
| `backend/app/quantum/qudit_lab/gates.py` | Dimension-aware Cirq Gate implementations: $X_d, Z_d, F_d, \text{SUM}_d, \text{CP}_d, \text{SWAP}_d, R_{jk}$ |
| `backend/app/quantum/qudit_lab/noise.py` | Dimension-aware Kraus noise channels: Depolarizing, Dephasing, Multi-level Relaxation |
| `backend/app/quantum/qudit_lab/validator.py` | Resource estimator, admission control, and circuit validation |
| `backend/app/quantum/qudit_lab/metrics.py` | Trace, Hermiticity, Positivity, Purity, Entropy, Partial trace tensor contractions |
| `backend/app/quantum/qudit_lab/simulator.py` | Cirq `DensityMatrixSimulator` runner, exact probabilities, seeded sampling |
| `backend/app/quantum/qudit_lab/presets.py` | 5 educational presets generated for dimensions 2..5 |
| `backend/app/quantum/qudit_lab/__init__.py` | Package exports |
| `backend/app/api/qudit_lab.py` | FastAPI router for `/qudit/...` |
| `backend/app/api/router.py` | Router inclusion |
| `backend/tests/test_qudit_lab_comprehensive.py` | 50 unit and integration tests |
| `frontend/web/src/api/quditLab.ts` | Frontend API client and TypeScript models |
| `frontend/web/src/components/qudit/QuditGatePalette.tsx` | Dimension-aware gate palette component |
| `frontend/web/src/components/qudit/QuditCircuitEditor.tsx` | Visual wire editor, multi-qudit connectors, initial level selectors |
| `frontend/web/src/components/qudit/DensityMatrixInspector.tsx` | Complex matrix heatmap, diagnostics, measurement bar chart, reduced subsystems |
| `frontend/web/src/components/qudit/QuditNoisePanel.tsx` | Noise channel toggles and sliders |
| `frontend/web/src/components/qudit/QuditLearnPanel.tsx` | Interactive educational guide |
| `frontend/web/src/pages/QuditLabPage.tsx` | Main Qudit Lab page workbench |
| `frontend/web/src/components/shell/nav.ts` | Top-level navigation link |
| `frontend/web/src/App.tsx` | `/qudit-lab` route registration |

---

## 9. Numerical Verification & Analytical Noise Oracle

### 9.1 Independent Analytical Oracle
For a qudit initialized in a pure state $|\psi\rangle$ subjected to a single-qudit generalized depolarizing channel:
$$\mathcal{E}(\rho) = (1 - p)\rho + \frac{p}{d} I_d$$
The exact analytical density-matrix purity is:
$$\text{Tr}(\mathcal{E}(\rho)^2) = (1 - p)^2 + \frac{2p(1 - p)}{d} + \frac{p^2}{d}$$

Evaluating across dimensions $d \in \{2, 3, 4, 5\}$ and error probabilities $p$:
- **$d = 3, p = 0.35$:** $\text{Tr}(\rho^2) = (0.65)^2 + \frac{2(0.35)(0.65)}{3} + \frac{0.35^2}{3} = 0.4225 + 0.151667 + 0.040833 = \mathbf{0.6150}$.
- **$d = 5, p = 0.10$:** $\text{Tr}(\rho^2) = (0.90)^2 + \frac{2(0.10)(0.90)}{5} + \frac{0.10^2}{5} = 0.8100 + 0.0360 + 0.0020 = \mathbf{0.8480}$.
- **$d = 5, p = 0.35$:** $\text{Tr}(\rho^2) = (0.65)^2 + \frac{2(0.35)(0.65)}{5} + \frac{0.35^2}{5} = 0.4225 + 0.0910 + 0.0245 = \mathbf{0.5380}$.
- **$p = 0.00$ (Any $d$):** $\text{Tr}(\rho^2) = 1.0000$ (pure state, $S(\rho) = 0.0000$).
- **$p = 1.00$ (Any $d$):** $\text{Tr}(\rho^2) = 1/d$ (maximally mixed state $\frac{1}{d}I$, $S(\rho) = \log_2 d$).

### 9.2 Audit Findings & Root Cause Analysis
During initial end-to-end testing, an apparent numerical discrepancy arose between the API test report ($0.6150$) and the browser test report ($0.8480$):

1. **Root Cause Confirmed:** In the browser test automation script (`browser-verify-qudit-lab.mjs`), Step 12 had switched the workbench dimension to $d = 5$. Step 14 then checked the depolarizing noise checkbox, but did not switch back to $d = 3$ and did not move the slider from its default value ($p = 0.10$). The log string erroneously read `Enabling Depolarizing Noise (p=0.35)`, but the actual configuration executed by Cirq was dimension $d = 5$ with $p = 0.10$.
2. **Numerical Accuracy:** For $d = 5$ and $p = 0.10$, the simulator's output purity is analytically $\mathbf{0.8480}$, which the frontend displayed with 100% precision.
3. **UI Slider Step Limitation:** `QuditNoisePanel.tsx` previously used `step={0.02}` on `<input type="range">`, preventing direct selection of $p = 0.35$ (which requires $0.01$ precision).

### 9.3 Remediation Actions Completed
1. **Frontend Input Enhancements:**
   - Updated `QuditNoisePanel.tsx` to provide both `<input type="range" step="0.01">` and an accompanying `<input type="number" step="0.01">` for depolarizing ($p$), dephasing ($\gamma$), and relaxation ($\gamma$).
   - Users and automation can now set and inspect exact arbitrary decimal parameters.
2. **Automated Regression Suite (`test_depolarizing_channel_analytical_oracle`):**
   - Added a 20-case deterministic parametrized test in `backend/tests/test_qudit_lab_comprehensive.py`.
   - Asserts trace preservation, Hermiticity, positivity, and exact agreement with the independent analytical oracle across all $d \in \{2, 3, 4, 5\}$ and $p \in \{0.0, 0.1, 0.35, 0.7, 1.0\}$.
   - Total test suite count increased from 50 to **70 passed**.
3. **Browser Automation Suite:**
   - Updated `browser-verify-qudit-lab.mjs` to distinctly test and assert:
     - $d = 3, p = 0.35 \implies \text{Purity} = \mathbf{0.6150}$ (saved screenshot `qudit_lab_noise_d3_p035.png`).
     - $d = 5, p = 0.10 \implies \text{Purity} = \mathbf{0.8480}$ (saved screenshot `qudit_lab_noise_simulation.png`).
     - $d = 5, p = 0.35 \implies \text{Purity} = \mathbf{0.5380}$.

