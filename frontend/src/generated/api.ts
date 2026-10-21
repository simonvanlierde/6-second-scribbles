// ⚠️  AUTO-GENERATED — do not edit.

// Contract:        contracts/openapi.json

// Generated from:  backend/app/main.py

// Source schemas:  contracts/openapi.json#/components/schemas

// Regenerate:      just generate-contracts

import { z } from "zod";

export const CreateRoomResponseSchema = z
  .object({ room_code: z.string() })
  .describe("Response for newly created room.");

const DifficultySchema = z.enum(["easy", "medium", "hard"]);
export type Difficulty = z.infer<typeof DifficultySchema>;

const GamePhaseSchema = z
  .enum(["lobby", "drawing", "guessing", "round_results", "final_results"])
  .describe("Valid room lifecycle phases for game flow state.");
export type GamePhase = z.infer<typeof GamePhaseSchema>;

export const LocaleAvailabilityItemSchema = z
  .object({
    category_count: z.number().int(),
    difficulty_counts: z.record(z.string(), z.number().int()).optional(),
    locale: z.string().regex(/^[a-z]{2,5}(?:-[A-Za-z0-9]{2,8})?$/),
  })
  .describe("Aggregated locale support across selectable system categories.");
export type LocaleAvailabilityItem = z.infer<typeof LocaleAvailabilityItemSchema>;

export const QuickPlayResponseSchema = z
  .object({ kind: z.enum(["existing", "created"]), room_code: z.string() })
  .describe("Response for quick-play: a joinable room, existing or freshly created.");

export const RoomStatusResponseSchema = z
  .object({
    exists: z.boolean(),
    game_phase: z
      .union([
        z
          .enum(["lobby", "drawing", "guessing", "round_results", "final_results"])
          .describe("Valid room lifecycle phases for game flow state."),
        z.null(),
      ])
      .optional(),
    players: z.union([z.number().int(), z.null()]).optional(),
  })
  .describe("Response for room status checks.");

export const UserResponseSchema = z
  .object({
    displayName: z.union([z.string(), z.null()]),
    id: z.string(),
    isGuest: z.boolean(),
    preferredLocale: z.string(),
    username: z.string(),
  })
  .describe("Public user payload for the current authenticated session.");
export type UserResponse = z.infer<typeof UserResponseSchema>;
