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
      players.value.set(id, { id, name, score: 0 });
    }
    if (players.value.size === 1 && !hostId.value) {
      hostId.value = id;
    }
  }

  function removePlayer(id: string) {
    players.value.delete(id);
  }

  function clearPlayers() {
    players.value.clear();
  }

  function setHost(id: string) {
    hostId.value = id;
  }

  function setGamePhase(phase: typeof gamePhase.value) {
    gamePhase.value = phase;
  }

  function setDifficulty(diff: Difficulty) {
    difficulty.value = diff;
  }

  function setMaxRounds(rounds: number) {
    maxRounds.value = rounds;
  }

  function setRoundStartTime(t: number | undefined) {
    roundStartTime.value = t;
  }

  function setRoundLength(s: number) {
    roundLength.value = s;
  }

  function setLocalPlayerCard(card: Card | undefined) {
    localPlayerCard.value = card;
  }

  function startGame(gameDifficulty: Difficulty, gameRounds: number, roundLengthSec: number) {
    difficulty.value = gameDifficulty;
    maxRounds.value = gameRounds;
    roundLength.value = roundLengthSec;
    currentRound.value = 0;
    players.value.forEach((player) => {
      player.score = 0;
    });
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
    players.value.forEach((player) => {
      player.score = 0;
    });
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
    players.value.clear();
    currentRound.value = 0;
    maxRounds.value = GAME_SETTINGS.rounds.DEFAULT;
    difficulty.value = GAME_SETTINGS.difficulty.DEFAULT;
    gamePhase.value = "lobby";
    roundStartTime.value = undefined;
    currentStrokes.value = [];
    localPlayerCard.value = undefined;
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

  function setShowDrawpad(val: boolean) {
    showDrawpad.value = val;
  }

  function setShowPadForRoom(val: boolean) {
    showPadForRoom.value = val;
  }

  function setRoomCodeAndSave(code: string) {
    setRoomCode(code);
    saveState();
  }

  function setLocalPlayerAndSave(id: string, name: string) {
    setLocalPlayer(id, name);
    saveState();
  }

  function setCategories(newCategories: string[]) {
    categories.value = newCategories;
  }

  function setReadyStatus(ready: number, total: number) {
    readyCount.value = ready;
    totalPlayers.value = total;
  }

  function setLanguage(lang: string) {
    language.value = lang;
  }

  function startKickVote(targetPlayerId: string, vote: KickVote) {
    kickVotes.value.set(targetPlayerId, vote);
  }

  function updateKickVote(targetPlayerId: string, data: Pick<KickVote, "currentVotes" | "requiredVotes">) {
    const existing = kickVotes.value.get(targetPlayerId);
    if (existing) {
      existing.currentVotes = data.currentVotes;
      existing.requiredVotes = data.requiredVotes;
    }
  }

  function removeKickVote(targetPlayerId: string) {
    kickVotes.value.delete(targetPlayerId);
  }

  return {
    // State
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

    // Actions
    setLocalPlayer,
    setRoomCode,
    addPlayer,
    removePlayer,
    clearPlayers,
    setHost,
    setGamePhase,
    setDifficulty,
    setMaxRounds,
    setRoundStartTime,
    setRoundLength,
    setLocalPlayerCard,
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
    setCategories,
    setReadyStatus,
    setShowDrawpad,
    setShowPadForRoom,
    setLanguage,
    startKickVote,
    updateKickVote,
    removeKickVote,
  };
});
