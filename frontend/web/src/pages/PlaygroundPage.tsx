import { useState } from "react";
import {
  Atom,
  Sliders,
  Beaker,
  Waves,
  PlusSquare,
  Layers,
  ArrowLeftRight,
  FlaskConical,
} from "lucide-react";
import { ComposerInner } from "@composer/Composer";
import {
  BitOrdering,
  InterferenceLab,
  MeasurementLab,
  PlusVsMinus,
  StateSpaceGrowth,
} from "../components/demos/Demos";
import { BlochCircle } from "../components/results/ResultsViews";
import {
  GATE_HELP,
  applyGates,
  blochAnglesOf,
  blochXYZ,
  probs,
  stateFromAmplitudes,
  stateFromAngles,
} from "../lib/demos";
import { gatesFromIr } from "../lib/playground";
import { ketExpression } from "../lib/quantum";
import { emptyCircuit, useCircuit } from "../state/circuit";
import { Button, Card, Tabs, TabsList, TabsTrigger, TabsContent, cn } from "../components/ui";

const TABS = [
  { id: "bit-vs-qubit", label: "Bit vs Qubit", icon: Atom },
  { id: "build-qubit", label: "Build a Qubit", icon: Sliders },
  { id: "measure", label: "Measurement", icon: Beaker },
  { id: "interference", label: "Interference", icon: Waves },
  { id: "plus-minus", label: "|+⟩ vs |−⟩", icon: PlusSquare },
  { id: "many-qubits", label: "State Growth", icon: Layers },
  { id: "bit-order", label: "Bit Ordering", icon: ArrowLeftRight },
] as const;

