import { fireEvent, render } from "@testing-library/svelte";
import { tick as nextTick } from "svelte";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import GameSettingsPanel from "@/components/GameSettingsPanel.svelte";
import { UI_TIMINGS } from "@/config/gameConfig";
import { useGameStore } from "@/stores/game.svelte";

const sendMock = vi.fn();
const fetchLocaleAvailabilityMock = vi.fn();
const localeOptions = {
  current: [
    { code: "en", label: "English", enabled: true },
    { code: "nl", label: "Nederlands", enabled: true },
  ],
};

vi.mock("@/composables/useGameConnection.svelte", () => ({
  useGameConnection: () => ({ send: sendMock }),
}));

vi.mock("@/composables/useLocaleAvailability.svelte", () => ({
  useLocaleAvailability: () => ({
    fetchLocaleAvailability: fetchLocaleAvailabilityMock,
    get localeOptions() {
      return localeOptions.current;
    },
  }),
}));

function mountPanel() {
  return render(GameSettingsPanel);
}

describe("GameSettingsPanel", () => {
  beforeEach(() => {
    useGameStore().reset();
    useGameStore().setLocalPlayer("", "");
    sendMock.mockReset();
    fetchLocaleAvailabilityMock.mockReset();
    localeOptions.current = [
      { code: "en", label: "English", enabled: true },
      { code: "nl", label: "Nederlands", enabled: true },
    ];
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders read-only chips for non-host players", () => {
    const store = useGameStore();
    store.setPlayers([
      { id: "p1", name: "Host" },
      { id: "p2", name: "Player" },
    ]);
    store.setHost("p1");
    store.localPlayerId = "p2";
    store.applySettingsUpdate({
      difficulty: "hard",
      rounds: 5,
      drawingTimeLimit: 70,
      guessingTimeLimit: 40,
    });

    const wrapper = mountPanel();

    expect(!!wrapper.container.querySelector(".settings--readonly")).toBe(true);
    expect(wrapper.container.textContent).toContain("hard");
    expect(wrapper.container.textContent).toContain("5 Rounds");
    expect(wrapper.container.textContent).toContain("70s");
    expect(wrapper.container.textContent).toContain("40s");
    expect(fetchLocaleAvailabilityMock).toHaveBeenCalledTimes(1);
  });

  it("renders host controls and expands advanced settings", async () => {
    const store = useGameStore();
    store.setPlayers([
      { id: "p1", name: "Host" },
      { id: "p2", name: "Player" },
    ]);
    store.setHost("p1");
    store.localPlayerId = "p1";

    const wrapper = mountPanel();

    expect(!!wrapper.container.querySelector(".settings--readonly")).toBe(false);
    expect(wrapper.container.textContent).toContain("Difficulty");
    expect(wrapper.container.querySelectorAll(".hd-seg__item")).toHaveLength(3);

    await fireEvent.click(wrapper.getByRole("button", { name: "Advanced Settings" }));

    expect(wrapper.container.textContent).toContain("Drawing time");
    expect(wrapper.container.textContent).toContain("Guessing time");
  });

  it("host broadcasts their playable locale as the room default", () => {
    const store = useGameStore();
    store.setPlayers([
      { id: "p1", name: "Host" },
      { id: "p2", name: "Player" },
    ]);
    store.setHost("p1");
    store.localPlayerId = "p1";
    store.setLocalPlayerLocale("nl");

    mountPanel();

    expect(sendMock).toHaveBeenCalledWith({
      type: "default_locale_update",
      locale: "nl",
    });
  });

  it("sends one settings update after the host stops clicking, not one per click", async () => {
    vi.useFakeTimers();
    const store = useGameStore();
    store.setPlayers([{ id: "p1", name: "Host" }]);
    store.setHost("p1");
    store.localPlayerId = "p1";
    const wrapper = mountPanel();
    sendMock.mockReset();

    const increase = wrapper.getByRole("button", { name: "Increase Rounds", exact: true });
    await fireEvent.click(increase);
    await fireEvent.click(increase);
    await fireEvent.click(increase);
    vi.advanceTimersByTime(299);

    expect(sendMock).not.toHaveBeenCalled();
    expect(store.maxRounds).toBe(8);

    vi.advanceTimersByTime(1);

    expect(sendMock).toHaveBeenCalledTimes(1);
    expect(sendMock).toHaveBeenCalledWith(expect.objectContaining({ type: "settings_update", rounds: 8 }));
  });

  it("flashes the read-only settings when the host changes them, then settles", async () => {
    vi.useFakeTimers();
    const store = useGameStore();
    store.setPlayers([
      { id: "p1", name: "Host" },
      { id: "p2", name: "Player" },
    ]);
    store.setHost("p1");
    store.localPlayerId = "p2";
    const wrapper = mountPanel();

    store.applySettingsUpdate({ rounds: 7 });
    await nextTick();

    expect(!!wrapper.container.querySelector(".settings-flash")).toBe(true);
    expect(wrapper.container.textContent).toContain("7 Rounds");

    vi.advanceTimersByTime(UI_TIMINGS.SETTINGS_FLASH_MS);
    await nextTick();

    expect(!!wrapper.container.querySelector(".settings-flash")).toBe(false);
    expect(sendMock).not.toHaveBeenCalledWith(expect.objectContaining({ type: "settings_update" }));
  });
});
