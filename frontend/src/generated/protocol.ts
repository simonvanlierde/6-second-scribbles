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
        z
          .object({
            id: z.string(),
            name: z.string(),
            color: z.union([z.string(), z.null()]).default(null),
            connected: z.boolean().default(true),
          })
          .strict(),
      ),
      hostId: z.union([z.string(), z.null()]).default(null),
      gamePhase: z
        .enum(["lobby", "drawing", "guessing", "round_results", "final_results"])
        .describe("Valid room lifecycle phases for game flow state."),
      difficulty: z.enum(["easy", "medium", "hard"]),
      currentRound: z.number().int().default(0),
      maxRounds: z.number().int(),
      roundStartTime: z.union([z.number().int(), z.null()]).default(null),
      guessingStartTime: z.union([z.number().int(), z.null()]).default(null),
      drawingTimeLimit: z.union([z.number().int().gte(1), z.null()]).default(null),
      guessingTimeLimit: z.union([z.number().int().gte(1), z.null()]).default(null),
      guessTargets: z.record(z.string(), z.string()).optional(),
      drawings: z.record(z.string(), z.string()).optional(),
      drawingHistory: z
        .array(
          z
            .object({
              round: z.number().int(),
              playerId: z.string(),
              name: z.string(),
              color: z.union([z.string(), z.null()]).default(null),
              drawing: z.string(),
            })
            .strict()
            .describe("One completed drawing retained for the end-of-game gallery."),
        )
        .optional(),
      lobbyStrokes: z
        .array(
          z
            .object({
              color: z.string(),
              width: z.number(),
              points: z.array(z.object({ x: z.number(), y: z.number() })).optional(),
            })
            .strict()
            .describe(
              "A full shared-drawpad stroke the server reconstructs from partial fragments.\n\nUnlike ``StrokeDelta`` (a per-frame fragment, capped at 1000 points), this is a\nwhole completed/in-progress stroke, so late joiners can hydrate the collective\ndoodle from ``room_state`` instead of only seeing strokes drawn after they join.",
            ),
        )
        .optional(),
      card: z
        .union([
          z.object({
            categoryId: z.union([z.number().int(), z.null()]).default(null),
            category: z.string(),
            itemIds: z.union([z.array(z.number().int()), z.null()]).default(null),
            items: z.array(z.string()),
            alternatives: z.union([z.record(z.string(), z.array(z.string())), z.null()]).default(null),
          }),
          z.null(),
        ])
        .default(null),
      readyCount: z.number().int().default(0),
      totalPlayers: z.number().int().default(0),
      padVisibility: z.boolean(),
      isPrivate: z.boolean(),
      defaultLocale: z.string().regex(/^[a-z]{2,5}(?:-[A-Za-z0-9]{2,8})?$/),
    })
    .strict(),
  z
    .object({
      type: z.literal("player_joined"),
      playerId: z.string(),
      name: z.string(),
      players: z.array(
        z
          .object({
            id: z.string(),
            name: z.string(),
            color: z.union([z.string(), z.null()]).default(null),
            connected: z.boolean().default(true),
          })
          .strict(),
      ),
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
  z
    .object({
      type: z.literal("default_locale_update"),
      locale: z.string().regex(/^[a-z]{2,5}(?:-[A-Za-z0-9]{2,8})?$/),
    })
    .strict(),
  z.object({ type: z.literal("player_left"), playerId: z.string() }).strict(),
  z
    .object({ type: z.literal("player_presence"), playerId: z.string(), connected: z.boolean() })
    .strict()
    .describe("A player's connection status changed (disconnected/reconnecting or back)."),
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
      highlights: z
        .union([
          z
            .object({
              bestGuesser: z
                .union([z.object({ playerId: z.string(), detail: z.string().default("") }).strict(), z.null()])
                .default(null),
              speedDemon: z
                .union([z.object({ playerId: z.string(), detail: z.string().default("") }).strict(), z.null()])
                .default(null),
              wildestMiss: z
                .union([z.object({ playerId: z.string(), detail: z.string().default("") }).strict(), z.null()])
                .default(null),
            })
            .strict(),
          z.null(),
        ])
        .default(null),
    })
    .strict(),
  z
    .object({
      type: z.literal("game_complete"),
      finalScores: z.record(z.string(), z.number().int()),
      winner: z.string(),
    })
    .strict(),
  z
    .object({
      type: z.literal("reaction_received"),
      drawingId: z.string(),
      reactionKey: z.enum(["laugh", "shock", "art", "mind-blown", "think"]),
      senderId: z.string(),
    })
    .strict(),
  z
    .object({
      type: z.literal("draw_stroke_batch"),
      fragments: z.array(
        z
          .object({
            playerId: z.string(),
            stroke: z
              .object({
                color: z.string().max(32),
                width: z.number().gt(0).lte(64),
                points: z
                  .array(z.object({ x: z.number(), y: z.number() }))
                  .max(1000)
                  .optional(),
              })
              .describe(
                "A stroke fragment: only the points added since the previous partial.\n\nSending deltas (rather than the whole growing point list every frame) keeps\nan in-progress stroke's relayed payload O(new points) instead of O(n^2).",
              ),
            strokeStart: z.boolean(),
          })
          .strict()
          .describe("One player's doodle fragment inside a ``draw_stroke_batch``."),
      ),
    })
    .strict()
    .describe("The lobby doodle fragments a room received during one tick, in arrival order."),
  z.object({
    type: z.literal("start_game"),
    difficulty: z.union([z.enum(["easy", "medium", "hard"]), z.null()]).default(null),
    rounds: z.union([z.number().int().gte(1).lte(10), z.null()]).default(null),
    drawingTimeLimit: z.union([z.number().int().gte(15).lte(180), z.null()]).default(null),
    guessingTimeLimit: z.union([z.number().int().gte(15).lte(180), z.null()]).default(null),
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
    rounds: z.union([z.number().int().gte(1).lte(10), z.null()]).default(null),
    drawingTimeLimit: z.union([z.number().int().gte(15).lte(180), z.null()]).default(null),
    guessingTimeLimit: z.union([z.number().int().gte(15).lte(180), z.null()]).default(null),
  }),
  z
    .object({ type: z.literal("draw_stroke"), playerId: z.union([z.string(), z.null()]).default(null) })
    .catchall(z.any()),
  z.object({ type: z.literal("drawpad_clear") }),
  z.object({ type: z.literal("pad_visibility"), visible: z.boolean().default(true) }),
]);

