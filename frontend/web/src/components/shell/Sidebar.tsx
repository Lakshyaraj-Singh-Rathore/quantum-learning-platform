import { NavLink } from "react-router-dom";
import { Atom } from "lucide-react";
import { NAV_ITEMS } from "./nav";
import { cn } from "../ui";

/* Auto-hiding navigation rail.
 *
 * The rail is always on screen at RAIL_WIDTH so the app never loses its
 * primary navigation, but it costs only that much width. Moving the pointer
 * into it expands the full sidebar as an overlay: the page underneath keeps
 * its geometry, so expanding the nav cannot reflow the Composer grid or any
 * other width-sensitive canvas.
 *
 * Two details that matter:
 *
 *   * Expansion is width-only and driven by CSS, not React state. A state
 *     flag would re-render the whole shell on every pointer entry and exit,
 *     which is visible as a stutter on the Composer.
 *
 *   * The labels are hidden rather than unmounted while collapsed. Unmounting
 *     would drop them from the accessibility tree and make the collapsed rail
 *     a row of unlabelled icons; `title` on the link still names each one for
 *     assistive technology and on hover.
 */

const RAIL = "w-[60px]";
const OPEN = "w-[240px]";

export function Sidebar() {
  return (
    <aside
      className={cn(
        "group fixed inset-y-0 left-0 z-40 flex shrink-0 flex-col overflow-hidden",
        "border-r border-line-soft bg-raised",
        "transition-[width] duration-200 ease-out",
        "focus-within:w-[240px] hover:w-[240px]",
        RAIL,
      )}
      data-sidebar="auto-hide"
    >
      {/* Brand. The wordmark only exists in the expanded state. */}
      <div className="flex h-14 shrink-0 items-center gap-2.5 px-[18px]">
        <span className="grid h-7 w-7 shrink-0 place-items-center rounded-lg bg-accent/15 text-accent">
          <Atom className="h-4 w-4" aria-hidden />
        </span>
        <span className="whitespace-nowrap text-[15px] font-semibold tracking-tight opacity-0 transition-opacity duration-150 group-hover:opacity-100 group-focus-within:opacity-100">
          QuantumLearn
        </span>
      </div>

      <nav
        className="flex flex-1 flex-col gap-0.5 overflow-y-auto overflow-x-hidden px-2.5 pt-3"
        aria-label="Primary"
      >
        {NAV_ITEMS.map(({ to, label, icon: Icon, phase, live }) => (
          <NavLink
            key={to}
            to={to}
            title={live ? `${label} · rebuilt (${phase})` : `${label} · rebuilt in ${phase}`}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-lg px-2.5 py-2 text-sm text-ink-2 transition-colors duration-150",
                "hover:bg-hover hover:text-ink",
                isActive && "bg-active text-ink font-medium",
              )
            }
          >
            <Icon className="h-4 w-4 shrink-0" aria-hidden />
            <span className="flex-1 whitespace-nowrap opacity-0 transition-opacity duration-150 group-hover:opacity-100 group-focus-within:opacity-100">
              {label}
            </span>
            {live && (
              <span
                aria-label="rebuilt"
                title="Rebuilt in the new UI"
                className="h-1.5 w-1.5 shrink-0 rounded-full bg-accent opacity-0 transition-opacity duration-150 group-hover:opacity-100 group-focus-within:opacity-100"
              />
            )}
          </NavLink>
        ))}
      </nav>

      <p className="shrink-0 px-4 pb-3 text-[11px] leading-relaxed text-ink-3 opacity-0 transition-opacity duration-150 group-hover:opacity-100 group-focus-within:opacity-100">
        UI migration in progress — pages land phase by phase (
        <span className="font-mono">docs/UI_REDESIGN_PLAN.md</span>).
      </p>

      {/* The cutover gate. P0–P7 are built; P8 (making the web app the default
          landing and marking Streamlit legacy) is deliberately NOT done. It
          waits on the owner personally clicking through the UI, so this marker
          stays until that sign-off happens. Remove it as part of P8. */}
      <p
        className="mx-4 mb-3 shrink-0 rounded-md border border-warn/40 bg-warn/10 px-2.5 py-2 text-[11px] font-semibold leading-relaxed text-ink opacity-0 transition-opacity duration-150 group-hover:opacity-100 group-focus-within:opacity-100"
        data-cutover-gate="pending-personal-ui-testing"
      >
        CUTOVER — AFTER PERSONAL UI TESTING
      </p>
    </aside>
  );
}

/** Width the shell must reserve so content never sits under the rail. */
export const SIDEBAR_RAIL_WIDTH = RAIL;
export const SIDEBAR_OPEN_WIDTH = OPEN;
