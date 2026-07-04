import { ref } from "vue";
import { useRouter } from "vue-router";
import {
  handleConnectionEvent,
  handleDrawingEvent,
  handleGameFlowEvent,
  handleKickEvent,
  handleResultsEvent,
} from "@/composables/connection/handlers";
import { useNotifications } from "@/composables/notifications";
import { BACKEND_HOST, UI_TIMINGS } from "@/config/gameConfig";
import { type ClientEvent, ClientEventSchema, type ServerEvent, ServerEventSchema } from "@/generated/protocol";
import { useGameStore } from "@/stores/game";

// Singleton WebSocket connection shared across all components
let ws: WebSocket | null = null;
const connectionError = ref<string | null>(null);
const lastJoinError = ref<{ error: string; message: string } | null>(null);
const currentRoomCode = ref<string | null>(null);
const isObserverConnection = ref(false);
let heartbeatInterval: number | null = null;
let stateRefreshInterval: number | null = null;

// Auto-reconnect state. The client treats a dropped socket as recoverable and
// re-runs the join handshake with exponential backoff, so transient drops and
// server restarts self-heal without losing the player's place in the game.
type ConnectionStatus = "disconnected" | "connecting" | "connected" | "reconnecting";
const connectionStatus = ref<ConnectionStatus>("disconnected");
let intentionalClose = false;
let reconnectTimer: number | null = null;
let reconnectAttempts = 0;
let lastRoomCode: string | null = null;
let lastConnectOptions: ConnectOptions = {};
const MAX_RECONNECT_ATTEMPTS = 12;
const RECONNECT_BASE_MS = 500;
const RECONNECT_MAX_MS = 5000;

type ConnectOptions = {
  observeOnly?: boolean;
  isRetry?: boolean;
};

