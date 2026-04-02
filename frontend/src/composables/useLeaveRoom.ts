import { useRouter } from "vue-router";
import { useGameConnection } from "@/composables/useGameConnection";
import { useGameStore } from "@/stores/game";
import type { useGameEngine } from "@/composables/useGameEngine";
import type { ShallowRef } from "vue";

/**
 * Shared leave-room logic. Disconnects the WebSocket, clears the game engine
 * (host only), resets Pinia state, and navigates back to the lobby.
 */
export function useLeaveRoom(gameEngineRef: ShallowRef<ReturnType<typeof useGameEngine> | null>) {
  const store = useGameStore();
  const router = useRouter();
  const { disconnect } = useGameConnection();

  function leaveRoom() {
    disconnect();
    gameEngineRef.value = null;
    store.reset();
    router.push("/");
  }

  return { leaveRoom };
}
