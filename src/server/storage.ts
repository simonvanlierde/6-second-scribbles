/**
 * Storage Helper Utilities for PartyKit Room.storage
 *
 * Provides type-safe access to Room.storage with defaults and batch operations
 */

// (no local DrawStroke usage here; shapes live in shared schema)
import type { RoomState } from '../shared/schemas/room.js'
import { DEFAULT_ROOM_STATE } from '../shared/schemas/room.js'
import type * as Party from 'partykit/server'

export class RoomStorage {
  constructor(private storage: Party.Storage) {}

  /**
   * Get a value from storage with a default fallback
   */
  async get<K extends keyof RoomState>(
    key: K,
    defaultValue: RoomState[K]
  ): Promise<RoomState[K]> {
    const value = await this.storage.get<RoomState[K]>(key)
    return value !== undefined ? value : defaultValue
  }

  /**
   * Set a value in storage
   */
  async set<K extends keyof RoomState>(key: K, value: RoomState[K]): Promise<void> {
    const impl: any = this.storage as any
    if (typeof impl.put === 'function') {
      await impl.put(key, value)
      return
    }
    if (typeof impl.set === 'function') {
      await impl.set(key, value)
      return
    }
    throw new Error('Underlying storage implementation does not provide put/set')
  }

  /**
   * Load entire room state from storage (with defaults for missing values)
   */
  async loadAll(): Promise<RoomState> {
    const [
      gamePhase,
      difficulty,
      maxRounds,
      roundLength,
      currentRound,
      roundStartTime,
      hostId,
      sharedPadStrokes,
      sharedPadVisibility,
      playerScores,
      readyPlayers,
      pendingIdle,
      categories,
    ] = await Promise.all([
      this.get('gamePhase', DEFAULT_ROOM_STATE.gamePhase),
      this.get('difficulty', DEFAULT_ROOM_STATE.difficulty),
      this.get('maxRounds', DEFAULT_ROOM_STATE.maxRounds),
      this.get('roundLength', DEFAULT_ROOM_STATE.roundLength),
      this.get('currentRound', DEFAULT_ROOM_STATE.currentRound),
      this.get('roundStartTime', DEFAULT_ROOM_STATE.roundStartTime),
      this.get('hostId', DEFAULT_ROOM_STATE.hostId),
      this.get('sharedPadStrokes', DEFAULT_ROOM_STATE.sharedPadStrokes),
      this.get('sharedPadVisibility', DEFAULT_ROOM_STATE.sharedPadVisibility),
      this.get('playerScores', DEFAULT_ROOM_STATE.playerScores),
      this.get('readyPlayers', DEFAULT_ROOM_STATE.readyPlayers),
      this.get('pendingIdle', DEFAULT_ROOM_STATE.pendingIdle),
      this.get('categories', DEFAULT_ROOM_STATE.categories),
    ])

    return {
      gamePhase,
      difficulty,
      maxRounds,
      roundLength,
      currentRound,
      roundStartTime,
      hostId,
      sharedPadStrokes,
      sharedPadVisibility,
      playerScores,
      readyPlayers,
      pendingIdle,
      categories,
    }
  }

  /**
   * Save multiple values at once
   */
  async savePartial(updates: Partial<RoomState>): Promise<void> {
    const impl: any = this.storage as any
    const promises = Object.entries(updates).map(([key, value]) => {
      if (typeof impl.put === 'function') return impl.put(key, value)
      if (typeof impl.set === 'function') return impl.set(key, value)
      return Promise.reject(new Error('Underlying storage implementation does not provide put/set'))
    })
    await Promise.all(promises)
  }

  /**
   * Reset room to default state
   */
  async reset(): Promise<void> {
    await this.savePartial(DEFAULT_ROOM_STATE)
  }

  /**
   * Get all keys in storage (for debugging)
   */
  async listKeys(): Promise<string[]> {
    const keys = await this.storage.list()
    return Array.from(keys.keys())
  }

  /**
   * Get all data in storage (for debugging)
   */
  async dumpAll(): Promise<Record<string, unknown>> {
    const map = await this.storage.list()
    const result: Record<string, unknown> = {}
    for (const [key, value] of map.entries()) {
      result[key] = value
    }
    return result
  }
}
