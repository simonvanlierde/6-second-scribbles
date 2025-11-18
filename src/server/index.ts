/**
 * Partykit Server for Six Second Scribbles
 *
 * Architecture: "Dumb Pipe" Pattern
 * - Server only relays messages between clients
 * - All game logic lives in client-side GameEngine
 * - Easy to migrate to FastAPI/custom backend later
 */

import type * as Party from 'partykit/server'
import type { RoomState } from '../shared/schemas/room.js'
import { normalizeRoomMetadata, RoomStateSchema } from '../shared/schemas/room.js'
import logger from '../utils/logger.js'
import IdleChecker from './idleChecker'
import { RoomStorage } from './storage'
import type { Player } from './types'

// Message types (shared contract between client and server)
export type GameMessage =
  | { type: 'join'; playerId: string; name: string }
  | {
      type: 'player_joined'
      playerId: string
      name: string
      players: Array<{ id: string; name: string }>
    }
  | { type: 'player_left'; playerId: string }
  | { type: 'host_changed'; newHostId: string }
  | { type: 'start_game'; difficulty: string; rounds: number; roundLength: number }
  | {
      type: 'start_round'
      round: number
      roundStartTime: number
      cards: Record<string, { category: string; items: string[] }>
    }
  | { type: 'submit_guess'; playerId: string; targetPlayerId: string; guesses: string[] }
  | { type: 'round_complete'; scores: Record<string, number> }
  | { type: 'game_complete'; finalScores: Record<string, number> }
  | { type: 'request_game_state'; playerId: string }
  | { type: 'player_ready'; playerId: string }
  | { type: 'restart_game' }
  | { type: 'heartbeat'; playerId: string }
  | { type: 'settings_update'; difficulty: string; rounds: number; roundLength: number }
  | {
      type: 'draw_stroke'
      playerId: string
      stroke: { color: string; width: number; points: Array<{ x: number; y: number }> }
    }
  | { type: 'drawpad_clear'; playerId: string }
  | {
      type: 'draw_stroke_partial'
      playerId: string
      stroke: { color: string; width: number; points: Array<{ x: number; y: number }> }
    }
  | { type: 'pad_visibility'; playerId: string; visible: boolean }

// re-used types Player, RoomMetadata, ExtendedRoom are imported from ./types

export default class GameServer implements Party.Server {
  // Expose the IdleChecker class on GameServer for backward-compatible access
  static idleChecker = IdleChecker
  // How long to wait before marking room as stale (for quick reconnects)
  static STALE_MARK_DELAY_MS = 5 * 60 * 1000 // 5 minutes
  players: Map<string, Player> = new Map()
  room: Party.Room
  storage: RoomStorage
  state: RoomState // In-memory cache of storage state
  idleChecker: IdleChecker
  // Timer handle for marking room as stale when empty
  private _staleTimer: ReturnType<typeof setTimeout> | null = null

  constructor(room: Party.Room) {
    this.room = room
    this.storage = new RoomStorage(room.storage)
    // State will be loaded in onStart()
    this.state = {
      gamePhase: 'waiting-room',
      difficulty: 'medium',
      maxRounds: 5,
      roundLength: 6,
      currentRound: 0,
      hostId: null,
      sharedPadStrokes: [],
      sharedPadVisibility: true,
      playerScores: {},
      readyPlayers: [],
      pendingIdle: {},
      categories: [],
    }

    // Create IdleChecker instance
    this.idleChecker = new IdleChecker({
      players: this.players,
      roomId: this.room.id,
      getRoomMetadata: () => ({
        categories: this.state.categories,
        gamePhase: this.state.gamePhase,
        roundStartTime: this.state.roundStartTime,
        roundLength: this.state.roundLength,
        difficulty: this.state.difficulty,
        maxRounds: this.state.maxRounds,
        sharedPadVisibility: this.state.sharedPadVisibility,
        sharedPadStrokes: this.state.sharedPadStrokes,
        readyPlayers: new Set(this.state.readyPlayers),
        pendingIdle: this.state.pendingIdle,
      }),
      setRoomMetadata: async (m) => {
        // Normalize untrusted metadata into typed RoomState fields
  const normalized = normalizeRoomMetadata(m as unknown as Record<string, unknown>)

        this.state.categories = normalized.categories
        this.state.gamePhase = normalized.gamePhase
        this.state.roundStartTime = normalized.roundStartTime
        this.state.roundLength = normalized.roundLength
        this.state.difficulty = normalized.difficulty
        this.state.maxRounds = normalized.maxRounds
        this.state.sharedPadVisibility = normalized.sharedPadVisibility
        this.state.sharedPadStrokes = normalized.sharedPadStrokes
        this.state.readyPlayers = normalized.readyPlayers
        this.state.pendingIdle = normalized.pendingIdle

        // Persist the volatile fields we track
        await this.storage.savePartial({
          pendingIdle: this.state.pendingIdle,
          readyPlayers: this.state.readyPlayers,
        })
      },
      broadcast: (m: string) => this.room.broadcast(m),
    })
  }

