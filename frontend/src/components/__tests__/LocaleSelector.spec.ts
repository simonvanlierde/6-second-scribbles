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

  it("keeps the inline variant compact and exposes a centered chevron wrapper", () => {
    const wrapper = mount(LocaleSelector, {
      props: {
        modelValue: "en",
        variant: "inline",
        options: [
          { code: "en", enabled: true },
          { code: "fr", enabled: true },
        ],
      },
    });

    expect(wrapper.get('[data-testid="inline-locale-selector"]').classes()).toContain("items-center");
    expect(wrapper.get("select").classes()).toContain("pr-3");
    expect(wrapper.get('[data-testid="inline-locale-chevron"]').classes()).toContain("-translate-y-1/2");
  });
});
