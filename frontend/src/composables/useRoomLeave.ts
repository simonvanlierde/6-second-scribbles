import { computed } from "vue";

import { i18n } from "@/i18n";
import { useGameStore } from "@/stores/game";

type LeaveDialogConfig = {
  title: string;
  message: string;
  confirmLabel: string;
  cancelLabel: string;
};

export function useRoomLeave() {
  const store = useGameStore();

  const shouldConfirm = computed(() => {
    if (store.gamePhase === "drawing" || store.gamePhase === "guessing") return true;
    return store.isHost && store.playersList.length > 1;
  });

  const dialog = computed<LeaveDialogConfig>(() => {
    if (store.gamePhase === "drawing") {
      return {
        title: i18n.global.t("leaveDialog.drawingTitle"),
        message: i18n.global.t("leaveDialog.drawingMessage"),
        confirmLabel: i18n.global.t("leaveDialog.leave"),
        cancelLabel: i18n.global.t("leaveDialog.stay"),
      };
    }

    if (store.gamePhase === "guessing") {
      return {
        title: i18n.global.t("leaveDialog.guessingTitle"),
        message: i18n.global.t("leaveDialog.guessingMessage"),
        confirmLabel: i18n.global.t("leaveDialog.leave"),
        cancelLabel: i18n.global.t("leaveDialog.stay"),
      };
    }

    if (store.isHost && store.playersList.length > 1) {
      return {
        title: i18n.global.t("leaveDialog.hostTitle"),
        message: i18n.global.t("leaveDialog.hostMessage"),
        confirmLabel: i18n.global.t("leaveDialog.leaveRoom"),
        cancelLabel: i18n.global.t("leaveDialog.stay"),
      };
    }

    return {
      title: i18n.global.t("leaveDialog.defaultTitle"),
      message: "",
      confirmLabel: i18n.global.t("leaveDialog.leave"),
      cancelLabel: i18n.global.t("leaveDialog.cancel"),
    };
  });

  return {
    shouldConfirm,
    dialog,
  };
}
