/**
 * Shared types for Six Second Scribbles
 * Used by both client and server
 */

export interface Card {
  category: string;
  items: string[];
}

export type SimpleCard = {
  id: string;
  name: string;
};

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

// WebSocket message types (fully typed protocol)
export type GameMessage =
  | { type: "join"; playerId: string; name: string }
  | { type: "player_joined"; playerId: string; name: string; players: Array<{ id: string; name: string }> }
  | { type: "player_left"; playerId: string }
  | { type: "host_changed"; newHostId: string }
  | { type: "room_state"; players: Array<{ id: string; name: string }>; categories: string[]; gamePhase: 'lobby' | 'drawing' | 'guessing' | 'scoring' | 'complete'; roundStartTime?: number; roundLength?: number }
  | { type: "start_game"; difficulty: Difficulty; rounds: number; roundLength: number } // Host sends roundLength to server
  | { type: "start_round"; round: number; roundStartTime: number; cards: Record<string, Card> } // Server sends roundStartTime to clients
  | { type: "drawing_complete"; playerId: string; drawing: string }
  | { type: "start_guessing"; assignments: Record<string, string>; roundStartTime: number } // Server sends roundStartTime for guessing phase
  | { type: "submit_guess"; playerId: string; targetPlayerId: string; guesses: string[] }
  | { type: "round_complete"; results: RoundResult[]; scores: Record<string, number> }
  | { type: "game_complete"; finalScores: Record<string, number>; winner: string }
  | { type: "request_game_state"; playerId: string }
  | { type: "player_ready"; playerId: string } // Player indicates ready for next game
  | { type: "ready_status"; readyCount: number; totalPlayers: number } // Server broadcasts ready count
  | { type: "restart_game" } // Host restarts the game
  | { type: "heartbeat"; playerId: string } // Client sends periodic heartbeat to indicate activity
  | { type: "settings_update"; difficulty: Difficulty; rounds: number; roundLength: number } // Host broadcasts settings changes
  | { type: "draw_stroke"; playerId: string; stroke: DrawStroke } // Real-time draw stroke (waiting room)
  | { type: "drawpad_clear"; playerId: string } // Host-clears the shared waiting-room pad
   | { type: 'pad_visibility'; playerId: string; visible: boolean } // Host-controlled visibility for drawpad
   | { type: 'draw_stroke_partial'; playerId: string; stroke: { color: string; width: number; points: Array<{ x: number; y: number }> } }
  ;

export type DrawStroke = {
  color: string;
  width: number;
  points: Array<{ x: number; y: number }>;
};
