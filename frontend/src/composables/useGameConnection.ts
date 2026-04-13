import { useNotifications } from "@/composables/notifications";
import { BACKEND_HOST, GAME_SETTINGS, UI_TIMINGS } from "@/config/gameConfig";
import {
	type ClientEvent,
	type ServerEvent,
	type ServerEventGroup,
	type ServerEventOf,
	ServerEventSchema,
} from "@/generated/protocol";
import { formatLocaleLabel } from "@/shared/locales";
import { useGameStore } from "@/stores/game";
import { ref } from "vue";
import { useRouter } from "vue-router";

// Singleton WebSocket connection shared across all components
let ws: WebSocket | null = null;
const isConnected = ref(false);
const connectionError = ref<string | null>(null);
const lastJoinError = ref<{ error: string; message: string } | null>(null);
const currentRoomCode = ref<string | null>(null);
const isObserverConnection = ref(false);
let heartbeatInterval: number | null = null;
let stateRefreshInterval: number | null = null;

type ConnectionEvent =
	| ServerEventGroup<"connection">
	| ServerEventOf<"host_changed">;
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
type ConnectOptions = {
	observeOnly?: boolean;
};

export function useGameConnection() {
	const store = useGameStore();
	const router = useRouter();
	const { showNotification } = useNotifications();

	function connect(roomCode: string, options: ConnectOptions = {}) {
		const observeOnly = options.observeOnly ?? false;
		if (ws) {
			ws.close();
		}
		store.setSpectatorMode(observeOnly);
		isObserverConnection.value = observeOnly;

		const url = `${BACKEND_HOST}/ws/${roomCode}`;
		const socket = new WebSocket(url);
		ws = socket;
		currentRoomCode.value = roomCode;

		socket.onopen = () => {
			if (ws !== socket) return;
			isConnected.value = true;
			connectionError.value = null;
			lastJoinError.value = null;

			if (!observeOnly) {
				send({
					type: "join",
					playerId: store.localPlayerId,
					name: store.localPlayerName,
					preferredLocale: store.localPlayerLocale,
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
				startStateRefresh(roomCode);
			} else {
				stopStateRefresh();
			}
		};

		socket.onmessage = (event: MessageEvent) => {
			try {
				const result = ServerEventSchema.safeParse(JSON.parse(event.data));
				if (!result.success) {
					console.error(
						"[WebSocket] Invalid message from server:",
						result.error.issues,
						"Raw:",
						event.data,
					);
					return;
				}
				handleMessage(result.data);
			} catch (error) {
				console.error(
					"[WebSocket] Failed to parse message:",
					error,
					"Raw:",
					event.data,
				);
				connectionError.value = "Failed to process server message";
			}
		};

		socket.onerror = (error) => {
			console.error("[WebSocket] Connection error:", error);
			connectionError.value = "Connection error occurred";
			isConnected.value = false;
		};

		socket.onclose = (event) => {
			if (import.meta.env.DEV)
				console.log("[WebSocket] Connection closed:", event.code, event.reason);
			if (ws === socket) {
				stopHeartbeat();
				stopStateRefresh();
				isConnected.value = false;
				currentRoomCode.value = null;
				isObserverConnection.value = false;
				ws = null;
			}
		};
	}

	function send(message: ClientEvent) {
		if (ws && ws.readyState === WebSocket.OPEN) {
			ws.send(JSON.stringify(message));
		}
	}

	function startStateRefresh(roomCode: string) {
		stopStateRefresh();
		stateRefreshInterval = window.setInterval(() => {
			if (
				!ws ||
				ws.readyState !== WebSocket.OPEN ||
				currentRoomCode.value !== roomCode
			) {
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

	// ── Connection & player events ────────────────────────────────────────────

	function handleConnectionEvent(message: ConnectionEvent) {
		switch (message.type) {
			case "join_error":
				lastJoinError.value = {
					error: message.error,
					message: message.message || "",
				};
				if (message.error === "game_in_progress") {
					showNotification(
						message.message ||
							"This round is already in progress. You can join next round.",
						"info",
					);
					break;
				}

				if (message.error === "room_full" && isObserverConnection.value) {
					showNotification(
						message.message || "This room is full, but you can keep watching.",
						"error",
					);
					break;
				}

				showNotification(message.message || "Unable to join room", "error");
				console.error("[WebSocket] Join error:", message.message);
				setTimeout(
					() => router.push({ name: "home" }),
					UI_TIMINGS.JOIN_ERROR_REDIRECT_MS,
				);
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
				break;
		}
	}

	// ── Game flow events ──────────────────────────────────────────────────────

	function handleGameFlowEvent(message: GameFlowEvent) {
		switch (message.type) {
			case "start_game":
				store.startGame(
					message.difficulty || GAME_SETTINGS.difficulty.DEFAULT,
					message.rounds || GAME_SETTINGS.rounds.DEFAULT,
					message.drawingTimeLimit ||
						GAME_SETTINGS.drawingTimeLimitSeconds.DEFAULT,
					message.guessingTimeLimit ||
						GAME_SETTINGS.guessingTimeLimitSeconds.DEFAULT,
				);
				break;

			case "start_round":
				if (typeof message.cards === "object" && message.cards !== null) {
					store.roundStartTime = message.roundStartTime;
					store.startRound(message.round ?? 1, message.cards);
				} else {
					console.error(
						"[WebSocket] Invalid cards in start_round message:",
						message,
					);
				}
				break;

			case "start_guessing":
				if (typeof store.startGuessing === "function") {
					store.startGuessing(
						message.guessingStartTime,
						message.guessTargets ?? {},
					);
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
						showNotification(
							`Room language changed to ${formatLocaleLabel(message.locale)}`,
						);
					}
				}
				break;

			case "room_custom_categories_update":
				store.setCustomCategoryIds(message.categoryIds ?? null);
				break;
		}
	}

	// ── Drawing events ────────────────────────────────────────────────────────

	function handleDrawingEvent(message: DrawingEvent) {
		switch (message.type) {
			case "draw_stroke":
			case "draw_stroke_partial":
				if (
					typeof message.drawing === "string" &&
					message.playerId &&
					message.playerId !== store.localPlayerId
				) {
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
						message.visible
							? "Host showed the drawpad for the room"
							: "Host hid the drawpad for the room",
					);
				}
				break;
		}
	}

	// ── Kick & moderation events ──────────────────────────────────────────────

	function handleKickEvent(message: KickEvent) {
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
				showNotification(
					message.error || "Failed to process kick request",
					"error",
				);
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
			case "default_locale_update":
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
		stopStateRefresh();
		if (ws) {
			ws.close();
			ws = null;
		}
		isConnected.value = false;
		currentRoomCode.value = null;
		isObserverConnection.value = false;
		store.setSpectatorMode(false);
	}

	return {
		isConnected,
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
