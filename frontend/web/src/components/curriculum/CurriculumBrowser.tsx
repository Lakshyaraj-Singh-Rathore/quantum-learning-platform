import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { BookOpen, CheckCircle2, ChevronDown, Circle, Lock, Sparkles } from "lucide-react";

import { Badge, Card, cn } from "../ui";
import type {
  CurriculumSection,
  CurriculumTopic,
  Difficulty,
  PrereqKind,
} from "../../api/curriculum";

/** Presentational layer for the curriculum tree. Every state shown here comes
 *  from the backend: nothing is inferred, and an absent value renders as a
 *  neutral placeholder rather than a guess. */

const DIFFICULTY_TONE: Record<Difficulty, "neutral" | "accent" | "warn"> = {
  beginner: "neutral",
  intermediate: "accent",
  advanced: "warn",
};

/** Where a topic stands, derived only from fields the backend returned. */
export type TopicState = "completed" | "available" | "blocked" | "not-started";

export function topicState(topic: CurriculumTopic): TopicState {
  if (topic.completed) return "completed";
  if (!topic.status.ready) return "blocked";
  if (topic.mastery > 0) return "available";
  return "not-started";
}

const STATE_LABEL: Record<TopicState, string> = {
  completed: "Completed",
  available: "In progress",
  blocked: "Prerequisites needed",
  "not-started": "Not started",
};

/** Icon + text, never colour alone: completion must survive colour blindness
 *  and greyscale. */
export function StateIndicator({ state }: { state: TopicState }) {
  const Icon =
    state === "completed"
      ? CheckCircle2
      : state === "blocked"
        ? Lock
        : state === "available"
          ? Sparkles
          : Circle;
  return (
    <span className="inline-flex items-center gap-1.5 text-[12px] text-ink-2">
      <Icon
        size={14}
        aria-hidden="true"
        className={cn(
          state === "completed" && "text-accent",
          state === "blocked" && "text-warn",
        )}
      />
      {STATE_LABEL[state]}
    </span>
  );
}

export function PrereqList({
  prerequisites,
  topicTitleById,
  satisfied,
}: {
  prerequisites: { slug: string; kind: PrereqKind }[];
  topicTitleById: Record<string, string>;
  /** Undefined when the backend did not evaluate (anonymous caller). */
  satisfied?: (slug: string) => boolean;
}) {
  if (prerequisites.length === 0) return null;
  const required = prerequisites.filter((p) => p.kind === "required");
  const recommended = prerequisites.filter((p) => p.kind === "recommended");

  const render = (list: typeof prerequisites, kind: PrereqKind) => (
    <div className="flex flex-col gap-1">
      <p className="text-[11px] font-semibold uppercase tracking-wide text-ink-3">
        {kind === "required" ? "Required before this" : "Recommended before this"}
      </p>
      <ul className="flex flex-wrap gap-1.5">
        {list.map((p) => {
          const met = satisfied ? satisfied(p.slug) : undefined;
          return (
            <li key={p.slug}>
              <Link
                to={`/curriculum/topic/${encodeURIComponent(p.slug)}`}
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[12px] transition-colors",
                  p.kind === "required"
                    ? "border-warn/40 text-warn hover:bg-warn/10"
                    : "border-line text-ink-2 hover:bg-hover",
                )}
              >
                {met === true && <CheckCircle2 size={12} aria-hidden="true" />}
                {topicTitleById[p.slug] ?? p.slug}
                <span className="sr-only">
                  {kind === "required" ? " (required)" : " (recommended)"}
                </span>
              </Link>
            </li>
          );
        })}
      </ul>
    </div>
  );

  return (
    <div className="flex flex-col gap-2">
      {required.length > 0 && render(required, "required")}
      {recommended.length > 0 && render(recommended, "recommended")}
    </div>
  );
}

