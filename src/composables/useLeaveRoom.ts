import { useRouter } from 'vue-router'

import { clearGameEngine } from '@/composables/gameEngineInstance'
import { useGameConnection } from '@/composables/useGameConnection'
import { useGameStore } from '@/stores/game'

export function useLeaveRoom() {
  const router = useRouter()
  const { disconnect } = useGameConnection()
  const store = useGameStore()

  async function leave() {
    // Ensure the socket is closed and engine cleared first
    try {
      disconnect()
    } catch {
      // ignore
    }
    try {
      clearGameEngine()
    } catch {
      // ignore
    }

    // Navigate to home first so app-level watchers don't redirect back into a room
    try {
      await router.replace('/')
    } catch {
      // ignore navigation errors
    }

    // Reset store state after navigation completes
    try {
      store.reset()
    } catch {
      // ignore
    }
  }

  return { leave }
}

export default useLeaveRoom
