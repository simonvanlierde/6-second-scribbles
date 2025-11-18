// Small logging helpers for server-side formatted fields
export function safeIso(timestamp: unknown, fallback = '<unknown>'): string {
  if (typeof timestamp === 'number' && Number.isFinite(timestamp)) {
    try {
      return new Date(timestamp).toISOString()
    } catch {
      return fallback
    }
  }
  return fallback
}

export function normalizeActivity(timestamp: unknown, now = Date.now()): number {
  if (typeof timestamp === 'number' && Number.isFinite(timestamp)) return timestamp
  return now
}

export default { safeIso, normalizeActivity }
