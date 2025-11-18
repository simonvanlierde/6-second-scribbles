import { describe, expect, it } from 'vitest'

import { normalizeActivity, safeIso } from '../src/server/logging'

describe('server logging helpers', () => {
  it('safeIso returns ISO for valid timestamps', () => {
    const ts = Date.now()
    const iso = safeIso(ts)
    expect(typeof iso).toBe('string')
    expect(iso).toContain('T')
  })

  it('safeIso returns fallback for invalid timestamp', () => {
    expect(safeIso(undefined)).toBe('<unknown>')
    expect(safeIso(null)).toBe('<unknown>')
    expect(safeIso(NaN)).toBe('<unknown>')
  })

  it('normalizeActivity returns numeric timestamp when valid', () => {
    const now = Date.now()
    expect(normalizeActivity(now, now + 100)).toBe(now)
  })

  it('normalizeActivity falls back to now when invalid', () => {
    const now = Date.now()
    expect(normalizeActivity(undefined, now)).toBe(now)
    expect(normalizeActivity(NaN, now)).toBe(now)
  })
})
