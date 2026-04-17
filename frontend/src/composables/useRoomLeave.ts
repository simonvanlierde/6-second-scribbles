import { computed } from "vue";

import { useGameStore } from "@/stores/game";

type LeaveDialogConfig = {
  title: string;
  message: string;
  confirmLabel: string;
  cancelLabel: string;
};

type LeaveContext = {
  spectator?: boolean;
};

export function useRoomLeave(context: LeaveContext = {}) {
  const store = useGameStore();
  const spectator = context.spectator ?? false;

  const shouldConfirm = computed(() => {
    if (spectator) return false;
    if (store.gamePhase === "drawing" || store.gamePhase === "guessing") return true;
    return store.isHost && store.playersList.length > 1;
  });

  const dialog = computed<LeaveDialogConfig>(() => {
    if (store.gamePhase === "drawing") {
      return {
        title: "Leave Game?",
        message: "Your drawing progress will be lost and the round will continue without you.",
        confirmLabel: "Leave",
        cancelLabel: "Stay",
      };
    }

    if (store.gamePhase === "guessing") {
      return {
        title: "Leave Round?",
        message: "Your guesses will be lost and the round will continue without you.",
        confirmLabel: "Leave",
        cancelLabel: "Stay",
      };
    }

    if (store.isHost && store.playersList.length > 1) {
      return {
        title: "Leave Room?",
        message: "Host will pass to another player when you leave.",
        confirmLabel: "Leave room",
        cancelLabel: "Stay",
      };
    }

    return {
      title: "Leave Room?",
      message: "",
      confirmLabel: "Leave",
      cancelLabel: "Cancel",
    };
  });

  return {
    shouldConfirm,
    dialog,
  };
}
