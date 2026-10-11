import { useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import { NarrowViewportNotice } from "./NarrowViewportNotice";
import { CommandPalette } from "./CommandPalette";
import { ErrorBoundary } from "./ErrorBoundary";

/**
 * Pages where the expanded sidebar should push the content aside rather than
 * float over it. These are the reading pages: covering the text you are
 * reading is annoying, whereas re-laying it out is not.
 *
 * The Composer is deliberately absent. Its canvas is width-sensitive and
 * drag-driven, so it keeps the overlay: the sidebar slides over it and the
 * grid's geometry never changes mid-interaction.
 */
const PUSH_PAGES = new Set(["/learn", "/curriculum"]);

export function AppShell() {
  // Owned here, not inside the palette, so the top bar's search button and the
  // global shortcut drive the same thing.
  const [paletteOpen, setPaletteOpen] = useState(false);

  // Route state, not hover state: this changes when you navigate, so it costs
  // nothing while the pointer is merely moving in and out of the rail.
  const { pathname } = useLocation();
  const pushes = PUSH_PAGES.has(pathname);

  return (
    /* The rail is position:fixed, so the shell reserves only its collapsed
     * width (w-[60px]) rather than the expanded 240px. Pages therefore get the
     * extra ~180px permanently, and the sidebar expands over them on hover
     * instead of pushing them around.
     *
     * The push/overlay choice is made in CSS via Tailwind's `peer`, driven by
     * the `peer` class on the rail. It is deliberately NOT React state: a
     * hover state flag here would re-render this shell — and so the current
     * page, Composer included — on every pointer entry and exit, which reads
     * as a stutter on the very canvas the overlay exists to protect. */
    <div className="flex h-full">
      <Sidebar />
      <div
        className={[
          "flex min-w-0 flex-1 flex-col pl-[60px]",
          pushes &&
            "transition-[padding] duration-200 ease-out peer-hover:pl-[240px] [.peer:focus-within~&]:pl-[240px]",
        ]
          .filter(Boolean)
          .join(" ")}
      >
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
