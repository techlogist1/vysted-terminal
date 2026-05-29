import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// `invoke("get_sidecar_port")` is the production port source — stub it.
const invokeMock = vi.fn();
vi.mock("@tauri-apps/api/core", () => ({
  invoke: (...args: unknown[]) => invokeMock(...args),
}));

/**
 * Regression coverage for the cold-boot bind-race fix: `getSidecarBaseUrl`
 * gates the cached base URL on a real `/health` probe with bounded backoff,
 * shares one in-flight probe across concurrent callers, and re-arms after a
 * failure. The module caches `readyPromise` at module scope, so each test gets
 * a fresh module via `vi.resetModules()`.
 */
describe("getSidecarBaseUrl readiness gate", () => {
  beforeEach(() => {
    vi.resetModules();
    invokeMock.mockReset();
    vi.unstubAllGlobals();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("resolves only after /health responds ok, retrying connection-refused with backoff", async () => {
    invokeMock.mockResolvedValue(54321);
    let attempts = 0;
    const fetchMock = vi.fn(async () => {
      attempts += 1;
      if (attempts < 3) {
        throw new Error("ECONNREFUSED"); // sidecar not bound yet
      }
      return { ok: true } as Response;
    });
    vi.stubGlobal("fetch", fetchMock);
    vi.useFakeTimers();

    const { getSidecarBaseUrl } = await import("@/lib/sidecar-client");
    const pending = getSidecarBaseUrl();
    await vi.advanceTimersByTimeAsync(5000);

    await expect(pending).resolves.toBe("http://127.0.0.1:54321");
    expect(attempts).toBe(3);
  });

  it("shares one in-flight probe across concurrent callers (single invoke)", async () => {
    invokeMock.mockResolvedValue(54321);
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({ ok: true }) as Response),
    );

    const { getSidecarBaseUrl } = await import("@/lib/sidecar-client");
    const [a, b] = await Promise.all([getSidecarBaseUrl(), getSidecarBaseUrl()]);

    expect(a).toBe(b);
    expect(invokeMock).toHaveBeenCalledTimes(1);
  });

  it("re-arms after a failed resolution so a later caller re-probes", async () => {
    invokeMock.mockRejectedValueOnce(new Error("no port yet")).mockResolvedValue(54321);
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({ ok: true }) as Response),
    );

    const { getSidecarBaseUrl } = await import("@/lib/sidecar-client");
    await expect(getSidecarBaseUrl()).rejects.toThrow();
    await expect(getSidecarBaseUrl()).resolves.toBe("http://127.0.0.1:54321");
    expect(invokeMock).toHaveBeenCalledTimes(2);
  });
});
