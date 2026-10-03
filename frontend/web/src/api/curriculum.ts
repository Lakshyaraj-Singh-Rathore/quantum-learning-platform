import { useQuery } from "@tanstack/react-query";

import { api } from "./client";

/** Types mirroring the real payloads of GET /curriculum,
 *  GET /curriculum/topics/{id} and GET /curriculum/next.
 *
 *  These were written against captured responses, not inferred from the
 *  backend source, so they can drift. If a field is absent at runtime the UI
 *  falls back to a neutral state rather than rendering a fabricated value. */

export type Difficulty = "beginner" | "intermediate" | "advanced";
export type PrereqKind = "required" | "recommended";

export interface CurriculumPrerequisite {
  slug: string;
  kind: PrereqKind;
}

/** The backend's decision. The frontend presents it; it does not re-derive it. */
export interface TopicStatus {
  ready: boolean;
  missing_required: string[];
  missing_recommended: string[];
  advisory: boolean;
  /** True for anonymous callers: edges are shown, but nothing is gated. */
  unevaluated?: boolean;
}

export interface CurriculumLesson {
  slug: string;
  title: string;
  track: string;
  position: number;
  is_primary: boolean;
  confidence: string;
}

export interface CurriculumTopic {
  slug: string;
  title: string;
  position: number;
  difficulty: Difficulty;
  summary: string;
  objectives: string[];
  /** 0..1, from verified or mapped mastery only. Not invented. */
  mastery: number;
  attempts: number;
  completed: boolean;
  prerequisites: CurriculumPrerequisite[];
  status: TopicStatus;
  lessons: CurriculumLesson[];
}

export interface CurriculumSection {
  slug: string;
  title: string;
  position: number;
  topics: CurriculumTopic[];
}

export interface CurriculumProgress {
  topics_total: number;
  topics_completed: number;
  percent: number;
}

export interface Curriculum {
  sections: CurriculumSection[];
  progress: CurriculumProgress;
}

export interface TopicDetail {
  slug: string;
  title: string;
  section_slug: string;
  difficulty: Difficulty;
  summary: string;
  objectives: string[];
  prerequisites: CurriculumPrerequisite[];
  status: TopicStatus;
  mastery: number;
  lessons: CurriculumLesson[];
}

export interface NextTopic {
  slug: string;
  title: string;
  section: string;
  difficulty: Difficulty;
  missing_required: string[];
  /** Null when the topic has no lesson yet. */
  lesson_slug: string | null;
}

const curriculumKey = ["curriculum"] as const;
const topicKey = (slug: string) => ["curriculum", "topic", slug] as const;
const nextKey = ["curriculum", "next"] as const;

export function fetchCurriculum(): Promise<Curriculum> {
  return api.get<Curriculum>("/curriculum");
}

export function fetchTopic(slug: string): Promise<TopicDetail> {
  return api.get<TopicDetail>(`/curriculum/topics/${encodeURIComponent(slug)}`);
}

export function fetchNext(): Promise<NextTopic[]> {
  return api.get<NextTopic[]>("/curriculum/next");
}

/** The whole tree is one request, so it is cached and shared. Auth is handled
 *  by the shared client: an anonymous caller simply gets zeroed progress. */
export function useCurriculum() {
  return useQuery({
    queryKey: curriculumKey,
    queryFn: fetchCurriculum,
    staleTime: 60_000,
  });
}

export function useTopic(slug: string | undefined) {
  return useQuery({
    queryKey: topicKey(slug ?? ""),
    queryFn: () => fetchTopic(slug as string),
    enabled: Boolean(slug),
    staleTime: 60_000,
  });
}

/** Kept separate from the tree: a failure here must not blank the curriculum,
 *  so it is never allowed to reject into the page's error state. */
export function useNextTopics() {
  return useQuery({
    queryKey: nextKey,
    queryFn: fetchNext,
    staleTime: 60_000,
    retry: 1,
  });
}
