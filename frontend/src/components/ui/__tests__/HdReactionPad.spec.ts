import { fireEvent, render } from "@testing-library/svelte";
import { beforeEach, describe, expect, it, vi } from "vitest";

import HdReactionPad from "@/components/ui/HdReactionPad.svelte";
import { REACTION_KEYS } from "@/composables/useReactions.svelte";

describe("HdReactionPad", () => {
  it("renders a button per reaction key", () => {
    const w = render(HdReactionPad, { props: { ...callbacks, name: "Ada" } });
    expect(Array.from(w.container.querySelectorAll("button"))).toHaveLength(REACTION_KEYS.length);
  });

  it("emits 'react' with the key when a button is clicked", async () => {
    const w = render(HdReactionPad, { props: { ...callbacks, name: "Ada" } });
    const buttons = Array.from(w.container.querySelectorAll("button"));
    const firstButton = buttons[0];
    if (!firstButton) throw new Error("expected at least one button");
    await fireEvent.click(firstButton);
    const emitted = events.react.mock.calls;
    expect(emitted).toBeTruthy();
    expect(emitted?.[0]).toEqual([REACTION_KEYS[0]]);
  });
});

const events = { react: vi.fn() };
const callbacks = { onreact: events.react };
beforeEach(() => {
  for (const event of Object.values(events)) event.mockClear();
});
