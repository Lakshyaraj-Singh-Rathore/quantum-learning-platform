import { Link, useParams } from "react-router-dom";
import { ArrowLeft, CheckCircle2, Lock, ArrowRight, Play } from "lucide-react";

import { Badge, Button, Card, ErrorNote, Spinner, cn } from "../components/ui";
import { useTopic, useCurriculum } from "../api/curriculum";
import type { Difficulty } from "../api/curriculum";

const DIFFICULTY_TONE: Record<Difficulty, "neutral" | "accent" | "warn"> = {
  beginner: "neutral",
  intermediate: "accent",
  advanced: "warn",
};

export function TopicDetailPage() {
  const { topicId } = useParams<{ topicId: string }>();
  const { data: topic, isLoading, error } = useTopic(topicId);
  const { data: curriculum } = useCurriculum();

  // Completed lessons from local storage
  const completedLessons: Record<string, boolean> = (() => {
    try {
      const stored = localStorage.getItem("ql_completed_lessons");
      return stored ? JSON.parse(stored) : {};
    } catch {
      return {};
    }
  })();

  // Map slug to human-readable title
  const getTopicTitle = (slug: string) => {
    if (!curriculum) return slug;
    for (const sec of curriculum.sections) {
      const found = sec.topics.find((t) => t.slug === slug);
      if (found) return found.title;
    }
    return slug;
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-12 text-ink-3 text-sm">
        <Spinner className="mr-2" />
        <span role="status">Loading topic specification…</span>
      </div>
    );
  }

  if (error) {
    const notFound = error instanceof Error && error.message.includes("Topic not found");
    return (
      <div className="flex flex-col gap-4 p-8 max-w-2xl mx-auto">
        <ErrorNote>
          {notFound
            ? `There is no curriculum topic registered under “${topicId}”.`
            : `Could not load topic details: ${error instanceof Error ? error.message : ""}`}
        </ErrorNote>
        <Link to="/curriculum">
          <Button variant="secondary" size="sm" className="gap-2">
            <ArrowLeft className="h-4 w-4" /> Back to Curriculum
          </Button>
        </Link>
      </div>
    );
  }

  if (!topic) return null;

  const blocked = !topic.status.ready;
  const evaluated = !topic.status.unevaluated;
  const required = topic.prerequisites.filter((p) => p.kind === "required");
  const recommended = topic.prerequisites.filter((p) => p.kind === "recommended");
  const firstLesson = topic.lessons[0] ?? null;

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-6 p-6">
      {/* Top Nav & CTA Row */}
      <div className="flex items-center justify-between border-b border-line pb-4">
        <Link to="/curriculum">
          <Button variant="ghost" size="sm" className="gap-2 text-ink-2 hover:text-ink">
            <ArrowLeft className="h-4 w-4" /> Back to Curriculum
          </Button>
        </Link>

        {firstLesson && (
          <Link to={`/learn?lesson=${encodeURIComponent(firstLesson.slug)}`}>
            <Button variant="primary" size="md" className="gap-2 shadow-sm font-semibold">
              <Play className="h-4 w-4" /> Start Learning ({firstLesson.title})
            </Button>
          </Link>
        )}
      </div>

      {/* Header Info */}
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <h1 className="text-3xl font-extrabold tracking-tight text-ink">{topic.title}</h1>
          <p className="mt-1 font-mono text-xs text-ink-3">{topic.slug}</p>
        </div>
        <Badge tone={DIFFICULTY_TONE[topic.difficulty] ?? "neutral"} className="text-xs px-3 py-1">
          {topic.difficulty} level
        </Badge>
      </header>

      {topic.summary && (
        <p className="text-sm leading-relaxed text-ink-2 bg-raised/50 p-4 rounded-xl border border-line-soft">
          {topic.summary}
        </p>
      )}

      {/* Prerequisites Warning if blocked */}
      {blocked && evaluated && topic.status.missing_required.length > 0 && (
        <div className="flex flex-col gap-3 rounded-xl border border-warn/40 bg-warn/10 p-5">
          <div className="flex items-center gap-2 text-sm font-semibold text-ink">
            <Lock size={16} className="text-warn" />
            <span>This topic requires previous conceptual foundation</span>
          </div>
          <p className="text-xs leading-relaxed text-ink-2">
            The mathematical descriptions assume prior familiarity with the topics below:
          </p>
          <div className="flex flex-wrap gap-2 pt-1">
            {topic.status.missing_required.map((slug) => (
              <Link
                key={slug}
                to={`/curriculum/topic/${encodeURIComponent(slug)}`}
                className="inline-flex items-center gap-1.5 rounded-lg border border-warn/40 bg-raised px-3 py-1 text-xs font-medium text-warn hover:bg-warn/15 transition-colors"
              >
                {getTopicTitle(slug)}
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Objectives */}
      {topic.objectives.length > 0 && (
        <Card className="p-6">
          <h2 className="text-sm font-bold uppercase tracking-wider text-ink mb-3">
            Learning Objectives
          </h2>
          <ul className="space-y-2">
            {topic.objectives.map((objective) => (
              <li key={objective} className="flex items-start gap-2.5 text-xs leading-relaxed text-ink-2">
                <CheckCircle2 size={15} className="mt-0.5 shrink-0 text-accent" />
                <span>{objective}</span>
              </li>
            ))}
          </ul>
        </Card>
      )}

      {/* Prerequisites Cards */}
      {(required.length > 0 || recommended.length > 0) && (
        <Card className="p-6 space-y-4">
          <h2 className="text-sm font-bold uppercase tracking-wider text-ink">Prerequisites</h2>
          {required.length > 0 && (
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-wider text-warn mb-2">
                Required Prior Understanding
              </p>
              <div className="flex flex-wrap gap-2">
                {required.map((p) => (
                  <Link
                    key={p.slug}
                    to={`/curriculum/topic/${encodeURIComponent(p.slug)}`}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-line bg-subtle px-3 py-1.5 text-xs text-ink hover:bg-hover hover:border-line-focus transition-colors"
                  >
                    {getTopicTitle(p.slug)}
                  </Link>
                ))}
              </div>
            </div>
          )}
          {recommended.length > 0 && (
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-wider text-ink-3 mb-2">
                Recommended Background
              </p>
              <div className="flex flex-wrap gap-2">
                {recommended.map((p) => (
                  <Link
                    key={p.slug}
                    to={`/curriculum/topic/${encodeURIComponent(p.slug)}`}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-line bg-subtle px-3 py-1.5 text-xs text-ink-2 hover:bg-hover hover:text-ink transition-colors"
                  >
                    {getTopicTitle(p.slug)}
                  </Link>
                ))}
              </div>
            </div>
          )}
        </Card>
      )}

      {/* Topic Lessons List */}
      <Card className="p-6">
        <h2 className="text-sm font-bold uppercase tracking-wider text-ink mb-4">
          Associated Topic Lessons
        </h2>
        {topic.lessons.length === 0 ? (
          <p className="text-xs text-ink-3">
            Lessons for this topic are being finalized in the curriculum repository.
          </p>
        ) : (
          <div className="space-y-2">
            {topic.lessons.map((lesson, index) => {
              const isDone = completedLessons[lesson.slug];
              return (
                <Link
                  key={lesson.slug}
                  to={`/learn?lesson=${encodeURIComponent(lesson.slug)}`}
                  className={cn(
                    "flex items-center justify-between gap-3 rounded-xl border border-line bg-raised p-3.5 transition-all hover:bg-hover hover:border-line-focus/40 group",
                  )}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-subtle font-mono text-xs text-ink-3">
                      {index + 1}
                    </span>
                    <span className="font-medium text-xs sm:text-sm text-ink truncate group-hover:text-accent transition-colors">
                      {lesson.title}
                    </span>
                  </div>

                  <div className="flex items-center gap-2.5 shrink-0">
                    {isDone && (
                      <Badge tone="ok" className="gap-1 text-[11px]">
                        <CheckCircle2 className="h-3 w-3" /> Done
                      </Badge>
                    )}
                    <Badge tone={lesson.track === "circuit" ? "accent" : "neutral"} className="text-xs">
                      {lesson.track === "circuit" ? "Circuit" : "Theory"}
                    </Badge>
                    <ArrowRight className="h-4 w-4 text-ink-3 group-hover:translate-x-0.5 transition-transform" />
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </Card>
    </div>
  );
}
