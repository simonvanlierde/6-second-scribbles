import { useRouter } from "vue-router";

import { useGameConnection } from "@/composables/useGameConnection";
import { useGameStore } from "@/stores/game";

/**
 * The shared "leave room" action used by every in-game view: send the explicit
 * leave (via disconnect), reset local state, and return home. Pass `beforeLeave`
 * for view-specific cleanup (e.g. clearing a results auto-restart timer).
 */
export function useLeaveRoom(beforeLeave?: () => void) {
  const router = useRouter();
  const store = useGameStore();
  const { disconnect } = useGameConnection();

  function leaveRoom() {
    beforeLeave?.();
    disconnect();
    store.reset();
    void router.push({ name: "home" });
  }

  return { leaveRoom };
}
