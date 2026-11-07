import { fireEvent, render } from "@testing-library/svelte";
import { describe, expect, it, vi } from "vitest";
import HomeView from "@/views/HomeView.svelte";

describe("HomeView", () => {
  it("renders the home create/join panel", () => {
    const wrapper = render(HomeView);

    expect(wrapper.container.textContent).toContain("Six Second Scribbles");
    expect(wrapper.container.querySelector(".home-main")).not.toBeNull();
  });

  it("opens the footer dialogs", async () => {
    HTMLDialogElement.prototype.showModal = vi.fn();
    HTMLDialogElement.prototype.close = vi.fn();

    const wrapper = render(HomeView);

    const [howToPlay, about] = Array.from(wrapper.container.querySelectorAll(".home-footer__link"));
    await fireEvent.click(howToPlay!);
    await fireEvent.click(about!);

    expect(HTMLDialogElement.prototype.showModal).toHaveBeenCalledTimes(2);
  });
});
