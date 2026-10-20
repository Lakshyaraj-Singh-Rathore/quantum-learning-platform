import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  Play,
  RotateCcw,
  Sparkles,
  Upload,
  Download,
  FileDown,
  Save,
  FolderOpen,
  Plus,
  Minus,
  ChevronDown,
  ChevronUp,
  ArrowRight,
  X,
  Code2,
  BarChart3,
  Globe,
    Copy,
    ExternalLink,
    AlertTriangle,
  } from "lucide-react";
import { ComposerInner } from "@composer/Composer";
import { circuitIsDynamic, maxLayer } from "@composer/ir";
import { bell, ghz, wState, qft3, emptyCircuit, useCircuit } from "../state/circuit";
import { backends } from "../api/backends";
import { inspectCircuit, submitJob, type NoiseIn } from "../api/jobs";
import { buildCircuit } from "../api/codelab";
import { simulateCircuit, PREVIEW_MAX_QUBITS } from "../lib/circuitSimulator";
import {
  EXPORT_TARGETS,
  downloadCircuitFile,
  copyCircuitCode,
  generateQasm3,
} from "../lib/circuitExport";
import { Histogram } from "../components/results/ResultsViews";
import { QSphere } from "../components/results/GeometryViews";
import {
  cn,
  Badge,
  Button,
  Card,
  ConfirmModal,
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  ErrorNote,
  Input,
  Label,
  Select,
  SelectItem,
  Spinner,
  Tooltip,
  toast,
} from "../components/ui";
import { ResultsPanel } from "../components/results/ResultsPanel";

const SHOT_CHOICES = [128, 256, 512, 1024, 2048, 4096, 8192];
const NOISE_BACKENDS = new Set(["qiskit_aer", "cudaq"]);

const DEFAULT_NOISE: NoiseIn = {
  enabled: false,
  t1_us: 50,
  t2_us: 30,
  readout_error: 0.02,
  gate_time_1q_us: 0.1,
  gate_time_2q_us: 0.4,
  gate_time_3q_us: 1.0,
};

interface SavedCircuitRecord {
  id: string;
  name: string;
  date: string;
  ir: any;
}

