import { z } from 'zod'

import type { DrawStroke } from '@/shared/types'

export const RoomStateSchema = z.object({
  gamePhase: z.enum(['waiting-room', 'drawing', 'guessing', 'scoring', 'complete']),
  difficulty: z.string(),
  maxRounds: z.preprocess((v) => (typeof v === 'string' && v.trim() !== '' ? Number(v) : v), z.number().int().finite()),
  roundLength: z.preprocess((v) => (typeof v === 'string' && v.trim() !== '' ? Number(v) : v), z.number().int().finite()),
  currentRound: z.preprocess((v) => (typeof v === 'string' && v.trim() !== '' ? Number(v) : v), z.number().int().finite()),
  roundStartTime: z.preprocess((v) => (typeof v === 'string' && v.trim() !== '' ? Number(v) : v), z.number().finite()).optional(),
  hostId: z.union([z.string(), z.null()]),
  sharedPadStrokes: z.array(z.any()),
  sharedPadVisibility: z.boolean(),
  playerScores: z.record(z.string(), z.preprocess((v) => (typeof v === 'string' && v.trim() !== '' ? Number(v) : v), z.number().finite())).optional(),
  readyPlayers: z.array(z.string()),
  pendingIdle: z.record(z.string(), z.preprocess((v) => (typeof v === 'string' && v.trim() !== '' ? Number(v) : v), z.number().finite())).optional(),
  categories: z.array(z.string()),
})

export type RoomState = z.infer<typeof RoomStateSchema>

export const DEFAULT_ROOM_STATE: RoomState = {
  gamePhase: 'waiting-room',
  difficulty: 'medium',
  maxRounds: 5,
  roundLength: 6,
  currentRound: 0,
  roundStartTime: undefined,
  hostId: null,
  sharedPadStrokes: [],
  sharedPadVisibility: true,
  playerScores: {},
  readyPlayers: [],
  pendingIdle: {},
  categories: [],
}

// Normalizer that coerces/validates loose metadata into a safe RoomState
export function normalizeRoomMetadata(metadata?: Record<string, unknown>): RoomState {
  const m = metadata ?? {}

  const gp = z.enum(['waiting-room', 'drawing', 'guessing', 'scoring', 'complete']).safeParse(m.gamePhase)
  const gamePhase = gp.success ? (gp.data as RoomState['gamePhase']) : DEFAULT_ROOM_STATE.gamePhase

  const difficultyRes = z.string().safeParse(m.difficulty)
  const difficulty = difficultyRes.success ? difficultyRes.data : DEFAULT_ROOM_STATE.difficulty

  const maxRoundsRes = z.preprocess((v) => (typeof v === 'string' && v.trim() !== '' ? Number(v) : v), z.number().int().finite()).safeParse(m.maxRounds)
  const maxRounds = maxRoundsRes.success ? maxRoundsRes.data : DEFAULT_ROOM_STATE.maxRounds

  const roundLengthRes = z.preprocess((v) => (typeof v === 'string' && v.trim() !== '' ? Number(v) : v), z.number().int().finite()).safeParse(m.roundLength)
  const roundLength = roundLengthRes.success ? roundLengthRes.data : DEFAULT_ROOM_STATE.roundLength

  const currentRoundRes = z.preprocess((v) => (typeof v === 'string' && v.trim() !== '' ? Number(v) : v), z.number().int().finite()).safeParse(m.currentRound)
  const currentRound = currentRoundRes.success ? currentRoundRes.data : DEFAULT_ROOM_STATE.currentRound

  const roundStartTimeRes = z.preprocess((v) => (typeof v === 'string' && v.trim() !== '' ? Number(v) : v), z.number().finite()).safeParse(m.roundStartTime)
  const roundStartTime = roundStartTimeRes.success ? roundStartTimeRes.data : DEFAULT_ROOM_STATE.roundStartTime

  const hostIdRes = z.union([z.string(), z.null()]).safeParse(m.hostId)
  const hostId = hostIdRes.success ? hostIdRes.data : DEFAULT_ROOM_STATE.hostId

  const sharedPadStrokes = Array.isArray(m.sharedPadStrokes) ? (m.sharedPadStrokes as DrawStroke[]) : DEFAULT_ROOM_STATE.sharedPadStrokes

  const sharedPadVisibility = typeof m.sharedPadVisibility === 'boolean' ? m.sharedPadVisibility : DEFAULT_ROOM_STATE.sharedPadVisibility

  const playerScoresRes = z.record(z.string(), z.preprocess((v) => (typeof v === 'string' && v.trim() !== '' ? Number(v) : v), z.number().finite())).safeParse(m.playerScores)
  const playerScores = playerScoresRes.success ? playerScoresRes.data : DEFAULT_ROOM_STATE.playerScores

  const readyPlayers = Array.isArray(m.readyPlayers) ? (m.readyPlayers as unknown[]).filter((x) => typeof x === 'string') as string[] : DEFAULT_ROOM_STATE.readyPlayers

  const pendingIdleRes = z.record(z.string(), z.preprocess((v) => (typeof v === 'string' && v.trim() !== '' ? Number(v) : v), z.number().finite())).safeParse(m.pendingIdle)
  const pendingIdle = pendingIdleRes.success ? pendingIdleRes.data : DEFAULT_ROOM_STATE.pendingIdle

  const categories = Array.isArray(m.categories) ? (m.categories as unknown[]).filter((x) => typeof x === 'string') as string[] : DEFAULT_ROOM_STATE.categories

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

export default RoomStateSchema
