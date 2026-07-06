import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import { i18n } from "@/i18n";
import HomeView from "@/views/HomeView.vue";

describe("HomeView", () => {
  it("renders the home create/join panel", () => {
    const wrapper = mount(HomeView, {
      global: {
        plugins: [i18n],
        stubs: {
          HomeCreateJoin: { template: '<div data-testid="create-join" />' },
        },
      },
    });

    expect(wrapper.text()).toContain("Six Second Scribbles");
    expect(wrapper.find('[data-testid="create-join"]').exists()).toBe(true);
  });

  it("opens the footer dialogs", async () => {
    HTMLDialogElement.prototype.showModal = vi.fn();
    HTMLDialogElement.prototype.close = vi.fn();

    const wrapper = mount(HomeView, {
      global: {
        plugins: [i18n],
        stubs: {
          HomeCreateJoin: { template: '<div data-testid="create-join" />' },
        },
      },
    });

    const [howToPlay, about] = wrapper.findAll(".home-footer__link");
    await howToPlay?.trigger("click");
    await about?.trigger("click");

    expect(HTMLDialogElement.prototype.showModal).toHaveBeenCalledTimes(2);
  });
});
