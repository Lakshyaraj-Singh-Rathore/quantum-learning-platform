import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Atom } from "lucide-react";
import { login, register } from "../api/auth";
import { ApiError } from "../api/client";
import { useSession } from "../state/session";
import { Button, Card, ErrorNote, Input, Label, cn } from "../components/ui";

type Mode = "login" | "register";

/** The frozen Streamlit app serves on its own port, so the link is host-
 *  relative rather than hardcoded to localhost (it must work for a learner on
 *  a LAN box too). Guarded because this component is also rendered by the
 *  headless smoke harness, where there is no window. */
function streamlitHost(): string {
  return typeof window === "undefined" ? "localhost" : window.location.hostname;
}

export function LoginPage({ mode: initialMode }: { mode: Mode }) {
  const [mode, setMode] = useState<Mode>(initialMode);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
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
        exc instanceof ApiError ? exc.message : "Something went wrong. Try again.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid h-full place-items-center px-4">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex items-center justify-center gap-2.5">
          <span className="grid h-8 w-8 place-items-center rounded-lg bg-accent/15 text-accent">
            <Atom className="h-5 w-5" aria-hidden />
          </span>
          <span className="text-lg font-semibold tracking-tight">QuantumLearn</span>
        </div>

        <Card className="p-6">
          <div
            role="tablist"
            aria-label="Authentication mode"
            className="mb-5 grid grid-cols-2 gap-1 rounded-lg bg-hover p-1"
          >
            {(["login", "register"] as const).map((m) => (
              <button
                key={m}
                role="tab"
                aria-selected={mode === m}
                onClick={() => {
                  setMode(m);
                  setError(null);
                }}
                className={cn(
                  "h-8 rounded-md text-sm font-medium text-ink-3 transition-colors",
                  mode === m && "bg-raised text-ink shadow-none",
                )}
              >
                {m === "login" ? "Sign in" : "Create account"}
              </button>
            ))}
          </div>

          <form onSubmit={onSubmit} className="flex flex-col gap-4">
            {mode === "register" && (
              <div>
                <Label htmlFor="displayName">Display name (optional)</Label>
                <Input
                  id="displayName"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  autoComplete="nickname"
                />
              </div>
            )}
            <div>
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
                autoFocus
              />
            </div>
            <div>
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                required
                minLength={mode === "register" ? 6 : undefined}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete={mode === "login" ? "current-password" : "new-password"}
              />
              {mode === "register" && (
                <p className="mt-1.5 text-xs text-ink-3">At least 6 characters.</p>
              )}
            </div>
            <ErrorNote>{error}</ErrorNote>
            <Button type="submit" variant="primary" disabled={busy}>
              {busy ? "Working…" : mode === "login" ? "Sign in" : "Create account"}
            </Button>
          </form>

          <p className="mt-4 text-center text-[13px] text-ink-3">
            {mode === "login" ? (
              <>
                No account?{" "}
                <Link to="/register" className="text-accent hover:underline">
                  Create one
                </Link>
              </>
            ) : (
              <>
                Already registered?{" "}
                <Link to="/login" className="text-accent hover:underline">
                  Sign in
                </Link>
              </>
            )}
          </p>
        </Card>

        <p className="mt-4 text-center text-xs leading-relaxed text-ink-3">
          The classic Streamlit UI stays available at{" "}
          <a
            href={`http://${streamlitHost()}:8501`}
            className="text-ink-2 underline decoration-line"
          >
            :8501
          </a>{" "}
          until parity cutover.
        </p>
      </div>
    </div>
  );
}