  async onStart() {
    logger.info(`[Server] Room ${this.room.id} starting/resuming from hibernation`)

    // Load state from storage
    this.state = await this.storage.loadAll()

    // Check if room was marked as stale and optionally reset if very old
    const staleMarker = await this.room.storage.get<{ abandoned_at: number }>('_stale')
    if (staleMarker?.abandoned_at) {
      const ageMs = Date.now() - staleMarker.abandoned_at
      const MAX_STALE_AGE_MS = 7 * 24 * 60 * 60 * 1000 // 7 days

      if (ageMs > MAX_STALE_AGE_MS) {
        logger.info(`[Server] Room ${this.room.id} is ${Math.floor(ageMs / (24 * 60 * 60 * 1000))} days old, resetting to defaults`)
        await this.storage.reset()
        this.state = await this.storage.loadAll()
        await this.room.storage.delete('_stale')
      } else {
        logger.info(`[Server] Room ${this.room.id} was stale but is being reused (${Math.floor(ageMs / (60 * 1000))} minutes old)`)
        // Clear stale marker since room is active again
        await this.room.storage.delete('_stale')
      }
    }

    logger.info(`[Server] Loaded state:`, {
      gamePhase: this.state.gamePhase,
      currentRound: this.state.currentRound,
      hostId: this.state.hostId,
      playerCount: this.players.size,
    })

    // Rebuild players map from active connections
    this.players.clear()
    for (const conn of this.room.getConnections()) {
      const connState = conn.state as any
      if (connState?.playerId && connState?.name) {
        this.players.set(connState.playerId, {
          id: connState.playerId,
          name: connState.name,
          connection: conn,
          categories: [], // Will be regenerated if needed
          lastActivity: Date.now(),
        })
      }
    }

    // If we have a saved hostId but that player is not connected, reassign host
    if (this.state.hostId && !this.players.has(this.state.hostId) && this.players.size > 0) {
      const newHostId = Array.from(this.players.keys())[0]
      if (typeof newHostId === 'string') {
        logger.info(`[Server] Saved host ${this.state.hostId} not connected, reassigning to ${newHostId}`)
        this.state.hostId = newHostId
        await this.storage.set('hostId', newHostId)
        this.room.broadcast(JSON.stringify({ type: 'host_changed', newHostId }))
      }
    }

    // Schedule periodic idle check (absolute epoch ms)
    const next = Date.now() + IdleChecker.IDLE_CHECKER_INTERVAL_MS
    logger.info(
      `[Server] Scheduling next idle check for room ${this.room.id} at ${new Date(next).toISOString()}`
    )
    try {
      const previousAlarm = await this.room.storage.getAlarm()
      if (previousAlarm === null || next < previousAlarm) {
        await this.room.storage.setAlarm(next)
        logger.debug(`[Server] setAlarm(${new Date(next).toISOString()}) set (previousAlarm=${previousAlarm})`)
      } else {
        logger.debug(
          `[Server] Not setting alarm because existing alarm is sooner: previousAlarm=${new Date(previousAlarm).toISOString()}`
        )
      }
    } catch (e) {
      // If storage.getAlarm isn't available or fails, fall back to setting the alarm
      logger.warn('[Server] Failed to read previous alarm; attempting to set alarm anyway', e)
      try {
        await this.room.storage.setAlarm(next)
      } catch (err) {
        logger.error('[Server] Failed to set alarm:', err)
      }
    }
  }

