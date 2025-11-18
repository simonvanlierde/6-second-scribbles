import { describe, it, expect } from 'vitest'

import { cardDecks } from '@/shared/cardDecks'

import { matchesAny } from '../fuzzy'

type DeckItem = { category: string; items: string[] }

// pick a small sample of canonical answers
const animals = (cardDecks.easy as DeckItem[]).find((d) => d.category === 'Animals')!.items
const fruits = (cardDecks.easy as DeckItem[]).find((d) => d.category === 'Fruits')!.items

describe('fuzzy.matchesAny', () => {
  it('matches exact answers', () => {
    expect(matchesAny('cat', animals)).toBe(true)
    expect(matchesAny('banana', fruits)).toBe(true)
  })

  it('matches fuzzy answers (typos)', () => {
    expect(matchesAny('kat', animals, { minScore: 0.6 })).toBe(true)
    expect(matchesAny('bananna', fruits, { minScore: 0.6 })).toBe(true)
  })

  it('does not match very different strings', () => {
    expect(matchesAny('car', animals)).toBe(false)
    expect(matchesAny('not-a-fruit', fruits)).toBe(false)
  })

  it('is case-insensitive and ignores punctuation', () => {
    expect(matchesAny('CAT', animals)).toBe(true)
    expect(matchesAny('banana!', fruits)).toBe(true)
  })
})
