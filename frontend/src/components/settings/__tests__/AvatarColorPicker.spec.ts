import { fireEvent, render } from "@testing-library/svelte";
import { describe, expect, it, vi } from "vitest";

import AvatarColorPicker from "@/components/settings/AvatarColorPicker.svelte";
import { AVATAR_COLORS } from "@/composables/useAvatar";

describe("AvatarColorPicker", () => {
  it("renders one selectable button per avatar color", () => {
    const onmodelValueChange = vi.fn();
    const w = render(AvatarColorPicker, {
      props: { modelValue: AVATAR_COLORS[0], initial: "S", onmodelValueChange },
    });
    expect(Array.from(w.container.querySelectorAll("button"))).toHaveLength(AVATAR_COLORS.length);
  });

  it("emits update:modelValue with the chosen color when clicked", async () => {
    const onmodelValueChange = vi.fn();
    const w = render(AvatarColorPicker, {
      props: { modelValue: AVATAR_COLORS[0], initial: "S", onmodelValueChange },
    });
    await fireEvent.click(Array.from(w.container.querySelectorAll("button"))[2]!);
    expect(onmodelValueChange).toHaveBeenCalledWith(AVATAR_COLORS[2]);
  });

  it("marks the current modelValue as active via aria-checked", () => {
    const _onmodelValueChange = vi.fn();
    const w = render(AvatarColorPicker, {
      props: { modelValue: AVATAR_COLORS[3], initial: "S" },
    });
    const btns = Array.from(w.container.querySelectorAll("button"));
    expect(btns[3]?.getAttribute("aria-checked")).toBe("true");
    expect(btns[0]?.getAttribute("aria-checked")).toBe("false");
  });
});