  async onAlarm() {
    // Delegate to IdleChecker which encapsulates the idle/prompt/kick logic
    await this.idleChecker.runCheck()
    // Schedule next check using absolute epoch to avoid ambiguity
    const next2 = Date.now() + IdleChecker.IDLE_CHECKER_INTERVAL_MS
    logger.info(`Rescheduling next idle check at ${new Date(next2).toISOString()}`)
    try {
      const previousAlarm = await this.room.storage.getAlarm()
      if (previousAlarm === null || next2 < previousAlarm) {
        await this.room.storage.setAlarm(next2)
        logger.debug(`[Server] setAlarm(${new Date(next2).toISOString()}) set (previousAlarm=${previousAlarm})`)
      } else {
        logger.debug(
          `[Server] Not rescheduling alarm because existing alarm is sooner: previousAlarm=${new Date(previousAlarm).toISOString()}`
        )
      }
    } catch (e) {
      logger.warn('[Server] Failed to read previous alarm during reschedule; attempting to set alarm anyway', e)
      try {
        await this.room.storage.setAlarm(next2)
      } catch (err) {
        logger.error('[Server] Failed to set alarm during reschedule:', err)
      }
    }
  }

  onConnect(conn: Party.Connection) {
    logger.info(`Connection ${conn.id} connected to room ${this.room.id}`)

    // If we had scheduled a stale marker because the room emptied, cancel it
    if (this._staleTimer) {
      try {
        clearTimeout(this._staleTimer as unknown as number)
      } catch {
        // ignore if environment uses NodeJS.Timeout
        clearTimeout(this._staleTimer as any)
      }
      this._staleTimer = null
      logger.debug(`[Server] Cancelled scheduled stale marker for ${this.room.id} because a connection rejoined`)
    }

    // Send current players, categories, game phase, and timing info to new connection
    const currentPlayers = Array.from(this.players.values()).map((p) => ({
      id: p.id,
      name: p.name,
    }))

    try {
      const metadata: Record<string, unknown> = {
        categories: this.state.categories,
        gamePhase: this.state.gamePhase,
        roundStartTime: this.state.roundStartTime,
        roundLength: this.state.roundLength,
        difficulty: this.state.difficulty,
        maxRounds: this.state.maxRounds,
        sharedPadVisibility: this.state.sharedPadVisibility,
        sharedPadStrokes: this.state.sharedPadStrokes,
        hostId: this.state.hostId,
      }

      const parsed = RoomStateSchema.safeParse(metadata)
      const validated = parsed.success ? parsed.data : normalizeRoomMetadata(metadata)

      conn.send(
        JSON.stringify({
          type: 'room_state',
          players: currentPlayers,
          ...validated,
        })
      )
    } catch (e) {
      // Fallback: send best-effort state directly
      logger.warn('[Server] Failed to validate room_state before sending, sending best-effort payload', e)
      conn.send(
        JSON.stringify({
          type: 'room_state',
          players: currentPlayers,
          categories: this.state.categories,
          gamePhase: this.state.gamePhase,
          roundStartTime: this.state.roundStartTime,
          roundLength: this.state.roundLength,
          difficulty: this.state.difficulty,
          maxRounds: this.state.maxRounds,
          sharedPadVisibility: this.state.sharedPadVisibility,
          sharedPadStrokes: this.state.sharedPadStrokes,
          hostId: this.state.hostId,
        })
      )
    }
  }

