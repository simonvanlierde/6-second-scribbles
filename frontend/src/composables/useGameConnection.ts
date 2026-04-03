import { ref } from "vue";
import { useRouter } from "vue-router";
import { useNotifications } from "@/composables/notifications";
import { BACKEND_HOST, GAME_SETTINGS, UI_TIMINGS } from "@/config/gameConfig";
import { type ClientEvent, type ServerEvent, ServerEventSchema } from "@/generated/protocol";
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
        const result = ServerEventSchema.safeParse(JSON.parse(event.data));
        if (!result.success) {
          console.error("[WebSocket] Invalid message from server:", result.error.issues, "Raw:", event.data);
          return;
        }
        handleMessage(result.data);
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

  function send(message: ClientEvent) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(message));
    }
  }

  // ── Connection & player events ────────────────────────────────────────────

  function handleConnectionEvent(message: ServerEvent) {
    switch (message.type) {
      case "join_error":
        showNotification(message.message || "Unable to join room", "error");
        console.error("[WebSocket] Join error:", message.message);
        setTimeout(() => router.push("/"), UI_TIMINGS.JOIN_ERROR_REDIRECT_MS);
        break;

      case "host_restored":
        console.log("[WebSocket] Host status restored");
        showNotification("Host status restored", "success");
        break;

      case "room_state":
        store.setPlayers(message.players);
        if (message.hostId) store.hostId = message.hostId;
        store.categories = message.categories ?? [];
        store.gamePhase = message.gamePhase;
        if (message.difficulty) store.difficulty = message.difficulty;
        if (message.maxRounds) store.maxRounds = message.maxRounds;
        if (message.roundStartTime) store.roundStartTime = message.roundStartTime;
        if (message.roundLength) store.roundLength = message.roundLength;
        if (message.padVisibility !== undefined) store.showPadForRoom = message.padVisibility;
        if (message.language) store.language = message.language;
        break;

      case "player_joined":
        store.setPlayers(message.players);
        if (message.isHost) store.hostId = message.playerId;
        break;

      case "player_left":
        store.removePlayer(message.playerId);
        break;

      case "host_changed":
        store.hostId = message.newHostId;
        break;
    }
  }

  // ── Game flow events ──────────────────────────────────────────────────────

  function handleGameFlowEvent(message: ServerEvent) {
    switch (message.type) {
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
          store.roundStartTime = message.roundStartTime;
          store.startRound(message.round ?? 1, message.cards);
          if (router.currentRoute.value.name !== "game") {
            router.push(`/game/${store.roomCode}`);
          }
        } else {
          console.error("[WebSocket] Invalid cards in start_round message:", message);
        }
        break;

      case "start_guessing":
        store.gamePhase = "guessing";
        break;

      case "round_complete":
        store.setRoundResults(message.results);
        store.updateScores(message.scores);
        store.gamePhase = "scoring";
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
        store.gamePhase = "lobby";
        break;

      case "ready_status":
        store.readyCount = message.readyCount;
        store.totalPlayers = message.totalPlayers;
        break;

      case "settings_update":
        if (message.difficulty) store.difficulty = message.difficulty;
        if (message.rounds !== null) store.maxRounds = message.rounds ?? store.maxRounds;
        if (message.roundLength !== null) store.roundLength = message.roundLength ?? store.roundLength;
        if (!store.isHost) {
          showNotification("Host updated game settings");
        }
        break;
    }
  }

  // ── Drawing events ────────────────────────────────────────────────────────

  function handleDrawingEvent(message: ServerEvent) {
    switch (message.type) {
      case "draw_stroke":
      case "draw_stroke_partial":
        if (message.stroke && message.playerId !== store.localPlayerId) {
          store.addStroke(message.stroke);
        }
        break;

      case "drawpad_clear":
        store.clearStrokes();
        break;

      case "pad_visibility":
        store.showPadForRoom = message.visible;
        store.showDrawpad = message.visible;
        if (!store.isHost) {
          showNotification(
            message.visible ? "Host showed the drawpad for the room" : "Host hid the drawpad for the room",
          );
        }
        break;
    }
  }

  // ── Kick & moderation events ──────────────────────────────────────────────

  function handleKickEvent(message: ServerEvent) {
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
          router.push("/");
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

      case "language_update":
        if (message.language) {
          store.language = message.language;
          if (!store.isHost) {
            const langNames: Record<string, string> = { en: "English", es: "Español", fr: "Français" };
            showNotification(`Language changed to ${langNames[message.language] || message.language}`);
          }
        }
        break;
    }
  }

  function handleMessage(message: ServerEvent) {
    if (import.meta.env.DEV) console.log("[WebSocket] Received:", message.type);

    switch (message.type) {
      case "join_error":
      case "host_restored":
      case "room_state":
      case "player_joined":
      case "player_left":
      case "host_changed":
        handleConnectionEvent(message);
        break;

      case "start_game":
      case "start_round":
      case "start_guessing":
      case "round_complete":
      case "game_complete":
      case "restart_game":
      case "ready_status":
      case "settings_update":
        handleGameFlowEvent(message);
        break;

      case "draw_stroke":
      case "draw_stroke_partial":
      case "drawpad_clear":
      case "pad_visibility":
        handleDrawingEvent(message);
        break;

      case "kick_vote_started":
      case "kick_vote_updated":
      case "player_kicked":
      case "kick_vote_expired":
      case "kick_error":
      case "language_update":
        handleKickEvent(message);
        break;
    }
  }

  function startHeartbeat() {
    stopHeartbeat();
    heartbeatInterval = window.setInterval(() => {
      send({ type: "heartbeat" });
    }, UI_TIMINGS.HEARTBEAT_INTERVAL_MS);
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
