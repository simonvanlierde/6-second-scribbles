import { untrack } from "svelte";
import { useAnnouncer } from "@/composables/useAnnouncer.svelte";
import { t } from "@/i18n";

type Input<T> = T | (() => T);
interface UseGameTimerOptions {
  startTime: Input<number | null | undefined>;
  duration: Input<number>;
  onExpire?: () => void;
  warningThreshold?: number;
}

function resolve<T>(input: Input<T>): T {
  return typeof input === "function" ? (input as () => T)() : input;
}

function computeTimeLeft(startTime: number | null | undefined, duration: number): number {
  if (!startTime || Number.isNaN(startTime)) return duration;
  const elapsed = Math.max(0, Math.floor((Date.now() - startTime) / 1000));
  return Math.max(0, duration - elapsed);
}

export function useGameTimer({ startTime, duration, onExpire, warningThreshold = 10 }: UseGameTimerOptions) {
  const initialTimeLeft = computeTimeLeft(resolve(startTime), resolve(duration));
  let timeLeft = $state(initialTimeLeft);
  let expired = false;
  let wasWarning = initialTimeLeft <= warningThreshold;
  let interval: number | undefined;
  const { announce } = useAnnouncer();

  function stop() {
    clearInterval(interval);
    interval = undefined;
  }
  function refresh() {
    timeLeft = computeTimeLeft(resolve(startTime), resolve(duration));
    const warning = timeLeft <= warningThreshold;
    if (warning && !wasWarning && timeLeft > 0) announce(t("phase.timeLow", { count: timeLeft }));
    wasWarning = warning;
    if (timeLeft <= 0 && !expired) {
      expired = true;
      stop();
      onExpire?.();
    }
  }
  // The owning screen disposes this effect, including its interval, on navigation.
  $effect.pre(() => {
    resolve(startTime);
    resolve(duration);
    untrack(() => {
      expired = false;
      interval = window.setInterval(refresh, 1000);
      refresh();
    });
    return stop;
  });

  return {
    get timeLeft() {
      return timeLeft;
    },
    get isWarning() {
      return timeLeft <= warningThreshold;
    },
  };
}
