import { useState } from "react";
import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import { NarrowViewportNotice } from "./NarrowViewportNotice";
import { CommandPalette } from "./CommandPalette";

export function AppShell() {
  // Owned here, not inside the palette, so the top bar's search button and the
  // global shortcut drive the same thing.
  const [paletteOpen, setPaletteOpen] = useState(false);

  return (
    <div className="flex h-full">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar onOpenPalette={() => setPaletteOpen(true)} />
        <NarrowViewportNotice />
        <main className="min-h-0 flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>
      <CommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} />
    </div>
  );
}
