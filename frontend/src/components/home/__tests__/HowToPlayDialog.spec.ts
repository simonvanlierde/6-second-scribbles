import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import HowToPlayDialog from "@/components/home/HowToPlayDialog.vue";
import { i18n } from "@/i18n";

describe("HowToPlayDialog", () => {
  it("renders the how-to steps when open", () => {
    const wrapper = mount(HowToPlayDialog, {
      props: { open: true },
      global: { plugins: [i18n] },
    });

    expect(wrapper.text()).toContain("How to Play");
    expect(wrapper.findAll("li")).toHaveLength(4);
  });
});
