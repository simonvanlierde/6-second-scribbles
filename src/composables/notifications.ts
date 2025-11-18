import { reactive, readonly } from 'vue'

type Notification = { id: number; text: string; undo?: (() => void) | null }
const state = reactive({ notifications: [] as Notification[] })
let nextId = 1

export function showNotification(text: string, duration = 3000) {
  const id = nextId++
  state.notifications.push({ id, text })
  setTimeout(() => {
    const idx = state.notifications.findIndex((n) => n.id === id)
    if (idx >= 0) state.notifications.splice(idx, 1)
  }, duration)
}

export function showUndoNotification(text: string, undo: () => void, duration = 5000) {
  const id = nextId++
  state.notifications.push({ id, text, undo })
  setTimeout(() => {
    const idx = state.notifications.findIndex((n) => n.id === id)
    if (idx >= 0) state.notifications.splice(idx, 1)
  }, duration)
}

export function useNotifications() {
  return {
    notifications: readonly(state.notifications),
    showNotification,
    showUndoNotification,
  }
}

export function dismissNotification(id: number) {
  const idx = state.notifications.findIndex((n) => n.id === id)
  if (idx >= 0) state.notifications.splice(idx, 1)
}