export function ComposerPage() {
  const navigate = useNavigate();
  const ir = useCircuit((state) => state.ir);
  const epoch = useCircuit((state) => state.epoch);
  const circuitName = useCircuit((state) => state.circuitName ?? "Quantum Circuit");
  const challengeContext = useCircuit((state) => state.challengeContext);
  const setIr = useCircuit((state) => state.setIr);
  const resetCircuit = useCircuit((state) => state.reset);
  const setQubits = useCircuit((state) => state.setQubits);
  const setCircuitName = useCircuit((state) => state.setCircuitName);
  const setChallengeContext = useCircuit((state) => state.setChallengeContext);

  const [shots, setShots] = useState(1024);
  const [backendId, setBackendId] = useState<string>("qiskit_aer");
  const [noise, setNoise] = useState<NoiseIn>(DEFAULT_NOISE);
  const [jobId, setJobId] = useState<number | null>(null);
  const [runSnapshot, setRunSnapshot] = useState<string | null>(null);
  const [ranQubits, setRanQubits] = useState<number | null>(null);
  const [runError, setRunError] = useState<string | null>(null);

  // IBM Quantum Platform Layout States
  const [showQasm, setShowQasm] = useState(false);
  const [bottomView, setBottomView] = useState<"ibm_dual" | "advanced" | "noise">("ibm_dual");

  // Live analytical statevector preview. Capped at PREVIEW_MAX_QUBITS (12) —
  // statevector cost is O(2^n) and it runs synchronously on every edit, so
  // wider circuits would block the main thread. Wider circuits still build and
  // still run on a backend; the preview just stops following and says so.
  const liveResult = useMemo(() => simulateCircuit(ir), [ir]);

  // Live OpenQASM 3.0 Code Generation
  const qasmCode = useMemo(() => generateQasm3(ir), [ir]);

  // Export Menu State & Handlers
  const [exportMenuOpen, setExportMenuOpen] = useState(false);
  const [exportMode, setExportMode] = useState<"file" | "code">("file");
  const exportMenuRef = useRef<HTMLDivElement>(null);

  // Close Export Menu on outside click or Escape key
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (exportMenuRef.current && !exportMenuRef.current.contains(e.target as Node)) {
        setExportMenuOpen(false);
      }
    }
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        setExportMenuOpen(false);
      }
    }
    if (exportMenuOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      document.addEventListener("keydown", handleKeyDown);
      return () => {
        document.removeEventListener("mousedown", handleClickOutside);
        document.removeEventListener("keydown", handleKeyDown);
      };
    }
  }, [exportMenuOpen]);

  // Dialog States
  const [clearConfirmOpen, setClearConfirmOpen] = useState(false);
  const [importDialogOpen, setImportDialogOpen] = useState(false);
  const [importQasmText, setImportQasmText] = useState("");
  const [importBusy, setImportBusy] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);

  const [savedCircuitsDialogOpen, setSavedCircuitsDialogOpen] = useState(false);
  const [savedCircuits, setSavedCircuits] = useState<SavedCircuitRecord[]>(() => {
    try {
      const stored = localStorage.getItem("ql_saved_circuits");
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  });

  const { data: catalogue } = useQuery({
    queryKey: ["backends"],
    queryFn: backends,
    staleTime: 30_000,
  });

  const dynamic = useMemo(() => circuitIsDynamic(ir), [ir]);
  const depth = maxLayer(ir.ops) + 1;

  const options = useMemo(() => {
    const want = dynamic ? "dynamic" : "static";
    const matching = (catalogue?.backends ?? []).filter((b) => b.supports.includes(want));
    return matching.length > 0 ? matching : (catalogue?.backends ?? []);
  }, [catalogue, dynamic]);

  useEffect(() => {
    if (options.length === 0) return;
    if (!options.some((b) => b.id === backendId)) setBackendId(options[0].id);
  }, [options, backendId]);

  const chosen = options.find((b) => b.id === backendId) ?? null;
  const maxShots = dynamic ? (catalogue?.limits.max_dynamic_shots ?? 8192) : 8192;
  const effectiveShots = Math.min(shots, maxShots);

  const irKey = JSON.stringify(ir);
  const report = useQuery({
    queryKey: ["inspect", irKey, backendId, effectiveShots],
    queryFn: () => inspectCircuit(ir, backendId, effectiveShots),
    staleTime: 5_000,
  });

  const canRun = chosen !== null && chosen.available && report.data?.ok === true;

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
      setRunSnapshot(irKey);
      setRanQubits(ir.n_qubits);
      toast.success("Simulation submitted successfully");
    },
    onError: (exc: Error) => {
      setRunError(exc.message);
      toast.error(`Simulation failed: ${exc.message}`);
    },
  });

  // Keyboard shortcut Ctrl+Enter to run
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        if (canRun && !run.isPending) {
          e.preventDefault();
          run.mutate();
        }
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [canRun, run]);

  // QASM Import Handler
  async function handleImportQasm() {
    if (!importQasmText.trim()) return;
    setImportBusy(true);
    setImportError(null);
    try {
      const res = await buildCircuit(importQasmText, "qasm3");
      if (res.circuit_ir) {
        setIr(res.circuit_ir);
        setImportDialogOpen(false);
        setImportQasmText("");
        toast.success("Circuit imported successfully from OpenQASM 3");
      }
    } catch (err: any) {
      setImportError(err.message || "Failed to parse OpenQASM 3 code.");
    } finally {
      setImportBusy(false);
    }
  }

  // Circuit Export Helper
  async function handleExportAction(targetId: string, mode: "file" | "code") {
    try {
      if (mode === "file") {
        const filename = downloadCircuitFile(targetId, ir, circuitName, effectiveShots);
        toast.success(`Downloaded ${filename} successfully!`);
      } else {
        const label = await copyCircuitCode(targetId, ir, circuitName, effectiveShots);
        toast.success(`Copied ${label} code to clipboard!`);
      }
      setExportMenuOpen(false);
    } catch (err: any) {
      toast.error(`Export failed: ${err.message || "Unknown error"}`);
    }
  }

  // Save / Load handlers
  function saveCurrentCircuit() {
    const record: SavedCircuitRecord = {
      id: Date.now().toString(),
      name: circuitName || "Untitled Circuit",
      date: new Date().toLocaleDateString(),
      ir,
    };
    const updated = [record, ...savedCircuits];
    setSavedCircuits(updated);
    localStorage.setItem("ql_saved_circuits", JSON.stringify(updated));
    toast.success(`Saved "${record.name}" to browser storage`);
  }

  function loadCircuit(record: SavedCircuitRecord) {
    setIr(record.ir);
    setCircuitName(record.name);
    setSavedCircuitsDialogOpen(false);
    toast.success(`Loaded "${record.name}"`);
  }

  function deleteSavedCircuit(id: string) {
    const updated = savedCircuits.filter((c) => c.id !== id);
    setSavedCircuits(updated);
    localStorage.setItem("ql_saved_circuits", JSON.stringify(updated));
    toast.info("Circuit removed from saved list");
  }

  return (
    <div className="flex flex-col h-full overflow-hidden bg-bg text-ink">
      {/* Challenge Persistent Banner */}
      {challengeContext && (
        <div className="flex items-center justify-between bg-accent-soft border-b border-accent/40 px-4 py-2 text-xs text-accent-ink shrink-0">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-accent">Active Challenge:</span>
            <span className="font-medium text-ink truncate">{challengeContext.title}</span>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="primary"
              size="sm"
              onClick={() => navigate(challengeContext.returnPath)}
              className="h-7 text-xs gap-1.5"
            >
              Submit to Challenge <ArrowRight className="h-3.5 w-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setChallengeContext(undefined)}
              className="h-7 text-xs text-ink-3 hover:text-ink"
            >
              <X className="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>
      )}

      {/* Top Composer Control Toolbar */}
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-line bg-raised px-4 py-2.5 shrink-0 z-20">
        <div className="flex flex-wrap items-center gap-3">
          {/* Circuit Title Input */}
          <Input
            value={circuitName}
            onChange={(e) => setCircuitName(e.target.value)}
            className="h-8 w-44 font-semibold text-xs border-line bg-bg focus:w-56 transition-all"
            placeholder="Circuit Name"
            aria-label="Circuit Name"
          />

          {/* Qubit Count Stepper */}
          <div className="flex items-center rounded-lg border border-line bg-bg p-0.5">
            <button
              onClick={() => setQubits(ir.n_qubits - 1)}
              disabled={ir.n_qubits <= 1}
              className="p-1 text-ink-3 hover:text-ink disabled:opacity-30 rounded-md transition-colors"
              title="Decrease qubits"
              aria-label="Decrease qubits"
            >
              <Minus className="h-3.5 w-3.5" />
            </button>
            <span className="px-2 text-xs font-mono font-medium text-ink tabular-nums">
              {ir.n_qubits} Qubits
            </span>
            <button
              onClick={() => setQubits(ir.n_qubits + 1)}
              disabled={ir.n_qubits >= 20}
              className="p-1 text-ink-3 hover:text-ink disabled:opacity-30 rounded-md transition-colors"
              title="Increase qubits"
              aria-label="Increase qubits"
            >
              <Plus className="h-3.5 w-3.5" />
            </button>
          </div>

          <div className="h-4 w-px bg-line-soft hidden md:block" />

          {/* Presets */}
          <div className="flex items-center gap-1">
            <Button size="sm" variant="ghost" onClick={() => resetCircuit(bell())} title="Load Bell state">
              <Sparkles className="h-3.5 w-3.5 text-accent" /> Bell
            </Button>
            <Button size="sm" variant="ghost" onClick={() => resetCircuit(ghz(3))} title="Load 3-qubit GHZ state">
              GHZ
            </Button>
            <Button size="sm" variant="ghost" onClick={() => resetCircuit(wState())} title="Load 3-qubit W state">
              W State
            </Button>
            <Button size="sm" variant="ghost" onClick={() => resetCircuit(qft3())} title="Load 3-qubit QFT">
              QFT
            </Button>
          </div>
        </div>

        {/* Right Toolbar Actions */}
        <div className="flex items-center gap-2">
          {/* OpenQASM 3 Live Panel Toggle */}
          <Button
            size="sm"
            variant={showQasm ? "secondary" : "ghost"}
            onClick={() => setShowQasm(!showQasm)}
            className="gap-1.5 text-xs font-mono font-medium"
            title="Toggle OpenQASM 3.0 live code panel"
          >
            <Code2 className="h-3.5 w-3.5 text-accent" />
            OpenQASM 3
          </Button>

          {/* QASM Import Button */}
          <Button size="sm" variant="secondary" onClick={() => setImportDialogOpen(true)} className="gap-1.5 text-xs">
            <Upload className="h-3.5 w-3.5" /> Import
          </Button>

          {/* Export Dropdown Menu */}
          <div className="relative" ref={exportMenuRef}>
            <Button
              size="sm"
              variant="secondary"
              onClick={() => setExportMenuOpen((prev) => !prev)}
              className={cn(
                "gap-1.5 text-xs font-medium transition-all duration-150",
                exportMenuOpen && "border-accent/50 bg-hover text-white ring-1 ring-accent/30 shadow-xs"
              )}
              title="Export circuit as downloadable file or copy source code"
              aria-expanded={exportMenuOpen}
              aria-haspopup="menu"
            >
              <Download className="h-3.5 w-3.5 text-accent" />
              <span>Export</span>
              <ChevronDown
                className={cn(
                  "h-3.5 w-3.5 text-ink-3 transition-transform duration-200",
                  exportMenuOpen && "rotate-180 text-accent"
                )}
              />
            </Button>

            {/* Dropdown Popover */}
            {exportMenuOpen && (
              <div
                role="menu"
                className="absolute right-0 top-full mt-1.5 w-84 rounded-xl border border-line bg-raised/95 backdrop-blur-xl p-2.5 shadow-2xl text-ink z-50 animate-in fade-in-0 zoom-in-95"
              >
                {/* Mode Switcher: Export File vs Export Code */}
                <div className="flex rounded-lg bg-subtle/80 p-0.5 border border-line-soft mb-2.5">
                  <button
                    type="button"
                    onClick={() => setExportMode("file")}
                    className={cn(
                      "flex-1 flex items-center justify-center gap-1.5 py-1.5 px-2 rounded-md text-xs font-semibold transition-all cursor-pointer",
                      exportMode === "file"
                        ? "bg-accent/20 text-accent border border-accent/30 shadow-xs"
                        : "text-ink-2 hover:text-ink hover:bg-hover/60"
                    )}
                  >
                    <FileDown className="h-3.5 w-3.5" />
                    <span>Export File</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setExportMode("code")}
                    className={cn(
                      "flex-1 flex items-center justify-center gap-1.5 py-1.5 px-2 rounded-md text-xs font-semibold transition-all cursor-pointer",
                      exportMode === "code"
                        ? "bg-accent/20 text-accent border border-accent/30 shadow-xs"
                        : "text-ink-2 hover:text-ink hover:bg-hover/60"
                    )}
                  >
                    <Copy className="h-3.5 w-3.5" />
                    <span>Export Code</span>
                  </button>
                </div>

                {/* Section Header */}
                <div className="flex items-center justify-between px-1.5 pb-1.5 mb-1 border-b border-line-soft/60">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-ink-3">
                    {exportMode === "file" ? "Download Circuit File" : "Copy Code to Clipboard"}
                  </span>
                  <span className="text-[10px] text-ink-3 font-mono">
                    8 backends
                  </span>
                </div>

                {/* Backends List */}
                <div className="space-y-0.5 max-h-[320px] overflow-y-auto pr-0.5 custom-scrollbar">
                  {EXPORT_TARGETS.map((target) => (
                    <div
                      key={target.id}
                      role="menuitem"
                      onClick={() => handleExportAction(target.id, exportMode)}
                      className="group flex items-center justify-between p-2 rounded-lg hover:bg-hover/80 hover:border-line-focus/30 border border-transparent transition-all cursor-pointer"
                    >
                      <div className="flex items-center gap-2.5 min-w-0">
                        <span
                          className={cn(
                            "flex h-6 w-6 items-center justify-center rounded-md font-mono text-[10px] font-bold shrink-0",
                            target.iconType === "qasm" && "bg-cyan-500/15 text-cyan-400 border border-cyan-500/30",
                            target.iconType === "python" && "bg-emerald-500/15 border border-emerald-500/30",
                            target.iconType === "cpp" && "bg-purple-500/15 text-purple-400 border border-purple-500/30",
                            target.iconType === "json" && "bg-amber-500/15 text-amber-400 border border-amber-500/30"
                          )}
                        >
                          {target.iconType === "python" ? (
                            <svg viewBox="0 0 24 24" className="h-4 w-4 shrink-0" fill="none">
                              <path
                                d="M11.914 1C6.4 1 6.74 3.39 6.74 3.39l.01 2.47h5.21v.74H4.67S1.18 6.19 1.18 11.68c0 5.48 3.05 5.29 3.05 5.29h1.82v-2.55s-.1-3.05 3-3.05h5.17V9.49s.28-3.23-3.24-3.23H6.5v-.77s-.12-2.1 2.57-2.1h5.19S16.9 3.39 16.9 1h-4.99zm-2.87 1.58a.82.82 0 1 1 0 1.63.82.82 0 0 1 0-1.63z"
                                fill="#38bdf8"
                              />
                              <path
                                d="M12.086 23c5.51 0 5.17-2.39 5.17-2.39l-.01-2.47h-5.21v-.74h7.28s3.49.41 3.49-5.08c0-5.48-3.05-5.29-3.05-5.29h-1.82v2.55s.1 3.05-3 3.05h-5.17v1.88s-.28 3.23 3.24 3.23h4.48v.77s.12 2.1-2.57 2.1h-5.19S7.1 20.61 7.1 23h4.99zm2.87-1.58a.82.82 0 1 1 0-1.63.82.82 0 0 1 0 1.63z"
                                fill="#facc15"
                              />
                            </svg>
                          ) : target.iconType === "qasm" ? (
                            <span className="text-[9px] font-bold">Q3</span>
                          ) : target.iconType === "cpp" ? (
                            <span className="text-[9px] font-bold">C++</span>
                          ) : (
                            <span className="text-[10px] font-bold">{"{ }"}</span>
                          )}
                        </span>
                        <div className="min-w-0 flex flex-col">
                          <span className="text-xs font-medium text-ink group-hover:text-white truncate">
                            {target.name}
                          </span>
                          <span className="text-[10px] text-ink-3 truncate leading-tight">
                            {target.description}
                          </span>
                        </div>
                      </div>

                      <div className="flex items-center gap-1.5 shrink-0 ml-2">
                        <span className="text-[10px] font-mono text-ink-3 group-hover:text-accent font-semibold px-1.5 py-0.5 rounded bg-subtle/60 border border-line-soft">
                          {target.ext}
                        </span>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleExportAction(target.id, "file");
                          }}
                          className="p-1 rounded hover:bg-white/10 text-ink-3 hover:text-accent transition-colors"
                          title={`Download ${target.ext} file`}
                        >
                          <FileDown className="h-3.5 w-3.5" />
                        </button>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleExportAction(target.id, "code");
                          }}
                          className="p-1 rounded hover:bg-white/10 text-ink-3 hover:text-accent transition-colors"
                          title={`Copy ${target.framework} code`}
                        >
                          <Copy className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Save / Load */}
          <Button size="sm" variant="ghost" onClick={saveCurrentCircuit} title="Save circuit to storage">
            <Save className="h-3.5 w-3.5" />
          </Button>
          <Button size="sm" variant="ghost" onClick={() => setSavedCircuitsDialogOpen(true)} title="Open saved circuits">
            <FolderOpen className="h-3.5 w-3.5" />
          </Button>

          <div className="h-4 w-px bg-line-soft" />

          {/* Clear Button */}
          <Button size="sm" variant="ghost" onClick={() => setClearConfirmOpen(true)} className="text-danger hover:text-danger hover:bg-danger/10">
            <RotateCcw className="h-3.5 w-3.5" /> Clear
          </Button>
        </div>
      </header>

      {/* Main Unified Scrollable Flow: Canvas on top, Results below */}
      <div className="flex-1 overflow-y-auto min-h-0 bg-bg">
        <div className="max-w-[1600px] mx-auto p-4 sm:p-6 space-y-6 w-full">
          {/* Top: Circuit Canvas & OpenQASM 3 Panel */}
          <div className="flex flex-col lg:flex-row gap-4">
            <div className="flex-1 min-w-0">
              <div className="composer-host dark rounded-xl border border-line bg-raised p-4 shadow-sm">
                <ComposerInner
                  key={epoch}
                  value={ir}
                  nQubits={ir.n_qubits}
                  onChange={setIr}
                  theme={{ base: "dark" }}
                />
              </div>
            </div>

            {/* Right Dock: OpenQASM 3.0 Live Code Panel */}
            {showQasm && (
              <div className="w-full lg:w-80 shrink-0 flex flex-col rounded-xl border border-line bg-raised overflow-hidden shadow-sm h-[520px] animate-in fade-in slide-in-from-right duration-200">
                <div className="flex items-center justify-between border-b border-line bg-subtle px-3 py-2">
                  <div className="flex items-center gap-2">
                    <Code2 className="h-4 w-4 text-accent" />
                    <span className="text-xs font-mono font-semibold text-white">OpenQASM 3.0</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => {
                        downloadCircuitFile("qasm", ir, circuitName);
                        toast.success("Downloaded circuit as .qasm");
                      }}
                      className="h-6 px-2 text-[11px] gap-1"
                      title="Download OpenQASM 3.0 file"
                    >
                      <Download className="h-3 w-3" /> Save .qasm
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => {
                        navigator.clipboard.writeText(qasmCode);
                        toast.success("Copied OpenQASM 3.0 to clipboard");
                      }}
                      className="h-6 px-2 text-[11px] gap-1"
                      title="Copy QASM"
                    >
                      <Copy className="h-3 w-3" /> Copy
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => navigate("/codelab")}
                      className="h-6 px-2 text-[11px] gap-1 text-accent hover:text-accent"
                      title="Open in Code Lab"
                    >
                      <ExternalLink className="h-3 w-3" /> Lab
                    </Button>
                  </div>
                </div>
                <div className="flex-1 p-3 overflow-auto font-mono text-xs text-ink-2 bg-[#080b12] leading-relaxed">
                  {qasmCode.split("\n").map((line, idx) => (
                    <div key={idx} className="flex gap-3 hover:bg-white/[0.02] px-1 py-0.5 rounded">
                      <span className="text-ink-3 select-none w-5 text-right opacity-50">{idx + 1}</span>
                      <span className="text-ink whitespace-pre">{line || " "}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Bottom: Results Section directly below */}
          <div className="rounded-xl border border-line bg-raised overflow-hidden shadow-sm">
            {/* Results Dock Control Header */}
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line bg-subtle px-4 py-2.5">
              <div className="flex items-center gap-3">
                <Badge tone={dynamic ? "warn" : "accent"}>
                  {dynamic ? "Dynamic Circuit" : "Static Circuit"}
                </Badge>
                <span className="text-xs text-ink-3 font-mono">
                  Depth: {depth} · Gates: {ir.ops.length}
                </span>

                {/* View Mode Switcher */}
                <div className="flex items-center gap-1 bg-bg p-0.5 rounded-lg border border-line ml-2">
                  <button
                    type="button"
                    onClick={() => setBottomView("ibm_dual")}
                    className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                      bottomView === "ibm_dual" ? "bg-hover text-white shadow-xs" : "text-ink-3 hover:text-ink"
                    }`}
                  >
                    IBM Dual View
                  </button>
                  <button
                    type="button"
                    onClick={() => setBottomView("advanced")}
                    className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                      bottomView === "advanced" ? "bg-hover text-white shadow-xs" : "text-ink-3 hover:text-ink"
                    }`}
                  >
                    Job Analytics
                  </button>
                  <button
                    type="button"
                    onClick={() => setBottomView("noise")}
                    className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                      bottomView === "noise" ? "bg-hover text-white shadow-xs" : "text-ink-3 hover:text-ink"
                    }`}
                  >
                    Noise Model
                  </button>
                </div>
              </div>

              <div className="flex items-center gap-2.5">
                {/* Backend Selector */}
                <div className="w-52">
                  <Select
                    value={backendId}
                    onValueChange={setBackendId}
                    aria-label="Simulation backend"
                    className="h-8 text-xs bg-raised"
                  >
                    {options.map((b) => (
                      <SelectItem key={b.id} value={b.id} disabled={!b.available}>
                        {b.label}
                      </SelectItem>
                    ))}
                  </Select>
                </div>

                {/* Shots Selector */}
                <div className="w-24">
                  <Select
                    value={String(effectiveShots)}
                    onValueChange={(val) => setShots(Number(val))}
                    aria-label="Simulation shots"
                    className="h-8 text-xs bg-raised"
                  >
                    {SHOT_CHOICES.filter((s) => s <= maxShots).map((s) => (
                      <SelectItem key={s} value={String(s)}>
                        {s} shots
                      </SelectItem>
                    ))}
                  </Select>
                </div>

                {/* Run Simulation Button */}
                <Tooltip
                  content={
                    !canRun
                      ? report.data?.errors[0] || "Selected backend is currently unavailable"
                      : "Execute quantum simulation (Ctrl+Enter)"
                  }
                >
                  <Button
                    variant="primary"
                    size="sm"
                    disabled={!canRun || run.isPending}
                    onClick={() => run.mutate()}
                    className="gap-1.5 h-8 px-4 font-semibold shadow-sm"
                  >
                    {run.isPending ? <Spinner className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}
                    Run on Hardware/Sim
                  </Button>
                </Tooltip>
              </div>
            </div>

            {/* Error Note if any */}
            {runError && (
              <div className="p-2 border-b border-danger/20 bg-danger/5">
                <ErrorNote className="text-xs">{runError}</ErrorNote>
              </div>
            )}

            {/* Scrollable Results Content */}
            <div className="p-4">
              {bottomView === "ibm_dual" && (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  {/* Left Panel: Probabilities */}
                  <div className="flex flex-col rounded-xl border border-line bg-subtle/50 p-4 shadow-sm min-h-[460px]">
                    <div className="flex items-center justify-between border-b border-line pb-3 mb-3">
                      <div className="flex items-center gap-2">
                        <BarChart3 className="h-4 w-4 text-accent" />
                        <h4 className="text-sm font-semibold text-white">Probabilities</h4>
                        <span className="text-[11px] text-ink-3 font-mono">
                          ({Object.keys(liveResult.probabilities).length} basis states)
                        </span>
                      </div>
                        <span className="text-[11px] text-ink-3 font-mono">Live Analytical Preview</span>
                      </div>
                      {liveResult.preview_truncated && (
                        <div
                          role="status"
                          className="mb-3 flex items-start gap-2 rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-2"
                        >
                          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-400" />
                          <p className="text-[11px] leading-relaxed text-amber-200">
                            Preview limited to the first {PREVIEW_MAX_QUBITS} of{" "}
                            {ir.n_qubits} qubits — statevector preview is exponential in
                            width and runs on every edit. Your circuit is unchanged and
                            still runs in full on any backend.
                          </p>
                        </div>
                      )}
                      <div className="flex-1 overflow-auto">
                        <Histogram result={liveResult} circuitLabel={circuitName || "Current Circuit"} />
                      </div>
                  </div>

                  {/* Right Panel: 3D Q-Sphere */}
                  <div className="flex flex-col rounded-xl border border-line bg-subtle/50 p-4 shadow-sm min-h-[460px]">
                    <div className="flex items-center justify-between border-b border-line pb-3 mb-3">
                      <div className="flex items-center gap-2">
                        <Globe className="h-4 w-4 text-accent" />
                        <h4 className="text-sm font-semibold text-white">3D Interactive Q-Sphere</h4>
                      </div>
                      <span className="text-[11px] text-ink-3 font-mono">Drag to Rotate</span>
                    </div>
                    <div className="flex-1 overflow-auto">
                      <QSphere result={liveResult} />
                    </div>
                  </div>
                </div>
              )}

              {bottomView === "noise" && (
                <div className="max-w-2xl mx-auto space-y-4 py-4">
                  <NoisePanelBasic
                    noise={noise}
                    onChange={setNoise}
                    enabled={NOISE_BACKENDS.has(backendId)}
                  />
                </div>
              )}

              {bottomView === "advanced" && (
                <div className="space-y-4">
                  {jobId === null ? (
                    <div className="flex flex-col items-center justify-center p-12 text-center border border-line-soft rounded-2xl bg-subtle/30">
                      <Play className="h-8 w-8 text-accent/50 mb-3 animate-pulse" />
                      <h4 className="text-base font-semibold text-white">No Backend Job Submitted Yet</h4>
                      <p className="text-xs text-ink-3 max-w-md mt-1 mb-4">
                        Click "Run on Hardware/Sim" above to execute this circuit on {backendId} with {effectiveShots} shots and view full execution logs, Born statistics, and density matrices.
                      </p>
                      <Button
                        variant="primary"
                        size="sm"
                        disabled={!canRun || run.isPending}
                        onClick={() => run.mutate()}
                        className="gap-1.5"
                      >
                        <Play className="h-3.5 w-3.5" /> Execute Simulation Run
                      </Button>
                    </div>
                  ) : (
                    <ResultsPanel
                      jobId={jobId}
                      stale={jobId !== null && runSnapshot !== null && runSnapshot !== irKey}
                      ranQubits={ranQubits}
                      currentQubits={ir.n_qubits}
                      ir={ir}
                    />
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Clear Confirmation Modal */}
      <ConfirmModal
        open={clearConfirmOpen}
        onOpenChange={setClearConfirmOpen}
        title="Clear Quantum Circuit"
        description="Are you sure you want to remove all gates and measurements from the current canvas? This cannot be undone."
        confirmLabel="Clear Canvas"
        variant="danger"
        onConfirm={() => resetCircuit(emptyCircuit(ir.n_qubits))}
      />

      {/* QASM Import Dialog */}
      <Dialog open={importDialogOpen} onOpenChange={setImportDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Import OpenQASM 3.0</DialogTitle>
            <DialogDescription>
              Paste OpenQASM 3.0 code below to compile and load it directly onto the Composer grid.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3">
            <textarea
              rows={8}
              value={importQasmText}
              onChange={(e) => setImportQasmText(e.target.value)}
              placeholder={`OPENQASM 3.0;\ninclude "stdgates.inc";\nqubit[2] q;\nh q[0];\ncx q[0], q[1];`}
              className="w-full rounded-lg border border-line bg-subtle p-3 text-xs font-mono text-ink placeholder:text-ink-3 focus:outline-none focus:border-line-focus"
            />
            {importError && <ErrorNote className="text-xs">{importError}</ErrorNote>}
          </div>

          <DialogFooter>
            <Button variant="ghost" onClick={() => setImportDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={handleImportQasm}
              disabled={importBusy || !importQasmText.trim()}
              className="gap-1.5"
            >
              {importBusy ? <Spinner className="h-3.5 w-3.5" /> : <Upload className="h-3.5 w-3.5" />}
              Import to Canvas
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Saved Circuits Dialog */}
      <Dialog open={savedCircuitsDialogOpen} onOpenChange={setSavedCircuitsDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Saved Circuits</DialogTitle>
            <DialogDescription>
              Select a previously saved circuit from local storage to load into the Composer.
            </DialogDescription>
          </DialogHeader>

          <div className="max-h-64 overflow-y-auto divide-y divide-line-soft">
            {savedCircuits.length === 0 ? (
              <p className="py-8 text-center text-xs text-ink-3">No saved circuits found.</p>
            ) : (
              savedCircuits.map((item) => (
                <div key={item.id} className="flex items-center justify-between py-2.5 px-1">
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-ink truncate">{item.name}</p>
                    <p className="text-[11px] text-ink-3">
                      {item.ir.n_qubits} qubits · {item.date}
                    </p>
                  </div>
                  <div className="flex items-center gap-1.5 ml-3">
                    <Button size="sm" variant="primary" onClick={() => loadCircuit(item)} className="h-7 text-xs">
                      Load
                    </Button>
                    <button
                      onClick={() => deleteSavedCircuit(item.id)}
                      className="p-1 rounded-md text-ink-3 hover:text-danger transition-colors"
                      title="Delete"
                    >
                      <X className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>

          <DialogFooter>
            <Button variant="ghost" onClick={() => setSavedCircuitsDialogOpen(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Basic Noise Panel Component                                                */
/* -------------------------------------------------------------------------- */
function NoisePanelBasic({
  noise,
  onChange,
  enabled,
}: {
  noise: NoiseIn;
  onChange: (n: NoiseIn) => void;
  enabled: boolean;
}) {
  const [open, setOpen] = useState(false);
  if (!enabled) return null;

  const set = (patch: Partial<NoiseIn>) => onChange({ ...noise, ...patch });
  const clamped = Math.min(noise.t2_us, 2 * noise.t1_us);

  return (
    <Card className="p-4 border-line bg-raised">
      <button
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="flex w-full items-center justify-between text-xs font-semibold text-ink cursor-pointer"
      >
        <span>Realistic Noise Model (T₁ / T₂ / Readout)</span>
        <span className="text-ink-3">
          {open ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        </span>
      </button>

      {open && (
        <div className="mt-3.5 flex flex-col gap-3 pt-3 border-t border-line-soft">
          <label className="flex items-center gap-2 text-xs font-medium text-ink cursor-pointer">
            <input
              type="checkbox"
              checked={noise.enabled}
              onChange={(e) => set({ enabled: e.target.checked })}
              className="h-4 w-4 rounded accent-accent"
            />
            <span>Enable Thermal Decoherence & Readout Noise</span>
          </label>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
            <div>
              <Label className="text-[11px]">T₁ Relaxation (µs)</Label>
              <Input
                type="number"
                value={noise.t1_us}
                min={1}
                max={200}
                className="h-7 text-xs"
                onChange={(e) => set({ t1_us: Number(e.target.value) })}
              />
            </div>
            <div>
              <Label className="text-[11px]">T₂ Dephasing (µs)</Label>
              <Input
                type="number"
                value={noise.t2_us}
                min={1}
                max={200}
                className="h-7 text-xs"
                onChange={(e) => set({ t2_us: Number(e.target.value) })}
              />
            </div>
            <div>
              <Label className="text-[11px]">Readout Error (%)</Label>
              <Input
                type="number"
                value={Math.round(noise.readout_error * 1000) / 10}
                min={0}
                max={20}
                step={0.1}
                className="h-7 text-xs"
                onChange={(e) => set({ readout_error: Number(e.target.value) / 100 })}
              />
            </div>
          </div>

          {noise.t2_us > 2 * noise.t1_us && (
            <p className="text-[11px] text-warn">
              Note: T₂ cannot exceed 2×T₁; will be clamped to {clamped.toFixed(1)} µs.
            </p>
          )}
        </div>
      )}
    </Card>
  );
}
