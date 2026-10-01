import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Send } from "lucide-react";
import { getLesson, listLessons, aiChat, type ChatTurn } from "../api/lessons";
import { Badge, Button, Card, ErrorNote, Spinner, cn } from "../components/ui";
import { Markdown } from "../components/Markdown";
import { DEMOS } from "../components/demos/Demos";

type Track = "Theory" | "Circuit" | "All";

const TRACKS: Track[] = ["Theory", "Circuit", "All"];

/** Mirrors DEMOS_FOR_LESSON in frontend/lib/lesson_demos.py. */
const DEMOS_FOR_LESSON: Record<string, string[]> = {
  "01_qubits": ["bit_vs_qubit", "build_a_qubit", "bloch", "circuit_lab"],
  "02_gates": ["gates", "plus_minus", "circuit_lab"],
  "03_entanglement": ["state_space"],
  "04_measurement": ["measure", "bit_order"],
  "05_deutsch_jozsa": ["interference"],
  "06_grover": ["interference"],
  "10_gates_bootcamp": ["gates", "bloch", "circuit_lab"],
  "11_bell_states": ["plus_minus", "state_space", "circuit_lab"],
  "12_control_flow": ["bit_order", "circuit_lab"],
  "13_classical_bit_vs_qubit": ["bit_vs_qubit", "build_a_qubit", "measure", "circuit_lab"],
};

