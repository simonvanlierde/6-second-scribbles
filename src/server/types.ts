import type * as Party from 'partykit/server'

export interface Player {
  id: string
  name: string
  connection: Party.Connection
  categories: string[]
  lastActivity: number
}

export interface RoomMetadata {
  categories: string[]
  gamePhase: string
  roundStartTime?: number
  roundLength?: number
  difficulty?: string
  maxRounds?: number
  sharedPadVisibility?: boolean
  strokes?: Array<{ color: string; width: number; points: Array<{ x: number; y: number }> }>
  // legacy/alias used in some parts of the codebase
  sharedPadStrokes?: Array<{
    color: string
    width: number
    points: Array<{ x: number; y: number }>
  }>
  readyPlayers: Set<string>
  pendingIdle?: Record<string, number>
}

export interface ExtendedRoom extends Party.Room {
  metadata: RoomMetadata
}
