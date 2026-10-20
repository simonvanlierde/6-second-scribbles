import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import LeaveRoomDialog from "@/components/LeaveRoomDialog.vue";
import HdDialog from "@/components/ui/HdDialog.vue";
import { useGameStore } from "@/stores/game";

const leaveRoomMock = vi.fn();

vi.mock("@/composables/useLeaveRoom", () => ({
  useLeaveRoom: () => ({ leaveRoom: leaveRoomMock }),
}));

describe("LeaveRoomDialog", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    leaveRoomMock.mockReset();
  });

  it("asks before a player leaves mid-round, and leaves on confirm", async () => {
    useGameStore().gamePhase = "drawing";
    const wrapper = mount(LeaveRoomDialog, { global: { stubs: { HdDialog: true } } });

    wrapper.vm.request();
    await wrapper.vm.$nextTick();

    const dialog = wrapper.findComponent(HdDialog);
    expect(dialog.props("open")).toBe(true);
    expect(leaveRoomMock).not.toHaveBeenCalled();

    dialog.vm.$emit("confirm");
    expect(leaveRoomMock).toHaveBeenCalledTimes(1);
  });

  it("leaves at once when there is nothing to lose", () => {
    const wrapper = mount(LeaveRoomDialog, { global: { stubs: { HdDialog: true } } });

    wrapper.vm.request();

    expect(wrapper.findComponent(HdDialog).props("open")).toBe(false);
    expect(leaveRoomMock).toHaveBeenCalledTimes(1);
  });
});
