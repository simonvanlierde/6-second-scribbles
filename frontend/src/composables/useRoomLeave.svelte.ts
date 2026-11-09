import { t } from "@/i18n";
import { useGameStore } from "@/stores/game.svelte";

type LeaveDialogConfig = {
  title: string;
  message: string;
  confirmLabel: string;
  cancelLabel: string;
};

export function useRoomLeave() {
  const store = useGameStore();

  let shouldConfirm = $derived.by(() => {
    if (store.gamePhase === "drawing" || store.gamePhase === "guessing") return true;
    return store.isHost && store.playersList.length > 1;
  });

  let dialog = $derived.by<LeaveDialogConfig>(() => {
    if (store.gamePhase === "drawing") {
      return {
        title: t("leaveDialog.drawingTitle"),
        message: t("leaveDialog.drawingMessage"),
        confirmLabel: t("leaveDialog.leave"),
        cancelLabel: t("leaveDialog.stay"),
      };
    }

    if (store.gamePhase === "guessing") {
      return {
        title: t("leaveDialog.guessingTitle"),
        message: t("leaveDialog.guessingMessage"),
        confirmLabel: t("leaveDialog.leave"),
        cancelLabel: t("leaveDialog.stay"),
      };
    }

    if (store.isHost && store.playersList.length > 1) {
      return {
        title: t("leaveDialog.hostTitle"),
        message: t("leaveDialog.hostMessage"),
        confirmLabel: t("leaveDialog.leaveRoom"),
        cancelLabel: t("leaveDialog.stay"),
      };
    }

    return {
      title: t("leaveDialog.defaultTitle"),
      message: "",
      confirmLabel: t("leaveDialog.leave"),
      cancelLabel: t("leaveDialog.cancel"),
    };
  });

  return {
    get shouldConfirm() {
      return shouldConfirm;
    },
    get dialog() {
      return dialog;
    },
  };
}
