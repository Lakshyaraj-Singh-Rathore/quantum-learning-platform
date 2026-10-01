import { api } from "./client";

/** Mirrors the lesson/quiz/tutor endpoints in backend/app/api. */

export interface LessonSummary {
  slug: string;
  title: string;
  tags: string[];
  order_index: number;
  /** "theory" | "circuit" — the two tracks the curriculum is split into. */
  track: string;
}

export interface LessonDetail {
  slug: string;
  title: string;
  tags: string[];
  /** Raw markdown, with the ingester's `<!-- track: … -->` marker stripped. */
  content: string;
}

export interface QuizQuestion {
  id: number;
  prompt: string;
  qtype: string;
  options: string[];
  tags: string[];
}

export interface Quiz {
  id: number;
  slug: string;
  title: string;
  tags: string[];
  questions: QuizQuestion[];
}

export interface QuizFeedback {
  question_id: number;
  prompt: string;
  your_answer: string;
  correct_answer: string;
  correct: boolean;
  explanation: string | null;
}

export interface QuizResult {
  score: number;
  max_score: number;
  percentage: number;
  feedback: QuizFeedback[];
}

export interface ChatCitation {
  lesson_slug: string;
  text: string;
}

export interface ChatReply {
  reply: string;
  citations: ChatCitation[];
  tools_used: string[];
}

export function listLessons(): Promise<LessonSummary[]> {
  return api.get<LessonSummary[]>("/lessons");
}

export function getLesson(slug: string): Promise<LessonDetail> {
  return api.get<LessonDetail>(`/lessons/${encodeURIComponent(slug)}`);
}

export function listQuizzes(): Promise<Quiz[]> {
  return api.get<Quiz[]>("/quizzes");
}

export function submitQuiz(slug: string, answers: Record<string, string>): Promise<QuizResult> {
  return api.post<QuizResult>(`/quizzes/${encodeURIComponent(slug)}/submit`, { answers });
}

export interface ChatTurn {
  role: "user" | "assistant";
  content: string;
}

/**
 * Grounded in the curriculum: the backend retrieves lesson chunks and passes
 * them to the model, so a reply is only as good as /content is.
 */
export function aiChat(
  message: string,
  history: ChatTurn[],
  circuitIr?: unknown,
  jobId?: number,
): Promise<ChatReply> {
  return api.post<ChatReply>("/ai/chat", {
    message,
    history,
    circuit_ir: circuitIr ?? null,
    job_id: jobId ?? null,
  });
}
