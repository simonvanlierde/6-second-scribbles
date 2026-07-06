import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import GameSettingsPanel from "@/components/GameSettingsPanel.vue";
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
});
