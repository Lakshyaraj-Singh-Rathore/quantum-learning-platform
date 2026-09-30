import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Play, RotateCcw, Sparkles } from "lucide-react";
import { ComposerInner } from "@composer/Composer";
import { circuitIsDynamic, makeOp, maxLayer } from "@composer/ir";
import type { CircuitIR } from "@composer/types";
import { useTheme } from "../state/theme";
import { backends } from "../api/backends";
import { inspectCircuit, jobResult, jobStatus, submitJob } from "../api/jobs";
import type { NoiseIn } from "../api/jobs";
import { Badge, Button, Card, ErrorNote, Input, Label, Separator, Spinner, cn } from "../components/ui";

const SHOT_CHOICES = [128, 256, 512, 1024, 2048, 4096, 8192];

const NOISE_BACKENDS = new Set(["qiskit_aer", "cudaq"]);

function bell(): CircuitIR {
  return {
    name: "bell",
    n_qubits: 2,
    n_clbits: 2,
    ops: [
      makeOp("gate", { gate: "h", qubits: [0], layer: 0 }),
      makeOp("gate", { gate: "x", qubits: [1], controls: [0], layer: 1 }),
      makeOp("measure", { qubits: [0], clbits: [0], layer: 2 }),
      makeOp("measure", { qubits: [1], clbits: [1], layer: 2 }),
    ],
  };
}

function empty(n = 2): CircuitIR {
  return { name: "circuit", n_qubits: n, n_clbits: n, ops: [] };
}

const DEFAULT_NOISE: NoiseIn = {
  enabled: false,
  t1_us: 50,
  t2_us: 30,
  readout_error: 0.02,
  gate_time_1q_us: 0.1,
  gate_time_2q_us: 0.4,
  gate_time_3q_us: 1.0,
};

