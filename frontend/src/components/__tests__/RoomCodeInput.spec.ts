import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { reactive } from "vue";

import RoomCodeInput from "@/components/RoomCodeInput.vue";
import HomeView from "@/views/HomeView.vue";

const pushMock = vi.fn();
const connectMock = vi.fn();
const storeMock = reactive({
  localPlayerName: "",
  localPlayerLocale: "en",
  roomCode: "",
  setLocalPlayer: vi.fn((_id: string, name: string) => {
    storeMock.localPlayerName = name;
  }),
  setRoomCode: vi.fn((roomCode: string) => {
    storeMock.roomCode = roomCode;
  }),
  setLocalPlayerAndSave: vi.fn((_id: string, name: string) => {
    storeMock.localPlayerName = name;
  }),
  setRoomCodeAndSave: vi.fn((roomCode: string) => {
    storeMock.roomCode = roomCode;
  }),
  setLocalPlayerLocale: vi.fn((locale: string) => {
    storeMock.localPlayerLocale = locale;
  }),
});
const fetchMock = vi.fn();
const showNotificationMock = vi.fn();

vi.mock("vue-router", () => ({ useRouter: () => ({ push: pushMock }) }));
vi.mock("@/composables/notifications", () => ({
  showNotification: (...args: unknown[]) => showNotificationMock(...args),
  useNotifications: () => ({ notifications: [], showNotification: showNotificationMock }),
}));
vi.mock("@/composables/useGameConnection", () => ({
  useGameConnection: () => ({ connect: connectMock }),
}));
vi.mock("@/shared/roomCode", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/shared/roomCode")>();
  return {
    ...actual,
    // spell-checker: ignore NEWRM1
    generateRoomCode: () => "NEWRM1",
  };
});
vi.mock("@/stores/game", () => ({ useGameStore: () => storeMock }));

beforeEach(() => {
  pushMock.mockClear();
  connectMock.mockClear();
  showNotificationMock.mockClear();
  fetchMock.mockReset();
  if (!HTMLDialogElement.prototype.showModal) {
    HTMLDialogElement.prototype.showModal = vi.fn();
  } else {
    HTMLDialogElement.prototype.showModal = vi.fn();
  }
  if (!HTMLDialogElement.prototype.close) {
    HTMLDialogElement.prototype.close = vi.fn();
  } else {
    HTMLDialogElement.prototype.close = vi.fn();
  }
  vi.stubGlobal(
    "fetch",
    fetchMock.mockResolvedValue({
      json: async () => ({ exists: true, players: 2, game_phase: "lobby" }),
    } as Response),
  );
});

function mountInput(modelValue = "") {
  return mount(RoomCodeInput, { props: { modelValue } });
}

/** Retrieve the nth input wrapper, throwing a clear error if absent. */
function getInput(wrapper: ReturnType<typeof mountInput>, index: number) {
  const el = wrapper.findAll("input.code-input")[index];
  if (!el) throw new Error(`No input at index ${index}`);
  return el;
}

/** Get the last emitted value for update:modelValue, throwing if none emitted. */
function lastEmittedValue(wrapper: ReturnType<typeof mountInput>): string {
  const emitted = wrapper.emitted("update:modelValue");
  if (!emitted || emitted.length === 0) throw new Error("No update:modelValue emitted");
  const last = emitted[emitted.length - 1];
  if (!last) throw new Error("Emitted entry is empty");
  return last[0] as string;
}

describe("RoomCodeInput", () => {
  it("renders 6 individual character inputs", () => {
    const wrapper = mountInput();
    expect(wrapper.findAll("input.code-input")).toHaveLength(6);
  });

  it("fills inputs on paste and uppercases the value", async () => {
    const wrapper = mountInput();
    const clipboard = new DataTransfer();
    clipboard.setData("text", " ab 12c ");
    await getInput(wrapper, 0).trigger("paste", { clipboardData: clipboard });
    await wrapper.vm.$nextTick();

    expect(lastEmittedValue(wrapper)).toBe("AB12C");
  });

  it("uppercases a typed letter and emits the updated model", async () => {
    const wrapper = mountInput();
    await getInput(wrapper, 0).setValue("a");
    await getInput(wrapper, 1).setValue("x");
    await wrapper.vm.$nextTick();

    expect(lastEmittedValue(wrapper)[1]).toBe("X");
  });

  it("backspace on a filled cell clears it", async () => {
    const wrapper = mountInput();
    await getInput(wrapper, 0).setValue("a");
    await getInput(wrapper, 1).setValue("b");
    await getInput(wrapper, 1).trigger("keydown", { key: "Backspace" });
    await wrapper.vm.$nextTick();

    expect(lastEmittedValue(wrapper)).toBe("A");
  });

  it("arrow keys do not throw", async () => {
    const wrapper = mountInput();
    await expect(getInput(wrapper, 1).trigger("keydown", { key: "ArrowLeft" })).resolves.not.toThrow();
    await expect(getInput(wrapper, 0).trigger("keydown", { key: "ArrowRight" })).resolves.not.toThrow();
  });
});

describe("CreateJoinCard (via HomeView)", () => {
  it("shows the saved player name in the compact chip", async () => {
    storeMock.localPlayerName = "Persistent Player";
    const wrapper = mount(HomeView);

    await wrapper.get('[data-testid="home-player-preferences-toggle"]').trigger("click");
    expect(wrapper.get('[data-testid="player-name-chip"]').text()).toContain("Persistent Player");
  });

  it("prompts for a name when creating a room without a saved name", async () => {
    const wrapper = mount(HomeView);

    const createButton = wrapper.findAll("button").find((button) => button.text().match(/create room/i));
    await createButton?.trigger("click");

    expect(wrapper.find('[data-testid="name-prompt-input"]').exists()).toBe(true);
  });

  it("shows a toast when the room does not exist", async () => {
    storeMock.localPlayerName = "Persistent Player";
    // First call: locale availability fetch performed by CreateJoinCard on mount.
    fetchMock.mockResolvedValueOnce({ json: async () => [] } as Response);
    // Second call: room status check should return `exists: false`.
    fetchMock.mockResolvedValueOnce({ json: async () => ({ exists: false }) } as Response);

    const wrapper = mount(HomeView);

    const codeInputs = wrapper.findAll("input.code-input");
    const code = "ABC123";
    for (let index = 0; index < code.length; index += 1) {
      await codeInputs[index]?.setValue(code[index] ?? "");
    }

    await wrapper.find("button.bg-success").trigger("click");
    await wrapper.vm.$nextTick();

    expect(showNotificationMock).toHaveBeenCalledWith(expect.stringContaining("doesn't exist"), "error");
    expect(connectMock).not.toHaveBeenCalled();
    expect(pushMock).not.toHaveBeenCalled();
  });
});
