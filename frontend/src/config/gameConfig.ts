// Shared configuration for game settings
import type { Difficulty } from "@/shared/types";

const configuredBackendHost = import.meta.env.VITE_BACKEND_HOST?.trim();

function getWindowOrigin(defaultOrigin: string): string {
  if (typeof window === "undefined") {
    return defaultOrigin;
  }

  return window.location.origin;
}

function getWindowWebSocketOrigin(defaultOrigin: string): string {
  if (typeof window === "undefined") {
    return defaultOrigin;
  }

  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}`;
}

export const BACKEND_HOST = configuredBackendHost || getWindowWebSocketOrigin("ws://localhost:3001");
export const API_HOST = configuredBackendHost
  ? configuredBackendHost.replace(/^ws(s?):\/\//, "http$1://")
  : getWindowOrigin("http://localhost:3001");

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
  ROUND_RESULTS_COUNTDOWN_S: 15,
  /** If all players are ready, host auto-restarts the game after this delay. */
  AUTO_RESTART_TIMEOUT_MS: 60_000,
} as const;

export const STORAGE_KEYS = {
  GAME_STATE: "gameState",
  PLAYER_NAME: "playerName",
  PLAYER_ID: "player_id",
  DRAWING_STATE: "drawingState",
  GUESSING_STATE: "guessingState",
} as const;
