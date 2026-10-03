import { Link } from "react-router-dom";
import { AlertTriangle, ArrowRight, BookOpen } from "lucide-react";

import { Card, ErrorNote, Spinner } from "../components/ui";
import { CurriculumBrowser } from "../components/curriculum/CurriculumBrowser";
import { useCurriculum, useNextTopics } from "../api/curriculum";
import { useSession } from "../state/session";

export function CurriculumPage() {
  const { data, isLoading, error, refetch } = useCurriculum();
  // Deliberately non-blocking: if the recommendation call fails the curriculum
  // itself must still render. A failed /next is not a failed curriculum.
  const next = useNextTopics();
  const token = useSession((s) => s.token);

  if (isLoading) {
    return (
      <div className="flex items-center gap-3 p-6 text-ink-2">
        <Spinner />
        <span role="status">Loading curriculum…</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col gap-3 p-6">
        <ErrorNote>
          Could not load the curriculum.{" "}
          {error instanceof Error ? error.message : "Unknown error"}
        </ErrorNote>
        <button
          type="button"
          onClick={() => void refetch()}
          className="self-start rounded-lg border border-line bg-raised px-3 py-1.5 text-[13px] text-ink hover:bg-hover"
        >
          Try again
        </button>
      </div>
    );
  }

  const sections = data?.sections ?? [];

  if (sections.length === 0) {
    return (
      <div className="p-6">
        <ErrorNote>
          The curriculum is empty. No topics have been published yet.
        </ErrorNote>
      </div>
    );
  }

  // Derived, never hardcoded: counts come from the response.
  const totalTopics = data?.progress.topics_total ?? 0;
  const completed = data?.progress.topics_completed ?? 0;
  const percent = data?.progress.percent ?? 0;

  const resume = next.data?.find((n) => n.lesson_slug) ?? null;

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-6 p-6">
      <header className="flex flex-col gap-2">
        <h1 className="text-xl font-semibold text-ink">Curriculum</h1>
        <p className="max-w-2xl text-[13px] leading-relaxed text-ink-2">
          A guided path through quantum computing, ordered so each topic only
          assumes what comes before it. Work through it in sequence, or jump to
          any topic whose prerequisites you already have.
        </p>
      </header>

      <Card className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-col gap-1">
          <p className="text-[12px] font-semibold uppercase tracking-wide text-ink-3">
            Your progress
          </p>
          {token ? (
            <p className="text-[13px] text-ink-2">
              {completed} of {totalTopics} topics completed
              {percent > 0 ? ` · ${percent}%` : ""}
            </p>
          ) : (
            <p className="text-[13px] text-ink-3">
              Sign in to track your progress. You can browse everything now.
            </p>
          )}
        </div>

        {resume ? (
          <Link
            to={`/learn?lesson=${encodeURIComponent(resume.lesson_slug as string)}`}
            className="inline-flex h-9 items-center gap-2 rounded-lg bg-accent px-3.5 text-sm font-medium text-accent-ink transition-opacity hover:opacity-90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
          >
            <BookOpen size={15} aria-hidden="true" />
            {completed > 0 ? "Resume learning" : "Start learning"}
            <ArrowRight size={15} aria-hidden="true" />
          </Link>
        ) : (
          next.error && (
            <span className="inline-flex items-center gap-1.5 text-[12px] text-ink-3">
              <AlertTriangle size={13} aria-hidden="true" />
              Next-lesson suggestion unavailable
            </span>
          )
        )}
      </Card>

      {resume && (
        <p className="text-[12px] text-ink-3">
          Suggested next:{" "}
          <Link
            to={`/curriculum/topic/${encodeURIComponent(resume.slug)}`}
            className="text-accent underline-offset-2 hover:underline"
          >
            {resume.title}
          </Link>
        </p>
      )}

      <CurriculumBrowser sections={sections} />
    </div>
  );
}
