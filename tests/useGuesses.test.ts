import { beforeEach, describe, expect, it } from 'vitest'

import { useGuesses } from '../src/composables/useGuesses'

describe('useGuesses', () => {
  let result: ReturnType<typeof useGuesses>

  beforeEach(() => {
    result = useGuesses(['p1', 'p2'])
  })

  it('initializes guess arrays for players', () => {
    const { playerGuesses } = result
    expect(Array.isArray(playerGuesses.value['p1'])).toBe(true)
    expect(playerGuesses.value['p1'].length).toBe(10)
  })

  it('submitGuesses returns null when no non-empty guesses', () => {
    const { submitGuesses } = result
    const res = submitGuesses('p1')
    expect(res).toEqual([])
  })

  it('submitGuesses filters out empty guesses and marks submittedPlayers', () => {
    const { playerGuesses, submitGuesses, submittedPlayers } = result
    playerGuesses.value['p1'][0] = 'cat'
    playerGuesses.value['p1'][1] = 'dog'
    const filtered = submitGuesses('p1')
    expect(filtered).toEqual(['cat', 'dog'])
    expect(submittedPlayers.value.has('p1')).toBe(true)
  })

  it('repeated submissions for same player simply keeps them marked submitted', () => {
    const { playerGuesses, submitGuesses, submittedPlayers } = result
    playerGuesses.value['p1'][0] = 'bird'
    const first = submitGuesses('p1')
    expect(first).toEqual(['bird'])
    const second = submitGuesses('p1')
    // second still returns filtered guesses (idempotent with current impl)
    expect(second).toEqual(['bird'])
    expect(submittedPlayers.value.has('p1')).toBe(true)
  })
})