export function ComposerPage() {
  const [ir, setIr] = useState<CircuitIR>(bell);
  // The grid is uncontrolled once mounted (it owns its own edit state), so a
  // programmatic reset remounts it rather than fighting it.
  const [epoch, setEpoch] = useState(0);
  const [shots, setShots] = useState(1024);
  const [backendId, setBackendId] = useState<string>("qiskit_aer");
  const [noise, setNoise] = useState<NoiseIn>(DEFAULT_NOISE);
  const [jobId, setJobId] = useState<number | null>(null);
  const [runSnapshot, setRunSnapshot] = useState<string | null>(null);
  const [ranQubits, setRanQubits] = useState<number | null>(null);
  const [runError, setRunError] = useState<string | null>(null);
  const { theme } = useTheme();
  const queryClient = useQueryClient();

  const { data: catalogue } = useQuery({ queryKey: ["backends"], queryFn: backends, staleTime: 30_000 });

  const dynamic = useMemo(() => circuitIsDynamic(ir), [ir]);
  const depth = maxLayer(ir.ops) + 1;

  const options = useMemo(() => {
    const want = dynamic ? "dynamic" : "static";
    const matching = (catalogue?.backends ?? []).filter((b) => b.supports.includes(want));
    return matching.length > 0 ? matching : (catalogue?.backends ?? []);
  }, [catalogue, dynamic]);

  // Keep the selected backend valid as the circuit flips between static and
  // dynamic: "auto" on the server would silently pick an engine, and a stale
  // selection here would look like the UI ignoring the circuit.
  useEffect(() => {
    if (options.length === 0) return;
    if (!options.some((b) => b.id === backendId)) setBackendId(options[0].id);
  }, [options, backendId]);

  const chosen = options.find((b) => b.id === backendId) ?? null;
  const maxShots = dynamic ? (catalogue?.limits.max_dynamic_shots ?? 8192) : 8192;
  const shotOptions = SHOT_CHOICES.filter((s) => s <= maxShots);
  const effectiveShots = Math.min(shots, maxShots);

  const irKey = JSON.stringify(ir);
  const report = useQuery({
    queryKey: ["inspect", irKey, backendId, effectiveShots],
    queryFn: () => inspectCircuit(ir, backendId, effectiveShots),
    staleTime: 5_000,
  });

  const canRun =
    chosen !== null && chosen.available && report.data?.ok === true;

  const run = useMutation({
    mutationFn: () =>
      submitJob({
        circuit_ir: ir,
        backend: backendId,
        shots: effectiveShots,
        noise: noise.enabled ? noise : null,
      }),
    onSuccess: (job) => {
      setRunError(null);
      setJobId(job.id);
      // Remember the exact circuit this job ran on, so the results below can
      // say when they no longer describe what is on the grid.
      setRunSnapshot(irKey);
      setRanQubits(ir.n_qubits);
    },
    onError: (exc: Error) => setRunError(exc.message),
  });

  return (
    <div className="flex h-full min-h-0 flex-col gap-5 p-6">
      <div className="flex items-center gap-3">
        <h2 className="text-xl font-semibold tracking-tight">Composer</h2>
        <Badge tone={dynamic ? "warn" : "accent"}>
          {dynamic ? "dynamic circuit" : "static circuit"}
        </Badge>
        <span className="text-sm text-ink-3">
          {ir.n_qubits} qubits · depth {depth} · {ir.ops.length} ops
        </span>
        <div className="ml-auto flex gap-2">
          <Button size="sm" onClick={() => { setIr(bell()); setEpoch((e) => e + 1); }}>
            <Sparkles className="h-3.5 w-3.5" /> Bell state
          </Button>
          <Button size="sm" onClick={() => { setIr(empty(ir.n_qubits)); setEpoch((e) => e + 1); }}>
            <RotateCcw className="h-3.5 w-3.5" /> Clear
          </Button>
        </div>
      </div>

      <div className="flex min-h-0 flex-1 flex-col gap-5 xl:flex-row">
        <Card className="min-h-0 flex-1 overflow-auto p-4">
          {/* The grid carries its own palette, scoped to .composer-host so it
              cannot overwrite the app's tokens (see circuit_composer styles). */}
          <div className={cn("composer-host", theme === "dark" && "dark")}>
            <ComposerInner
              key={epoch}
              value={ir}
              nQubits={ir.n_qubits}
              onChange={setIr}
            />
          </div>
        </Card>

        <div className="flex w-full shrink-0 flex-col gap-4 xl:w-[340px]">
          <Card>
            <h3 className="mb-3 text-sm font-semibold">Run settings</h3>
            <div className="flex flex-col gap-4">
              <div>
                <Label htmlFor="backend">Backend</Label>
                <select
                  id="backend"
                  value={backendId}
                  onChange={(e) => setBackendId(e.target.value)}
                  className="h-9 w-full rounded-lg border border-line bg-raised px-2 text-sm text-ink"
                >
                  {options.map((b) => (
                    <option key={b.id} value={b.id} disabled={!b.available}>
                      {b.label}
                      {b.available ? "" : "  (unavailable)"}
                    </option>
                  ))}
                </select>
                {chosen && !chosen.available && (
                  <p className="mt-2 text-[13px] text-warn">{chosen.reason}</p>
                )}
              </div>

              <div>
                <Label htmlFor="shots">Shots</Label>
                <select
                  id="shots"
                  value={effectiveShots}
                  onChange={(e) => setShots(Number(e.target.value))}
                  className="h-9 w-full rounded-lg border border-line bg-raised px-2 text-sm text-ink"
                >
                  {shotOptions.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
                <p className="mt-1.5 text-xs text-ink-3">
                  More shots means less sampling noise, and a slower run.
                </p>
              </div>
            </div>

            {backendId === "qbraid" && (
              <p className="mt-4 rounded-lg border border-line-soft bg-hover p-3 text-[13px] leading-relaxed text-ink-2">
                <strong className="font-semibold text-ink">
                  qBraid runs on a remote device and spends credits on every run.
                </strong>{" "}
                Credits are consumed at submission, so a run that later times out
                still costs them. The local backends (Qiskit Aer, Cirq, PennyLane)
                are free, instant, and give identical results for static circuits —
                use qBraid to demonstrate real hardware submission, not for
                iterating on a circuit.
              </p>
            )}
          </Card>

          <NoisePanel noise={noise} onChange={setNoise} enabled={NOISE_BACKENDS.has(backendId)} />

          <Card>
            <h3 className="mb-3 text-sm font-semibold">Circuit analysis</h3>
            {report.isLoading && (
              <p className="flex items-center gap-2 text-sm text-ink-3">
                <Spinner /> checking…
              </p>
            )}
            {report.data?.errors.map((e) => (
              <p key={e} role="alert" className="text-[13px] text-danger">
                {e}
              </p>
            ))}
            {report.data?.warnings.map((w) => (
              <p key={w} className="text-[13px] text-warn">
                {w}
              </p>
            ))}
            {report.data && report.data.errors.length === 0 && (
              <p className="text-[13px] text-ink-2">
                {String(report.data.summary.n_ops ?? 0)} operations ·{" "}
                {String(report.data.summary.depth ?? 0)} layers · ready to run
              </p>
            )}
            {report.isError && <ErrorNote>{String(report.error)}</ErrorNote>}

            <Separator className="my-4" />
            <ErrorNote className="mb-2">{runError}</ErrorNote>
            <Button
              variant="primary"
              className="w-full"
              disabled={!canRun || run.isPending}
              onClick={() => run.mutate()}
            >
              {run.isPending ? <Spinner /> : <Play className="h-4 w-4" />}
              Run simulation
            </Button>
            {!canRun && report.data && (
              <p className="mt-2 text-xs text-ink-3">
                Fix the errors above, or pick an available backend.
              </p>
            )}
          </Card>
        </div>
      </div>

      <ResultsPanel
        jobId={jobId}
        stale={jobId !== null && runSnapshot !== null && runSnapshot !== irKey}
        ranQubits={ranQubits}
        currentQubits={ir.n_qubits}
        onDone={() => void queryClient.invalidateQueries({ queryKey: ["jobs"] })}
      />
    </div>
  );
}

// --------------------------------------------------------------------- noise

function NoisePanel({
  noise,
  onChange,
  enabled,
}: {
  noise: NoiseIn;
  onChange: (n: NoiseIn) => void;
  enabled: boolean;
}) {
  const [open, setOpen] = useState(false);
  if (!enabled) {
    return null;
  }
  const set = (patch: Partial<NoiseIn>) => onChange({ ...noise, ...patch });
  const clamped = Math.min(noise.t2_us, 2 * noise.t1_us);

  return (
    <Card>
      <button
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="flex w-full items-center justify-between text-sm font-semibold"
      >
        Noise model (T1 / T2 / readout)
        <span className="text-ink-3">{open ? "−" : "+"}</span>
      </button>
      {open && (
        <div className="mt-4 flex flex-col gap-4">
          <p className="text-[13px] leading-relaxed text-ink-2">
            These are <strong className="font-semibold text-ink">teaching parameters you choose</strong>,
            not calibration data from any real quantum computer. They reproduce the{" "}
            <em>kind</em> of errors hardware shows: energy loss (T1), dephasing (T2)
            and misread bits.
          </p>

          <label className="flex items-center gap-2 text-sm text-ink-2">
            <input
              type="checkbox"
              checked={noise.enabled}
              onChange={(e) => set({ enabled: e.target.checked })}
              className="h-4 w-4 accent-[var(--accent)]"
            />
            Enable noise
          </label>

          <div className="grid grid-cols-2 gap-3">
            <NumberField label="T1 relaxation (us)" value={noise.t1_us} min={1} max={200} step={1}
              onChange={(v) => set({ t1_us: v })} />
            <NumberField label="T2 dephasing (us)" value={noise.t2_us} min={1} max={200} step={1}
              onChange={(v) => set({ t2_us: v })} />
            <NumberField label="Readout error (%)" value={Math.round(noise.readout_error * 1000) / 10}
              min={0} max={20} step={0.1}
              onChange={(v) => set({ readout_error: v / 100 })} />
            <NumberField label="1-qubit pulse (us)" value={noise.gate_time_1q_us} min={0.02} max={2} step={0.02}
              onChange={(v) => set({ gate_time_1q_us: v })} />
            <NumberField label="2-qubit pulse (us)" value={noise.gate_time_2q_us} min={0.05} max={4} step={0.05}
              onChange={(v) => set({ gate_time_2q_us: v })} />
            <NumberField label="3-qubit pulse (us)" value={noise.gate_time_3q_us} min={0.1} max={6} step={0.1}
              onChange={(v) => set({ gate_time_3q_us: v })} />
          </div>

          {noise.t2_us > 2 * noise.t1_us && (
            <p className="text-[13px] text-warn">
              T2 cannot exceed 2xT1; it will be clamped to {clamped.toFixed(1)} us.
            </p>
          )}
          <p className="text-xs leading-relaxed text-ink-3">
            Longer pulses mean more decoherence per gate. Z / S / T / RZ are virtual
            (frame changes in software), so they pick up no thermal error.
          </p>
        </div>
      )}
    </Card>
  );
}

function NumberField({
  label,
  value,
  min,
  max,
  step,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (v: number) => void;
}) {
  return (
    <div>
      <Label>{label}</Label>
      <Input
        type="number"
        value={value}
        min={min}
        max={max}
        step={step}
        onChange={(e) => {
          const v = Number(e.target.value);
          if (!Number.isNaN(v)) onChange(Math.min(max, Math.max(min, v)));
        }}
      />
    </div>
  );
}

// ------------------------------------------------------------------- results

function ResultsPanel({
  jobId,
  stale,
  ranQubits,
  currentQubits,
  onDone,
}: {
  jobId: number | null;
  stale: boolean;
  ranQubits: number | null;
  currentQubits: number;
  onDone: () => void;
}) {
  const [status, setStatus] = useState<string | null>(null);

  useEffect(() => {
    if (jobId === null) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    let delay = 400;
    const tick = async () => {
      try {
        const s = await jobStatus(jobId);
        if (cancelled) return;
        setStatus(s.status);
        if (s.status === "completed" || s.status === "failed") {
          onDone();
          return;
        }
      } catch {
        if (!cancelled) setStatus("unreachable");
        return;
      }
      timer = setTimeout(tick, delay);
      delay = Math.min(Math.round(delay * 1.5), 1500);
    };
    void tick();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [jobId, onDone]);

  const result = useQuery({
    queryKey: ["job-result", jobId],
    queryFn: () => jobResult(jobId as number),
    enabled: jobId !== null && status === "completed",
    staleTime: Infinity,
  });

  if (jobId === null) return null;

  const running = status !== null && status !== "completed" && status !== "failed";
  const counts = result.data?.result?.counts ?? null;
  const total = counts ? Object.values(counts).reduce((a, b) => a + b, 0) : 0;

  return (
    <Card>
      <div className="mb-3 flex items-center gap-3">
        <h3 className="text-sm font-semibold">Results — job #{jobId}</h3>
        {running && (
          <span className="flex items-center gap-2 text-[13px] text-ink-3">
            <Spinner /> {status}…
          </span>
        )}
        {status === "completed" && <Badge tone="accent">completed</Badge>}
        {(status === "failed" || result.data?.error) && (
          <Badge tone="danger">failed</Badge>
        )}
      </div>

      {stale && (
        <p className="mb-3 rounded-lg border border-warn/40 bg-warn/10 p-3 text-[13px] leading-relaxed text-warn">
          These results are from an earlier version of the circuit.
          {ranQubits !== null && ranQubits !== currentQubits && (
            <>
              {" "}
              It ran on {ranQubits} qubit{ranQubits === 1 ? "" : "s"}; the grid now has{" "}
              {currentQubits}.
            </>
          )}{" "}
          Press <strong className="font-semibold">Run simulation</strong> to refresh
          them.
        </p>
      )}

      {result.data?.error && <ErrorNote className="mb-3">{result.data.error}</ErrorNote>}
      {result.isError && <ErrorNote className="mb-3">{String(result.error)}</ErrorNote>}

      {counts && (
        <div className="flex flex-col gap-1.5">
          {Object.entries(counts)
            .sort((a, b) => b[1] - a[1])
            .map(([bits, n]) => {
              const pct = total > 0 ? (n / total) * 100 : 0;
              return (
                <div key={bits} className="flex items-center gap-3 text-sm">
                  <code className="w-20 shrink-0 font-mono text-[13px] text-ink">{bits}</code>
                  <div className="h-2 flex-1 overflow-hidden rounded-full bg-hover">
                    <div
                      className="h-full rounded-full bg-accent"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <span className="w-28 shrink-0 text-right text-[13px] tabular-nums text-ink-2">
                    {n} · {pct.toFixed(1)}%
                  </span>
                </div>
              );
            })}
          <p className="mt-3 text-xs text-ink-3">
            {result.data?.result?.metadata.bit_order} ·{" "}
            {result.data?.result?.metadata.backend} ·{" "}
            {result.data?.result?.metadata.runtime_seconds}s · {total} shots
          </p>
        </div>
      )}
    </Card>
  );
}
