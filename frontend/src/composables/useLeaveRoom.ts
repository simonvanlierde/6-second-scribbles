import { useRouter } from "vue-router";
import { useGameConnection } from "@/composables/useGameConnection";
import { useGameStore } from "@/stores/game";

/**
 * Shared leave-room logic. Disconnects the WebSocket, resets Pinia state,
 * and navigates back to the home screen.
 */
export function useLeaveRoom() {
  const store = useGameStore();
  const router = useRouter();
  const { disconnect } = useGameConnection();

  function leaveRoom() {
    disconnect();
    store.reset();
    router.push({ name: "home" });
  }

  return { leaveRoom };
}
