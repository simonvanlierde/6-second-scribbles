import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import StepperInput from "@/components/StepperInput.vue";
import { i18n } from "@/i18n";

function mountStepper(modelValue = 5) {
  return mount(StepperInput, {
    props: {
      modelValue,
      label: "Rounds",
      min: 1,
      max: 10,
    },
    global: { plugins: [i18n] },
  });
}

describe("StepperInput", () => {
  it("increments and decrements within range", async () => {
    const wrapper = mountStepper(5);

    await wrapper.find('[aria-label="Increase Rounds"]').trigger("click");
    expect(wrapper.emitted("update:modelValue")?.at(-1)).toEqual([6]);

    await wrapper.setProps({ modelValue: 6 });
    await wrapper.find('[aria-label="Decrease Rounds"]').trigger("click");

    expect(wrapper.emitted("update:modelValue")?.at(-1)).toEqual([5]);
  });

  it("updates only valid typed values and clamps on blur", async () => {
    const wrapper = mountStepper(5);
    const input = wrapper.find("input");

    await input.setValue("8");
    expect(wrapper.emitted("update:modelValue")?.at(-1)).toEqual([8]);

    await input.setValue("99");
    expect(wrapper.text()).toContain("Must be between 1 and 10");

    await input.trigger("blur");
    expect(wrapper.emitted("update:modelValue")?.at(-1)).toEqual([10]);
  });
});
