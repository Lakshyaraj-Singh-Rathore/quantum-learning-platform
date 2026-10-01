import { useState } from "react";
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
import { useTheme } from "../state/theme";
import { Button, Card, cn } from "../components/ui";

const TABS = [
  "Bit vs Qubit",
  "Build a Qubit",
  "Measure",
  "Interference",
  "|+⟩ vs |−⟩",
  "Many Qubits",
  "Bit Order",
] as const;

export function PlaygroundPage() {
  const [tab, setTab] = useState(0);

  return (
    <div className="flex flex-col gap-5 p-6">
      <div>
        <h2 className="text-xl font-semibold tracking-tight">Quantum Playground</h2>
        <p className="text-[13px] text-ink-3">
          Every control here changes a real quantum state. Nothing is pre-recorded: the Bloch
          sphere, amplitudes, probabilities and histogram are all computed from the state you
          build.
        </p>
      </div>
      <p className="rounded-lg border border-line bg-raised px-3 py-2 text-[13px] text-ink-2">
        These same demonstrations appear inside the lessons that teach them, under{" "}
        <strong className="text-ink">Try it yourself</strong>. This page collects them in one
        place for when you want to experiment without reading.
      </p>

      <div className="flex flex-wrap gap-1 border-b border-line pb-2">
        {TABS.map((label, index) => (
          <button
            key={label}
            onClick={() => setTab(index)}
            className={cn(
              "rounded-md px-3 py-1.5 text-[13px] transition-colors",
              tab === index ? "bg-accent/10 font-medium text-ink" : "text-ink-2 hover:bg-hover",
            )}
          >
            {label}
          </button>
        ))}
      </div>

      <Card>
        {tab === 0 && <BitVsQubit />}
        {tab === 1 && <BuildAQubit />}
        {tab === 2 && <MeasurementLab />}
        {tab === 3 && <InterferenceLab />}
        {tab === 4 && <PlusVsMinus />}
        {tab === 5 && <StateSpaceGrowth />}
        {tab === 6 && <BitOrdering />}
      </Card>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* 1. A bit picks a side. A qubit lives on a sphere.                          */
/* -------------------------------------------------------------------------- */

export function BitVsQubit() {
  const [bit, setBit] = useState(0);
  const [theta, setTheta] = useState(60);
  const state = stateFromAngles(theta, 0);
  const [p0, p1] = probs(state);

  return (
    <div className="flex flex-col gap-3">
      <h3 className="text-base font-semibold text-ink">
        A bit picks a side. A qubit lives on a sphere.
      </h3>
      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-lg border border-line p-3">
          <p className="mb-2 text-sm font-semibold text-ink">Classical bit</p>
          <div className="flex gap-1">
            {[0, 1].map((value) => (
              <button
                key={value}
                onClick={() => setBit(value)}
                className={cn(
                  "rounded-md border px-3 py-1 text-[13px]",
                  bit === value ? "border-accent bg-accent/10 text-ink" : "border-line text-ink-2",
                )}
              >
                {value}
              </button>
            ))}
          </div>
          <p className="mt-2 text-[13px] text-ink-2">
            Value <span className="font-mono text-ink">{bit}</span>
          </p>
          <p className="mt-1 text-[12px] text-ink-3">
            There is nothing in between. Reading it changes nothing.
          </p>
        </div>

        <div className="rounded-lg border border-line p-3">
          <p className="mb-2 text-sm font-semibold text-ink">Qubit</p>
          <label className="flex flex-col gap-1 text-[13px]">
            <span className="text-ink-2">
              θ — how far from |0⟩ toward |1⟩ ({theta.toFixed(0)}°)
            </span>
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
          <pre className="mt-2 overflow-auto rounded-lg border border-line-soft bg-hover/60 p-2 font-mono text-[12px] text-ink-2">
            {`|ψ⟩ = ${state[0][0].toFixed(3)}|0⟩ + ${state[1][0].toFixed(3)}|1⟩`}
          </pre>
          <div className="mt-2 grid grid-cols-2 gap-2">
            <Metric label="P(0)" value={p0.toLocaleString(undefined, { style: "percent", minimumFractionDigits: 1 })} />
            <Metric label="P(1)" value={p1.toLocaleString(undefined, { style: "percent", minimumFractionDigits: 1 })} />
          </div>
          <p className="mt-2 text-[12px] text-ink-3">
            Slide it anywhere. The qubit is genuinely in between — until you measure, which forces
            one of the two answers.
          </p>
        </div>
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-line bg-raised px-3 py-2">
      <p className="text-[11px] uppercase tracking-wide text-ink-3">{label}</p>
      <p className="font-mono text-sm text-ink">{value}</p>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* 2. Build a qubit: amplitudes, angles, and a circuit that rotates it        */
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
  const { theme } = useTheme();

  const length = Math.hypot(alpha, beta);
  let state =
    mode === "Amplitudes" ? stateFromAmplitudes(alpha, beta) : stateFromAngles(theta, phi);

  // Gates come off the real grid, so the learner sees the circuit they built
  // act on the state they dialled in.
  const { applied, skipped } = gatesFromIr(ir, 0);
  if (applied.length > 0) state = applyGates(state, applied);

  const [p0, p1] = probs(state);
  const [thetaOut, phiOut] = blochAnglesOf(state);
  const [x, y, z] = blochXYZ(state);

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h3 className="text-base font-semibold text-ink">Amplitudes are not probabilities</h3>
        <p className="text-[13px] text-ink-3">
          Amplitudes can be negative. Probabilities never are. Square the amplitude and the sign
          disappears — but the sign still matters, as the Interference tab shows.
        </p>
      </div>

      <div className="flex gap-1 rounded-lg border border-line bg-raised p-1">
        {(["Amplitudes", "Bloch angles"] as const).map((option) => (
          <button
            key={option}
            onClick={() => setMode(option)}
            className={cn(
              "flex-1 rounded-md px-3 py-1 text-[13px] transition-colors",
              mode === option ? "bg-accent text-white" : "text-ink-2 hover:bg-hover",
            )}
          >
            {option}
          </button>
        ))}
      </div>

      {mode === "Amplitudes" ? (
        <div className="grid gap-4 md:grid-cols-2">
          <Slider label={`Amplitude of |0⟩ (${alpha.toFixed(2)})`} value={alpha} min={-1} max={1} step={0.01} onChange={setAlpha} />
          <Slider label={`Amplitude of |1⟩ (${beta.toFixed(2)})`} value={beta} min={-1} max={1} step={0.01} onChange={setBeta} />
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          <Slider label={`θ (degrees) — ${theta.toFixed(0)}°`} value={theta} min={0} max={180} onChange={setTheta} />
          <Slider label={`φ (degrees) — ${phi.toFixed(0)}°`} value={phi} min={0} max={360} onChange={setPhi} />
        </div>
      )}

      {mode === "Amplitudes" && Math.abs(length - 1) > 0.01 && (
        <p className="rounded-lg border border-line bg-raised px-3 py-2 text-[13px] text-ink-2">
          Your numbers had length {length.toFixed(3)}, so they were rescaled to length 1.
          Probabilities must sum to 100%.
        </p>
      )}

      <div>
        <h4 className="mb-1 text-sm font-semibold text-ink">Then build a circuit</h4>
        <p className="mb-2 text-[13px] text-ink-3">
          Drag gates onto the wire. This is the same composer as the Composer page, so anything
          you build here carries over.
        </p>
        <div className={cn("composer-host", theme === "dark" && "dark")}>
          <ComposerInner key={epoch} value={ir} nQubits={ir.n_qubits} onChange={setIr} />
        </div>
        <div className="mt-2 flex flex-wrap items-center gap-3">
          <Button size="sm" onClick={() => resetCircuit(emptyCircuit(1))}>
            ↺ Clear the wire
          </Button>
          {applied.length > 0 && (
            <span className="text-[12px] text-ink-3">Applied to q0: {applied.join(" ── ")}</span>
          )}
        </div>
        <p className="mt-1 text-[11px] text-ink-3">{Object.values(GATE_HELP).join("; ")}</p>
      </div>

      {skipped.length > 0 && (
        <p className="rounded-lg border border-line bg-raised px-3 py-2 text-[13px] text-ink-2">
          This demo models a <strong className="text-ink">single qubit</strong>, so these were not
          applied: {[...new Set(skipped)].sort().join(", ")}. Try them in the Composer, where the
          full simulator runs.
        </p>
      )}

      <div>
        <h4 className="mb-2 text-sm font-semibold text-ink">The state</h4>
        <pre className="overflow-auto rounded-lg border border-line-soft bg-hover/60 p-3 font-mono text-[12px] text-ink-2">
          {ketExpression(
            state.map(([re, im]) => ({ re, im })),
            3,
          )?.expression ?? "0"}
        </pre>
        <div className="mt-2 grid grid-cols-2 gap-2 lg:grid-cols-4">
          <Metric label="P(0)" value={p0.toLocaleString(undefined, { style: "percent", minimumFractionDigits: 1 })} />
          <Metric label="P(1)" value={p1.toLocaleString(undefined, { style: "percent", minimumFractionDigits: 1 })} />
          <Metric label="θ" value={`${thetaOut.toFixed(1)}°`} />
          <Metric label="φ" value={`${phiOut.toFixed(1)}°`} />
        </div>
        <div className="mt-2 overflow-auto rounded-lg border border-line-soft">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-line bg-hover/40 text-left text-[11px] uppercase tracking-wide text-ink-3">
                <th className="px-3 py-1.5 font-medium">Basis</th>
                <th className="px-3 py-1.5 text-right font-medium">Amplitude</th>
                <th className="px-3 py-1.5 text-right font-medium">Probability</th>
              </tr>
            </thead>
            <tbody>
              {[
                ["|0⟩", state[0], p0],
                ["|1⟩", state[1], p1],
              ].map(([label, amplitude, probability]) => (
                <tr key={label as string} className="border-b border-line-soft/60 last:border-0">
                  <td className="px-3 py-1.5 font-mono text-ink-2">{label as string}</td>
                  <td className="px-3 py-1.5 text-right font-mono text-ink-2">
                    {formatComplex(amplitude as [number, number])}
                  </td>
                  <td className="px-3 py-1.5 text-right font-mono text-ink-2">
                    {(probability as number).toLocaleString(undefined, {
                      style: "percent",
                      minimumFractionDigits: 2,
                    })}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div>
        <h4 className="mb-2 text-sm font-semibold text-ink">On the Bloch sphere</h4>
        <div className="flex justify-center">
          <BlochCircle q={0} x={x} y={y} z={z} />
        </div>
      </div>
    </div>
  );
}

function formatComplex([re, im]: [number, number]): string {
  if (Math.abs(im) < 1e-9) return re.toFixed(4);
  return `${re.toFixed(4)}${im >= 0 ? "+" : "-"}i${Math.abs(im).toFixed(4)}`;
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
    <label className="flex flex-col gap-1 text-[13px]">
      <span className="text-ink-2">{label}</span>
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
