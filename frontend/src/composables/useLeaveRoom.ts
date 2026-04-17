import { useRouter } from "vue-router";
import { useGameConnection } from "@/composables/useGameConnection";
import { useGameStore } from "@/stores/game";

export function useLeaveRoom() {
  const router = useRouter();
  const store = useGameStore();
  const { disconnect } = useGameConnection();

  function leaveRoom() {
    if (typeof disconnect === "function") disconnect();
    store.reset();
    router.push({ name: "home" });
  }

  return { leaveRoom };
}
