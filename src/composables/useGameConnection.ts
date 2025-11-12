import { ref } from 'vue';
import { useRouter } from 'vue-router';

import { getGameEngine } from './gameEngineInstance';

import { useNotifications } from '@/composables/notifications';
import { GAME_SETTINGS } from '@/config/gameConfig';
import type { GameMessage } from '@/shared/types';
import { useGameStore } from '@/stores/game';


const PARTYKIT_HOST = (import.meta as any).env?.VITE_PARTYKIT_HOST || 'ws://localhost:1999';

// Singleton WebSocket connection shared across all components
let ws: WebSocket | null = null;
const isConnected = ref(false);
const connectionError = ref<string | null>(null);
let heartbeatInterval: number | null = null;

export function useGameConnection() {
  const store = useGameStore()
  const router = useRouter()
  const { showNotification } = useNotifications()

  function connect(roomCode: string) {
    if (ws) {
      ws.close()
    }

    const url = `${PARTYKIT_HOST}/party/${roomCode}`
    ws = new WebSocket(url)

    ws.onopen = () => {
      isConnected.value = true
      connectionError.value = null

      // Send join message
      send({
        type: 'join',
        playerId: store.localPlayerId,
        name: store.localPlayerName,
      })

      // Request game state to handle missing categories on reload
      send({
        type: 'request_game_state',
        playerId: store.localPlayerId,
      })

      // Start heartbeat to keep connection active and prevent idle timeout
      startHeartbeat()
    }

    ws.onmessage = (event: MessageEvent) => {
      try {
        const message: GameMessage = JSON.parse(event.data)
        handleMessage(message)
      } catch (error) {
        console.error('[WebSocket] Failed to parse message:', error, 'Raw:', event.data)
        connectionError.value = 'Failed to process server message'
      }
    }

    ws.onerror = (error) => {
      console.error('[WebSocket] Connection error:', error)
      connectionError.value = 'Connection error occurred'
      isConnected.value = false
    }

    ws.onclose = (event) => {
      console.log('[WebSocket] Connection closed:', event.code, event.reason)
      stopHeartbeat()
      isConnected.value = false
    }
  }

  function send(message: GameMessage) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      console.log('[WebSocket] Sending message:', message); // Log the message object
      ws.send(JSON.stringify(message))
    }
  }

  function handleMessage(message: GameMessage) {
    console.log('[WebSocket] Received:', message.type)

    switch (message.type) {
      case 'room_state':
        // Sync existing players when joining (including ourselves)
        message.players.forEach((p) => {
          store.addPlayer(p.id, p.name)
        })

        // Sync categories, game phase, and timing info
        store.setCategories(message.categories)
        store.setGamePhase(message.gamePhase)

        if (message.roundStartTime) {
          store.roundStartTime = message.roundStartTime
        }
        if (message.roundLength) {
          store.roundLength = message.roundLength
        }
        if ((message as any).padVisibility !== undefined) {
          // padVisibility is a host-controlled room-level preference
          store.setShowPadForRoom(!!(message as any).padVisibility)
        }
        break

      case 'player_joined':
        // Sync all players from the full list (including ourselves)
        message.players.forEach((p) => {
          store.addPlayer(p.id, p.name)
        })
        break

      case 'player_left':
        store.removePlayer(message.playerId)
        break

      case 'host_changed':
        store.setHost(message.newHostId)
        // Show notification if we became the host
        if (message.newHostId === store.localPlayerId) {
          console.log('You are now the host!')
        }
        break

      case 'start_game':
        store.setDifficulty(message.difficulty)
        store.setMaxRounds(message.rounds)
        store.startGame(
          message.difficulty || GAME_SETTINGS.difficulty.DEFAULT,
          message.rounds || GAME_SETTINGS.rounds.DEFAULT,
          message.roundLength || GAME_SETTINGS.roundLengthSeconds.DEFAULT
        )
        router.push(`/game/${store.roomCode}`)
        break

      case 'start_round':
        if (typeof message.cards === 'object' && message.cards !== null) {
          // Store the server-generated roundStartTime
          store.roundStartTime = message.roundStartTime;
          store.startRound(message.round, message.cards);

          // Navigate to game view if not already there
          if (router.currentRoute.value.name !== 'game') {
            router.push(`/game/${store.roomCode}`)
          }
        } else {
          console.error('[WebSocket] Invalid cards in start_round message:', message);
        }
        break

      case 'drawing_complete':
        store.setPlayerDrawing(message.playerId, message.drawing)
        break

      case 'start_guessing':
        // Store the guessing phase start time
        store.roundStartTime = message.roundStartTime;
        store.setGamePhase('guessing')
        break

      case 'submit_guess':
        // Forward guess submissions to game engine (host only)
        if (store.isHost) {
          const gameEngine = getGameEngine();
          if (gameEngine) {
            gameEngine.handleGuessSubmission({
              playerId: message.playerId,
              targetPlayerId: message.targetPlayerId,
              guesses: message.guesses
            });
          }
        }
        break

      case 'round_complete':
        store.setRoundResults(message.results)
        store.updateScores(message.scores)
        store.setGamePhase('scoring')
        router.push(`/round-results/${store.roomCode}`)
        break

      case 'game_complete':
        store.updateScores(message.finalScores)
        store.endGame()
        router.push(`/results/${store.roomCode}`)
        break

      case 'restart_game':
        // Host initiated restart - all players should reset and go to waiting room
        store.playersList.forEach(player => {
          player.score = 0
        })
        store.currentRound = 0
        store.setGamePhase('lobby')
        // Note: The router will be triggered by the gamePhase watch in ResultsView
        break

      case 'ready_status':
        // Server broadcasts updated ready count
        store.setReadyStatus(message.readyCount, message.totalPlayers)
        break

      case 'settings_update':
        // Host broadcast settings changes - update store for non-hosts
        store.setDifficulty(message.difficulty)
        store.setMaxRounds(message.rounds)
        store.roundLength = message.roundLength
        store.saveState()
        console.log('[WebSocket] Settings updated:', message)
        // Show a small toast to non-hosts so they notice the change
        if (!store.isHost) {
          showNotification('Host updated game settings')
        }
        break
      case 'draw_stroke':
        // Add remote stroke to shared store so waiting-room canvases render it
        // Ignore strokes that originated from this client to avoid duplicate drawing
        if (message.stroke && message.playerId !== store.localPlayerId) {
          store.addStroke(message.stroke)
        }
        break

      case 'draw_stroke_partial':
        // Add incremental stroke points to store for near-realtime rendering
        if (message.stroke && message.playerId !== store.localPlayerId) {
          // Treat partial updates like strokes for the waiting-room canvas
          store.addStroke(message.stroke)
        }
        break

      case 'drawpad_clear':
        // Clear shared strokes when host clears the pad
        store.clearStrokes()
        break
      case 'pad_visibility':
        // Host-controlled pad visibility (room-level)
        const visibleForRoom = !!(message as any).visible
        store.setShowPadForRoom(visibleForRoom)

        // Force per-client visibility to match the host's room-level decision so
        // everyone's UI reflects the host preference immediately.
        // Note: this intentionally overrides the per-client preference when the
        // host changes the room setting.
        store.setShowDrawpad(visibleForRoom)

        if (!store.isHost) {
          const visible = visibleForRoom
          showNotification(visible ? 'Host showed the drawpad for the room' : 'Host hid the drawpad for the room')
        }
        break
    }
  }

  function startHeartbeat() {
    // Clear any existing heartbeat
    stopHeartbeat()

    // Send heartbeat every 60 seconds (well before the 5 minute timeout)
    heartbeatInterval = window.setInterval(() => {
      send({
        type: 'heartbeat',
        playerId: store.localPlayerId,
      })
    }, 60000)
  }

  function stopHeartbeat() {
    if (heartbeatInterval) {
      clearInterval(heartbeatInterval)
      heartbeatInterval = null
    }
  }

  function disconnect() {
    stopHeartbeat()
    if (ws) {
      ws.close()
      ws = null
    }
    isConnected.value = false
  }

  return {
    isConnected,
    connectionError,
    connect,
    send,
    disconnect,
    // exposed for tests
    handleMessage,
  }
}
