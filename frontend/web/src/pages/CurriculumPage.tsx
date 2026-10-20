import { Link } from "react-router-dom";
import { ArrowRight, BookOpen, Compass } from "lucide-react";

import { Button, Card, ErrorNote, Spinner } from "../components/ui";
import { CurriculumBrowser } from "../components/curriculum/CurriculumBrowser";
import { useCurriculum, useNextTopics } from "../api/curriculum";
import { useSession } from "../state/session";

export function CurriculumPage() {
  const { data, isLoading, error, refetch } = useCurriculum();
  const next = useNextTopics();
  const token = useSession((s) => s.token);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-12 text-ink-3 text-sm">
        <Spinner className="mr-2" />
        <span role="status">Loading curriculum topics…</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col gap-4 p-8 max-w-2xl mx-auto">
        <ErrorNote>
          Could not load curriculum data: {error instanceof Error ? error.message : "Unknown error"}
        </ErrorNote>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => void refetch()}
          className="self-start"
        >
          Try again
        </Button>
      </div>
    );
  }

  const sections = data?.sections ?? [];

  if (sections.length === 0) {
    return (
      <div className="p-8 max-w-2xl mx-auto">
        <ErrorNote>The curriculum is currently empty. No topics published yet.</ErrorNote>
      </div>
    );
  }

  const totalTopics = data?.progress.topics_total ?? 0;
  const completed = data?.progress.topics_completed ?? 0;
  const percent = data?.progress.percent ?? 0;

  const resume = next.data?.find((n) => n.lesson_slug) ?? null;

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6 p-6">
      <header className="flex flex-col gap-2 border-b border-line pb-4">
        <h1 className="text-2xl font-bold tracking-tight text-ink flex items-center gap-2.5">
          <Compass className="h-6 w-6 text-accent" /> Structured Quantum Curriculum
        </h1>
        <p className="max-w-2xl text-sm leading-relaxed text-ink-3">
          A pedagogical sequence through quantum theory, linear algebra, circuit synthesis, and algorithmic speedups. Each topic builds cleanly on its verified prerequisites.
        </p>
      </header>

      {/* Progress & Quick Resume Card */}
      <Card className="p-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex flex-col gap-2 min-w-0 flex-1">
            <span className="text-[11px] font-bold uppercase tracking-wider text-ink-3">
              Curriculum Progress
            </span>
            {token ? (
              <div className="space-y-2">
                <p className="text-sm font-semibold text-ink">
                  {completed} of {totalTopics} topics completed ({percent}%)
                </p>
                {/* Visual Progress Bar */}
                <div className="h-2 w-full max-w-md overflow-hidden rounded-full bg-subtle border border-line-soft">
                  <div
                    className="h-full bg-accent transition-all duration-300"
                    style={{ width: `${percent}%` }}
                  />
                </div>
              </div>
            ) : (
              <p className="text-xs text-ink-3">
                Sign in to persist your progress and track mastery across devices.
              </p>
            )}
          </div>

          {resume ? (
            <Link
              to={`/learn?lesson=${encodeURIComponent(resume.lesson_slug as string)}`}
              className="inline-flex h-9 items-center gap-2 rounded-lg bg-accent px-4 text-xs font-semibold text-accent-ink hover:opacity-90 shadow-sm transition-all"
            >
              <BookOpen size={14} aria-hidden="true" />
              {completed > 0 ? "Resume Learning" : "Start Learning"}
              <ArrowRight size={14} aria-hidden="true" />
            </Link>
          ) : (
            next.error && (
              <span className="text-xs text-ink-3">Next topic suggestion queued</span>
            )
          )}
        </div>

        {resume && (
          <p className="text-xs text-ink-3 mt-3 pt-3 border-t border-line-soft">
            Recommended next step:{" "}
            <Link
              to={`/curriculum/topic/${encodeURIComponent(resume.slug)}`}
              className="text-accent font-medium hover:underline"
            >
              {resume.title}
            </Link>
          </p>
        )}
      </Card>

      <CurriculumBrowser sections={sections} />
    </div>
  );
}
