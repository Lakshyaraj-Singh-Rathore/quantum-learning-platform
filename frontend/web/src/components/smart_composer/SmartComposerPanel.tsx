import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  CheckCircle2,
  Cpu,
  ShieldCheck,
  Sparkles,
  Wand2,
  X,
  Zap,
} from "lucide-react";
import {
  smartComposerApi,
  type GenerationResult,
  type SimplificationResult,
} from "../../api/smartComposer";
import {
  Badge,
  Button,
  Card,
  Input,
  Label,
  Spinner,
} from "../ui";

interface SmartComposerPanelProps {
  currentIr: any;
  onAdoptCircuit: (newIr: any) => void;
  onClose?: () => void;
}

export function SmartComposerPanel({
  currentIr,
  onAdoptCircuit,
  onClose,
}: SmartComposerPanelProps) {
  const [activeTab, setActiveTab] = useState<"simplify" | "generate">("simplify");

  // Generator State
  const [prompt, setPrompt] = useState("Prepare Bell state |Phi+>");
  const [generationResult, setGenerationResult] = useState<GenerationResult | null>(null);

  // Simplifier State
  const [objective, setObjective] = useState<string>("min_gates");
  const [simplificationResult, setSimplificationResult] = useState<SimplificationResult | null>(null);

  // Rules query
  const rulesQuery = useQuery({
    queryKey: ["smart_composer_rules"],
    queryFn: smartComposerApi.getRules,
  });

  // Generator Mutation
  const generateMutation = useMutation({
    mutationFn: () => smartComposerApi.generate({ prompt }),
    onSuccess: (data) => {
      setGenerationResult(data);
    },
  });

  // Simplifier Mutation
  const simplifyMutation = useMutation({
    mutationFn: () => smartComposerApi.simplify(currentIr, objective),
    onSuccess: (data) => {
      setSimplificationResult(data);
    },
  });

  return (
    <div className="flex flex-col gap-5 p-6 bg-[#090b14] text-ink min-h-[550px] rounded-2xl border border-white/10 shadow-2xl">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-white/10 pb-4">
        <div className="flex items-center gap-3">
          <span className="p-2 rounded-xl bg-gradient-to-tr from-accent/30 to-purple-500/30 text-accent border border-accent/40 shadow-sm">
            <Sparkles className="h-5 w-5 animate-pulse" />
          </span>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xl font-bold tracking-tight text-white font-display">
                Smart Composer AI Studio
              </h2>
              <Badge tone="accent" className="border-purple-500/40 text-purple-400 text-xs">
                Verified Engine
              </Badge>
            </div>
            <p className="text-xs text-ink-3 mt-0.5">
              Dual-mode AI circuit generation &amp; mathematically verified circuit simplification.
            </p>
          </div>
        </div>

        {/* Mode Switch Tabs */}
        <div className="flex items-center gap-1.5 p-1 bg-surface rounded-xl border border-white/5">
          <button
            onClick={() => setActiveTab("simplify")}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer flex items-center gap-1.5 ${
              activeTab === "simplify"
                ? "bg-accent/20 text-accent border border-accent/40 shadow-xs"
                : "text-ink-3 hover:text-ink hover:bg-white/5"
            }`}
          >
            <Cpu className="h-3.5 w-3.5" />
            Circuit Simplification
          </button>
          <button
            onClick={() => setActiveTab("generate")}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer flex items-center gap-1.5 ${
              activeTab === "generate"
                ? "bg-accent/20 text-accent border border-accent/40 shadow-xs"
                : "text-ink-3 hover:text-ink hover:bg-white/5"
            }`}
          >
            <Wand2 className="h-3.5 w-3.5" />
            AI Generator
          </button>
          {onClose && (
            <button
              onClick={onClose}
              aria-label="Close Smart Composer Studio"
              className="p-1.5 rounded-lg text-ink-3 hover:text-white hover:bg-white/5 ml-1"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>

      {/* -------------------- TAB 1: CIRCUIT SIMPLIFICATION -------------------- */}
      {activeTab === "simplify" && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Controls Column (5 cols) */}
          <div className="lg:col-span-5 flex flex-col gap-4">
            <Card className="p-4 bg-surface/50 border border-white/10 rounded-xl flex flex-col gap-4 text-xs">
              <span className="font-semibold text-white flex items-center gap-1.5">
                <Cpu className="h-4 w-4 text-accent" />
                Optimization Parameters
              </span>

              <div className="flex flex-col gap-1.5">
                <Label className="text-ink-3 text-xs">Target Objective:</Label>
                <select
                  aria-label="Optimization Objective"
                  value={objective}
                  onChange={(e) => setObjective(e.target.value)}
                  className="h-8 rounded-lg bg-surface border border-white/10 text-xs px-2.5 text-ink focus:outline-none focus:border-accent"
                >
                  <option value="min_gates">Minimize Total Gate Count</option>
                  <option value="min_depth">Minimize Circuit Depth</option>
                  <option value="min_2q_gates">Minimize 2-Qubit Entanglers (CX/CZ)</option>
                  <option value="noise_aware">Noise-Aware (Maximize Fidelity)</option>
                </select>
              </div>

              <div className="p-3 rounded-lg bg-bg border border-white/5 flex flex-col gap-1 text-[11px] font-mono">
                <div className="text-ink-4">Original Circuit Profile:</div>
                <div className="flex justify-between">
                  <span>Qubits: {currentIr?.n_qubits || 2}</span>
                  <span>Gates: {currentIr?.ops?.length || 0}</span>
                </div>
              </div>

              <Button
                variant="primary"
                size="md"
                onClick={() => simplifyMutation.mutate()}
                disabled={simplifyMutation.isPending}
                className="w-full flex items-center justify-center gap-2 shadow-sm"
              >
                {simplifyMutation.isPending ? (
                  <>
                    <Spinner className="h-4 w-4" />
                    Running Equivalence Passes…
                  </>
                ) : (
                  <>
                    <Zap className="h-4 w-4" />
                    Analyze &amp; Simplify Circuit
                  </>
                )}
              </Button>
            </Card>

            {/* Verified Rules Guide */}
            <Card className="p-3.5 bg-surface/30 border border-white/5 rounded-xl text-xs flex flex-col gap-2 max-h-56 overflow-y-auto">
              <span className="font-semibold text-ink-3 flex items-center gap-1.5">
                <ShieldCheck className="h-3.5 w-3.5 text-accent" />
                Active Verified Rule Library ({rulesQuery.data?.length || 8})
              </span>
              <div className="flex flex-col gap-1.5">
                {rulesQuery.data?.slice(0, 5).map((rule) => (
                  <div key={rule.id} className="p-2 rounded bg-bg/50 border border-white/5 flex flex-col gap-0.5">
                    {/* Neither child could shrink, so a long formula
                        (R03_PAULI_PUSH) ran into the rule id and spilled a
                        character onto the description line below. Allow the
                        pair to wrap instead of collide: nothing is hidden, the
                        formula simply takes a second line when it needs one. */}
                    <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5">
                      <span className="font-bold text-white text-[11px] font-mono shrink-0">{rule.id}</span>
                      <span
                        className="text-[10px] text-accent font-mono break-all text-right"
                        title={rule.mathematical_formula}
                      >
                        {rule.mathematical_formula}
                      </span>
                    </div>
                    <span className="text-[10px] text-ink-3 line-clamp-1">{rule.description}</span>
                  </div>
                ))}
              </div>
            </Card>
          </div>

          {/* Results Column (7 cols) */}
          <div className="lg:col-span-7 flex flex-col gap-4">
            {simplificationResult ? (
              <div className="flex flex-col gap-4">
                {/* Equivalence Certificate Banner */}
                <div
                  className={`p-3.5 rounded-xl border flex items-center justify-between text-xs ${
                    simplificationResult.verification.is_equivalent
                      ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-300"
                      : "bg-red-500/10 border-red-500/30 text-red-300"
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="h-5 w-5 shrink-0" />
                    <div>
                      <div className="font-bold">
                        {simplificationResult.verification.is_equivalent
                          ? "Numerical Operator Equivalence Verified"
                          : "Equivalence Check Failed"}
                      </div>
                      <div className="text-[11px] opacity-80">
                        {simplificationResult.verification.details}
                      </div>
                    </div>
                  </div>
                  <Badge tone={simplificationResult.verification.is_equivalent ? "ok" : "danger"} className="font-mono text-[10px]">
                    {simplificationResult.verification.tier}
                  </Badge>
                </div>

                {/* Before / After Metrics Comparison Table */}
                <Card className="p-4 bg-surface/50 border border-white/10 rounded-xl flex flex-col gap-3">
                  <span className="text-xs font-semibold text-white">Before &amp; After Optimization Gains</span>
                  <div className="grid grid-cols-4 gap-2 text-center">
                    <div className="p-2.5 rounded-lg bg-bg border border-white/5 flex flex-col">
                      <span className="text-[10px] text-ink-3">Total Gates</span>
                      <span className="text-sm font-mono font-bold text-white mt-1">
                        {simplificationResult.original_metrics.total_gates} →{" "}
                        <span className="text-accent">
                          {simplificationResult.simplified_metrics.total_gates}
                        </span>
                      </span>
                      {simplificationResult.improvements.gate_reduction_pct ? (
                        <span className="text-[10px] text-emerald-400 font-semibold mt-0.5">
                          -{simplificationResult.improvements.gate_reduction_pct}%
                        </span>
                      ) : null}
                    </div>

                    <div className="p-2.5 rounded-lg bg-bg border border-white/5 flex flex-col">
                      <span className="text-[10px] text-ink-3">Circuit Depth</span>
                      <span className="text-sm font-mono font-bold text-white mt-1">
                        {simplificationResult.original_metrics.depth} →{" "}
                        <span className="text-accent">
                          {simplificationResult.simplified_metrics.depth}
                        </span>
                      </span>
                      {simplificationResult.improvements.depth_reduction_pct ? (
                        <span className="text-[10px] text-emerald-400 font-semibold mt-0.5">
                          -{simplificationResult.improvements.depth_reduction_pct}%
                        </span>
                      ) : null}
                    </div>

                    <div className="p-2.5 rounded-lg bg-bg border border-white/5 flex flex-col">
                      <span className="text-[10px] text-ink-3">2Q Entanglers</span>
                      <span className="text-sm font-mono font-bold text-white mt-1">
                        {simplificationResult.original_metrics.two_qubit_gates} →{" "}
                        <span className="text-accent">
                          {simplificationResult.simplified_metrics.two_qubit_gates}
                        </span>
                      </span>
                    </div>

                    <div className="p-2.5 rounded-lg bg-bg border border-white/5 flex flex-col">
                      <span className="text-[10px] text-ink-3">Est. Hardware Fidelity</span>
                      <span className="text-sm font-mono font-bold text-emerald-400 mt-1">
                        {(simplificationResult.simplified_metrics.estimated_fidelity * 100).toFixed(1)}%
                      </span>
                    </div>
                  </div>
                </Card>

                {/* Applied Rules Badges */}
                {simplificationResult.applied_rules.length > 0 && (
                  <div className="flex flex-col gap-2">
                    <span className="text-xs font-semibold text-ink-3">Applied Verified Rules:</span>
                    <div className="flex flex-wrap gap-2">
                      {simplificationResult.applied_rules.map((rule) => (
                        <div
                          key={rule.id}
                          className="px-2.5 py-1 rounded-lg bg-accent/10 border border-accent/30 text-accent text-xs flex items-center gap-1.5"
                          title={rule.mathematical_formula}
                        >
                          <CheckCircle2 className="h-3.5 w-3.5 text-accent" />
                          <span className="font-mono font-bold">{rule.id}</span>
                          <span className="text-ink-3">({rule.name})</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Explanation text */}
                <p className="text-xs text-ink-3 leading-relaxed bg-surface/30 p-3 rounded-lg border border-white/5">
                  {simplificationResult.explanation}
                </p>

                {/* Adoption Action */}
                {simplificationResult.accepted && (
                  <Button
                    variant="primary"
                    size="md"
                    onClick={() => {
                      onAdoptCircuit(simplificationResult.simplified_circuit);
                    }}
                    className="flex items-center justify-center gap-2"
                  >
                    <CheckCircle2 className="h-4 w-4" />
                    Adopt Simplified Circuit into Composer
                  </Button>
                )}
              </div>
            ) : (
              <div className="h-64 grid place-items-center text-xs text-ink-4 border border-dashed border-white/10 rounded-xl">
                Click &quot;Analyze &amp; Simplify Circuit&quot; to inspect reductions and verify equivalence.
              </div>
            )}
          </div>
        </div>
      )}

      {/* -------------------- TAB 2: AI CIRCUIT GENERATOR -------------------- */}
      {activeTab === "generate" && (
        <div className="flex flex-col gap-5 max-w-3xl mx-auto w-full">
          <div className="flex flex-col gap-2 text-xs">
            <Label className="text-ink-3">Describe the Quantum Circuit or Algorithm:</Label>
            <div className="flex gap-2">
              <Input
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="e.g. Prepare Bell state |Phi+>, 3-qubit GHZ, or Grover search for |11>"
                className="text-xs flex-1"
              />
              <Button
                variant="primary"
                size="md"
                onClick={() => generateMutation.mutate()}
                disabled={generateMutation.isPending || !prompt.trim()}
                className="flex items-center gap-2"
              >
                {generateMutation.isPending ? <Spinner className="h-4 w-4" /> : <Wand2 className="h-4 w-4" />}
                Generate
              </Button>
            </div>
          </div>

          {/* Quick Benchmark Chips */}
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span className="text-ink-4">Try benchmark:</span>
            {[
              "Prepare Bell state |Phi+>",
              "Bell state |Psi+>",
              "Create 3-qubit GHZ state",
              "Grover search for |11>",
              "Equal Superposition",
            ].map((chip) => (
              <button
                key={chip}
                onClick={() => setPrompt(chip)}
                className="px-2.5 py-1 rounded-lg bg-surface border border-white/10 text-ink-3 hover:text-white hover:border-accent text-[11px] transition-colors cursor-pointer"
              >
                {chip}
              </button>
            ))}
          </div>

          {/* Generator Result */}
          {generationResult && (
            <Card className="p-4 bg-surface/50 border border-white/10 rounded-xl flex flex-col gap-4 text-xs">
              <div className="flex items-center justify-between border-b border-white/10 pb-3">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-accent" />
                  <span className="font-bold text-white text-sm">
                    {generationResult.circuit.name || "Generated Circuit"}
                  </span>
                </div>
                <div className="flex gap-2 text-ink-3 font-mono text-[11px]">
                  <span>Qubits: {generationResult.metrics.n_qubits}</span>
                  <span>Gates: {generationResult.metrics.total_gates}</span>
                  <span>Depth: {generationResult.metrics.depth}</span>
                </div>
              </div>

              {/* Verified Checks List */}
              <div className="flex flex-col gap-1.5">
                <span className="font-semibold text-ink-3">Automated Correctness Oracles Passed:</span>
                {generationResult.passed_tests.map((test, idx) => (
                  <div key={idx} className="flex items-center gap-2 text-emerald-400 font-mono text-[11px]">
                    <CheckCircle2 className="h-3.5 w-3.5 shrink-0" />
                    <span>{test}</span>
                  </div>
                ))}
              </div>

              <div className="p-3 rounded-lg bg-bg/50 border border-white/5 text-ink-3 text-[11px]">
                {generationResult.explanation}
              </div>

              <Button
                variant="primary"
                size="md"
                onClick={() => {
                  onAdoptCircuit(generationResult.circuit);
                }}
                className="flex items-center justify-center gap-2 mt-1"
              >
                <CheckCircle2 className="h-4 w-4" />
                Load Generated Circuit into Composer
              </Button>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
