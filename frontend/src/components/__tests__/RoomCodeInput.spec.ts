import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import RoomCodeInput from "@/components/RoomCodeInput.vue";
import LobbyView from "@/views/LobbyView.vue";

const pushMock = vi.fn();
const connectMock = vi.fn();
const storeMock = {
  localPlayerName: "",
  setLocalPlayer: vi.fn(),
  setRoomCode: vi.fn(),
  setLocalPlayerAndSave: vi.fn(),
  setRoomCodeAndSave: vi.fn(),
};

vi.mock("vue-router", () => ({ useRouter: () => ({ push: pushMock }) }));
vi.mock("@/composables/useGameConnection", () => ({
  useGameConnection: () => ({ connect: connectMock }),
}));
vi.mock("@/stores/game", () => ({ useGameStore: () => storeMock }));

beforeEach(() => {
  pushMock.mockClear();
  connectMock.mockClear();
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

describe("LobbyView", () => {
  it("create room triggers navigation", async () => {
    const wrapper = mount(LobbyView);
    await wrapper.find("#player-name").setValue("Test Player");
    await wrapper.find(".btn.btn-primary").trigger("click");
    expect(pushMock).toHaveBeenCalled();
  });
});
