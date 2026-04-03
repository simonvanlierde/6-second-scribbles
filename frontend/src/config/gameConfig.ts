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

export const ROUND_LENGTH_SECONDS = {
  DEFAULT: 60,
  MIN: 15,
  MAX: 180,
} as const;

export const GAME_SETTINGS = {
  difficulty: { DEFAULT: DEFAULT_DIFFICULTY },
  rounds: ROUNDS,
  roundLengthSeconds: ROUND_LENGTH_SECONDS,
};

export const UI_TIMINGS = {
  HEARTBEAT_INTERVAL_MS: 60_000,
  JOIN_ERROR_REDIRECT_MS: 2_000,
  SETTINGS_FLASH_MS: 900,
  COPY_TOOLTIP_MS: 800,
} as const;