export function useGameConnection() {
  const store = useGameStore();
  const router = useRouter();
  const { showNotification } = useNotifications();

  const ctx = {
    store,
    router,
    showNotification,
    send,
    isObserverConnection,
    stopStateRefresh,
  };

  function connect(roomCode: string, options: ConnectOptions = {}) {
    const normalizedRoomCode = roomCode.trim();
    if (!normalizedRoomCode) {
      if (import.meta.env.DEV) console.warn("[WebSocket] Refused to connect without a room code");
      return;
    }

    const observeOnly = options.observeOnly ?? false;
    // A fresh (non-retry) connect resets the backoff and re-arms auto-reconnect.
    if (!options.isRetry) reconnectAttempts = 0;
    intentionalClose = false;
    lastRoomCode = normalizedRoomCode;
    lastConnectOptions = { observeOnly };
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    connectionStatus.value = options.isRetry ? "reconnecting" : "connecting";

    if (ws) {
      ws.close();
    }
    store.setSpectatorMode(observeOnly);
    isObserverConnection.value = observeOnly;

    const url = `${BACKEND_HOST}/ws/${normalizedRoomCode}`;
    const socket = new WebSocket(url);
    ws = socket;
    currentRoomCode.value = normalizedRoomCode;

    socket.onopen = () => {
      if (ws !== socket) return;
      connectionStatus.value = "connected";
      reconnectAttempts = 0;
      connectionError.value = null;
      lastJoinError.value = null;

      if (!observeOnly) {
        store.addPlayer(store.localPlayerId, store.localPlayerName);
        send({
          type: "join",
          playerId: store.localPlayerId,
          name: store.localPlayerName,
          preferredLocale: store.localPlayerLocale,
          preferredColor: store.localPlayerColor,
        });
      } else {
        store.setSpectatorMode(true);
      }

      send({
        type: "request_game_state",
        playerId: store.localPlayerId || null,
      });

      startHeartbeat();
      if (observeOnly) {
        startStateRefresh(normalizedRoomCode);
      } else {
        stopStateRefresh();
      }
    };

    socket.onmessage = (event: MessageEvent) => {
      if (ws !== socket) return; // ignore messages queued on a superseded socket
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

    socket.onerror = (error) => {
      console.error("[WebSocket] Connection error:", error);
      connectionError.value = "Connection error occurred";
    };

    socket.onclose = (event) => {
      if (import.meta.env.DEV) console.log("[WebSocket] Connection closed:", event.code, event.reason);
      // Ignore the close of a socket we've already replaced (e.g. a fresh connect
      // or an in-flight retry superseded this one).
      if (ws !== socket) return;
      stopHeartbeat();
      stopStateRefresh();
      currentRoomCode.value = null;
      isObserverConnection.value = false;
      ws = null;

      // 1008 = server policy close (e.g. room full): retrying would loop, so stop.
      const terminal = event.code === 1008;
      const canReconnect =
        !intentionalClose && !terminal && Boolean(lastRoomCode) && reconnectAttempts < MAX_RECONNECT_ATTEMPTS;
      if (!canReconnect) {
        connectionStatus.value = "disconnected";
        return;
      }

      connectionStatus.value = "reconnecting";
      const delay = Math.min(RECONNECT_BASE_MS * 2 ** reconnectAttempts, RECONNECT_MAX_MS);
      reconnectAttempts += 1;
      reconnectTimer = window.setTimeout(() => {
        reconnectTimer = null;
        if (lastRoomCode) connect(lastRoomCode, { ...lastConnectOptions, isRetry: true });
      }, delay);
    };
  }

  function send(message: ClientEvent) {
    const result = ClientEventSchema.safeParse(message);
    if (!result.success) {
      console.error("[WebSocket] Refused to send invalid client event:", result.error.issues, "Raw:", message);
      return false;
    }
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(result.data));
      return true;
    }
    return false;
  }

  function handleMessage(message: ServerEvent) {
    if (import.meta.env.DEV) console.log("[WebSocket] Received:", message.type);

    switch (message.type) {
      case "join_error":
      case "host_restored":
      case "room_state":
      case "player_joined":
      case "player_left":
      case "player_presence":
      case "host_changed":
        handleConnectionEvent(message, ctx);
        break;

      case "start_game":
      case "start_round":
      case "start_guessing":
      case "round_complete":
      case "game_complete":
      case "restart_game":
      case "ready_status":
      case "settings_update":
      case "default_locale_update":
      case "room_custom_categories_update":
        handleGameFlowEvent(message, ctx);
        break;

      case "draw_stroke":
      case "draw_stroke_partial":
      case "drawpad_clear":
      case "pad_visibility":
        handleDrawingEvent(message, ctx);
        break;

      case "reaction_received":
        handleResultsEvent(message, ctx);
        break;

      case "kick_vote_started":
      case "kick_vote_updated":
      case "player_kicked":
      case "kick_vote_expired":
      case "kick_error":
        handleKickEvent(message, ctx);
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

  function startStateRefresh(roomCode: string) {
    stopStateRefresh();
    stateRefreshInterval = window.setInterval(() => {
      if (!ws || ws.readyState !== WebSocket.OPEN || currentRoomCode.value !== roomCode) {
        stopStateRefresh();
        return;
      }
      send({
        type: "request_game_state",
        playerId: store.localPlayerId || null,
      });
    }, 2000);
  }

  function stopStateRefresh() {
    if (stateRefreshInterval) {
      clearInterval(stateRefreshInterval);
      stateRefreshInterval = null;
    }
  }

  function disconnect() {
    // User-initiated leave: stop any pending auto-reconnect and stay closed.
    intentionalClose = true;
    reconnectAttempts = 0;
    lastRoomCode = null;
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    // Tell the server this is an intentional leave (immediate removal) rather
    // than a drop (which would keep us as a "reconnecting" presence).
    if (ws && ws.readyState === WebSocket.OPEN && !isObserverConnection.value) {
      send({ type: "leave" });
    }
    stopHeartbeat();
    stopStateRefresh();
    if (ws) {
      ws.close();
      ws = null;
    }
    connectionStatus.value = "disconnected";
    currentRoomCode.value = null;
    isObserverConnection.value = false;
    store.setSpectatorMode(false);
  }

  return {
    connectionStatus,
    connectionError,
    lastJoinError,
    currentRoomCode,
    connect,
    send,
    disconnect,
    // exposed for tests
    handleMessage,
  };
}
