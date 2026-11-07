import { render } from "@testing-library/svelte";
import { describe, expect, it, vi } from "vitest";

const notifications = [
  { id: 1, text: "Saved", type: "success" as const },
  { id: 2, text: "Failed", type: "error" as const },
];

vi.mock("@/composables/notifications.svelte", () => ({
  useNotifications: () => ({ notifications }),
}));

import HdToast from "@/components/ui/HdToast.svelte";

describe("HdToast", () => {
  it("renders one toast per active notification", () => {
    const w = render(HdToast, { props: {} });
    const items = Array.from(w.container.querySelectorAll(".hd-toast"));
    expect(items).toHaveLength(2);
    expect(w.container.textContent?.trim()).toContain("Saved");
    expect(w.container.textContent?.trim()).toContain("Failed");
  });

  it("applies a type class per notification", () => {
    const w = render(HdToast, { props: {} });
    const items = Array.from(w.container.querySelectorAll(".hd-toast"));
    expect(Array.from(items[0]?.classList)).toContain("hd-toast--success");
    expect(Array.from(items[1]?.classList)).toContain("hd-toast--error");
  });
});
