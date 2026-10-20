import { useState } from "react";
import { useLocation } from "react-router-dom";
import { LogOut, Menu, Search, ChevronRight, User } from "lucide-react";
import { useSession } from "../../state/session";
import { BackendBadge } from "./BackendBadge";
import { NAV_ITEMS, NAV_SECTIONS } from "./nav";
import { Button, ConfirmModal, Tooltip } from "../ui";

export function TopBar({
  onOpenPalette,
  onOpenMobileNav,
}: {
  onOpenPalette?: () => void;
  onOpenMobileNav?: () => void;
}) {
  const location = useLocation();
  const currentItem = NAV_ITEMS.find((n) => location.pathname.startsWith(n.to));
  const currentSection = NAV_SECTIONS.find((s) => s.id === currentItem?.section);
  const user = useSession((s) => s.user);
  const clear = useSession((s) => s.clear);

  const [signOutOpen, setSignOutOpen] = useState(false);

  return (
    <header className="flex h-15 shrink-0 items-center justify-between border-b border-white/5 bg-bg/80 backdrop-blur-xl px-5 lg:px-8 z-20">
      {/* Left: Mobile Menu + Breadcrumbs */}
      <div className="flex items-center gap-3.5 min-w-0">
        <button
          onClick={onOpenMobileNav}
          className="lg:hidden p-2 rounded-xl text-ink-2 hover:text-white hover:bg-white/5 transition-colors cursor-pointer"
          aria-label="Open navigation menu"
        >
          <Menu className="h-5 w-5" />
        </button>

        <nav aria-label="Breadcrumb" className="flex items-center gap-2 text-xs sm:text-sm min-w-0">
          {currentSection && (
            <>
              <span className="text-ink-3/90 truncate font-medium hidden sm:inline">{currentSection.label}</span>
              <ChevronRight className="h-3.5 w-3.5 text-ink-3/60 shrink-0 hidden sm:inline" />
            </>
          )}
          <h1 className="font-bold text-white tracking-tight truncate text-sm sm:text-base font-display">
            {currentItem?.label ?? "Overview"}
          </h1>
        </nav>
      </div>

      {/* Right: Actions & User Chip */}
      <div className="flex items-center gap-3">
        <BackendBadge />

        <Button
          variant="ghost"
          size="sm"
          onClick={onOpenPalette}
          aria-label="Search commands"
          title="Search commands (Ctrl-K)"
          className="gap-2 text-ink-3 hover:text-white border border-white/5 bg-subtle/40 rounded-xl px-3"
        >
          <Search className="h-3.5 w-3.5" />
          <kbd className="hidden rounded-md border border-white/10 bg-white/5 px-1.5 py-0.5 text-[10px] md:inline font-mono text-ink-2">
            Ctrl-K
          </kbd>
        </Button>

        {user && (
          <Tooltip content={`Signed in as ${user.email} (${user.display_name || "Learner"})`}>
            <div className="flex items-center gap-2.5 rounded-full border border-white/10 bg-raised/90 backdrop-blur-md py-1 pl-1.5 pr-2 text-xs text-ink-2 shadow-sm">
              <div className="grid h-6 w-6 place-items-center rounded-full bg-gradient-to-tr from-accent/30 to-accent-2/30 text-accent font-bold text-[10px] border border-accent/40">
                <User className="h-3 w-3" />
              </div>

              <span className="max-w-[14ch] md:max-w-[20ch] truncate font-medium text-white">
                {user.display_name || user.email}
              </span>

              {user.role && user.role !== "student" && (
                <span className="rounded-full bg-accent/20 px-2 py-0.5 text-[9px] font-bold text-accent uppercase tracking-wider border border-accent/30">
                  {user.role}
                </span>
              )}

              <button
                onClick={() => setSignOutOpen(true)}
                title="Sign out"
                aria-label="Sign out"
                className="grid h-6 w-6 place-items-center rounded-full text-ink-3 hover:bg-danger/20 hover:text-danger transition-colors cursor-pointer"
              >
                <LogOut className="h-3 w-3" />
              </button>
            </div>
          </Tooltip>
        )}
      </div>

      {/* Sign Out Confirmation Modal */}
      <ConfirmModal
        open={signOutOpen}
        onOpenChange={setSignOutOpen}
        title="Sign Out"
        description="Are you sure you want to end your current session? Any unsaved edits on the canvas will be cleared."
        confirmLabel="Yes, sign out"
        cancelLabel="Stay signed in"
        variant="danger"
        onConfirm={clear}
      />
    </header>
  );
}
