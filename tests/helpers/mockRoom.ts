/* eslint-disable @typescript-eslint/no-explicit-any */

/**
 * Test helpers for mocking PartyKit Room and Connection objects
 */

export function createMockStorage() {
  const data = new Map<string, any>()

  return {
    async get<T>(key: string): Promise<T | undefined> {
      return data.get(key) as T | undefined
    },
    async put(key: string, value: any): Promise<void> {
      data.set(key, value)
    },
    async delete(key: string): Promise<boolean> {
      return data.delete(key)
    },
    async list(): Promise<Map<string, any>> {
      return new Map(data)
    },
    async setAlarm(_time: number): Promise<void> {
      // Mock - do nothing
    },
    async getAlarm(): Promise<number | null> {
      return null
    },
    async deleteAlarm(): Promise<void> {
      // Mock - do nothing
    },
    // Expose for testing
    _data: data,
  }
}

export function createMockConnection(id: string, room: any) {
  const sentMessages: string[] = []

  const conn: any = {
    id,
    state: undefined,
    setState(s: any) {
      this.state = s
    },
    send: (msg: string) => {
      sentMessages.push(msg)
    },
    close: () => {},
    // Helper for tests to check sent messages
    getSent: () => sentMessages,
  }
  room._connections.push(conn)
  return conn
}

export function createMockRoom() {
  const broadcasted: string[] = []
  const storage = createMockStorage()

  return {
    id: 'test-room',
    _connections: [] as any[],
    storage,
    broadcast: (msg: string) => broadcasted.push(msg),
    getBroadcasts: () => broadcasted,
    getConnections() {
      return this._connections
    },
  }
}
