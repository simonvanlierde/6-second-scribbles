import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import HdReactionPad from "@/components/ui/HdReactionPad.vue";
import { REACTION_KEYS } from "@/composables/useReactions";

describe("HdReactionPad", () => {
  it("renders a button per reaction key", () => {
    const w = mount(HdReactionPad);
    expect(w.findAll("button")).toHaveLength(REACTION_KEYS.length);
  });

  it("emits 'react' with the key when a button is clicked", async () => {
    const w = mount(HdReactionPad);
    const buttons = w.findAll("button");
    const firstButton = buttons[0];
    if (!firstButton) throw new Error("expected at least one button");
    await firstButton.trigger("click");
    const emitted = w.emitted("react");
    expect(emitted).toBeTruthy();
    expect(emitted?.[0]).toEqual([REACTION_KEYS[0]]);
  });
});