function TopicCard({
  topic,
  topicTitleById,
}: {
  topic: CurriculumTopic;
  topicTitleById: Record<string, string>;
}) {
  const state = topicState(topic);
  const firstLesson = topic.lessons[0];
  const blocked = state === "blocked";

  return (
    <Card className="flex flex-col gap-3 p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <h4 className="text-[15px] font-semibold text-ink">{topic.title}</h4>
          <p className="mt-0.5 font-mono text-[11px] text-ink-3">{topic.slug}</p>
        </div>
        <Badge tone={DIFFICULTY_TONE[topic.difficulty] ?? "neutral"}>
          {topic.difficulty}
        </Badge>
      </div>

      {topic.summary && (
        <p className="text-[13px] leading-relaxed text-ink-2">{topic.summary}</p>
      )}

      <div className="flex flex-wrap items-center gap-3">
        <StateIndicator state={state} />
        <span className="text-[12px] text-ink-3">
          {topic.lessons.length} {topic.lessons.length === 1 ? "lesson" : "lessons"}
        </span>
        <Link
          to={`/curriculum/topic/${encodeURIComponent(topic.slug)}`}
          className="text-[12px] text-accent underline-offset-2 hover:underline"
        >
          Details
        </Link>
      </div>

      {blocked && topic.status.missing_required.length > 0 && (
        <p className="rounded-lg border border-warn/30 bg-warn/5 px-3 py-2 text-[12px] leading-relaxed text-ink-2">
          Complete{" "}
          {topic.status.missing_required.map((slug, i) => (
            <span key={slug}>
              {i > 0 && ", "}
              <Link
                to={`/curriculum/topic/${encodeURIComponent(slug)}`}
                className="text-warn underline underline-offset-2"
              >
                {topicTitleById[slug] ?? slug}
              </Link>
            </span>
          ))}{" "}
          first — this topic builds on it, so the material assumes you already
          know it.
        </p>
      )}

      {/* Declared edges, always shown when present: a learner should see the
          dependency even when it is already satisfied. */}
      {topic.prerequisites.length > 0 && (
        <PrereqList
          prerequisites={topic.prerequisites}
          topicTitleById={topicTitleById}
          satisfied={
            topic.status.unevaluated
              ? undefined
              : (slug) =>
                  !topic.status.missing_required.includes(slug) &&
                  !topic.status.missing_recommended.includes(slug)
          }
        />
      )}

      {!blocked && topic.status.advisory && (
        <p className="rounded-lg border border-line bg-hover px-3 py-2 text-[12px] leading-relaxed text-ink-3">
          Helpful but not required:{" "}
          {topic.status.missing_recommended
            .map((s) => topicTitleById[s] ?? s)
            .join(", ")}
          . You can start this now.
        </p>
      )}

      {topic.lessons.length === 0 ? (
        <p className="text-[12px] text-ink-3">
          Lessons for this topic are not written yet.
        </p>
      ) : (
        <Link
          to={`/learn?lesson=${encodeURIComponent(firstLesson.slug)}`}
          title={firstLesson.title}
          className="inline-flex h-8 items-center justify-center gap-2 self-start rounded-lg border border-line bg-raised px-3 text-[13px] font-medium text-ink transition-colors hover:bg-hover focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
        >
          <BookOpen size={14} aria-hidden="true" />
          {state === "completed" ? "Review lesson" : "Start lesson"}
        </Link>
      )}
    </Card>
  );
}

export function CurriculumBrowser({ sections }: { sections: CurriculumSection[] }) {
  const topicTitleById = useMemo(() => {
    const map: Record<string, string> = {};
    for (const section of sections) {
      for (const topic of section.topics) map[topic.slug] = topic.title;
    }
    return map;
  }, [sections]);

  // First section with content starts open so the page is never a wall of
  // collapsed headings. Later sections default closed.
  const [open, setOpen] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(sections.map((s, i) => [s.slug, i === 0])),
  );

  const toggle = (slug: string) => setOpen((prev) => ({ ...prev, [slug]: !prev[slug] }));

  return (
    <div className="flex flex-col gap-4">
      {sections.map((section) => {
        const expanded = open[section.slug] ?? false;
        const panelId = `section-panel-${section.slug}`;
        const done = section.topics.filter((t) => t.completed).length;

        return (
          <section key={section.slug} className="rounded-xl border border-line bg-raised">
            <h3>
              <button
                type="button"
                onClick={() => toggle(section.slug)}
                aria-expanded={expanded}
                aria-controls={panelId}
                className="flex w-full items-center gap-3 rounded-xl px-5 py-4 text-left transition-colors hover:bg-hover focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
              >
                <ChevronDown
                  size={18}
                  aria-hidden="true"
                  className={cn(
                    "shrink-0 text-ink-3 transition-transform",
                    expanded && "rotate-180",
                  )}
                />
                <span className="min-w-0 flex-1">
                  <span className="block text-[15px] font-semibold text-ink">
                    {section.title}
                  </span>
                  <span className="mt-0.5 block text-[12px] text-ink-3">
                    {section.topics.length}{" "}
                    {section.topics.length === 1 ? "topic" : "topics"}
                    {done > 0 ? ` · ${done} completed` : ""}
                  </span>
                </span>
              </button>
            </h3>

            <div
              id={panelId}
              hidden={!expanded}
              className="flex flex-col gap-3 border-t border-line px-5 py-4"
            >
              {section.topics.length === 0 ? (
                <p className="text-[13px] text-ink-3">
                  No topics in this section yet.
                </p>
              ) : (
                section.topics.map((topic) => (
                  <TopicCard
                    key={topic.slug}
                    topic={topic}
                    topicTitleById={topicTitleById}
                  />
                ))
              )}
            </div>
          </section>
        );
      })}
    </div>
  );
}
