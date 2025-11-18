import PartySocket from 'partysocket'
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import { useNotifications } from '@/composables/notifications'
import { GAME_SETTINGS } from '@/config/gameConfig'
import { RoomStateSchema, normalizeRoomMetadata } from '@/shared/schemas/room'
import type { GameMessage } from '@/shared/types'
import { useGameStore } from '@/stores/game'
import logger from '@/utils/logger'

import { clearGameEngine, getGameEngine } from './gameEngineInstance'

// Minimal interface describing the methods we use on the socket instance.
interface PartySocketLike {
  addEventListener: (type: string, cb: (event?: unknown) => void) => void
  removeEventListener: (type: string, cb: (event?: unknown) => void) => void
  send: (data: string) => void
  close: (code?: number, reason?: string) => void
}

// Vite provides typed `import.meta.env` via `env.d.ts` (vite/client)
const PARTYKIT_HOST = import.meta.env.VITE_PARTYKIT_HOST || 'localhost:1999'

// Singleton WebSocket connection shared across all components
// PartySocket provides a WebSocket-compatible client with automatic reconnects
let ws: PartySocketLike | null = null
const isConnected = ref(false)
const connectionError = ref<string | null>(null)
let heartbeatInterval: number | null = null
// Idle prompt state (ms remaining). If null, no prompt shown.
const idlePromptMs = ref<number | null>(null)
// Message shown when server forcefully disconnects a client for inactivity
const idleKickedMessage = ref<string | null>(null)
// Track whether the close was initiated locally (so we don't treat it as a kick)
let closingByClient = false

