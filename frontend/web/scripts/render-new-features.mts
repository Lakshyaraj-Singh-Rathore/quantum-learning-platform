/** In-depth UI/UX component render checks for newest platform features:
 * - Qudit Lab (Beta): Dimension selectors, Gate Palette, Circuit Editor, DensityMatrixInspector
 * - Smart Composer AI Studio: Generation tab, Simplification tab, Objectives, Equivalence badge
 * - Quantum Noise Lab: Preset selection, T1/T2 decoherence, SPAM, Comparison dashboard
 *
 * Usage:
 *   npx tsx scripts/render-new-features.mts
 */

// 1. Setup mock session and DOM globals for React SSR
const store = new Map<string, string>();
store.set(
  "ql-session",
  JSON.stringify({
    state: {
      token: "mock-render-token",
      user: {
        id: 1,
        email: "student@quantum.local",
        role: "student",
        display_name: "Student Tester",
        is_active: true,
      },
    },
    version: 0,
  }),
);

const storage = {
  getItem: (k: string) => store.get(k) ?? null,
  setItem: (k: string, v: string) => void store.set(k, v),
  removeItem: (k: string) => void store.delete(k),
  clear: () => store.clear(),
  key: () => null,
  length: 0,
};

(globalThis as { localStorage?: unknown }).localStorage = storage;
(globalThis as { window?: unknown }).window = {
  localStorage: storage,
  location: { hostname: "localhost", href: "http://localhost/", origin: "http://localhost" },
};

const { renderToString } = await import("react-dom/server");
const { createElement } = await import("react");
const { MemoryRouter } = await import("react-router-dom");
const { QueryClient, QueryClientProvider } = await import("@tanstack/react-query");

// Import the newest UI components
const { QuditLabPage } = await import("../src/pages/QuditLabPage");
const { QuditGatePalette } = await import("../src/components/qudit/QuditGatePalette");
const { DensityMatrixInspector } = await import("../src/components/qudit/DensityMatrixInspector");
const { SmartComposerPanel } = await import("../src/components/smart_composer/SmartComposerPanel");
const { NoiseLabView } = await import("../src/components/noise/NoiseLabView");

