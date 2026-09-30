import { NavLink } from "react-router-dom";
import { Atom } from "lucide-react";
import { NAV_ITEMS } from "./nav";
import { cn } from "../ui";

export function Sidebar() {
  return (
    <aside className="flex w-[240px] shrink-0 flex-col border-r border-line-soft bg-raised max-[1100px]:w-[64px]">
      <div className="flex h-14 items-center gap-2.5 px-4 max-[1100px]:justify-center max-[1100px]:px-0">
        <span className="grid h-7 w-7 place-items-center rounded-lg bg-accent/15 text-accent">
          <Atom className="h-4 w-4" aria-hidden />
        </span>
        <span className="text-[15px] font-semibold tracking-tight max-[1100px]:hidden">
          QuantumLearn
        </span>
      </div>

      <nav className="flex flex-1 flex-col gap-0.5 px-2.5 pt-3 max-[1100px]:px-2" aria-label="Primary">
        {NAV_ITEMS.map(({ to, label, icon: Icon, phase, live }) => (
          <NavLink
            key={to}
            to={to}
            title={live ? `${label} · rebuilt (${phase})` : `${label} · rebuilt in ${phase}`}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-lg px-2.5 py-2 text-sm text-ink-2 transition-colors duration-150",
                "hover:bg-hover hover:text-ink",
                "max-[1100px]:justify-center",
                isActive && "bg-active text-ink font-medium",
              )
            }
          >
            <Icon className="h-4 w-4 shrink-0" aria-hidden />
            <span className="flex-1 max-[1100px]:hidden">{label}</span>
            {live && (
              <span
                aria-label="rebuilt"
                title="Rebuilt in the new UI"
                className="h-1.5 w-1.5 shrink-0 rounded-full bg-accent max-[1100px]:hidden"
              />
            )}
          </NavLink>
        ))}
      </nav>

      <p className="px-4 pb-3 text-[11px] leading-relaxed text-ink-3 max-[1100px]:hidden">
        UI migration in progress — pages land phase by phase
        (<span className="font-mono">docs/UI_REDESIGN_PLAN.md</span>).
      </p>
    </aside>
  );
}
