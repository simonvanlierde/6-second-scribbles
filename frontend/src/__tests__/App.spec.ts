import { render } from "@testing-library/svelte";
import { tick } from "svelte";
import { describe, expect, it, vi } from "vitest";

import App from "@/App.svelte";
import { useAnnouncer } from "@/composables/useAnnouncer.svelte";

vi.mock("@/stores/auth.svelte", () => ({
  useAuthStore: () => ({ bootstrap: vi.fn(), currentUser: null }),
}));

describe("App", () => {
  it("reads announcements out through one polite live region", async () => {
    useAnnouncer().message = "";
    const { container } = render(App);
    const region = container.querySelector("[role=status][aria-atomic=true]")!;
    expect(region.textContent).toBe("");

    useAnnouncer().announce("Round 2: guessing");
    await tick();
    await tick();

    expect(region.textContent).toBe("Round 2: guessing");
  });
});
