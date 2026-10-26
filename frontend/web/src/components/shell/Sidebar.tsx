import { NavLink } from "react-router-dom";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { NAV_SECTIONS, useNavItems } from "./nav";
import { cn, Tooltip, QuantumLogo } from "../ui";
import { create } from "zustand";

interface SidebarStore {
  isCollapsed: boolean;
  toggleCollapsed: () => void;
  setCollapsed: (val: boolean) => void;
}

export const useSidebarStore = create<SidebarStore>((set) => ({
  isCollapsed: typeof window !== "undefined" && localStorage.getItem("ql_sidebar_collapsed") === "true",
  toggleCollapsed: () =>
    set((state) => {
      const next = !state.isCollapsed;
      localStorage.setItem("ql_sidebar_collapsed", String(next));
      return { isCollapsed: next };
    }),
  setCollapsed: (val) => {
    localStorage.setItem("ql_sidebar_collapsed", String(val));
    set({ isCollapsed: val });
  },
}));

export const SIDEBAR_EXPANDED_WIDTH = "w-[230px]";
export const SIDEBAR_COLLAPSED_WIDTH = "w-[64px]";

export function Sidebar({
  mobile = false,
  onNavigate,
}: {
  mobile?: boolean;
  onNavigate?: () => void;
}) {
  const { isCollapsed, toggleCollapsed } = useSidebarStore();
  // Flag-gated entries are absent until the server confirms them, so the
  // sidebar never offers a link to a feature this deployment has off.
  const navItems = useNavItems();
  const collapsed = !mobile && isCollapsed;

  return (
    <aside
      className={cn(
        "flex flex-col shrink-0 border-r border-white/5 bg-[#090b14]/90 backdrop-blur-2xl transition-all duration-200 select-none z-30 shadow-2xl",
        mobile ? "w-full h-full" : collapsed ? "w-[64px] h-screen fixed inset-y-0 left-0" : "w-[230px] h-screen fixed inset-y-0 left-0",
      )}
      aria-label="Sidebar navigation"
    >
      {/* Brand Header */}
      <div className={cn("flex h-15 shrink-0 items-center border-b border-white/5", collapsed ? "justify-center px-2" : "justify-between px-4")}>
        <div className="flex items-center gap-3 min-w-0">
          <div
            onClick={collapsed ? toggleCollapsed : undefined}
            title={collapsed ? "QuantumLearn Studio (click to expand)" : "QuantumLearn Studio"}
            className="cursor-pointer transition-transform duration-150 hover:scale-105 shrink-0"
          >
            <QuantumLogo
              className={collapsed ? "h-10 w-10" : "h-8.5 w-8.5"}
              size={collapsed ? 26 : 22}
            />
          </div>
          {!collapsed && (
            <div className="flex flex-col min-w-0">
              <span className="truncate text-sm font-bold tracking-tight text-white font-display">
                QuantumLearn
              </span>
              <span className="text-[10px] text-ink-3 font-medium tracking-wider uppercase">
                Studio
              </span>
            </div>
          )}
        </div>

        {!mobile && !collapsed && (
          <button
            onClick={toggleCollapsed}
            aria-label="Collapse sidebar"
            title="Collapse sidebar"
            className="p-1.5 rounded-lg text-ink-3 hover:text-white hover:bg-white/5 transition-colors cursor-pointer"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* Navigation Sections */}
      <nav
        className={cn(
          "flex-1 overflow-y-auto overflow-x-hidden py-3",
          collapsed ? "px-2 space-y-2" : "px-2.5 space-y-4",
        )}
        aria-label="Primary"
      >
        {NAV_SECTIONS.map((sec, secIdx) => {
          const items = navItems.filter((item) => item.section === sec.id);
          if (items.length === 0) return null;

          return (
            <div key={sec.id} className={cn("space-y-1", collapsed && "flex flex-col items-center")}>
              {!collapsed && (
                <div className="px-2.5 py-1 text-[10px] font-bold text-ink-3/80 uppercase tracking-widest font-mono">
                  {sec.label}
                </div>
              )}
              {collapsed && secIdx > 0 && (
                <div className="my-1.5 h-px w-6 bg-white/10" />
              )}

              {items.map(({ to, label, icon: Icon }) => {
                const navLink = (
                  <NavLink
                    key={to}
                    to={to}
                    onClick={onNavigate}
                    className={({ isActive }) =>
                      cn(
                        "group relative flex items-center transition-all duration-150 cursor-pointer select-none",
                        collapsed
                          ? "h-10 w-10 justify-center rounded-xl mx-auto"
                          : "gap-3 rounded-xl px-3 py-2 text-xs sm:text-sm",
                        isActive
                          ? "bg-accent/15 text-accent font-semibold border border-accent/40 shadow-[0_0_15px_-4px_rgba(59,130,246,0.5)]"
                          : "text-ink-3 hover:text-white hover:bg-white/[0.06] border border-transparent hover:border-white/10",
                      )
                    }
                  >
                    {({ isActive }) => (
                      <>
                        <Icon
                          className={cn(
                            "shrink-0 transition-all duration-150",
                            collapsed ? "h-5 w-5" : "h-4 w-4",
                            isActive ? "text-accent stroke-[2.25]" : "text-ink-3 group-hover:text-white stroke-[1.75]",
                          )}
                          aria-hidden
                        />
                        {!collapsed && <span className="truncate">{label}</span>}
                        {isActive && !collapsed && (
                          <div className="ml-auto h-1.5 w-1.5 rounded-full bg-accent shadow-[0_0_8px_2px_rgba(59,130,246,0.8)]" />
                        )}
                        {/* Active indicator bar on collapsed sidebar */}
                        {isActive && collapsed && (
                          <span
                            className="absolute -left-2 top-2 bottom-2 w-1 rounded-r-full bg-accent shadow-[0_0_8px_rgba(59,130,246,0.8)]"
                            aria-hidden
                          />
                        )}
                      </>
                    )}
                  </NavLink>
                );

                if (collapsed) {
                  return (
                    <Tooltip key={to} content={label} side="right">
                      {navLink}
                    </Tooltip>
                  );
                }

                return navLink;
              })}
            </div>
          );
        })}
      </nav>

      {/* Bottom Actions for Collapsed Bar */}
      {!mobile && collapsed && (
        <div className="p-2 border-t border-white/5 flex justify-center">
          <Tooltip content="Expand sidebar" side="right">
            <button
              onClick={toggleCollapsed}
              aria-label="Expand sidebar"
              className="h-10 w-10 flex items-center justify-center rounded-xl text-ink-3 hover:text-white hover:bg-white/5 transition-colors cursor-pointer"
            >
              <ChevronRight className="h-5 w-5" />
            </button>
          </Tooltip>
        </div>
      )}
    </aside>
  );
}
