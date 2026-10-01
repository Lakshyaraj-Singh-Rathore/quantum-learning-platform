/**
 * Quantum Password Search — the Grover module, ported from lib/grover_ui.py.
 *
 * Presentation only: every number comes from src/lib/grover.ts, which
 * simulates a real 2ⁿ state vector. Nothing here invents a percentage.
 *
 * The two framings the original is deliberate about are kept:
 *
 * - Grover is never described as "trying all 64 passwords at once". The
 *   pipeline shown is superposition → oracle → amplification → measurement.
 * - The optimal count is ⌊π/4·√N⌋, not √N. The learner can overshoot on
 *   purpose and watch the probability fall.
 */
import { useState } from "react";
import {
  MAX_QUBITS,
  MIN_QUBITS,
  analyticProbability,
  classicalAttempts,
  label,
  measure,
  optimalIterations,
  parsePassword,
  run,
} from "../../lib/grover";
import { Button, Card, cn } from "../ui";

const GUESSES = [
  "It checks every password one by one, just faster",
  "It amplifies the amplitude of the target state",
  "Every state disappears except the target",
  "The computer simply knows the answer",
];

export function GroverLab() {
  const [nQubits, setNQubits] = useState(6);
  const [raw, setRaw] = useState("101101");
  const [step, setStep] = useState<number | null>(null);
  const [shots, setShots] = useState(100);
  const [seed, setSeed] = useState(0);
  const [guess, setGuess] = useState(GUESSES[0]);
  const [revealed, setRevealed] = useState<string | null>(null);
  const [overRotate, setOverRotate] = useState(false);

  const nStates = 2 ** nQubits;
  const { target, error } = parsePassword(raw, nQubits);
  const optimal = optimalIterations(nQubits);
  const currentStep = step === null ? optimal : Math.min(step, optimal);

  if (target === null) {
    return (
      <div className="flex flex-col gap-3">
        <GroverIntro />
        <Setup
          nQubits={nQubits}
          setNQubits={(value) => {
            setNQubits(value);
            setRaw(value < 6 ? "1".repeat(value) : "101101");
            setStep(null);
          }}
          raw={raw}
          setRaw={setRaw}
          nStates={nStates}
        />
        <p className="rounded-lg border border-warn/40 bg-warn/10 px-3 py-2 text-[13px] text-ink">
          {error}
        </p>
      </div>
    );
  }

  const frames = run(nQubits, target, optimal);
  const frame = frames[currentStep];
  const others = (1 - frame.targetProbability) / Math.max(1, nStates - 1);
  const counts = measure(frame.amplitudes, shots, seed);
  const hits = counts[target] ?? 0;

  return (
    <div className="flex flex-col gap-4">
      <GroverIntro />
      <Setup
        nQubits={nQubits}
        setNQubits={(value) => {
          setNQubits(value);
          setRaw(value < 6 ? "1".repeat(value) : "101101");
          setStep(null);
        }}
        raw={raw}
        setRaw={setRaw}
        nStates={nStates}
      />

      {/* Predict first, so the reveal lands on a formed opinion. */}
      <Card>
        <h4 className="mb-2 text-sm font-semibold">🤔 Predict first — what will Grover do?</h4>
        <div className="flex flex-col gap-1">
          {GUESSES.map((option) => (
            <label
              key={option}
              className={cn(
                "flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-1.5 text-[13px]",
                guess === option ? "border-accent bg-accent/10 text-ink" : "border-line text-ink-2",
              )}
            >
              <input
                type="radio"
                name="grover_guess"
                value={option}
                checked={guess === option}
                onChange={() => {
                  setGuess(option);
                  setRevealed(null);
                }}
                className="accent-accent"
              />
              {option}
            </label>
          ))}
        </div>
        <Button size="sm" className="mt-2" onClick={() => setRevealed(guess)}>
          Reveal
        </Button>
        {revealed !== null && (
          <p
            className={cn(
              "mt-2 rounded-lg border px-3 py-2 text-[13px]",
              revealed.startsWith("It amplifies")
                ? "border-ok/40 bg-ok/10 text-ink"
                : "border-danger/40 bg-danger/10 text-ink",
            )}
          >
            {revealed.startsWith("It amplifies") ? (
              <>
                Correct. The oracle marks the target with a phase flip, and the diffusion
                operator turns that phase difference into a larger amplitude. Nothing is checked
                one at a time.
              </>
            ) : (
              <>
                Not quite. Grover prepares a superposition, marks the target with a{" "}
                <strong>phase flip</strong>, then amplifies that marked amplitude. It never reads
                candidates one by one, and the other states do not vanish — they just end up with
                small amplitudes.
              </>
            )}
          </p>
        )}
      </Card>

      {/* The pipeline */}
      <Card>
        <h4 className="mb-2 text-sm font-semibold">The pipeline</h4>
        <pre className="overflow-auto rounded-lg border border-line-soft bg-hover/60 p-3 font-mono text-[12px] text-ink-2">
          superposition → oracle (phase flip) → diffusion (amplify) → measure
        </pre>

        <label className="mt-3 block text-[13px] text-ink-2">
          Grover iteration — {currentStep} / {optimal}
          <input
            type="range"
            min={0}
            max={optimal}
            step={1}
            value={currentStep}
            onChange={(e) => setStep(Number(e.target.value))}
            className="mt-1 w-full accent-accent"
          />
        </label>
        <p className="text-[11px] text-ink-3">
          Optimal for {nStates} states is ⌊π/4·√N⌋ = {optimal}.
        </p>

        <div className="mt-3 grid grid-cols-2 gap-2 lg:grid-cols-4">
          <Metric label="Iteration" value={`${currentStep} / ${optimal}`} />
          <Metric label="P(target)" value={`${(frame.targetProbability * 100).toFixed(2)}%`} />
          <Metric label="P(any other state)" value={`${(others * 100).toFixed(2)}%`} />
          <Metric label="Target amplitude" value={`${frame.amplitudes[target].re >= 0 ? "+" : ""}${frame.amplitudes[target].re.toFixed(4)}`} />
        </div>

        {currentStep === 0 && (
          <p className="mt-2 text-[12px] text-ink-3">
            Every state starts with amplitude 1/√{nStates} = {(1 / Math.sqrt(nStates)).toFixed(4)},
            so each is equally likely.
          </p>
        )}
      </Card>

      {/* The amplification curve */}
      <Card>
        <h4 className="mb-2 text-sm font-semibold">How the target&apos;s probability grows</h4>
        <Curve points={frames.map((f) => ({ x: f.iteration, y: f.targetProbability }))} others={frames.map((f) => ({ x: f.iteration, y: (1 - f.targetProbability) / Math.max(1, nStates - 1) }))} />

        <label className="mt-3 flex items-center gap-2 text-[13px] text-ink-2">
          <input
            type="checkbox"
            checked={overRotate}
            onChange={(e) => setOverRotate(e.target.checked)}
            className="accent-accent"
          />
          Show what happens if you keep going past the optimum
        </label>
        <p className="text-[11px] text-ink-3">
          A common misconception is that more iterations is always better.
        </p>

        {overRotate && (
          <div className="mt-3">
            <OverRotation nQubits={nQubits} target={target} optimal={optimal} nStates={nStates} />
          </div>
        )}
      </Card>

      {/* The search space */}
      <Card>
        <h4 className="mb-2 text-sm font-semibold">The search space right now</h4>
        <SearchSpace nQubits={nQubits} target={target} probabilities={frame.probabilities} />
      </Card>

      {/* Measurement */}
      <Card>
        <h4 className="mb-2 text-sm font-semibold">Measure</h4>
        <div className="flex flex-wrap items-end gap-3">
          <label className="text-[13px] text-ink-2">
            Shots — {shots}
            <select
              value={shots}
              onChange={(e) => setShots(Number(e.target.value))}
              className="mt-1 h-9 rounded-lg border border-line bg-raised px-2 text-sm text-ink"
            >
              {[1, 10, 100, 1024].map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <Button size="sm" onClick={() => setSeed((s) => s + 1)}>
            🎲 Measure
          </Button>
        </div>

        <div className="mt-3 grid gap-2 md:grid-cols-2">
          <Metric
            label={`Measured the target in ${hits}/${shots} shots`}
            value={`${((hits / Math.max(shots, 1)) * 100).toFixed(1)}%`}
            delta={`theory ${(frame.targetProbability * 100).toFixed(1)}%`}
          />
          <div className="overflow-auto rounded-lg border border-line-soft">
            <table className="w-full text-[12px]">
              <thead>
                <tr className="border-b border-line bg-hover/40 text-left text-[11px] uppercase tracking-wide text-ink-3">
                  <th className="px-2 py-1.5 font-medium">State</th>
                  <th className="px-2 py-1.5 text-right font-medium">Shots</th>
                  <th className="px-2 py-1.5 font-medium">Is target</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(counts)
                  .sort((a, b) => Number(b[1]) - Number(a[1]))
                  .slice(0, 6)
                  .map(([index, count]) => (
                    <tr key={index} className="border-b border-line-soft/60 last:border-0">
                      <td className="px-2 py-1 font-mono text-ink-2">{label(Number(index), nQubits)}</td>
                      <td className="px-2 py-1 text-right font-mono text-ink-2">{count}</td>
                      <td className="px-2 py-1">{Number(index) === target ? "🎯" : ""}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>
      </Card>

      {/* Classical versus Grover */}
      <Card>
        <h4 className="mb-2 text-sm font-semibold">Classical search versus Grover</h4>
        <Comparison nQubits={nQubits} target={target} optimal={optimal} nStates={nStates} final={frames[frames.length - 1].targetProbability} />
      </Card>

      {/* Why this is only a demonstration */}
      <Card>
        <details className="[&_summary]:cursor-pointer">
          <summary className="text-sm font-semibold">Why 6 qubits is only a demonstration</summary>
          <div className="mt-3 flex flex-col gap-2 text-[13px] leading-relaxed text-ink-2">
            <p>
              This search space is <strong className="text-ink">{nStates} states</strong>. A real
              12-character password drawn from 94 printable characters is about 10²³ possibilities —
              Grover would reduce that to roughly 10¹¹ <em>oracle queries</em>, which is still far
              beyond any machine that exists or is planned.
            </p>
            <p>
              Real systems also defend in ways this model ignores: passwords are salted and hashed,
              attempts are rate-limited, and multi-factor authentication means the password alone is
              not enough.
            </p>
            <p>
              <strong className="text-ink">The honest takeaway.</strong> Grover halves the effective
              key length, so a scheme that needs 128 bits of classical security needs about 256 bits
              to keep the same margin against a quantum attacker. That is a real consideration for
              the design of future cryptography — not a way to break into accounts.
            </p>
          </div>
        </details>
      </Card>
    </div>
  );
}

/* -------------------------------------------------------------------------- */

function GroverIntro() {
  return (
    <div className="flex flex-col gap-2">
      <h3 className="text-lg font-semibold tracking-tight">🔐 Quantum Password Search</h3>
      <p className="text-[13px] text-ink-3">
        A teaching simulation of Grover&apos;s algorithm. The password is a toy binary string that
        never leaves your browser session, and nothing here touches a real system.
      </p>
      <p className="rounded-lg border border-line bg-raised px-3 py-2 text-[13px] text-ink-2">
        <strong className="text-ink">Quantum computers do not magically crack passwords.</strong>{" "}
        Grover&apos;s algorithm gives a <em>quadratic</em> speedup for searching an unstructured
        space — O(√N) oracle queries instead of O(N) — and only when you already have an oracle that
        can recognise a correct answer.
      </p>
    </div>
  );
}

function Setup({
  nQubits,
  setNQubits,
  raw,
  setRaw,
  nStates,
}: {
  nQubits: number;
  setNQubits: (value: number) => void;
  raw: string;
  setRaw: (value: string) => void;
  nStates: number;
}) {
  return (
    <Card>
      <div className="grid gap-4 md:grid-cols-[1fr_1fr_auto]">
        <label className="flex flex-col gap-1 text-[13px]">
          <span className="text-ink-2">Password length (qubits) — {nQubits}</span>
          <input
            type="range"
            min={MIN_QUBITS}
            max={MAX_QUBITS}
            step={1}
            value={nQubits}
            onChange={(e) => setNQubits(Number(e.target.value))}
            className="accent-accent"
          />
          <span className="text-[11px] text-ink-3">
            Capped at 6 so the whole 64-state space stays visible.
          </span>
        </label>
        <label className="flex flex-col gap-1 text-[13px]">
          <span className="text-ink-2">Toy password (binary)</span>
          <input
            value={raw}
            maxLength={nQubits}
            onChange={(e) => setRaw(e.target.value)}
            className="h-9 rounded-lg border border-line bg-raised px-3 font-mono text-sm text-ink"
          />
        </label>
        <Metric label="Search space" value={`2^${nQubits} = ${nStates} states`} />
      </div>
    </Card>
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

/** Two polylines on one axis: the target, and every other state. */
function Curve({
  points,
  others,
}: {
  points: { x: number; y: number }[];
  others: { x: number; y: number }[];
}) {
  const width = 520;
  const height = 160;
  const padding = 28;
  const maxX = Math.max(...points.map((p) => p.x), 1);
  const maxY = 1;
  const toXY = (p: { x: number; y: number }) =>
    `${(padding + (p.x / maxX) * (width - padding * 2)).toFixed(1)},${(height - padding - (p.y / maxY) * (height - padding * 2)).toFixed(1)}`;

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className="h-40 w-full rounded-lg border border-line-soft bg-raised"
      role="img"
      aria-label="Target probability against Grover iteration"
    >
      <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="var(--line)" />
      <line x1={padding} y1={padding} x2={padding} y2={height - padding} stroke="var(--line)" />
      <polyline points={others.map(toXY).join(" ")} fill="none" stroke="var(--ink-3)" strokeWidth="1.5" strokeDasharray="4 3" />
      <polyline points={points.map(toXY).join(" ")} fill="none" stroke="var(--accent)" strokeWidth="2" />
      {points.map((point) => {
        const [x, y] = toXY(point).split(",").map(Number);
        return <circle key={point.x} cx={x} cy={y} r="2.5" fill="var(--accent)" />;
      })}
      <text x={width - padding} y={height - 8} textAnchor="end" fontSize="9" fill="var(--ink-3)">
        iteration
      </text>
      <text x={width - padding} y={padding - 10} textAnchor="end" fontSize="9" fill="var(--ink-3)">
        — — each other state
      </text>
    </svg>
  );
}

/** The over-rotation lesson: keep rotating and you go past the target. */
function OverRotation({
  nQubits,
  target,
  optimal,
  nStates,
}: {
  nQubits: number;
  target: number;
  optimal: number;
  nStates: number;
}) {
  const frames = run(nQubits, target, optimal * 2 + 2);
  const peak = frames.reduce((best, frame) =>
    frame.targetProbability > best.targetProbability ? frame : best,
  );

  return (
    <div className="flex flex-col gap-2">
      <Curve
        points={frames.map((f) => ({ x: f.iteration, y: f.targetProbability }))}
        others={frames.map((f) => ({ x: f.iteration, y: 0 }))}
      />
      <p className="rounded-lg border border-warn/40 bg-warn/10 px-3 py-2 text-[13px] text-ink">
        The probability peaks at iteration <strong>{peak.iteration}</strong> (
        {(peak.targetProbability * 100).toFixed(1)}%) and then <strong>falls again</strong>. Grover
        rotates the state toward the target; keep rotating and you go past it. This is why the
        optimal count is ⌊π/4·√N⌋ and not √N — for N={nStates} that is {optimal}, not{" "}
        {Math.floor(Math.sqrt(nStates))}.
      </p>
    </div>
  );
}

function SearchSpace({
  nQubits,
  target,
  probabilities,
}: {
  nQubits: number;
  target: number;
  probabilities: number[];
}) {
  return (
    <div className="max-h-[420px] overflow-auto rounded-lg border border-line-soft">
      <table className="w-full text-[12px]">
        <thead>
          <tr className="sticky top-0 border-b border-line bg-raised text-left text-[11px] uppercase tracking-wide text-ink-3">
            <th className="px-3 py-1.5 font-medium">State</th>
            <th className="px-3 py-1.5 font-medium">Probability</th>
          </tr>
        </thead>
        <tbody>
          {probabilities.map((probability, index) => (
            <tr key={index} className="border-b border-line-soft/60 last:border-0">
              <td className="w-24 px-3 py-1 font-mono text-ink-2">
                {index === target ? "🎯 " : ""}
                {label(index, nQubits)}
              </td>
              <td className="px-3 py-1">
                <div className="flex items-center gap-2">
                  <div className="h-2.5 flex-1 overflow-hidden rounded bg-hover">
                    <div className="h-full bg-accent" style={{ width: `${probability * 100}%` }} />
                  </div>
                  <span className="w-16 text-right font-mono text-ink-3">
                    {probability.toFixed(4)}
                  </span>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Comparison({
  nQubits,
  target,
  optimal,
  nStates,
  final,
}: {
  nQubits: number;
  target: number;
  optimal: number;
  nStates: number;
  final: number;
}) {
  const classical = classicalAttempts(nQubits, target);
  const rows: [string, string, string][] = [
    ["How it searches", "One candidate at a time", "Marks the target, amplifies its amplitude"],
    ["Queries needed", `up to ${classical.worstCase}`, `about ⌊π/4·√${nStates}⌋ = ${optimal}`],
    ["Complexity", "O(N)", "O(√N)"],
    [
      "For this password",
      `${classical.checkedToFind} checks scanning in order`,
      `${optimal} iterations → ${(final * 100).toFixed(1)}%`,
    ],
    ["Result", "Certain", "Probabilistic — very likely, not guaranteed"],
  ];

  return (
    <div className="overflow-auto rounded-lg border border-line-soft">
      <table className="w-full text-[13px]">
        <thead>
          <tr className="border-b border-line bg-hover/40 text-left text-[11px] uppercase tracking-wide text-ink-3">
            <th className="px-3 py-2 font-medium" />
            <th className="px-3 py-2 font-medium">Classical brute force</th>
            <th className="px-3 py-2 font-medium">Grover</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([row, left, right]) => (
            <tr key={row} className="border-b border-line-soft/60 last:border-0">
              <td className="px-3 py-1.5 font-medium text-ink-2">{row}</td>
              <td className="px-3 py-1.5 text-ink-2">{left}</td>
              <td className="px-3 py-1.5 text-ink-2">{right}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="border-t border-line-soft px-3 py-2 text-[11px] text-ink-3">
        The closed form sin²((2k+1)·asin(1/√N)) gives{" "}
        {(analyticProbability(nQubits, optimal) * 100).toFixed(2)}% at the optimum, which is what the
        simulation shows too.
      </p>
    </div>
  );
}
