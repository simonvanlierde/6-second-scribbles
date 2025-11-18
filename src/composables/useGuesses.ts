import { ref } from 'vue'

import { matchesAny } from '@/utils/fuzzy'

type AnswersMap = Record<string, string[]>

export function useGuesses(playerIds: string[], answers?: AnswersMap) {
  const playerGuesses = ref<Record<string, string[]>>({})
  const submittedPlayers = ref<Set<string>>(new Set())

  function init() {
    submittedPlayers.value = new Set()
    playerIds.forEach((id) => {
      playerGuesses.value[id] = Array(10).fill('')
    })
  }

  function submitGuesses(targetPlayerId: string) {
    const guesses = playerGuesses.value[targetPlayerId] || []
    const filtered = guesses.map((g) => g.trim()).filter((g) => g !== '')
    // Allow submitting zero guesses: user can choose to submit an empty list.
    // We'll treat empty submission as an explicit submit (return an empty array),
    // so the caller will still mark the player as submitted and notify the server.

    // If we have canonical answers for this target, apply fuzzy matching
    const canonical = answers?.[targetPlayerId]
    let accepted = filtered
    if (canonical && canonical.length > 0) {
      accepted = filtered.filter((g) => matchesAny(g, canonical, { minScore: 0.75 }))
    }

    // accepted may be empty (no matches or user submitted nothing); still count as submitted
    submittedPlayers.value = new Set([...submittedPlayers.value, targetPlayerId])
    return accepted
  }

  init()

  return { playerGuesses, submittedPlayers, init, submitGuesses }
}

export default useGuesses