export function LearnPage() {
  const [track, setTrack] = useState<Track>("All");
  const [slug, setSlug] = useState<string | null>(null);
  const [histories, setHistories] = useState<Record<string, ChatTurn[]>>({});
  const [question, setQuestion] = useState("");
  const [demoKey, setDemoKey] = useState<string | null>(null);

  const lessons = useQuery({ queryKey: ["lessons"], queryFn: listLessons, staleTime: 5 * 60_000 });

  const visible = useMemo(() => {
    const all = lessons.data ?? [];
    if (track === "All") return all;
    const wanted = track.toLowerCase();
    return all.filter((l) => (l.track || "theory") === wanted);
  }, [lessons.data, track]);

  // Derived, not stored: a selected lesson that is not in the visible track
  // (or none selected yet) falls back to the first one. Keeping this out of an
  // effect means the page is correct on its very first render.
  const current = slug && visible.some((l) => l.slug === slug) ? slug : (visible[0]?.slug ?? null);

  const detail = useQuery({
    queryKey: ["lesson", current],
    queryFn: () => getLesson(current as string),
    enabled: current !== null,
    staleTime: 5 * 60_000,
  });

  const chosen = (lessons.data ?? []).find((l) => l.slug === current) ?? null;
  const demoKeys = (current ? DEMOS_FOR_LESSON[current] : undefined) ?? [];
  const demoKeyNow = demoKey && demoKeys.includes(demoKey) ? demoKey : demoKeys[0];
  const activeDemo = demoKeyNow ? DEMOS[demoKeyNow] : undefined;
  const trackLabel = ((chosen?.track as string) || "theory").toLowerCase();
  const history = current ? (histories[current] ?? []) : [];

  const chat = useMutation({
    mutationFn: (turns: ChatTurn[]) => aiChat(turns[turns.length - 1].content, turns.slice(0, -1).slice(-6)),
    onSuccess: (reply, turns) => {
      if (!current) return;
      setHistories((prev) => ({
        ...prev,
        [current]: [...turns, { role: "assistant", content: reply.reply }],
      }));
    },
  });

  function ask() {
    const text = question.trim();
    if (!text || !current) return;
    const next = [...history, { role: "user" as const, content: text }];
    setHistories((prev) => ({ ...prev, [current]: next }));
    setQuestion("");
    chat.mutate(next);
  }

  if (lessons.isLoading) {
    return (
      <p className="flex items-center gap-2 p-6 text-sm text-ink-3">
        <Spinner /> loading lessons…
      </p>
    );
  }

  if (lessons.isError) {
    return <ErrorNote className="m-6">{String(lessons.error)}</ErrorNote>;
  }

  if (visible.length === 0 && (lessons.data ?? []).length === 0) {
    return (
      <div className="p-6">
        <ErrorNote>
          No lessons are loaded yet. The API ingests <code>/content/*.md</code> on startup —
          check that the content folder is mounted.
        </ErrorNote>
      </div>
    );
  }

  return (
    <div className="grid gap-6 p-6 lg:grid-cols-[240px_minmax(0,1fr)]">
      <nav className="flex flex-col gap-3">
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-3">Track</p>
          <div className="flex gap-1 rounded-lg border border-line bg-raised p-1">
            {TRACKS.map((t) => (
              <button
                key={t}
                onClick={() => setTrack(t)}
                className={cn(
                  "flex-1 rounded-md px-2 py-1 text-[13px] transition-colors",
                  track === t ? "bg-accent text-white" : "text-ink-2 hover:bg-hover",
                )}
              >
                {t}
              </button>
            ))}
          </div>
          <p className="mt-2 text-[12px] leading-relaxed text-ink-3">
            <strong className="font-medium text-ink-2">Theory</strong> explains the concepts.{" "}
            <strong className="font-medium text-ink-2">Circuit</strong> is hands-on practice in
            the Composer.
          </p>
        </div>

        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-3">Lessons</p>
          {visible.length === 0 ? (
            <p className="text-[13px] text-ink-3">No lessons in the {track} track yet.</p>
          ) : (
            <ul className="flex flex-col gap-1">
              {visible.map((lesson) => {
                const active = lesson.slug === slug;
                return (
                  <li key={lesson.slug}>
                    <button
                      onClick={() => setSlug(lesson.slug)}
                      className={cn(
                        "flex w-full items-start gap-2 rounded-lg px-2 py-1.5 text-left text-[13px] leading-snug transition-colors",
                        active ? "bg-accent/10 text-ink" : "text-ink-2 hover:bg-hover",
                      )}
                    >
                      <Badge tone={lesson.track === "circuit" ? "accent" : "neutral"}>
                        {lesson.track === "circuit" ? "C" : "T"}
                      </Badge>
                      <span className={cn(active && "font-medium")}>{lesson.title}</span>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </nav>

      <div className="flex min-w-0 flex-col gap-5">
        {chosen && (
          <header className="flex flex-col gap-2">
            <h2 className="text-xl font-semibold tracking-tight">{chosen.title}</h2>
            {trackLabel === "circuit" && (
              <p className="rounded-lg border border-line bg-raised px-3 py-2 text-[13px] text-ink-2">
                <strong className="text-ink">Hands-on lesson.</strong> Open the{" "}
                <strong className="text-ink">Composer</strong> in another tab and build each
                circuit as you read.
              </p>
            )}
            <p className="text-[13px] text-ink-3">
              Track: <code className="font-mono">{trackLabel}</code>
              {chosen.tags.length > 0 && (
                <>
                  {"  |  Concepts: "}
                  {chosen.tags.map((tag, i) => (
                    <span key={tag}>
                      {i > 0 && ", "}
                      <code className="font-mono">{tag}</code>
                    </span>
                  ))}
                </>
              )}
            </p>
          </header>
        )}

        {detail.isLoading && (
          <p className="flex items-center gap-2 text-sm text-ink-3">
            <Spinner /> loading lesson…
          </p>
        )}
        {detail.isError && <ErrorNote>{String(detail.error)}</ErrorNote>}

        {detail.data && (
          <Card>
            <Markdown>{detail.data.content}</Markdown>
          </Card>
        )}

        {demoKeys.length > 0 && (
          <Card>
            <h3 className="text-sm font-semibold">🧪 Try it yourself</h3>
            <p className="mt-1 text-[13px] text-ink-3">
              These are live: every control computes a real quantum state, and the
              visualisations are the same ones the Composer uses.
            </p>
            <div className="mt-3 flex flex-wrap gap-1">
              {demoKeys.map((key) => (
                <button
                  key={key}
                  onClick={() => setDemoKey(key)}
                  className={cn(
                    "rounded-md border px-2.5 py-1 text-[13px] transition-colors",
                    demoKey === key
                      ? "border-accent bg-accent/10 text-ink"
                      : "border-line text-ink-2 hover:bg-hover",
                  )}
                >
                  {DEMOS[key].title}
                </button>
              ))}
            </div>
            {activeDemo && (
              <div className="mt-4">
                <p className="mb-2 text-[12px] text-ink-3">{activeDemo.blurb}</p>
                <activeDemo.Component />
              </div>
            )}
          </Card>
        )}

        <Card>
          <h3 className="mb-3 text-sm font-semibold">Ask the AI tutor</h3>
          <div className="flex max-h-96 flex-col gap-3 overflow-auto">
            {history.length === 0 && (
              <p className="text-[13px] text-ink-3">
                The tutor answers from the curriculum, and cites the lessons it used.
              </p>
            )}
            {history.map((turn, i) => (
              <div
                key={i}
                className={cn(
                  "rounded-lg px-3 py-2 text-[13px] leading-relaxed",
                  turn.role === "user" ? "bg-accent/10 text-ink" : "bg-hover/60 text-ink-2",
                )}
              >
                <Markdown>{turn.content}</Markdown>
              </div>
            ))}
            {chat.isPending && (
              <p className="flex items-center gap-2 text-[13px] text-ink-3">
                <Spinner /> Thinking…
              </p>
            )}
            {chat.data?.citations && chat.data.citations.length > 0 && (
              <details className="rounded-lg border border-line-soft [&_summary]:cursor-pointer">
                <summary className="px-3 py-2 text-[12px] font-medium text-ink-2">
                  Sources from the curriculum
                </summary>
                <div className="flex flex-col gap-2 border-t border-line-soft p-3">
                  {chat.data.citations.map((citation, i) => (
                    <div key={i}>
                      <p className="text-[12px] font-semibold text-ink">
                        {citation.lesson_slug}
                      </p>
                      <p className="font-mono text-[11px] text-ink-3">
                        {citation.text.slice(0, 400)}…
                      </p>
                    </div>
                  ))}
                </div>
              </details>
            )}
          </div>
          {chat.isError && <ErrorNote className="mt-2">{String(chat.error)}</ErrorNote>}
          <div className="mt-3 flex gap-2">
            <input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") ask();
              }}
              placeholder={chosen ? `Ask about ${chosen.title}...` : "Ask a question..."}
              className="h-9 flex-1 rounded-lg border border-line bg-raised px-3 text-sm text-ink placeholder:text-ink-3"
            />
            <Button variant="primary" size="sm" onClick={ask} disabled={!question.trim() || chat.isPending}>
              {chat.isPending ? <Spinner /> : <Send className="h-3.5 w-3.5" />}
              Ask
            </Button>
          </div>
        </Card>
      </div>
    </div>
  );
}
