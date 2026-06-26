import { reactive, readonly } from "vue";

export type NotificationType = "info" | "success" | "error";

type Notification = { id: number; text: string; type: NotificationType };

const state = reactive({ notifications: [] as Notification[] });
let nextId = 1;

export function showNotification(text: string, type: NotificationType = "info", duration = 3000) {
  const id = nextId++;
  state.notifications.push({ id, text, type });
  setTimeout(() => {
    const idx = state.notifications.findIndex((n) => n.id === id);
    if (idx >= 0) state.notifications.splice(idx, 1);
  }, duration);
}

export function useNotifications() {
  return {
    notifications: readonly(state.notifications),
    showNotification,
  };
}
