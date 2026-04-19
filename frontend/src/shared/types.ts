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

export interface Deck {
  easy: Card[];
  medium: Card[];
  hard: Card[];
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
}

export interface GameState {
  roomCode: string;
  players: Map<string, Player>;
  currentRound: number;
  maxRounds: number;
  roundStartTime?: number; // Unix timestamp when the current round started (server-generated)
  guessingStartTime?: number; // Unix timestamp when the guessing phase started (server-generated)
  drawingTimeLimit?: number; // Drawing duration in seconds (host-configured)
  guessingTimeLimit?: number; // Guessing duration in seconds (host-configured)
  guessTargets?: Record<string, string>; // One assigned drawing target per player
  gamePhase: GamePhase;
}

export interface GuessSubmission {
  playerId: string;
  targetPlayerId: string;
  guesses: string[];
}

export interface RoundResult {
  playerId: string;
  targetPlayerId: string;
  correctGuesses: number;
  totalItems: number;
  pointsEarned: number;
}

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
