/* Quantum ML Lab — four views over one experiment lifecycle.
 *
 * The route is gated as well as the nav entry. Hiding a link is presentation;
 * a user who has the URL, or a stale bookmark, must get the same answer the
 * server would give. With the flag off every `/qml/*` endpoint 404s, so a
 * page that rendered anyway would just be a slower way to show an error.
 */
import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Badge, EmptyState, Spinner, Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui";
import { QmlConfigForm } from "../components/qml/QmlConfigForm";
import { QmlCircuitPreview } from "../components/qml/QmlCircuitPreview";
import { QmlTrainingDashboard } from "../components/qml/QmlTrainingDashboard";
import { QmlExplanationPanel } from "../components/qml/QmlExplanationPanel";
import { QmlResultsPanel } from "../components/qml/QmlResultsPanel";
import { useQmlExperiment } from "../hooks/useQmlExperiment";
import { runInference } from "../api/qml";
import {
  isClassificationResult,
  isInterrupted,
  isRegressionResult,
  type RegressionResult,
} from "../api/qml";
import { useQmlEnabled } from "../hooks/useFeatures";
import {
  createExperiment,
  DEFAULT_CONFIG,
  describeQml,
  isTerminal,
  listExperiments,
  type Experiment,
  type ExperimentStatus,
  type QmlConfig,
} from "../api/qml";

type View = "configure" | "circuit" | "training" | "results";

function HistoryList({
  experiments,
  activeId,
  onSelect,
}: {
  experiments: Experiment[];
  activeId: number | null;
  onSelect: (id: number) => void;
}) {
  if (experiments.length === 0) {
    return <p className="px-1 text-[11px] text-ink-3">No experiments yet.</p>;
  }
  return (
    <ul className="space-y-1">
      {experiments.map((e) => (
        <li key={e.id}>
          <button
            type="button"
            onClick={() => onSelect(e.id)}
            aria-current={e.id === activeId ? "true" : undefined}
            className={
              e.id === activeId
                ? "flex w-full items-center justify-between gap-2 rounded-lg border border-accent/40 bg-accent/10 px-2.5 py-1.5 text-left text-xs text-ink"
                : "flex w-full items-center justify-between gap-2 rounded-lg border border-transparent px-2.5 py-1.5 text-left text-xs text-ink-2 hover:border-line hover:bg-hover"
            }
          >
            <span className="truncate">
              #{e.id} · {e.config.dataset?.name ?? "—"}
            </span>
            <span className="shrink-0 text-[10px] text-ink-3">{e.status}</span>
          </button>
        </li>
      ))}
    </ul>
  );
}

