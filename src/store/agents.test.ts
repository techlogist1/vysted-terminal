import { afterEach, describe, expect, it, vi } from "vitest";

import { useAgentsStore } from "@/store/agents";

vi.mock("@/lib/sidecar-client", async () => {
  const actual =
    await vi.importActual<typeof import("@/lib/sidecar-client")>("@/lib/sidecar-client");
  return { ...actual, getSidecarBaseUrl: vi.fn(async () => "http://127.0.0.1:9999") };
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("useAgentsStore.refreshCustom", () => {
  it("refreshCustom 404 -> customStatus error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify({ detail: "Not Found" }), { status: 404 })),
    );
    await useAgentsStore.getState().refreshCustom();
    expect(useAgentsStore.getState().customStatus).toBe("error");
    expect(useAgentsStore.getState().customError).toBe("Not Found");
  });
});
