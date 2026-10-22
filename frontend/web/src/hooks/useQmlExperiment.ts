/* Polling + history accumulation for one QML experiment.
 *
 * `GET /qml/experiments/{id}` is incremental: it takes `after_epoch` and
 * returns only rows past it (`services/qml_lab.py:219-241`). That keeps the
 * poll cheap, but it means the caller owns the curve — a component that just
 * renders `data.history` would show the last tick's epochs and nothing else,
 * with the chart appearing to reset every half second.
 *
 * So history is accumulated here, merged by epoch number. Merging by key
 * rather than appending makes it idempotent: react-query can retry a request
 * or run the same fetch twice under StrictMode without duplicating points.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  cancelExperiment,
  getExperiment,
  isTerminal,
  runInference,
  type EpochRow,
  type ExperimentDetail,
} from "../api/qml";

/** How often a live experiment is polled, in milliseconds. */
export const POLL_INTERVAL_MS = 1000;

export function useQmlExperiment(experimentId: number | null) {
  const queryClient = useQueryClient();
  const [history, setHistory] = useState<EpochRow[]>([]);
  const lastEpochRef = useRef(0);

  // A new experiment starts a new curve. Doing this in an effect keyed on the
  // id — rather than inside the query — means the old points are gone before
  // the first response of the new run can be merged into them.
  useEffect(() => {
    setHistory([]);
    lastEpochRef.current = 0;
  }, [experimentId]);

  const query = useQuery({
    queryKey: ["qml", "experiment", experimentId],
    queryFn: () => getExperiment(experimentId as number, lastEpochRef.current),
    enabled: experimentId !== null,
    // `false` stops the poll; 0 would be a legal interval that spins.
    refetchInterval: (q) => (isTerminal(q.state.data?.status) ? false : POLL_INTERVAL_MS),
    refetchIntervalInBackground: false,
    staleTime: 0,
  });

  const data: ExperimentDetail | undefined = query.data;

  useEffect(() => {
    if (!data || data.history.length === 0) return;
    setHistory((prev) => {
      const merged = new Map(prev.map((row) => [row.epoch, row]));
      for (const row of data.history) merged.set(row.epoch, row);
      const next = [...merged.values()].sort((a, b) => a.epoch - b.epoch);
      lastEpochRef.current = next.length > 0 ? next[next.length - 1].epoch : 0;
      return next;
    });
  }, [data]);

  const cancel = useMutation({
    mutationFn: () => cancelExperiment(experimentId as number),
    onSuccess: () => {
      // Pull the terminal status straight away rather than waiting out the
      // poll, so the button stops saying "Cancelling…" immediately.
      void queryClient.invalidateQueries({ queryKey: ["qml", "experiment", experimentId] });
      void queryClient.invalidateQueries({ queryKey: ["qml", "experiments"] });
    },
  });

  const inference = useMutation({
    mutationFn: (features: number[][]) => runInference(experimentId as number, features),
  });

  const reset = useCallback(() => {
    setHistory([]);
    lastEpochRef.current = 0;
    inference.reset();
  }, [inference]);

  return {
    experiment: data,
    history,
    isLoading: query.isPending && experimentId !== null,
    error: query.error as Error | null,
    cancel,
    inference,
    reset,
  };
}
