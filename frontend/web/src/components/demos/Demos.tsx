/**
 * The lesson demos, ported from frontend/lib/lesson_demos.py.
 *
 * Each one is self-contained and computes its own state: nothing here is a
 * recording, and the numbers are the ones the golden fixtures pin. The maths
 * lives in src/lib/demos.ts and src/lib/quantum.ts.
 *
 * `circuit_lab` is the exception — see the note on it at the bottom.
 */
import { useState } from "react";
import { ExternalLink } from "lucide-react";
import { Link } from "react-router-dom";
import { ComposerInner } from "@composer/Composer";
import { maxLayer } from "@composer/ir";
import { ketExpression } from "../../lib/quantum";
import {
  GATES,
  GATE_HELP,
  LANDMARKS,
  SQRT1_2,
  applyGates,
  bitstringTable,
  blochAnglesOf,
  blochXYZ,
  collapse,
  interference,
  probs,
  sample,
  stateFromAmplitudes,
  stateFromAngles,
  stateSpaceRows,
  type Statevector,
} from "../../lib/demos";
import { BlochCircle } from "../results/ResultsViews";
import { Button, cn } from "../ui";
import { emptyCircuit, useCircuit } from "../../state/circuit";
import { useTheme } from "../../state/theme";

/* -------------------------------------------------------------------------- */
/* small shared pieces                                                        */
/* -------------------------------------------------------------------------- */

function Slider({
  label,
  value,
  min,
  max,
  step = 1,
  disabled,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step?: number;
  disabled?: boolean;
  onChange: (value: number) => void;
}) {
  return (
    <label className={cn("flex flex-col gap-1 text-[13px]", disabled && "opacity-50")}>
      <span className="text-ink-2">{label}</span>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(Number(e.target.value))}
        className="accent-accent"
      />
    </label>
  );
}

function Metric({ label, value, delta }: { label: string; value: string; delta?: string }) {
  return (
    <div className="rounded-lg border border-line bg-raised px-3 py-2">
      <p className="text-[11px] uppercase tracking-wide text-ink-3">{label}</p>
      <p className="font-mono text-sm text-ink">{value}</p>
      {delta && <p className="text-[11px] text-ink-3">{delta}</p>}
    </div>
  );
}

function Note({ tone = "info", children }: { tone?: "info" | "good" | "warn"; children: React.ReactNode }) {
  const tones = {
    info: "border-line bg-raised text-ink-2",
    good: "border-ok/40 bg-ok/10 text-ink",
    warn: "border-warn/40 bg-warn/10 text-ink",
  } as const;
  return <p className={cn("rounded-lg border px-3 py-2 text-[13px] leading-relaxed", tones[tone])}>{children}</p>;
}

/** A state, written as |ψ⟩ = … using the golden-tested formatter. */
function ketOf(state: Statevector): string {
  const built = ketExpression(
    state.map(([re, im]) => ({ re, im })),
    3,
  );
  return built ? `|ψ⟩ = ${built.expression}` : "|ψ⟩ = 0";
}

function Ket({ state }: { state: Statevector }) {
  return (
    <pre className="overflow-auto rounded-lg border border-line-soft bg-hover/60 p-3 font-mono text-[12px] text-ink-2">
      {ketOf(state)}
    </pre>
  );
}

