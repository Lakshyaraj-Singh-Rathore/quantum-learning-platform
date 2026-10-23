import React, { useEffect, useState } from "react";
import {
  Sparkles,
  Play,
  HardDrive,
  FlaskConical,
  CheckCircle2,
} from "lucide-react";
import {
  quditLabApi,
  type EducationalPreset,
  type QuditCircuit,
  type QuditGateCatalogueItem,
  type QuditLimits,
  type QuditNoiseConfig,
  type SimulationResult,
} from "../api/quditLab";
import { QuditCircuitEditor } from "../components/qudit/QuditCircuitEditor";
import { DensityMatrixInspector } from "../components/qudit/DensityMatrixInspector";
import { QuditNoisePanel } from "../components/qudit/QuditNoisePanel";
import { QuditLearnPanel } from "../components/qudit/QuditLearnPanel";
import { Badge, Button, toast } from "../components/ui";

/**
 * QL-015. The shared toast anchor is bottom-right and is NOT moved: every page
 * uses it, and repositioning it globally to fix one page is how a P4 becomes a
 * P1. The Qudit Lab is the page where that anchor collides with live content --
 * measured at 1920 the default position lands on the "Run Simulation" button
 * itself, and at 1366 on the circuit grid. Candidate positions were measured
 * against every interactive control on the page:
 *
 *     1920   bottom-right  covers 1 (Run Simulation)   top-right  covers 2
 *            bottom-center covers 3                    top-center covers 0
 *     1366   bottom-right  covers 0                    top-right  covers 2
 *            bottom-center covers 4                    top-center covers 0
 *
 * so this page -- and only this page -- raises its toasts top-center. Sonner
 * takes `position` per toast (ToastT.position), so nothing about the shared
 * <Toaster> changes and every other page keeps bottom-right.
 */
const QUDIT_TOAST = { position: "top-center" } as const;

const DEFAULT_DIMENSION = 3;

