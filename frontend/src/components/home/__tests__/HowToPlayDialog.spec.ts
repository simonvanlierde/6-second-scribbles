import { render } from "@testing-library/svelte";
import { describe, expect, it } from "vitest";

import HowToPlayDialog from "@/components/home/HowToPlayDialog.svelte";

describe("HowToPlayDialog", () => {
  it("renders the how-to steps when open", () => {
    const wrapper = render(HowToPlayDialog, {
      props: { open: true },
    });

    expect(wrapper.container.textContent!).toContain("How to Play");
    expect(Array.from(wrapper.container.querySelectorAll("li"))).toHaveLength(4);
  });
});
