import Fuse from 'fuse.js'

export type FuseOptions = Partial<Fuse.IFuseOptions<any>> & {
  threshold?: number // override fuse's threshold
}

export function buildFuse(list: string[], opts?: FuseOptions) {
  const options: Fuse.IFuseOptions<string> = {
    keys: [],
    includeScore: true,
    shouldSort: true,
    threshold: opts?.threshold ?? 0.35, // smaller => stricter
  }
  return new Fuse(list, options)
}

export function matchesAny(guess: string, allowed: string[] | string, opts?: { minScore?: number }) {
  const arr = Array.isArray(allowed) ? allowed : [allowed]
  if (arr.length === 0) return false
  const fuse = buildFuse(arr, { threshold: 0.35 })
  const results = fuse.search(guess)
  if (results.length === 0) return false
  // fuse score: 0 = exact, 1 = no match; invert to similarity-like
  const best = results[0]!
  const score = 1 - (best.score ?? 1)
  const minScore = opts?.minScore ?? 0.7
  return score >= minScore
}

export default { buildFuse, matchesAny }
