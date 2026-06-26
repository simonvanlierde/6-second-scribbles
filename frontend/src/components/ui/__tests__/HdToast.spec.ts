import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

const notifications = [
  { id: 1, text: "Saved", type: "success" as const },
  { id: 2, text: "Failed", type: "error" as const },
];

vi.mock("@/composables/notifications", () => ({
  useNotifications: () => ({ notifications }),
}));

import HdToast from "@/components/ui/HdToast.vue";

describe("HdToast", () => {
  it("renders one toast per active notification", () => {
    const w = mount(HdToast);
    const items = w.findAll(".hd-toast");
    expect(items).toHaveLength(2);
    expect(w.text()).toContain("Saved");
    expect(w.text()).toContain("Failed");
  });

  it("applies a type class per notification", () => {
    const w = mount(HdToast);
    const items = w.findAll(".hd-toast");
    expect(items[0]?.classes()).toContain("hd-toast--success");
    expect(items[1]?.classes()).toContain("hd-toast--error");
  });
});
