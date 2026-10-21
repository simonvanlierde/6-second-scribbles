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
  // A client clock running behind the server's makes elapsed negative: that is no time used yet.
  const elapsed = Math.max(0, Math.floor((Date.now() - startTime) / 1000));
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

  let interval: number | undefined;
  function stop() {
    clearInterval(interval);
    interval = undefined;
  }
  function start() {
    stop();
    interval = window.setInterval(refresh, 1000);
  }
  // Outside a component (as in unit tests) nothing disposes the timer.
  if (getCurrentScope()) onScopeDispose(stop);

  start();
  refresh();

  watch(
    () => [toValue(startTime), toValue(duration)] as const,
    () => {
      expired = false;
      start();
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
