// ⚠️  AUTO-GENERATED — do not edit.

// Contract:        contracts/openapi.json

// Generated from:  backend/app/main.py

// Source schemas:  contracts/openapi.json#/components/schemas

// Regenerate:      just generate-contracts

import { z } from "zod";

export const AppInfoResponseSchema = z
  .object({
    cache: z.string().default("ok"),
    database: z.string().default("ok"),
    service: z.string(),
    status: z.string(),
    version: z.string(),
  })
  .describe("Root endpoint response.");
export type AppInfoResponse = z.infer<typeof AppInfoResponseSchema>;

export const CategoryListItemSchema = z
  .object({
    difficulty: z.enum(["easy", "medium", "hard"]),
    id: z.number().int(),
    locale: z.union([z.string().regex(/^[a-z]{2,5}(?:-[A-Za-z0-9]{2,8})?$/), z.null()]),
    name: z.string(),
  })
  .describe("Compact localized category representation used by list endpoints.");
export type CategoryListItem = z.infer<typeof CategoryListItemSchema>;

export const CategorySelectionRequestSchema = z
  .object({
    count: z.number().int().gte(1).default(1),
    difficulty: z.enum(["easy", "medium", "hard"]),
    locale: z
      .string()
      .regex(/^[a-z]{2,5}(?:-[A-Za-z0-9]{2,8})?$/)
      .optional(),
    locales: z.array(z.string().regex(/^[a-z]{2,5}(?:-[A-Za-z0-9]{2,8})?$/)).optional(),
    player_count: z.number().int().gte(1).default(2),
  })
  .describe("Parameters for selecting category sets for a room/game.");
export type CategorySelectionRequest = z.infer<typeof CategorySelectionRequestSchema>;

export const CategorySelectionResponseSchema = z
  .object({
    difficulty: z.enum(["easy", "medium", "hard"]),
    selections: z.array(
      z
        .object({
          alternatives: z.record(z.string(), z.array(z.string())),
          category_id: z.number().int(),
          category_name: z.string(),
          item_ids: z.array(z.number().int()),
          items: z.array(z.string()),
        })
        .describe("One selected localized category set for game setup."),
    ),
  })
  .describe("Response for room-scoped category selection.");
export type CategorySelectionResponse = z.infer<typeof CategorySelectionResponseSchema>;

export const CreateRoomResponseSchema = z
  .object({ room_code: z.string() })
  .describe("Response for newly created room.");
export type CreateRoomResponse = z.infer<typeof CreateRoomResponseSchema>;

export const DifficultySchema = z.enum(["easy", "medium", "hard"]);
export type Difficulty = z.infer<typeof DifficultySchema>;

export const GamePhaseSchema = z
  .enum(["lobby", "drawing", "guessing", "round_results", "final_results"])
  .describe("Valid room lifecycle phases for game flow state.");
export type GamePhase = z.infer<typeof GamePhaseSchema>;

export const GuestAuthRequestSchema = z
  .object({
    displayName: z.union([z.string().max(80), z.null()]).optional(),
    preferredLocale: z.string().max(16).default("en"),
  })
  .describe("Optional request body for guest session bootstrap.");
export type GuestAuthRequest = z.infer<typeof GuestAuthRequestSchema>;

export const HTTPValidationErrorSchema = z.object({
  detail: z
    .array(
      z.object({
        ctx: z.record(z.string(), z.any()).optional(),
        input: z.any().optional(),
        loc: z.array(z.union([z.string(), z.number().int()])),
        msg: z.string(),
        type: z.string(),
      }),
    )
    .optional(),
});
export type HTTPValidationError = z.infer<typeof HTTPValidationErrorSchema>;

export const LanguageCodeSchema = z.string().regex(/^[a-z]{2,5}(?:-[A-Za-z0-9]{2,8})?$/);
export type LanguageCode = z.infer<typeof LanguageCodeSchema>;

