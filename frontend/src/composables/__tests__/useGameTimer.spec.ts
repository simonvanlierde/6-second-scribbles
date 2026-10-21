import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { effectScope, nextTick, ref } from "vue";

import { useAnnouncer } from "@/composables/useAnnouncer";
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

    vi.advanceTimersByTime(2_000);

    expect(timeLeft.value).toBe(0);
    expect(onExpire).toHaveBeenCalledTimes(2);
  });

  it("gives the full time when the client clock is slightly behind the server's start time", () => {
    const onExpire = vi.fn();
    const { timeLeft } = useGameTimer({ startTime: Date.now() + 1, duration: 30, onExpire });

    expect(timeLeft.value).toBe(30);
    expect(onExpire).not.toHaveBeenCalled();
  });

  it("stops ticking once the screen that owns it goes away", () => {
    const onExpire = vi.fn();
    const scope = effectScope();
    const timer = scope.run(() => useGameTimer({ startTime: Date.now(), duration: 2, onExpire }));

    vi.advanceTimersByTime(1_000);
    expect(timer?.timeLeft.value).toBe(1);

    scope.stop();
    vi.advanceTimersByTime(5_000);

    expect(timer?.timeLeft.value).toBe(1);
    expect(onExpire).not.toHaveBeenCalled();
  });

  it("tells screen readers once when time is running low, not every second", async () => {
    const { message } = useAnnouncer();
    message.value = "";
    useGameTimer({ startTime: Date.now(), duration: 12 });

    vi.advanceTimersByTime(1_000);
    await nextTick();
    expect(message.value).toBe("");

    vi.advanceTimersByTime(1_000);
    await nextTick();
    await nextTick();
    expect(message.value).toBe("10 seconds left");

    message.value = "";
    vi.advanceTimersByTime(3_000);
    await nextTick();
    await nextTick();
    expect(message.value).toBe("");
  });

  it("stays quiet when a reconnect finds the time already up", async () => {
    const { message } = useAnnouncer();
    message.value = "";
    const startTime = ref(Date.now());
    const { isWarning } = useGameTimer({ startTime, duration: 30 });

    startTime.value = Date.now() - 60_000;
    await nextTick();
    await nextTick();

    expect(isWarning.value).toBe(true);
    expect(message.value).toBe("");
  });
});
