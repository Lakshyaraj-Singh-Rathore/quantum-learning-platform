import { useQuery } from "@tanstack/react-query";
import { Atom, Check, X } from "lucide-react";
import { backends } from "../../api/backends";
import { cn } from "../ui";

/** The engine badge the plan promised: one pill, honest about what the
 * server actually reports. The CUDA-Q GPU entry gets a dedicated dot
 * because on this platform that availability IS the story — its unavailability
 * reason (from is_available()) shows in the tooltip, never smoothed over. */
export function BackendBadge() {
  const { data } = useQuery({
    queryKey: ["backends"],
    queryFn: backends,
    staleTime: 30_000,
  });

  if (!data) {
    return (
      <span className="inline-flex h-7 items-center gap-2 rounded-full border border-line bg-raised px-3 text-xs text-ink-3">
        <Spinner /> engines…
      </span>
    );
  }

  const { backends: list } = data;
  const up = list.filter((b) => b.available).length;
  const cudaq = list.find((b) => b.id === "cudaq");

  const tooltip = list
    .map((b) => `${b.available ? "✓" : "✗"} ${b.label}${b.available ? "" : ` — ${b.reason || "unavailable"}`}`)
    .join("\n");

  return (
    <span
      title={tooltip}
      className="inline-flex h-7 items-center gap-2 rounded-full border border-line bg-raised px-3 text-xs text-ink-2"
    >
      <Atom className="h-3.5 w-3.5 text-ink-3" aria-hidden />
      <span>
        {up}/{list.length} engines
      </span>
      {cudaq && (
        <span
          className={cn(
            "inline-flex items-center gap-1 rounded-full px-1.5 py-0.5 text-[11px] font-medium",
            cudaq.available ? "bg-accent/15 text-accent" : "bg-hover text-ink-3",
          )}
        >
          GPU {cudaq.available ? <Check className="h-3 w-3" /> : <X className="h-3 w-3" />}
        </span>
      )}
    </span>
  );
}

function Spinner() {
  return (
    <svg className="h-3 w-3 animate-spin" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeOpacity="0.3" strokeWidth="3" />
    </svg>
  );
}
