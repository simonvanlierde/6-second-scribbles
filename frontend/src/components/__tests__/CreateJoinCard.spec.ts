import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { reactive } from "vue";

import CreateJoinCard from "@/components/CreateJoinCard.vue";

const pushMock = vi.fn();
const connectMock = vi.fn();
const storeMock = reactive({
  localPlayerName: "",
  roomCode: "",
  setLocalPlayer: vi.fn(),
  setRoomCode: vi.fn(),
  setLocalPlayerAndSave: vi.fn(),
  setRoomCodeAndSave: vi.fn(),
});

vi.mock("vue-router", () => ({ useRouter: () => ({ push: pushMock }) }));
vi.mock("@/composables/notifications", () => ({
  showNotification: vi.fn(),
}));
vi.mock("@/composables/useGameConnection", () => ({
  useGameConnection: () => ({ connect: connectMock }),
}));
vi.mock("@/stores/game", () => ({ useGameStore: () => storeMock }));

describe("CreateJoinCard", () => {
  beforeEach(() => {
    pushMock.mockClear();
    connectMock.mockClear();
    storeMock.localPlayerName = "";
    storeMock.roomCode = "";
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
    vi.stubGlobal("fetch", vi.fn());
  });

  it("renders the random room action as a full-width secondary CTA", () => {
    const wrapper = mount(CreateJoinCard, {
      global: {
        mocks: {
          $t: (key: string) => key,
        },
        stubs: {
          RoomCodeInput: {
            template: '<div data-testid="room-code-input" />',
          },
        },
      },
    });

    const randomButton = wrapper.get('[data-testid="join-random-room-button"]');

    expect(randomButton.classes()).toContain("w-full");
    expect(randomButton.classes()).toContain("rounded-[20px]");
    expect(randomButton.text()).toContain("home.joinRandomRoom");
  });

  it("opens the name prompt when creating a room without a saved name", async () => {
    const wrapper = mount(CreateJoinCard, {
      global: {
        mocks: {
          $t: (key: string) => key,
        },
        stubs: {
          RoomCodeInput: {
            template: '<div data-testid="room-code-input" />',
          },
        },
      },
    });

    const createButton = wrapper.findAll("button").find((button) => button.text().includes("home.createRoom"));
    await createButton?.trigger("click");

    expect(wrapper.getComponent({ name: "NamePromptDialog" }).props("open")).toBe(true);
  });
});
