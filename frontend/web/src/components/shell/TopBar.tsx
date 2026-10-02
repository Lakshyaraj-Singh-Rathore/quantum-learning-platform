import { useLocation } from "react-router-dom";
import { LogOut, Moon, Search, Sun } from "lucide-react";
import { useSession } from "../../state/session";
import { useTheme } from "../../state/theme";
import { BackendBadge } from "./BackendBadge";
import { NAV_ITEMS } from "./nav";
import { Button } from "../ui";

export function TopBar({ onOpenPalette }: { onOpenPalette?: () => void }) {
  const location = useLocation();
  const item = NAV_ITEMS.find((n) => location.pathname.startsWith(n.to));
  const user = useSession((s) => s.user);
  const clear = useSession((s) => s.clear);
  const { theme, toggle } = useTheme();

  return (
    <header className="flex h-14 shrink-0 items-center gap-3 border-b border-line-soft bg-bg px-5">
      <h1 className="text-[15px] font-semibold tracking-tight">
        {item?.label ?? "QuantumLearn"}
      </h1>
      <div className="ml-auto flex items-center gap-3">
        <BackendBadge />
        <Button
          variant="ghost"
          size="sm"
          onClick={onOpenPalette}
          aria-label="Search commands"
          title="Search commands (Ctrl-K)"
          className="gap-2 text-ink-3"
        >
          <Search className="h-4 w-4" />
          <kbd className="hidden rounded border border-line px-1 text-[10px] md:inline">
            Ctrl-K
          </kbd>
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={toggle}
          aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
          title={theme === "dark" ? "Light mode" : "Dark mode"}
        >
          {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </Button>
        {user && (
          <span className="hidden items-center gap-2 rounded-full border border-line bg-raised py-1 pl-3 pr-1 text-xs text-ink-2 sm:inline-flex">
            <span className="max-w-[16ch] truncate">{user.display_name || user.email}</span>
            {user.role !== "student" && (
              <span className="rounded-full bg-accent/15 px-2 py-0.5 font-medium text-accent">
                {user.role}
              </span>
            )}
            <button
              onClick={clear}
              title="Sign out"
              aria-label="Sign out"
              className="grid h-6 w-6 place-items-center rounded-full text-ink-3 hover:bg-hover hover:text-ink"
            >
              <LogOut className="h-3.5 w-3.5" />
            </button>
          </span>
        )}
      </div>
    </header>
  );
}
