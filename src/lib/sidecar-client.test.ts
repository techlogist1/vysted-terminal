import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// `invoke("get_sidecar_port")` is the production port source — stub it.
const invokeMock = vi.fn();
vi.mock("@tauri-apps/api/core", () => ({
  invoke: (...args: unknown[]) => invokeMock(...args),
}));

/** `get_sidecar_port` for a bound engine. */
const READY = { port: 54321, state: "ready", reason: null };

/** R15-LIFECYCLE-010: a spawn failure is named at once, never a 120 s probe. */
describe("a failed sidecar boot", () => {
  beforeEach(() => {
    vi.resetModules();
    invokeMock.mockReset();
    vi.unstubAllGlobals();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("get_sidecar_port answering failed throws its reason at once, without a /health probe", async () => {
    invokeMock.mockResolvedValue({
      port: 54321,
      state: "failed",
      reason: "The data engine could not start (binary not found).",
    });
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const { getSidecarBaseUrl, SidecarError } = await import("@/lib/sidecar-client");

    const error = await getSidecarBaseUrl().catch((e: unknown) => e);

    expect(error).toBeInstanceOf(SidecarError);
    expect((error as Error).message).toBe("The data engine could not start (binary not found).");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("a spawn that fails while the probe waits stops the wait with its reason", async () => {
    invokeMock
      .mockResolvedValueOnce({ port: 54321, state: "starting", reason: null })
      .mockResolvedValue({ port: 54321, state: "failed", reason: "The data engine stopped." });
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new TypeError("Load failed"); // nothing bound yet
      }),
    );
    vi.useFakeTimers();
    const { getSidecarBaseUrl } = await import("@/lib/sidecar-client");

    const pending = getSidecarBaseUrl().catch((e: unknown) => e);
    await vi.advanceTimersByTimeAsync(1_000);

    expect(((await pending) as Error).message).toBe("The data engine stopped.");
    vi.useRealTimers();
  });
});

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
    invokeMock.mockResolvedValue(READY);
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
    invokeMock.mockResolvedValue(READY);
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
    invokeMock.mockRejectedValueOnce(new Error("no port yet")).mockResolvedValue(READY);
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
        return READY;
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

/** R15-UI-014 / R15-CODE-PLATFORM-011: every verb shares one error layer. */
describe("sidecarRequest error layer", () => {
  beforeEach(() => {
    vi.resetModules();
    invokeMock.mockReset();
    invokeMock.mockResolvedValue(READY);
    vi.unstubAllGlobals();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  /** A fetch whose `/health` probe answers ok and whose other calls run `rest`. */
  function stubFetch(rest: () => Promise<Response>) {
    const fetchMock = vi.fn(async (url: string) =>
      new URL(url).pathname === "/health" ? ({ ok: true } as Response) : rest(),
    );
    vi.stubGlobal("fetch", fetchMock);
    return fetchMock;
  }

  it("a refused connection is SidecarError(0) with the unreachable sentence, not 'Load failed'", async () => {
    stubFetch(async () => {
      throw new TypeError("Load failed");
    });
    const { SIDECAR_UNREACHABLE, SidecarError, sidecarGet } = await import("@/lib/sidecar-client");

    const error = await sidecarGet("/macro/series").catch((e: unknown) => e);

    expect(error).toBeInstanceOf(SidecarError);
    expect((error as InstanceType<typeof SidecarError>).status).toBe(0);
    expect((error as Error).message).toBe(SIDECAR_UNREACHABLE);
  });

  it("a POST answering a 422 array throws 'field: msg' and sends a JSON body", async () => {
    const detail = [
      { loc: ["body", "budget", "max_tokens"], msg: "Input should be a valid integer" },
    ];
    const fetchMock = stubFetch(
      async () => new Response(JSON.stringify({ detail }), { status: 422 }),
    );
    const { sidecarRequest } = await import("@/lib/sidecar-client");

    await expect(
      sidecarRequest("POST", "/agents/buffett/runs", { body: { prompt: "x" } }),
    ).rejects.toThrow("max_tokens: Input should be a valid integer");
    const [, init] = fetchMock.mock.calls.at(-1) as unknown as [string, RequestInit];
    expect(init.method).toBe("POST");
    expect(init.body).toBe(JSON.stringify({ prompt: "x" }));
    expect((init.headers as Record<string, string>)["Content-Type"]).toBe("application/json");
  });

  it("a 204 resolves undefined", async () => {
    stubFetch(async () => new Response(null, { status: 204 }));
    const { sidecarRequest } = await import("@/lib/sidecar-client");

    await expect(sidecarRequest("DELETE", "/custom-agents/custom:x")).resolves.toBeUndefined();
  });
});

/**
 * R15-CODE-PLATFORM-039: sidecarRequest is the default REST path for every
 * sidecar call, including polls that never research (e.g. the watchlist's 5 s
 * `/quotes` refresh) — it must not do an unmemoised keychain read + ship the
 * tier_b BYOK OpenRouter key on every one of those.
 */
describe("sidecarRequest omits the research key on its default REST path", () => {
  beforeEach(() => {
    vi.resetModules();
    invokeMock.mockReset();
    vi.unstubAllGlobals();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("tier_b GET /quotes sends no X-Vysted-Openrouter-Key and reads the keychain 0 times", async () => {
    invokeMock.mockImplementation(async (cmd: string) => {
      if (cmd === "get_sidecar_port") return READY;
      if (cmd === "keychain_get") return "sk-or-v1-should-never-be-read";
      throw new Error(`unexpected invoke: ${cmd}`);
    });
    const capturedHeaders: Record<string, string>[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        if (new URL(url).pathname === "/health") return { ok: true } as Response;
        capturedHeaders.push((init?.headers ?? {}) as Record<string, string>);
        return { ok: true, json: async () => ({}) } as Response;
      }),
    );
    const { useSearchSettingsStore } = await import("@/store/search-settings");
    useSearchSettingsStore.getState().setResearchTier("tier_b");
    const { sidecarGet } = await import("@/lib/sidecar-client");

    await sidecarGet("/quotes", { symbols: "AAPL" });

    expect(capturedHeaders[0]["X-Vysted-Openrouter-Key"]).toBeUndefined();
    // The tier header itself still rides every request — only the keychain
    // read + secret are omitted on this path.
    expect(capturedHeaders[0]["X-Vysted-Research-Tier"]).toBe("tier_b");
    expect(invokeMock.mock.calls.filter((c) => c[0] === "keychain_get")).toHaveLength(0);
  });
});
