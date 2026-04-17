// ⚠️  AUTO-GENERATED — do not edit.
// Contract:        backend/app/rooms/protocol.py
// Generated from:  backend/app/rooms/protocol.py
// Source schemas:  contracts/jsonschema/
// Regenerate:      just generate-contracts

import { z } from "zod";

export const ServerEventSchema = z.union([
  z
    .object({
      type: z.literal("room_state"),
      players: z.array(
        z.object({ id: z.string(), name: z.string(), categories: z.array(z.string()).optional() }).strict(),
      ),
      hostId: z.union([z.string(), z.null()]).default(null),
      categories: z.array(z.string()).optional(),
      gamePhase: z
        .enum(["lobby", "drawing", "guessing", "round_results", "final_results"])
        .describe("Valid room lifecycle phases for game flow state."),
      difficulty: z.enum(["easy", "medium", "hard"]),
      maxRounds: z.number().int(),
      roundStartTime: z.union([z.number().int(), z.null()]).default(null),
      guessingStartTime: z.union([z.number().int(), z.null()]).default(null),
      drawingTimeLimit: z.union([z.number().int().gte(1), z.null()]).default(null),
      guessingTimeLimit: z.union([z.number().int().gte(1), z.null()]).default(null),
      guessTargets: z.record(z.string(), z.string()).optional(),
      padVisibility: z.boolean(),
      isPrivate: z.boolean(),
      defaultLocale: z.string().regex(/^[a-z]{2,5}$/),
      customCategoryIds: z.union([z.array(z.number().int()), z.null()]).default(null),
    })
    .strict(),
  z
    .object({
      type: z.literal("player_joined"),
      playerId: z.string(),
      name: z.string(),
      players: z.array(z.object({ id: z.string(), name: z.string() }).strict()),
      isHost: z.boolean(),
    })
    .strict(),
  z.object({ type: z.literal("host_restored"), message: z.string() }).strict(),
  z
    .object({
      type: z.literal("protocol_error"),
      error: z.string(),
      message: z.union([z.string(), z.null()]).default(null),
    })
    .strict(),
  z
    .object({
      type: z.literal("permission_error"),
      error: z.string(),
      message: z.union([z.string(), z.null()]).default(null),
    })
    .strict(),
  z
    .object({
      type: z.literal("player_ready_error"),
      error: z.string(),
      message: z.union([z.string(), z.null()]).default(null),
    })
    .strict(),
  z
    .object({
      type: z.literal("submit_guess_error"),
      error: z.string(),
      message: z.union([z.string(), z.null()]).default(null),
    })
    .strict(),
  z
    .object({
      type: z.literal("join_error"),
      error: z.string(),
      message: z.union([z.string(), z.null()]).default(null),
    })
    .strict(),
  z
    .object({
      type: z.literal("kick_error"),
      error: z.string(),
      message: z.union([z.string(), z.null()]).default(null),
    })
    .strict(),
  z
    .object({
      type: z.literal("start_round"),
      round: z.union([z.number().int(), z.null()]).default(null),
      cards: z.record(
        z.string(),
        z.object({
          categoryId: z.union([z.number().int(), z.null()]).default(null),
          category: z.string(),
          itemIds: z.union([z.array(z.number().int()), z.null()]).default(null),
          items: z.array(z.string()),
          alternatives: z.union([z.record(z.string(), z.array(z.string())), z.null()]).default(null),
        }),
      ),
      roundStartTime: z.number().int(),
    })
    .strict(),
  z.object({ type: z.literal("ready_status"), readyCount: z.number().int(), totalPlayers: z.number().int() }).strict(),
  z.object({ type: z.literal("host_changed"), newHostId: z.string() }).strict(),
  z.object({ type: z.literal("default_locale_update"), locale: z.string().regex(/^[a-z]{2,5}$/) }).strict(),
  z
    .object({
      type: z.literal("room_custom_categories_update"),
      categoryIds: z.union([z.array(z.number().int()), z.null()]).default(null),
    })
    .strict(),
  z.object({ type: z.literal("player_left"), playerId: z.string() }).strict(),
  z
    .object({
      type: z.literal("kick_vote_started"),
      targetPlayerId: z.string(),
      targetPlayerName: z.string(),
      initiatorId: z.string(),
      requiredVotes: z.number().int(),
      currentVotes: z.number().int(),
      expiresAt: z.number(),
    })
    .strict(),
  z
    .object({
      type: z.literal("kick_vote_updated"),
      targetPlayerId: z.string(),
      currentVotes: z.number().int(),
      requiredVotes: z.number().int(),
    })
    .strict(),
  z.object({ type: z.literal("kick_vote_expired"), targetPlayerId: z.string() }).strict(),
  z
    .object({ type: z.literal("player_kicked"), playerId: z.string(), playerName: z.string(), reason: z.string() })
    .strict(),
  z
    .object({
      type: z.literal("round_complete"),
      results: z.array(
        z
          .object({
            playerId: z.string(),
            targetPlayerId: z.string(),
            correctGuesses: z.number().int(),
            totalItems: z.number().int(),
            pointsEarned: z.number().int(),
          })
          .strict(),
      ),
      scores: z.record(z.string(), z.number().int()),
    })
    .strict(),
  z
    .object({
      type: z.literal("game_complete"),
      finalScores: z.record(z.string(), z.number().int()),
      winner: z.string(),
    })
    .strict(),
  z.object({
    type: z.literal("start_game"),
    difficulty: z.union([z.enum(["easy", "medium", "hard"]), z.null()]).default(null),
    rounds: z.union([z.number().int().gte(1), z.null()]).default(null),
    drawingTimeLimit: z.union([z.number().int().gte(1), z.null()]).default(null),
    guessingTimeLimit: z.union([z.number().int().gte(1), z.null()]).default(null),
  }),
  z.object({
    type: z.literal("start_guessing"),
    guessingStartTime: z.union([z.number().int(), z.null()]).default(null),
    guessTargets: z.record(z.string(), z.string()).optional(),
  }),
  z.object({ type: z.literal("restart_game") }),
  z.object({
    type: z.literal("settings_update"),
    difficulty: z.union([z.enum(["easy", "medium", "hard"]), z.null()]).default(null),
    rounds: z.union([z.number().int().gte(1), z.null()]).default(null),
    drawingTimeLimit: z.union([z.number().int().gte(1), z.null()]).default(null),
    guessingTimeLimit: z.union([z.number().int().gte(1), z.null()]).default(null),
  }),
  z
    .object({ type: z.literal("draw_stroke"), playerId: z.union([z.string(), z.null()]).default(null) })
    .catchall(z.any()),
  z
    .object({ type: z.literal("draw_stroke_partial"), playerId: z.union([z.string(), z.null()]).default(null) })
    .catchall(z.any()),
  z.object({ type: z.literal("drawpad_clear") }),
  z.object({ type: z.literal("pad_visibility"), visible: z.boolean().default(true) }),
]);