  async onMessage(message: string, sender: Party.Connection) {
    try {
      // Parse early so we can inspect message type for rate limiting
      const msg = JSON.parse(message) as any

      // --- Rate limiting per-connection (simple sliding window + warnings) ---
      // Limits are per-message-type; defaults applied for general messages.
      const RATE_WINDOW_MS = 1000
      const DEFAULT_MAX_PER_WINDOW = 20 // sane default: 20 messages / sec
      const TYPE_LIMITS: Record<string, number> = {
        draw_stroke_partial: 500, // many small incremental messages expected
        draw_stroke: 200,
        heartbeat: 1000, // frequent heartbeats ok
        default: DEFAULT_MAX_PER_WINDOW,
      }

      const now = Date.now()
      const prevState = (sender.state as any) || {}
      const rate = prevState._rate || { windowStart: now, count: 0, warnings: 0 }
      // reset window if expired
      if (now - rate.windowStart > RATE_WINDOW_MS) {
        rate.windowStart = now
        rate.count = 0
      }

      const msgType = typeof msg === 'object' && msg?.type ? String(msg.type) : 'unknown'
  const maxForType: number = (TYPE_LIMITS[msgType] ?? TYPE_LIMITS.default) as number

      rate.count = (rate.count || 0) + 1
      // Persist back into connection state (merge with existing keys)
      try {
        sender.setState({ ...prevState, _rate: rate })
      } catch {
        // ignore setState failures
      }

      if (rate.count > maxForType) {
        rate.warnings = (rate.warnings || 0) + 1
        // update state with new warning count
        try {
          sender.setState({ ...prevState, _rate: rate })
        } catch {
          /* ignore */
        }

        // First N times: send a polite warning and ignore this message.
        const WARN_LIMIT = 2
        if (rate.warnings <= WARN_LIMIT) {
          logger.warn(`[Server] Rate limit warning for connection ${sender.id} (type=${msgType}) count=${rate.count}`)
          try {
            sender.send(JSON.stringify({ type: 'rate_limit_warning', message: 'You are sending messages too quickly' }))
          } catch {
            /* ignore send failures */
          }
          // drop this message (don't process)
          return
        }

        // Repeated abuse: close the connection to stop the spammer.
        logger.warn(`[Server] Closing connection ${sender.id} for repeated rate limit violations (type=${msgType})`)
        try {
          // Inform client then close
          sender.send(JSON.stringify({ type: 'rate_limited', reason: 'too_many_messages' }))
        } catch {
          /* ignore */
        }
        try {
          sender.close()
        } catch {
          /* ignore */
        }
        return
      }
      // --- end rate limiting ---


      // Update last activity for the sender (except for join messages, handled separately)
      if (msg.type !== 'join') {
        for (const player of this.players.values()) {
          if (player.connection.id === sender.id) {
            player.lastActivity = Date.now()
            break
          }
        }
      }

      // Handle join specially to track players
      if (msg.type === 'join') {
        // Persist player identity on the connection using PartyKit connection state
        sender.setState({ playerId: msg.playerId, name: msg.name })

        this.players.set(msg.playerId, {
          id: msg.playerId,
          name: msg.name,
          connection: sender,
          categories: this.generateCategoriesForPlayer(), // Assign categories on join
          lastActivity: Date.now(),
        })

        // If this is the first player, make them host
        if (this.players.size === 1) {
          this.state.hostId = msg.playerId
          await this.storage.set('hostId', msg.playerId)
        }

        // Broadcast updated player list derived from current connections (PartyKit API)
        const allPlayers: Array<{ id: string; name: string }> = []
        for (const conn of this.room.getConnections()) {
          const s = (conn.state as any) || {}
          if (s.playerId && s.name) allPlayers.push({ id: s.playerId, name: s.name })
        }

        logger.info('Broadcasting player_joined with players:', allPlayers)

        this.room.broadcast(
          JSON.stringify({
            type: 'player_joined',
            playerId: msg.playerId,
            name: msg.name,
            players: allPlayers,
          })
        )

        return
      }

      // Handle idle confirmation from clients
      if (msg.type === 'idle_confirm') {
        // Find player id for sender
        let senderPlayerId: string | null = null
        for (const [pid, player] of this.players.entries()) {
          if (player.connection.id === sender.id) {
            senderPlayerId = pid
            break
          }
        }
        if (senderPlayerId) {
          const player = this.players.get(senderPlayerId)
          if (player) {
            player.lastActivity = Date.now()
            if (this.state.pendingIdle && this.state.pendingIdle[senderPlayerId]) {
              delete this.state.pendingIdle[senderPlayerId]
              await this.storage.set('pendingIdle', this.state.pendingIdle)
            }
            // Acknowledge to client
            sender.send(JSON.stringify({ type: 'idle_confirmed' }))
            logger.info(`Received idle_confirm from ${player.name} (${senderPlayerId})`)
          }
        }
        return
      }

      // Handle start_game: Store roundLength, relay to all clients
      if (msg.type === 'start_game') {
        logger.debug('[Server] Raw start_game message:', JSON.stringify(msg))

        const playerCount = this.players.size
        if (playerCount < 2) {
          logger.error(
            '[Server] Cannot start game: Not enough players. Current player count:',
            playerCount
          )
          return
        }

        // Prevent duplicate processing
        if (this.state.gamePhase !== 'waiting-room') {
          logger.warn('[Server] Ignoring start_game message - game already started.')
          return
        }

        // Store game settings and update phase
        this.state.roundLength = msg.roundLength
        this.state.difficulty = msg.difficulty
        this.state.maxRounds = msg.rounds
        this.state.gamePhase = 'drawing'
        this.state.readyPlayers = []

        // Persist to storage
        await this.storage.savePartial({
          roundLength: this.state.roundLength,
          difficulty: this.state.difficulty,
          maxRounds: this.state.maxRounds,
          gamePhase: this.state.gamePhase,
          readyPlayers: this.state.readyPlayers,
        })

        logger.info(`Game configured with round length: ${msg.roundLength} seconds`)

        // Just relay the start_game message to all clients
        // Host client's game engine will handle starting the first round
        this.room.broadcast(message)
        return
      }

      // Handle start_round: Generate roundStartTime and broadcast
      if (msg.type === 'start_round') {
        const roundStartTime = Date.now()
        this.state.roundStartTime = roundStartTime
        this.state.gamePhase = 'drawing'
        this.state.currentRound = msg.round
        this.state.readyPlayers = []

        // Persist to storage
        await this.storage.savePartial({
          roundStartTime: this.state.roundStartTime,
          gamePhase: this.state.gamePhase,
          currentRound: this.state.currentRound,
          readyPlayers: this.state.readyPlayers,
        })

        logger.info(`Starting round ${msg.round} at ${roundStartTime}`)

        // Broadcast start_round with server-generated roundStartTime
        this.room.broadcast(
          JSON.stringify({
            ...msg,
            roundStartTime,
          })
        )
        return
      }

      if (msg.type === 'round_complete') {
        this.state.gamePhase = 'scoring'
        await this.storage.set('gamePhase', 'scoring')
      }

      if (msg.type === 'game_complete') {
        this.state.gamePhase = 'complete'
        this.state.readyPlayers = []
        await this.storage.savePartial({
          gamePhase: this.state.gamePhase,
          readyPlayers: this.state.readyPlayers,
        })
      }

      // Handle player_ready: Track ready players for post-game
      if (msg.type === 'player_ready') {
        if (!this.state.readyPlayers.includes(msg.playerId)) {
          this.state.readyPlayers.push(msg.playerId)
          await this.storage.set('readyPlayers', this.state.readyPlayers)
        }
        logger.info(
          `Player ${msg.playerId} is ready. Ready count: ${this.state.readyPlayers.length}/${this.players.size}`
        )

        // Broadcast ready status to all players
        this.room.broadcast(
          JSON.stringify({
            type: 'ready_status',
            readyCount: this.state.readyPlayers.length,
            totalPlayers: this.players.size,
          })
        )
        return
      }

      // Handle restart_game: Reset game state and notify all players
      if (msg.type === 'restart_game') {
        logger.info('[Server] Host initiated game restart')

        // Reset game state
        this.state.readyPlayers = []
        this.state.gamePhase = 'waiting-room'
        this.state.currentRound = 0
        this.state.roundStartTime = undefined
        this.state.playerScores = {}

        // Persist to storage
        await this.storage.savePartial({
          readyPlayers: this.state.readyPlayers,
          gamePhase: this.state.gamePhase,
          currentRound: this.state.currentRound,
          roundStartTime: this.state.roundStartTime,
          playerScores: this.state.playerScores,
        })

        // Broadcast restart to all players so they navigate to waiting room
        this.room.broadcast(message)
        return
      }

      // Handle heartbeat: Just update last activity (already done above)
      if (msg.type === 'heartbeat') {
        // Activity already updated above, no need to broadcast
        return
      }

      // Handle settings_update: Host broadcasts settings changes to all players
      if (msg.type === 'settings_update') {
        // Find the playerId associated with the sender connection
        let senderPlayerId: string | null = null
        for (const [pid, player] of this.players.entries()) {
          if (player.connection.id === sender.id) {
            senderPlayerId = pid
            break
          }
        }

        // Only allow the current host to broadcast settings updates
        if (senderPlayerId && this.state.hostId && senderPlayerId === this.state.hostId) {
          // Persist the settings in storage so new joiners receive them
          this.state.difficulty = msg.difficulty
          this.state.maxRounds = msg.rounds
          this.state.roundLength = msg.roundLength

          await this.storage.savePartial({
            difficulty: this.state.difficulty,
            maxRounds: this.state.maxRounds,
            roundLength: this.state.roundLength,
          })

          logger.info('[Server] Broadcasting settings update from host:', msg)
          this.room.broadcast(message)
        } else {
          logger.warn('[Server] Ignored settings_update from non-host connection', sender.id)
        }

        return
      }

      // Handle draw_stroke: Relay stroke data to all clients (including sender)
      if (msg.type === 'draw_stroke') {
        // Optional: We could validate senderPlayerId here but allowing all players to draw in waiting room
        // Persist stroke in storage so new joiners receive it
        try {
          this.state.sharedPadStrokes.push(msg.stroke)
          // Save to storage asynchronously (don't await to keep it fast)
          this.storage.set('sharedPadStrokes', this.state.sharedPadStrokes)
        } catch (e) {
          logger.error('[Server] Error persisting stroke:', e)
        }
        this.room.broadcast(message)
        return
      }

      // Handle draw_stroke_partial: Relay incremental stroke points to all clients
      if (msg.type === 'draw_stroke_partial') {
        this.room.broadcast(message)
        return
      }

      // Handle drawpad_clear: Only allow host to clear the shared waiting-room pad
      if (msg.type === 'drawpad_clear') {
        // Find the playerId associated with the sender connection
        let senderPlayerId: string | null = null
        for (const [pid, player] of this.players.entries()) {
          if (player.connection.id === sender.id) {
            senderPlayerId = pid
            break
          }
        }

        if (senderPlayerId && this.state.hostId && senderPlayerId === this.state.hostId) {
          logger.info('[Server] Host cleared drawpad')
          // Clear persisted strokes
          this.state.sharedPadStrokes = []
          await this.storage.set('sharedPadStrokes', this.state.sharedPadStrokes)
          this.room.broadcast(message)
        } else {
          logger.info('[Server] Ignored drawpad_clear from non-host connection', sender.id)
        }

        return
      }

      // remove_stroke handler removed - eraser implemented as white stroke overlay

      // Handle drawpad_restore: allow host to restore a previously saved set of strokes
      if (msg.type === 'drawpad_restore') {
        let senderPlayerId: string | null = null
        for (const [pid, player] of this.players.entries()) {
          if (player.connection.id === sender.id) {
            senderPlayerId = pid
            break
          }
        }

        if (senderPlayerId && this.state.hostId && senderPlayerId === this.state.hostId) {
          logger.info('[Server] Host requested drawpad_restore')
          // Persist restored strokes
          try {
            this.state.sharedPadStrokes = (msg as any).strokes || []
            await this.storage.set('sharedPadStrokes', this.state.sharedPadStrokes)
          } catch (e) {
            logger.error('[Server] Error restoring strokes:', e)
          }
          this.room.broadcast(message)
        } else {
          logger.info('[Server] Ignored drawpad_restore from non-host connection', sender.id)
        }

        return
      }

      // Handle pad_visibility: Only allow host to change visibility
      if (msg.type === 'pad_visibility') {
        let senderPlayerId: string | null = null
        for (const [pid, player] of this.players.entries()) {
          if (player.connection.id === sender.id) {
            senderPlayerId = pid
            break
          }
        }

        if (senderPlayerId && this.state.hostId && senderPlayerId === this.state.hostId) {
          this.state.sharedPadVisibility = (msg as any).visible
          await this.storage.set('sharedPadVisibility', this.state.sharedPadVisibility)
          logger.info('[Server] Host updated pad visibility to', (msg as any).visible)
          this.room.broadcast(message)
        } else {
          logger.warn('[Server] Ignored pad_visibility from non-host connection', sender.id)
        }

        return
      }

      // Handle request_game_state to send the current game state to the requester
      if (msg.type === 'request_game_state') {
        const currentPlayers = Array.from(this.players.values()).map((p) => ({
          id: p.id,
          name: p.name,
          categories: p.categories, // Include categories in room_state
        }))

        try {
          const metadata: Record<string, unknown> = {
            categories: this.state.categories,
            gamePhase: this.state.gamePhase,
            roundStartTime: this.state.roundStartTime,
            roundLength: this.state.roundLength,
            difficulty: this.state.difficulty,
            maxRounds: this.state.maxRounds,
            sharedPadVisibility: this.state.sharedPadVisibility,
            sharedPadStrokes: this.state.sharedPadStrokes,
            hostId: this.state.hostId,
          }

          const parsed = RoomStateSchema.safeParse(metadata)
          const validated = parsed.success ? parsed.data : normalizeRoomMetadata(metadata)

          sender.send(
            JSON.stringify({
              type: 'room_state',
              players: currentPlayers,
              ...validated,
            })
          )
        } catch (e) {
          logger.warn('[Server] Failed to validate room_state before sending, sending best-effort payload', e)
          sender.send(
            JSON.stringify({
              type: 'room_state',
              players: currentPlayers,
              categories: this.state.categories,
              gamePhase: this.state.gamePhase,
              roundStartTime: this.state.roundStartTime,
              roundLength: this.state.roundLength,
              difficulty: this.state.difficulty,
              maxRounds: this.state.maxRounds,
              sharedPadVisibility: this.state.sharedPadVisibility,
              sharedPadStrokes: this.state.sharedPadStrokes,
              hostId: this.state.hostId,
            })
          )
        }

        return
      }

      // For all other messages, just relay to all clients including sender
      // (Game logic is handled client-side)
      this.room.broadcast(message)
    } catch (error) {
      logger.error('Error processing message:', error)
    }
  }

