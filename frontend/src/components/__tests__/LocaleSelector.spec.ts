import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import LocaleSelector from "@/components/LocaleSelector.vue";

describe("LocaleSelector", () => {
  it("renders disabled locales with reasons", () => {
    const wrapper = mount(LocaleSelector, {
      props: {
        modelValue: "en",
        options: [
          { code: "en", enabled: true },
          { code: "es", enabled: false, reason: "No playable categories yet" },
        ],
      },
    });

    const options = wrapper.findAll("option");
    expect(options).toHaveLength(2);
    expect(options[1]?.attributes("disabled")).toBeDefined();
    expect(wrapper.text()).toContain("No playable categories yet");
  });

  it("emits update when locale changes", async () => {
    const wrapper = mount(LocaleSelector, {
      props: {
        modelValue: "en",
        options: [
          { code: "en", enabled: true },
          { code: "fr", enabled: true },
        ],
      },
    });

    await wrapper.get("select").setValue("fr");

    expect(wrapper.emitted("update:modelValue")).toEqual([["fr"]]);
  });
});
