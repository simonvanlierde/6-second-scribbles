import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { nextTick, ref } from "vue";

import { useGameTimer } from "@/composables/useGameTimer";

describe("useGameTimer", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-01-01T00:00:00.000Z"));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("starts from the full duration when no start time is available", () => {
    const { timeLeft, isWarning } = useGameTimer({
      startTime: () => null,
      duration: () => 30,
    });

    expect(timeLeft.value).toBe(30);
    expect(isWarning.value).toBe(false);
  });

  it("counts down from the server start time", () => {
    const start = Date.now() - 5_000;
    const { timeLeft, isWarning } = useGameTimer({
      startTime: () => start,
      duration: () => 12,
      warningThreshold: 7,
    });

    expect(timeLeft.value).toBe(7);
    expect(isWarning.value).toBe(true);
  });

  it("expires once and refreshes when the start time changes", async () => {
    const startTime = ref(Date.now());
    const onExpire = vi.fn();
    const { timeLeft } = useGameTimer({
      startTime,
      duration: () => 2,
      onExpire,
    });

    expect(timeLeft.value).toBe(2);

    vi.advanceTimersByTime(2_000);

    expect(timeLeft.value).toBe(0);
    expect(onExpire).toHaveBeenCalledTimes(1);

    startTime.value = Date.now();
    await nextTick();

    expect(timeLeft.value).toBe(2);
  });
});