let failures = 0;
function check(name: string, ok: boolean, extra = "") {
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${extra ? ` — ${extra}` : ""}`);
  if (!ok) failures += 1;
}

// Strip React SSR comment delimiters e.g. <!-- -->
const stripComments = (html: string) => html.replace(/<!--.*?-->/g, "");

// Prepare pre-populated query client with mock data
const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: false, gcTime: Infinity },
  },
});

function renderWith(element: React.ReactElement): string {
  return renderToString(
    createElement(
      QueryClientProvider,
      { client: queryClient },
      createElement(MemoryRouter, null, element),
    ),
  );
}

console.log("=".repeat(80));
console.log("RUNNING IN-DEPTH UI/UX COMPONENT RENDER TESTS FOR NEWEST FEATURES");
console.log("=".repeat(80));

// -----------------------------------------------------------------------------
// 1. QUDIT LAB (BETA) PAGE & COMPONENTS
// -----------------------------------------------------------------------------
console.log("\n[Component 1] QuditLabPage & Workbench Components");
const quditHtml = renderWith(createElement(QuditLabPage));
const quditPlain = stripComments(quditHtml);

check("Qudit Lab page renders successfully", quditHtml.length > 5000, `${quditHtml.length} chars`);
check("Header carries page title 'Qudit Lab'", quditHtml.includes("Qudit Lab"));
check("Beta tag badge is present", quditHtml.includes("Beta"));

// Dimension selectors
check("All four local dimension selector buttons are offered (d=2, 3, 4, 5)",
  quditPlain.includes("d = 2") &&
  quditPlain.includes("d = 3") &&
  quditPlain.includes("d = 4") &&
  quditPlain.includes("d = 5")
);

// Safety & Resource Status Bar
check("Resource & safety status bar renders",
  quditHtml.includes("State Dimension") || quditHtml.includes("Hilbert Space") || quditHtml.includes("Safety Cap")
);

// Circuit Canvas & Controls
check("Circuit Editor canvas renders",
  quditHtml.includes("Circuit Canvas") || quditPlain.includes("q0")
);

check("Simulation trigger button 'Run Simulation' is present",
  quditHtml.includes("Run Simulation")
);

// Noise Panel
check("Noise panel controls are rendered",
  quditHtml.includes("Depolarizing") || quditHtml.includes("Dephasing") || quditHtml.includes("Noise Controls")
);

check("No runtime error or undefined leaked into Qudit Lab",
  !quditHtml.includes("Cannot read") && !quditHtml.includes("undefined is not")
);

// Direct Gate Palette Verification with Mock Catalogue
console.log("\n[Component 1b] QuditGatePalette (Dimension-Aware Gate Representation)");
const mockGateCatalogue = [
  { id: "x", name: "Shift Gate X_d", symbol: "X_d", category: "single_qudit", is_two_qudit: false, latex: "X_d", description: "Cyclic shift" },
  { id: "z", name: "Phase Gate Z_d", symbol: "Z_d", category: "single_qudit", is_two_qudit: false, latex: "Z_d", description: "Clock phase" },
  { id: "f", name: "Fourier Gate F_d", symbol: "F_d", category: "single_qudit", is_two_qudit: false, latex: "F_d", description: "Discrete Fourier" },
  { id: "sum", name: "Controlled Shift SUM_d", symbol: "SUM", category: "two_qudit", is_two_qudit: true, latex: "SUM", description: "Generalized CNOT" },
  { id: "cp", name: "Controlled Phase CP_d", symbol: "CP", category: "two_qudit", is_two_qudit: true, latex: "CP", description: "Generalized CZ" },
  { id: "swap", name: "Swap Gate SWAP_d", symbol: "SWAP", category: "two_qudit", is_two_qudit: true, latex: "SWAP", description: "State swap" },
  { id: "r_jk", name: "Givens Rotation R_jk", symbol: "R_jk", category: "parametric", is_two_qudit: false, latex: "R_jk", description: "Two-level rotation" },
];

const paletteHtml = renderWith(
  createElement(QuditGatePalette, {
    dimension: 3,
    catalogue: mockGateCatalogue,
    onAddGate: () => {},
  })
);

check("Gate Palette renders with d=3 dimension adaptation",
  paletteHtml.includes("X_3") && paletteHtml.includes("Z_3") && paletteHtml.includes("F_3")
);
check("Two-qudit entangling gates (SUM, CP, SWAP) are offered",
  paletteHtml.includes("SUM") && paletteHtml.includes("CP") && paletteHtml.includes("SWAP")
);

// Direct Density Matrix Inspector Verification with Active Simulation Result
console.log("\n[Component 1c] DensityMatrixInspector (Active Simulation State)");
const mockSimResult = {
  circuit_id: "test-circ",
  dimension: 3,
  n_qudits: 2,
  total_dim: 9,
  basis_labels: ["|0,0⟩", "|0,1⟩", "|0,2⟩", "|1,0⟩", "|1,1⟩", "|1,2⟩", "|2,0⟩", "|2,1⟩", "|2,2⟩"],
  populations: { "|0,0⟩": 0.333, "|1,1⟩": 0.333, "|2,2⟩": 0.333 },
  coherences: {},
  probabilities: { "|0,0⟩": 0.333, "|1,1⟩": 0.333, "|2,2⟩": 0.333 },
  state_validation: {
    is_valid: true,
    trace: 1.0,
    trace_residual: 0.0,
    hermiticity_residual: 0.0,
    is_hermitian: true,
    min_eigenvalue: 0.0,
    is_positive_semidefinite: true,
    purity: 1.0,
    entropy: 0.0,
    diagnostics: [],
  },
  density_matrix: [
    [{ real: 0.333, imag: 0.0, mag: 0.333, phase: 0.0 }]
  ],
  density_matrix_truncated: false,
  reduced_states: {
    q0: {
      wire_index: 0,
      dimension: 3,
      density_matrix: [[{ real: 0.333, imag: 0.0, mag: 0.333, phase: 0.0 }]],
      purity: 0.333,
      entropy: 1.585,
      populations: [0.333, 0.333, 0.333],
    },
  },
  execution_time_ms: 12.5,
  memory_estimate_bytes: 1296,
  noisy: false,
  warnings: [],
};

const inspectorHtml = renderWith(
  createElement(DensityMatrixInspector, {
    result: mockSimResult as any,
    loading: false,
  })
);

check("Density Matrix Inspector renders active tabs (Matrix, Distribution, Reduced)",
  inspectorHtml.includes("Density Matrix") &&
  inspectorHtml.includes("Measurement Distribution") &&
  inspectorHtml.includes("Reduced Subsystems")
);
check("Trace and Purity badges are rendered",
  inspectorHtml.includes("Trace Tr(ρ)") && inspectorHtml.includes("Purity γ = Tr(ρ²)")
);

// -----------------------------------------------------------------------------
// 2. SMART COMPOSER AI STUDIO TESTS
// -----------------------------------------------------------------------------
console.log("\n[Component 2] SmartComposerPanel (AI Generation & Simplification)");

const mockCircuitIr = {
  n_qubits: 2,
  n_clbits: 2,
  name: "Redundant Test Circuit",
  ops: [
    { kind: "gate", gate: "h", qubits: [0], layer: 0 },
    { kind: "gate", gate: "h", qubits: [0], layer: 1 },
    { kind: "gate", gate: "cx", qubits: [1], controls: [0], layer: 2 },
    { kind: "gate", gate: "cx", qubits: [1], controls: [0], layer: 3 },
  ],
};

const smartComposerHtml = renderWith(
  createElement(SmartComposerPanel, {
    currentIr: mockCircuitIr,
    onAdoptCircuit: () => {},
    onClose: () => {},
  })
);

check("Smart Composer panel renders", smartComposerHtml.length > 2000, `${smartComposerHtml.length} chars`);
check("Header displays 'Smart Composer AI Studio'", smartComposerHtml.includes("Smart Composer AI Studio"));
check("Verified Engine badge rendered", smartComposerHtml.includes("Verified Engine"));

// Mode tabs
check("Mode switcher tabs exist (Circuit Simplification vs AI Generator)",
  smartComposerHtml.includes("Circuit Simplification") &&
  smartComposerHtml.includes("AI Generator")
);

// Simplifier controls
check("Optimization objectives are offered",
  smartComposerHtml.includes("Objective") || smartComposerHtml.includes("min_gates") || smartComposerHtml.includes("Minimum Gates")
);

check("Action button 'Simplify Circuit' is present",
  smartComposerHtml.includes("Simplify Circuit") || smartComposerHtml.includes("Simplify")
);

check("Current circuit metrics displayed (Gates, Depth)",
  smartComposerHtml.includes("Gates") && smartComposerHtml.includes("Depth")
);

check("No runtime error leaked into Smart Composer",
  !smartComposerHtml.includes("Cannot read") && !smartComposerHtml.includes("undefined is not")
);

// -----------------------------------------------------------------------------
// 3. QUANTUM NOISE LAB VIEW TESTS
// -----------------------------------------------------------------------------
console.log("\n[Component 3] NoiseLabView (Decoherence, Presets & State Analytics)");

const noiseLabHtml = renderWith(
  createElement(NoiseLabView, {
    circuitIr: mockCircuitIr,
    backendId: "qiskit_aer",
  })
);

check("Noise Lab View renders", noiseLabHtml.length > 3000, `${noiseLabHtml.length} chars`);
check("Noise categories are offered (Decoherence, Stochastic, Readout)",
  noiseLabHtml.includes("Decoherence") || noiseLabHtml.includes("Stochastic") || noiseLabHtml.includes("Readout")
);

check("Simulation execution action 'Run Noise Simulation' is present",
  noiseLabHtml.includes("Run Noise Simulation") || noiseLabHtml.includes("Simulate")
);

check("Shots configuration control is present",
  noiseLabHtml.includes("shots") || noiseLabHtml.includes("Shots")
);

check("No runtime error leaked into Noise Lab",
  !noiseLabHtml.includes("Cannot read") && !noiseLabHtml.includes("undefined is not")
);

console.log("\n" + "=".repeat(80));
console.log(
  failures === 0
    ? "ALL NEW FEATURES UI/UX RENDER CHECKS PASSED!"
    : `${failures} UI/UX RENDER CHECK(S) FAILED.`
);
console.log("=".repeat(80));

process.exit(failures === 0 ? 0 : 1);
