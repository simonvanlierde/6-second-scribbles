import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import HdDialog from "@/components/ui/HdDialog.vue";

describe("HdDialog", () => {
  it("renders title and message", () => {
    const w = mount(HdDialog, {
      props: { open: true, title: "Are you sure?", message: "This will leave the room." },
    });
    expect(w.text()).toContain("Are you sure?");
    expect(w.text()).toContain("This will leave the room.");
  });

  it("emits confirm when the confirm button is clicked", async () => {
    const w = mount(HdDialog, { props: { open: true, title: "T", message: "M" } });
    await w.find('[data-testid="hd-dialog-confirm"]').trigger("click");
    expect(w.emitted("confirm")).toHaveLength(1);
    expect(w.emitted("update:open")?.[0]).toEqual([false]);
  });

  it("emits cancel when the cancel button is clicked", async () => {
    const w = mount(HdDialog, { props: { open: true, title: "T", message: "M" } });
    await w.find('[data-testid="hd-dialog-cancel"]').trigger("click");
    expect(w.emitted("cancel")).toHaveLength(1);
    expect(w.emitted("update:open")?.[0]).toEqual([false]);
  });

  it("uses custom button labels when provided", () => {
    const w = mount(HdDialog, {
      props: {
        open: true,
        title: "T",
        message: "M",
        confirmLabel: "Yep",
        cancelLabel: "Nope",
      },
    });
    expect(w.find('[data-testid="hd-dialog-confirm"]').text()).toBe("Yep");
    expect(w.find('[data-testid="hd-dialog-cancel"]').text()).toBe("Nope");
  });
});
