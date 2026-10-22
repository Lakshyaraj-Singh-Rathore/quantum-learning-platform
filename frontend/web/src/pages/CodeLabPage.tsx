import { useEffect, useMemo, useState, useRef } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  Play,
  RotateCcw,
  Sparkles,
  Hammer,
  Code2,
  Terminal,
  AlertTriangle,
  GripHorizontal,
} from "lucide-react";
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
import { CircuitDiagram } from "../components/results/CircuitDiagram";
import { ResultsPanel } from "../components/results/ResultsPanel";
import {
  Badge,
  Button,
  Card,
  ErrorNote,
  Label,
  Select,
  SelectItem,
  Spinner,
  Tabs,
  TabsList,
  TabsTrigger,
  Textarea,
} from "../components/ui";

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

  // Editor height resizer state
  const [editorHeight, setEditorHeight] = useState<number>(() => {
    try {
      const saved = localStorage.getItem("ql_codelab_editor_height");
      return saved ? Math.max(200, Math.min(600, parseInt(saved, 10))) : 400;
    } catch {
      return 400;
    }
  });
  const isDragging = useRef(false);
  const dragStartY = useRef(0);
  const startHeight = useRef(400);

  const { data: starterData, isLoading: loadingStarters } = useQuery({
    queryKey: ["codelab-starters"],
    queryFn: starters,
    staleTime: 5 * 60_000,
  });

  useEffect(() => {
    if (!starterData || framework !== null) return;
    setFramework(starterData.frameworks[0] ?? "qiskit");
  }, [starterData, framework]);

  useEffect(() => {
    if (!starterData || framework === null) return;
    setCode(starterData.starters[framework] ?? "");
    setBuilt(null);
    setJobId(null);
  }, [framework, starterData]);

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

  const { data: catalogue } = useQuery({ queryKey: ["backends"], queryFn: backends, staleTime: 30_000 });

  const kind = built?.is_dynamic ? "dynamic" : "static";
  const options = useMemo(() => {
    const matching = (catalogue?.backends ?? []).filter((b) => b.supports.includes(kind));
    return matching.length > 0 ? matching : (catalogue?.backends ?? []);
  }, [catalogue, kind]);

  useEffect(() => {
    if (options.length === 0) return;
    const defaultBackend =
      framework === "qasm3"
        ? "openqasm3"
        : framework === "cirq"
        ? "cirq"
        : framework === "pennylane"
        ? "pennylane"
        : framework === "cudaq"
        ? "cudaq"
        : "qiskit_aer";
    if (options.some((b) => b.id === defaultBackend)) {
      setBackendId(defaultBackend);
    } else if (!options.some((b) => b.id === backendId)) {
      setBackendId(options[0].id);
    }
  }, [framework, options]);

  const chosen = options.find((b) => b.id === backendId) ?? null;
  const maxShots = built?.is_dynamic ? (catalogue?.limits.max_dynamic_shots ?? 8192) : 8192;
  const shotOptions = SHOT_CHOICES.filter((s) => s <= maxShots);
  const effectiveShots = Math.min(shots, maxShots);

  const run = useMutation({
    mutationFn: (circuitIR?: any) => {
      const targetIR = circuitIR ?? built?.circuit_ir;
      if (!targetIR) throw new Error("Build the circuit first.");
      return submitJob({
        circuit_ir: targetIR,
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

  const build = useMutation({
    mutationFn: () => buildCircuit(code, framework as string),
    onSuccess: (result) => {
      setBuilt(result);
      setJobId(null);
      setRunError(null);
    },
  });

  // Single click Build & Run flow
  const buildAndRun = useMutation({
    mutationFn: async () => {
      const result = await buildCircuit(code, framework as string);
      setBuilt(result);
      setRunError(null);
      return run.mutateAsync(result.circuit_ir);
    },
    onError: (exc: Error) => setRunError(exc.message),
  });

  const generate = useMutation({
    mutationFn: () => generateCode(prompt, framework as string),
    onSuccess: (result) => {
      setCode(result.code);
      setBuilt(null);
    },
  });

  // Drag resizer handlers
  const handleMouseDown = (e: React.MouseEvent) => {
    isDragging.current = true;
    dragStartY.current = e.clientY;
    startHeight.current = editorHeight;
    document.body.style.cursor = "row-resize";
    document.body.style.userSelect = "none";

    const onMouseMove = (ev: MouseEvent) => {
      if (!isDragging.current) return;
      const delta = ev.clientY - dragStartY.current;
      const nextH = Math.max(200, Math.min(600, startHeight.current + delta));
      setEditorHeight(nextH);
      localStorage.setItem("ql_codelab_editor_height", nextH.toString());
    };

    const onMouseUp = () => {
      isDragging.current = false;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
    };

    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);
  };

  const problems = findings.data?.findings ?? [];
  const generationError = generate.error ? String(generate.error) : "";
  const aiNotConfigured = generationError.includes("GEMINI_API_KEY");

  if (loadingStarters) {
    return (
      <div className="flex items-center justify-center p-12 text-ink-3 text-sm">
        <Spinner className="mr-2" /> Loading Code Lab SDKs…
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 p-6 max-w-6xl mx-auto">
      {/* Top Header & Language Picker */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-line pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-ink flex items-center gap-2.5">
            <Code2 className="h-6 w-6 text-accent" /> Quantum Code Lab
          </h1>
          <p className="text-sm text-ink-3 mt-1">
            Write code in Qiskit, Cirq, PennyLane or OpenQASM 3. Assign your output circuit to a variable named{" "}
            <code className="font-mono text-accent-ink bg-subtle px-1.5 py-0.5 rounded border border-line">circuit</code>.
          </p>
        </div>

        {/* Framework Tabs */}
        {starterData && (
          <Tabs
            value={framework ?? "qiskit"}
            onValueChange={(val) => setFramework(val)}
            className="w-auto"
          >
            <TabsList>
              {starterData.frameworks.map((f) => (
                <TabsTrigger key={f} value={f}>
                  {FRAMEWORK_LABELS[f] ?? f}
                </TabsTrigger>
              ))}
            </TabsList>
          </Tabs>
        )}
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_340px]">
        {/* Left Column: Resizable CodeMirror Editor & Problems (if any) */}
        <div className="flex flex-col gap-4">
          <Card className="p-0 overflow-hidden border-line bg-raised shadow-md relative">
            <div className="flex items-center justify-between border-b border-line-soft bg-subtle/80 px-4 py-2">
              <span className="text-xs font-mono text-ink-3 flex items-center gap-1.5">
                <Terminal className="h-3.5 w-3.5 text-accent" />
                {FRAMEWORK_LABELS[framework ?? ""] ?? framework} Editor
              </span>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => {
                  if (framework && starterData) setCode(starterData.starters[framework] ?? "");
                }}
                className="h-6 text-xs text-ink-3 hover:text-ink gap-1"
                title="Reset to starter code"
              >
                <RotateCcw className="h-3 w-3" /> Reset
              </Button>
            </div>

            {/* CodeMirror instance with dynamic resizable height */}
            <div style={{ height: `${editorHeight}px` }} className="overflow-hidden">
              <CodeMirror
                value={code}
                height={`${editorHeight}px`}
                theme="dark"
                extensions={framework === "qasm3" ? [] : [python()]}
                onChange={(value) => setCode(value)}
                basicSetup={{ lineNumbers: true, foldGutter: false, highlightActiveLine: true }}
              />
            </div>

            {/* Vertical Resize Drag Handle */}
            <div
              onMouseDown={handleMouseDown}
              className="h-3 w-full bg-subtle hover:bg-line-focus cursor-row-resize flex items-center justify-center border-t border-line transition-colors"
              title="Drag up or down to resize editor height"
            >
              <GripHorizontal className="h-3.5 w-3.5 text-ink-3/70" />
            </div>
          </Card>

          {/* Problems Card: ONLY rendered when problems exist */}
          {problems.length > 0 && (
            <Card className="border-danger/30 bg-danger/5 p-4">
              <div className="flex items-center gap-2 mb-2 text-danger">
                <AlertTriangle className="h-4 w-4" />
                <h3 className="text-xs font-bold uppercase tracking-wider">
                  Syntax & Static Analysis Issues ({problems.length})
                </h3>
              </div>
              <ul className="space-y-1 text-xs text-ink-2 pl-6 list-disc">
                {problems.map((f, i) => (
                  <li key={i}>
                    <strong className="text-ink font-mono">Line {f.line}:{f.column}</strong> — {f.message}
                  </li>
                ))}
              </ul>

              {findings.data?.annotated && (
                <pre className="mt-3 overflow-x-auto rounded-lg border border-danger/20 bg-subtle p-3 font-mono text-[11px] text-ink-2">
                  {findings.data.annotated}
                </pre>
              )}
            </Card>
          )}

          {/* Educational Sandbox Notes */}
          <details className="rounded-xl border border-line bg-raised p-4 [&_summary]:cursor-pointer">
            <summary className="text-xs font-semibold text-ink-2 hover:text-ink">
              Sandbox execution environment & supported packages
            </summary>
            <div className="mt-3 text-xs leading-relaxed text-ink-3 space-y-2">
              <p>
                Code runs isolated in an ephemeral sandbox with no disk or outbound network access.
                Available imports include: <code className="font-mono text-accent-ink">qiskit</code>,{" "}
                <code className="font-mono text-accent-ink">cirq</code>,{" "}
                <code className="font-mono text-accent-ink">pennylane</code>,{" "}
                <code className="font-mono text-accent-ink">numpy</code>, and pure computational modules.
              </p>
              <p>
                Ensure your final circuit is stored in variable <code className="font-mono text-ink">circuit</code>.
              </p>
            </div>
          </details>
        </div>

        {/* Right Column: AI Assistant & Build/Run Controls */}
        <div className="flex flex-col gap-4">
          {/* AI Drafting Card */}
          <Card className="p-4 border-line bg-raised">
            <div className="flex items-center gap-2 mb-1.5">
              <Sparkles className="h-4 w-4 text-accent" />
              <h3 className="text-sm font-semibold text-ink">AI Code Assistant</h3>
            </div>
            <p className="text-xs text-ink-3 mb-3 leading-relaxed">
              Describe a circuit algorithm and Gemini will draft code into the editor.
              Nothing runs until you press Build, and you can edit the draft first —
              treat it as a starting point, not an answer.
            </p>

            <Textarea
              rows={3}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="e.g. Prepare a 3-qubit GHZ state, then measure all qubits..."
              className="text-xs mb-2.5 resize-none"
            />

            <Button
              size="sm"
              variant="secondary"
              disabled={!prompt.trim() || generate.isPending || aiNotConfigured}
              onClick={() => generate.mutate()}
              className="w-full gap-1.5 text-xs"
            >
              {generate.isPending ? <Spinner className="h-3.5 w-3.5" /> : <Sparkles className="h-3.5 w-3.5 text-accent" />}
              Draft Code into Editor
            </Button>

            {aiNotConfigured && (
              <p className="mt-2 text-[11px] text-warn bg-warn/10 p-2 rounded border border-warn/20">
                GEMINI_API_KEY is not configured in backend .env
              </p>
            )}
            {generate.isError && !aiNotConfigured && (
              <ErrorNote className="mt-2 text-xs">{String(generate.error)}</ErrorNote>
            )}
          </Card>

          {/* Unified Build & Run Action Card */}
          <Card className="p-4 border-line bg-raised space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-ink-3">
              Execution Controls
            </h3>

            {/* Backend & Shots Config */}
            <div className="space-y-3">
              <div>
                <Label className="text-xs">Execution Engine</Label>
                <Select
                  value={backendId}
                  onValueChange={setBackendId}
                  className="bg-bg text-xs"
                >
                  {options.map((b) => (
                    <SelectItem key={b.id} value={b.id} disabled={!b.available}>
                      {b.label}
                    </SelectItem>
                  ))}
                </Select>
              </div>

              <div>
                <Label className="text-xs">Sampling Shots</Label>
                <Select
                  value={String(effectiveShots)}
                  onValueChange={(val) => setShots(Number(val))}
                  className="bg-bg text-xs"
                >
                  {shotOptions.map((s) => (
                    <SelectItem key={s} value={String(s)}>
                      {s} shots
                    </SelectItem>
                  ))}
                </Select>
              </div>
            </div>

            {/* Action Buttons: Unified "Build & Run" Primary Flow */}
            <div className="space-y-2 pt-2 border-t border-line-soft">
              <Button
                variant="primary"
                size="md"
                disabled={!framework || buildAndRun.isPending || problems.length > 0 || (chosen ? !chosen.available : false)}
                onClick={() => buildAndRun.mutate()}
                className="w-full gap-2 shadow-sm font-semibold"
              >
                {buildAndRun.isPending ? (
                  <Spinner className="h-4 w-4" />
                ) : (
                  <Play className="h-4 w-4" />
                )}
                Build & Run Simulation
              </Button>

              <Button
                variant="secondary"
                size="sm"
                disabled={!framework || build.isPending || problems.length > 0}
                onClick={() => build.mutate()}
                className="w-full text-xs gap-1.5"
              >
                {build.isPending ? <Spinner className="h-3 w-3" /> : <Hammer className="h-3 w-3" />}
                Build Circuit Only
              </Button>
            </div>

            {buildAndRun.isError && <ErrorNote className="text-xs">{String(buildAndRun.error)}</ErrorNote>}
            {build.isError && <ErrorNote className="text-xs">{String(build.error)}</ErrorNote>}
            {runError && <ErrorNote className="text-xs">{runError}</ErrorNote>}
          </Card>

          {/* Build Output Summary */}
          {built && (
            <Card className="p-4 border-line bg-raised">
              <div className="flex items-center justify-between mb-2">
                <Badge tone="ok">Circuit Compiled</Badge>
                <span className="text-xs font-mono text-ink-3">
                  {built.n_qubits} qubits · depth {built.depth}
                </span>
              </div>

              {built.stdout && (
                <div className="mt-3">
                  <span className="text-[11px] font-semibold text-ink-3 uppercase tracking-wider block mb-1">
                    Standard Output:
                  </span>
                  <pre className="max-h-36 overflow-auto rounded border border-line bg-subtle p-2 font-mono text-[11px] text-ink-2">
                    {built.stdout}
                  </pre>
                </div>
              )}
            </Card>
          )}
        </div>
      </div>

      {/* Built Circuit Diagram */}
      {built && (
        <Card className="p-6">
          <h3 className="text-base font-bold text-ink mb-3">Compiled Quantum Circuit Diagram</h3>
          <div className="overflow-x-auto rounded-xl border border-line bg-subtle p-4">
            <CircuitDiagram ir={built.circuit_ir} />
          </div>

          <details className="mt-4 [&_summary]:cursor-pointer">
            <summary className="text-xs font-semibold text-ink-2 hover:text-ink">
              View Generated OpenQASM 3.0 IR
            </summary>
            <pre className="mt-2 max-h-64 overflow-auto rounded-lg border border-line bg-subtle p-3 font-mono text-xs text-ink-2">
              {built.qasm3}
            </pre>
          </details>
        </Card>
      )}

      {/* Results Panel */}
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
