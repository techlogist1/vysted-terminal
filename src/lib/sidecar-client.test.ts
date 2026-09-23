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

/**
 * R15-DATA-002: AMAL is Amal Ltd on BSE and Amalgamated Financial on NASDAQ. An
 * Equity Overview opened for the NASDAQ listing in an IN session must send the
 * picked listing's region on EVERY leg (quote, fundamentals, the three
 * statements, ratings, narrative), or the sidecar binds the session region's
 * company on some legs and the panel shows two companies at once.
 */
describe("per-instrument region override", () => {
  beforeEach(() => {
    vi.resetModules();
    invokeMock.mockReset();
    vi.unstubAllGlobals();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("an overview for the picked US listing sends X-Vysted-Region: US on every leg", async () => {
    invokeMock.mockImplementation(async (cmd: string) => {
      if (cmd === "get_sidecar_port") {
        return 54321;
      }
      throw new Error(`no keychain in tests (${cmd})`);
    });
    const requests: { path: string; region: string | undefined }[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        const path = new URL(url).pathname;
        if (path !== "/health") {
          const headers = (init?.headers ?? {}) as Record<string, string>;
          requests.push({ path, region: headers["X-Vysted-Region"] });
        }
        return { ok: true, json: async () => ({}) } as Response;
      }),
    );
    const { useSettingsStore } = await import("@/store/settings");
    useSettingsStore.setState({ region: "IN" });
    const { loadCompanyNarrative, loadEquityOverview } =
      await import("@/modules/equity-overview/api");

    await loadEquityOverview("AMAL", "US");
    await loadCompanyNarrative("AMAL", "US");

    expect(requests.map((r) => r.path).sort()).toEqual(
      [
        "/fundamentals/AMAL",
        "/fundamentals/AMAL/balance",
        "/fundamentals/AMAL/cashflow",
        "/fundamentals/AMAL/income",
        "/fundamentals/AMAL/narrative",
        "/fundamentals/AMAL/ratings",
        "/quotes/AMAL",
      ].sort(),
    );
    expect(requests.every((r) => r.region === "US")).toBe(true);
  });
});