export type ServerEvent = z.infer<typeof ServerEventSchema>;
export type ServerEventOf<TType extends ServerEvent["type"]> = Extract<ServerEvent, { type: TType }>;

export const ClientEventSchema = z.union([
  z.object({
    type: z.literal("join"),
    playerId: z.string().max(64),
    name: z.string().max(80),
    preferredLocale: z.union([z.string().regex(/^[a-z]{2,5}(?:-[A-Za-z0-9]{2,8})?$/), z.null()]).default(null),
    preferredColor: z.union([z.string(), z.null()]).default(null),
    rejoinKey: z.union([z.string().max(128), z.null()]).default(null),
  }),
  z.object({
    type: z.literal("start_game"),
    difficulty: z.union([z.enum(["easy", "medium", "hard"]), z.null()]).default(null),
    rounds: z.union([z.number().int().gte(1).lte(10), z.null()]).default(null),
    drawingTimeLimit: z.union([z.number().int().gte(15).lte(180), z.null()]).default(null),
    guessingTimeLimit: z.union([z.number().int().gte(15).lte(180), z.null()]).default(null),
  }),
  z.object({ type: z.literal("player_ready"), playerId: z.string().max(64) }),
  z.object({
    type: z.literal("submit_guess"),
    targetPlayerId: z.string(),
    playerId: z.string().max(64),
    guesses: z.array(z.string().max(100)).max(50).optional(),
  }),
  z.object({ type: z.literal("restart_game") }),
  z.object({ type: z.literal("heartbeat") }),
  z.object({ type: z.literal("leave") }).describe("An explicit, intentional leave — remove the player immediately."),
  z
    .object({ type: z.literal("watch") })
    .describe("Follow the room as a spectator: get its broadcasts without joining."),
  z.object({
    type: z.literal("settings_update"),
    difficulty: z.union([z.enum(["easy", "medium", "hard"]), z.null()]).default(null),
    rounds: z.union([z.number().int().gte(1).lte(10), z.null()]).default(null),
    drawingTimeLimit: z.union([z.number().int().gte(15).lte(180), z.null()]).default(null),
    guessingTimeLimit: z.union([z.number().int().gte(15).lte(180), z.null()]).default(null),
  }),
  z.object({
    type: z.literal("default_locale_update"),
    locale: z
      .string()
      .regex(/^[a-z]{2,5}(?:-[A-Za-z0-9]{2,8})?$/)
      .optional(),
  }),
  z
    .object({ type: z.literal("draw_stroke"), playerId: z.union([z.string(), z.null()]).default(null) })
    .catchall(z.any()),
  z.object({
    type: z.literal("draw_stroke_partial"),
    playerId: z.union([z.string(), z.null()]).default(null),
    stroke: z
      .union([
        z
          .object({
            color: z.string().max(32),
            width: z.number().gt(0).lte(64),
            points: z
              .array(z.object({ x: z.number(), y: z.number() }))
              .max(1000)
              .optional(),
          })
          .describe(
            "A stroke fragment: only the points added since the previous partial.\n\nSending deltas (rather than the whole growing point list every frame) keeps\nan in-progress stroke's relayed payload O(new points) instead of O(n^2).",
          ),
        z.null(),
      ])
      .default(null),
    strokeStart: z.boolean().default(false),
  }),
  z.object({ type: z.literal("drawpad_clear") }),
  z.object({ type: z.literal("pad_visibility"), visible: z.boolean().default(true) }),
  z.object({ type: z.literal("privacy_changed"), isPrivate: z.boolean() }),
  z.object({ type: z.literal("initiate_kick"), targetPlayerId: z.string() }),
  z.object({ type: z.literal("cast_kick_vote"), targetPlayerId: z.string() }),
  z.object({ type: z.literal("request_game_state"), playerId: z.union([z.string(), z.null()]).default(null) }),
  z.object({
    type: z.literal("reaction_send"),
    drawingId: z.string(),
    reactionKey: z.enum(["laugh", "shock", "art", "mind-blown", "think"]),
  }),
]);
export type ClientEvent = z.infer<typeof ClientEventSchema>;
