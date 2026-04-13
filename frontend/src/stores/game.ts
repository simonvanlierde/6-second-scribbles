import { defineStore } from "pinia";
import { computed, ref, watch } from "vue";

import { GAME_SETTINGS, STORAGE_KEYS } from "@/config/gameConfig";
import { normalizeGamePhase } from "@/shared/gamePhase";
import type {
	Card,
	Difficulty,
	DrawStroke,
	KickVote,
	Player,
	RoundResult,
} from "@/shared/types";

function getBrowserLocale(): string {
	if (typeof navigator === "undefined" || !navigator.language) {
		return "en";
	}

	return navigator.language.split("-")[0]?.toLowerCase() || "en";
}

export const useGameStore = defineStore("game", () => {
	// Load from localStorage if available (guard for test environments where localStorage may be limited)
	const savedState = (() => {
		try {
			return localStorage.getItem(STORAGE_KEYS.GAME_STATE);
		} catch {
			return null;
		}
	})();
	const initialState = savedState ? JSON.parse(savedState) : null;

	// Load user's name from localStorage
	const savedName =
		(() => {
			try {
				return (
					localStorage.getItem(STORAGE_KEYS.PLAYER_NAME) ||
					initialState?.localPlayerName ||
					null
				);
			} catch {
				return initialState?.localPlayerName || null;
			}
		})() || "";
	const localPlayerName = ref<string>(savedName);

	// State
	const roomCode = ref<string>(initialState?.roomCode || "");
	const localPlayerId = ref<string>(initialState?.localPlayerId || "");
	const localPlayerLocale = ref<string>(
		initialState?.localPlayerLocale || getBrowserLocale(),
	);
	const players = ref<Map<string, Player>>(new Map());
	const pendingLocalPlayerId = ref<string | null>(null);
	const pendingLocalPlayerName = ref<string | null>(null);
	const hostId = ref<string | null>(null);
	const currentRound = ref<number>(initialState?.currentRound || 0);
	const maxRounds = ref<number>(
		initialState?.maxRounds || GAME_SETTINGS.rounds.DEFAULT,
	);
	const difficulty = ref<Difficulty>(
		initialState?.difficulty || GAME_SETTINGS.difficulty.DEFAULT,
	);
	const gamePhase = ref(normalizeGamePhase(initialState?.gamePhase));
	const drawingTimeLimit = ref<number>(
		initialState?.drawingTimeLimit ||
			GAME_SETTINGS.drawingTimeLimitSeconds.DEFAULT,
	);
	const guessingTimeLimit = ref<number>(
		initialState?.guessingTimeLimit ||
			GAME_SETTINGS.guessingTimeLimitSeconds.DEFAULT,
	);
	const roundStartTime = ref<number | undefined>(initialState?.roundStartTime);
	const guessingStartTime = ref<number | undefined>(
		initialState?.guessingStartTime,
	);
	const guessTargets = ref<Record<string, string>>(
		initialState?.guessTargets || {},
	);
	const currentStrokes = ref<DrawStroke[]>([]);
	const localPadVisible = ref<boolean>(initialState?.localPadVisible ?? true);
	const roomPadVisible = ref<boolean>(true);
	const localPlayerCard = ref<Card | undefined>();
	const isSpectatorMode = ref<boolean>(false);
	const lastRoundResults = ref<RoundResult[]>([]);
	const categories = ref<string[]>([]);
	const readyCount = ref<number>(0);
	const totalPlayers = ref<number>(0);
	const defaultLocale = ref<string>(initialState?.defaultLocale || "en");
	const customCategoryIds = ref<number[] | null>(
		initialState?.customCategoryIds ?? null,
	);
	const isPrivateRoom = ref<boolean>(false);
	const kickVotes = ref<Map<string, KickVote>>(new Map());

	// Computed
	const localPlayer = computed(() => players.value.get(localPlayerId.value));
	const playersList = computed(() => Array.from(players.value.values()));
	const canStartGame = computed(
		() => players.value.size >= 2 && gamePhase.value === "lobby",
	);
	const isHost = computed(() => hostId.value === localPlayerId.value);

	// Actions
	function setLocalPlayer(id: string, name: string) {
		localPlayerId.value = id;
		localPlayerName.value = name;
		try {
			localStorage.setItem(STORAGE_KEYS.PLAYER_NAME, name);
		} catch {
			/* unavailable */
		}
	}

	function setSpectatorMode(visible: boolean) {
		isSpectatorMode.value = visible;
	}

	function setPendingLocalPlayer(id: string, name: string) {
		pendingLocalPlayerId.value = id;
		pendingLocalPlayerName.value = name;
	}

	function clearPendingLocalPlayer() {
		pendingLocalPlayerId.value = null;
		pendingLocalPlayerName.value = null;
	}

	function confirmPendingLocalPlayer(id: string) {
		if (pendingLocalPlayerId.value !== id || !pendingLocalPlayerName.value)
			return;

		setLocalPlayer(id, pendingLocalPlayerName.value);
		clearPendingLocalPlayer();
		saveState();
	}

	function setRoomCode(code: string) {
		roomCode.value = code;
	}

	function addPlayer(id: string, name: string) {
		if (!players.value.has(id)) {
			const next = new Map(players.value);
			next.set(id, { id, name, score: 0 });
			players.value = next;
		}
		if (players.value.size === 1 && !hostId.value) {
			hostId.value = id;
		}
	}

	function setPlayers(nextPlayers: Array<{ id: string; name: string }>) {
		const next = new Map<string, Player>();

		for (const incoming of nextPlayers) {
			const existing = players.value.get(incoming.id);
			next.set(incoming.id, {
				id: incoming.id,
				name: incoming.name,
				score: existing?.score ?? 0,
				currentCard: existing?.currentCard,
				drawing: existing?.drawing,
			});
		}

		players.value = next;

		if (players.value.size === 1 && !hostId.value) {
			hostId.value = nextPlayers[0]?.id ?? null;
		}
	}

	function removePlayer(id: string) {
		if (!players.value.has(id)) return;

		const next = new Map(players.value);
		next.delete(id);
		players.value = next;
	}

	function clearPlayers() {
		players.value = new Map();
	}

	function startGame(
		gameDifficulty: Difficulty,
		gameRounds: number,
		drawingTimeLimitSec: number,
		guessingTimeLimitSec: number,
	) {
		difficulty.value = gameDifficulty;
		maxRounds.value = gameRounds;
		drawingTimeLimit.value = drawingTimeLimitSec;
		guessingTimeLimit.value = guessingTimeLimitSec;
		currentRound.value = 0;
		gamePhase.value = "lobby";

		const next = new Map(players.value);
		for (const [id, p] of next) next.set(id, { ...p, score: 0 });
		players.value = next;
	}

	function startRound(roundNumber: number, cards: Record<string, Card>) {
		currentRound.value = roundNumber;
		gamePhase.value = "drawing";
		readyCount.value = 0;
		totalPlayers.value = players.value.size;
		guessingStartTime.value = undefined;
		guessTargets.value = {};
		clearStrokes();

		const next = new Map(players.value);
		localPlayerCard.value = undefined;

		for (const [playerId, player] of next) {
			next.set(playerId, {
				...player,
				currentCard: cards[playerId],
				drawing: undefined,
			});

			if (playerId === localPlayerId.value) {
				localPlayerCard.value = cards[playerId];
			}
		}

		players.value = next;
	}

	/** Resets round counter and all player scores (used when restarting a game). */
	function resetRound() {
		currentRound.value = 0;
		const next = new Map(players.value);
		for (const [id, p] of next) next.set(id, { ...p, score: 0 });
		players.value = next;
	}

	function addStroke(stroke: DrawStroke) {
		currentStrokes.value.push(stroke);
	}

	function clearStrokes() {
		currentStrokes.value = [];
	}

	function setPlayerDrawing(playerId: string, drawing: string) {
		const player = players.value.get(playerId);
		if (player) {
			player.drawing = drawing;
		}
	}

	function updateScores(scores: Record<string, number>) {
		for (const [playerId, score] of Object.entries(scores)) {
			const player = players.value.get(playerId);
			if (player) {
				player.score = score;
			}
		}
	}

	function setRoundResults(results: RoundResult[]) {
		lastRoundResults.value = results;
	}

	function startGuessing(
		startTime?: number | null,
		targets?: Record<string, string>,
	) {
		gamePhase.value = "guessing";
		guessingStartTime.value = startTime ?? Date.now();
		guessTargets.value = targets ?? {};
		readyCount.value = 0;
		totalPlayers.value = players.value.size;
	}

	function endGame() {
		gamePhase.value = "final_results";
		readyCount.value = 0;
		totalPlayers.value = players.value.size;
	}

	function setHost(id: string | null) {
		hostId.value = id;
	}

	function setDefaultLocale(nextLocale: string) {
		defaultLocale.value = nextLocale;
	}

	function setCustomCategoryIds(nextCategoryIds: number[] | null) {
		customCategoryIds.value = nextCategoryIds ? [...nextCategoryIds] : null;
	}

	function setLocalPlayerLocale(nextLocale: string) {
		localPlayerLocale.value = nextLocale;
	}

	function setRoomPadVisible(visible: boolean) {
		roomPadVisible.value = visible;
	}

	function setLocalPadVisible(visible: boolean) {
		localPadVisible.value = visible;
	}

	function setPrivacy(isPrivate: boolean) {
		isPrivateRoom.value = isPrivate;
	}

	function setReadyStatus(ready: number, total: number) {
		readyCount.value = ready;
		totalPlayers.value = total;
	}

	function applySettingsUpdate(settings: {
		difficulty?: Difficulty | null;
		rounds?: number | null;
		drawingTimeLimit?: number | null;
		guessingTimeLimit?: number | null;
	}) {
		if (settings.difficulty) difficulty.value = settings.difficulty;
		if (settings.rounds !== null && settings.rounds !== undefined)
			maxRounds.value = settings.rounds;
		if (
			settings.drawingTimeLimit !== null &&
			settings.drawingTimeLimit !== undefined
		) {
			drawingTimeLimit.value = settings.drawingTimeLimit;
		}
		if (
			settings.guessingTimeLimit !== null &&
			settings.guessingTimeLimit !== undefined
		) {
			guessingTimeLimit.value = settings.guessingTimeLimit;
		}
	}

	function applyRoomState(roomState: {
		players: Array<{ id: string; name: string }>;
		hostId?: string | null;
		categories?: string[] | null;
		gamePhase: string;
		difficulty?: Difficulty | null;
		maxRounds?: number | null;
		roundStartTime?: number | null;
		guessingStartTime?: number | null;
		drawingTimeLimit?: number | null;
		guessingTimeLimit?: number | null;
		guessTargets?: Record<string, string> | null;
		padVisibility?: boolean;
		defaultLocale?: string | null;
		customCategoryIds?: number[] | null;
		isPrivate?: boolean;
	}) {
		setPlayers(roomState.players);
		hostId.value = roomState.hostId ?? null;
		categories.value = roomState.categories ?? [];
		gamePhase.value = normalizeGamePhase(roomState.gamePhase);
		applySettingsUpdate({
			difficulty: roomState.difficulty,
			rounds: roomState.maxRounds,
			drawingTimeLimit: roomState.drawingTimeLimit,
			guessingTimeLimit: roomState.guessingTimeLimit,
		});
		roundStartTime.value = roomState.roundStartTime ?? undefined;
		guessingStartTime.value = roomState.guessingStartTime ?? undefined;
		guessTargets.value = roomState.guessTargets ?? {};
		if (roomState.padVisibility !== undefined)
			roomPadVisible.value = roomState.padVisibility;
		if (roomState.defaultLocale) defaultLocale.value = roomState.defaultLocale;
		customCategoryIds.value = roomState.customCategoryIds ?? null;
		if (roomState.isPrivate !== undefined)
			isPrivateRoom.value = roomState.isPrivate;
	}

	function reset() {
		roomCode.value = "";
		players.value = new Map();
		kickVotes.value = new Map();
		hostId.value = null;
		clearPendingLocalPlayer();
		currentRound.value = 0;
		maxRounds.value = GAME_SETTINGS.rounds.DEFAULT;
		difficulty.value = GAME_SETTINGS.difficulty.DEFAULT;
		gamePhase.value = "lobby";
		roundStartTime.value = undefined;
		guessingStartTime.value = undefined;
		drawingTimeLimit.value = GAME_SETTINGS.drawingTimeLimitSeconds.DEFAULT;
		guessingTimeLimit.value = GAME_SETTINGS.guessingTimeLimitSeconds.DEFAULT;
		guessTargets.value = {};
		currentStrokes.value = [];
		localPlayerCard.value = undefined;
		isSpectatorMode.value = false;
		lastRoundResults.value = [];
		categories.value = [];
		readyCount.value = 0;
		totalPlayers.value = 0;
		localPadVisible.value = true;
		roomPadVisible.value = true;
		defaultLocale.value = "en";
		customCategoryIds.value = null;
		localPlayerLocale.value = getBrowserLocale();
		isPrivateRoom.value = false;
	}

	function getFinalScores() {
		return playersList.value
			.map((p) => ({ playerId: p.id, playerName: p.name, score: p.score }))
			.sort((a, b) => b.score - a.score);
	}

	function getWinner() {
		return getFinalScores()[0];
	}

	/** Force a synchronous persist to localStorage. Rarely needed — prefer letting the watcher handle it. */
	function saveState() {
		try {
			localStorage.setItem(STORAGE_KEYS.PLAYER_NAME, localPlayerName.value);
			localStorage.setItem(
				STORAGE_KEYS.GAME_STATE,
				JSON.stringify({
					localPlayerLocale: localPlayerLocale.value,
					roomCode: roomCode.value,
					localPlayerId: localPlayerId.value,
					localPlayerName: localPlayerName.value,
					currentRound: currentRound.value,
					maxRounds: maxRounds.value,
					difficulty: difficulty.value,
					gamePhase: gamePhase.value,
					roundStartTime: roundStartTime.value,
					guessingStartTime: guessingStartTime.value,
					drawingTimeLimit: drawingTimeLimit.value,
					guessingTimeLimit: guessingTimeLimit.value,
					guessTargets: guessTargets.value,
					localPadVisible: localPadVisible.value,
					defaultLocale: defaultLocale.value,
					customCategoryIds: customCategoryIds.value,
				}),
			);
		} catch {
			/* localStorage unavailable (e.g. test environment) */
		}
	}

	// Automatically persist relevant fields whenever any of them change.
	watch(
		[
			roomCode,
			localPlayerId,
			localPlayerLocale,
			localPlayerName,
			currentRound,
			maxRounds,
			difficulty,
			gamePhase,
			roundStartTime,
			guessingStartTime,
			drawingTimeLimit,
			guessingTimeLimit,
			localPadVisible,
			defaultLocale,
			customCategoryIds,
		],
		saveState,
	);

	function setRoomCodeAndSave(code: string) {
		setRoomCode(code);
		saveState();
	}

	function setLocalPlayerAndSave(id: string, name: string) {
		setLocalPlayer(id, name);
		saveState();
	}

	function startKickVote(targetPlayerId: string, vote: KickVote) {
		const next = new Map(kickVotes.value);
		next.set(targetPlayerId, vote);
		kickVotes.value = next;
	}

	function updateKickVote(
		targetPlayerId: string,
		data: Pick<KickVote, "currentVotes" | "requiredVotes">,
	) {
		const existing = kickVotes.value.get(targetPlayerId);
		if (existing) {
			const next = new Map(kickVotes.value);
			next.set(targetPlayerId, {
				...existing,
				currentVotes: data.currentVotes,
				requiredVotes: data.requiredVotes,
			});
			kickVotes.value = next;
		}
	}

	function removeKickVote(targetPlayerId: string) {
		if (!kickVotes.value.has(targetPlayerId)) return;

		const next = new Map(kickVotes.value);
		next.delete(targetPlayerId);
		kickVotes.value = next;
	}

	return {
		// State (exposed as writable refs — set directly: store.difficulty = 'hard')
		roomCode,
		localPlayerId,
		localPlayerName,
		pendingLocalPlayerId,
		pendingLocalPlayerName,
		players,
		hostId,
		currentRound,
		maxRounds,
		difficulty,
		gamePhase,
		roundStartTime,
		guessingStartTime,
		drawingTimeLimit,
		guessingTimeLimit,
		currentStrokes,
		localPlayerCard,
		isSpectatorMode,
		lastRoundResults,
		categories,
		guessTargets,
		readyCount,
		totalPlayers,
		defaultLocale,
		customCategoryIds,
		localPlayerLocale,
		localPadVisible,
		roomPadVisible,
		kickVotes,
		isPrivateRoom,

		// Computed
		localPlayer,
		playersList,
		canStartGame,
		isHost,

		// Actions (complex mutations with side-effects)
		setLocalPlayer,
		setSpectatorMode,
		setPendingLocalPlayer,
		clearPendingLocalPlayer,
		confirmPendingLocalPlayer,
		setRoomCode,
		addPlayer,
		setPlayers,
		removePlayer,
		clearPlayers,
		startGame,
		startRound,
		resetRound,
		addStroke,
		clearStrokes,
		setPlayerDrawing,
		updateScores,
		setRoundResults,
		startGuessing,
		endGame,
		setHost,
		setDefaultLocale,
		setCustomCategoryIds,
		setLocalPlayerLocale,
		setRoomPadVisible,
		setLocalPadVisible,
		setPrivacy,
		setReadyStatus,
		applySettingsUpdate,
		applyRoomState,
		reset,
		getFinalScores,
		getWinner,
		saveState,
		setRoomCodeAndSave,
		setLocalPlayerAndSave,
		startKickVote,
		updateKickVote,
		removeKickVote,
	};
});
