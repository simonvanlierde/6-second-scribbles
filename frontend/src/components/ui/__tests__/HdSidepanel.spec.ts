import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import HdSidepanel from "@/components/ui/HdSidepanel.vue";

describe("HdSidepanel", () => {
  it("renders the title and body slot", () => {
    const w = mount(HdSidepanel, {
      props: { open: true, title: "Settings" },
      slots: { default: "<p>body content</p>" },
    });
    expect(w.text()).toContain("Settings");
    expect(w.text()).toContain("body content");
  });

  it("emits close + update:open=false when the close button is clicked", async () => {
    const w = mount(HdSidepanel, {
      props: { open: true, title: "X" },
      slots: { default: "x" },
    });
    await w.find('[data-testid="hd-sidepanel-close"]').trigger("click");
    expect(w.emitted("close")).toHaveLength(1);
    expect(w.emitted("update:open")?.[0]).toEqual([false]);
  });

  it("calls showModal / close on the underlying dialog when open changes", async () => {
    // jsdom's <dialog> doesn't actually toggle .open when showModal/close are
    // called; we mock both AND make them sync .open so the component's
    // "only close if currently open" guard fires correctly.
    HTMLDialogElement.prototype.showModal = vi.fn(function (this: HTMLDialogElement) {
      this.open = true;
    });
    HTMLDialogElement.prototype.close = vi.fn(function (this: HTMLDialogElement) {
      this.open = false;
    });
    const w = mount(HdSidepanel, {
      props: { open: false, title: "X" },
      slots: { default: "x" },
    });
    expect(HTMLDialogElement.prototype.showModal).not.toHaveBeenCalled();
    await w.setProps({ open: true });
    expect(HTMLDialogElement.prototype.showModal).toHaveBeenCalledTimes(1);
    await w.setProps({ open: false });
    expect(HTMLDialogElement.prototype.close).toHaveBeenCalledTimes(1);
  });

  it("applies the bottom variant class", () => {
    const w = mount(HdSidepanel, {
      props: { open: true, title: "X", side: "bottom" },
      slots: { default: "x" },
    });
    expect(w.find("dialog").classes()).toContain("hd-sidepanel--bottom");
  });
});
