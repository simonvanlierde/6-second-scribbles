import { useRouter } from "vue-router";

import { useGameConnection } from "@/composables/useGameConnection";
import { useGameStore } from "@/stores/game";

/**
 * The shared "leave room" action used by every in-game view: send the explicit
 * leave (via disconnect), reset local state, and return home.
 */
export function useLeaveRoom() {
  const router = useRouter();
  const store = useGameStore();
  const { disconnect } = useGameConnection();

  function leaveRoom() {
    disconnect();
    store.reset();
    void router.push({ name: "home" });
  }

  return { leaveRoom };
}
