import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import HdToggle from "@/components/ui/HdToggle.vue";

describe("HdToggle", () => {
  it("renders optional label and help text", () => {
    const wrapper = mount(HdToggle, {
      props: {
        modelValue: false,
        label: "Private Room",
        help: "Private rooms do not appear in quick play.",
      },
    });

    expect(wrapper.text()).toContain("Private Room");
    expect(wrapper.find('[role="img"]').attributes("title")).toBe("Private rooms do not appear in quick play.");
  });

  it("emits model update and change when toggled", async () => {
    const wrapper = mount(HdToggle, {
      props: {
        modelValue: false,
        label: "Private Room",
      },
    });

    await wrapper.find("input").setValue(true);

    expect(wrapper.emitted("update:modelValue")?.[0]).toEqual([true]);
    expect(wrapper.emitted("change")).toHaveLength(1);
  });
});
