import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Info,
  Play,
  TrendingDown,
} from "lucide-react";
import {
  noiseLabApi,
  type NoiseConfig,
  type NoiseSimulationResult,
  type SweepPoint,
} from "../../api/noiseLab";
import {
  Badge,
  Button,
  Card,
  Input,
  Label,
  Spinner,
} from "../ui";

interface NoiseLabViewProps {
  circuitIr: any;
  backendId?: string;
  onSimulationDone?: (result: NoiseSimulationResult) => void;
}

const DEFAULT_CONFIG: NoiseConfig = {
  name: "superconducting_transmon",
  description: "Superconducting transmon model with T1/T2 decoherence and readout error.",
  decoherence: {
    enabled: true,
    t1_us: 60.0,
    t2_us: 45.0,
    gate_time_1q_us: 0.03,
    gate_time_2q_us: 0.30,
    gate_time_3q_us: 1.00,
    excited_state_pop: 0.0,
  },
  stochastic: {
    enabled: true,
    depolarizing_1q: 0.001,
    depolarizing_2q: 0.01,
    bit_flip: 0.0,
    phase_flip: 0.0,
    bit_phase_flip: 0.0,
    reset_error: 0.0,
  },
  coherent: {
    enabled: false,
    over_rotation_1q_rad: 0.0,
    over_rotation_2q_rad: 0.0,
    phase_offset_rad: 0.0,
  },
  readout: {
    enabled: true,
    prob_1_given_0: 0.015,
    prob_0_given_1: 0.025,
  },
  correlated: {
    enabled: false,
    zz_crosstalk_strength: 0.0,
    correlated_depolarizing_2q: 0.0,
  },
  simulation_method: "automatic",
};

