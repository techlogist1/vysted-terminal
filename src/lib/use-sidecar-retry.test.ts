import { renderHook } from "@testing-library/react";
import { act } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SidecarError } from "@/lib/sidecar-client";
import { useRetryOnSidecarReady } from "@/lib/use-sidecar-retry";

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

async function attemptsFor(error: unknown): Promise<number> {
  const load = vi.fn(() => Promise.reject(error));
  renderHook(() => useRetryOnSidecarReady(load, []));
  await act(async () => {
    await vi.advanceTimersByTimeAsync(60_000);
  });
  return load.mock.calls.length;
}

describe("useRetryOnSidecarReady (R15-UI-015)", () => {
  it("settles after one attempt when the engine answered (a keyless 502)", async () => {
    expect(await attemptsFor(new SidecarError(502, "FRED needs a free API key"))).toBe(1);
  });

  it("retries a raw fetch failure (the engine is not up yet)", async () => {
    expect(await attemptsFor(new TypeError("Failed to fetch"))).toBeGreaterThan(1);
  });

  it("retries an unreachable engine (SidecarError 0) and a not-ready one (503)", async () => {
    expect(await attemptsFor(new SidecarError(0, "not responding"))).toBeGreaterThan(1);
    expect(await attemptsFor(new SidecarError(503, "not ready yet"))).toBeGreaterThan(1);
  });
});
