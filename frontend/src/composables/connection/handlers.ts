/**
 * Pure WebSocket message handler.
 *
 * It receives the store and the callbacks it needs, so it is testable in
 * isolation without a live WebSocket connection.
 */

import type { Router } from "vue-router";

import type { NotificationType } from "@/composables/notifications";
import { useReactions } from "@/composables/useReactions";
import { UI_TIMINGS } from "@/config/gameConfig";
import type { ClientEvent, ServerEvent } from "@/generated/protocol";
import { i18n } from "@/i18n";
import { formatLocaleLabel } from "@/shared/locales";
import { createLogger } from "@/shared/logger";
import type { useGameStore } from "@/stores/game";

const log = createLogger("WebSocket");

type ShowNotification = (text: string, type?: NotificationType, duration?: number) => void;

export type HandlerContext = {
  store: ReturnType<typeof useGameStore>;
  router: Router;
  showNotification: ShowNotification;
  send: (message: ClientEvent) => void;
};

/** Apply one validated server event to the store; events the client does not act on are ignored. */
export function handleServerEvent(message: ServerEvent, ctx: HandlerContext): void {
  const { store, router, showNotification } = ctx;

  switch (message.type) {
    // ── Connection & players ──

    case "join_error":
      if (message.error === "game_in_progress") {
        showNotification(message.message || i18n.global.t("notifications.roundInProgressJoinLater"), "info");
        break;
      }

      showNotification(
        message.error === "spectators_full"
          ? i18n.global.t("notifications.spectatorsFull")
          : message.error === "seats_busy"
            ? i18n.global.t("notifications.seatsBusy")
            : message.message || i18n.global.t("notifications.unableToJoinRoom"),
        "error",
      );
      log.error("Join error:", message.message);
      setTimeout(() => router.push({ name: "home" }), UI_TIMINGS.JOIN_ERROR_REDIRECT_MS);
      break;

    case "host_restored":
      log.info("Host status restored");
      showNotification(i18n.global.t("notifications.hostStatusRestored"), "success");
      break;

    case "room_state":
      store.applyRoomState(message);
      break;

    case "player_joined":
      store.setPlayers(message.players);
      if (message.isHost) store.setHost(message.playerId);
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

    // ── Game flow ──

    case "start_game":
      store.onStartGame(message);
      break;

    case "start_round":
      if (typeof message.cards === "object" && message.cards !== null) {
        store.onStartRound(message);
      } else {
        log.error("Invalid cards in start_round message:", message);
      }
      break;

    case "start_guessing":
      store.onStartGuessing(message);
      break;

    case "round_complete":
      useReactions().clear(); // drop the previous round's reactions before showing this one
      store.onRoundComplete(message);
      break;

    case "game_complete":
      store.onGameComplete(message);
      break;

    case "restart_game":
      store.onRestartGame();
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

    // ── Drawing ──

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

    // ── Reactions ──

    case "reaction_received":
      useReactions().add(message.drawingId, message.reactionKey);
      break;

    // ── Kick votes & moderation ──

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

    case "protocol_error":
      // The server drops oversized frames; without this a drawing that did not
      // fit would vanish and guessers would wait for it forever.
      if (message.error === "payload_too_large")
        showNotification(i18n.global.t("notifications.drawingTooLarge"), "error", 8000);
      else log.warn("Server rejected a message:", message.error);
      break;
  }
}