export default function QmlLabPage() {
  const { enabled, resolved } = useQmlEnabled();
  const queryClient = useQueryClient();

  const [config, setConfig] = useState<QmlConfig>(DEFAULT_CONFIG);
  const [experimentId, setExperimentId] = useState<number | null>(null);
  const [view, setView] = useState<View>("configure");

  const describe = useQuery({
    queryKey: ["qml", "describe"],
    queryFn: describeQml,
    staleTime: Infinity,
    enabled,
  });

  const experiments = useQuery({
    queryKey: ["qml", "experiments"],
    queryFn: () => listExperiments(20),
    enabled,
  });

  const { experiment, history, cancel, inference, reset } = useQmlExperiment(
    enabled ? experimentId : null,
  );

  const create = useMutation({
    mutationFn: (c: QmlConfig) => createExperiment(c),
    onSuccess: (created) => {
      reset();
      setExperimentId(created.id);
      // A cached duplicate comes back already terminal, so send the user
      // straight to what they actually wanted to see.
      setView(isTerminal(created.status) ? "results" : "training");
      void queryClient.invalidateQueries({ queryKey: ["qml", "experiments"] });
    },
  });

  const status = (experiment?.status ?? "queued") as ExperimentStatus;
  const running = experiment !== undefined && !isTerminal(status);

  const algorithmInfo = useMemo(
    () => describe.data?.algorithms.find((a) => a.name === config.algorithm),
    [describe.data, config.algorithm],
  );

  const activeCircuit = experiment?.config?.circuit ?? config.circuit;
  const activeFeatures = useMemo(() => {
    const dsName = experiment?.config?.dataset?.name ?? config.dataset.name;
    const pool = algorithmInfo?.datasets ?? describe.data?.datasets ?? [];
    const ds = pool.find((d) => d.name === dsName);
    return ds?.n_features ?? 2;
  }, [experiment, algorithmInfo, describe.data, config.dataset.name]);

  const serverParameters = useMemo(() => {
    // An interrupted result has no `circuit` key at all, so this must narrow
    // before reading one -- the union is what makes that a compile error
    // rather than an undefined at runtime.
    const result = experiment?.result;
    if (!result || isInterrupted(result)) return undefined;
    const circuit = result.circuit as { n_parameters?: number } | undefined;
    return typeof circuit?.n_parameters === "number" ? circuit.n_parameters : undefined;
  }, [experiment]);

  const kernelSummary = useMemo(() => {
    const result = experiment?.result;
    return isClassificationResult(result) ? result.kernel : undefined;
  }, [experiment]);

  // Response curve for a single-feature regression target.
  //
  // This is the model's own prediction swept across the input range, taken
  // from the real inference endpoint. It is NOT the predicted-vs-actual
  // scatter §2E.3 asks for: that needs per-sample test predictions and their
  // targets, and no endpoint serves them. Sweeping is what the shipped API
  // can answer honestly.
  const regressionResult = isRegressionResult(experiment?.result)
    ? (experiment?.result as RegressionResult)
    : undefined;
  const curveFeatures = useMemo(() => {
    if (!regressionResult) return null;
    if (Number(regressionResult.dataset?.n_features ?? 0) !== 1) return null;
    const steps = 48;
    const rows: number[][] = [];
    for (let i = 0; i < steps; i += 1) {
      rows.push([-Math.PI + (2 * Math.PI * i) / (steps - 1)]);
    }
    return rows;
  }, [regressionResult]);

  const curve = useQuery({
    queryKey: ["qml", "response-curve", experimentId],
    queryFn: () => runInference(experimentId as number, curveFeatures as number[][]),
    enabled: enabled && experimentId !== null && curveFeatures !== null,
    staleTime: Infinity,
    retry: false,
  });

  const responseCurve = useMemo(() => {
    if (!regressionResult) return undefined;
    if (curveFeatures === null) {
      return {
        points: [],
        unavailableReason:
          "A response curve is drawn for single-feature targets only; this one has more than one input.",
      };
    }
    const data = curve.data;
    if (!data || data.task !== "regression") {
      return {
        points: [],
        unavailableReason: curve.isError
          ? "The saved model could not be queried for a response curve."
          : "Sampling the model…",
      };
    }
    return {
      points: data.values.map((y, i) => ({ x: curveFeatures[i][0], y })),
    };
  }, [regressionResult, curveFeatures, curve.data, curve.isError]);

  // Flag resolution order matters: show nothing while the answer is in
  // flight, then either the lab or the same NotFound any unknown URL gets.
  if (!resolved) {
    return (
      <div className="flex items-center justify-center p-16 text-sm text-ink-3">
        <Spinner />
      </div>
    );
  }
  if (!enabled) {
    // The same answer the server gives: with the flag off every /qml/*
    // endpoint 404s, so the page must not pretend the feature is merely
    // unavailable right now. App.tsx's own NotFound is a module-local
    // function, and exporting it would make App and this lazy page import
    // each other; EmptyState carries the same message without the cycle.
    return (
      <div className="flex h-full items-center justify-center p-8">
        <EmptyState
          title="404 - State Undefined"
          description="The quantum route you collapsed does not exist in this Hilbert space."
        />
      </div>
    );
  }

  return (
    <div className="space-y-5 p-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-ink">Quantum ML Lab</h1>
          <p className="mt-0.5 text-xs text-ink-3">
            Train a variational quantum classifier on a locally simulated circuit, and
            measure it against a classical baseline.
          </p>
        </div>
        {experiment && (
          <Badge tone={running ? "accent" : status === "completed" ? "ok" : "warn"}>
            #{experiment.id} {status}
          </Badge>
        )}
      </header>

      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_200px]">
        <Tabs value={view} onValueChange={(v) => setView(v as View)}>
          <TabsList>
            <TabsTrigger value="configure">Configuration</TabsTrigger>
            <TabsTrigger value="circuit">Circuit</TabsTrigger>
            <TabsTrigger value="training">Training</TabsTrigger>
            <TabsTrigger value="results">Results</TabsTrigger>
          </TabsList>

          <TabsContent value="configure">
            <QmlConfigForm
              config={config}
              onChange={setConfig}
              describe={describe.data}
              describeError={describe.error as Error | null}
              onSubmit={() => create.mutate(config)}
              submitting={create.isPending}
              submitError={create.error as Error | null}
              disabled={running}
            />
            {running && (
              <p className="mt-3 text-[11px] text-warn">
                An experiment is running. Only one runs at a time — cancel it from the
                Training tab to submit another.
              </p>
            )}
          </TabsContent>

          <TabsContent value="circuit">
            <QmlCircuitPreview
              circuit={activeCircuit}
              nFeatures={activeFeatures}
              serverParameters={serverParameters}
            />
          </TabsContent>

          <TabsContent value="training">
            {experimentId === null ? (
              <EmptyState
                title="Nothing training"
                description="Submit a configuration to start an experiment, then watch its loss and accuracy here."
              />
            ) : (
              <QmlTrainingDashboard
                experimentId={experimentId}
                status={status}
                history={history}
                totalEpochs={experiment?.config?.training?.epochs ?? config.training.epochs}
                error={experiment?.error ?? null}
                cached={experiment?.cached ?? false}
                onCancel={() => cancel.mutate()}
                cancelling={cancel.isPending}
                cancelError={cancel.error as Error | null}
                onViewResults={() => setView("results")}
                algorithm={algorithmInfo}
                kernel={kernelSummary}
              />
            )}
          </TabsContent>

          <TabsContent value="results">
            {experimentId === null ? (
              <EmptyState
                title="No experiment selected"
                description="Train a model, or pick an earlier experiment from the list."
              />
            ) : (
              <QmlResultsPanel
                result={experiment?.result ?? null}
                status={status}
                error={experiment?.error ?? null}
                inference={inference.data}
                onRunInference={(features) => inference.mutate(features)}
                inferenceRunning={inference.isPending}
                inferenceError={inference.error as Error | null}
                responseCurve={responseCurve}
              />
            )}
            {/* §2E.1: the explanation extends the Results view rather than
                adding a route. Only offered once there is a stored result
                to ground on -- an explanation of nothing is the failure
                mode this feature exists to avoid. */}
            {experimentId != null && experiment?.result && isTerminal(status) && (
              <QmlExplanationPanel experimentId={experimentId} />
            )}
          </TabsContent>
        </Tabs>

        <aside className="space-y-2">
          <h2 className="px-1 text-[10px] font-semibold uppercase tracking-wider text-ink-3">
            Recent
          </h2>
          <div className="rounded-2xl border border-line bg-raised/40 p-2">
            <HistoryList
              experiments={experiments.data ?? []}
              activeId={experimentId}
              onSelect={(id) => {
                reset();
                setExperimentId(id);
                const selectedExp = (experiments.data ?? []).find((e) => e.id === id);
                if (selectedExp?.config) {
                  setConfig(selectedExp.config);
                }
                setView("results");
              }}
            />
          </div>
        </aside>
      </div>
    </div>
  );
}