export const QuditLabPage: React.FC = () => {
  const [dimension, setDimension] = useState<number>(DEFAULT_DIMENSION);
  const [limits, setLimits] = useState<QuditLimits | null>(null);
  const [catalogue, setCatalogue] = useState<QuditGateCatalogueItem[]>([]);
  const [presets, setPresets] = useState<EducationalPreset[]>([]);

  // Circuit State
  const [circuit, setCircuit] = useState<QuditCircuit>({
    version: "1.0",
    id: "qudit-circuit-main",
    name: "Qudit Experiment",
    dimension: DEFAULT_DIMENSION,
    wires: [
      { id: "q0", index: 0, dimension: DEFAULT_DIMENSION, initial_state: 0, label: "q0" },
    ],
    ops: [
      { id: "op-1", gate: "f", targets: [0], controls: [], params: {}, dimension: DEFAULT_DIMENSION },
    ],
  });

  // Noise State
  const [noiseConfig, setNoiseConfig] = useState<QuditNoiseConfig>({
    depolarizing: { enabled: false, p: 0.1 },
    dephasing: { enabled: false, gamma: 0.1 },
    relaxation: { enabled: false, gamma: 0.1 },
  });

  // Simulation Controls & Results
  const [shots, setShots] = useState<number>(1024);
  const [seed, setSeed] = useState<number>(42);
  const [isSimulating, setIsSimulating] = useState<boolean>(false);
  const [simResult, setSimResult] = useState<SimulationResult | null>(null);
  // Snapshot of the exact circuit + noise a displayed result was produced
  // from, so the panel can say when it no longer describes the editor. The
  // qubit Composer already does this (ComposerPage passes `stale` to
  // ResultsPanel); the Qudit Lab was presenting a previous run as current.
  const [resultSnapshot, setResultSnapshot] = useState<string | null>(null);
  const [activeSideTab, setActiveSideTab] = useState<"noise" | "learn">("noise");

  // Load limits, catalogue, and presets on mount
  useEffect(() => {
    async function loadInitial() {
      try {
        // Presets are deliberately NOT fetched here: the [dimension] effect
        // below already fetches them on mount and on every change, so asking
        // for them here issued the same request twice on every page load.
        const [limitsData, catData] = await Promise.all([
          quditLabApi.getLimits(),
          quditLabApi.getCatalogue(),
        ]);
        setLimits(limitsData);
        setCatalogue(catData);
      } catch (err) {
        console.error("Failed to load qudit lab metadata:", err);
      }
    }
    loadInitial();
  }, []);

  // Update presets when dimension changes
  useEffect(() => {
    async function updatePresetsForDim() {
      try {
        const data = await quditLabApi.getPresets(dimension);
        setPresets(data);
      } catch (err) {
        console.error("Failed to update presets:", err);
      }
    }
    updatePresetsForDim();
  }, [dimension]);

  // Execute simulation
  const handleRunSimulation = async (
    customCircuit?: QuditCircuit,
    customNoise?: QuditNoiseConfig
  ) => {
    const targetCircuit = customCircuit || circuit;
    const targetNoise = customNoise || noiseConfig;
    const snapshot = JSON.stringify({ c: targetCircuit, n: targetNoise, shots, seed });

    setIsSimulating(true);
    try {
      const result = await quditLabApi.simulate({
        circuit: targetCircuit,
        noise: targetNoise,
        shots,
        seed,
        calculate_entropy: true,
      });
      setSimResult(result);
      setResultSnapshot(snapshot);
    } catch (err: any) {
      console.error("Simulation error:", err);
      toast.error(err.message || "Failed to execute qudit density-matrix simulation", QUDIT_TOAST);
      // A failed run must not leave the previous result looking current.
      setResultSnapshot(null);
    } finally {
      setIsSimulating(false);
    }
  };

  // Run initial simulation on first load once metadata is loaded
  useEffect(() => {
    handleRunSimulation();
  }, []);

  // Handle Dimension Change
  const handleDimensionChange = (newDim: number) => {
    if (newDim === dimension) return;
    setDimension(newDim);

    // Reinitialize circuit for the new dimension
    const newCircuit: QuditCircuit = {
      version: "1.0",
      id: `qudit-circuit-${newDim}`,
      name: `Qudit Experiment (d=${newDim})`,
      dimension: newDim,
      wires: [
        { id: "q0", index: 0, dimension: newDim, initial_state: 0, label: "q0" },
      ],
      ops: [
        { id: "op-1", gate: "f", targets: [0], controls: [], params: {}, dimension: newDim },
      ],
    };
    setCircuit(newCircuit);
    handleRunSimulation(newCircuit);
    toast.success(`Dimension switched to d = ${newDim}`, QUDIT_TOAST);
  };

  // Apply Preset
  const handleApplyPreset = (preset: EducationalPreset) => {
    setDimension(preset.dimension);
    setCircuit(preset.circuit);
    if (preset.noise) {
      setNoiseConfig(preset.noise);
    }
    handleRunSimulation(preset.circuit, preset.noise || undefined);
    toast.success(`Loaded preset: ${preset.title}`, QUDIT_TOAST);
  };

  // Reset Circuit
  const handleResetCircuit = () => {
    const blankCircuit: QuditCircuit = {
      ...circuit,
      wires: [
        { id: "q0", index: 0, dimension, initial_state: 0, label: "q0" },
      ],
      ops: [],
    };
    setCircuit(blankCircuit);
    handleRunSimulation(blankCircuit);
    toast.info("Circuit reset to single idle qudit", QUDIT_TOAST);
  };

  const maxQuditsAllowed = limits?.safe_limits[String(dimension)] ?? 4;
  const totalDim = Math.pow(dimension, circuit.wires.length);
  const rawBytes = 16 * Math.pow(totalDim, 2);
  const rawMiB = (rawBytes / (1024 * 1024)).toFixed(2);

  return (
    <div className="min-h-full space-y-5 p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-line pb-5">
        <div>
          <div className="flex items-center gap-2.5 mb-1.5">
            <div className="grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-tr from-accent/30 to-indigo-500/30 text-accent border border-accent/40 shadow-sm">
              <FlaskConical className="h-5 w-5" />
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-ink">
              Qudit Lab <span className="text-xs font-semibold uppercase px-2 py-0.5 rounded-full bg-accent/20 text-accent border border-accent/40">Beta</span>
            </h1>
          </div>
          <p className="text-xs text-ink-3 max-w-2xl">
            A dedicated mixed-dimensional quantum simulation laboratory powered by Google Cirq.
            Explore qudit gates, genuine density-matrix evolution, quantum mixedness, and generalized entanglement.
          </p>
        </div>

        {/* Dimension Selector & System Safety Badges */}
        <div className="flex flex-wrap items-center gap-2 shrink-0">
          <span className="text-xs font-semibold text-ink-3 mr-1">Local Dimension:</span>
          {[3, 4, 5].map((d) => (
            <button
              key={d}
              type="button"
              onClick={() => handleDimensionChange(d)}
              className={`px-3 py-1.5 rounded-lg text-xs font-mono font-bold transition-all ${
                dimension === d
                  ? "bg-accent text-accent-ink shadow-md scale-105"
                  : "bg-subtle/80 text-ink-2 hover:bg-hover hover:text-ink border border-line"
              }`}
              aria-label={`Select dimension ${d}`}
            >
              d = {d}
              <span className="text-[10px] ml-1 opacity-70">
                {d === 3 ? "Qutrit" : d === 4 ? "Ququart" : "5-Level"}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Resource & Safety Limit Status Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-xl border border-line/70 bg-subtle/30 text-xs">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-1.5 text-ink-2">
            <HardDrive className="h-4 w-4 text-accent" />
            <span>State Dimension:</span>
            <b className="font-mono text-ink">D = {totalDim}</b> ({circuit.wires.length} qudits)
          </div>

          <div className="flex items-center gap-1.5 text-ink-2">
            <span>Raw Density Matrix:</span>
            <b className="font-mono text-accent">{rawMiB} MiB</b>
            <span className="text-ink-3">(complex128)</span>
          </div>

          <Badge tone="neutral">
            Safety Cap: Max {maxQuditsAllowed} Qudits at d={dimension}
          </Badge>
        </div>

        {simResult && (
          <div className="flex items-center gap-2 text-ink-3">
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
            <span>Execution time:</span>
            <span className="font-mono font-semibold text-ink">
              {simResult.execution_time_ms} ms
            </span>
          </div>
        )}
      </div>

      {/* Educational Presets Carousel Bar */}
      <div className="space-y-2">
        <div className="flex items-center gap-2 text-xs font-semibold text-ink">
          <Sparkles className="h-3.5 w-3.5 text-accent" />
          <span>Educational Presets (d = {dimension})</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-2.5">
          {presets.map((preset) => (
            <button
              key={preset.id}
              type="button"
              onClick={() => handleApplyPreset(preset)}
              className="p-2.5 rounded-lg border border-line bg-raised/60 hover:border-accent/40 hover:bg-accent/5 text-left transition-all group"
            >
              <div className="flex items-center justify-between mb-1">
                <Badge tone="neutral" className="text-[10px]">
                  {preset.category}
                </Badge>
                <span className="text-[10px] text-ink-3 font-mono">d={preset.dimension}</span>
              </div>
              {/* QL-016. These are teaching labels, so `truncate` hid the thing
                  being taught: at 1366px "Fourier Superposition (F_3)" became
                  "Fourier Superposition (F_..." and "Two-Qudit Bell State
                  (|phi+>)" lost which Bell state it prepares. Wrapping costs a
                  line of height and keeps the title readable at every width. */}
              <div className="text-xs font-semibold text-ink group-hover:text-accent break-words">
                {preset.title}
              </div>
              <p className="text-[11px] text-ink-3 line-clamp-2 mt-1 leading-relaxed">
                {preset.description}
              </p>
            </button>
          ))}
        </div>
      </div>

      {/* Circuit Building Section: 3-Column Composer matching Qubit Composer Layout */}
      <div className="space-y-4">
        <QuditCircuitEditor
          circuit={circuit}
          maxQudits={maxQuditsAllowed}
          catalogue={catalogue}
          onUpdateCircuit={setCircuit}
          onResetCircuit={handleResetCircuit}
        />
      </div>

      {/* Simulation Controls Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-4 rounded-xl border border-line bg-raised/60 shadow-sm">
        <div className="flex flex-wrap items-center gap-4 text-xs">
          <div className="flex items-center gap-2">
            <span className="text-ink-3">Shots (Sampling):</span>
            <select
              value={shots}
              onChange={(e) => setShots(Number(e.target.value))}
              className="bg-bg border border-line rounded px-2 py-1 font-mono text-xs text-ink focus:outline-none focus:border-accent"
              aria-label="Simulation shots"
            >
              <option value={256}>256</option>
              <option value={512}>512</option>
              <option value={1024}>1024</option>
              <option value={4096}>4096</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-ink-3">RNG Seed:</span>
            <input
              type="number"
              value={seed}
              onChange={(e) => setSeed(Number(e.target.value))}
              className="w-16 bg-bg border border-line rounded px-2 py-1 font-mono text-xs text-ink focus:outline-none focus:border-accent"
              aria-label="Random seed"
            />
          </div>

          <div className="flex items-center gap-2">
            <span className="text-ink-3">Side Panel:</span>
            <div className="flex items-center bg-subtle p-0.5 rounded border border-line">
              <button
                type="button"
                onClick={() => setActiveSideTab("noise")}
                className={`px-2.5 py-1 rounded text-xs transition-colors ${
                  activeSideTab === "noise"
                    ? "bg-accent text-accent-ink font-semibold"
                    : "text-ink-3 hover:text-ink"
                }`}
              >
                Noise Channels
              </button>
              <button
                type="button"
                onClick={() => setActiveSideTab("learn")}
                className={`px-2.5 py-1 rounded text-xs transition-colors ${
                  activeSideTab === "learn"
                    ? "bg-accent text-accent-ink font-semibold"
                    : "text-ink-3 hover:text-ink"
                }`}
              >
                Theory Guide
              </button>
            </div>
          </div>
        </div>

        <Button
          variant="primary"
          size="md"
          onClick={() => handleRunSimulation()}
          disabled={isSimulating}
          className="shadow-md"
          aria-label="Run density matrix simulation"
        >
          {isSimulating ? (
            <div className="h-4 w-4 mr-1.5 rounded-full border-2 border-white border-t-transparent animate-spin" />
          ) : (
            <Play className="h-4 w-4 mr-1.5 fill-current" />
          )}
          Run Simulation
        </Button>
      </div>

      {/* Side Panel: Noise vs Learn */}
      {activeSideTab === "noise" ? (
        <QuditNoisePanel
          dimension={dimension}
          config={noiseConfig}
          onChange={(newNoise) => {
            setNoiseConfig(newNoise);
            handleRunSimulation(undefined, newNoise);
          }}
        />
      ) : (
        <QuditLearnPanel />
      )}

      {/* Simulation Results & Density Matrix Inspector */}
      <DensityMatrixInspector
        result={simResult}
        loading={isSimulating}
        stale={
          simResult !== null &&
          resultSnapshot !== JSON.stringify({ c: circuit, n: noiseConfig, shots, seed })
        }
        onRerun={() => handleRunSimulation()}
      />
    </div>
  );
};