export function useGameConnection() {
  const store = useGameStore()
  const router = useRouter()
  const { showNotification } = useNotifications()

  // Shared cleanup used when the server forcefully disconnects a client (idle kick)
  function handleServerKick(message = 'You were removed from the room due to inactivity.') {
    try {
      stopHeartbeat()
      clearGameEngine()
      // reset store and navigate to lobby
      store.reset()
      router.push('/')
      // expose a dismissible message to the UI
      idleKickedMessage.value = message
    } catch {
      logger.warn('[useGameConnection] Error during server-kick cleanup')
    }
  }

  function connect(roomCode: string) {
    // Close existing socket if any
    if (ws) {
      try {
        closingByClient = true
        ws.close()
      } catch {}
      ws = null
    }

    // Create PartySocket which is WebSocket-compatible and auto-reconnects
    ws = new PartySocket({
      host: PARTYKIT_HOST,
      room: roomCode,
      maxRetries: 10,
      maxEnqueuedMessages: 1000,
      debug: false,
    })

    ws.addEventListener('open', () => {
      isConnected.value = true
      connectionError.value = null

      // Send join and request_game_state as before
      send({ type: 'join', playerId: store.localPlayerId, name: store.localPlayerName })
      send({ type: 'request_game_state', playerId: store.localPlayerId })

      startHeartbeat()
    })

    ws.addEventListener('message', (e: unknown) => {
      try {
        if (!e || typeof e !== 'object') throw new Error('invalid event')
        const data = (e as { data?: unknown }).data as string | undefined
        if (!data) throw new Error('no data')
        const message: GameMessage = JSON.parse(data)
        handleMessage(message)
      } catch (error) {
        logger.error('[WebSocket] Failed to parse message:', error)
        connectionError.value = 'Failed to process server message'
      }
    })

    ws.addEventListener('error', (err: unknown) => {
      logger.error('[WebSocket] Connection error:', err)
      connectionError.value = 'Connection error occurred'
      isConnected.value = false
    })

    ws.addEventListener('close', (event: unknown) => {
      const ev = (event as { code?: number; reason?: string } | undefined) || {}
      logger.info('[WebSocket] Connection closed:', ev.code, ev.reason)
      stopHeartbeat()
      isConnected.value = false
      if (closingByClient) {
        closingByClient = false
        return
      }
      handleServerKick('Disconnected from server')
    })
  }

  function send(message: GameMessage) {
    try {
      if (!ws) return
      // PartySocket buffers messages if not yet open; just call send
      logger.debug('[WebSocket] Sending message:', message)
      ws.send(JSON.stringify(message))
    } catch (e) {
      logger.warn('[WebSocket] Failed to send message', e)
    }
  }

  // Request authoritative game state and return a promise resolved when room_state arrives
  function requestGameState(playerId?: string): Promise<void> {
    return new Promise((resolve, reject) => {
      let timeoutId: ReturnType<typeof setTimeout> | null = null

      // Temporary handler to resolve when next room_state arrives
      const onMessage = (event?: unknown) => {
        try {
          if (!event || typeof event !== 'object') return
          const evt = event as { data?: unknown }
          const data = evt.data as string | undefined
          if (!data) return
          const message: GameMessage = JSON.parse(data)
          if (message.type === 'room_state') {
            handleMessage(message)
            // detach and resolve
            if (ws) ws.removeEventListener('message', onMessage)
            if (timeoutId) clearTimeout(timeoutId)
            resolve()
          }
        } catch (err) {
          logger.debug('[WebSocket] temporary onMessage parse error', err)
        }
      }

      // Add timeout to prevent hanging forever
      timeoutId = setTimeout(() => {
        if (ws) ws.removeEventListener('message', onMessage)
        reject(new Error('Timeout waiting for room_state'))
      }, 5000) // 5 second timeout

      // If there's no socket instance, create one. PartySocket will buffer
      // outgoing messages until the socket is open, so we can send immediately.
      if (!ws) {
        if (store.roomCode) {
          try {
            connect(store.roomCode)
          } catch (e) {
            if (timeoutId) clearTimeout(timeoutId)
            reject(e)
            return
          }
        } else {
          if (timeoutId) clearTimeout(timeoutId)
          reject(new Error('No roomCode to connect to'))
          return
        }
      }

      if (ws) {
        ws.addEventListener('message', onMessage)
        // Send explicit request if connection already open
        try {
          send({ type: 'request_game_state', playerId: playerId || store.localPlayerId })
        } catch (err) {
          if (ws) ws.removeEventListener('message', onMessage)
          if (timeoutId) clearTimeout(timeoutId)
          reject(err)
        }
      } else {
        // Shouldn't happen, but handle it
        if (timeoutId) clearTimeout(timeoutId)
        reject(new Error('Failed to establish websocket connection'))
      }
    })
  }

  function handleMessage(message: GameMessage) {
    logger.debug('[WebSocket] Received:', message.type)

    switch (message.type) {
      case 'room_state':
        // Validate and normalize incoming room_state using shared schema
        // so malformed persisted metadata doesn't crash the client.
        try {
          const raw = message as unknown as Record<string, unknown>
          // Players handled separately (they are already typed by GameMessage)
          message.players.forEach((p) => {
            store.addPlayer(p.id, p.name)
          })

          const metadata: Record<string, unknown> = {
            categories: raw.categories,
            gamePhase: raw.gamePhase,
            roundStartTime: raw.roundStartTime,
            roundLength: raw.roundLength,
            difficulty: raw.difficulty,
            maxRounds: raw.maxRounds,
            sharedPadVisibility: raw.sharedPadVisibility,
            sharedPadStrokes: raw.sharedPadStrokes,
            hostId: raw.hostId,
          }

          const parsed = RoomStateSchema.safeParse(metadata)
          const validated = parsed.success ? parsed.data : normalizeRoomMetadata(metadata)

          // Apply validated fields to the store
          store.setCategories(validated.categories)
          store.setGamePhase(validated.gamePhase)
          if (validated.roundStartTime) store.roundStartTime = validated.roundStartTime
          if (validated.roundLength) store.roundLength = validated.roundLength
          if (typeof validated.hostId === 'string') store.setHost(validated.hostId)
          store.setDifficulty(validated.difficulty as import('@/shared/types').Difficulty)
          store.setMaxRounds(validated.maxRounds)
          store.setShowPadForRoom(validated.sharedPadVisibility)
          try {
            store.setStrokes(validated.sharedPadStrokes as import('@/shared/types').DrawStroke[])
          } catch (err) {
            logger.warn('[WebSocket] Failed to set strokes from room_state after validation', err)
          }

          logger.info('[WebSocket] Synced room state from server (validated):', {
            gamePhase: validated.gamePhase,
            hostId: validated.hostId,
            difficulty: validated.difficulty,
            maxRounds: validated.maxRounds,
          })
        } catch (err) {
          logger.warn('[WebSocket] Failed to validate/process room_state', err)
        }
        break

      case 'player_joined':
        // Sync all players from the full list (including ourselves)
        message.players.forEach((p) => {
          store.addPlayer(p.id, p.name)
        })
        // Show a toast for other players joining
        if (message.playerId !== store.localPlayerId) {
          showNotification(`${message.name} joined the room`)
        }
        break

      case 'player_left':
        store.removePlayer(message.playerId)
        // Show a toast for other players leaving (use provided name when present)
        if (message.playerId !== store.localPlayerId) {
          const m = message as Extract<GameMessage, { type: 'player_left'; name?: string }>
          showNotification(m.name ? `${m.name} left the room` : 'A player left the room')
        }
        break

      case 'host_changed':
        store.setHost(message.newHostId)
        // Show notification if we became the host
        if (message.newHostId === store.localPlayerId) {
          showNotification('You are now the host!')
        } else {
          // Try to show the new host name if available
          const newHost = store.players.get(message.newHostId)
          const name = newHost ? newHost.name : 'a player'
          showNotification(`${name} is now the host`)
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
        // Router guard will redirect to correct phase route based on gamePhase
        break

      case 'start_round':
        if (typeof message.cards === 'object' && message.cards !== null) {
          // Store the server-generated roundStartTime
          store.roundStartTime = message.roundStartTime
          store.startRound(message.round, message.cards)
          // Router guard will redirect to correct phase route based on gamePhase
        } else {
          logger.error('[WebSocket] Invalid cards in start_round message:', message)
        }
        break

      case 'drawing_complete':
        store.setPlayerDrawing(message.playerId, message.drawing)
        break

      case 'start_guessing':
        // Store the guessing phase start time
        store.roundStartTime = message.roundStartTime
        store.setGamePhase('guessing')
        break

      case 'submit_guess':
        // Forward guess submissions to game engine (host only)
        if (store.isHost) {
          const gameEngine = getGameEngine()
          if (gameEngine) {
            gameEngine.handleGuessSubmission({
              playerId: message.playerId,
              targetPlayerId: message.targetPlayerId,
              guesses: message.guesses,
            })
          }
        }
        break

      case 'round_complete':
        store.setRoundResults(message.results)
        store.updateScores(message.scores)
        store.setGamePhase('scoring')
        // Router guard will redirect to correct phase route based on gamePhase
        break

      case 'game_complete':
        store.updateScores(message.finalScores)
        store.endGame()
        // Router guard will redirect to correct phase route based on gamePhase
        break

      case 'restart_game':
        // Host initiated restart - all players should reset and go to waiting room
        store.playersList.forEach((player) => {
          player.score = 0
        })
        store.currentRound = 0
        store.setGamePhase('waiting-room')
        clearGameEngine()
        // Note: The router will navigate via gamePhase watcher in App.vue
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
        logger.info('[WebSocket] Settings updated from server:', message)
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
      case 'drawpad_restore': {
        const m = message as Extract<GameMessage, { type: 'drawpad_restore' }>
        if (Array.isArray(m.strokes)) {
          store.setStrokes(m.strokes)
        }
        break
      }
      case 'pad_visibility':
        // Host-controlled pad visibility (room-level)
        // `message` is narrowed by the switch case to the `pad_visibility` variant
        // so it's safe to extract `visible` using a type extract rather than `any`.
        const visibleForRoom = Boolean(
          (message as Extract<GameMessage, { type: 'pad_visibility' }>).visible
        )
        store.setShowPadForRoom(visibleForRoom)

        // Force per-client visibility to match the host's room-level decision so
        // everyone's UI reflects the host preference immediately.
        // Note: this intentionally overrides the per-client preference when the
        // host changes the room setting.
        store.setShowDrawpad(visibleForRoom)

        if (!store.isHost) {
          const visible = visibleForRoom
          showNotification(
            visible ? 'Host showed the drawpad for the room' : 'Host hid the drawpad for the room'
          )
        }
        break
      case 'idle_prompt': {
        const m = message as Extract<GameMessage, { type: 'idle_prompt' }>
        if (m.timeoutMs) idlePromptMs.value = m.timeoutMs
        break
      }
      case 'idle_confirmed': {
        idlePromptMs.value = null
        break
      }
      case 'kicked': {
        // Server explicitly informs client that it was kicked (e.g., for inactivity)
        const m = message as Extract<GameMessage, { type: 'kicked' }>
        handleServerKick(m.reason || 'You were removed from the room')
        break
      }
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
      // Mark that this close was initiated locally so onclose handler doesn't treat
      // it as a server-initiated kick.
      closingByClient = true
      ws.close()
      ws = null
    }
    isConnected.value = false
  }

  function confirmIdle() {
    send({ type: 'idle_confirm', playerId: store.localPlayerId })
  }

  function dismissIdleKick() {
    idleKickedMessage.value = null
  }

  return {
    isConnected,
    connectionError,
    connect,
    send,
    disconnect,
    // exposed for tests
    handleMessage,
    // request game state helper
    requestGameState,
    // idle prompt API
    idlePromptMs,
    confirmIdle,
    idleKickedMessage,
    dismissIdleKick,
  }
}
