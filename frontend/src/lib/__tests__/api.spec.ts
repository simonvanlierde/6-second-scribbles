// cspell:ignore unstub
import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, apiRequest } from "@/lib/api";

function stubFetch(response: Response) {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response));
}

describe("apiRequest", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("raises the backend's detail with the status, so callers can tell a 429 apart", async () => {
    stubFetch(Response.json({ detail: "Too many open rooms from your network." }, { status: 429 }));

    const error = await apiRequest("/api/rooms/", { method: "POST" }).catch((err: unknown) => err);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 429, message: "Too many open rooms from your network." });
  });

  it("falls back to a generic message when the error body is not JSON", async () => {
    stubFetch(new Response("<html>Bad gateway</html>", { status: 502 }));

    await expect(apiRequest("/api/rooms/quick-play")).rejects.toMatchObject({
      status: 502,
      message: "Request failed with status 502",
    });
  });
});
