import { renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const invokeMock = vi.fn();
/** `get_sidecar_port` for a bound engine. */
const READY = { port: 54321, state: "ready", reason: null };
vi.mock("@tauri-apps/api/core", () => ({
  invoke: (...args: unknown[]) => invokeMock(...args),
}));

/**
 * R15-LIFECYCLE-011: `sidecarStatus` moves both ways. A connection-refused call
 * turns `connected` into `error`; the next answer turns it back, and that edge
 * re-runs a `useRetryOnSidecarReady` panel whose load had failed.
 */
describe("sidecar status follows reachability", () => {
  beforeEach(() => {
    vi.resetModules();
    invokeMock.mockReset();
    invokeMock.mockResolvedValue(READY);
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("a refused call flips connected to error; a later answer flips back and re-runs a panel load", async () => {
    let engineUp = true;
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        if (!engineUp) {
          throw new TypeError("Load failed");
        }
        return new Response("{}", { status: 200 });
      }),
    );
    const { useAppStore } = await import("@/store/app");
    const { sidecarGet, SIDECAR_UNREACHABLE } = await import("@/lib/sidecar-client");
    const { useRetryOnSidecarReady } = await import("@/lib/use-sidecar-retry");

    await useAppStore.getState().connectSidecar();
    expect(useAppStore.getState().sidecarStatus).toBe("connected");

    vi.useFakeTimers();
    engineUp = false;
    const load = vi.fn(() => sidecarGet<unknown>("/macro/series").then(() => undefined));
    renderHook(() => useRetryOnSidecarReady(load, []));
    await vi.advanceTimersByTimeAsync(0);

    expect(useAppStore.getState().sidecarStatus).toBe("error");
    expect(useAppStore.getState().sidecarError).toBe(SIDECAR_UNREACHABLE);
    const loadsWhileDown = load.mock.calls.length;

    engineUp = true;
    await sidecarGet("/health");
    await vi.advanceTimersByTimeAsync(0);

    expect(useAppStore.getState().sidecarStatus).toBe("connected");
    expect(load.mock.calls.length).toBe(loadsWhileDown + 1);
  });

  it("while in error, /health is re-probed until the engine answers", async () => {
    let engineUp = false;
    const fetchMock = vi.fn(async () => {
      if (!engineUp) {
        throw new TypeError("Load failed");
      }
      return new Response("{}", { status: 200 });
    });
    vi.stubGlobal("fetch", fetchMock);
    const { useAppStore, SIDECAR_REPROBE_MS } = await import("@/store/app");
    const { sidecarGet } = await import("@/lib/sidecar-client");
    // The engine was up at boot and has since died.
    engineUp = true;
    await useAppStore.getState().connectSidecar();
    engineUp = false;
    vi.useFakeTimers();
    await sidecarGet("/quotes/AAPL").catch(() => undefined);
    expect(useAppStore.getState().sidecarStatus).toBe("error");

    engineUp = true;
    await vi.advanceTimersByTimeAsync(SIDECAR_REPROBE_MS);

    expect(useAppStore.getState().sidecarStatus).toBe("connected");
  });
});
