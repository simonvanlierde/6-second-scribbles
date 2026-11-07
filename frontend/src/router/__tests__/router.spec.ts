import { afterEach, describe, expect, it } from "vitest";
import { startRouter, useRoute, useRouter } from "@/router";

let stop: (() => void) | undefined;
afterEach(() => {
  stop?.();
  window.history.replaceState(null, "", "/");
});

describe("browser routing", () => {
  it("normalizes room links on initial load", () => {
    window.history.replaceState(null, "", "/rooms/abcdef");
    stop = startRouter();
    expect(useRoute().params.roomCode).toBe("ABCDEF");
    expect(window.location.pathname).toBe("/rooms/ABCDEF");
  });

  it("updates the route after navigation and browser history events", async () => {
    stop = startRouter();
    await useRouter().push({ name: "room", params: { roomCode: "ABCDEF" } });
    expect(useRoute().name).toBe("room");
    window.history.replaceState(null, "", "/__ds");
    window.dispatchEvent(new PopStateEvent("popstate"));
    expect(useRoute().name).toBe("design-system");
    expect(useRoute().params).toEqual({});
  });

  it("redirects unknown and malformed links home", () => {
    for (const path of ["/missing", "/rooms/%E0%A4%A"]) {
      window.history.replaceState(null, "", path);
      const dispose = startRouter();
      expect(useRoute().name).toBe("home");
      expect(window.location.pathname).toBe("/");
      dispose();
    }
  });
});
