import { useState, type FormEvent } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Atom, Sparkles, Shield, Cpu, ChevronRight, User } from "lucide-react";
import { login, register } from "../api/auth";
import { ApiError } from "../api/client";
import { useSession } from "../state/session";
import { Button, Card, ErrorNote, Input, Label, Tabs, TabsList, TabsTrigger } from "../components/ui";

type Mode = "login" | "register";

export function LoginPage({ mode: initialMode }: { mode: Mode }) {
  const [mode, setMode] = useState<Mode>(initialMode);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [demoBusy, setDemoBusy] = useState<string | null>(null);
  const user = useSession((s) => s.user);
  const setFromToken = useSession((s) => s.setFromToken);
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from ?? "/learn";


  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const token =
        mode === "login"
          ? await login({ email, password })
          : await register({ email, password, display_name: displayName });
      setFromToken(token);
      navigate(from, { replace: true });
    } catch (exc) {
      setError(
        exc instanceof ApiError ? exc.message : "Authentication failed. Check your credentials.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function loginAsDemo(demoEmail: string, targetPath: string) {
    setMode("login");
    setEmail(demoEmail);
    setPassword("password123");
    setError(null);
    setBusy(true);
    setDemoBusy(demoEmail);
    try {
      const token = await login({ email: demoEmail, password: "password123" });
      setFromToken(token);
      navigate(targetPath, { replace: true });
    } catch (exc) {
      setError(
        exc instanceof ApiError ? exc.message : "Instant demo authentication failed. Check credentials.",
      );
    } finally {
      setBusy(false);
      setDemoBusy(null);
    }
  }

  return (
    <div className="min-h-screen w-full flex flex-col lg:flex-row bg-[#06080d] text-ink relative overflow-hidden select-none">
      {/* Ambient Radial Spotlight Illumination */}
      <div className="absolute top-[-10%] left-[-10%] w-[50vw] h-[50vw] rounded-full bg-blue-600/10 blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[50vw] h-[50vw] rounded-full bg-indigo-600/10 blur-[120px] pointer-events-none" />
      <div className="absolute top-[30%] right-[30%] w-[35vw] h-[35vw] rounded-full bg-purple-600/8 blur-[100px] pointer-events-none" />

      {/* Left Column: Platform Identity & Live Holographic Quantum Processor */}
      <div className="relative flex-1 flex flex-col justify-between p-8 sm:p-12 lg:p-16 border-b lg:border-b-0 lg:border-r border-white/5 z-10">
        {/* Brand Header */}
        <div className="flex items-center gap-3.5">
          <div className="relative grid h-10 w-10 place-items-center rounded-2xl bg-gradient-to-tr from-accent/30 to-accent-2/30 text-accent border border-accent/40 shadow-[0_0_20px_-3px_rgba(59,130,246,0.6)]">
            <Atom className="h-5 w-5 animate-spin-slow" />
            <div className="absolute inset-0 rounded-2xl bg-accent/20 blur-xs" />
          </div>
          <div>
            <span className="text-xl font-bold tracking-tight text-white font-display">
              QuantumLearn
            </span>
            <span className="block text-[11px] font-semibold text-accent uppercase tracking-widest">
              Scientific Computing Platform
            </span>
          </div>
        </div>

        {/* Hero Narrative & Holographic Simulation */}
        <div className="my-auto py-8 max-w-xl">
          <div className="inline-flex items-center gap-2 rounded-full border border-accent/30 bg-accent/10 px-3.5 py-1 text-xs font-semibold text-accent mb-6 shadow-[0_0_15px_-3px_rgba(59,130,246,0.3)]">
            <Sparkles className="h-3.5 w-3.5" />
            <span>Interactive Statevector Simulation Engine</span>
          </div>

          <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-white font-display leading-[1.15]">
            Master Quantum Computing{" "}
            <span className="bg-gradient-to-r from-blue-400 via-indigo-300 to-purple-400 bg-clip-text text-transparent">
              from First Principles.
            </span>
          </h1>

          <p className="mt-4 text-sm sm:text-base text-ink-2 leading-relaxed max-w-lg">
            Construct entangled circuits, inspect 3D Bloch spheres, simulate thermal noise decoherence, and test algorithmic speedups on cloud-native backends.
          </p>

          {/* Futuristic Holographic Quantum Processor Simulation Box */}
          <div className="mt-8 rounded-2xl border border-white/10 bg-gradient-to-b from-white/[0.05] to-white/[0.01] backdrop-blur-xl p-5 sm:p-6 shadow-[0_8px_32px_-4px_rgba(0,0,0,0.6)] relative group">
            {/* Top simulation status bar */}
            <div className="flex items-center justify-between pb-3.5 border-b border-white/5 text-xs font-mono">
              <span className="text-accent flex items-center gap-2 font-medium">
                <Cpu className="h-3.5 w-3.5" />
                HILBERT SPACE: 2-QUBIT SYSTEM
              </span>
              <span className="flex items-center gap-2 text-ok text-[11px] font-semibold tracking-wider">
                <span className="h-2 w-2 rounded-full bg-ok shadow-[0_0_8px_2px_rgba(16,185,129,0.8)] animate-pulse" />
                DETERMINISTIC KERNEL
              </span>
            </div>

            {/* Live Interactive SVG Diagram */}
            <svg className="w-full h-36 mt-4 select-none" viewBox="0 0 420 130" fill="none">
              <defs>
                <linearGradient id="laserWire" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.8" />
                  <stop offset="50%" stopColor="#6366f1" stopOpacity="0.9" />
                  <stop offset="100%" stopColor="#06b6d4" stopOpacity="0.8" />
                </linearGradient>
                <filter id="neonGlowH" x="-20%" y="-20%" width="140%" height="140%">
                  <feDropShadow dx="0" dy="0" stdDeviation="4" floodColor="#f97316" floodOpacity="0.6" />
                </filter>
                <filter id="neonGlowCX" x="-20%" y="-20%" width="140%" height="140%">
                  <feDropShadow dx="0" dy="0" stdDeviation="4" floodColor="#10b981" floodOpacity="0.6" />
                </filter>
              </defs>

              {/* Base Waveguide Track Wires (Guaranteed 100% Solid Visibility) */}
              <line x1="42" y1="40" x2="330" y2="40" stroke="#1e293b" strokeWidth="3" strokeLinecap="round" />
              <line x1="42" y1="95" x2="330" y2="95" stroke="#1e293b" strokeWidth="3" strokeLinecap="round" />

              {/* Glowing Electric Quantum Core Wires */}
              <line x1="42" y1="40" x2="330" y2="40" stroke="#3b82f6" strokeWidth="1.75" strokeOpacity="0.8" strokeLinecap="round" />
              <line x1="42" y1="95" x2="330" y2="95" stroke="#3b82f6" strokeWidth="1.75" strokeOpacity="0.8" strokeLinecap="round" />

              {/* Animated Glowing Laser Wave Packets */}
              <line x1="42" y1="40" x2="330" y2="40" stroke="#93c5fd" strokeWidth="2" strokeDasharray="12 24" strokeLinecap="round" className="ql-wire-flow" />
              <line x1="42" y1="95" x2="330" y2="95" stroke="#93c5fd" strokeWidth="2" strokeDasharray="12 24" strokeLinecap="round" className="ql-wire-flow" />

              {/* Wire Input Terminals */}
              <circle cx="42" cy="40" r="3.5" fill="#3b82f6" />
              <circle cx="42" cy="40" r="1.5" fill="#ffffff" />
              <circle cx="42" cy="95" r="3.5" fill="#3b82f6" />
              <circle cx="42" cy="95" r="1.5" fill="#ffffff" />

              {/* Post-Measurement Classical Bit Double Wires */}
              <line x1="362" y1="38" x2="395" y2="38" stroke="#64748b" strokeWidth="1.5" strokeLinecap="round" />
              <line x1="362" y1="42" x2="395" y2="42" stroke="#64748b" strokeWidth="1.5" strokeLinecap="round" />
              <line x1="362" y1="93" x2="395" y2="93" stroke="#64748b" strokeWidth="1.5" strokeLinecap="round" />
              <line x1="362" y1="97" x2="395" y2="97" stroke="#64748b" strokeWidth="1.5" strokeLinecap="round" />

              {/* Wire State Labels */}
              <text x="12" y="44" fill="#94a3b8" fontSize="13" fontFamily="var(--font-mono)" fontWeight="600">|q₀⟩</text>
              <text x="12" y="99" fill="#94a3b8" fontSize="13" fontFamily="var(--font-mono)" fontWeight="600">|q₁⟩</text>

              {/* Hadamard Gate Node (Warm Amber Neon) */}
              <g className="ql-gate-node cursor-pointer" filter="url(#neonGlowH)">
                <rect x="95" y="24" width="32" height="32" rx="8" fill="#0f1422" stroke="#f97316" strokeWidth="2" />
                <text x="105" y="45" fill="#f97316" fontSize="14" fontWeight="bold" fontFamily="var(--font-mono)">H</text>
              </g>

              {/* Entanglement Bridge (CNOT) */}
              <g filter="url(#neonGlowCX)">
                <circle cx="190" cy="40" r="5" fill="#10b981" />
                <line x1="190" y1="40" x2="190" y2="95" stroke="#10b981" strokeWidth="2" strokeDasharray="3 3" />
                <circle cx="190" cy="95" r="12" fill="#0f1422" stroke="#10b981" strokeWidth="2" />
                <line x1="190" y1="87" x2="190" y2="103" stroke="#10b981" strokeWidth="2" />
                <line x1="182" y1="95" x2="198" y2="95" stroke="#10b981" strokeWidth="2" />
              </g>

              {/* Phase S Gate */}
              <g className="ql-gate-node" style={{ animationDelay: "1.2s" }}>
                <rect x="260" y="24" width="32" height="32" rx="8" fill="#0f1422" stroke="#06b6d4" strokeWidth="2" />
                <text x="271" y="45" fill="#06b6d4" fontSize="14" fontWeight="bold" fontFamily="var(--font-mono)">S</text>
              </g>

              {/* Measurements */}
              <rect x="330" y="24" width="32" height="32" rx="8" fill="#0f1422" stroke="#94a3b8" strokeWidth="1.5" />
              <path d="M338 48 A 8 8 0 0 1 354 48" stroke="#94a3b8" strokeWidth="1.5" fill="none" />
              <line x1="346" y1="48" x2="353" y2="33" stroke="#94a3b8" strokeWidth="1.5" />

              <rect x="330" y="79" width="32" height="32" rx="8" fill="#0f1422" stroke="#94a3b8" strokeWidth="1.5" />
              <path d="M338 103 A 8 8 0 0 1 354 103" stroke="#94a3b8" strokeWidth="1.5" fill="none" />
              <line x1="346" y1="103" x2="353" y2="88" stroke="#94a3b8" strokeWidth="1.5" />
            </svg>

            {/* Bottom State readout */}
            <div className="mt-3 flex items-center justify-between text-xs font-mono text-ink-2 bg-black/40 rounded-xl px-3.5 py-2 border border-white/5">
              <span>STATE: (|00⟩ + i|11⟩) / √2</span>
              <span className="text-accent font-semibold">ENTANGLEMENT: 100%</span>
            </div>
          </div>
        </div>

        {/* Bottom Feature Badges */}
        <div className="flex flex-wrap items-center gap-6 text-xs text-ink-3 font-medium">
          <span className="flex items-center gap-1.5">
            <Shield className="h-3.5 w-3.5 text-accent" /> Sandbox Isolation
          </span>
          <span className="flex items-center gap-1.5">
            <Cpu className="h-3.5 w-3.5 text-accent" /> Qiskit & Cirq Interop
          </span>
          <span className="flex items-center gap-1.5">
            <Sparkles className="h-3.5 w-3.5 text-accent" /> AI Curriculum Tutor
          </span>
        </div>
      </div>

      {/* Right Column: Floating Auth Glass Card */}
      <div className="flex-1 flex items-center justify-center p-6 sm:p-12 lg:p-16 z-10">
        <div className="w-full max-w-md">
          <Card className="p-8 sm:p-10 border border-white/10 bg-[#0c0f1a]/85 backdrop-blur-2xl shadow-[0_16px_48px_-8px_rgba(0,0,0,0.7)]">
            <div className="mb-6">
              <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white font-display">
                {mode === "login" ? "Welcome back" : "Create account"}
              </h2>
              <p className="mt-1.5 text-xs sm:text-sm text-ink-3 leading-relaxed">
                {mode === "login"
                  ? "Access your circuits, saved simulations, and curriculum progress."
                  : "Begin your journey with hands-on interactive quantum simulations."}
              </p>
            </div>

            {user && (
              <div className="mb-6 flex items-center justify-between rounded-xl bg-accent/10 border border-accent/30 p-3.5 text-xs text-accent">
                <div className="flex items-center gap-2.5 min-w-0 pr-2">
                  <User className="h-4 w-4 shrink-0" />
                  <span className="truncate">
                    Active: <strong className="text-white">{user.email}</strong>
                  </span>
                </div>
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  className="h-7 px-2.5 text-xs border-accent/40 text-accent hover:bg-accent/20 cursor-pointer shrink-0"
                  onClick={() => navigate(from, { replace: true })}
                >
                  Go to Workspace →
                </Button>
              </div>
            )}

            <Tabs

              value={mode}
              onValueChange={(val) => {
                setMode(val as Mode);
                setError(null);
              }}
              className="mb-6"
            >
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="login">Sign In</TabsTrigger>
                <TabsTrigger value="register">Register</TabsTrigger>
              </TabsList>
            </Tabs>

            <form onSubmit={onSubmit} className="flex flex-col gap-4">
              {mode === "register" && (
                <div>
                  <Label htmlFor="displayName">Your Full Name</Label>
                  <Input
                    id="displayName"
                    value={displayName}
                    onChange={(e) => setDisplayName(e.target.value)}
                    placeholder="e.g. Richard Feynman"
                    autoComplete="name"
                  />
                </div>
              )}

              <div>
                <Label htmlFor="email">Email Address</Label>
                <Input
                  id="email"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@example.com"
                  autoComplete="email"
                  autoFocus
                />
              </div>

              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <Label htmlFor="password" className="mb-0">Password</Label>
                </div>
                <Input
                  id="password"
                  type="password"
                  required
                  minLength={mode === "register" ? 6 : undefined}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  autoComplete={mode === "login" ? "current-password" : "new-password"}
                />
                {mode === "register" && (
                  <p className="mt-1.5 text-[11px] text-ink-3">Must be at least 6 characters long.</p>
                )}
              </div>

              <ErrorNote>{error}</ErrorNote>

              <Button
                type="submit"
                variant="primary"
                size="lg"
                disabled={busy}
                className="w-full mt-2 font-bold tracking-tight text-sm shadow-lg gap-2"
              >
                {busy ? "Authenticating…" : mode === "login" ? "Sign In to Workspace" : "Create My Account"}
                {!busy && <ChevronRight className="h-4 w-4" />}
              </Button>
            </form>

            {/* Quick Demo Instant Access Buttons */}
            <div className="mt-8 pt-6 border-t border-white/5">
              <div className="flex items-center justify-between mb-3">
                <span className="block text-[11px] font-bold uppercase tracking-wider text-ink-3 font-mono">
                  Instant Demo Access (1-Click):
                </span>
                <span className="text-[10px] text-accent font-mono font-medium">password123</span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => loginAsDemo("student@quantum.local", "/learn")}
                  className="p-3 rounded-xl border border-white/10 bg-white/[0.03] hover:bg-white/[0.08] hover:border-accent/40 text-ink-2 hover:text-white transition-all text-left group cursor-pointer disabled:opacity-50"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="block font-semibold text-white group-hover:text-accent transition-colors">
                      Student Demo
                    </span>
                    {demoBusy === "student@quantum.local" ? (
                      <span className="h-3.5 w-3.5 border-2 border-accent border-t-transparent rounded-full animate-spin" />
                    ) : (
                      <ChevronRight className="h-3.5 w-3.5 opacity-40 group-hover:opacity-100 group-hover:translate-x-0.5 transition-all text-accent" />
                    )}
                  </div>
                  <span className="text-[10px] text-ink-3 block">Learner Workspace (/learn)</span>
                </button>

                <button
                  type="button"
                  disabled={busy}
                  onClick={() => loginAsDemo("instructor@quantum.local", "/dashboard")}
                  className="p-3 rounded-xl border border-white/10 bg-white/[0.03] hover:bg-white/[0.08] hover:border-accent/40 text-ink-2 hover:text-white transition-all text-left group cursor-pointer disabled:opacity-50"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="block font-semibold text-white group-hover:text-accent transition-colors">
                      Instructor Demo
                    </span>
                    {demoBusy === "instructor@quantum.local" ? (
                      <span className="h-3.5 w-3.5 border-2 border-accent border-t-transparent rounded-full animate-spin" />
                    ) : (
                      <ChevronRight className="h-3.5 w-3.5 opacity-40 group-hover:opacity-100 group-hover:translate-x-0.5 transition-all text-accent" />
                    )}
                  </div>
                  <span className="text-[10px] text-ink-3 block">Cohort Analytics (/dashboard)</span>
                </button>
              </div>
            </div>

            <p className="mt-6 text-center text-xs text-ink-3">
              {mode === "login" ? (
                <>
                  New to QuantumLearn?{" "}
                  <button
                    type="button"
                    onClick={() => {
                      setMode("register");
                      setError(null);
                    }}
                    className="text-accent hover:underline font-semibold"
                  >
                    Create account
                  </button>
                </>
              ) : (
                <>
                  Already registered?{" "}
                  <button
                    type="button"
                    onClick={() => {
                      setMode("login");
                      setError(null);
                    }}
                    className="text-accent hover:underline font-semibold"
                  >
                    Sign in here
                  </button>
                </>
              )}
            </p>
          </Card>
        </div>
      </div>
    </div>
  );
}
