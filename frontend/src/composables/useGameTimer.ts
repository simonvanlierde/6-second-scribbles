import type { MaybeRefOrGetter } from "vue";
import { computed, getCurrentScope, onScopeDispose, ref, toValue, watch } from "vue";

import { useAnnouncer } from "@/composables/useAnnouncer";
import { i18n } from "@/i18n";

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
      stop();
      onExpire?.();
    }
  }

  const interval = window.setInterval(refresh, 1000);
  const stop = () => clearInterval(interval);
  // Outside a component (as in unit tests) nothing disposes the timer.
  if (getCurrentScope()) onScopeDispose(stop);

  refresh();

  watch(
    () => [toValue(startTime), toValue(duration)] as const,
    () => {
      expired = false;
      refresh();
    },
  );

  const isWarning = computed(() => timeLeft.value <= warningThreshold);

  // The visible countdown is hidden from screen readers (a tick a second is noise),
  // so say once that time is running low.
  const { announce } = useAnnouncer();
  watch(isWarning, (warning) => {
    if (warning && timeLeft.value > 0) announce(i18n.global.t("phase.timeLow", { count: timeLeft.value }));
  });

  return { timeLeft, isWarning };
}
