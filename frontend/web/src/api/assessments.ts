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
