import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/sidecar-client", () => ({
  getSidecarBaseUrl: () => Promise.resolve("http://127.0.0.1:51763"),
}));

const refreshMock = vi.hoisted(() => vi.fn(async () => undefined));
vi.mock("@/store/agents", () => ({
  useAgentsStore: { getState: () => ({ refresh: refreshMock }) },
}));

import { CATALOG_BY_ID } from "@/lib/marketplace";
import { pluginAgentId, syncPluginAgents } from "@/lib/plugin-agents";
import { PluginRuntime } from "@/lib/plugin-runtime";

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

  it("updates an already-registered agent via PUT on a 409 so a revised spec replaces it (R15-AGENT-057)", async () => {
    const fetchMock = vi.fn(async (_url: string, init?: RequestInit) =>
      init?.method === "POST" ? { ok: false, status: 409 } : { ok: true, status: 200 },
    );
    vi.stubGlobal("fetch", fetchMock);
    await syncPluginAgents("vysted-lenses", true);
    const put = (fetchMock as unknown as FetchCalls).mock.calls.find((c) => c[1]?.method === "PUT");
    expect(put).toBeDefined();
    expect(String(put![0])).toContain(encodeURIComponent("custom:vysted-lenses-quant-tutor"));
    const lenses = CATALOG_BY_ID["vysted-lenses"].discovered.instance.getAgents!();
    const tutor = lenses.find((a) => a.id === "quant-tutor")!;
    expect(JSON.parse(String(put![1]!.body)).system_prompt).toBe(tutor.systemPrompt);
  });

  it("a rejected registration (422) marks the plugin errored with the reason (R15-AGENT-057)", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({ ok: false, status: 422, text: async () => "unknown tool id" })),
    );
    const runtime = new PluginRuntime({
      hostVersion: "0.8.0",
      host: {
        attach: (id) => syncPluginAgents(id, true),
        detach: (id) => syncPluginAgents(id, false),
      },
    });
    const snapshot = await runtime.loadPlugin(CATALOG_BY_ID["vysted-lenses"].discovered);
    expect(snapshot.state).toBe("error");
    expect(snapshot.errorMessage).toContain("HTTP 422 unknown tool id");
    expect(refreshMock).toHaveBeenCalled();
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
