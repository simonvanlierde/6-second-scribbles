/**
 * Shared types for Six Second Scribbles
 * Used by both client and server
 */

export interface Card {
  category: string;
  items: string[];
}

export interface Deck {
  easy: Card[];
  medium: Card[];
  hard: Card[];
}

export type Difficulty = "easy" | "medium" | "hard";

export interface Player {
  id: string;
  name: string;
  score: number;
  currentCard?: Card;
  drawing?: string; // Base64 data URL of canvas drawing
}

export interface GameState {
  roomCode: string;
  players: Map<string, Player>;
  currentRound: number;
  maxRounds: number;
  roundStartTime?: number; // Unix timestamp when the current round started (server-generated)
  roundLength?: number; // Duration of each round in seconds (host-configured)
  gamePhase: "lobby" | "drawing" | "guessing" | "scoring" | "complete";
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

// WebSocket message types (fully typed protocol)
export type GameMessage =
  // ── Outbound (client → server) ───────────────────────────────────────────
  | { type: "join"; playerId: string; name: string }
  | { type: "start_game"; difficulty: Difficulty; rounds: number; roundLength: number }
  | { type: "request_game_state"; playerId: string }
  | { type: "player_ready"; playerId: string }
  | { type: "heartbeat"; playerId: string }
  | { type: "settings_update"; difficulty: Difficulty; rounds: number; roundLength: number }
  | { type: "draw_stroke"; playerId: string; stroke: DrawStroke }
  | { type: "draw_stroke_partial"; playerId: string; stroke: DrawStroke }
  | { type: "drawpad_clear"; playerId: string }
  | { type: "pad_visibility"; playerId: string; visible: boolean }
  | { type: "submit_guess"; playerId: string; targetPlayerId: string; guesses: string[] }
  | { type: "drawing_complete"; playerId: string; drawing: string }
  | { type: "initiate_kick"; playerId: string; targetPlayerId: string }
  | { type: "cast_kick_vote"; playerId: string; targetPlayerId: string }
  | { type: "privacy_changed"; playerId: string; isPrivate: boolean }
  // ── Bidirectional (sent by client, relayed by server to all clients) ──────
  | { type: "restart_game" }
  | { type: "language_update"; playerId?: string; language: string }
  // ── Inbound (server → client) ────────────────────────────────────────────
  | { type: "join_error"; message: string }
  | { type: "host_restored" }
  | {
      type: "room_state";
      players: Array<{ id: string; name: string }>;
      hostId?: string;
      categories: string[];
      gamePhase: "lobby" | "drawing" | "guessing" | "scoring" | "complete";
      roundStartTime?: number;
      roundLength?: number;
      padVisibility?: boolean;
      language?: string;
    }
  | {
      type: "player_joined";
      playerId: string;
      name: string;
      players: Array<{ id: string; name: string }>;
      isHost?: boolean;
    }
  | { type: "player_left"; playerId: string }
  | { type: "host_changed"; newHostId: string }
  | { type: "start_round"; round: number; roundStartTime: number; cards: Record<string, Card> }
  | { type: "start_guessing"; assignments: Record<string, string>; roundStartTime: number }
  | { type: "round_complete"; results: RoundResult[]; scores: Record<string, number> }
  | { type: "game_complete"; finalScores: Record<string, number>; winner: string }
  | { type: "ready_status"; readyCount: number; totalPlayers: number }
  | {
      type: "kick_vote_started";
      targetPlayerId: string;
      targetPlayerName: string;
      initiatorId: string;
      currentVotes: number;
      requiredVotes: number;
      expiresAt: number;
    }
  | { type: "kick_vote_updated"; targetPlayerId: string; currentVotes: number; requiredVotes: number }
  | { type: "player_kicked"; playerId: string; playerName: string }
  | { type: "kick_vote_expired"; targetPlayerId: string; targetPlayerName: string }
  | { type: "kick_error"; error: string };
