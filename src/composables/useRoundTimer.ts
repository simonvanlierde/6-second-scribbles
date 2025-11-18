import { ref } from 'vue'

export function useRoundTimer({
  roundLength,
  roundStartTime,
}: {
  roundLength: number
  roundStartTime?: number | null
}) {
  const timeLeft = ref(roundLength)
  let interval: number | null = null

  function computeInitial() {
    if (roundStartTime && !isNaN(roundStartTime)) {
      const elapsed = Math.floor((Date.now() - (roundStartTime as number)) / 1000)
      if (elapsed < 0) {
        // start time in the future: full round length remaining
        timeLeft.value = roundLength
      } else {
        // elapsed >= 0: clamp to 0..roundLength
        timeLeft.value = Math.max(0, roundLength - elapsed)
      }
    } else {
      timeLeft.value = roundLength
    }
  }

  function start() {
    stop()
    computeInitial()
    interval = window.setInterval(() => {
      if (roundStartTime && !isNaN(roundStartTime)) {
        const elapsed = Math.floor((Date.now() - (roundStartTime as number)) / 1000)
        if (elapsed < 0) {
          timeLeft.value = roundLength
        } else {
          timeLeft.value = Math.max(0, roundLength - elapsed)
        }
      } else {
        timeLeft.value = roundLength
      }
    }, 1000)
  }

  function stop() {
    if (interval) {
      clearInterval(interval)
      interval = null
    }
  }

  computeInitial()

  return { timeLeft, start, stop }
}

export default useRoundTimer
