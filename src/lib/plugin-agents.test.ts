import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/sidecar-client", () => ({
  getSidecarBaseUrl: () => Promise.resolve("http://127.0.0.1:51763"),
}));

const refreshMock = vi.hoisted(() => vi.fn(async () => undefined));
vi.mock("@/store/agents", () => ({
  useAgentsStore: { getState: () => ({ refresh: refreshMock }) },
}));

import { pluginAgentId, syncPluginAgents } from "@/lib/plugin-agents";

type FetchCalls = { mock: { calls: [string, RequestInit | undefined][] } };

describe("plugin-agents — agent slice of the marketplace (FR-050/US10 AS3)", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    refreshMock.mockClear();
  });

  it("derives a custom:-prefixed, slug-safe id", () => {
    expect(pluginAgentId("vysted-lenses", "quant-tutor")).toBe("custom:vysted-lenses-quant-tutor");
  });

  it("registers an agent plugin's agents as custom agents so they are runnable", async () => {
    const fetchMock = vi.fn(async () => ({
      ok: true,
      json: async () => ({}),
    })) as unknown as typeof fetch;
    vi.stubGlobal("fetch", fetchMock);
    await syncPluginAgents("vysted-lenses", true);
    const calls = (fetchMock as unknown as FetchCalls).mock.calls;
    const post = calls.find(
      (c) => String(c[0]).includes("/custom-agents") && c[1]?.method === "POST",
    );
    expect(post).toBeDefined();
    const body = JSON.parse(String(post![1]!.body));
    expect(body.id).toBe("custom:vysted-lenses-quant-tutor");
    expect(body.tools).toContain("price_data");
    expect(body.default_provider).toBe("anthropic");
    expect(refreshMock).toHaveBeenCalled();
  });

  it("is a no-op for a non-agent plugin (yfinance data)", async () => {
    const fetchMock = vi.fn(async () => ({
      ok: true,
      json: async () => ({}),
    })) as unknown as typeof fetch;
    vi.stubGlobal("fetch", fetchMock);
    await syncPluginAgents("vysted-yfinance", true);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("removes (DELETE) the registered agents on unregister", async () => {
    const fetchMock = vi.fn(async () => ({ ok: true })) as unknown as typeof fetch;
    vi.stubGlobal("fetch", fetchMock);
    await syncPluginAgents("vysted-lenses", false);
    const calls = (fetchMock as unknown as FetchCalls).mock.calls;
    const del = calls.find((c) => c[1]?.method === "DELETE");
    expect(del).toBeDefined();
    expect(String(del![0])).toContain("vysted-lenses-quant-tutor");
  });
});
