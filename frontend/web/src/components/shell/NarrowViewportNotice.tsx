/**
 * Warns when the window is narrower than the supported minimum.
 *
 * The design system targets 900px and up: below that the composer's
 * three-column shell and the results grids stop being usable rather than
 * merely getting tight. Rather than silently degrade, say so.
 *
 * The notice is honest about what it is: the app is not *made* read-only below
 * the breakpoint, because disabling every editor from one place would be an
 * invasive change with wide blast radius. It reports that the layout is not
 * supported at this width, which is the true state of affairs.
 */
import { useEffect, useState } from "react";

export const MIN_SUPPORTED_WIDTH = 900;

/** Tracks a CSS media query. Returns false during SSR, when there is no window. */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) return;
    const list = window.matchMedia(query);
    setMatches(list.matches);
    const onChange = (event: MediaQueryListEvent) => setMatches(event.matches);
    // Safari < 14 only has the deprecated addListener.
    if (list.addEventListener) {
      list.addEventListener("change", onChange);
      return () => list.removeEventListener("change", onChange);
    }
    list.addListener(onChange);
    return () => list.removeListener(onChange);
  }, [query]);

  return matches;
}

export function NarrowViewportNotice() {
  const narrow = useMediaQuery(`(max-width: ${MIN_SUPPORTED_WIDTH - 1}px)`);

  if (!narrow) return null;

  return (
    <div
      role="status"
      className="border-b border-warn/40 bg-warn/10 px-4 py-2 text-[13px] text-ink"
    >
      <strong className="font-semibold">Narrow window.</strong> This interface is designed for
      screens at least {MIN_SUPPORTED_WIDTH}px wide. Below that the layout is cramped, editing is
      not supported, and the composer in particular will be difficult to use. Widen the window, or
      rotate your device.
    </div>
  );
}