  async onClose(connection: Party.Connection) {
    // Determine disconnected player's id via connection state (PartyKit)
    const connState = (connection.state as any) || {}
    let disconnectedPlayerId = connState.playerId || null
    // Fallback: if state didn't include playerId, match by connection id in our players map
    if (!disconnectedPlayerId) {
      for (const [pid, player] of this.players.entries()) {
        if (player.connection && player.connection.id === connection.id) {
          disconnectedPlayerId = pid
          break
        }
      }
    }

    // Capture display name before removing from players map
    const leftPlayerName = disconnectedPlayerId
      ? this.players.get(disconnectedPlayerId)?.name || connState.name
      : undefined

    // Remove from our players map if present (do this after capturing name)
    if (disconnectedPlayerId && this.players.has(disconnectedPlayerId)) {
      this.players.delete(disconnectedPlayerId)
    }

    // Notify others that this player left (include display name when available)
    try {
      this.room.broadcast(
        JSON.stringify({
          type: 'player_left',
          playerId: disconnectedPlayerId,
          name: leftPlayerName,
        })
      )
    } catch (e) {
      console.warn('[Server] Error broadcasting player_left for', disconnectedPlayerId, e)
    }

    console.log('[Server] onClose:', { disconnectedPlayerId, leftPlayerName, hostId: this.state.hostId })

    // After removal, inspect current connections to decide host transfer or room cleanup
    const remaining: Array<{ playerId: string; name: string }> = []
    for (const conn of this.room.getConnections()) {
      const s = (conn.state as any) || {}
      if (s.playerId && s.name) remaining.push({ playerId: s.playerId, name: s.name })
    }

    // If the disconnected player was host, transfer host if anyone remains
    if (disconnectedPlayerId === this.state.hostId) {
      // Exclude the disconnected player in case the room's connection list wasn't updated yet
      const filtered = remaining.filter((r) => r.playerId !== disconnectedPlayerId)
      console.log('[Server] remaining connections:', remaining, 'filtered:', filtered)
      if (filtered.length > 0) {
        const newHost = filtered[0]
        if (newHost) {
          this.state.hostId = newHost.playerId
          await this.storage.set('hostId', newHost.playerId)
          try {
            this.room.broadcast(
              JSON.stringify({ type: 'host_changed', newHostId: newHost.playerId })
            )
          } catch (e) {
            console.warn('[Server] Error broadcasting host_changed', e)
          }
          console.log(`Host transferred to ${newHost.name} (${newHost.playerId})`)
        }
      } else {
        // No players left — mark room as abandoned
        this.state.hostId = null
        console.log(`Room ${this.room.id} is now empty`)

        // Schedule marking room as stale after a delay (allows quick reconnects)
        // PartyKit will eventually garbage collect truly abandoned rooms
        if (this._staleTimer) {
          try {
            clearTimeout(this._staleTimer as unknown as number)
          } catch {
            clearTimeout(this._staleTimer as any)
          }
        }
        this._staleTimer = setTimeout(async () => {
          try {
            // Mark room as stale but don't delete it
            // This allows the room code to still work if someone returns
            const staleMarker = {
              abandoned_at: Date.now(),
              last_host: this.state.hostId,
            }
            await this.storage.set('_stale' as any, staleMarker)
            logger.info(`[Server] Marked room ${this.room.id} as stale (abandoned at ${new Date(staleMarker.abandoned_at).toISOString()})`)
          } catch (err) {
            logger.warn('[Server] Failed to mark room as stale (ignored):', err)
          } finally {
            this._staleTimer = null
          }
        }, GameServer.STALE_MARK_DELAY_MS)
      }
    }
  }

