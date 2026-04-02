import { ref } from "vue";
import { useRouter } from "vue-router";
import { useNotifications } from "@/composables/notifications";
import { BACKEND_HOST, GAME_SETTINGS } from "@/config/gameConfig";
import type { GameMessage } from "@/shared/types";
import { useGameStore } from "@/stores/game";

// Singleton WebSocket connection shared across all components
let ws: WebSocket | null = null;
const isConnected = ref(false);
const connectionError = ref<string | null>(null);
let heartbeatInterval: number | null = null;

export function useGameConnection() {
  const store = useGameStore();
  const router = useRouter();
  const { showNotification } = useNotifications();

  function connect(roomCode: string) {
    if (ws) {
      ws.close();
    }

    const url = `${BACKEND_HOST}/party/${roomCode}`;
    ws = new WebSocket(url);

    ws.onopen = () => {
      isConnected.value = true;
      connectionError.value = null;

      send({
        type: "join",
        playerId: store.localPlayerId,
        name: store.localPlayerName,
      });

      send({
        type: "request_game_state",
        playerId: store.localPlayerId,
      });

      startHeartbeat();
    };

    ws.onmessage = (event: MessageEvent) => {
      try {
        const message: GameMessage = JSON.parse(event.data);
        handleMessage(message);
      } catch (error) {
        console.error("[WebSocket] Failed to parse message:", error, "Raw:", event.data);
        connectionError.value = "Failed to process server message";
      }
    };

    ws.onerror = (error) => {
      console.error("[WebSocket] Connection error:", error);
      connectionError.value = "Connection error occurred";
      isConnected.value = false;
    };

    ws.onclose = (event) => {
      if (import.meta.env.DEV) console.log("[WebSocket] Connection closed:", event.code, event.reason);
      stopHeartbeat();
      isConnected.value = false;
    };
  }

  function send(message: GameMessage) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(message));
    }
  }

  function handleMessage(message: GameMessage) {
    if (import.meta.env.DEV) console.log("[WebSocket] Received:", message.type);

    switch (message.type) {
      case "join_error": {
        showNotification(message.message || "Unable to join room", "error");
        console.error("[WebSocket] Join error:", message.message);
        setTimeout(() => router.push("/"), 2000);
        break;
      }

      case "host_restored":
        console.log("[WebSocket] Host status restored");
        showNotification("Host status restored", "success");
        break;

      case "room_state":
        store.setPlayers(message.players);
        if (message.hostId) store.setHost(message.hostId);
        store.setCategories(message.categories);
        store.setGamePhase(message.gamePhase);
        if (message.difficulty) store.setDifficulty(message.difficulty);
        if (message.maxRounds) store.setMaxRounds(message.maxRounds);
        if (message.roundStartTime) store.setRoundStartTime(message.roundStartTime);
        if (message.roundLength) store.setRoundLength(message.roundLength);
        if (message.padVisibility !== undefined) store.setShowPadForRoom(message.padVisibility);
        if (message.language) store.setLanguage(message.language);
        break;

      case "player_joined":
        store.setPlayers(message.players);
        if (message.isHost) store.setHost(message.playerId);
        break;

      case "player_left":
        store.removePlayer(message.playerId);
        break;

      case "host_changed":
        store.setHost(message.newHostId);
        break;

      case "start_game":
        store.startGame(
          message.difficulty || GAME_SETTINGS.difficulty.DEFAULT,
          message.rounds || GAME_SETTINGS.rounds.DEFAULT,
          message.roundLength || GAME_SETTINGS.roundLengthSeconds.DEFAULT,
        );
        router.push(`/game/${store.roomCode}`);
        break;

      case "start_round":
        if (typeof message.cards === "object" && message.cards !== null) {
          store.setRoundStartTime(message.roundStartTime);
          store.startRound(message.round, message.cards);
          if (router.currentRoute.value.name !== "game") {
            router.push(`/game/${store.roomCode}`);
          }
        } else {
          console.error("[WebSocket] Invalid cards in start_round message:", message);
        }
        break;

      case "drawing_complete":
        store.setPlayerDrawing(message.playerId, message.drawing);
        break;

      case "start_guessing":
        store.setRoundStartTime(message.roundStartTime);
        store.setGamePhase("guessing");
        break;

      case "round_complete":
        store.setRoundResults(message.results);
        store.updateScores(message.scores);
        store.setGamePhase("scoring");
        router.push(`/round-results/${store.roomCode}`);
        // RoundResultsView owns the 5-second countdown and calls startRound from there.
        break;

      case "game_complete":
        store.updateScores(message.finalScores);
        store.endGame();
        router.push(`/results/${store.roomCode}`);
        break;

      case "restart_game":
        store.resetRound();
        store.setGamePhase("lobby");
        break;

      case "ready_status":
        store.setReadyStatus(message.readyCount, message.totalPlayers);
        break;

      case "settings_update":
        store.setDifficulty(message.difficulty);
        store.setMaxRounds(message.rounds);
        store.setRoundLength(message.roundLength);
        if (!store.isHost) {
          showNotification("Host updated game settings");
        }
        break;

      case "draw_stroke":
      case "draw_stroke_partial":
        if (message.stroke && message.playerId !== store.localPlayerId) {
          store.addStroke(message.stroke);
        }
        break;

      case "drawpad_clear":
        store.clearStrokes();
        break;

      case "pad_visibility": {
        store.setShowPadForRoom(message.visible);
        store.setShowDrawpad(message.visible);
        if (!store.isHost) {
          showNotification(
            message.visible ? "Host showed the drawpad for the room" : "Host hid the drawpad for the room",
          );
        }
        break;
      }

      case "kick_vote_started": {
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
      }

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
          router.push("/");
        } else {
          showNotification(`${message.playerName} was kicked from the room`);
        }
        break;

      case "kick_vote_expired":
        store.removeKickVote(message.targetPlayerId);
        showNotification(`Kick vote for ${message.targetPlayerName} expired`);
        break;

      case "kick_error":
        showNotification(message.error || "Failed to process kick request", "error");
        break;

      case "language_update": {
        if (message.language) {
          store.setLanguage(message.language);
          if (!store.isHost) {
            const langNames: Record<string, string> = { en: "English", es: "Español", fr: "Français" };
            showNotification(`Language changed to ${langNames[message.language] || message.language}`);
          }
        }
        break;
      }

      case "custom_category_added":
        store.setCategories([...store.categories, message.category.name]);
        showNotification(`Added custom category: ${message.category.name}`);
        break;

      case "custom_category_removed":
        store.setCategories(store.categories.filter((name) => name !== message.category_name));
        showNotification(`Removed custom category: ${message.category_name}`);
        break;
    }
  }

  function startHeartbeat() {
    stopHeartbeat();
    heartbeatInterval = window.setInterval(() => {
      send({ type: "heartbeat", playerId: store.localPlayerId });
    }, 60000);
  }

  function stopHeartbeat() {
    if (heartbeatInterval) {
      clearInterval(heartbeatInterval);
      heartbeatInterval = null;
    }
  }

  function disconnect() {
    stopHeartbeat();
    if (ws) {
      ws.close();
      ws = null;
    }
    isConnected.value = false;
  }

  return {
    isConnected,
    connectionError,
    connect,
    send,
    disconnect,
    // exposed for tests
    handleMessage,
  };
}
