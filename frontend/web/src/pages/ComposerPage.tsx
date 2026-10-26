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
  ArrowRight,
  X,
  Code2,
  BarChart3,
  Globe,
  Copy,
  ExternalLink,
  AlertTriangle,
  FileCode,
  ShieldCheck,
  FileUp,
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
import {
  IMPORT_FORMATS,
  MAX_IMPORT_BYTES,
  MAX_IMPORT_CHARS,
  detectFormat,
  validateAndSanitizeCircuitIR,
} from "../lib/circuitImport";
import { Histogram } from "../components/results/ResultsViews";
import { QSphere } from "../components/results/GeometryViews";
import {
  cn,
  Badge,
  Button,
  ConfirmModal,
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  ErrorNote,
  Input,
  Select,
  SelectItem,
  Spinner,
  Tooltip,
  toast,
} from "../components/ui";
import { ResultsPanel } from "../components/results/ResultsPanel";
import { NoiseLabView } from "../components/noise/NoiseLabView";
import { SmartComposerPanel } from "../components/smart_composer/SmartComposerPanel";
import type { NoiseSimulationResult } from "../api/noiseLab";

const SHOT_CHOICES = [128, 256, 512, 1024, 2048, 4096, 8192];

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
  const circuitName = useCircuit((state) => state.circuitName ?? "Quantum Circuit");
  const challengeContext = useCircuit((state) => state.challengeContext);
  const setIr = useCircuit((state) => state.setIr);
  const resetCircuit = useCircuit((state) => state.reset);
  const setQubits = useCircuit((state) => state.setQubits);
  const setCircuitName = useCircuit((state) => state.setCircuitName);
  const setChallengeContext = useCircuit((state) => state.setChallengeContext);
  const userEditedNameRef = useRef(false);

  const [shots, setShots] = useState(1024);
  const [backendId, setBackendId] = useState<string>("qiskit_aer");
  const [noise, setNoise] = useState<NoiseIn>(DEFAULT_NOISE);
  const [noiseSimResult, setNoiseSimResult] = useState<NoiseSimulationResult | null>(null);
  const [jobId, setJobId] = useState<number | null>(null);
  const [runSnapshot, setRunSnapshot] = useState<string | null>(null);
  const [ranQubits, setRanQubits] = useState<number | null>(null);
  const [runError, setRunError] = useState<string | null>(null);

  // IBM Quantum Platform Layout States
  const [showQasm, setShowQasm] = useState(false);
  const [showSmartComposer, setShowSmartComposer] = useState(false);
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
  const [importFormat, setImportFormat] = useState<string>("auto");
  const [importText, setImportText] = useState("");
  const [importFileName, setImportFileName] = useState<string | null>(null);
  const [importFileSize, setImportFileSize] = useState<number | null>(null);
  const [importBusy, setImportBusy] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

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

  // File Upload Handler with size & format guards
  function handleFileUpload(file: File) {
    if (!file) return;
    if (file.size > MAX_IMPORT_BYTES) {
      setImportError(
        `File size exceeds 100 KB limit (${(file.size / 1024).toFixed(1)} KB). Please upload a smaller circuit file.`
      );
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      const text = (e.target?.result as string) || "";
      if (text.length > MAX_IMPORT_CHARS) {
        setImportError(
          `File exceeds maximum character limit of ${MAX_IMPORT_CHARS.toLocaleString()} characters.`
        );
        return;
      }
      setImportText(text);
      setImportFileName(file.name);
      setImportFileSize(file.size);
      setImportError(null);

      // Auto-detect format from file extension and content
      const detected = detectFormat(text, file.name);
      setImportFormat(detected);
    };
    reader.onerror = () => {
      setImportError("Failed to read file from disk.");
    };
    reader.readAsText(file);
  }

  // Multi-Format Circuit Import Handler
  async function handleImportCircuit() {
    const trimmed = importText.trim();
    if (!trimmed) {
      setImportError("Please paste circuit code or upload a file first.");
      return;
    }

    // Determine target format
    let effectiveFormat = importFormat;
    if (effectiveFormat === "auto") {
      effectiveFormat = detectFormat(trimmed, importFileName ?? undefined);
    }

    if (effectiveFormat === "cudaq_cpp") {
      setImportError(
        "CUDA-Q C++ (.cpp) requires compilation via nvq++ and cannot be directly parsed in the browser. Please use CUDA-Q Python or OpenQASM 3.0 instead."
      );
      return;
    }

    setImportBusy(true);
    setImportError(null);

    try {
      if (effectiveFormat === "json") {
        // Direct, safe AST validation and parsing without subprocess execution
        const result = validateAndSanitizeCircuitIR(trimmed);
        if (!result.ok) {
          setImportError(result.error);
          return;
        }
        setIr(result.ir);
        if (result.ir.name && result.ir.name !== "circuit" && result.ir.name !== "imported_circuit") {
          setCircuitName(result.ir.name);
        }
        setImportDialogOpen(false);
        setImportText("");
        setImportFileName(null);
        setImportFileSize(null);
        toast.success("Circuit imported safely from Circuit IR (JSON)");
      } else {
        // QASM3, Qiskit, Cirq, PennyLane, qBraid, CUDA-Q via backend codelab service (sandboxed)
        const backendFramework = effectiveFormat === "cudaq" ? "cudaq" : effectiveFormat;
        const res = await buildCircuit(trimmed, backendFramework);
        if (res.circuit_ir) {
          setIr(res.circuit_ir);
          if (res.circuit_ir.name && res.circuit_ir.name !== "circuit") {
            setCircuitName(res.circuit_ir.name);
          }
          setImportDialogOpen(false);
          setImportText("");
          setImportFileName(null);
          setImportFileSize(null);
          const fmtObj = IMPORT_FORMATS.find((f) => f.id === effectiveFormat);
          toast.success(`Circuit imported successfully from ${fmtObj?.name || effectiveFormat}`);
        } else {
          setImportError("No valid circuit was returned by compiler.");
        }
      }
    } catch (err: any) {
      setImportError(err.message || "Failed to compile circuit. Please verify syntax.");
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
    userEditedNameRef.current = true;
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
            onChange={(e) => {
              userEditedNameRef.current = true;
              setCircuitName(e.target.value);
            }}
            className="h-8 w-44 font-semibold text-xs border-line bg-bg focus:w-56 transition-all"
            placeholder="Circuit Name"
            aria-label="Circuit Name"
          />

          {/* Qubit Count Stepper */}
          <div className="flex items-center rounded-lg border border-line bg-bg p-0.5">
            <button
              onClick={() => {
                const n = ir.n_qubits - 1;
                setQubits(n);
                if (!userEditedNameRef.current && (circuitName === "Bell State" || circuitName.includes("GHZ") || circuitName.includes("Circuit"))) {
                  setCircuitName(`${n}-Qubit Circuit`);
                }
              }}
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
              onClick={() => {
                const n = ir.n_qubits + 1;
                setQubits(n);
                if (!userEditedNameRef.current && (circuitName === "Bell State" || circuitName.includes("GHZ") || circuitName.includes("Circuit"))) {
                  setCircuitName(`${n}-Qubit Circuit`);
                }
              }}
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
            <Button
              size="sm"
              variant="ghost"
              onClick={() => {
                userEditedNameRef.current = false;
                resetCircuit(bell(), "Bell State");
              }}
              title="Load Bell state"
            >
              <Sparkles className="h-3.5 w-3.5 text-accent" /> Bell
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => {
                userEditedNameRef.current = false;
                resetCircuit(ghz(3), "GHZ State");
              }}
              title="Load 3-qubit GHZ state"
            >
              GHZ
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => {
                userEditedNameRef.current = false;
                resetCircuit(wState(), "W State");
              }}
              title="Load 3-qubit W state"
            >
              W State
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => {
                userEditedNameRef.current = false;
                resetCircuit(qft3(), "3-Qubit QFT");
              }}
              title="Load 3-qubit QFT"
            >
              QFT
            </Button>
          </div>
        </div>

        {/* Right Toolbar Actions */}
        <div className="flex items-center gap-2">
          {/* Smart Composer AI Studio Toggle */}
          <Button
            size="sm"
            variant={showSmartComposer ? "secondary" : "ghost"}
            onClick={() => setShowSmartComposer(!showSmartComposer)}
            className="gap-1.5 text-xs font-medium text-purple-400 border border-purple-500/30 hover:bg-purple-500/10"
            title="Smart Composer AI Studio: generate and simplify quantum circuits"
          >
            <Sparkles className="h-3.5 w-3.5 text-purple-400" />
            <span>Smart Composer</span>
          </Button>

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
          {/* Smart Composer AI Studio Panel */}
          {showSmartComposer && (
            <div className="animate-in fade-in slide-in-from-top-3 duration-200">
              <SmartComposerPanel
                currentIr={ir}
                onAdoptCircuit={(newIr) => {
                  setIr(newIr);
                  toast.success("Adopted circuit into Composer!");
                }}
                onClose={() => setShowSmartComposer(false)}
              />
            </div>
          )}

          {/* Top: Circuit Canvas & OpenQASM 3 Panel */}
          <div className="flex flex-col lg:flex-row gap-4">
            <div className="flex-1 min-w-0">
              <div className="composer-host dark rounded-xl border border-line bg-raised p-4 shadow-sm">
                <ComposerInner
                  value={ir}
                  nQubits={ir.n_qubits}
                  onChange={(newIr) => {
                    setIr(newIr);
                    if (!userEditedNameRef.current) {
                      if (circuitName === "Bell State" && (newIr.n_qubits !== 2 || newIr.ops.length !== 4)) {
                        setCircuitName(`${newIr.n_qubits}-Qubit Circuit`);
                      }
                    }
                  }}
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
                    Noise Lab
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

                {/* Noise Model Toggle */}
                {(backendId === "qiskit_aer" || backendId === "cudaq" || backendId === "auto") && (
                  <button
                    type="button"
                    onClick={() => setNoise((n) => ({ ...n, enabled: !n.enabled }))}
                    className={`h-8 px-2.5 rounded-lg border text-xs font-medium flex items-center gap-1.5 transition-all ${
                      noise.enabled
                        ? "bg-amber-500/15 border-amber-500/40 text-amber-300 shadow-xs"
                        : "bg-raised border-line text-ink-3 hover:text-ink hover:border-line-soft"
                    }`}
                    title={
                      noise.enabled
                        ? `Noise model active: T1=${noise.t1_us}µs, T2=${noise.t2_us}µs, Readout=${(noise.readout_error * 100).toFixed(0)}%`
                        : "Enable T1/T2 decoherence & readout noise for simulation"
                    }
                  >
                    <span className={`h-2 w-2 rounded-full ${noise.enabled ? "bg-amber-400 animate-pulse" : "bg-ink-4"}`} />
                    Noise: <span className="font-semibold">{noise.enabled ? "ON" : "OFF"}</span>
                  </button>
                )}

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
                <div className="space-y-4 py-2">
                  <NoiseLabView
                    circuitIr={ir}
                    backendId={backendId}
                    onSimulationDone={(res) => setNoiseSimResult(res)}
                  />
                </div>
              )}

              {bottomView === "advanced" && (
                <div className="space-y-4">
                  {jobId === null && !noiseSimResult ? (
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
                      noiseSimResult={noiseSimResult}
                      onRunNoise={(n) => {
                        setNoise(n);
                        run.mutate();
                      }}
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
        onConfirm={() => {
          userEditedNameRef.current = false;
          resetCircuit(emptyCircuit(ir.n_qubits), "Untitled Circuit");
        }}
      />

      {/* Multi-Format Circuit Import Dialog */}
      <Dialog
        open={importDialogOpen}
        onOpenChange={(open) => {
          setImportDialogOpen(open);
          if (!open) setImportError(null);
        }}
      >
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent/15 text-accent border border-accent/30">
                <FileCode className="h-4 w-4" />
              </div>
              <div>
                <DialogTitle>Import Quantum Circuit</DialogTitle>
                <DialogDescription>
                  Load circuits from OpenQASM 3.0, Circuit IR JSON, Qiskit, Cirq, PennyLane, qBraid, or CUDA-Q.
                </DialogDescription>
              </div>
            </div>
          </DialogHeader>

          <div className="space-y-4">
            {/* Format Selector Pills */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-ink-2">Circuit Format</label>
              <div className="flex flex-wrap gap-1.5">
                {IMPORT_FORMATS.map((fmt) => {
                  const isSelected = importFormat === fmt.id;
                  return (
                    <button
                      key={fmt.id}
                      type="button"
                      onClick={() => {
                        setImportFormat(fmt.id);
                        setImportError(null);
                      }}
                      className={cn(
                        "flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-xs font-medium transition-all cursor-pointer",
                        isSelected
                          ? "border-accent bg-accent/15 text-accent font-semibold shadow-xs"
                          : "border-line bg-subtle/60 text-ink-2 hover:bg-hover hover:text-ink"
                      )}
                    >
                      <Badge
                        tone={isSelected ? "accent" : "neutral"}
                        className="px-1 py-0 text-[10px] font-mono"
                      >
                        {fmt.badge}
                      </Badge>
                      <span>{fmt.name}</span>
                    </button>
                  );
                })}
              </div>
              <p className="text-[11px] text-ink-3">
                {IMPORT_FORMATS.find((f) => f.id === importFormat)?.description}
              </p>
            </div>

            {/* Drag & Drop File Upload Area */}
            <div
              onDragOver={(e) => {
                e.preventDefault();
                e.stopPropagation();
              }}
              onDrop={(e) => {
                e.preventDefault();
                e.stopPropagation();
                const file = e.dataTransfer.files?.[0];
                if (file) handleFileUpload(file);
              }}
              onClick={() => fileInputRef.current?.click()}
              className="group relative flex flex-col items-center justify-center rounded-xl border border-dashed border-line hover:border-accent/60 bg-subtle/30 hover:bg-accent/5 p-4 transition-all cursor-pointer text-center"
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".qasm,.json,.py,.cpp,.cc,.cxx,.txt"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) handleFileUpload(file);
                }}
              />
              <FileUp className="h-6 w-6 text-ink-3 group-hover:text-accent transition-colors mb-1.5" />
              <div className="text-xs font-medium text-ink">
                Drop circuit file here, or <span className="text-accent underline">browse</span>
              </div>
              <p className="text-[10px] text-ink-3 mt-0.5">
                Supports .qasm, .json, .py (Qiskit/Cirq/PennyLane/qBraid/CUDA-Q), and .cpp (up to 100 KB)
              </p>
            </div>

            {/* Selected File Badge (if loaded from file) */}
            {importFileName && (
              <div className="flex items-center justify-between rounded-lg border border-accent/30 bg-accent/10 px-3 py-1.5 text-xs text-accent">
                <div className="flex items-center gap-2 truncate">
                  <FileCode className="h-4 w-4 shrink-0" />
                  <span className="font-mono font-medium truncate">{importFileName}</span>
                  {importFileSize !== null && (
                    <span className="text-[11px] opacity-75">
                      ({(importFileSize / 1024).toFixed(1)} KB)
                    </span>
                  )}
                </div>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    setImportFileName(null);
                    setImportFileSize(null);
                    setImportText("");
                    if (fileInputRef.current) fileInputRef.current.value = "";
                  }}
                  className="rounded p-1 hover:bg-accent/20 text-accent transition-colors"
                  title="Remove uploaded file"
                  aria-label="Remove uploaded file"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </div>
            )}

            {/* Circuit Code Textarea */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <label className="font-semibold text-ink-2">Circuit Code / Specification</label>
                <span className="text-[11px] font-mono text-ink-3">
                  {importText.length.toLocaleString()} / {MAX_IMPORT_CHARS.toLocaleString()} chars
                </span>
              </div>
              <textarea
                rows={9}
                value={importText}
                maxLength={MAX_IMPORT_CHARS}
                onChange={(e) => {
                  setImportText(e.target.value);
                  if (importError) setImportError(null);
                  if (importFormat === "auto" && e.target.value.length > 10) {
                    const detected = detectFormat(e.target.value, importFileName ?? undefined);
                    if (detected !== "auto") {
                      // Optionally reflect detection
                    }
                  }
                }}
                placeholder={
                  IMPORT_FORMATS.find((f) => f.id === importFormat)?.placeholder ||
                  IMPORT_FORMATS[0].placeholder
                }
                className="w-full rounded-lg border border-line bg-subtle p-3 text-xs font-mono text-ink placeholder:text-ink-3/60 focus:outline-none focus:border-line-focus shadow-inner"
              />
            </div>

            {/* Error Message */}
            {importError && (
              <ErrorNote className="text-xs flex items-start gap-1.5">
                <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
                <span>{importError}</span>
              </ErrorNote>
            )}

            {/* Data Safety & Integrity Notice */}
            <div className="flex items-start gap-2 rounded-lg border border-line-soft bg-subtle/50 p-2.5 text-[11px] text-ink-3">
              <ShieldCheck className="h-4 w-4 text-emerald-500 shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold text-ink-2">Tamper-Proof & Safe Parsing: </span>
                Circuit IR (JSON) and OpenQASM 3.0 are parsed via pure AST validation with strict boundary and index guards. Python frameworks are transpiled inside a sealed, isolated execution sandbox with no network or filesystem tampering.
              </div>
            </div>
          </div>

          <DialogFooter className="mt-4 flex items-center justify-between sm:justify-between w-full">
            <div>
              {importText && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setImportText("");
                    setImportFileName(null);
                    setImportFileSize(null);
                    setImportError(null);
                    if (fileInputRef.current) fileInputRef.current.value = "";
                  }}
                  className="text-xs text-ink-3 hover:text-ink"
                >
                  Clear Input
                </Button>
              )}
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                onClick={() => {
                  setImportDialogOpen(false);
                  setImportError(null);
                }}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                onClick={handleImportCircuit}
                disabled={importBusy || !importText.trim()}
                className="gap-1.5"
              >
                {importBusy ? <Spinner className="h-3.5 w-3.5" /> : <Upload className="h-3.5 w-3.5" />}
                Import to Canvas
              </Button>
            </div>
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
