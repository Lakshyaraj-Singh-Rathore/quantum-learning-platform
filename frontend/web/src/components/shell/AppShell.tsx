import { useState } from "react";
import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import { NarrowViewportNotice } from "./NarrowViewportNotice";
import { CommandPalette } from "./CommandPalette";
import { ErrorBoundary } from "./ErrorBoundary";

export function AppShell() {
  // Owned here, not inside the palette, so the top bar's search button and the
  // global shortcut drive the same thing.
  const [paletteOpen, setPaletteOpen] = useState(false);

    return (
      /* The rail is position:fixed, so the shell reserves only its collapsed
       * width (w-[60px]) rather than the expanded 240px. Pages therefore get
       * the extra ~180px permanently, and the sidebar expands over them on
       * hover instead of pushing them around. */
      <div className="flex h-full">
        <Sidebar />
        <div className="flex min-w-0 flex-1 flex-col pl-[60px]">
        <TopBar onOpenPalette={() => setPaletteOpen(true)} />
        <NarrowViewportNotice />
        <main className="min-h-0 flex-1 overflow-y-auto">
          {/* Around the page, not the app: a crash should cost the page and
              leave the shell standing, so you can navigate away. */}
          <ErrorBoundary label="This page">
            <Outlet />
          </ErrorBoundary>
        </main>
      </div>
      <CommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} />
    </div>
  );
}
