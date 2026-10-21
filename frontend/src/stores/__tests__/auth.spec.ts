import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useAuthStore } from "@/stores/auth";

const apiRequestMock = vi.fn();

vi.mock("@/lib/api", () => ({
  apiRequest: (...args: unknown[]) => apiRequestMock(...args),
}));

const user = {
  displayName: "Simon",
  id: "u1",
  isGuest: false,
  preferredLocale: "en",
  username: "simon",
};

describe("auth store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    apiRequestMock.mockReset();
  });

  it("uses the existing session when /api/me succeeds", async () => {
    apiRequestMock.mockResolvedValueOnce(user);

    const store = useAuthStore();
    await store.bootstrap("nl", "Guest");

    expect(store.currentUser).toEqual(user);
    expect(apiRequestMock).toHaveBeenCalledTimes(1);
    expect(apiRequestMock.mock.calls[0][0]).toBe("/api/me");
  });

  it("creates a guest when the existing session is unavailable", async () => {
    apiRequestMock.mockRejectedValueOnce(new Error("not signed in"));
    apiRequestMock.mockResolvedValueOnce({ ...user, isGuest: true });

    const store = useAuthStore();
    await store.bootstrap("nl", "Guest");

    expect(store.currentUser?.isGuest).toBe(true);
    expect(apiRequestMock).toHaveBeenLastCalledWith(
      "/api/auth/guest",
      expect.objectContaining({
        method: "POST",
        body: { preferredLocale: "nl", displayName: "Guest" },
      }),
    );
  });

  it("ignores a second bootstrap while the first is still running", async () => {
    // Two guest accounts for one browser would split its rooms and kick bans.
    let resolveMe: (value: typeof user) => void = () => {};
    apiRequestMock.mockReturnValueOnce(
      new Promise((resolve) => {
        resolveMe = resolve;
      }),
    );

    const store = useAuthStore();
    const first = store.bootstrap("en", null);
    await store.bootstrap("en", null);
    resolveMe(user);
    await first;

    expect(apiRequestMock).toHaveBeenCalledTimes(1);
    expect(store.currentUser).toEqual(user);
  });

  it("stays signed out when guest auth also fails", async () => {
    apiRequestMock.mockRejectedValueOnce(new Error("not signed in"));
    apiRequestMock.mockRejectedValueOnce(new Error("guest auth failed"));

    const store = useAuthStore();
    await store.bootstrap("en", null);

    expect(store.currentUser).toBeNull();
  });
});
