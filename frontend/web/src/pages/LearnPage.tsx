import { useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  Send,
  Search,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  FlaskConical,
  Bot,
  Sparkles,
  BookOpen,
  Cpu,
  ExternalLink,
} from "lucide-react";
import { getLesson, listLessons, aiChat, type ChatTurn } from "../api/lessons";
import { Badge, Button, ErrorNote, Input, Spinner, Textarea, cn } from "../components/ui";
import { Markdown } from "../components/Markdown";
import { DEMOS } from "../components/demos/Demos";

type Track = "Theory" | "Circuit" | "All";
const TRACKS: Track[] = ["All", "Theory", "Circuit"];

const DEMOS_FOR_LESSON: Record<string, string[]> = {
  "01_qubits": ["bit_vs_qubit", "build_a_qubit", "bloch", "circuit_lab"],
  "02_gates": ["gates", "plus_minus", "circuit_lab"],
  "03_entanglement": ["entanglement_lab", "circuit_lab"],
  "04_measurement": ["measure", "bit_order"],
  "05_deutsch_jozsa": ["interference"],
  "06_grover": ["interference"],
  "10_gates_bootcamp": ["gates", "bloch", "circuit_lab"],
  "11_bell_states": ["entanglement_lab", "plus_minus", "circuit_lab"],
  "12_control_flow": ["bit_order", "circuit_lab"],
  "13_classical_bit_vs_qubit": ["bit_vs_qubit", "build_a_qubit", "measure", "circuit_lab"],
  "21_entanglement_measures": ["entanglement_lab", "state_space"],
  "24_tensor_products": ["state_space"],
  "26_teleportation": ["entanglement_lab", "circuit_lab"],
};

