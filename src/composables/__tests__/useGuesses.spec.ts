import { describe, expect, it } from 'vitest'

import { useGuesses } from '../useGuesses'

describe('useGuesses', () => {
  it('allows empty submission: returns [] and marks submitted player', () => {
    const playerIds = ['p1']
    const { playerGuesses, submittedPlayers, init, submitGuesses } = useGuesses(playerIds)
    init()
    // ensure all inputs empty
    playerGuesses.value['p1'] = Array(10).fill('')
    const res = submitGuesses('p1')
    expect(Array.isArray(res)).toBe(true)
    expect(res!.length).toBe(0)
    expect(submittedPlayers.value.has('p1')).toBe(true)
  })

  it('marks submitted when guesses provided but none match canonical answers', () => {
    const playerIds = ['p2']
    const answers = { p2: ['apple', 'banana'] }
    const { playerGuesses, submittedPlayers, init, submitGuesses } = useGuesses(playerIds, answers)
    init()
    playerGuesses.value['p2'] = ['xyz', '', '', '', '', '', '', '', '', '']
    const res = submitGuesses('p2')
    // filtered non-empty but fuzzy matching removes them -> accepted is []
    expect(Array.isArray(res)).toBe(true)
    expect(res!.length).toBe(0)
    expect(submittedPlayers.value.has('p2')).toBe(true)
  })

  it('returns accepted matches when guesses match canonical answers', () => {
    const playerIds = ['p3']
    const answers = { p3: ['cat'] }
    const { playerGuesses, submittedPlayers, init, submitGuesses } = useGuesses(playerIds, answers)
    init()
    playerGuesses.value['p3'] = ['cat', '', '', '', '', '', '', '', '', '']
    const res = submitGuesses('p3')
    expect(res).toEqual(['cat'])
    expect(submittedPlayers.value.has('p3')).toBe(true)
  })
})
