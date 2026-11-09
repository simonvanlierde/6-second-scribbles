import { fireEvent, render } from "@testing-library/svelte";
import { tick } from "svelte";
import { beforeEach, describe, expect, it, vi } from "vitest";
import LeaveRoomDialog from "@/components/LeaveRoomDialog.svelte";
import { useGameStore } from "@/stores/game.svelte";

const leaveRoomMock = vi.fn();
vi.mock("@/composables/useLeaveRoom", () => ({ useLeaveRoom: () => ({ leaveRoom: leaveRoomMock }) }));

describe("LeaveRoomDialog", () => {
  beforeEach(() => {
    useGameStore().reset();
    useGameStore().setLocalPlayer("", "");
    leaveRoomMock.mockReset();
    HTMLDialogElement.prototype.showModal = vi.fn(function (this: HTMLDialogElement) {
      this.open = true;
    });
    HTMLDialogElement.prototype.close = vi.fn(function (this: HTMLDialogElement) {
      this.open = false;
    });
  });
  it("asks before a player leaves mid-round, and leaves on confirm", async () => {
    useGameStore().gamePhase = "drawing";
    const { component, container } = render(LeaveRoomDialog);
    component.request();
    await tick();
    expect(HTMLDialogElement.prototype.showModal).toHaveBeenCalled();
    expect(leaveRoomMock).not.toHaveBeenCalled();
    await fireEvent.click(container.querySelector('[data-testid="hd-dialog-confirm"]')!);
    expect(leaveRoomMock).toHaveBeenCalledTimes(1);
  });
  it("stays in the room when the player cancels", async () => {
    useGameStore().gamePhase = "guessing";
    const { component, container } = render(LeaveRoomDialog);
    component.request();
    await tick();
    await fireEvent.click(container.querySelector('[data-testid="hd-dialog-cancel"]')!);
    expect(HTMLDialogElement.prototype.close).toHaveBeenCalled();
    expect(leaveRoomMock).not.toHaveBeenCalled();
  });
  it("leaves at once when there is nothing to lose", () => {
    const { component } = render(LeaveRoomDialog);
    component.request();
    expect(HTMLDialogElement.prototype.showModal).not.toHaveBeenCalled();
    expect(leaveRoomMock).toHaveBeenCalledTimes(1);
  });
});
