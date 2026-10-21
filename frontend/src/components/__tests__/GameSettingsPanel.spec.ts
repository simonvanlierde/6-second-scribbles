import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import GameSettingsPanel from "@/components/GameSettingsPanel.vue";
import { UI_TIMINGS } from "@/config/gameConfig";
import { i18n } from "@/i18n";
import { useGameStore } from "@/stores/game";

const sendMock = vi.fn();
const fetchLocaleAvailabilityMock = vi.fn();
const localeOptions = ref([
  { code: "en", label: "English", enabled: true },
  { code: "nl", label: "Nederlands", enabled: true },
]);

vi.mock("@/composables/useGameConnection", () => ({
  useGameConnection: () => ({ send: sendMock }),
}));

vi.mock("@/composables/useLocaleAvailability", () => ({
  useLocaleAvailability: () => ({
    fetchLocaleAvailability: fetchLocaleAvailabilityMock,
    localeOptions,
  }),
}));

function mountPanel() {
  return mount(GameSettingsPanel, {
    global: {
      plugins: [i18n],
    },
  });
}

describe("GameSettingsPanel", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    sendMock.mockReset();
    fetchLocaleAvailabilityMock.mockReset();
    localeOptions.value = [
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

    expect(wrapper.find(".settings--readonly").exists()).toBe(true);
    expect(wrapper.text()).toContain("hard");
    expect(wrapper.text()).toContain("5 Rounds");
    expect(wrapper.text()).toContain("70s");
    expect(wrapper.text()).toContain("40s");
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

    expect(wrapper.find(".settings--readonly").exists()).toBe(false);
    expect(wrapper.text()).toContain("Difficulty");
    expect(wrapper.findAll(".hd-seg__item")).toHaveLength(3);

    await wrapper.find(".advanced-toggle").trigger("click");

    expect(wrapper.text()).toContain("Drawing time");
    expect(wrapper.text()).toContain("Guessing time");
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

    const increase = wrapper.get('button[aria-label="Increase Rounds"]');
    await increase.trigger("click");
    await increase.trigger("click");
    await increase.trigger("click");
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
    await wrapper.vm.$nextTick();

    expect(wrapper.find(".settings-flash").exists()).toBe(true);
    expect(wrapper.text()).toContain("7 Rounds");

    vi.advanceTimersByTime(UI_TIMINGS.SETTINGS_FLASH_MS);
    await wrapper.vm.$nextTick();

    expect(wrapper.find(".settings-flash").exists()).toBe(false);
    expect(sendMock).not.toHaveBeenCalledWith(expect.objectContaining({ type: "settings_update" }));
  });
});