export function CountsBar({ counts }: { counts: Record<string, number> }) {
  const total = Object.values(counts).reduce((a, b) => a + b, 0) || 1;
  return (
    <div className="flex flex-col gap-2">
      {Object.entries(counts).map(([key, value]) => (
        <div key={key} className="flex items-center gap-2">
          <span className="w-8 font-mono text-[13px] text-ink-2">|{key}⟩</span>
          <div className="h-4 flex-1 overflow-hidden rounded bg-hover">
            <div
              className="h-full bg-accent"
              style={{ width: `${(value / total) * 100}%` }}
            />
          </div>
          <span className="w-24 text-right font-mono text-[12px] text-ink-3">
            {value} · {((value / total) * 100).toFixed(1)}%
          </span>
        </div>
      ))}
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* 01 qubits                                                                  */
/* -------------------------------------------------------------------------- */

function BitVsQubit() {
  const [bit, setBit] = useState(0);
  const [theta, setTheta] = useState(90);
  const [observed, setObserved] = useState<number | null>(null);
  const [history, setHistory] = useState<number[]>([]);

  const prepared = stateFromAngles(theta, 0);
  const state: Statevector =
    observed === null ? prepared : observed === 0 ? [[1, 0], [0, 0]] : [[0, 0], [1, 0]];
  const [p0, p1] = probs(state);

  function measure() {
    const outcome = collapse(prepared);
    setObserved(outcome);
    setHistory((prev) => [...prev, outcome]);
  }

  return (
    <div className="flex flex-col gap-3">
      <p className="text-[13px] text-ink-3">
        A classical bit has two options. A qubit has infinitely many — but only until you
        look at it.
      </p>
      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-lg border border-line p-3">
          <p className="mb-2 text-sm font-semibold text-ink">Classical bit</p>
          <div className="flex gap-1">
            {[0, 1].map((v) => (
              <button
                key={v}
                onClick={() => setBit(v)}
                className={cn(
                  "rounded-md border px-3 py-1 text-[13px]",
                  bit === v ? "border-accent bg-accent/10 text-ink" : "border-line text-ink-2",
                )}
              >
                {v}
              </button>
            ))}
          </div>
          <p className="mt-2 text-[13px] text-ink-2">
            Reads as <strong className="font-mono text-ink">{bit}</strong>
          </p>
          <p className="mt-1 text-[12px] text-ink-3">
            Reading it changes nothing. Read it a million times and it is still the value you
            set.
          </p>
        </div>

        <div className="rounded-lg border border-line p-3">
          <p className="mb-2 text-sm font-semibold text-ink">Qubit</p>
          <Slider
            label={`θ — how far from |0⟩ toward |1⟩ (${theta.toFixed(0)}°)`}
            value={theta}
            min={0}
            max={180}
            disabled={observed !== null}
            onChange={setTheta}
          />
          <p className="mt-1 text-[12px] text-ink-3">
            Locked while the qubit is collapsed — reset it to move again.
          </p>
          <div className="mt-2">
            <Ket state={state} />
          </div>
          <div className="mt-2 grid grid-cols-2 gap-2">
            <Metric label="P(0)" value={p0.toLocaleString(undefined, { style: "percent", minimumFractionDigits: 1 })} />
            <Metric label="P(1)" value={p1.toLocaleString(undefined, { style: "percent", minimumFractionDigits: 1 })} />
          </div>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Button size="sm" variant="primary" onClick={measure} disabled={observed !== null}>
          🔬 Measure the qubit
        </Button>
        <Button size="sm" onClick={() => setObserved(null)} disabled={observed === null}>
          ♻ Reset qubit
        </Button>
        {history.length > 0 && (
          <>
            <span className="text-[12px] text-ink-3">
              <strong className="text-ink">{history.length}</strong> measurement(s):{" "}
              <strong className="text-ink">{history.filter((h) => h === 0).length}</strong> zeros,{" "}
              <strong className="text-ink">{history.filter((h) => h === 1).length}</strong> ones{" "}
              <code className="font-mono">{history.slice(-24).join(" ")}</code>
            </span>
            <Button size="sm" onClick={() => setHistory([])}>
              Clear the record
            </Button>
          </>
        )}
      </div>

      {observed === null ? (
        <Note>
          The qubit is in <strong>superposition</strong>. It has no value yet — not a hidden one
          you cannot see, genuinely none. Press <strong>Measure</strong> and it is forced to
          choose.
        </Note>
      ) : (
        <>
          <Note tone="good">
            <strong>
              Collapsed to |{observed}⟩.
            </strong>{" "}
            The superposition is gone. Measure again and you will get {observed} every time —
            the state really did change when you looked. Press <strong>Reset</strong> for a fresh
            qubit.
          </Note>
          {history.length >= 4 && (
            <p className="text-[12px] text-ink-3">
              Across {history.length} prepare-and-measure cycles you have seen{" "}
              {history.filter((h) => h === 0).length} zeros and{" "}
              {history.filter((h) => h === 1).length} ones. Individual results are
              unpredictable; the proportion is not.
            </p>
          )}
        </>
      )}
    </div>
  );
}

function BuildAQubit() {
  const [alpha, setAlpha] = useState(0.8);
  const [beta, setBeta] = useState(0.6);
  const length = Math.hypot(alpha, beta);
  const state = stateFromAmplitudes(alpha, beta);
  const [p0, p1] = probs(state);

  return (
    <div className="flex flex-col gap-3">
      <p className="text-[13px] text-ink-3">
        Amplitudes can be negative; probabilities never are. Squaring hides the sign — but the
        sign still matters, as interference shows.
      </p>
      <div className="grid gap-4 md:grid-cols-2">
        <Slider label={`Amplitude of |0⟩ (${alpha.toFixed(2)})`} value={alpha} min={-1} max={1} step={0.01} onChange={setAlpha} />
        <Slider label={`Amplitude of |1⟩ (${beta.toFixed(2)})`} value={beta} min={-1} max={1} step={0.01} onChange={setBeta} />
      </div>
      {Math.abs(length - 1) > 0.01 && (
        <Note>
          Your numbers had length {length.toFixed(3)}, so they were rescaled to 1. Probabilities
          have to sum to 100%.
        </Note>
      )}
      <Ket state={state} />
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-line text-left text-[11px] uppercase tracking-wide text-ink-3">
            <th className="py-2 pr-3 font-medium">Basis</th>
            <th className="py-2 pr-3 text-right font-medium">Amplitude</th>
            <th className="py-2 pr-3 text-right font-medium">Squared</th>
            <th className="py-2 text-right font-medium">Probability</th>
          </tr>
        </thead>
        <tbody>
          {[
            ["|0⟩", state[0][0], p0],
            ["|1⟩", state[1][0], p1],
          ].map(([label, amp, prob]) => (
            <tr key={label as string} className="border-b border-line-soft/60">
              <td className="py-1.5 font-mono">{label as string}</td>
              <td className="py-1.5 text-right font-mono">
                {(amp as number) >= 0 ? "+" : ""}
                {(amp as number).toFixed(3)}
              </td>
              <td className="py-1.5 text-right font-mono">{(prob as number).toFixed(3)}</td>
              <td className="py-1.5 text-right font-mono">
                {(prob as number).toLocaleString(undefined, { style: "percent", minimumFractionDigits: 1 })}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {alpha * beta < 0 && (
        <Note tone="good">
          One amplitude is negative, yet both probabilities are positive. That hidden sign is
          what makes interference possible.
        </Note>
      )}
    </div>
  );
}

function BlochExplorer() {
  const [theta, setTheta] = useState(90);
  const [phi, setPhi] = useState(0);
  const [preset, setPreset] = useState("(custom)");

  const [t, p] = preset !== "(custom)" ? LANDMARKS[preset] : [theta, phi];
  const state = stateFromAngles(t, p);
  const [p0, p1] = probs(state);
  const [x, y, z] = blochXYZ(state);

  return (
    <div className="flex flex-col gap-3">
      <p className="text-[13px] text-ink-3">
        Every pure single-qubit state is a point on this sphere. |0⟩ is the north pole, |1⟩ the
        south, and the equator is where measurement is a coin flip.
      </p>
      <div className="grid gap-4 md:grid-cols-3">
        <Slider
          label={`θ (degrees) — ${t.toFixed(0)}°`}
          value={t}
          min={0}
          max={180}
          onChange={(v) => {
            setTheta(v);
            setPreset("(custom)");
          }}
        />
        <Slider
          label={`φ (degrees) — ${p.toFixed(0)}°`}
          value={p}
          min={0}
          max={360}
          onChange={(v) => {
            setPhi(v);
            setPreset("(custom)");
          }}
        />
        <label className="flex flex-col gap-1 text-[13px]">
          <span className="text-ink-2">…or jump to a landmark</span>
          <select
            value={preset}
            onChange={(e) => setPreset(e.target.value)}
            className="h-9 rounded-lg border border-line bg-raised px-2 text-sm text-ink"
          >
            <option value="(custom)">(custom)</option>
            {Object.keys(LANDMARKS).map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </label>
      </div>
      {preset !== "(custom)" && (
        <p className="text-[12px] text-ink-3">
          Showing <strong className="text-ink">{preset}</strong> at θ={t.toFixed(0)}°, φ=
          {p.toFixed(0)}°.
        </p>
      )}
      <Ket state={state} />
      <div className="grid grid-cols-2 gap-2">
        <Metric label="P(0)" value={p0.toLocaleString(undefined, { style: "percent", minimumFractionDigits: 1 })} />
        <Metric label="P(1)" value={p1.toLocaleString(undefined, { style: "percent", minimumFractionDigits: 1 })} />
      </div>
      <div className="flex justify-center">
        <BlochCircle q={0} x={x} y={y} z={z} />
      </div>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* 02 gates / 10 gates bootcamp                                               */
/* -------------------------------------------------------------------------- */

function GateSandbox() {
  const [start, setStart] = useState("|0⟩");
  const [gates, setGates] = useState<string[]>([]);

  const [theta, phi] = LANDMARKS[start];
  const initial = stateFromAngles(theta, phi);
  const before = probs(initial);
  const state = gates.length > 0 ? applyGates(initial, gates) : initial;
  const after = probs(state);
  const [thetaOut, phiOut] = blochAnglesOf(state);
  const [x, y, z] = blochXYZ(state);

  function toggle(gate: string) {
    setGates((prev) => (prev.includes(gate) ? prev.filter((g) => g !== gate) : [...prev, gate]));
  }

  return (
    <div className="flex flex-col gap-3">
      <p className="text-[13px] text-ink-3">
        Gates rotate the state on the Bloch sphere. Stack a few and watch where the arrow ends
        up.
      </p>
      <div className="grid gap-4 md:grid-cols-[1fr_2fr]">
        <label className="flex flex-col gap-1 text-[13px]">
          <span className="text-ink-2">Start from</span>
          <select
            value={start}
            onChange={(e) => setStart(e.target.value)}
            className="h-9 rounded-lg border border-line bg-raised px-2 text-sm text-ink"
          >
            {Object.keys(LANDMARKS).map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </label>
        <div className="flex flex-col gap-1">
          <span className="text-[13px] text-ink-2">
            Apply gates, left to right (like a circuit wire)
          </span>
          <div className="flex flex-wrap gap-1">
            {Object.keys(GATES).map((gate) => (
              <button
                key={gate}
                onClick={() => toggle(gate)}
                title={GATE_HELP[gate]}
                className={cn(
                  "rounded-md border px-2.5 py-1 font-mono text-[13px]",
                  gates.includes(gate)
                    ? "border-accent bg-accent/10 text-ink"
                    : "border-line text-ink-2 hover:bg-hover",
                )}
              >
                {gate}
              </button>
            ))}
          </div>
          <p className="text-[12px] text-ink-3">{Object.values(GATE_HELP).join("; ")}</p>
        </div>
      </div>

      <pre className="overflow-auto rounded-lg border border-line-soft bg-hover/60 p-3 font-mono text-[12px] text-ink-2">
        {gates.length > 0 ? ["|ψ⟩", ...gates].join(" ── ") : "|ψ⟩ (no gates yet)"}
        {"\n\n"}
        {ketOf(state)}
      </pre>

      <div className="grid grid-cols-3 gap-2">
        <Metric
          label="P(0)"
          value={after[0].toLocaleString(undefined, { style: "percent", minimumFractionDigits: 1 })}
          delta={`${((after[0] - before[0]) * 100).toFixed(1)} pts`}
        />
        <Metric
          label="P(1)"
          value={after[1].toLocaleString(undefined, { style: "percent", minimumFractionDigits: 1 })}
          delta={`${((after[1] - before[1]) * 100).toFixed(1)} pts`}
        />
        <Metric label="θ, φ" value={`${thetaOut.toFixed(0)}°, ${phiOut.toFixed(0)}°`} />
      </div>
      <div className="flex justify-center">
        <BlochCircle q={0} x={x} y={y} z={z} />
      </div>
    </div>
  );
}

/** Also reused by the Playground, which collects the demos in one place. */
export function PlusVsMinus() {
  const [applyH, setApplyH] = useState(false);
  let plus = stateFromAngles(90, 0);
  let minus = stateFromAngles(90, 180);
  if (applyH) {
    plus = applyGates(plus, ["H"]);
    minus = applyGates(minus, ["H"]);
  }

  return (
    <div className="flex flex-col gap-3">
      <p className="text-[13px] text-ink-3">
        These two states are indistinguishable when you measure them, yet one more gate tells
        them apart. This is why phase is real information.
      </p>
      <label className="flex items-center gap-2 text-[13px] text-ink-2">
        <input type="checkbox" checked={applyH} onChange={(e) => setApplyH(e.target.checked)} className="accent-accent" />
        Apply H to both
      </label>
      <div className="grid gap-4 md:grid-cols-2">
        {[
          [applyH ? "H|+⟩" : "|+⟩", plus],
          [applyH ? "H|−⟩" : "|−⟩", minus],
        ].map(([name, state]) => {
          const [p0, p1] = probs(state as Statevector);
          return (
            <div key={name as string} className="rounded-lg border border-line p-3">
              <p className="mb-2 text-sm font-semibold text-ink">{name as string}</p>
              <Ket state={state as Statevector} />
              <p className="mt-2 text-[13px] text-ink-2">
                P(0) ={" "}
                <strong className="text-ink">
                  {p0.toLocaleString(undefined, { style: "percent", maximumFractionDigits: 0 })}
                </strong>{" "}
                · P(1) ={" "}
                <strong className="text-ink">
                  {p1.toLocaleString(undefined, { style: "percent", maximumFractionDigits: 0 })}
                </strong>
              </p>
            </div>
          );
        })}
      </div>
      {applyH ? (
        <Note tone="good">
          <strong>H|+⟩ = |0⟩ and H|−⟩ = |1⟩.</strong> The relative phase was carrying information
          the whole time; one gate turned it into something you can measure.
        </Note>
      ) : (
        <Note tone="warn">
          Both give 50/50 in the computational basis. A histogram alone can never tell them apart
          — toggle the switch above.
        </Note>
      )}
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* 04 measurement                                                             */
/* -------------------------------------------------------------------------- */

/** Also reused by the Playground, which collects the demos in one place. */
export function MeasurementLab() {
  const [theta, setTheta] = useState(90);
  const [shots, setShots] = useState(1024);
  const [seed, setSeed] = useState(0);

  const state = stateFromAngles(theta, 0);
  const [p0] = probs(state);
  const counts = sample(state, shots, seed);
  const observed = counts["0"] / Math.max(shots, 1);
  const observed1 = counts["1"] / Math.max(shots, 1);

  return (
    <div className="flex flex-col gap-3">
      <p className="text-[13px] text-ink-3">
        You cannot predict one shot. You can predict the distribution — and even that only
        approximately, from a finite number of shots.
      </p>
      <div className="grid gap-4 md:grid-cols-3">
        <Slider label={`θ (degrees) — ${theta.toFixed(0)}°`} value={theta} min={0} max={180} onChange={setTheta} />
        <label className="flex flex-col gap-1 text-[13px]">
          <span className="text-ink-2">Shots — {shots}</span>
          <input
            type="range"
            min={0}
            max={4}
            step={1}
            value={[1, 10, 100, 1024, 4096].indexOf(shots)}
            onChange={(e) => setShots([1, 10, 100, 1024, 4096][Number(e.target.value)])}
            className="accent-accent"
          />
        </label>
        <div className="flex items-end">
          <Button size="sm" onClick={() => setSeed((s) => s + 1)}>
            🎲 Run again
          </Button>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-2 md:grid-cols-5">
        <Metric label="Theory P(0)" value={p0.toLocaleString(undefined, { style: "percent", minimumFractionDigits: 1 })} />
        <Metric
          label="Observed P(0)"
          value={observed.toLocaleString(undefined, { style: "percent", minimumFractionDigits: 1 })}
          delta={`${((observed - p0) * 100).toFixed(1)} pts`}
        />
        <Metric label="Theory P(1)" value={(1 - p0).toLocaleString(undefined, { style: "percent", minimumFractionDigits: 1 })} />
        <Metric
          label="Observed P(1)"
          value={observed1.toLocaleString(undefined, { style: "percent", minimumFractionDigits: 1 })}
          delta={`${((observed1 - (1 - p0)) * 100).toFixed(1)} pts`}
        />
        <Metric label="Shots" value={String(shots)} />
      </div>
      <CountsBar counts={counts} />
      <p className="text-[12px] text-ink-3">
        The gap between theory and observation is sampling error. Try 1 shot, then 4096, and
        watch it shrink.
      </p>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* 05 deutsch-jozsa / 06 grover                                               */
/* -------------------------------------------------------------------------- */

/** Also reused by the Playground, which collects the demos in one place. */
export function InterferenceLab() {
  const [ampA, setAmpA] = useState(SQRT1_2);
  const [ampB, setAmpB] = useState(-SQRT1_2);
  const result = interference(ampA, ampB);

  return (
    <div className="flex flex-col gap-3">
      <p className="text-[13px] text-ink-3">
        Two paths lead to the same outcome. Quantum mechanics adds their amplitudes first and
        squares afterwards — which is how an outcome can be cancelled entirely.
      </p>
      <div className="grid gap-4 md:grid-cols-2">
        <Slider label={`Path A amplitude (${ampA.toFixed(3)})`} value={ampA} min={-1} max={1} step={0.01} onChange={setAmpA} />
        <Slider label={`Path B amplitude (${ampB.toFixed(3)})`} value={ampB} min={-1} max={1} step={0.01} onChange={setAmpB} />
      </div>
      <pre className="overflow-auto rounded-lg border border-line-soft bg-hover/60 p-3 font-mono text-[12px] text-ink-2">
        {`  Path A : ${ampA >= 0 ? "+" : ""}${ampA.toFixed(3)}
  Path B : ${ampB >= 0 ? "+" : ""}${ampB.toFixed(3)}
  ─────────────────
  Total  : ${result.amplitude >= 0 ? "+" : ""}${result.amplitude.toFixed(3)}

  Quantum   = (${result.amplitude >= 0 ? "+" : ""}${result.amplitude.toFixed(3)})² = ${result.probability.toFixed(3)}
  Classical = ${result.classical.toFixed(3)}`}
      </pre>
      <div className="grid grid-cols-2 gap-2">
        <Metric label="Quantum P" value={result.probability.toFixed(3)} />
        <Metric
          label="Classical P"
          value={result.classical.toFixed(3)}
          delta={`${(result.probability - result.classical).toFixed(3)}`}
        />
      </div>
      {result.probability < 0.01 ? (
        <Note tone="good">
          <strong>Perfect destructive interference.</strong> Two real paths lead here and the
          outcome never occurs. Classically impossible: two non-negative probabilities can never
          sum to zero.
        </Note>
      ) : result.probability > result.classical + 0.01 ? (
        <Note>
          <strong>Constructive interference</strong> — the paths reinforce each other.
        </Note>
      ) : null}
      <p className="text-[12px] text-ink-3">
        Grover&apos;s algorithm is this on repeat: destructive interference on the wrong answers,
        constructive on the right one.
      </p>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* 03 entanglement / 11 bell states                                           */
/* -------------------------------------------------------------------------- */

/** Also reused by the Playground, which collects the demos in one place. */
export function StateSpaceGrowth() {
  const [n, setN] = useState(10);
  const states = 2 ** n;
  const memory = (states * 16) / 1e6;
  const rows = stateSpaceRows(Math.min(n, 20));
  const peak = Math.max(...rows.map((r) => r.states)) || 1;

  return (
    <div className="flex flex-col gap-3">
      <p className="text-[13px] text-ink-3">
        A classical n-bit register holds ONE of 2ⁿ values. An n-qubit state needs ALL 2ⁿ
        amplitudes at once.
      </p>
      <Slider label={`Number of qubits — ${n}`} value={n} min={1} max={30} onChange={setN} />
      <div className="grid grid-cols-3 gap-2">
        <Metric label="Amplitudes to track" value={states.toLocaleString()} />
        <Metric label="Memory for the state" value={`${memory.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} MB`} />
        <Metric label="Classical bits for one value" value={String(n)} />
      </div>
      <div className="flex h-32 items-end gap-1">
        {rows.map((row) => (
          <div
            key={row.qubits}
            className="flex-1 rounded-t bg-accent/70"
            style={{ height: `${Math.max(2, (row.states / peak) * 100)}%` }}
            title={`${row.qubits} qubits → ${row.states.toLocaleString()} amplitudes`}
          />
        ))}
      </div>
      <p className="text-[11px] text-ink-3">
        qubits → amplitudes, 1 to {Math.min(n, 20)}
      </p>
      {n >= 20 && (
        <Note tone="warn">
          At {n} qubits the amplitudes alone need {memory.toLocaleString(undefined, { maximumFractionDigits: 0 })} MB.
          This platform caps static simulation at 20 qubits for exactly this reason — the cost
          doubles with every qubit.
        </Note>
      )}
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* 04 measurement / 12 control flow                                           */
/* -------------------------------------------------------------------------- */

/** Also reused by the Playground, which collects the demos in one place. */
export function BitOrdering() {
  const [nBits, setNBits] = useState(3);
  const [value, setValue] = useState(1);
  const bits = value.toString(2).padStart(nBits, "0");
  const rows = bitstringTable(value, nBits);

  return (
    <div className="flex flex-col gap-3">
      <p className="text-[13px] text-ink-3">
        This platform follows the Qiskit convention. Reading a bitstring the wrong way round is a
        common mistake, and it fails silently.
      </p>
      <div className="grid gap-4 md:grid-cols-2">
        <Slider
          label={`Qubits — ${nBits}`}
          value={nBits}
          min={2}
          max={5}
          onChange={(v) => {
            setNBits(v);
            setValue((prev) => Math.min(prev, 2 ** v - 1));
          }}
        />
        <Slider label={`Bitstring value — ${value}`} value={value} min={0} max={2 ** nBits - 1} onChange={setValue} />
      </div>
      <pre className="rounded-lg border border-line-soft bg-hover/60 p-3 font-mono text-[12px] text-ink-2">
        {`bitstring:  ${bits}`}
      </pre>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-line text-left text-[11px] uppercase tracking-wide text-ink-3">
            <th className="py-2 pr-3 font-medium">Qubit</th>
            <th className="py-2 pr-3 text-right font-medium">Value</th>
            <th className="py-2 pr-3 font-medium">Position in string</th>
            <th className="py-2 font-medium">Is qubit 0?</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.qubit} className="border-b border-line-soft/60">
              <td className="py-1.5 font-mono">{row.qubit}</td>
              <td className="py-1.5 text-right font-mono">{row.value}</td>
              <td className="py-1.5 text-ink-3">{row.position}</td>
              <td className="py-1.5 text-ink-2">{row.rightmost ? "← yes, rightmost" : ""}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <Note>
        <code className="font-mono">{bits}</code> means q0 = <strong>{bits[bits.length - 1]}</strong>.
        Reading left to right would wrongly give q0 = {bits[0]}.
      </Note>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Circuit lab                                                                */
/* -------------------------------------------------------------------------- */

/**
 * The real drag-and-drop grid, in the lesson — the same component the Composer
 * uses, reading and writing the same session circuit, so a circuit built here
 * is still there when the learner opens the Composer to run it. This is the
 * Streamlit behaviour, and it is why the circuit moved into a shared store.
 *
 * It deliberately does not mount the whole Composer page: the page owns run
 * settings and results, and this is a lesson.
 */
function CircuitLab() {
  const ir = useCircuit((state) => state.ir);
  const epoch = useCircuit((state) => state.epoch);
  const setIr = useCircuit((state) => state.setIr);
  const resetCircuit = useCircuit((state) => state.reset);
  const { theme } = useTheme();
  const depth = maxLayer(ir.ops) + 1;

  return (
    <div className="flex flex-col gap-3">
      <p className="text-[13px] text-ink-3">
        The real composer, right here. Drag a gate onto the grid, or click a gate then a cell.
        This shares the same circuit as the Composer page, so you can carry your work over to
        run and export it.
      </p>
      <div className={cn("composer-host", theme === "dark" && "dark")}>
        <ComposerInner key={epoch} value={ir} nQubits={ir.n_qubits} onChange={setIr} />
      </div>
      <div className="grid grid-cols-3 gap-2">
        <Metric label="Qubits" value={String(ir.n_qubits)} />
        <Metric label="Operations" value={String(ir.ops.length)} />
        <Metric label="Depth" value={String(depth)} />
      </div>
      <div className="flex flex-wrap gap-2">
        <Button size="sm" onClick={() => resetCircuit(emptyCircuit(ir.n_qubits))}>
          ↺ Clear this circuit
        </Button>
        <Link to="/composer">
          <Button size="sm" variant="primary">
            <ExternalLink className="h-3.5 w-3.5" />
            Run it on a simulator
          </Button>
        </Link>
      </div>
      <p className="text-[12px] text-ink-3">
        Open the <strong>Composer</strong> page to run this on a simulator, inspect the state,
        or export it as Qiskit, Cirq, PennyLane or OpenQASM.
      </p>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Registry — mirrors DEMO_REGISTRY in frontend/lib/lesson_demos.py           */
/* -------------------------------------------------------------------------- */

export const DEMOS: Record<
  string,
  { title: string; blurb: string; Component: () => JSX.Element }
> = {
  bit_vs_qubit: {
    title: "A bit versus a qubit",
    blurb: "Discrete choice against a continuum",
    Component: BitVsQubit,
  },
  build_a_qubit: {
    title: "Amplitude is not probability",
    blurb: "Square the amplitude to get the probability",
    Component: BuildAQubit,
  },
  bloch: {
    title: "Explore the Bloch sphere",
    blurb: "Move θ and φ and watch the state follow",
    Component: BlochExplorer,
  },
  gates: {
    title: "Gate sandbox",
    blurb: "Stack gates and watch the state rotate",
    Component: GateSandbox,
  },
  plus_minus: {
    title: "|+⟩ versus |−⟩",
    blurb: "Same histogram, different physics",
    Component: PlusVsMinus,
  },
  measure: {
    title: "Measurement and sampling error",
    blurb: "Theory against a finite number of shots",
    Component: MeasurementLab,
  },
  interference: {
    title: "Interference lab",
    blurb: "Amplitudes add before they are squared",
    Component: InterferenceLab,
  },
  state_space: {
    title: "Exponential state space",
    blurb: "Why 2ⁿ gets out of hand",
    Component: StateSpaceGrowth,
  },
  bit_order: {
    title: "Bit ordering",
    blurb: "Which character is qubit 0?",
    Component: BitOrdering,
  },
  circuit_lab: {
    title: "Build a circuit here",
    blurb: "The real drag-and-drop composer, in the lesson",
    Component: CircuitLab,
  },
};
