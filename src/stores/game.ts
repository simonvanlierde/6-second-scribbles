import { defineStore } from 'pinia';
import { computed, ref } from 'vue';

import { GAME_SETTINGS } from '@/config/gameConfig';
import type { Card, Difficulty, DrawStroke, Player, RoundResult } from '@/shared/types';

export const useGameStore = defineStore('game', () => {
  // Load from localStorage if available
  const savedState = localStorage.getItem('gameState')
  const initialState = savedState ? JSON.parse(savedState) : null

  // Load user's name from localStorage
  const savedName = localStorage.getItem('playerName') || '';
  const localPlayerName = ref<string>(savedName);

  // State
  const roomCode = ref<string>(initialState?.roomCode || '')
  const localPlayerId = ref<string>(initialState?.localPlayerId || '')
  const players = ref<Map<string, Player>>(new Map())
  const hostId = ref<string | null>(null)
  const currentRound = ref<number>(initialState?.currentRound || 0)
  const maxRounds = ref<number>(initialState?.maxRounds || GAME_SETTINGS.rounds.DEFAULT); // Use default from gameConfig
  const difficulty = ref<Difficulty>(initialState?.difficulty || GAME_SETTINGS.difficulty.DEFAULT); // Use default from gameConfig
  const gamePhase = ref<'lobby' | 'drawing' | 'guessing' | 'scoring' | 'complete'>(initialState?.gamePhase || 'lobby')
  const roundLength = ref<number>(initialState?.roundLength || GAME_SETTINGS.roundLengthSeconds.DEFAULT); // Duration of each round in seconds
  const roundStartTime = ref<number | undefined>(initialState?.roundStartTime); // Unix timestamp when current round started
  const currentStrokes = ref<DrawStroke[]>([])
  const showDrawpad = ref<boolean>(initialState?.showDrawpad ?? true)
  const showPadForRoom = ref<boolean>(initialState?.showPadForRoom ?? true)
  const localPlayerCard = ref<Card | undefined>()
  const lastRoundResults = ref<RoundResult[]>([])
  const categories = ref<string[]>([])
  const readyCount = ref<number>(0)
  const totalPlayers = ref<number>(0)

  // Computed
  const localPlayer = computed(() => players.value.get(localPlayerId.value))
  const playersList = computed(() => Array.from(players.value.values()))
  const canStartGame = computed(() => {
    const result = players.value.size >= 2 && gamePhase.value === 'lobby';
    console.log('[Store] canStartGame:', result, 'Player count:', players.value.size, 'Game phase:', gamePhase.value);
    return result;
  })
  const isHost = computed(() => hostId.value === localPlayerId.value)

  // Actions
  function setLocalPlayer(id: string, name: string) {
    localPlayerId.value = id;
    localPlayerName.value = name;
    localStorage.setItem('playerName', name); // Save name to localStorage
  }

  function setRoomCode(code: string) {
    roomCode.value = code
  }

  function addPlayer(id: string, name: string) {
    if (!players.value.has(id)) {
      players.value.set(id, {
        id,
        name,
        score: 0,
      })
    }
    // If this is the first player, make them host
    if (players.value.size === 1 && !hostId.value) {
      hostId.value = id
    }
  }

  function removePlayer(id: string) {
    players.value.delete(id)
  }

  function clearPlayers() {
    players.value.clear()
  }

  function setHost(id: string) {
    hostId.value = id
  }

  function setGamePhase(phase: typeof gamePhase.value) {
    gamePhase.value = phase
    saveState()
  }

  function setDifficulty(diff: Difficulty) {
    difficulty.value = diff
    saveState()
  }

  function setMaxRounds(rounds: number) {
    maxRounds.value = rounds
    saveState()
  }

  function startGame(gameDifficulty: Difficulty, gameRounds: number, roundLengthSec: number) {
    // Store the game configuration but don't change phase yet
    // Phase will change when we receive start_round from server
    difficulty.value = gameDifficulty;
    maxRounds.value = gameRounds;
    roundLength.value = roundLengthSec;

    // Reset scores and round for new game
    currentRound.value = 0;
    players.value.forEach(player => {
      player.score = 0;
    });

    saveState();
  }

  function startRound(roundNumber: number, cards: Record<string, Card>) {
    currentRound.value = roundNumber;
    gamePhase.value = 'drawing';
    clearStrokes();

    // Assign cards to all players
    for (const [playerId, card] of Object.entries(cards)) {
      const player = players.value.get(playerId);
      if (player) {
        player.currentCard = card;
      }

      // Set local player's card
      if (playerId === localPlayerId.value) {
        localPlayerCard.value = card;
        console.log('[Store] Set localPlayerCard for round', roundNumber, ':', card);
      }
    }

    saveState();
  }

  function addStroke(stroke: DrawStroke) {
    currentStrokes.value.push(stroke)
  }

  function clearStrokes() {
    currentStrokes.value = []
  }

  function setPlayerDrawing(playerId: string, drawing: string) {
    const player = players.value.get(playerId)
    if (player) {
      player.drawing = drawing
    }
  }

  function updateScores(scores: Record<string, number>) {
    for (const [playerId, score] of Object.entries(scores)) {
      const player = players.value.get(playerId)
      if (player) {
        player.score = score
      }
    }
    saveState()
  }

  function setRoundResults(results: RoundResult[]) {
    lastRoundResults.value = results
  }

  function nextRound() {
    currentRound.value++
    clearStrokes()
    saveState()
  }

  function endGame() {
    gamePhase.value = 'complete'
    saveState()
  }

  function reset() {
    roomCode.value = ''
    players.value.clear()
    currentRound.value = 0
    maxRounds.value = GAME_SETTINGS.rounds.DEFAULT
    difficulty.value = GAME_SETTINGS.difficulty.DEFAULT
    gamePhase.value = 'lobby'
    roundStartTime.value = undefined
    currentStrokes.value = []
    localPlayerCard.value = undefined
  }

  function getRandomCard(cards: Card[]): Card | undefined {
    if (cards.length === 0) return undefined
    const randomIndex = Math.floor(Math.random() * cards.length)
    return cards[randomIndex]
  }

  function getFinalScores() {
    return playersList.value
      .map(p => ({
        playerId: p.id,
        playerName: p.name,
        score: p.score,
      }))
      .sort((a, b) => b.score - a.score)
  }

  function getWinner() {
    const scores = getFinalScores()
    return scores[0]
  }

  function saveState() {
    const state = {
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
    }
    localStorage.setItem('gameState', JSON.stringify(state))
  }

  function setShowDrawpad(val: boolean) {
    showDrawpad.value = val
    saveState()
  }

  function setShowPadForRoom(val: boolean) {
    showPadForRoom.value = val
    saveState()
  }

  // Save state whenever it changes
  function setRoomCodeAndSave(code: string) {
    setRoomCode(code)
    saveState()
  }

  function setLocalPlayerAndSave(id: string, name: string) {
    setLocalPlayer(id, name)
    saveState()
  }

  function setCategories(newCategories: string[]) {
    categories.value = newCategories
  }

  function setReadyStatus(ready: number, total: number) {
    readyCount.value = ready
    totalPlayers.value = total
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
    startGame,
    startRound,
    addStroke,
    clearStrokes,
    setPlayerDrawing,
    updateScores,
    setRoundResults,
    nextRound,
    endGame,
    reset,
    getRandomCard,
    getFinalScores,
    getWinner,
    saveState,
    setRoomCodeAndSave,
    setLocalPlayerAndSave,
    setCategories,
    setReadyStatus,
    setShowDrawpad,
    showDrawpad,
    showPadForRoom,
    setShowPadForRoom,
  }
})