export type ServerEvent = z.infer<typeof ServerEventSchema>;
export type ServerEventType = ServerEvent["type"];
export type ServerEventOf<TType extends ServerEventType> = Extract<ServerEvent, { type: TType }>;
export type ServerEventMap = { [TType in ServerEventType]: ServerEventOf<TType> };
export const serverEventTypes = [
  "default_locale_update",
  "draw_stroke",
  "draw_stroke_partial",
  "drawpad_clear",
  "game_complete",
  "host_changed",
  "host_restored",
  "join_error",
  "kick_error",
  "kick_vote_expired",
  "kick_vote_started",
  "kick_vote_updated",
  "pad_visibility",
  "permission_error",
  "player_joined",
  "player_kicked",
  "player_left",
  "player_ready_error",
  "protocol_error",
  "ready_status",
  "restart_game",
  "room_custom_categories_update",
  "room_state",
  "round_complete",
  "settings_update",
  "start_game",
  "start_guessing",
  "start_round",
  "submit_guess_error",
] as const satisfies readonly ServerEventType[];
export const serverEventGroups = {
  connection: ["host_restored", "join_error", "player_joined", "player_left", "room_state"],
  gameFlow: [
    "game_complete",
    "host_changed",
    "ready_status",
    "restart_game",
    "round_complete",
    "settings_update",
    "start_game",
    "start_guessing",
    "start_round",
  ],
  roomSettings: ["default_locale_update", "room_custom_categories_update"],
  drawing: ["draw_stroke", "draw_stroke_partial", "drawpad_clear", "pad_visibility"],
  moderation: ["kick_error", "kick_vote_expired", "kick_vote_started", "kick_vote_updated", "player_kicked"],
  errors: ["permission_error", "player_ready_error", "protocol_error", "submit_guess_error"],
} as const satisfies Record<string, readonly ServerEventType[]>;
export const serverEventSummaries = {
  default_locale_update: "Room default locale updated.",
  draw_stroke: "A completed draw stroke relay.",
  draw_stroke_partial: "An in-progress draw stroke relay.",
  drawpad_clear: "Drawpad cleared.",
  game_complete: "Game completion results broadcast.",
  host_changed: "Host ownership changed.",
  host_restored: "A reconnecting host regained host status.",
  join_error: "Join failed but the connection remained valid.",
  kick_error: "Kick workflow error.",
  kick_vote_expired: "Kick vote expired.",
  kick_vote_started: "Kick vote started.",
  kick_vote_updated: "Kick vote tally updated.",
  pad_visibility: "Shared drawpad visibility changed.",
  permission_error: "Unauthorized action attempt.",
  player_joined: "A player joined the room.",
  player_kicked: "A player was kicked from the room.",
  player_left: "A player left the room.",
  player_ready_error: "Player-ready validation failed.",
  protocol_error: "Malformed or invalid websocket payload.",
  ready_status: "Current ready-player counts.",
  restart_game: "Game restart broadcast.",
  room_custom_categories_update: "Room-level private category selection changed.",
  room_state: "Current room snapshot.",
  round_complete: "Round completion results broadcast.",
  settings_update: "Game settings updated.",
  start_game: "Game start broadcast.",
  start_guessing: "Guessing phase started.",
  start_round: "Round start broadcast with assigned cards.",
  submit_guess_error: "Guess submission validation failed.",
} as const satisfies Record<ServerEventType, string>;
export type ServerEventGroupName = keyof typeof serverEventGroups;
export type ServerEventGroup<TGroup extends ServerEventGroupName> = ServerEventOf<
  (typeof serverEventGroups)[TGroup][number]