export const LocaleAvailabilityItemSchema = z
  .object({
    category_count: z.number().int(),
    difficulty_counts: z.record(z.string(), z.number().int()).optional(),
    locale: z.string().regex(/^[a-z]{2,5}(?:-[A-Za-z0-9]{2,8})?$/),
  })
  .describe("Aggregated locale support across selectable system categories.");
export type LocaleAvailabilityItem = z.infer<typeof LocaleAvailabilityItemSchema>;

export const LoginRequestSchema = z
  .object({
    password: z.string().min(8).max(128),
    username: z
      .string()
      .regex(/^[a-zA-Z0-9_-]+$/)
      .min(3)
      .max(40),
  })
  .describe("Request body for username/password login.");
export type LoginRequest = z.infer<typeof LoginRequestSchema>;

export const QuickPlayResponseSchema = z
  .object({ kind: z.enum(["existing", "created"]), room_code: z.string() })
  .describe("Response for quick-play: a joinable room, existing or freshly created.");
export type QuickPlayResponse = z.infer<typeof QuickPlayResponseSchema>;

export const RandomRoomResponseSchema = z
  .object({ max_players: z.number().int(), player_count: z.number().int(), room_code: z.string() })
  .describe("Response for finding a random joinable room.");
export type RandomRoomResponse = z.infer<typeof RandomRoomResponseSchema>;

export const RegisterRequestSchema = z
  .object({
    displayName: z.union([z.string().max(80), z.null()]).optional(),
    password: z.string().min(8).max(128),
    preferredLocale: z.string().max(16).default("en"),
    username: z
      .string()
      .regex(/^[a-zA-Z0-9_-]+$/)
      .min(3)
      .max(40),
  })
  .describe("Request body for account registration.");
export type RegisterRequest = z.infer<typeof RegisterRequestSchema>;

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
export type RoomStatusResponse = z.infer<typeof RoomStatusResponseSchema>;

export const SelectedCategorySetSchema = z
  .object({
    alternatives: z.record(z.string(), z.array(z.string())),
    category_id: z.number().int(),
    category_name: z.string(),
    item_ids: z.array(z.number().int()),
    items: z.array(z.string()),
  })
  .describe("One selected localized category set for game setup.");
export type SelectedCategorySet = z.infer<typeof SelectedCategorySetSchema>;

export const StatsResponseSchema = z
  .object({
    active_rooms: z.number().int(),
    empty_rooms: z.number().int(),
    hibernated_rooms: z.number().int(),
    status: z.string(),
    total_players: z.number().int(),
    total_rooms: z.number().int(),
  })
  .describe("Server statistics response.");
export type StatsResponse = z.infer<typeof StatsResponseSchema>;

export const UpdatePreferencesRequestSchema = z
  .object({
    displayName: z.union([z.string(), z.null()]).optional(),
    preferredLocale: z.union([z.string(), z.null()]).optional(),
  })
  .describe("Request body for updating user preferences.");
export type UpdatePreferencesRequest = z.infer<typeof UpdatePreferencesRequestSchema>;

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

export const ValidationErrorSchema = z.object({
  ctx: z.record(z.string(), z.any()).optional(),
  input: z.any().optional(),
  loc: z.array(z.union([z.string(), z.number().int()])),
  msg: z.string(),
  type: z.string(),
});
export type ValidationError = z.infer<typeof ValidationErrorSchema>;

export const apiSchemaNames = [
  "AppInfoResponse",
  "CategoryListItem",
  "CategorySelectionRequest",
  "CategorySelectionResponse",
  "CreateRoomResponse",
  "Difficulty",
  "GamePhase",
  "GuestAuthRequest",
  "HTTPValidationError",
  "LanguageCode",
  "LocaleAvailabilityItem",
  "LoginRequest",
  "QuickPlayResponse",
  "RandomRoomResponse",
  "RegisterRequest",
  "RoomStatusResponse",
  "SelectedCategorySet",
  "StatsResponse",
  "UpdatePreferencesRequest",
  "UserResponse",
  "ValidationError",
] as const;
