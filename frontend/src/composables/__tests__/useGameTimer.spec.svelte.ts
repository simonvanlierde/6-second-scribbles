import { flushSync, tick as nextTick } from "svelte";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useAnnouncer } from "@/composables/useAnnouncer.svelte";
import { useGameTimer } from "@/composables/useGameTimer.svelte";

const disposers: Array<() => void> = [];
function timer(options: Parameters<typeof useGameTimer>[0]) {
  let result!: ReturnType<typeof useGameTimer>;
  const dispose = $effect.root(() => {
    result = useGameTimer(options);
  });
  disposers.push(dispose);
  flushSync();
  return result;
}
describe("useGameTimer", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-01-01T00:00:00.000Z"));
  });

  afterEach(() => {
    for (const dispose of disposers.splice(0)) dispose();
    vi.useRealTimers();
  });

  it("starts from the full duration when no start time is available", () => {
    const clock = timer({
      startTime: () => null,
      duration: () => 30,
    });

    expect(clock.timeLeft).toBe(30);
    expect(clock.isWarning).toBe(false);
  });

  it("counts down from the server start time", () => {
    const start = Date.now() - 5_000;
    const clock = timer({
      startTime: () => start,
      duration: () => 12,
      warningThreshold: 7,
    });

    expect(clock.timeLeft).toBe(7);
    expect(clock.isWarning).toBe(true);
  });

  it("expires once and refreshes when the start time changes", async () => {
    let startTime = $state(Date.now());
    const onExpire = vi.fn();
    const clock = timer({
      startTime: () => startTime,
      duration: () => 2,
      onExpire,
    });

    expect(clock.timeLeft).toBe(2);

    vi.advanceTimersByTime(2_000);

    expect(clock.timeLeft).toBe(0);
    expect(onExpire).toHaveBeenCalledTimes(1);

    startTime = Date.now();
    await nextTick();

    expect(clock.timeLeft).toBe(2);

    vi.advanceTimersByTime(2_000);

    expect(clock.timeLeft).toBe(0);
    expect(onExpire).toHaveBeenCalledTimes(2);
  });

  it("gives the full time when the client clock is slightly behind the server's start time", () => {
    const onExpire = vi.fn();
    const clock = timer({ startTime: Date.now() + 1, duration: 30, onExpire });

    expect(clock.timeLeft).toBe(30);
    expect(onExpire).not.toHaveBeenCalled();
  });

  it("stops ticking once the screen that owns it goes away", () => {
    const onExpire = vi.fn();
    const clock = timer({ startTime: Date.now(), duration: 2, onExpire });

    vi.advanceTimersByTime(1_000);
    expect(clock.timeLeft).toBe(1);

    disposers.pop()?.();
    vi.advanceTimersByTime(5_000);

    expect(clock.timeLeft).toBe(1);
    expect(onExpire).not.toHaveBeenCalled();
  });

  it("tells screen readers once when time is running low, not every second", async () => {
    const announcer = useAnnouncer();
    announcer.message = "";
    timer({ startTime: Date.now(), duration: 12 });

    vi.advanceTimersByTime(1_000);
    await nextTick();
    expect(announcer.message).toBe("");

    vi.advanceTimersByTime(1_000);
    await nextTick();
    await nextTick();
    expect(announcer.message).toBe("10 seconds left");

    announcer.message = "";
    vi.advanceTimersByTime(3_000);
    await nextTick();
    await nextTick();
    expect(announcer.message).toBe("");
  });

  it("stays quiet when a reconnect finds the time already up", async () => {
    const announcer = useAnnouncer();
    announcer.message = "";
    let startTime = $state(Date.now());
    const clock = timer({ startTime: () => startTime, duration: 30 });

    startTime = Date.now() - 60_000;
    await nextTick();
    await nextTick();

    expect(clock.isWarning).toBe(true);
    expect(announcer.message).toBe("");
  });
});
