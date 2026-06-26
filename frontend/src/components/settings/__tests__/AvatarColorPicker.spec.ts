import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import AvatarColorPicker from "@/components/settings/AvatarColorPicker.vue";
import { AVATAR_COLORS } from "@/composables/useAvatar";

describe("AvatarColorPicker", () => {
  it("renders one selectable button per avatar color", () => {
    const w = mount(AvatarColorPicker, {
      props: { modelValue: AVATAR_COLORS[0], initial: "S" },
    });
    expect(w.findAll("button")).toHaveLength(AVATAR_COLORS.length);
  });

  it("emits update:modelValue with the chosen color when clicked", async () => {
    const w = mount(AvatarColorPicker, {
      props: { modelValue: AVATAR_COLORS[0], initial: "S" },
    });
    await w.findAll("button")[2]?.trigger("click");
    expect(w.emitted("update:modelValue")?.[0]).toEqual([AVATAR_COLORS[2]]);
  });

  it("marks the current modelValue as active via aria-checked", () => {
    const w = mount(AvatarColorPicker, {
      props: { modelValue: AVATAR_COLORS[3], initial: "S" },
    });
    const btns = w.findAll("button");
    expect(btns[3]?.attributes("aria-checked")).toBe("true");
    expect(btns[0]?.attributes("aria-checked")).toBe("false");
  });
});