>;

export const ClientEventSchema = z.union([
  z.object({
    type: z.literal("join"),
    playerId: z.string(),
    name: z.string(),
    preferredLocale: z.union([z.string().regex(/^[a-z]{2,5}$/), z.null()]).default(null),
  }),
  z.object({
    type: z.literal("start_game"),
    difficulty: z.union([z.enum(["easy", "medium", "hard"]), z.null()]).default(null),
    rounds: z.union([z.number().int().gte(1), z.null()]).default(null),
    drawingTimeLimit: z.union([z.number().int().gte(1), z.null()]).default(null),
    guessingTimeLimit: z.union([z.number().int().gte(1), z.null()]).default(null),
  }),
  z.object({
    type: z.literal("start_round"),
    round: z.union([z.number().int(), z.null()]).default(null),
    cards: z.record(
      z.string(),
      z.object({
        categoryId: z.union([z.number().int(), z.null()]).default(null),
        category: z.string(),
        itemIds: z.union([z.array(z.number().int()), z.null()]).default(null),
        items: z.array(z.string()),
        alternatives: z.union([z.record(z.string(), z.array(z.string())), z.null()]).default(null),
      }),
    ),
  }),
  z.object({ type: z.literal("round_complete") }),
  z.object({ type: z.literal("game_complete") }),
  z.object({ type: z.literal("player_ready"), playerId: z.string() }),
  z.object({
    type: z.literal("start_guessing"),
    guessingStartTime: z.union([z.number().int(), z.null()]).default(null),
    guessTargets: z.record(z.string(), z.string()).optional(),
  }),
  z.object({
    type: z.literal("submit_guess"),
    targetPlayerId: z.string(),
    playerId: z.string(),
    guesses: z.array(z.string()).optional(),
  }),
  z.object({ type: z.literal("restart_game") }),
  z.object({ type: z.literal("heartbeat") }),
  z.object({
    type: z.literal("settings_update"),
    difficulty: z.union([z.enum(["easy", "medium", "hard"]), z.null()]).default(null),
    rounds: z.union([z.number().int().gte(1), z.null()]).default(null),
    drawingTimeLimit: z.union([z.number().int().gte(1), z.null()]).default(null),
    guessingTimeLimit: z.union([z.number().int().gte(1), z.null()]).default(null),
  }),
  z.object({
    type: z.literal("default_locale_update"),
    locale: z
      .string()
      .regex(/^[a-z]{2,5}$/)
      .optional(),
  }),
  z.object({
    type: z.literal("room_custom_categories_update"),
    categoryIds: z.union([z.array(z.number().int()), z.null()]).default(null),
  }),
  z
    .object({ type: z.literal("draw_stroke"), playerId: z.union([z.string(), z.null()]).default(null) })
    .catchall(z.any()),
  z
    .object({ type: z.literal("draw_stroke_partial"), playerId: z.union([z.string(), z.null()]).default(null) })
    .catchall(z.any()),
  z.object({ type: z.literal("drawpad_clear") }),
  z.object({ type: z.literal("pad_visibility"), visible: z.boolean().default(true) }),
  z.object({ type: z.literal("privacy_changed"), isPrivate: z.boolean() }),
  z.object({ type: z.literal("initiate_kick"), targetPlayerId: z.string() }),
  z.object({ type: z.literal("cast_kick_vote"), targetPlayerId: z.string() }),
  z.object({ type: z.literal("request_game_state"), playerId: z.union([z.string(), z.null()]).default(null) }),
]);
export type ClientEvent = z.infer<typeof ClientEventSchema>;
export type ClientEventType = ClientEvent["type"];
export type ClientEventOf<TType extends ClientEventType> = Extract<ClientEvent, { type: TType }>;
export type ClientEventMap = { [TType in ClientEventType]: ClientEventOf<TType> };
export const clientEventTypes = [
  "cast_kick_vote",
  "default_locale_update",
  "draw_stroke",
  "draw_stroke_partial",
  "drawpad_clear",
  "game_complete",
  "heartbeat",
  "initiate_kick",
  "join",
  "pad_visibility",
  "player_ready",
  "privacy_changed",
  "request_game_state",
  "restart_game",
  "room_custom_categories_update",
  "round_complete",
  "settings_update",
  "start_game",
  "start_guessing",
  "start_round",
  "submit_guess",
] as const satisfies readonly ClientEventType[];
export const clientEventGroups = {
  connection: ["heartbeat", "join", "request_game_state"],
  gameFlow: [
    "game_complete",
    "player_ready",
    "restart_game",
    "round_complete",
    "settings_update",
    "start_game",
    "start_guessing",
    "start_round",
    "submit_guess",
  ],
  roomSettings: ["default_locale_update", "privacy_changed", "room_custom_categories_update"],
  drawing: ["draw_stroke", "draw_stroke_partial", "drawpad_clear", "pad_visibility"],
  moderation: ["cast_kick_vote", "initiate_kick"],
} as const satisfies Record<string, readonly ClientEventType[]>;
export const clientEventSummaries = {
  cast_kick_vote: "Cast a vote in an active kick vote.",
  default_locale_update: "Change the room default locale.",
  draw_stroke: "Broadcast a completed draw stroke.",
  draw_stroke_partial: "Broadcast an in-progress draw stroke.",
  drawpad_clear: "Clear the shared drawpad.",
  game_complete: "Signal that the game is complete.",
  heartbeat: "Keep the websocket session alive.",
  initiate_kick: "Start a kick vote for a target player.",
  join: "Join a room with the local player identity.",
  pad_visibility: "Show or hide the shared drawpad.",
  player_ready: "Mark the current player as ready.",
  privacy_changed: "Change the room privacy setting.",
  request_game_state: "Request the latest room snapshot.",
  restart_game: "Restart the game from the lobby state.",
  room_custom_categories_update: "Override the host's private category selection for this room.",
  round_complete: "Signal that the current round is complete.",
  settings_update: "Update shared game settings.",
  start_game: "Host starts a game with room settings.",
  start_guessing: "Host transitions the room into guessing.",
  start_round: "Host starts a drawing round with assigned cards.",
  submit_guess: "Submit guesses for another player's drawing.",
} as const satisfies Record<ClientEventType, string>;
export type ClientEventGroupName = keyof typeof clientEventGroups;
export type ClientEventGroup<TGroup extends ClientEventGroupName> = ClientEventOf<
  (typeof clientEventGroups)[TGroup][number]
>;
