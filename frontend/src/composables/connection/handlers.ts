/**
 * Pure WebSocket message handlers.
 *
 * Each function receives the store and necessary callbacks so they are
 * testable in isolation without needing a live WebSocket connection.
 */

import type { Ref } from "vue";
import type { Router } from "vue-router";

import type { NotificationType } from "@/composables/notifications";
import { REACTION_KEYS, type ReactionKey, useReactions } from "@/composables/useReactions";
import { GAME_SETTINGS, UI_TIMINGS } from "@/config/gameConfig";
import type { ClientEvent, ServerEventGroup, ServerEventOf } from "@/generated/protocol";
import { i18n } from "@/i18n";
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
type ResultsEvent = ServerEventGroup<"results">;

function isReactionKey(key: string): key is ReactionKey {
  return (REACTION_KEYS as readonly string[]).includes(key);
}

// ── Connection & player events ────────────────────────────────────────────────

export function handleConnectionEvent(message: ConnectionEvent, ctx: HandlerContext): void {
  const { store, router, showNotification, isObserverConnection, stopStateRefresh } = ctx;

  switch (message.type) {
    case "join_error":
      if (message.error === "game_in_progress") {
        showNotification(message.message || i18n.global.t("notifications.roundInProgressJoinLater"), "info");
        break;
      }

      if (message.error === "room_full" && isObserverConnection.value) {
        showNotification(message.message || i18n.global.t("notifications.roomFullWatchOnly"), "error");
        break;
      }

      showNotification(message.message || i18n.global.t("notifications.unableToJoinRoom"), "error");
      console.error("[WebSocket] Join error:", message.message);
      setTimeout(() => router.push({ name: "home" }), UI_TIMINGS.JOIN_ERROR_REDIRECT_MS);
      break;

    case "host_restored":
      console.log("[WebSocket] Host status restored");
      showNotification(i18n.global.t("notifications.hostStatusRestored"), "success");
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
      // Ignore a "left" for ourselves: it is a stale teardown from a previous
      // socket during reconnect, and acting on it would wipe us from the room.
      if (message.playerId !== store.localPlayerId) store.removePlayer(message.playerId);
      break;

    case "player_presence":
      // A peer dropped or came back; keep them in the roster, just flag presence.
      if (message.playerId !== store.localPlayerId) store.setPlayerConnected(message.playerId, message.connected);
      break;

    case "host_changed":
      store.setHost(message.newHostId);
      if (message.newHostId === store.localPlayerId) {
        showNotification(i18n.global.t("notifications.youAreNowHost"), "success");
      } else {
        const nextHost = store.players.get(message.newHostId);
        showNotification(
          nextHost
            ? i18n.global.t("notifications.hostChanged", {
                name: nextHost.name,
              })
            : i18n.global.t("notifications.hostChangedFallback"),
        );
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
      useReactions().clear(); // drop the previous round's reactions before showing this one
      store.setRoundResults(message.results);
      store.setRoundHighlights(message.highlights ?? null);
      store.updateScores(message.scores);
      // Snapshot this round's drawings for the end-of-game gallery before the
      // next start_round clears them. currentRound still names the finished round.
      store.captureRoundDrawings(store.currentRound);
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
        showNotification(i18n.global.t("notifications.hostUpdatedSettings"));
      }
      break;

    case "default_locale_update":
      if (message.locale) {
        store.setDefaultLocale(message.locale);
        if (!store.isHost) {
          showNotification(
            i18n.global.t("notifications.roomLanguageChanged", {
              locale: formatLocaleLabel(message.locale),
            }),
          );
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
      // A completed stroke carries the full PNG for the shared/round drawing.
      if (typeof message.drawing === "string" && message.playerId && message.playerId !== store.localPlayerId) {
        store.setPlayerDrawing(message.playerId, message.drawing);
      }
      break;

    case "draw_stroke_partial":
      // An in-progress stroke arrives as delta fragments; append them to the
      // sender's active stroke (a new stroke when strokeStart is set).
      if (message.stroke && message.playerId && message.playerId !== store.localPlayerId) {
        store.applyPartialStroke(
          message.playerId,
          {
            color: message.stroke.color,
            width: message.stroke.width,
            points: message.stroke.points ?? [],
          },
          message.strokeStart ?? false,
        );
      }
      break;

    case "drawpad_clear":
      store.clearStrokes();
      break;

    case "pad_visibility":
      store.setRoomPadVisible(message.visible);
      if (!store.isHost) {
        showNotification(i18n.global.t(message.visible ? "notifications.drawpadShown" : "notifications.drawpadHidden"));
      }
      break;
  }
}

// ── Results events (reactions) ────────────────────────────────────────────────

export function handleResultsEvent(message: ResultsEvent, _ctx: HandlerContext): void {
  switch (message.type) {
    case "reaction_received":
      if (isReactionKey(message.reactionKey)) {
        useReactions().add(message.drawingId, message.reactionKey);
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
        showNotification(
          i18n.global.t("moderation.kickVoteStartedByYou", {
            name: message.targetPlayerName,
          }),
        );
      } else {
        showNotification(
          i18n.global.t("moderation.kickVoteStarted", {
            name: message.targetPlayerName,
          }),
        );
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
        showNotification(i18n.global.t("moderation.youWereKicked"), "error");
        store.reset();
        router.push({ name: "home" });
      } else {
        showNotification(
          i18n.global.t("moderation.playerKicked", {
            name: message.playerName,
          }),
        );
      }
      break;

    case "kick_vote_expired": {
      // The event carries only the id, so resolve the display name from the store
      // (falling back to a generic label rather than showing a raw player id).
      const targetName = store.players.get(message.targetPlayerId)?.name ?? i18n.global.t("common.unknown");
      store.removeKickVote(message.targetPlayerId);
      showNotification(i18n.global.t("moderation.kickVoteExpired", { name: targetName }));
      break;
    }

    case "kick_error":
      showNotification(message.error || i18n.global.t("moderation.kickRequestFailed"), "error");
      break;
  }
}
