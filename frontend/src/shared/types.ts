/**
 * Shared types for Six Second Scribbles
 * Used by both client and server
 */

import type { Difficulty as ContractDifficulty, GamePhase as ContractGamePhase } from "@/generated/api";

export interface Card {
  category: string;
  items: string[];
  alternatives?: Record<string, string[]> | null;
}

export type Difficulty = ContractDifficulty;
export type GamePhase = ContractGamePhase;

export interface Player {
  id: string;
  name: string;
  score: number;
  color?: string | null;
  currentCard?: Card;
  drawing?: string; // Base64 data URL of canvas drawing
  connected: boolean; // false while disconnected/"reconnecting"
}

export interface RoundResult {
  playerId: string;
  targetPlayerId: string;
  correctGuesses: number;
  totalItems: number;
  pointsEarned: number;
}

export interface RoundHighlight {
  playerId: string;
  detail: string;
}

export interface RoundHighlights {
  bestGuesser: RoundHighlight | null;
  speedDemon: RoundHighlight | null;
  wildestMiss: RoundHighlight | null;
}

export type HighlightKind = "bestGuesser" | "speedDemon" | "wildestMiss";

export interface KickVote {
  currentVotes: number;
  requiredVotes: number;
  expiresAt: number;
}

export type DrawStroke = {
  color: string;
  width: number;
  points: Array<{ x: number; y: number }>;
};

/** A single drawing captured for the end-of-game gallery (one per player per round). */
export interface GalleryDrawing {
  round: number;
  playerId: string;
  name: string;
  color: string;
  drawing: string; // Base64 data URL
}