export function LearnPage() {
  const [track, setTrack] = useState<Track>("All");
  const [slug, setSlug] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [mobileTab, setMobileTab] = useState<"content" | "tutor">("content");
  const [completedLessons, setCompletedLessons] = useState<Record<string, boolean>>(() => {
    try {
      const saved = localStorage.getItem("ql_completed_lessons");
      return saved ? JSON.parse(saved) : {};
    } catch {
      return {};
    }
  });

  const [searchParams, setSearchParams] = useSearchParams();
  const lessonFromUrl = searchParams.get("lesson");
  const [histories, setHistories] = useState<Record<string, ChatTurn[]>>({});
  const [question, setQuestion] = useState("");
  const [demoKey, setDemoKey] = useState<string | null>(null);

  const lessons = useQuery({ queryKey: ["lessons"], queryFn: listLessons, staleTime: 5 * 60_000 });

  const allLessons = lessons.data ?? [];

  const requested = useMemo(() => {
    return lessonFromUrl ? (allLessons.find((l) => l.slug === lessonFromUrl) ?? null) : null;
  }, [allLessons, lessonFromUrl]);

  const visible = useMemo(() => {
    let filtered = allLessons;
    if (track !== "All") {
      const wanted = track.toLowerCase();
      filtered = filtered.filter((l) => (l.track || "theory").toLowerCase() === wanted);
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (l) => l.title.toLowerCase().includes(q) || l.tags.some((t) => t.toLowerCase().includes(q)),
      );
    }
    if (requested && !filtered.some((l) => l.slug === requested.slug)) {
      return [requested, ...filtered];
    }
    return filtered;
  }, [allLessons, track, searchQuery, requested]);

  const currentSlug =
    lessonFromUrl && allLessons.some((l) => l.slug === lessonFromUrl)
      ? lessonFromUrl
      : slug && allLessons.some((l) => l.slug === slug)
        ? slug
        : (visible[0]?.slug ?? allLessons[0]?.slug ?? null);

  const detail = useQuery({
    queryKey: ["lesson", currentSlug],
    queryFn: () => getLesson(currentSlug as string),
    enabled: currentSlug !== null,
    staleTime: 5 * 60_000,
  });

  const chosenLesson = allLessons.find((l) => l.slug === currentSlug) ?? null;
  const currentIndex = allLessons.findIndex((l) => l.slug === currentSlug);
  const prevLesson = currentIndex > 0 ? allLessons[currentIndex - 1] : null;
  const nextLesson = currentIndex >= 0 && currentIndex < allLessons.length - 1 ? allLessons[currentIndex + 1] : null;

  const demoKeys = (currentSlug ? DEMOS_FOR_LESSON[currentSlug] : undefined) ?? [];
  const interactiveDemoKeys = demoKeys.filter((k) => k !== "circuit_lab");
  const demoKeyNow = demoKey && interactiveDemoKeys.includes(demoKey) ? demoKey : (interactiveDemoKeys[0] ?? demoKeys[0]);
  const activeDemo = demoKeyNow ? DEMOS[demoKeyNow] : undefined;
  const history = currentSlug ? (histories[currentSlug] ?? []) : [];

  const selectLesson = (targetSlug: string) => {
    setSlug(targetSlug);
    setSearchParams({ lesson: targetSlug });
    setDemoKey(null);
    setMobileTab("content");
  };

  const toggleComplete = (targetSlug: string) => {
    setCompletedLessons((prev) => {
      const next = { ...prev, [targetSlug]: !prev[targetSlug] };
      localStorage.setItem("ql_completed_lessons", JSON.stringify(next));
      return next;
    });
  };

  const chat = useMutation({
    mutationFn: (turns: ChatTurn[]) =>
      aiChat(turns[turns.length - 1].content, turns.slice(0, -1).slice(-6)),
    onSuccess: (reply, turns) => {
      if (!currentSlug) return;
      setHistories((prev) => ({
        ...prev,
        [currentSlug]: [...turns, { role: "assistant", content: reply.reply }],
      }));
    },
  });

  function ask() {
    const text = question.trim();
    if (!text || !currentSlug) return;
    const next = [...history, { role: "user" as const, content: text }];
    setHistories((prev) => ({ ...prev, [currentSlug]: next }));
    setQuestion("");
    chat.mutate(next);
  }

  // Helper to map citation slug to lesson title
  const getCitationTitle = (citationSlug: string) => {
    const found = allLessons.find((l) => l.slug === citationSlug);
    return found ? found.title : citationSlug;
  };

  if (lessons.isLoading) {
    return (
      <div className="flex items-center justify-center h-full p-12 text-ink-3">
        <Spinner className="mr-3" /> Loading curriculum lessons…
      </div>
    );
  }

  if (lessons.isError) {
    return (
      <div className="p-8">
        <ErrorNote>{String(lessons.error)}</ErrorNote>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full overflow-hidden bg-bg text-ink">
      {/* Mobile Tab Switcher */}
      <div className="xl:hidden flex border-b border-line bg-raised px-4 py-2 shrink-0 justify-around">
        <button
          onClick={() => setMobileTab("content")}
          className={cn(
            "flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors",
            mobileTab === "content" ? "bg-subtle text-accent border border-line" : "text-ink-2",
          )}
        >
          <BookOpen className="h-4 w-4" /> Lesson Content
        </button>
        <button
          onClick={() => setMobileTab("tutor")}
          className={cn(
            "flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors",
            mobileTab === "tutor" ? "bg-subtle text-accent border border-line" : "text-ink-2",
          )}
        >
          <Bot className="h-4 w-4" /> AI Tutor {history.length > 0 && `(${history.length})`}
        </button>
      </div>

      {/* Main 3-Column Desktop Layout */}
      <div className="flex flex-1 min-h-0 overflow-hidden">
        {/* COLUMN 1: Lesson List Sidebar (260px) */}
        <aside
          className={cn(
            "w-full sm:w-[260px] xl:w-[280px] shrink-0 border-r border-line bg-raised flex flex-col min-h-0",
            mobileTab === "tutor" ? "hidden xl:flex" : "flex",
          )}
        >
          {/* Track Filter Tabs */}
          <div className="p-3 border-b border-line-soft">
            <div className="flex rounded-lg border border-line bg-subtle p-0.5">
              {TRACKS.map((t) => (
                <button
                  key={t}
                  onClick={() => setTrack(t)}
                  className={cn(
                    "flex-1 rounded-md py-1 text-xs font-medium transition-all text-center",
                    track === t ? "bg-raised text-ink shadow-xs border border-line/60" : "text-ink-3 hover:text-ink",
                  )}
                >
                  {t}
                </button>
              ))}
            </div>

            {/* Client-side search */}
            <div className="relative mt-2.5">
              <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-ink-3" />
              <Input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search lessons..."
                className="h-8 pl-8 text-xs bg-bg"
              />
            </div>
          </div>

          {/* Lessons Scrollable List */}
          <nav className="flex-1 overflow-y-auto p-2 space-y-0.5" aria-label="Lessons">
            {visible.length === 0 ? (
              <p className="p-4 text-xs text-ink-3 text-center">No matching lessons found.</p>
            ) : (
              visible.map((lesson) => {
                const isActive = lesson.slug === currentSlug;
                const isDone = completedLessons[lesson.slug];

                return (
                  <button
                    key={lesson.slug}
                    onClick={() => selectLesson(lesson.slug)}
                    className={cn(
                      "flex w-full items-start gap-2.5 rounded-lg px-2.5 py-2 text-left text-xs transition-colors group",
                      isActive
                        ? "bg-active text-ink font-semibold border border-line-focus/40 shadow-xs"
                        : "text-ink-2 hover:bg-hover hover:text-ink",
                    )}
                  >
                    <span
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleComplete(lesson.slug);
                      }}
                      title={isDone ? "Completed" : "Mark as completed"}
                      className={cn(
                        "mt-0.5 shrink-0 transition-colors cursor-pointer",
                        isDone ? "text-ok" : "text-ink-3 hover:text-ink",
                      )}
                    >
                      <CheckCircle2 className="h-4 w-4" />
                    </span>

                    <span className="flex-1 leading-snug line-clamp-2">{lesson.title}</span>

                    <Badge
                      tone={lesson.track === "circuit" ? "accent" : "neutral"}
                      className="text-[10px] px-1.5 py-0 shrink-0 uppercase tracking-wider"
                    >
                      {lesson.track === "circuit" ? "Circuit" : "Theory"}
                    </Badge>
                  </button>
                );
              })
            )}
          </nav>
        </aside>

        {/* COLUMN 2: Lesson Content (max 72ch prose) */}
        <section
          className={cn(
            "flex-1 min-w-0 overflow-y-auto p-6 lg:p-10",
            mobileTab === "tutor" ? "hidden xl:block" : "block",
          )}
        >
          <div className="max-w-[72ch] mx-auto pb-16">
            {chosenLesson && (
              <header className="mb-8">
                <div className="flex flex-wrap items-center gap-2 mb-3">
                  <Badge tone={chosenLesson.track === "circuit" ? "accent" : "neutral"}>
                    {chosenLesson.track === "circuit" ? "Circuit Track" : "Theory Track"}
                  </Badge>

                  {chosenLesson.tags.map((tag) => (
                    <Badge key={tag} tone="neutral">
                      {tag}
                    </Badge>
                  ))}

                  {completedLessons[chosenLesson.slug] && (
                    <Badge tone="ok" className="gap-1">
                      <CheckCircle2 className="h-3 w-3" /> Completed
                    </Badge>
                  )}
                </div>

                <h1 className="text-3xl lg:text-4xl font-extrabold tracking-tight text-ink leading-tight">
                  {chosenLesson.title}
                </h1>
              </header>
            )}

            {detail.isLoading && (
              <div className="py-12 flex items-center justify-center text-sm text-ink-3">
                <Spinner className="mr-2.5" /> Loading lesson content…
              </div>
            )}

            {detail.isError && (
              <ErrorNote className="my-4">{String(detail.error)}</ErrorNote>
            )}

            {detail.data && (
              <article className="lesson-prose mb-10">
                <Markdown>{detail.data.content}</Markdown>
              </article>
            )}

            {/* Try It Yourself Demos */}
            {demoKeys.length > 0 && (
              <div className="my-10 rounded-xl border border-line bg-raised p-6 shadow-sm">
                <div className="flex items-center gap-2 mb-2">
                  <FlaskConical className="h-5 w-5 text-accent" />
                  <h3 className="text-base font-semibold text-ink">Try it yourself</h3>
                </div>
                <p className="text-sm text-ink-3 mb-4">
                  Interactive quantum simulations computed live in your browser:
                </p>

                <div className="flex flex-wrap items-center gap-1.5 mb-5">
                  {demoKeys.map((key) => {
                    const isComposer = key === "circuit_lab";
                    if (isComposer) {
                      return (
                        <Link
                          key={key}
                          to="/composer"
                          className="rounded-lg border border-accent/40 bg-accent/10 px-3 py-1.5 text-xs font-medium text-accent hover:bg-accent/20 hover:border-accent inline-flex items-center gap-1.5 transition-colors cursor-pointer shadow-xs"
                          title="Open the full interactive Composer studio"
                        >
                          <Cpu className="h-3.5 w-3.5 text-accent" />
                          Build circuit in Composer
                          <ExternalLink className="h-3 w-3 opacity-80" />
                        </Link>
                      );
                    }
                    return (
                      <button
                        key={key}
                        type="button"
                        onClick={() => setDemoKey(key)}
                        className={cn(
                          "rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors inline-flex items-center gap-1.5 cursor-pointer",
                          demoKeyNow === key
                            ? "border-accent bg-accent/15 text-accent font-semibold"
                            : "border-line bg-subtle text-ink-2 hover:bg-hover",
                        )}
                      >
                        {DEMOS[key]?.title ?? key}
                      </button>
                    );
                  })}
                </div>

                {activeDemo && (
                  <div className="pt-2 border-t border-line-soft">
                    <p className="mb-4 text-xs text-ink-3 italic">{activeDemo.blurb}</p>
                    <div className="overflow-x-auto">
                      <activeDemo.Component />
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Bottom Actions & Prev/Next Navigation */}
            <div className="mt-12 pt-6 border-t border-line space-y-6">
              {chosenLesson && (
                <div className="flex items-center justify-between">
                  <Button
                    variant={completedLessons[chosenLesson.slug] ? "secondary" : "primary"}
                    size="md"
                    onClick={() => toggleComplete(chosenLesson.slug)}
                    className="gap-2"
                  >
                    <CheckCircle2 className="h-4 w-4" />
                    {completedLessons[chosenLesson.slug] ? "Completed (Click to undo)" : "Mark as Complete"}
                  </Button>
                </div>
              )}

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {prevLesson ? (
                  <button
                    onClick={() => selectLesson(prevLesson.slug)}
                    className="flex flex-col items-start p-4 rounded-xl border border-line bg-raised hover:bg-hover hover:border-line-focus/40 transition-colors text-left group"
                  >
                    <span className="flex items-center gap-1 text-xs text-ink-3 mb-1">
                      <ChevronLeft className="h-3.5 w-3.5 group-hover:-translate-x-0.5 transition-transform" />
                      Previous Lesson
                    </span>
                    <span className="text-sm font-medium text-ink line-clamp-1">{prevLesson.title}</span>
                  </button>
                ) : (
                  <div />
                )}

                {nextLesson && (
                  <button
                    onClick={() => selectLesson(nextLesson.slug)}
                    className="flex flex-col items-end p-4 rounded-xl border border-line bg-raised hover:bg-hover hover:border-line-focus/40 transition-colors text-right group"
                  >
                    <span className="flex items-center gap-1 text-xs text-ink-3 mb-1">
                      Next Lesson
                      <ChevronRight className="h-3.5 w-3.5 group-hover:translate-x-0.5 transition-transform" />
                    </span>
                    <span className="text-sm font-medium text-ink line-clamp-1">{nextLesson.title}</span>
                  </button>
                )}
              </div>
            </div>
          </div>
        </section>

        {/* COLUMN 3: AI Tutor Sidebar (320px) */}
        <aside
          className={cn(
            "w-full sm:w-[320px] xl:w-[340px] shrink-0 border-l border-line bg-raised flex flex-col min-h-0",
            mobileTab === "content" ? "hidden xl:flex" : "flex",
          )}
        >
          {/* AI Header */}
          <div className="p-4 border-b border-line-soft">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-accent" />
                <h3 className="text-sm font-semibold text-ink">AI Tutor</h3>
              </div>
              <Badge tone="accent" className="text-[10px]">Grounded</Badge>
            </div>
            {chosenLesson && (
              <p className="mt-1.5 text-xs text-ink-3 truncate" title={chosenLesson.title}>
                Scoped to: <span className="text-ink-2 font-medium">{chosenLesson.title}</span>
              </p>
            )}
          </div>

          {/* Chat Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3.5">
            {history.length === 0 && (
              <div className="text-center py-8 px-2 text-ink-3">
                <Bot className="h-8 w-8 mx-auto mb-2.5 text-ink-3/60" />
                <p className="text-xs leading-relaxed">
                  Have a question about this lesson? Ask the AI Tutor. Answers are grounded in the curriculum with direct citations.
                </p>
              </div>
            )}

            {history.map((turn, i) => (
              <div
                key={i}
                className={cn(
                  "flex flex-col max-w-[90%] text-xs leading-relaxed rounded-xl p-3 shadow-xs",
                  turn.role === "user"
                    ? "ml-auto bg-accent-soft text-accent-ink border border-accent/30"
                    : "mr-auto bg-subtle text-ink border border-line",
                )}
              >
                <span className="text-[10px] font-semibold text-ink-3 mb-1 uppercase tracking-wider">
                  {turn.role === "user" ? "You" : "AI Tutor"}
                </span>
                <Markdown>{turn.content}</Markdown>
              </div>
            ))}

            {chat.isPending && (
              <div className="flex items-center gap-2 text-xs text-ink-3 p-2 bg-subtle rounded-lg">
                <Spinner className="h-3.5 w-3.5" /> Reasoning with curriculum context…
              </div>
            )}

            {chat.data?.citations && chat.data.citations.length > 0 && (
              <div className="mt-2 rounded-lg border border-line bg-subtle/50 p-2.5">
                <span className="block text-[11px] font-semibold text-ink-3 uppercase tracking-wider mb-2">
                  Sources cited:
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {chat.data.citations.map((c, idx) => (
                    <button
                      key={idx}
                      onClick={() => selectLesson(c.lesson_slug)}
                      className="text-[11px] px-2 py-0.5 rounded-md border border-line bg-raised text-accent hover:underline text-left"
                    >
                      {getCitationTitle(c.lesson_slug)}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {chat.isError && <ErrorNote className="text-xs">{String(chat.error)}</ErrorNote>}
          </div>

          {/* AI Input Area */}
          <div className="p-3 border-t border-line-soft bg-raised">
            <div className="relative">
              <Textarea
                rows={2}
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    ask();
                  }
                }}
                placeholder={chosenLesson ? `Ask about ${chosenLesson.title}...` : "Ask a quantum question..."}
                className="text-xs p-2.5 pr-10 resize-none"
              />
              <button
                type="button"
                onClick={ask}
                disabled={!question.trim() || chat.isPending}
                className="absolute right-2.5 bottom-2.5 flex items-center justify-center h-7 w-7 rounded-lg bg-accent text-white hover:bg-accent/90 disabled:bg-accent/40 disabled:text-white/70 disabled:cursor-not-allowed transition-all shadow-sm cursor-pointer"
                title="Send message (Enter)"
              >
                {chat.isPending ? (
                  <Spinner className="h-3.5 w-3.5 text-white" />
                ) : (
                  <Send className="h-3.5 w-3.5 text-white stroke-[2.25]" />
                )}
              </button>
            </div>
            <p className="mt-1.5 text-[10px] text-ink-3 text-center">
              Chat resets when you switch lessons
            </p>
          </div>
        </aside>
      </div>
    </div>
  );
}
