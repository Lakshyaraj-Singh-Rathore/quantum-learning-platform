import { api } from "./client";

/** Mirrors backend/app/api/dashboard.py. */

export interface MasteryRow {
  tag: string;
  score: number;
  [key: string]: unknown;
}

export interface Recommendation {
  kind: "lesson" | "quiz" | string;
  slug: string;
  title?: string;
  reason: string;
}

export interface LearnerProgress {
  user_id: number;
  quizzes_taken: number;
  challenges_attempted: number;
  challenges_passed: number;
  average_quiz_percentage: number;
  mastery: MasteryRow[];
  recommendations: Recommendation[];
}

export interface InstructorOverview {
  total_students: number;
  total_jobs: number;
  quiz_completion: Record<string, unknown>[];
  challenge_completion: Record<string, unknown>[];
  common_errors: Record<string, unknown>[];
  weakest_tags: Record<string, unknown>[];
  leaderboard: Record<string, unknown>[];
}

export interface StudentSummary {
  id: number;
  email: string;
  display_name: string | null;
  [key: string]: unknown;
}

export function myProgress(): Promise<LearnerProgress> {
  return api.get<LearnerProgress>("/dashboard/me");
}

export function instructorOverview(): Promise<InstructorOverview> {
  return api.get<InstructorOverview>("/dashboard/instructor");
}

export function listStudents(): Promise<StudentSummary[]> {
  return api.get<StudentSummary[]>("/dashboard/students");
}

export function studentDetail(studentId: number): Promise<LearnerProgress> {
  return api.get<LearnerProgress>(`/dashboard/students/${studentId}`);
}
