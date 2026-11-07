import { fireEvent, render } from "@testing-library/svelte";
import { describe, expect, it, vi } from "vitest";

import SettingsPanel from "@/components/settings/SettingsPanel.svelte";
import { useSettingsPanel } from "@/composables/useSettingsPanel.svelte";
import { useGameStore } from "@/stores/game.svelte";

vi.mock("@/composables/useLocaleAvailability.svelte", () => ({
  useLocaleAvailability: () => ({
    localeOptions: [],
    fetchLocaleAvailability: vi.fn(),
  }),
}));

function mountPanel(initialState: Record<string, unknown> = {}) {
  const store = useGameStore();
  store.reset();
  store.setLocalPlayer("", "");
  Object.assign(store, { localPlayerName: "", localPlayerColor: "var(--avatar-1)", ...initialState });
  HTMLDialogElement.prototype.showModal = vi.fn(function (this: HTMLDialogElement) {
    this.open = true;
  });
  HTMLDialogElement.prototype.close = vi.fn(function (this: HTMLDialogElement) {
    this.open = false;
  });
  return render(SettingsPanel, { props: { open: true } });
}

describe("SettingsPanel", () => {
  it("shows the current player name in the name input", () => {
    const w = mountPanel({ localPlayerName: "Simon" });
    // The aria-label resolves through i18n, which may render as a key in the
    // isolated test context — find the name input by reference to the avatar
    // picker it sits next to instead.
    const input = Array.from(w.container.querySelectorAll("input[type='text']")).find((i) => i.tagName === "INPUT");
    expect(input).toBeTruthy();
    expect((input as HTMLInputElement | undefined)?.value).toBe("Simon");
  });

  it("renders three theme options in the appearance segmented control", () => {
    const w = mountPanel();
    const seg = w.container.querySelector(".seg")!;
    expect(seg !== null).toBe(true);
    expect(seg.querySelectorAll(".seg__btn")).toHaveLength(3);
  });

  it("reveals an avatar color picker with 6 swatches when the avatar is clicked", async () => {
    const w = mountPanel({ localPlayerName: "Simon" });
    // The picker is collapsed by default; clicking the avatar button expands it.
    expect(w.container.querySelector('[role="radiogroup"][aria-label="Avatar color"]')! !== null).toBe(false);
    await fireEvent.click(w.container.querySelector(".avatar-btn")!);
    const picker = w.container.querySelector('[role="radiogroup"][aria-label="Avatar color"]')!;
    expect(picker !== null).toBe(true);
    expect(picker.querySelectorAll("button")).toHaveLength(6);
  });

  it("renders a sound toggle", () => {
    const w = mountPanel();
    const soundToggle = w.container.querySelector(".switch__input")!;
    expect(soundToggle !== null).toBe(true);
    expect((soundToggle as HTMLInputElement).type).toBe("checkbox");
  });

  it("is the shared dialog, and closing it resumes the action that asked for a name", async () => {
    const w = mountPanel({ localPlayerName: "Simon" });
    expect(w.container.querySelector("dialog")).not.toBeNull();
    expect(w.container.querySelector('[data-testid="hd-dialog-confirm"]')! !== null).toBe(false);
    const action = vi.fn();
    useSettingsPanel().pendingNameAction = action;

    await fireEvent.click(w.container.querySelector('[data-testid="hd-dialog-close"]')!);

    expect(action).toHaveBeenCalledTimes(1);
    expect(HTMLDialogElement.prototype.close).toHaveBeenCalled();
  });

  it("closes on Enter in the name field and resumes the action that asked for a name", async () => {
    const w = mountPanel({ localPlayerName: "Simon" });
    const action = vi.fn();
    useSettingsPanel().pendingNameAction = action;

    await fireEvent.keyUp(w.container.querySelector("input[type='text']")!, { key: "Enter" });

    expect(HTMLDialogElement.prototype.close).toHaveBeenCalled();
    expect(action).toHaveBeenCalledTimes(1);
  });
});
