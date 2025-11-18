import { useGameEngine } from './useGameEngine'

// Global game engine instance for the host
// This is null for non-host players
let gameEngineInstance: ReturnType<typeof useGameEngine> | null = null

export function initGameEngine() {
  if (!gameEngineInstance) {
    gameEngineInstance = useGameEngine()
  }
  return gameEngineInstance
}

export function getGameEngine() {
  return gameEngineInstance
}

export function clearGameEngine() {
  gameEngineInstance = null
}
