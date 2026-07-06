import { useIntervalFn } from "@vueuse/core";
import type { MaybeRefOrGetter } from "vue";
import { computed, ref, toValue, watch } from "vue";

interface UseGameTimerOptions {
  startTime: MaybeRefOrGetter<number | null | undefined>;
  duration: MaybeRefOrGetter<number>;
  onExpire?: () => void;
  warningThreshold?: number;
}

function computeTimeLeft(startTime: number | null | undefined, duration: number): number {
  if (!startTime || Number.isNaN(startTime)) return duration;
  const elapsed = Math.floor((Date.now() - startTime) / 1000);
  if (elapsed < 0 || elapsed > duration) return 0;
  return Math.max(0, duration - elapsed);
}

export function useGameTimer({ startTime, duration, onExpire, warningThreshold = 10 }: UseGameTimerOptions) {
  const timeLeft = ref(computeTimeLeft(toValue(startTime), toValue(duration)));
  let expired = false;

  function refresh() {
    timeLeft.value = computeTimeLeft(toValue(startTime), toValue(duration));
    if (timeLeft.value <= 0 && !expired) {
      expired = true;
      pause();
      onExpire?.();
    }
  }

  const { pause } = useIntervalFn(refresh, 1000, { immediate: true });

  function stop() {
    pause();
  }

  refresh();

  watch(
    () => [toValue(startTime), toValue(duration)] as const,
    () => {
      expired = false;
      refresh();
    },
  );

  const isWarning = computed(() => timeLeft.value <= warningThreshold);

  return { timeLeft, isWarning, stop };
}