  onError(_connection: Party.Connection, error: Error) {
    console.error('Connection error:', error)
  }

  async onRequest(req: Party.Request) {
    const url = new URL(req.url)

    // Debug endpoint to inspect storage
    if (url.pathname.endsWith('/debug/storage')) {
      try {
        const data = await this.storage.dumpAll()
        return new Response(JSON.stringify(data, null, 2), {
          headers: { 'Content-Type': 'application/json' },
        })
      } catch (e) {
        return new Response(JSON.stringify({ error: String(e) }), {
          status: 500,
          headers: { 'Content-Type': 'application/json' },
        })
      }
    }

    // Debug endpoint to inspect current state
    if (url.pathname.endsWith('/debug/state')) {
      return new Response(
        JSON.stringify(
          {
            state: this.state,
            players: Array.from(this.players.values()).map((p) => ({
              id: p.id,
              name: p.name,
              lastActivity: p.lastActivity,
            })),
            connections: this.room.getConnections ?
              Array.from(this.room.getConnections()).length :
              'unavailable',
          },
          null,
          2
        ),
        {
          headers: { 'Content-Type': 'application/json' },
        }
      )
    }

    return new Response('Not found', { status: 404 })
  }

  // Helper function to generate categories for a player
  private generateCategoriesForPlayer(): string[] {
    // Replace with actual category generation logic
    return ['Category1', 'Category2', 'Category3']
  }

  // Helper: list connections which have a playerId in their connection state.
  // Returns an array of { playerId, name } in the order the server's room provides.
  private listActiveConnections(): Array<{ playerId: string; name: string }> {
    try {
      const conns =
        this.room.getConnections && typeof this.room.getConnections === 'function'
          ? (this.room.getConnections() as any[])
          : (this.room as any)._connections || []

      const result: Array<{ playerId: string; name: string }> = []
      for (const c of conns) {
        const state = (c.state as any) || {}
        if (state.playerId) {
          result.push({ playerId: state.playerId, name: state.name || 'Player' })
        }
      }
      return result
    } catch (e) {
      console.warn('[Server] listActiveConnections failed', e)
      return []
    }
  }
}

GameServer satisfies Party.Worker
