import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";

import App from "../App.vue";

describe("App", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("mounts without errors", () => {
    const wrapper = mount(App, {
      global: {
        stubs: { RouterView: true, ToastContainer: true },
      },
    });
    expect(wrapper.find("#app").exists()).toBe(true);
  });
});
