/**
 * Pure WebSocket message handlers.
 *
 * Each function receives the store and necessary callbacks so they are
 * testable in isolation without needing a live WebSocket connection.
 */

import type { Ref } from "vue";
import type { Router } from "vue-router";

import type { NotificationType } from "@/composables/notifications";
import { GAME_SETTINGS, UI_TIMINGS } from "@/config/gameConfig";
import type { ClientEvent, ServerEventGroup, ServerEventOf } from "@/generated/protocol";
import { formatLocaleLabel } from "@/shared/locales";
import type { useGameStore } from "@/stores/game";

export type ShowNotification = (text: string, type?: NotificationType, duration?: number) => void;

export type HandlerContext = {
  store: ReturnType<typeof useGameStore>;
  router: Router;
  showNotification: ShowNotification;
  send: (message: ClientEvent) => void;
  isObserverConnection: Ref<boolean>;
  stopStateRefresh: () => void;
};

// ── Event type aliases ────────────────────────────────────────────────────────

type ConnectionEvent = ServerEventGroup<"connection"> | ServerEventOf<"host_changed">;
type GameFlowEvent = ServerEventOf<
  | "start_game"
  | "start_round"
  | "start_guessing"
  | "round_complete"
  | "game_complete"
  | "restart_game"
  | "ready_status"
  | "settings_update"
  | "default_locale_update"
  | "room_custom_categories_update"
>;
type DrawingEvent = ServerEventGroup<"drawing">;
type KickEvent = ServerEventGroup<"moderation">;

// ── Connection & player events ────────────────────────────────────────────────

export function handleConnectionEvent(message: ConnectionEvent, ctx: HandlerContext): void {
  const { store, router, showNotification, isObserverConnection, stopStateRefresh } = ctx;

  switch (message.type) {
    case "join_error":
      if (message.error === "game_in_progress") {
        showNotification(message.message || "This round is already in progress. You can join next round.", "info");
        break;
      }

      if (message.error === "room_full" && isObserverConnection.value) {
        showNotification(message.message || "This room is full, but you can keep watching.", "error");
        break;
      }

      showNotification(message.message || "Unable to join room", "error");
      console.error("[WebSocket] Join error:", message.message);
      setTimeout(() => router.push({ name: "home" }), UI_TIMINGS.JOIN_ERROR_REDIRECT_MS);
      break;

    case "host_restored":
      console.log("[WebSocket] Host status restored");
      showNotification("Host status restored", "success");
      break;

    case "room_state":
      store.applyRoomState(message);
      break;

    case "player_joined":
      store.setPlayers(message.players);
      if (message.isHost) store.setHost(message.playerId);
      if (store.pendingLocalPlayerId === message.playerId) {
        store.confirmPendingLocalPlayer(message.playerId);
        store.setSpectatorMode(false);
        isObserverConnection.value = false;
        stopStateRefresh();
      }
      break;

    case "player_left":
      store.removePlayer(message.playerId);
      break;

    case "host_changed":
      store.setHost(message.newHostId);
      if (message.newHostId === store.localPlayerId) {
        showNotification("You are now the host", "success");
      } else {
        const nextHost = store.players.get(message.newHostId);
        showNotification(nextHost ? `${nextHost.name} is now the host` : "Host changed");
      }
      break;
  }
}

// ── Game flow events ──────────────────────────────────────────────────────────

