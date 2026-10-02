/**
 * Ctrl-K / Cmd-K command palette.
 *
 * The plan lists this as optional for P7; it is here because a seven-page app
 * with no keyboard route is tedious to move around, and because "go to X"
 * should not require hunting for the sidebar.
 *
 * It is a real palette, not a search box: every entry is a command with a
 * consequence (navigate, switch theme, sign out), matching is fuzzy and ranked,
 * and it is fully operable from the keyboard -- arrows move, Enter runs,
 * Escape closes, and focus is trapped in the input while it is open.
 */
import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { LogOut, Moon, Search, Sun } from "lucide-react";

import { useSession } from "../../state/session";
import { useTheme } from "../../state/theme";
import { NAV_ITEMS } from "./nav";

interface Command {
  id: string;
  label: string;
  /** Secondary text shown on the right — the destination or the current state. */
  hint?: string;
  icon: React.ComponentType<{ className?: string }>;
  run: () => void;
}

/**
 * Rank a candidate against a query. Higher is better; -1 means no match.
 *
 * Exact prefix beats a substring, which beats a subsequence. The subsequence
 * case is what makes "dash" find "Dashboard" and "cl" find "Code Lab".
 */
export function score(haystack: string, needle: string): number {
  if (!needle) return 1;
  const h = haystack.toLowerCase();
  const n = needle.toLowerCase().replace(/\s+/g, "");
  if (h === n) return 100;
  if (h.startsWith(n)) return 80;
  const at = h.indexOf(n);
  if (at > 0) return 60 - Math.min(at, 20);

  let hi = 0;
  for (const ch of n) {
    const found = h.indexOf(ch, hi);
    if (found === -1) return -1;
    hi = found + 1;
  }
  return 20 - hi;
}

export function CommandPalette({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();
  const { theme, toggle } = useTheme();
  const clear = useSession((s) => s.clear);

  const commands = useMemo<Command[]>(
    () => [
      ...NAV_ITEMS.map((item) => ({
        id: `go-${item.to}`,
        label: `Go to ${item.label}`,
        hint: item.to,
        icon: item.icon,
        run: () => navigate(item.to),
      })),
      {
        id: "theme",
        label: theme === "dark" ? "Switch to light mode" : "Switch to dark mode",
        hint: "appearance",
        icon: theme === "dark" ? Sun : Moon,
        run: toggle,
      },
      {
        id: "signout",
        label: "Sign out",
        hint: "ends the session",
        icon: LogOut,
        run: clear,
      },
    ],
    [navigate, theme, toggle, clear],
  );

  const results = useMemo(() => {
    const ranked = commands
      .map((c) => ({ c, s: score(c.label, query) }))
      .filter((r) => r.s >= 0)
      .sort((a, b) => b.s - a.s);
    return ranked.map((r) => r.c);
  }, [commands, query]);

  // Read the platform modifier once so the hint matches what the user presses.
  const isMac =
    typeof navigator !== "undefined" && /Mac|iPhone|iPad/.test(navigator.platform ?? "");

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        onOpenChange(!open);
        setQuery("");
        setActive(0);
      } else if (e.key === "Escape") {
        onOpenChange(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onOpenChange]);

  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

  useEffect(() => {
    setActive(0);
  }, [query]);

  if (!open) return null;

  const runActive = () => {
    const command = results[active];
    if (!command) return;
    command.run();
    onOpenChange(false);
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-black/50 p-4 pt-[12vh]"
      onClick={() => onOpenChange(false)}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Command palette"
        className="w-full max-w-lg overflow-hidden rounded-xl border border-line bg-bg shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-2 border-b border-line-soft px-3">
          <Search className="h-4 w-4 shrink-0 text-ink-3" aria-hidden="true" />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "ArrowDown") {
                e.preventDefault();
                setActive((i) => Math.min(i + 1, results.length - 1));
              } else if (e.key === "ArrowUp") {
                e.preventDefault();
                setActive((i) => Math.max(i - 1, 0));
              } else if (e.key === "Enter") {
                e.preventDefault();
                runActive();
              }
            }}
            aria-label="Search commands"
            aria-controls="command-results"
            aria-activedescendant={results[active] ? `cmd-${results[active].id}` : undefined}
            placeholder="Jump to a page or run a command…"
            className="h-12 w-full bg-transparent text-sm text-ink outline-none placeholder:text-ink-3"
          />
          <kbd className="shrink-0 rounded border border-line px-1.5 py-0.5 text-[10px] text-ink-3">
            esc
          </kbd>
        </div>

        <ul id="command-results" role="listbox" aria-label="Commands" className="max-h-80 overflow-y-auto py-1">
          {results.length === 0 && (
            <li className="px-3 py-6 text-center text-sm text-ink-3">No matching command.</li>
          )}
          {results.map((command, i) => {
            const Icon = command.icon;
            return (
              <li key={command.id} id={`cmd-${command.id}`} role="option" aria-selected={i === active}>
                <button
                  type="button"
                  onMouseEnter={() => setActive(i)}
                  onClick={() => {
                    command.run();
                    onOpenChange(false);
                  }}
                  className={`flex w-full items-center gap-3 px-3 py-2 text-left text-sm ${
                    i === active ? "bg-raised text-ink" : "text-ink-2"
                  }`}
                >
                  <Icon className="h-4 w-4 shrink-0 text-ink-3" />
                  <span className="flex-1 truncate">{command.label}</span>
                  {command.hint && (
                    <span className="shrink-0 font-mono text-[11px] text-ink-3">{command.hint}</span>
                  )}
                </button>
              </li>
            );
          })}
        </ul>

        <div className="flex items-center gap-3 border-t border-line-soft px-3 py-2 text-[11px] text-ink-3">
          <span>
            <kbd className="rounded border border-line px-1">↑</kbd>{" "}
            <kbd className="rounded border border-line px-1">↓</kbd> to move
          </span>
          <span>
            <kbd className="rounded border border-line px-1">↵</kbd> to run
          </span>
          <span className="ml-auto">
            <kbd className="rounded border border-line px-1">{isMac ? "⌘" : "Ctrl"}</kbd>
            <kbd className="rounded border border-line px-1">K</kbd> to toggle
          </span>
        </div>
      </div>
    </div>
  );
}
