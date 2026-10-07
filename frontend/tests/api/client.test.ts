import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";

import { apiFetch } from "../../src/api/client";

function mockFetchOnce(body: unknown = {}, status = 200) {
  return vi.fn().mockResolvedValue({
    status,
    ok: status >= 200 && status < 300,
    json: async () => body,
  });
}

describe("apiFetch CSRF header injection", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    document.cookie = "csrf_token=the-csrf-token";
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    document.cookie = "csrf_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC";
  });

  it.each(["POST", "PATCH", "PUT", "DELETE"])(
    "attaches X-CSRF-Token on a %s request with no per-call-site code",
    async (method) => {
      const fetchMock = mockFetchOnce();
      globalThis.fetch = fetchMock as unknown as typeof fetch;

      await apiFetch("/some/path", { method });

      const [, init] = fetchMock.mock.calls[0];
      const headers = new Headers(init.headers);
      expect(headers.get("X-CSRF-Token")).toBe("the-csrf-token");
    },
  );

  it("does not attach X-CSRF-Token on a GET request", async () => {
    const fetchMock = mockFetchOnce();
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    await apiFetch("/some/path");

    const [, init] = fetchMock.mock.calls[0];
    const headers = new Headers(init.headers);
    expect(headers.get("X-CSRF-Token")).toBeNull();
  });
});
