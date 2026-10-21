import { useState } from "react";
import { Outlet } from "react-router-dom";
import { Sidebar, useSidebarStore } from "./Sidebar";
import { TopBar } from "./TopBar";
import { CommandPalette } from "./CommandPalette";
import { ErrorBoundary } from "./ErrorBoundary";
import { NarrowViewportNotice } from "./NarrowViewportNotice";
import { ToastProvider, cn } from "../ui";
import { X } from "lucide-react";

export function AppShell() {
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const { isCollapsed } = useSidebarStore();

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-bg text-ink">
      <ToastProvider />

      {/* Accessible Skip to Content Link */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-50 focus:rounded-md focus:bg-accent focus:px-4 focus:py-2 focus:text-accent-ink focus:shadow-lg focus:outline-none"
      >
        Skip to main content
      </a>

      {/* Desktop Persistent Sidebar */}
      <div className="hidden lg:block shrink-0">
        <Sidebar />
      </div>

      {/* Mobile Slide-Over Drawer */}
      {mobileNavOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-black/70 backdrop-blur-xs transition-opacity"
            onClick={() => setMobileNavOpen(false)}
            aria-hidden="true"
          />

          {/* Drawer container */}
          <div className="fixed inset-y-0 left-0 flex w-[260px] max-w-[85vw] flex-col bg-raised shadow-2xl z-50 animate-in slide-in-from-left duration-200">
            {/* The sidebar inside this drawer is a z-30 element, so a z-10
                close button was painted underneath its header row: the X was
                visible but every click landed on the sidebar instead. A
                screenshot cannot show this — only a hit test can. Keep it
                above the sidebar, below the drawer shell itself. */}
            <div className="absolute right-2 top-3 z-40">
              <button
                onClick={() => setMobileNavOpen(false)}
                className="p-1.5 rounded-lg text-ink-3 hover:text-ink hover:bg-hover transition-colors"
                aria-label="Close menu"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <Sidebar mobile onNavigate={() => setMobileNavOpen(false)} />
          </div>
        </div>
      )}

      {/* Main App Layout */}
      <div
        className={cn(
          "flex min-w-0 flex-1 flex-col transition-all duration-200 h-full overflow-hidden",
          isCollapsed ? "lg:pl-[64px]" : "lg:pl-[230px]",
        )}
      >
        <TopBar
          onOpenPalette={() => setPaletteOpen(true)}
          onOpenMobileNav={() => setMobileNavOpen(true)}
        />

        {/* The component existed but was never mounted, so the 900px minimum
            the design targets was never actually communicated to anyone. */}
        <NarrowViewportNotice />

        <main
          id="main-content"
          tabIndex={-1}
          className="min-h-0 flex-1 overflow-y-auto focus:outline-none"
        >
          <ErrorBoundary label="This page">
            <Outlet />
          </ErrorBoundary>
        </main>
      </div>

      <CommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} />
    </div>
  );
}
