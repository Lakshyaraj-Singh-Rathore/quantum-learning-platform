import type { ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { backends } from "../api/backends";
import { useSession } from "../state/session";
import { Badge, Card, ErrorNote, Spinner, cn } from "../components/ui";

interface PlaceholderProps {
  title: string;
  phase: string;
  intro: string;
  bullets: string[];
  /** Pages may opt into the live proof strip (identity + engine catalogue),
   * showing the data layer is real even while the widgets land. */
  proof?: boolean;
  children?: ReactNode;
}

/** Honest placeholders per the plan: what lands here, in which phase, plus a
 * live demonstration that the shell speaks the same API the frozen UI uses.
 * Nothing here pretends to be the rebuilt page. */
export function PlaceholderPage({ title, phase, intro, bullets, proof, children }: PlaceholderProps) {
  return (
    <div className="mx-auto w-full max-w-3xl px-6 py-10">
      <div className="mb-2 flex items-center gap-3">
        <h2 className="text-xl font-semibold tracking-tight">{title}</h2>
        <Badge tone="accent">rebuilt in {phase}</Badge>
      </div>
      <p className="mb-6 text-[15px] leading-relaxed text-ink-2">{intro}</p>

      <Card>
        <h3 className="mb-3 text-sm font-semibold text-ink">On this page when it lands</h3>
        <ul className="flex flex-col gap-2">
          {bullets.map((b) => (
            <li key={b} className="flex gap-2.5 text-sm leading-relaxed text-ink-2">
              <span aria-hidden className="mt-[9px] h-1 w-1 shrink-0 rounded-full bg-accent" />
              {b}
            </li>
          ))}
        </ul>
      </Card>

      {children}
      {proof && <LiveProof />}
    </div>
  );
}

function LiveProof() {
  const user = useSession((s) => s.user);
  const { data, error, isLoading } = useQuery({
    queryKey: ["backends"],
    queryFn: backends,
    staleTime: 30_000,
  });

  return (
    <Card className="mt-4">
      <h3 className="mb-3 text-sm font-semibold text-ink">
        Live from the API <span className="font-normal text-ink-3">— the shell is already wired</span>
      </h3>
      {user && (
        <p className="mb-3 text-sm text-ink-2">
          Signed in as <span className="font-medium text-ink">{user.display_name || user.email}</span>{" "}
          <span className="text-ink-3">· {user.role}</span>
        </p>
      )}
      {isLoading && (
        <p className="flex items-center gap-2 text-sm text-ink-3">
          <Spinner /> loading engine catalogue…
        </p>
      )}
      {error != null && (
        <ErrorNote>
          {error instanceof Error ? error.message : "API unreachable"}
        </ErrorNote>
      )}
      {data && (
        <ul className="flex flex-col">
          {data.backends.map((b) => (
            <li
              key={b.id}
              className="flex items-center gap-3 border-b border-line-soft py-2.5 text-sm last:border-0"
            >
              <span
                aria-label={b.available ? "available" : "unavailable"}
                className={cn(
                  "h-2 w-2 shrink-0 rounded-full",
                  b.available ? "bg-accent" : "bg-ink-3/40",
                )}
              />
              <span className="font-medium text-ink">{b.label}</span>
              <span className="text-xs text-ink-3">{b.supports.join(", ")}</span>
              {!b.available && (
                <span className="ml-auto max-w-[45%] truncate text-xs text-ink-3" title={b.reason}>
                  {b.reason || "unavailable"}
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
