// Shared configuration for game settings
import type { Difficulty } from "@/shared/types";

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
