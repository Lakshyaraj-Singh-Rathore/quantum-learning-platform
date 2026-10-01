import { api } from "./client";

/** Mirrors GET /games in backend/app/api/assessments.py. */

export interface GameLevel {
  slug: string;
  title: string;
  prompt: string;
  level: number;
  /** null for state-graded levels, else "truth_table" | "find_bug" | "shot_detective". */
  grader: string | null;
  allowed_gates: string[];
  constraints: Record<string, unknown>;
  tags: string[];
  /** A broken circuit to repair, for the Find-the-Bug levels. */
  starter_ir: Record<string, unknown> | null;
  epsilon: number | null;
  max_edits: number | null;
  n_controls: number | null;
  best_score: number;
  passed: boolean;
  attempts: number;
}

export interface Game {
  game_id: string;
  title: string;
  blurb: string;
  icon: string;
  completed: number;
  total: number;
  levels: GameLevel[];
}

export function listGames(): Promise<{ games: Game[] }> {
  return api.get<{ games: Game[] }>("/games");
}