export function handleGameFlowEvent(message: GameFlowEvent, ctx: HandlerContext): void {
  const { store, showNotification } = ctx;

  switch (message.type) {
    case "start_game":
      store.startGame(
        message.difficulty || GAME_SETTINGS.difficulty.DEFAULT,
        message.rounds || GAME_SETTINGS.rounds.DEFAULT,
        message.drawingTimeLimit || GAME_SETTINGS.drawingTimeLimitSeconds.DEFAULT,
        message.guessingTimeLimit || GAME_SETTINGS.guessingTimeLimitSeconds.DEFAULT,
      );
      break;

    case "start_round":
      if (typeof message.cards === "object" && message.cards !== null) {
        store.roundStartTime = message.roundStartTime;
        store.startRound(message.round ?? 1, message.cards);
      } else {
        console.error("[WebSocket] Invalid cards in start_round message:", message);
      }
      break;

    case "start_guessing":
      if (typeof store.startGuessing === "function") {
        store.startGuessing(message.guessingStartTime, message.guessTargets ?? {});
      } else {
        // HMR can briefly keep an older Pinia store instance alive while this
        // module has already reloaded, so fall back to direct state updates.
        store.gamePhase = "guessing";
        store.guessingStartTime = message.guessingStartTime ?? Date.now();
        store.guessTargets = message.guessTargets ?? {};
        store.readyCount = 0;
        store.totalPlayers = store.playersList.length;
      }
      break;

    case "round_complete":
      store.setRoundResults(message.results);
      store.updateScores(message.scores);
      store.gamePhase = "round_results";
      store.readyCount = 0;
      store.totalPlayers = store.playersList.length;
      // RoundResultsView owns the 5-second countdown and calls startRound from there.
      break;

    case "game_complete":
      store.updateScores(message.finalScores);
      store.endGame();
      break;

    case "restart_game":
      store.resetRound();
      store.gamePhase = "lobby";
      break;

    case "ready_status":
      store.setReadyStatus(message.readyCount, message.totalPlayers);
      break;

    case "settings_update":
      store.applySettingsUpdate(message);
      if (!store.isHost) {
        showNotification("Host updated game settings");
      }
      break;

    case "default_locale_update":
      if (message.locale) {
        store.setDefaultLocale(message.locale);
        if (!store.isHost) {
          showNotification(`Room language changed to ${formatLocaleLabel(message.locale)}`);
        }
      }
      break;

    case "room_custom_categories_update":
      store.setCustomCategoryIds(message.categoryIds ?? null);
      break;
  }
}

// ── Drawing events ────────────────────────────────────────────────────────────

export function handleDrawingEvent(message: DrawingEvent, ctx: HandlerContext): void {
  const { store, showNotification } = ctx;

  switch (message.type) {
    case "draw_stroke":
    case "draw_stroke_partial":
      if (typeof message.drawing === "string" && message.playerId && message.playerId !== store.localPlayerId) {
        store.setPlayerDrawing(message.playerId, message.drawing);
        break;
      }

      if (message.stroke && message.playerId !== store.localPlayerId) {
        store.addStroke(message.stroke);
      }
      break;

    case "drawpad_clear":
      store.clearStrokes();
      break;

    case "pad_visibility":
      store.setRoomPadVisible(message.visible);
      if (!store.isHost) {
        showNotification(
          message.visible ? "Host showed the drawpad for the room" : "Host hid the drawpad for the room",
        );
      }
      break;
  }
}

// ── Kick & moderation events ──────────────────────────────────────────────────

export function handleKickEvent(message: KickEvent, ctx: HandlerContext): void {
  const { store, router, showNotification } = ctx;

  switch (message.type) {
    case "kick_vote_started":
      store.startKickVote(message.targetPlayerId, {
        currentVotes: message.currentVotes,
        requiredVotes: message.requiredVotes,
        expiresAt: message.expiresAt,
      });
      if (message.initiatorId === store.localPlayerId) {
        showNotification(`Started kick vote for ${message.targetPlayerName}`);
      } else {
        showNotification(`Kick vote started for ${message.targetPlayerName}`);
      }
      break;

    case "kick_vote_updated":
      store.updateKickVote(message.targetPlayerId, {
        currentVotes: message.currentVotes,
        requiredVotes: message.requiredVotes,
      });
      break;

    case "player_kicked":
      store.removePlayer(message.playerId);
      store.removeKickVote(message.playerId);
      if (message.playerId === store.localPlayerId) {
        showNotification("You have been kicked from the room", "error");
        store.reset();
        router.push({ name: "home" });
      } else {
        showNotification(`${message.playerName} was kicked from the room`);
      }
      break;

    case "kick_vote_expired":
      store.removeKickVote(message.targetPlayerId);
      showNotification(`Kick vote for ${message.targetPlayerId} expired`);
      break;

    case "kick_error":
      showNotification(message.error || "Failed to process kick request", "error");
      break;
  }
}
