import { reactive, readonly } from 'vue';

type Notification = { id: number; text: string }
const state = reactive({ notifications: [] as Notification[] })
let nextId = 1

export function showNotification(text: string, duration = 3000) {
  const id = nextId++
  state.notifications.push({ id, text })
  setTimeout(() => {
    const idx = state.notifications.findIndex(n => n.id === id)
    if (idx >= 0) state.notifications.splice(idx, 1)
  }, duration)
}

export function useNotifications() {
  return {
    notifications: readonly(state.notifications),
    showNotification,
  }
}
