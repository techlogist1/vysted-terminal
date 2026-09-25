// @vitest-environment node
import { afterEach, describe, expect, it, vi } from "vitest";

const { _httpGetOk } = await import("./smoke-test-sidecars.mjs");

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("_httpGetOk (R15-CODE-PLATFORM-062)", () => {
  it("a 404 and an offline host (ENOTFOUND-shaped failure) yield different shapes", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce({ ok: false, status: 404 })
        .mockRejectedValueOnce(
          Object.assign(new Error("fetch failed"), { cause: { code: "ENOTFOUND" } }),
        ),
    );

    const notFound = await _httpGetOk("https://example.invalid/a");
    expect(notFound).toEqual({ ok: false, status: 404, error: null });

    const offline = await _httpGetOk("https://example.invalid/b");
    expect(offline.ok).toBe(false);
    expect(offline.status).toBeNull();
    expect(offline.error).toMatch(/fetch failed/);

    // The two failures must be distinguishable, never the same collapsed shape.
    expect(notFound).not.toEqual(offline);
  });

  it("a 200 reports ok:true with its status", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce({ ok: true, status: 200 }));
    await expect(_httpGetOk("https://example.invalid/c")).resolves.toEqual({
      ok: true,
      status: 200,
      error: null,
    });
  });
});
