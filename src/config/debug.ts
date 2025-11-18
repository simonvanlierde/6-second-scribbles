// DEBUG flag detection for Vite-based clients and Node-based servers.
// Client (Vite): set VITE_DEBUG="true" to enable debug logging in the browser.
// Server (Node): set DEBUG="true" or NODE_ENV not equal to 'production'.
export const DEBUG: boolean = (() => {
  // import.meta.env is available in the Vite client build; prefer that.
  try {
    const meta = import.meta as unknown
    const env = (meta as { env?: Record<string, unknown> } | undefined)?.env
    if (env && typeof env.VITE_DEBUG !== 'undefined') return String(env.VITE_DEBUG) === 'true'
    if (env && typeof env.MODE === 'string') return env.MODE === 'development'
  } catch {
    // ignore
  }

  // Fallback to Node process.env when available
  try {
    if (typeof process !== 'undefined') {
      const p = process as unknown as { env?: Record<string, string> }
      const penv = p.env
      if (penv) {
        if (typeof penv.DEBUG !== 'undefined') return String(penv.DEBUG) === 'true'
        if (penv.NODE_ENV) return penv.NODE_ENV !== 'production'
      }
    }
  } catch {
    // ignore
  }

  return false
})()
