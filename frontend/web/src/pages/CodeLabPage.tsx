import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Hammer, RotateCcw, Sparkles } from "lucide-react";
import CodeMirror from "@uiw/react-codemirror";
import { python } from "@codemirror/lang-python";
import { backends } from "../api/backends";
import { submitJob } from "../api/jobs";
import {
  FRAMEWORK_LABELS,
  buildCircuit,
  checkCode,
  generateCode,
  starters,
} from "../api/codelab";
import { useTheme } from "../state/theme";
import { CircuitDiagram } from "../components/results/CircuitDiagram";
import { ResultsPanel } from "../components/results/ResultsPanel";
import { Badge, Button, Card, ErrorNote, Spinner } from "../components/ui";

const SHOT_CHOICES = [128, 256, 512, 1024, 2048, 4096, 8192];

export function CodeLabPage() {
  const [framework, setFramework] = useState<string | null>(null);
  const [code, setCode] = useState("");
  const [debounced, setDebounced] = useState("");
  const [built, setBuilt] = useState<Awaited<ReturnType<typeof buildCircuit>> | null>(null);
  const [jobId, setJobId] = useState<number | null>(null);
  const [runError, setRunError] = useState<string | null>(null);
  const [shots, setShots] = useState(1024);
  const [backendId, setBackendId] = useState("qiskit_aer");
  const [prompt, setPrompt] = useState("");
  const { theme } = useTheme();

  const { data: starterData, isLoading: loadingStarters } = useQuery({
    queryKey: ["codelab-starters"],
    queryFn: starters,
    staleTime: 5 * 60_000,
  });

  // Switching language must replace the code: leaving Qiskit under a Cirq
  // heading is worse than losing an edit. It also invalidates any circuit
  // built from the old language's source.
  useEffect(() => {
    if (!starterData || framework !== null) return;
    setFramework(starterData.frameworks[0] ?? "qiskit");
  }, [starterData, framework]);

  useEffect(() => {
    if (!starterData || framework === null) return;
    setCode(starterData.starters[framework] ?? "");
    setBuilt(null);
    setJobId(null);
    // Only when the language changes — not on every keystroke.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [framework, starterData]);

  // Debounce the checks: they run on every keystroke server-side, and the
  // point is to catch a typo before the learner presses Build, not to race
  // their typing.
  useEffect(() => {
    const id = setTimeout(() => setDebounced(code), 400);
    return () => clearTimeout(id);
  }, [code]);

  const findings = useQuery({
    queryKey: ["codelab-check", debounced, framework],
    queryFn: () => checkCode(debounced, framework as string),
    enabled: framework !== null && debounced.length > 0,
    staleTime: 5_000,
  });

  const build = useMutation({
    mutationFn: () => buildCircuit(code, framework as string),
    onSuccess: (result) => {
      setBuilt(result);
      setJobId(null);
      setRunError(null);
    },
  });

  const generate = useMutation({
    mutationFn: () => generateCode(prompt, framework as string),
    onSuccess: (result) => {
      setCode(result.code);
      setBuilt(null);
    },
  });

  const { data: catalogue } = useQuery({ queryKey: ["backends"], queryFn: backends, staleTime: 30_000 });

  const kind = built?.is_dynamic ? "dynamic" : "static";
  const options = useMemo(() => {
    const matching = (catalogue?.backends ?? []).filter((b) => b.supports.includes(kind));
    return matching.length > 0 ? matching : (catalogue?.backends ?? []);
  }, [catalogue, kind]);

  useEffect(() => {
    if (options.length === 0) return;
    if (!options.some((b) => b.id === backendId)) setBackendId(options[0].id);
  }, [options, backendId]);

  const chosen = options.find((b) => b.id === backendId) ?? null;
  const maxShots = built?.is_dynamic ? (catalogue?.limits.max_dynamic_shots ?? 8192) : 8192;
  const shotOptions = SHOT_CHOICES.filter((s) => s <= maxShots);
  const effectiveShots = Math.min(shots, maxShots);

  const run = useMutation({
    mutationFn: () => {
      if (!built) throw new Error("Build the circuit first.");
      return submitJob({
        circuit_ir: built.circuit_ir,
        backend: backendId,
        shots: effectiveShots,
      });
    },
    onSuccess: (job) => {
      setJobId(job.id);
      setRunError(null);
    },
    onError: (exc: Error) => setRunError(exc.message),
  });

  const problems = findings.data?.findings ?? [];

  if (loadingStarters) {
    return (
      <p className="flex items-center gap-2 p-6 text-sm text-ink-3">
        <Spinner /> loading languages…
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-5 p-6">
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="text-xl font-semibold tracking-tight">Code Lab</h2>
        <p className="text-sm text-ink-3">
          Write a program that builds a circuit, then run it on any backend. Assign your
          finished circuit to a variable named <code className="font-mono text-ink-2">circuit</code>.
        </p>
        <div className="ml-auto flex items-center gap-2">
          <label htmlFor="framework" className="text-[13px] text-ink-2">
            Language
          </label>
          <select
            id="framework"
            value={framework ?? ""}
            onChange={(e) => setFramework(e.target.value)}
            className="h-9 rounded-lg border border-line bg-raised px-2 text-sm text-ink"
          >
            {(starterData?.frameworks ?? []).map((f) => (
              <option key={f} value={f}>
                {FRAMEWORK_LABELS[f] ?? f}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_340px]">
        <div className="flex flex-col gap-4">
          <Card className="p-0">
            <div className="overflow-hidden rounded-xl">
              <CodeMirror
                value={code}
                height="340px"
                theme={theme === "dark" ? "dark" : "light"}
                extensions={framework === "qasm3" ? [] : [python()]}
                onChange={(value) => setCode(value)}
                basicSetup={{ lineNumbers: true, foldGutter: false, highlightActiveLine: true }}
              />
            </div>
          </Card>

          <Card>
            <div className="mb-2 flex items-center gap-2">
              <h3 className="text-sm font-semibold">Problems</h3>
              {findings.isFetching && <Spinner />}
              {!findings.isFetching && problems.length > 0 && (
                <Badge tone="danger">
                  {problems.length} problem{problems.length === 1 ? "" : "s"}
                </Badge>
              )}
              {!findings.isFetching && problems.length === 0 && code.trim().length > 0 && (
                <Badge tone="accent">ready to build</Badge>
              )}
            </div>
            {problems.length > 0 ? (
              <>
                <p className="mb-2 text-[13px] text-ink-2">
                  Fix these before building:
                </p>
                <ul className="flex flex-col gap-1">
                  {problems.map((f) => (
                    <li key={`${f.line}-${f.column}-${f.message}`} className="text-[13px] text-ink-2">
                      <strong className="font-medium text-ink">Line {f.line}</strong>, col{" "}
                      {f.column} — {f.message}
                    </li>
                  ))}
                </ul>
              </>
            ) : (
              <p className="text-[13px] text-ink-3">
                Nothing found. These checks are static: they catch typos, blocked imports and
                a missing <code className="font-mono">circuit</code>, but they never run your
                program.
              </p>
            )}
          </Card>

          {problems.length > 0 && findings.data?.annotated && (
            <details
              open
              className="rounded-xl border border-line bg-raised p-4 [&_summary]:cursor-pointer"
            >
              <summary className="text-sm font-semibold">
                Highlighted view with error markers
              </summary>
              <pre className="mt-3 overflow-auto rounded-lg border border-line-soft bg-hover/60 p-3 font-mono text-[12px] leading-relaxed text-ink-2">
                {findings.data.annotated}
              </pre>
            </details>
          )}

          <details className="rounded-xl border border-line bg-raised p-4 [&_summary]:cursor-pointer">
            <summary className="text-sm font-semibold">What am I allowed to write?</summary>
            <div className="mt-3 flex flex-col gap-2 text-[13px] leading-relaxed text-ink-2">
              <p>
                Your code runs in a <strong className="text-ink">sandbox</strong>: a separate
                process with a time limit and no access to files, the network, or other
                programs. You can import <code className="font-mono">qiskit</code>,{" "}
                <code className="font-mono">cirq</code>,{" "}
                <code className="font-mono">pennylane</code>,{" "}
                <code className="font-mono">numpy</code>,{" "}
                <code className="font-mono">math</code> and other maths libraries.
              </p>
              <p>
                <strong className="text-ink">The one rule:</strong> assign your circuit to a
                variable named <code className="font-mono">circuit</code>.
              </p>
              <ul className="list-disc pl-5">
                <li>
                  <strong className="text-ink">Qiskit</strong> — a{" "}
                  <code className="font-mono">QuantumCircuit</code>
                </li>
                <li>
                  <strong className="text-ink">Cirq</strong> — a{" "}
                  <code className="font-mono">cirq.Circuit</code>
                </li>
                <li>
                  <strong className="text-ink">PennyLane</strong> — a{" "}
                  <code className="font-mono">QNode</code> (the decorated function)
                </li>
                <li>
                  <strong className="text-ink">OpenQASM 3</strong> — no Python at all: write
                  QASM directly and it is parsed as-is (this is the platform&apos;s native
                  format)
                </li>
              </ul>
              <p>
                Beyond the quantum SDKs you can import{" "}
                <code className="font-mono">qiskit_aer</code>,{" "}
                <code className="font-mono">matplotlib</code>,{" "}
                <code className="font-mono">pandas</code>,{" "}
                <code className="font-mono">networkx</code>,{" "}
                <code className="font-mono">scipy</code>,{" "}
                <code className="font-mono">sympy</code> and the pure-computation parts of the
                standard library. Anything that reaches the filesystem, network or other
                processes stays blocked.
              </p>
              <p>
                Angles must be concrete numbers: bind a Qiskit{" "}
                <code className="font-mono">Parameter</code> with{" "}
                <code className="font-mono">qc.assign_parameters(&#123;theta: 3.14159 / 2&#125;)</code>{" "}
                before returning the circuit.
              </p>
              <p>
                Your program&apos;s <code className="font-mono">print()</code> output is shown
                back to you, so you can debug. Circuits are converted to OpenQASM 3 internally,
                so a gate outside the supported set will be reported rather than silently
                dropped.
              </p>
            </div>
          </details>
        </div>

        <div className="flex flex-col gap-4">
          <Card>
            <h3 className="mb-2 text-sm font-semibold">Generate code with AI</h3>
            <p className="mb-3 text-[13px] leading-relaxed text-ink-2">
              Describe the circuit and Gemini drafts{" "}
              <strong className="text-ink">{FRAMEWORK_LABELS[framework ?? ""] ?? framework}</strong>{" "}
              code into the editor. Nothing runs until you press Build, and you can edit the
              draft first — treat it as a starting point, not an answer.
            </p>
            <input
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="a GHZ state on 3 qubits, then measure everything"
              className="mb-2 h-9 w-full rounded-lg border border-line bg-raised px-3 text-sm text-ink placeholder:text-ink-3"
            />
            <Button
              size="sm"
              disabled={!prompt.trim() || generate.isPending}
              onClick={() => generate.mutate()}
              className="w-full"
            >
              {generate.isPending ? <Spinner /> : <Sparkles className="h-3.5 w-3.5" />}
              Generate
            </Button>
            {generate.isError && (
              <ErrorNote className="mt-2">{String(generate.error)}</ErrorNote>
            )}
          </Card>

          <div className="flex gap-2">
            <Button
              variant="primary"
              className="flex-1"
              disabled={!framework || build.isPending}
              onClick={() => build.mutate()}
            >
              {build.isPending ? <Spinner /> : <Hammer className="h-4 w-4" />}
              Build circuit
            </Button>
            <Button
              onClick={() => {
                if (framework && starterData) setCode(starterData.starters[framework] ?? "");
              }}
              title="Reset to example"
            >
              <RotateCcw className="h-4 w-4" />
            </Button>
          </div>
          {build.isError && <ErrorNote>{String(build.error)}</ErrorNote>}

          {built && (
            <Card>
              <div className="mb-3 flex items-center gap-2">
                <Badge tone="accent">circuit built</Badge>
                <span className="text-[13px] text-ink-3">
                  {built.n_qubits} qubits · depth {built.depth}
                </span>
              </div>
              {built.stdout && (
                <details
                  open
                  className="mb-3 rounded-lg border border-line-soft [&_summary]:cursor-pointer"
                >
                  <summary className="px-3 py-2 text-[13px] font-medium">
                    Your program&apos;s output
                  </summary>
                  <pre className="max-h-48 overflow-auto border-t border-line-soft bg-hover/60 p-3 font-mono text-[12px] text-ink-2">
                    {built.stdout}
                  </pre>
                </details>
              )}
              <div className="flex gap-3">
                <label className="flex-1 text-[13px] text-ink-2">
                  Backend
                  <select
                    value={backendId}
                    onChange={(e) => setBackendId(e.target.value)}
                    className="mt-1 h-9 w-full rounded-lg border border-line bg-raised px-2 text-sm text-ink"
                  >
                    {options.map((b) => (
                      <option key={b.id} value={b.id} disabled={!b.available}>
                        {b.label}
                        {b.available ? "" : "  (unavailable)"}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="w-24 text-[13px] text-ink-2">
                  Shots
                  <select
                    value={effectiveShots}
                    onChange={(e) => setShots(Number(e.target.value))}
                    className="mt-1 h-9 w-full rounded-lg border border-line bg-raised px-2 text-sm text-ink"
                  >
                    {shotOptions.map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              {chosen && !chosen.available && (
                <p className="mt-2 text-[13px] text-warn">{chosen.reason}</p>
              )}
              <ErrorNote className="mt-2">{runError}</ErrorNote>
              <Button
                variant="primary"
                className="mt-3 w-full"
                disabled={!chosen?.available || run.isPending}
                onClick={() => run.mutate()}
              >
                {run.isPending ? <Spinner /> : <Hammer className="h-4 w-4" />}
                Run simulation
              </Button>
            </Card>
          )}
        </div>
      </div>

      {built && (
        <Card>
          <h3 className="mb-3 text-sm font-semibold">Built circuit</h3>
          <div className="overflow-auto">
            <CircuitDiagram ir={built.circuit_ir} />
          </div>
          <details className="mt-3 [&_summary]:cursor-pointer">
            <summary className="text-[13px] font-medium text-ink-2">OpenQASM 3</summary>
            <pre className="mt-2 max-h-64 overflow-auto rounded-lg border border-line-soft bg-hover/60 p-3 font-mono text-[12px] text-ink-2">
              {built.qasm3}
            </pre>
          </details>
        </Card>
      )}

      <ResultsPanel
        jobId={jobId}
        stale={false}
        ranQubits={built?.n_qubits ?? null}
        currentQubits={built?.n_qubits ?? 0}
        ir={built?.circuit_ir ?? { name: "circuit", n_qubits: 0, n_clbits: 0, ops: [] }}
      />
    </div>
  );
}