export function NoiseLabView({ circuitIr, backendId = "qiskit_aer", onSimulationDone }: NoiseLabViewProps) {
  const [config, setConfig] = useState<NoiseConfig>(DEFAULT_CONFIG);
  const [activeCategory, setActiveCategory] = useState<
    "decoherence" | "stochastic" | "coherent" | "readout" | "correlated"
  >("decoherence");
  const [shots, setShots] = useState(1024);
  const [simResult, setSimResult] = useState<NoiseSimulationResult | null>(null);
  const [sweepResults, setSweepResults] = useState<SweepPoint[] | null>(null);
  const [sweepParam, setSweepParam] = useState("decoherence.t1_us");
  const [sweepMin, setSweepMin] = useState(10);
  const [sweepMax, setSweepMax] = useState(100);

  // Load Catalogue and Presets
  const presetsQuery = useQuery({
    queryKey: ["noise_presets"],
    queryFn: noiseLabApi.getPresets,
  });

  const catalogueQuery = useQuery({
    queryKey: ["noise_catalogue"],
    queryFn: noiseLabApi.getCatalogue,
  });

  // Validation Query
  const validationQuery = useQuery({
    queryKey: ["noise_validation", config, circuitIr?.n_qubits],
    queryFn: () => noiseLabApi.validate(config, circuitIr?.n_qubits),
    enabled: Boolean(config),
  });

  // Simulation Mutation
  const simulateMutation = useMutation({
    mutationFn: (overrideConfig?: NoiseConfig) =>
      noiseLabApi.simulate(circuitIr, overrideConfig ?? config, shots),
    onSuccess: (data) => {
      setSimResult(data);
      onSimulationDone?.(data);
    },
  });

  // Sweep Mutation
  const sweepMutation = useMutation({
    mutationFn: () =>
      noiseLabApi.sweep(circuitIr, config, sweepParam, sweepMin, sweepMax, 6, 512),
    onSuccess: (data) => {
      setSweepResults(data);
    },
  });

  // Apply preset
  const handleSelectPreset = (presetKey: string) => {
    if (presetsQuery.data && presetsQuery.data[presetKey]) {
      const newConfig = presetsQuery.data[presetKey];
      setConfig(newConfig);
      // Immediately run simulation for the new preset so results appear right away!
      simulateMutation.mutate(newConfig);
    }
  };

  // Run on first load if circuit exists
  useEffect(() => {
    if (circuitIr && !simResult && !simulateMutation.isPending) {
      simulateMutation.mutate();
    }
  }, [circuitIr]);

  const t2ExceedsBound = config.decoherence.enabled && config.decoherence.t2_us > 2 * config.decoherence.t1_us;
  const validation = validationQuery.data;

  return (
    <div className="flex flex-col gap-6 p-6 bg-[#090b14] text-ink min-h-[600px] rounded-2xl border border-white/5">
      {/* Header & Preset Selector */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-white/10 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-1.5 rounded-lg bg-accent/20 text-accent border border-accent/30">
              <Activity className="h-5 w-5" />
            </span>
            <h2 className="text-xl font-bold tracking-tight text-white font-display">
              Quantum Noise Simulation Laboratory
            </h2>
            <Badge tone="accent" className="text-xs">
              Qiskit Aer Native
            </Badge>
            <span className="text-[11px] text-ink-3 font-mono">
              ({backendId} • {catalogueQuery.data ? catalogueQuery.data.length : 8} channels)
            </span>
          </div>
          <p className="text-xs text-ink-3 mt-1">
            Scientifically modeled quantum decoherence, stochastic channels, coherent errors, and SPAM readout faults.
          </p>
        </div>

        {/* Presets and Controls */}
        <div className="flex items-center gap-2">
          <Label className="text-xs text-ink-3">Preset:</Label>
          <select
            aria-label="Noise configuration preset"
            className="h-8 rounded-lg bg-raised border border-white/10 text-xs px-2.5 text-ink focus:outline-none focus:border-accent"
            onChange={(e) => handleSelectPreset(e.target.value)}
            defaultValue="superconducting_transmon"
          >
            <option value="ideal">Ideal Textbook (Zero Noise)</option>
            <option value="superconducting_transmon">Superconducting Transmon (IBM-class)</option>
            <option value="trapped_ion">Trapped Ion (IonQ/Quantinuum-class)</option>
            <option value="pure_dephasing">Dominant Dephasing (T₂ &lt;&lt; 2T₁)</option>
            <option value="readout_dominated">Readout / SPAM Faults Only</option>
            <option value="coherent_overrotation">Coherent Gate Miscalibration</option>
            <option value="high_depolarizing">High Stochastic Depolarizing</option>
          </select>

          <select
            aria-label="Simulation shots"
            value={shots}
            onChange={(e) => setShots(Number(e.target.value))}
            className="h-8 rounded-lg bg-raised border border-white/10 text-xs px-2 text-ink focus:outline-none focus:border-accent"
          >
            <option value={512}>512 shots</option>
            <option value={1024}>1024 shots</option>
            <option value={2048}>2048 shots</option>
            <option value={4096}>4096 shots</option>
          </select>

          <Button
            variant="primary"
            size="sm"
            onClick={() => simulateMutation.mutate()}
            disabled={simulateMutation.isPending || (validation && !validation.valid)}
            className="flex items-center gap-1.5 shadow-sm font-semibold"
          >
            {simulateMutation.isPending ? <Spinner className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}
            Run Noise Simulation
          </Button>
        </div>
      </div>

      {/* Simulation Error Alert if any */}
      {simulateMutation.isError && (
        <div className="p-3.5 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-xs flex items-start gap-2.5">
          <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5 text-red-400" />
          <div className="flex flex-col gap-1">
            <span className="font-semibold">Noise Simulation Failed:</span>
            <span>{String(simulateMutation.error)}</span>
          </div>
        </div>
      )}

      {/* Physics Validation Alert if invalid */}
      {validation && !validation.valid && (
        <div className="p-3.5 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-xs flex items-start gap-2.5">
          <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5 text-red-400" />
          <div className="flex flex-col gap-1">
            <span className="font-semibold">Unphysical Noise Parameter Detected:</span>
            {validation.errors.map((err, idx) => (
              <span key={idx}>• {err}</span>
            ))}
          </div>
        </div>
      )}

      {/* Main Workspace Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Noise Channels Configurator (5 cols) */}
        <div className="lg:col-span-5 flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-ink-3">
              Noise Mechanisms
            </span>
            <span className="text-[11px] text-ink-4">
              {config.simulation_method} simulation
            </span>
          </div>

          {/* Category Tabs */}
          <div className="grid grid-cols-5 gap-1 p-1 bg-raised rounded-xl border border-white/5 text-[11px]">
            {(
              [
                ["decoherence", "Decoherence"],
                ["stochastic", "Stochastic"],
                ["coherent", "Coherent"],
                ["readout", "Readout"],
                ["correlated", "Crosstalk"],
              ] as const
            ).map(([cat, label]) => (
              <button
                key={cat}
                onClick={() => setActiveCategory(cat)}
                className={`py-1.5 px-1 rounded-lg text-center font-medium transition-all cursor-pointer truncate ${
                  activeCategory === cat
                    ? "bg-accent/20 text-accent font-semibold border border-accent/30 shadow-xs"
                    : "text-ink-3 hover:text-ink hover:bg-white/5"
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          {/* Active Category Controls Card */}
          <Card className="p-4 bg-raised/50 border border-white/10 rounded-xl flex flex-col gap-4">
            {/* 1. Decoherence & Relaxation */}
            {activeCategory === "decoherence" && (
              <div className="flex flex-col gap-3.5 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-white">T₁ / T₂ Relaxation & Dephasing</span>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <span className="text-[11px] text-ink-3">Enable</span>
                    <input
                      type="checkbox"
                      checked={config.decoherence.enabled}
                      onChange={(e) =>
                        setConfig({
                          ...config,
                          decoherence: { ...config.decoherence, enabled: e.target.checked },
                        })
                      }
                      className="rounded accent-accent"
                    />
                  </label>
                </div>

                <div className="flex flex-col gap-1.5">
                  <div className="flex justify-between">
                    <span className="text-ink-3">Energy Relaxation T₁:</span>
                    <span className="font-mono text-white">{config.decoherence.t1_us} µs</span>
                  </div>
                  <input
                    type="range"
                    min="1"
                    max="300"
                    step="1"
                    value={config.decoherence.t1_us}
                    onChange={(e) =>
                      setConfig({
                        ...config,
                        decoherence: { ...config.decoherence, t1_us: parseFloat(e.target.value) },
                      })
                    }
                    className="w-full accent-accent"
                  />
                </div>

                <div className="flex flex-col gap-1.5">
                  <div className="flex justify-between">
                    <span className="text-ink-3">Dephasing T₂:</span>
                    <span className={`font-mono ${t2ExceedsBound ? "text-red-400 font-bold" : "text-white"}`}>
                      {config.decoherence.t2_us} µs
                    </span>
                  </div>
                  <input
                    type="range"
                    min="1"
                    max="600"
                    step="1"
                    value={config.decoherence.t2_us}
                    onChange={(e) =>
                      setConfig({
                        ...config,
                        decoherence: { ...config.decoherence, t2_us: parseFloat(e.target.value) },
                      })
                    }
                    className="w-full accent-accent"
                  />
                  {t2ExceedsBound ? (
                    <span className="text-[11px] text-red-400">
                      ⚠ T₂ cannot physically exceed 2×T₁ ({2 * config.decoherence.t1_us} µs)
                    </span>
                  ) : (
                    <span className="text-[10px] text-ink-4">
                      Physical bound satisfied: T₂ ≤ 2×T₁ ({2 * config.decoherence.t1_us} µs)
                    </span>
                  )}
                </div>

                <div className="grid grid-cols-2 gap-3 pt-2 border-t border-white/5">
                  <div>
                    <span className="text-ink-3 text-[11px]">1Q Gate Time:</span>
                    <div className="font-mono text-white mt-0.5">{config.decoherence.gate_time_1q_us} µs</div>
                  </div>
                  <div>
                    <span className="text-ink-3 text-[11px]">2Q Gate Time:</span>
                    <div className="font-mono text-white mt-0.5">{config.decoherence.gate_time_2q_us} µs</div>
                  </div>
                </div>
              </div>
            )}

            {/* 2. Stochastic Channels */}
            {activeCategory === "stochastic" && (
              <div className="flex flex-col gap-3.5 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-white">Stochastic Quantum Errors</span>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <span className="text-[11px] text-ink-3">Enable</span>
                    <input
                      type="checkbox"
                      checked={config.stochastic.enabled}
                      onChange={(e) =>
                        setConfig({
                          ...config,
                          stochastic: { ...config.stochastic, enabled: e.target.checked },
                        })
                      }
                      className="rounded accent-accent"
                    />
                  </label>
                </div>

                <div className="flex flex-col gap-1.5">
                  <div className="flex justify-between">
                    <span className="text-ink-3">1Q Depolarizing Rate:</span>
                    <span className="font-mono text-white">
                      {(config.stochastic.depolarizing_1q * 100).toFixed(2)}%
                    </span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="0.05"
                    step="0.001"
                    value={config.stochastic.depolarizing_1q}
                    onChange={(e) =>
                      setConfig({
                        ...config,
                        stochastic: { ...config.stochastic, depolarizing_1q: parseFloat(e.target.value) },
                      })
                    }
                    className="w-full accent-accent"
                  />
                </div>

                <div className="flex flex-col gap-1.5">
                  <div className="flex justify-between">
                    <span className="text-ink-3">2Q Depolarizing Rate:</span>
                    <span className="font-mono text-white">
                      {(config.stochastic.depolarizing_2q * 100).toFixed(2)}%
                    </span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="0.20"
                    step="0.005"
                    value={config.stochastic.depolarizing_2q}
                    onChange={(e) =>
                      setConfig({
                        ...config,
                        stochastic: { ...config.stochastic, depolarizing_2q: parseFloat(e.target.value) },
                      })
                    }
                    className="w-full accent-accent"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3 pt-2 border-t border-white/5">
                  <div className="flex flex-col gap-1">
                    <span className="text-ink-3 text-[11px]">Bit-Flip (X):</span>
                    <span className="font-mono text-white">{(config.stochastic.bit_flip * 100).toFixed(1)}%</span>
                  </div>
                  <div className="flex flex-col gap-1">
                    <span className="text-ink-3 text-[11px]">Phase-Flip (Z):</span>
                    <span className="font-mono text-white">{(config.stochastic.phase_flip * 100).toFixed(1)}%</span>
                  </div>
                </div>
              </div>
            )}

            {/* 3. Coherent Errors */}
            {activeCategory === "coherent" && (
              <div className="flex flex-col gap-3.5 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-white">Systematic Unitary Miscalibration</span>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <span className="text-[11px] text-ink-3">Enable</span>
                    <input
                      type="checkbox"
                      checked={config.coherent.enabled}
                      onChange={(e) =>
                        setConfig({
                          ...config,
                          coherent: { ...config.coherent, enabled: e.target.checked },
                        })
                      }
                      className="rounded accent-accent"
                    />
                  </label>
                </div>

                <div className="flex flex-col gap-1.5">
                  <div className="flex justify-between">
                    <span className="text-ink-3">1Q Over-rotation:</span>
                    <span className="font-mono text-white">
                      {config.coherent.over_rotation_1q_rad.toFixed(3)} rad (
                      {((config.coherent.over_rotation_1q_rad * 180) / Math.PI).toFixed(1)}°)
                    </span>
                  </div>
                  <input
                    type="range"
                    min="-0.2"
                    max="0.2"
                    step="0.01"
                    value={config.coherent.over_rotation_1q_rad}
                    onChange={(e) =>
                      setConfig({
                        ...config,
                        coherent: { ...config.coherent, over_rotation_1q_rad: parseFloat(e.target.value) },
                      })
                    }
                    className="w-full accent-accent"
                  />
                </div>

                <div className="flex flex-col gap-1.5">
                  <div className="flex justify-between">
                    <span className="text-ink-3">1Q Phase Offset (Δφ):</span>
                    <span className="font-mono text-white">
                      {config.coherent.phase_offset_rad.toFixed(3)} rad (
                      {((config.coherent.phase_offset_rad * 180) / Math.PI).toFixed(1)}°)
                    </span>
                  </div>
                  <input
                    type="range"
                    min="-0.3"
                    max="0.3"
                    step="0.01"
                    value={config.coherent.phase_offset_rad}
                    onChange={(e) =>
                      setConfig({
                        ...config,
                        coherent: { ...config.coherent, phase_offset_rad: parseFloat(e.target.value) },
                      })
                    }
                    className="w-full accent-accent"
                  />
                </div>

                <div className="flex flex-col gap-1.5">
                  <div className="flex justify-between">
                    <span className="text-ink-3">2Q Over-rotation:</span>
                    <span className="font-mono text-white">
                      {config.coherent.over_rotation_2q_rad.toFixed(3)} rad
                    </span>
                  </div>
                  <input
                    type="range"
                    min="-0.3"
                    max="0.3"
                    step="0.01"
                    value={config.coherent.over_rotation_2q_rad}
                    onChange={(e) =>
                      setConfig({
                        ...config,
                        coherent: { ...config.coherent, over_rotation_2q_rad: parseFloat(e.target.value) },
                      })
                    }
                    className="w-full accent-accent"
                  />
                </div>
              </div>
            )}

            {/* 4. Readout Errors */}
            {activeCategory === "readout" && (
              <div className="flex flex-col gap-3.5 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-white">Measurement / SPAM Confusion</span>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <span className="text-[11px] text-ink-3">Enable</span>
                    <input
                      type="checkbox"
                      checked={config.readout.enabled}
                      onChange={(e) =>
                        setConfig({
                          ...config,
                          readout: { ...config.readout, enabled: e.target.checked },
                        })
                      }
                      className="rounded accent-accent"
                    />
                  </label>
                </div>

                <div className="flex flex-col gap-1.5">
                  <div className="flex justify-between">
                    <span className="text-ink-3">P(1|0) False Excitation:</span>
                    <span className="font-mono text-white">
                      {(config.readout.prob_1_given_0 * 100).toFixed(1)}%
                    </span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="0.10"
                    step="0.005"
                    value={config.readout.prob_1_given_0}
                    onChange={(e) =>
                      setConfig({
                        ...config,
                        readout: { ...config.readout, prob_1_given_0: parseFloat(e.target.value) },
                      })
                    }
                    className="w-full accent-accent"
                  />
                </div>

                <div className="flex flex-col gap-1.5">
                  <div className="flex justify-between">
                    <span className="text-ink-3">P(0|1) Relaxation during Readout:</span>
                    <span className="font-mono text-white">
                      {(config.readout.prob_0_given_1 * 100).toFixed(1)}%
                    </span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="0.15"
                    step="0.005"
                    value={config.readout.prob_0_given_1}
                    onChange={(e) =>
                      setConfig({
                        ...config,
                        readout: { ...config.readout, prob_0_given_1: parseFloat(e.target.value) },
                      })
                    }
                    className="w-full accent-accent"
                  />
                </div>

                {/* Confusion Matrix Preview */}
                <div className="p-2.5 rounded-lg bg-bg border border-white/5 font-mono text-[11px]">
                  <div className="text-ink-4 text-[10px] mb-1">Confusion Matrix M = [P(m|p)]:</div>
                  <div className="flex justify-between">
                    <span>|0⟩ prep:</span>
                    <span>
                      P(0)={(1 - config.readout.prob_1_given_0).toFixed(3)}, P(1)=
                      {config.readout.prob_1_given_0.toFixed(3)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>|1⟩ prep:</span>
                    <span>
                      P(0)={config.readout.prob_0_given_1.toFixed(3)}, P(1)=
                      {(1 - config.readout.prob_0_given_1).toFixed(3)}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* 5. Correlated Crosstalk */}
            {activeCategory === "correlated" && (
              <div className="flex flex-col gap-3.5 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-white">Residual ZZ Crosstalk</span>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <span className="text-[11px] text-ink-3">Enable</span>
                    <input
                      type="checkbox"
                      checked={config.correlated.enabled}
                      onChange={(e) =>
                        setConfig({
                          ...config,
                          correlated: { ...config.correlated, enabled: e.target.checked },
                        })
                      }
                      className="rounded accent-accent"
                    />
                  </label>
                </div>

                <div className="flex flex-col gap-1.5">
                  <div className="flex justify-between">
                    <span className="text-ink-3">ZZ Coupling Strength:</span>
                    <span className="font-mono text-white">
                      {config.correlated.zz_crosstalk_strength.toFixed(3)}
                    </span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="0.5"
                    step="0.02"
                    value={config.correlated.zz_crosstalk_strength}
                    onChange={(e) =>
                      setConfig({
                        ...config,
                        correlated: { ...config.correlated, zz_crosstalk_strength: parseFloat(e.target.value) },
                      })
                    }
                    className="w-full accent-accent"
                  />
                  <span className="text-[10px] text-ink-4">
                    Simulates parasitic Hamiltonian exp(-i ζ Z⊗Z / 2) between adjacent spectator wires.
                  </span>
                </div>
              </div>
            )}
          </Card>

          {/* Parameter Sweep Accordion */}
          <Card className="p-3.5 bg-raised/30 border border-white/5 rounded-xl text-xs flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-white flex items-center gap-1.5">
                <TrendingDown className="h-3.5 w-3.5 text-accent" />
                Automated Parameter Sweep
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2 text-[11px]">
              <div>
                <Label className="text-ink-3">Parameter:</Label>
                <select
                  aria-label="Parameter to sweep"
                  value={sweepParam}
                  onChange={(e) => setSweepParam(e.target.value)}
                  className="w-full h-7 rounded bg-raised border border-white/10 px-1 text-xs"
                >
                  <option value="decoherence.t1_us">T1 (µs)</option>
                  <option value="decoherence.t2_us">T2 (µs)</option>
                  <option value="stochastic.depolarizing_2q">2Q Depolarizing</option>
                  <option value="readout.prob_1_given_0">Readout P(1|0)</option>
                </select>
              </div>

              <div>
                <Label className="text-ink-3">Range [Min, Max]:</Label>
                <div className="flex gap-1">
                  <Input
                    type="number"
                    value={sweepMin}
                    onChange={(e) => setSweepMin(parseFloat(e.target.value))}
                    className="h-7 text-xs"
                  />
                  <Input
                    type="number"
                    value={sweepMax}
                    onChange={(e) => setSweepMax(parseFloat(e.target.value))}
                    className="h-7 text-xs"
                  />
                </div>
              </div>
            </div>

            <Button
              variant="secondary"
              size="sm"
              onClick={() => sweepMutation.mutate()}
              disabled={sweepMutation.isPending}
              className="w-full h-7 text-xs"
            >
              {sweepMutation.isPending ? <Spinner className="h-3 w-3 mr-1" /> : null}
              Run 6-Point Sweep
            </Button>
          </Card>
        </div>

        {/* Right Column: Results & Comparisons (7 cols) */}
        <div className="lg:col-span-7 flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-ink-3">
              Experimental Comparison & Metrics
            </span>
            {simResult && (
              <span className="text-[11px] text-ink-4">
                Method: <span className="font-mono text-accent">{simResult.method_used}</span>
              </span>
            )}
          </div>

          {/* Metric Cards Row */}
          {simResult?.metrics && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <Card className="p-3 bg-raised/50 border border-white/5 rounded-xl flex flex-col">
                <span className="text-[11px] text-ink-3">Quantum State Fidelity</span>
                <span className="text-lg font-mono font-bold text-accent mt-0.5">
                  {simResult.metrics.fidelity !== null && simResult.metrics.fidelity !== undefined
                    ? (simResult.metrics.fidelity * 100).toFixed(2) + "%"
                    : "N/A"}
                </span>
                <span className="text-[9px] text-ink-4 mt-1">
                  {simResult.metrics.is_exact_density_matrix ? "Exact ⟨ψ|ρ|ψ⟩" : "Sampled Bound"}
                </span>
              </Card>

              <Card className="p-3 bg-raised/50 border border-white/5 rounded-xl flex flex-col">
                <span className="text-[11px] text-ink-3">Density Matrix Purity</span>
                <span className="text-lg font-mono font-bold text-white mt-0.5">
                  {simResult.metrics.purity !== null && simResult.metrics.purity !== undefined
                    ? simResult.metrics.purity.toFixed(3)
                    : "1.000"}
                </span>
                <span className="text-[9px] text-ink-4 mt-1">Tr(ρ²) · Mixed State Purity</span>
              </Card>

              <Card className="p-3 bg-raised/50 border border-white/5 rounded-xl flex flex-col">
                <span className="text-[11px] text-ink-3">Total Variation Distance</span>
                <span className="text-lg font-mono font-bold text-emerald-400 mt-0.5">
                  {simResult.metrics.total_variation_distance.toFixed(4)}
                </span>
                <span className="text-[9px] text-ink-4 mt-1">½ ∑ |P_ideal - P_noisy|</span>
              </Card>

              <Card className="p-3 bg-raised/50 border border-white/5 rounded-xl flex flex-col">
                <span className="text-[11px] text-ink-3">Von Neumann Entropy</span>
                <span className="text-lg font-mono font-bold text-white mt-0.5">
                  {simResult.metrics.entropy_bits !== null && simResult.metrics.entropy_bits !== undefined
                    ? simResult.metrics.entropy_bits.toFixed(3)
                    : "0.000"}
                </span>
                <span className="text-[9px] text-ink-4 mt-1">-Tr(ρ log₂ ρ) (bits)</span>
              </Card>
            </div>
          )}

          {/* Dual Bar Histogram: Ideal vs Noisy */}
          <Card className="p-4 bg-raised/40 border border-white/10 rounded-xl flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-white flex items-center gap-1.5">
                <BarChart3 className="h-4 w-4 text-accent" />
                Measurement Distributions: Ideal vs Noisy
              </span>
              <div className="flex items-center gap-3 text-[11px]">
                <div className="flex items-center gap-1.5">
                  <div className="h-2.5 w-2.5 rounded-xs bg-accent" />
                  <span className="text-ink-3">Ideal</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="h-2.5 w-2.5 rounded-xs bg-amber-400" />
                  <span className="text-ink-3">Noisy Aer</span>
                </div>
              </div>
            </div>

            {simResult ? (
              <div className="flex flex-col gap-3 pt-2">
                {Array.from(
                  new Set([
                    ...Object.keys(simResult.ideal_probabilities),
                    ...Object.keys(simResult.noisy_probabilities),
                  ])
                )
                  .sort()
                  .map((state) => {
                    const idealP = simResult.ideal_probabilities[state] || 0;
                    const noisyP = simResult.noisy_probabilities[state] || 0;
                    const delta = noisyP - idealP;
                    return (
                      <div key={state} className="flex flex-col gap-1.5 text-xs bg-black/20 p-2.5 rounded-lg border border-white/5">
                        <div className="flex justify-between font-mono text-[11px]">
                          <span className="text-white font-bold flex items-center gap-1.5">
                            |{state}⟩
                            {Math.abs(delta) > 0.005 && (
                              <span className={`text-[10px] px-1.5 py-0.2 rounded font-semibold ${
                                delta > 0 ? "bg-amber-500/15 text-amber-300" : "bg-cyan-500/15 text-cyan-300"
                              }`}>
                                {delta > 0 ? `+${(delta * 100).toFixed(1)}%` : `${(delta * 100).toFixed(1)}%`}
                              </span>
                            )}
                          </span>
                          <span>
                            <span className="text-accent font-semibold">Ideal: {(idealP * 100).toFixed(1)}%</span>
                            {" · "}
                            <span className="text-amber-400 font-semibold">Noisy: {(noisyP * 100).toFixed(1)}%</span>
                          </span>
                        </div>

                        <div className="flex flex-col gap-1">
                          {/* Ideal Bar Row */}
                          <div className="flex items-center gap-2">
                            <span className="w-10 text-[10px] text-accent font-mono font-medium">Ideal</span>
                            <div className="h-2 flex-1 bg-bg rounded-full overflow-hidden p-0.5">
                              <div
                                className="h-full bg-accent rounded-full transition-all duration-300"
                                style={{ width: `${Math.min(100, Math.max(idealP > 0 ? 2 : 0, idealP * 100))}%` }}
                                title={`Ideal: ${(idealP * 100).toFixed(2)}%`}
                              />
                            </div>
                            <span className="w-12 text-right font-mono text-[10px] text-ink-3">
                              {(idealP * 100).toFixed(1)}%
                            </span>
                          </div>
                          {/* Noisy Bar Row */}
                          <div className="flex items-center gap-2">
                            <span className="w-10 text-[10px] text-amber-400 font-mono font-medium">Noisy</span>
                            <div className="h-2 flex-1 bg-bg rounded-full overflow-hidden p-0.5">
                              <div
                                className="h-full bg-amber-400 rounded-full transition-all duration-300"
                                style={{ width: `${Math.min(100, Math.max(noisyP > 0 ? 2 : 0, noisyP * 100))}%` }}
                                title={`Noisy: ${(noisyP * 100).toFixed(2)}%`}
                              />
                            </div>
                            <span className="w-12 text-right font-mono text-[10px] text-ink-3">
                              {(noisyP * 100).toFixed(1)}%
                            </span>
                          </div>
                        </div>
                      </div>
                    );
                  })}
              </div>
            ) : (
              <div className="h-32 grid place-items-center text-xs text-ink-4">
                Click Run Noise Simulation to view ideal vs noisy execution
              </div>
            )}
          </Card>

          {/* Parameter Sweep Results Table if present */}
          {sweepResults && (
            <Card className="p-3 bg-raised/30 border border-white/5 rounded-xl text-xs flex flex-col gap-2">
              <span className="text-xs font-semibold text-white">Parameter Sweep Decay Curve</span>
              <div className="grid grid-cols-5 text-[10px] text-ink-3 border-b border-white/5 pb-1 font-mono">
                <span>Value</span>
                <span>Fidelity</span>
                <span>Purity</span>
                <span>TVD</span>
                <span>Trace Dist</span>
              </div>
              <div className="flex flex-col gap-1 max-h-32 overflow-y-auto font-mono text-[11px]">
                {sweepResults.map((pt, idx) => (
                  <div key={idx} className="grid grid-cols-5 py-0.5 border-b border-white/5 last:border-0">
                    <span className="text-white">{pt.value}</span>
                    <span className="text-accent">
                      {pt.fidelity !== null && pt.fidelity !== undefined ? (pt.fidelity * 100).toFixed(1) + "%" : "-"}
                    </span>
                    <span className="text-white">
                      {pt.purity !== null && pt.purity !== undefined ? pt.purity.toFixed(3) : "-"}
                    </span>
                    <span className="text-emerald-400">
                      {pt.tvd !== null && pt.tvd !== undefined ? pt.tvd.toFixed(4) : "-"}
                    </span>
                    <span className="text-ink-3">
                      {pt.trace_distance !== null && pt.trace_distance !== undefined ? pt.trace_distance.toFixed(4) : "-"}
                    </span>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* Educational Insights Box */}
          <div className="p-3 rounded-xl bg-accent/5 border border-accent/20 text-xs text-ink-3 flex items-start gap-2.5">
            <Info className="h-4 w-4 shrink-0 mt-0.5 text-accent" />
            <div className="flex flex-col gap-0.5">
              <span className="font-semibold text-white">Quantum Physics Note:</span>
              <p className="text-[11px] leading-relaxed">
                T₁ energy relaxation causes irreversible decay of excited state |1⟩ to ground state |0⟩. Dephasing T₂
                destroys quantum phase interference. Notice how entanglement collapses and entropy increases as noise
                approaches real hardware thresholds.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
