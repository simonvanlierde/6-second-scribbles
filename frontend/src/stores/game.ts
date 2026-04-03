import { defineStore } from "pinia";
import { computed, ref, watch } from "vue";

import { GAME_SETTINGS } from "@/config/gameConfig";
import type { Card, Difficulty, DrawStroke, KickVote, Player, RoundResult } from "@/shared/types";

export const useGameStore = defineStore("game", () => {
  // Load from localStorage if available (guard for test environments where localStorage may be limited)
  const savedState = (() => {
    try {
      return localStorage.getItem("gameState");
    } catch {
      return null;
    }
  })();
  const initialState = savedState ? JSON.parse(savedState) : null;

  // Load user's name from localStorage
  const savedName =
    (() => {
      try {
        return localStorage.getItem("playerName");
      } catch {
        return null;
      }
    })() || "";
  const localPlayerName = ref<string>(savedName);

  // State
  const roomCode = ref<string>(initialState?.roomCode || "");
  const localPlayerId = ref<string>(initialState?.localPlayerId || "");
  const players = ref<Map<string, Player>>(new Map());
  const hostId = ref<string | null>(null);
  const currentRound = ref<number>(initialState?.currentRound || 0);
  const maxRounds = ref<number>(initialState?.maxRounds || GAME_SETTINGS.rounds.DEFAULT);
  const difficulty = ref<Difficulty>(initialState?.difficulty || GAME_SETTINGS.difficulty.DEFAULT);
  const gamePhase = ref<"lobby" | "drawing" | "guessing" | "scoring" | "complete">(initialState?.gamePhase || "lobby");
  const roundLength = ref<number>(initialState?.roundLength || GAME_SETTINGS.roundLengthSeconds.DEFAULT);
  const roundStartTime = ref<number | undefined>(initialState?.roundStartTime);
  const currentStrokes = ref<DrawStroke[]>([]);
  const showDrawpad = ref<boolean>(initialState?.showDrawpad ?? true);
  const showPadForRoom = ref<boolean>(initialState?.showPadForRoom ?? true);
  const localPlayerCard = ref<Card | undefined>();
  const lastRoundResults = ref<RoundResult[]>([]);
  const categories = ref<string[]>([]);
  const readyCount = ref<number>(0);
  const totalPlayers = ref<number>(0);
  const language = ref<string>(initialState?.language || "en");
  const kickVotes = ref<Map<string, KickVote>>(new Map());

  // Computed
  const localPlayer = computed(() => players.value.get(localPlayerId.value));
  const playersList = computed(() => Array.from(players.value.values()));
  const canStartGame = computed(() => players.value.size >= 2 && gamePhase.value === "lobby");
  const isHost = computed(() => hostId.value === localPlayerId.value);

  // Actions
  function setLocalPlayer(id: string, name: string) {
    localPlayerId.value = id;
    localPlayerName.value = name;
    try {
      localStorage.setItem("playerName", name);
    } catch {
      /* unavailable */
    }
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

  function startGame(gameDifficulty: Difficulty, gameRounds: number, roundLengthSec: number) {
    difficulty.value = gameDifficulty;
    maxRounds.value = gameRounds;
    roundLength.value = roundLengthSec;
    currentRound.value = 0;

    const next = new Map(players.value);
    for (const [id, p] of next) next.set(id, { ...p, score: 0 });
    players.value = next;
  }

  function startRound(roundNumber: number, cards: Record<string, Card>) {
    currentRound.value = roundNumber;
    gamePhase.value = "drawing";
    clearStrokes();

    for (const [playerId, card] of Object.entries(cards)) {
      const player = players.value.get(playerId);
      if (player) {
        player.currentCard = card;
      }
      if (playerId === localPlayerId.value) {
        localPlayerCard.value = card;
      }
    }
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

  function endGame() {
    gamePhase.value = "complete";
  }

  function reset() {
    roomCode.value = "";
    players.value = new Map();
    kickVotes.value = new Map();
    hostId.value = null;
    currentRound.value = 0;
    maxRounds.value = GAME_SETTINGS.rounds.DEFAULT;
    difficulty.value = GAME_SETTINGS.difficulty.DEFAULT;
    gamePhase.value = "lobby";
    roundStartTime.value = undefined;
    roundLength.value = GAME_SETTINGS.roundLengthSeconds.DEFAULT;
    currentStrokes.value = [];
    localPlayerCard.value = undefined;
    lastRoundResults.value = [];
    categories.value = [];
    readyCount.value = 0;
    totalPlayers.value = 0;
    showDrawpad.value = true;
    showPadForRoom.value = true;
    language.value = "en";
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
      localStorage.setItem(
        "gameState",
        JSON.stringify({
          roomCode: roomCode.value,
          localPlayerId: localPlayerId.value,
          localPlayerName: localPlayerName.value,
          currentRound: currentRound.value,
          maxRounds: maxRounds.value,
          difficulty: difficulty.value,
          gamePhase: gamePhase.value,
          roundStartTime: roundStartTime.value,
          roundLength: roundLength.value,
          showDrawpad: showDrawpad.value,
          showPadForRoom: showPadForRoom.value,
          language: language.value,
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
      localPlayerName,
      currentRound,
      maxRounds,
      difficulty,
      gamePhase,
      roundStartTime,
      roundLength,
      showDrawpad,
      showPadForRoom,
      language,
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

  function updateKickVote(targetPlayerId: string, data: Pick<KickVote, "currentVotes" | "requiredVotes">) {
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
    players,
    hostId,
    currentRound,
    maxRounds,
    difficulty,
    gamePhase,
    roundStartTime,
    roundLength,
    currentStrokes,
    localPlayerCard,
    lastRoundResults,
    categories,
    readyCount,
    totalPlayers,
    language,
    showDrawpad,
    showPadForRoom,
    kickVotes,

    // Computed
    localPlayer,
    playersList,
    canStartGame,
    isHost,

    // Actions (complex mutations with side-effects)
    setLocalPlayer,
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
    endGame,
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
