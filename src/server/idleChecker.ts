import logger from '../utils/logger'
import { normalizeActivity, safeIso } from './logging'
import type { Player, RoomMetadata } from './types'

export type BroadcastFn = (msg: string) => void

export interface IdleCheckerOptions {
  players: Map<string, Player>
  roomId: string
  getRoomMetadata: () => RoomMetadata
  setRoomMetadata: (m: RoomMetadata) => void
  broadcast: BroadcastFn
}

export class IdleChecker {
  // Per-phase timeout constants
  static readonly WAITING_ROOM_TIMEOUT_MS = 5 * 60 * 1000 // 5 minutes
  static readonly INGAME_IDLE_TIMEOUT_MS = 2.5 * 60 * 1000 // 2.5 minutes
  static readonly IDLE_CHECKER_INTERVAL_MS = 10 * 1000 // check interval
  static readonly PROMPT_TIMEOUT_MS = 30 * 1000 // prompt length

  options: IdleCheckerOptions
  // Guard against multiple rapid invocations from the alarm system
  private lastRunMs = 0

  constructor(options: IdleCheckerOptions) {
    this.options = options
  }

  async runCheck() {
    const { players, roomId } = this.options
    const room = this.options.getRoomMetadata()
    logger.info(
      `IdleChecker fired for room ${roomId} at ${safeIso(Date.now())} (phase=${room.gamePhase})`
    )

    // Debounce: if runCheck was invoked too recently, skip to avoid thrashing
    const now = Date.now()
    if (now - this.lastRunMs < 500) {
      logger.debug(`IdleChecker: skipping run because last run was ${now - this.lastRunMs}ms ago`)
      return
    }
    this.lastRunMs = now

    const isWaitingRoom = room.gamePhase === 'waiting-room'
    const idleTimeoutMs = isWaitingRoom
      ? IdleChecker.WAITING_ROOM_TIMEOUT_MS
      : IdleChecker.INGAME_IDLE_TIMEOUT_MS

    if (room.gamePhase === 'complete') {
      // no-op when game complete
      return
    }

    // now already defined above
    const idleToDisconnect: string[] = []

    if (!room.pendingIdle) room.pendingIdle = {}

    for (const [playerId, player] of players.entries()) {
      // Defensive normalization: tests or some code paths may leave lastActivity undefined
      const lastActivityNum = normalizeActivity(player.lastActivity, now)
      const idleTime = now - lastActivityNum

      const pendingExpiryDebug = room.pendingIdle ? room.pendingIdle[playerId] : undefined
      const lastActivityIso = safeIso(player.lastActivity)

      logger.debug(
        `Player ${player.name} (${playerId}) lastActivity=${lastActivityIso} idle=${Math.floor(
          idleTime / 1000
        )}s pendingExpiry=${pendingExpiryDebug}`
      )

      const pendingExpiry = room.pendingIdle[playerId]
      if (pendingExpiry) {
        if (now >= pendingExpiry) {
          logger.info(`Idle prompt expired for ${player.name} (${playerId}), disconnecting.`)
          idleToDisconnect.push(playerId)
          delete room.pendingIdle[playerId]
        }
        continue
      }

      const promptThreshold = idleTimeoutMs - IdleChecker.PROMPT_TIMEOUT_MS
      if (idleTime >= idleTimeoutMs) {
        logger.info(
          `Player ${player.name} (${playerId}) exceeded idle timeout (${Math.floor(idleTime / 1000)}s), disconnecting.`
        )
        idleToDisconnect.push(playerId)
      } else if (idleTime >= promptThreshold) {
        try {
          player.connection.send(
            JSON.stringify({ type: 'idle_prompt', timeoutMs: IdleChecker.PROMPT_TIMEOUT_MS })
          )
          room.pendingIdle[playerId] = now + IdleChecker.PROMPT_TIMEOUT_MS
          logger.info(
            `Sent idle prompt to ${player.name} (${playerId}); expires in ${Math.floor(
              IdleChecker.PROMPT_TIMEOUT_MS / 1000
            )}s`
          )
        } catch (e) {
          console.warn('[Server] Failed to send idle prompt to', playerId, e)
        }
      }
    }

    for (const playerId of idleToDisconnect) {
      const player = players.get(playerId)
      if (player) {
        logger.info(`[Server] Disconnecting idle player: ${player.name}`)
        // Try to notify the player first
        try {
          player.connection.send(JSON.stringify({ type: 'kicked', reason: 'idle' }))
        } catch (e) {
          console.warn('[Server] Failed to send kicked message to', playerId, e)
        }

        // Broadcast player_left to room (do this before closing connection to avoid send-after-close)
        try {
          const playerName = player.name
          this.options.broadcast(
            JSON.stringify({ type: 'player_left', playerId, name: playerName })
          )
        } catch (e) {
          console.warn('[Server] Error broadcasting player_left for', playerId, e)
        }

        try {
          player.connection.close(4000, 'Idle: kicked')
        } catch (e) {
          console.warn('[Server] Error closing connection for', playerId, e)
        }

        players.delete(playerId)
      }
    }

    // Persist any metadata mutation via setRoomMetadata
    this.options.setRoomMetadata(room)
  }
}

export default IdleChecker
