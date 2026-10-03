import { Link, useParams } from "react-router-dom";
import { ArrowLeft, BookOpen, CheckCircle2, Lock } from "lucide-react";

import { Badge, Card, ErrorNote, Spinner, cn } from "../components/ui";
import { useTopic } from "../api/curriculum";
import type { Difficulty } from "../api/curriculum";

const DIFFICULTY_TONE: Record<Difficulty, "neutral" | "accent" | "warn"> = {
  beginner: "neutral",
  intermediate: "accent",
  advanced: "warn",
};

export function TopicDetailPage() {
  // Stable namespaced id, e.g. "nisq.vqe". Deep-linkable and shareable.
  const { topicId } = useParams<{ topicId: string }>();
  const { data: topic, isLoading, error } = useTopic(topicId);

  if (isLoading) {
    return (
      <div className="flex items-center gap-3 p-6 text-ink-2">
        <Spinner />
        <span role="status">Loading topic…</span>
      </div>
    );
  }

  if (error) {
    // A 404 is a wrong or stale link, not an outage: say so and offer a way out.
    const notFound = error instanceof Error && error.message.includes("Topic not found");
    return (
      <div className="flex flex-col gap-3 p-6">
        <ErrorNote>
          {notFound
            ? `There is no topic called “${topicId}”.`
            : `Could not load this topic. ${error instanceof Error ? error.message : ""}`}
        </ErrorNote>
        <Link
          to="/curriculum"
          className="self-start rounded-lg border border-line bg-raised px-3 py-1.5 text-[13px] text-ink hover:bg-hover"
        >
          Back to curriculum
        </Link>
      </div>
    );
  }

  if (!topic) return null;

  const blocked = !topic.status.ready;
  const evaluated = !topic.status.unevaluated;
  const required = topic.prerequisites.filter((p) => p.kind === "required");
  const recommended = topic.prerequisites.filter((p) => p.kind === "recommended");

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-5 p-6">
      <Link
        to="/curriculum"
        className="inline-flex items-center gap-1.5 self-start text-[13px] text-ink-2 hover:text-ink"
      >
        <ArrowLeft size={14} aria-hidden="true" />
        Back to curriculum
      </Link>

      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h1 className="text-xl font-semibold text-ink">{topic.title}</h1>
          <p className="mt-0.5 font-mono text-[11px] text-ink-3">{topic.slug}</p>
        </div>
        <Badge tone={DIFFICULTY_TONE[topic.difficulty] ?? "neutral"}>
          {topic.difficulty}
        </Badge>
      </header>

      {topic.summary && (
        <p className="text-[13px] leading-relaxed text-ink-2">{topic.summary}</p>
      )}

      {blocked && evaluated && topic.status.missing_required.length > 0 && (
        <div className="flex flex-col gap-2 rounded-xl border border-warn/40 bg-warn/5 p-4">
          <p className="flex items-center gap-2 text-[13px] font-medium text-ink">
            <Lock size={15} aria-hidden="true" className="text-warn" />
            This topic builds on material you have not covered yet
          </p>
          <p className="text-[12px] leading-relaxed text-ink-2">
            The lesson assumes you already understand the topic below. You can
            still read ahead, but the explanations will reference it without
            re-teaching it.
          </p>
          <ul className="flex flex-wrap gap-1.5">
            {topic.status.missing_required.map((slug) => (
              <li key={slug}>
                <Link
                  to={`/curriculum/topic/${encodeURIComponent(slug)}`}
                  className="inline-flex items-center gap-1.5 rounded-full border border-warn/40 px-2.5 py-0.5 text-[12px] text-warn hover:bg-warn/10"
                >
                  {slug}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      )}

      {!blocked && topic.status.advisory && topic.status.missing_recommended.length > 0 && (
        <p className="rounded-xl border border-line bg-hover p-4 text-[12px] leading-relaxed text-ink-3">
          Recommended background: {topic.status.missing_recommended.join(", ")}.
          Helpful, but not required — you can start this now.
        </p>
      )}

      {topic.objectives.length > 0 && (
        <Card className="flex flex-col gap-2">
          <h2 className="text-[13px] font-semibold text-ink">Learning objectives</h2>
          <ul className="flex flex-col gap-1.5">
            {topic.objectives.map((objective) => (
              <li
                key={objective}
                className="flex items-start gap-2 text-[13px] leading-relaxed text-ink-2"
              >
                <CheckCircle2
                  size={14}
                  aria-hidden="true"
                  className="mt-0.5 shrink-0 text-accent"
                />
                {objective}
              </li>
            ))}
          </ul>
        </Card>
      )}

      {(required.length > 0 || recommended.length > 0) && (
        <Card className="flex flex-col gap-3">
          <h2 className="text-[13px] font-semibold text-ink">Prerequisites</h2>
          {required.length > 0 && (
            <div className="flex flex-col gap-1.5">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-ink-3">
                Required
              </p>
              <ul className="flex flex-wrap gap-1.5">
                {required.map((p) => (
                  <li key={p.slug}>
                    <Link
                      to={`/curriculum/topic/${encodeURIComponent(p.slug)}`}
                      className="inline-flex items-center gap-1.5 rounded-full border border-warn/40 px-2.5 py-0.5 text-[12px] text-warn hover:bg-warn/10"
                    >
                      {p.slug}
                      <span className="sr-only"> (required)</span>
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {recommended.length > 0 && (
            <div className="flex flex-col gap-1.5">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-ink-3">
                Recommended
              </p>
              <ul className="flex flex-wrap gap-1.5">
                {recommended.map((p) => (
                  <li key={p.slug}>
                    <Link
                      to={`/curriculum/topic/${encodeURIComponent(p.slug)}`}
                      className="inline-flex items-center gap-1.5 rounded-full border border-line px-2.5 py-0.5 text-[12px] text-ink-2 hover:bg-hover"
                    >
                      {p.slug}
                      <span className="sr-only"> (recommended, not required)</span>
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </Card>
      )}

      <Card className="flex flex-col gap-3">
        <h2 className="text-[13px] font-semibold text-ink">Lessons</h2>
        {topic.lessons.length === 0 ? (
          <p className="text-[13px] text-ink-3">
            Lessons for this topic are not written yet. This topic is part of
            the planned curriculum.
          </p>
        ) : (
          <ol className="flex flex-col gap-2">
            {topic.lessons.map((lesson, index) => (
              <li key={lesson.slug}>
                <Link
                  to={`/learn?lesson=${encodeURIComponent(lesson.slug)}`}
                  className={cn(
                    "flex items-center justify-between gap-3 rounded-lg border border-line bg-raised px-3.5 py-2.5 transition-colors hover:bg-hover focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent",
                  )}
                >
                  <span className="flex min-w-0 items-center gap-3">
                    <span className="w-5 shrink-0 text-[12px] text-ink-3">
                      {index + 1}
                    </span>
                    <span className="truncate text-[13px] text-ink">
                      {lesson.title}
                    </span>
                  </span>
                  <span className="flex shrink-0 items-center gap-2">
                    <Badge tone={lesson.track === "circuit" ? "accent" : "neutral"}>
                      {lesson.track}
                    </Badge>
                    <BookOpen size={14} aria-hidden="true" className="text-ink-3" />
                  </span>
                </Link>
              </li>
            ))}
          </ol>
        )}
      </Card>

    </div>
  );
}
