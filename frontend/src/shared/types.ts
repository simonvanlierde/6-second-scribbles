/**
 * Shared types for Six Second Scribbles
 * Used by both client and server
 */

import type { Difficulty as ContractDifficulty, GamePhase as ContractGamePhase } from "@/generated/api";
import type { ServerEventOf } from "@/generated/protocol";

type RoomState = ServerEventOf<"room_state">;
type RoundComplete = ServerEventOf<"round_complete">;

export type Card = ServerEventOf<"start_round">["cards"][string];

export type Difficulty = ContractDifficulty;
export type GamePhase = ContractGamePhase;

export interface Player {
  id: string;
  name: string;
  score: number;
  color: string;
  currentCard?: Card;
  drawing?: string; // Base64 data URL of canvas drawing
  connected: boolean; // false while disconnected/"reconnecting"
}

export type RoundResult = RoundComplete["results"][number];
export type RoundHighlights = NonNullable<RoundComplete["highlights"]>;
export type RoundHighlight = NonNullable<RoundHighlights["bestGuesser"]>;

export type HighlightKind = "bestGuesser" | "speedDemon" | "wildestMiss";

export type KickVote = Pick<ServerEventOf<"kick_vote_started">, "currentVotes" | "requiredVotes" | "expiresAt">;

export type DrawStroke = Required<NonNullable<RoomState["lobbyStrokes"]>[number]>;

/** One drawing in the end-of-game gallery; the store fills in a colour the server left out. */
export type GalleryDrawing = Omit<NonNullable<RoomState["drawingHistory"]>[number], "color"> & { color: string };
