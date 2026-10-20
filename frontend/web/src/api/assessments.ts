import { api } from "./client";
import type { CircuitIR } from "@composer/types";

/** Mirrors the challenge endpoints in backend/app/api/assessments.py. */

export interface Challenge {
  id: number;
  slug: string;
  title: string;
  /** Markdown. */
  prompt: string;
  allowed_gates: string[];
  constraints: Record<string, unknown>;
  tags: string[];
  is_dynamic: boolean;
}

export interface ChallengeAttempt {
  attempt_id: number;
  job_id: number | null;
  /** "queued" | "running" | "graded" | "failed" — poll until it settles. */
  status: string;
  passed: boolean;
  score: number;
  feedback: string;
  details: Record<string, unknown>;
}

export function listChallenges(): Promise<Challenge[]> {
  return api.get<Challenge[]>("/challenges");
}

export function submitChallenge(
  slug: string,
  circuitIr: CircuitIR,
  shots = 1024,
): Promise<ChallengeAttempt> {
  return api.post<ChallengeAttempt>(`/challenges/${encodeURIComponent(slug)}/submit`, {
    circuit_ir: circuitIr,
    shots,
  });
}

export function getAttempt(attemptId: number): Promise<ChallengeAttempt> {
  return api.get<ChallengeAttempt>(`/attempts/${attemptId}`);
}

// ---------------------------------------------------------------------------
// AI Real-Time Assignments (Gemini API + RAG)
// ---------------------------------------------------------------------------

export interface TopicInfo {
  id: string;
  name: string;
  category: string;
  description: string;
  rag_query: string;
}

export interface AssignmentQuestion {
  id: string;
  topic_id: string;
  topic_name: string;
  prompt: string;
  options: string[];
  correct_idx?: number;
  explanation?: string;
  difficulty: "beginner" | "intermediate" | "advanced";
  source: string;
}

export interface GeneratedAssignment {
  assignment_id: string;
  created_at: string;
  topics: string[];
  total_questions: number;
  by_topic: Record<string, AssignmentQuestion[]>;
  questions: AssignmentQuestion[];
  model_used: string;
}

export interface QuestionEvaluation {
  id: string;
  prompt: string;
  topic_id: string;
  topic_name: string;
  selected_idx: number;
  correct_idx: number;
  is_correct: boolean;
  selected_text: string;
  correct_text: string;
  explanation: string;
}

export interface EvaluationResult {
  assignment_id: string;
  score: number;
  total: number;
  percentage: number;
  topic_scores: Record<string, { correct: number; total: number; percentage: number }>;
  results: QuestionEvaluation[];
  summary: string;
}

export interface DailyChallenge {
  date: string;
  challenge_id: string;
  title: string;
  difficulty: "beginner" | "intermediate" | "advanced";
  topic: string;
  prompt: string;
  story: string;
  target_state: string;
  allowed_gates: string[];
  constraints: {
    max_qubits: number;
    max_gates: number;
    target_fidelity: number;
  };
  starter_ir: CircuitIR;
  hints: string[];
  xp_reward: number;
}

export interface DailyChallengeVerifyResult {
  passed: boolean;
  score: number;
  fidelity: number;
  feedback: string;
  details?: Record<string, unknown>;
}

export function getAssessmentTopics(): Promise<TopicInfo[]> {
  return api.get<TopicInfo[]>("/assessments/topics");
}

export function generateAiAssignment(
  topics: string[],
  numQuestions = 5,
  difficulty = "mixed",
): Promise<GeneratedAssignment> {
  return api.post<GeneratedAssignment>("/assessments/generate-assignment", {
    topics,
    num_questions: numQuestions,
    difficulty,
  });
}

export function evaluateAiAssignment(
  assignment: GeneratedAssignment,
  answers: Record<string, string>,
): Promise<EvaluationResult> {
  return api.post<EvaluationResult>("/assessments/evaluate-assignment", {
    assignment,
    answers,
  });
}

export function getDailyChallenge(): Promise<DailyChallenge> {
  return api.get<DailyChallenge>("/assessments/daily-challenge");
}

export function verifyDailyChallenge(
  challengeId: string,
  circuitIr: CircuitIR,
): Promise<DailyChallengeVerifyResult> {
  return api.post<DailyChallengeVerifyResult>("/assessments/daily-challenge/verify", {
    challenge_id: challengeId,
    circuit_ir: circuitIr,
  });
}