export function PlaygroundPage() {
  const [activeTab, setActiveTab] = useState<string>("bit-vs-qubit");

  return (
    <div className="flex flex-col gap-6 p-6 max-w-6xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-ink flex items-center gap-2.5">
          <FlaskConical className="h-6 w-6 text-accent" /> Quantum Interactive Playground
        </h1>
        <p className="text-sm text-ink-3 mt-1">
          Direct manipulation sandbox for quantum primitives. Every control updates live wavefunctions, density projections, and interference envelopes.
        </p>
      </div>

      <p className="rounded-xl border border-line bg-raised p-4 text-xs text-ink-2 leading-relaxed">
        These interactive models are identical to the inline simulators embedded in the curriculum. Here they are collected for direct experimentation without instructional prose.
      </p>

      {/* Tabs with Icons */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <div className="overflow-x-auto pb-1">
          <TabsList className="h-10 p-1 bg-subtle">
            {TABS.map(({ id, label, icon: Icon }) => (
              <TabsTrigger key={id} value={id} className="gap-2 text-xs py-1.5 px-3">
                <Icon className="h-3.5 w-3.5 text-accent" />
                {label}
              </TabsTrigger>
            ))}
          </TabsList>
        </div>

        <Card className="mt-4 p-6 min-h-[460px]">
          <TabsContent value="bit-vs-qubit">
            <BitVsQubit />
          </TabsContent>
          <TabsContent value="build-qubit">
            <BuildAQubit />
          </TabsContent>
          <TabsContent value="measure">
            <MeasurementLab />
          </TabsContent>
          <TabsContent value="interference">
            <InterferenceLab />
          </TabsContent>
          <TabsContent value="plus-minus">
            <PlusVsMinus />
          </TabsContent>
          <TabsContent value="many-qubits">
            <StateSpaceGrowth />
          </TabsContent>
          <TabsContent value="bit-order">
            <BitOrdering />
          </TabsContent>
        </Card>
      </Tabs>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* 1. Bit vs Qubit                                                            */
/* -------------------------------------------------------------------------- */
export function BitVsQubit() {
  const [bit, setBit] = useState(0);
  const [theta, setTheta] = useState(60);
  const state = stateFromAngles(theta, 0);
  const [p0, p1] = probs(state);

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-base font-bold text-ink">
          Classical Bits vs Quantum Superposition
        </h3>
        <p className="text-xs text-ink-3 mt-0.5">
          A classical bit is strictly deterministic (0 or 1). A qubit exists in a continuous complex state vector |ψ⟩ on the Bloch sphere until measured.
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2 pt-2">
        {/* Classical bit box */}
        <div className="rounded-xl border border-line bg-subtle/40 p-5 space-y-3">
          <p className="text-xs font-bold uppercase tracking-wider text-ink-3">Classical Discrete Bit</p>
          <div className="flex gap-2">
            {[0, 1].map((value) => (
              <button
                key={value}
                onClick={() => setBit(value)}
                className={cn(
                  "flex-1 rounded-lg border py-2 text-sm font-bold font-mono transition-colors",
                  bit === value
                    ? "border-accent bg-accent/20 text-accent-ink"
                    : "border-line bg-raised text-ink-2 hover:bg-hover",
                )}
              >
                Bit: {value}
              </button>
            ))}
          </div>
          <div className="pt-2 text-xs text-ink-2 space-y-1">
            <p>
              Current State: <span className="font-mono font-bold text-ink">{bit}</span>
            </p>
            <p className="text-ink-3">
              Deterministic. Reading or checking the bit does not disturb its physical state.
            </p>
          </div>
        </div>

        {/* Qubit box */}
        <div className="rounded-xl border border-line bg-subtle/40 p-5 space-y-3">
          <p className="text-xs font-bold uppercase tracking-wider text-ink-3">Quantum Statevector Qubit</p>
          <label className="flex flex-col gap-1.5 text-xs text-ink-2">
            <span>θ Angle ({theta.toFixed(0)}°) — Rotation from |0⟩ to |1⟩</span>
            <input
              type="range"
              min={0}
              max={180}
              step={1}
              value={theta}
              onChange={(e) => setTheta(Number(e.target.value))}
              className="accent-accent"
            />
          </label>

          <pre className="overflow-x-auto rounded-lg border border-line bg-raised p-2.5 font-mono text-xs text-ink">
            {`|ψ⟩ = ${state[0][0].toFixed(3)}|0⟩ + ${state[1][0].toFixed(3)}|1⟩`}
          </pre>

          <div className="grid grid-cols-2 gap-2 pt-1">
            <div className="rounded-lg border border-line bg-raised p-2 text-center">
              <span className="text-[10px] uppercase text-ink-3 font-semibold block">P(|0⟩)</span>
              <span className="text-sm font-mono font-bold text-ink">
                {p0.toLocaleString(undefined, { style: "percent", minimumFractionDigits: 1 })}
              </span>
            </div>
            <div className="rounded-lg border border-line bg-raised p-2 text-center">
              <span className="text-[10px] uppercase text-ink-3 font-semibold block">P(|1⟩)</span>
              <span className="text-sm font-mono font-bold text-ink">
                {p1.toLocaleString(undefined, { style: "percent", minimumFractionDigits: 1 })}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* 2. Build a Qubit                                                           */
/* -------------------------------------------------------------------------- */
export function BuildAQubit() {
  const [mode, setMode] = useState<"Amplitudes" | "Bloch angles">("Amplitudes");
  const [alpha, setAlpha] = useState(0.8);
  const [beta, setBeta] = useState(0.6);
  const [theta, setTheta] = useState(90);
  const [phi, setPhi] = useState(0);

  const ir = useCircuit((state) => state.ir);
  const setIr = useCircuit((state) => state.setIr);
  const epoch = useCircuit((state) => state.epoch);
  const resetCircuit = useCircuit((state) => state.reset);

  let state =
    mode === "Amplitudes" ? stateFromAmplitudes(alpha, beta) : stateFromAngles(theta, phi);

  const { applied } = gatesFromIr(ir, 0);
  if (applied.length > 0) state = applyGates(state, applied);

  const [p0, p1] = probs(state);
  const [thetaOut, phiOut] = blochAnglesOf(state);
  const [x, y, z] = blochXYZ(state);

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-base font-bold text-ink">Complex Amplitudes vs Probabilities</h3>
        <p className="text-xs text-ink-3 mt-0.5">
          Quantum amplitudes α, β can have negative or imaginary phases, creating interference before measurement squares them into real probabilities |α|² and |β|².
        </p>
      </div>

      <div className="flex gap-2">
        {(["Amplitudes", "Bloch angles"] as const).map((opt) => (
          <button
            key={opt}
            onClick={() => setMode(opt)}
            className={cn(
              "rounded-lg px-3 py-1.5 text-xs font-medium border transition-colors",
              mode === opt
                ? "border-accent bg-accent/15 text-accent font-semibold"
                : "border-line bg-subtle text-ink-2 hover:bg-hover",
            )}
          >
            Configure via {opt}
          </button>
        ))}
      </div>

      {mode === "Amplitudes" ? (
        <div className="grid gap-4 sm:grid-cols-2">
          <Slider label={`Amplitude α for |0⟩: ${alpha.toFixed(2)}`} value={alpha} min={-1} max={1} step={0.01} onChange={setAlpha} />
          <Slider label={`Amplitude β for |1⟩: ${beta.toFixed(2)}`} value={beta} min={-1} max={1} step={0.01} onChange={setBeta} />
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          <Slider label={`θ (colatitude): ${theta.toFixed(0)}°`} value={theta} min={0} max={180} onChange={setTheta} />
          <Slider label={`φ (longitude): ${phi.toFixed(0)}°`} value={phi} min={0} max={360} onChange={setPhi} />
        </div>
      )}

      {/* Wire manipulation */}
      <div className="space-y-3 pt-2">
        <h4 className="text-xs font-bold uppercase tracking-wider text-ink-3">
          Apply Unitary Operations on Canvas
        </h4>
        <div className="composer-host dark rounded-xl border border-line bg-subtle p-3 overflow-x-auto">
          <ComposerInner key={epoch} value={ir} nQubits={ir.n_qubits} onChange={setIr} theme={{ base: "dark" }} />
        </div>
        <div className="flex items-center gap-3">
          <Button size="sm" variant="secondary" onClick={() => resetCircuit(emptyCircuit(1))} className="text-xs">
            Reset Wire
          </Button>
          {applied.length > 0 && (
            <span className="text-xs font-mono text-ink-3">Operations: {applied.join(" → ")}</span>
          )}
        </div>

        {/* Clean Gate Definition List (Replacing comma-separated string) */}
        <div className="rounded-xl border border-line bg-subtle/50 p-4 mt-3">
          <h5 className="text-[11px] font-bold uppercase tracking-wider text-ink-3 mb-2">
            Unitary Gate Mechanics Reference
          </h5>
          <dl className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5 text-xs">
            {Object.entries(GATE_HELP).map(([gate, desc]) => (
              <div key={gate} className="rounded-md border border-line-soft bg-raised p-2">
                <dt className="font-mono font-bold text-accent">{gate.toUpperCase()}</dt>
                <dd className="text-ink-3 text-[11px] mt-0.5">{desc}</dd>
              </div>
            ))}
          </dl>
        </div>
      </div>

      {/* Statevector & Bloch Projection */}
      <div className="grid gap-6 md:grid-cols-2 pt-2 border-t border-line-soft">
        <div className="space-y-3">
          <h4 className="text-xs font-bold uppercase tracking-wider text-ink-3">State Vector Metrics</h4>
          <pre className="overflow-x-auto rounded-lg border border-line bg-raised p-3 font-mono text-xs text-ink">
            {ketExpression(state.map(([re, im]) => ({ re, im })), 3)?.expression ?? "0"}
          </pre>
          <div className="grid grid-cols-2 gap-2 text-center text-xs">
            <div className="rounded border border-line bg-raised p-2">
              <span className="text-[10px] text-ink-3 block">P(|0⟩)</span>
              <span className="font-mono font-bold text-ink">{p0.toLocaleString(undefined, { style: "percent", minimumFractionDigits: 1 })}</span>
            </div>
            <div className="rounded border border-line bg-raised p-2">
              <span className="text-[10px] text-ink-3 block">P(|1⟩)</span>
              <span className="font-mono font-bold text-ink">{p1.toLocaleString(undefined, { style: "percent", minimumFractionDigits: 1 })}</span>
            </div>
            <div className="rounded border border-line bg-raised p-2">
              <span className="text-[10px] text-ink-3 block">Bloch θ</span>
              <span className="font-mono font-bold text-ink">{thetaOut.toFixed(1)}°</span>
            </div>
            <div className="rounded border border-line bg-raised p-2">
              <span className="text-[10px] text-ink-3 block">Bloch φ</span>
              <span className="font-mono font-bold text-ink">{phiOut.toFixed(1)}°</span>
            </div>
          </div>
        </div>

        <div className="space-y-2 flex flex-col items-center justify-center">
          <h4 className="text-xs font-bold uppercase tracking-wider text-ink-3 self-start">Bloch Sphere Projection</h4>
          <BlochCircle q={0} x={x} y={y} z={z} />
        </div>
      </div>
    </div>
  );
}

function Slider({
  label,
  value,
  min,
  max,
  step = 1,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step?: number;
  onChange: (value: number) => void;
}) {
  return (
    <label className="flex flex-col gap-1.5 text-xs text-ink-2">
      <span>{label}</span>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="accent-accent"
      />
    </label>
  );
}
