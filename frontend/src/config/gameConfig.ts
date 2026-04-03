// Shared configuration for game settings
import type { Difficulty } from "@/shared/types";

export const BACKEND_HOST = import.meta.env.VITE_BACKEND_HOST || "ws://localhost:8000";
// HTTP(S) base URL derived from the WebSocket URL (ws → http, wss → https).
export const API_HOST = BACKEND_HOST.replace(/^ws(s?):\/\//, "http$1://");

export const DEFAULT_DIFFICULTY: Difficulty = "medium";

export const ROUNDS = {
  DEFAULT: 5,
  MIN: 1,
  MAX: 10,
} as const;

export const DRAWING_TIME_LIMIT_SECONDS = {
  DEFAULT: 60,
  MIN: 15,
  MAX: 180,
} as const;

export const GUESSING_TIME_LIMIT_SECONDS = {
  DEFAULT: 60,
  MIN: 15,
  MAX: 180,
} as const;

export const GAME_SETTINGS = {
  difficulty: { DEFAULT: DEFAULT_DIFFICULTY },
  rounds: ROUNDS,
  drawingTimeLimitSeconds: DRAWING_TIME_LIMIT_SECONDS,
  guessingTimeLimitSeconds: GUESSING_TIME_LIMIT_SECONDS,
};

export const UI_TIMINGS = {
  HEARTBEAT_INTERVAL_MS: 60_000,
  JOIN_ERROR_REDIRECT_MS: 2_000,
  SETTINGS_FLASH_MS: 900,
  COPY_TOOLTIP_MS: 800,
} as const;

export const GAME_TIMINGS = {
  /** Countdown (seconds) shown on the round-results screen before server advances. */
  ROUND_RESULTS_COUNTDOWN_S: 5,
  /** If all players are ready, host auto-restarts the game after this delay. */
  AUTO_RESTART_TIMEOUT_MS: 60_000,
} as const;

export const STORAGE_KEYS = {
  GAME_STATE: "gameState",
  PLAYER_NAME: "playerName",
  PLAYER_ID: "player_id",
  DRAWING_STATE: "drawingState",
} as const;
