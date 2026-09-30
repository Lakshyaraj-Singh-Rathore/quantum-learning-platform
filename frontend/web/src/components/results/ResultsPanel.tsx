import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { jobResult, jobStatus } from "../../api/jobs";
import { Badge, ErrorNote, Spinner, cn } from "../ui";
import {
  BlochView,
  BornVsShots,
  DensityMatrix,
  Histogram,
  IdealVsNoisy,
  MetricGauges,
  ProbabilityTable,
  ResultSummary,
  StatevectorTable,
} from "./ResultsViews";

const TABS = [
  { id: "histogram", label: "Histogram" },
  { id: "ideal", label: "Ideal vs noisy" },
  { id: "born", label: "Born vs shots" },
  { id: "probabilities", label: "Probabilities" },
  { id: "statevector", label: "Statevector" },
  { id: "density", label: "Density matrix" },
  { id: "bloch", label: "Bloch" },
] as const;

type TabId = (typeof TABS)[number]["id"];

/** Polls a job and renders the result views once it completes.
 *
 * The circuit that produced the job is remembered, so editing the grid after a
 * run marks the results stale instead of silently showing numbers that no
 * longer describe the circuit on screen (the Streamlit page does the same, and
 * it matters: a 15-qubit histogram rendering under a 2-qubit grid is a lie).
 */
export function ResultsPanel({
  jobId,
  stale,
  ranQubits,
  currentQubits,
}: {
  jobId: number | null;
  stale: boolean;
  ranQubits: number | null;
  currentQubits: number;
}) {
  const [status, setStatus] = useState<string | null>(null);
  const [tab, setTab] = useState<TabId>("histogram");

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
        if (s.status === "completed" || s.status === "failed") return;
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
  }, [jobId]);

  const result = useQuery({
    queryKey: ["job-result", jobId],
    queryFn: () => jobResult(jobId as number),
    enabled: jobId !== null && status === "completed",
    staleTime: Infinity,
  });

  if (jobId === null) return null;

  const running = status !== null && status !== "completed" && status !== "failed";
  const data = result.data?.result ?? null;

  return (
    <section className="flex flex-col gap-4 rounded-xl border border-line bg-raised p-5">
      <div className="flex flex-wrap items-center gap-3">
        <h3 className="text-sm font-semibold">Results — job #{jobId}</h3>
        {running && (
          <span className="flex items-center gap-2 text-[13px] text-ink-3">
            <Spinner /> {status}…
          </span>
        )}
        {status === "completed" && <Badge tone="accent">completed</Badge>}
        {(status === "failed" || result.data?.error) && <Badge tone="danger">failed</Badge>}
      </div>

      {stale && (
        <p className="rounded-lg border border-warn/40 bg-warn/10 p-3 text-[13px] leading-relaxed text-warn">
          These results are from an earlier version of the circuit.
          {ranQubits !== null && ranQubits !== currentQubits && (
            <>
              {" "}
              It ran on {ranQubits} qubit{ranQubits === 1 ? "" : "s"}; the grid now has{" "}
              {currentQubits}.
            </>
          )}{" "}
          Press <strong className="font-semibold">Run simulation</strong> to refresh them.
        </p>
      )}

      {result.data?.error && <ErrorNote>{result.data.error}</ErrorNote>}
      {result.isError && <ErrorNote>{String(result.error)}</ErrorNote>}
      {status !== null && status !== "completed" && !result.data?.error && (
        <p className="text-[13px] text-ink-3">Job status: {status}</p>
      )}

      {data && (
        <>
          <ResultSummary result={data} />
          <MetricGauges result={data} />

          <div
            role="tablist"
            aria-label="Result views"
            className="flex flex-wrap gap-1 border-b border-line-soft pb-2"
          >
            {TABS.map((t) => (
              <button
                key={t.id}
                role="tab"
                aria-selected={tab === t.id}
                onClick={() => setTab(t.id)}
                className={cn(
                  "rounded-lg px-3 py-1.5 text-[13px] text-ink-2 transition-colors",
                  "hover:bg-hover hover:text-ink",
                  tab === t.id && "bg-active font-medium text-ink",
                )}
              >
                {t.label}
              </button>
            ))}
          </div>

          <div role="tabpanel">
            {tab === "histogram" && <Histogram result={data} />}
            {tab === "ideal" && <IdealVsNoisy result={data} />}
            {tab === "born" && <BornVsShots result={data} />}
            {tab === "probabilities" && <ProbabilityTable result={data} />}
            {tab === "statevector" && <StatevectorTable result={data} />}
            {tab === "density" && <DensityMatrix result={data} />}
            {tab === "bloch" && <BlochView result={data} />}
          </div>
        </>
      )}
    </section>
  );
}
