import type * as Party from 'partykit/server'
import { describe, expect, it } from 'vitest'

import GameServer from '../src/server'
import { DEFAULT_ROOM_STATE, normalizeRoomMetadata } from '../src/shared/schemas/room'

// Minimal fake storage implementation for tests
class FakeStorage {
  private map = new Map<string, unknown>()
  async get(key: string) { return this.map.get(key) }
  async set(key: string, value: unknown) { this.map.set(key, value) }
  async put(key: string, value: unknown) { this.map.set(key, value) }
  async list() { return this.map }
  async delete(key: string) { this.map.delete(key) }
  // alarm methods
  async getAlarm(): Promise<null> { return null }
  async setAlarm(_v: number): Promise<void> { return }
}

class FakeRoom {
  storage = new FakeStorage()
  id = 'test-room'
  private conns: Array<unknown> = []
  broadcast(_msg: string) {
    // no-op for tests
  }
  getConnections() { return this.conns }
}

describe('normalizeRoomMetadata and GameServer resilience', () => {
  it('normalizes malformed metadata via normalizeRoomMetadata', () => {
    const malformed: Record<string, unknown> = {
      gamePhase: 'not-a-real-phase',
      maxRounds: '10',
      roundLength: '45',
      readyPlayers: [123, 'p1'],
      pendingIdle: { p1: '1609459200000' },
      categories: ['cat1', 2, null],
    }

    const normalized = normalizeRoomMetadata(malformed)
    expect(normalized.gamePhase).toBe(DEFAULT_ROOM_STATE.gamePhase)
    expect(normalized.maxRounds).toBe(10)
    expect(normalized.roundLength).toBe(45)
    expect(Array.isArray(normalized.readyPlayers)).toBe(true)
    expect(normalized.readyPlayers).toContain('p1')
  expect(typeof (normalized.pendingIdle?.p1)).toBe('number')
    expect(normalized.categories).toEqual(['cat1'])
  })

  it('GameServer setRoomMetadata accepts malformed metadata and updates state safely', async () => {
  const room = new FakeRoom()
  const server = new GameServer(room as unknown as Party.Room)

    // Call the internal setRoomMetadata via idleChecker options with malformed data
    const malformed: Record<string, unknown> = {
      gamePhase: 'guessing',
      maxRounds: '3',
      roundLength: '30',
      readyPlayers: ['p1'],
      pendingIdle: { p1: '1609459200000' },
    }

    // The IdleChecker will call our provided setRoomMetadata; call it directly to simulate
    // Note: in constructor we wired setRoomMetadata as an async function
  await (server as unknown as { idleChecker: { options: { setRoomMetadata(m: Record<string, unknown>): Promise<void> } } }).idleChecker.options.setRoomMetadata(malformed)

  // Assert server.state now contains normalized values
  const s = (server as unknown as { state: Record<string, unknown> }).state
  expect((s.maxRounds as number)).toBe(3)
  expect((s.roundLength as number)).toBe(30)
  expect((s.readyPlayers as string[])).toContain('p1')
  const pendingIdle = s.pendingIdle as Record<string, number>
  expect(typeof pendingIdle.p1).toBe('number')
  })
})
