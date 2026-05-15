import { describe, expect, it, beforeEach, vi, afterEach } from "vitest";

import { openbbMcpPlugin } from "./index";
import manifest from "./manifest.json";

import type { PluginManifest } from "../../types/plugin-runtime";

type FetchMock = ReturnType<typeof vi.fn>;

describe("openbb-mcp plugin", () => {
  let fetchMock: FetchMock;

  beforeEach(async () => {
    fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    await openbbMcpPlugin.shutdown();
  });

  afterEach(async () => {
    await openbbMcpPlugin.shutdown();
    vi.unstubAllGlobals();
  });

  it("manifest matches the plugin instance identity", () => {
    const typed = manifest as PluginManifest;
    expect(typed.id).toBe(openbbMcpPlugin.pluginId);
    expect(typed.version).toBe(openbbMcpPlugin.version);
    expect(typed.name).toBe(openbbMcpPlugin.pluginName);
  });

  it("declares only contributesData", () => {
    expect(openbbMcpPlugin.capabilities.contributesData).toBe(true);
    expect(openbbMcpPlugin.capabilities.contributesPanels).toBe(false);
    expect(openbbMcpPlugin.capabilities.contributesCommands).toBe(false);
    expect(openbbMcpPlugin.capabilities.contributesAgents).toBe(false);
    expect(openbbMcpPlugin.capabilities.contributesNodes).toBe(false);
    expect(openbbMcpPlugin.capabilities.supportsControlPlane).toBe(false);
  });

  it("getDataSources returns equity, fundamentals, and macro shapes", () => {
    const sources = openbbMcpPlugin.getDataSources?.() ?? [];
    expect(sources.length).toBe(3);
    const ids = sources.map((s) => s.id);
    expect(ids).toContain("openbb-mcp-equity");
    expect(ids).toContain("openbb-mcp-fundamentals");
    expect(ids).toContain("openbb-mcp-macro");
  });

  it("healthCheck reports unavailable before initialize", async () => {
    const status = await openbbMcpPlugin.healthCheck();
    expect(status.status).toBe("unavailable");
    expect(status.message).toContain("not initialised");
  });

  it("healthCheck reports healthy when /openbb-mcp/status reports available", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => ({
        available: true,
        provider: "openbb-mcp",
        endpoint: "http://127.0.0.1:9000/mcp/",
        lastToolCallOk: true,
        lastError: null,
      }),
    });
    await openbbMcpPlugin.initialize({
      dataDir: "/tmp/openbb-mcp",
      settings: {},
      sidecarBaseUrl: "http://127.0.0.1:0",
      hostVersion: "0.4.0",
      secrets: {},
    });
    const status = await openbbMcpPlugin.healthCheck();
    expect(status.status).toBe("healthy");
    expect(fetchMock).toHaveBeenCalled();
  });

  it("healthCheck reports unavailable when /openbb-mcp/status reports !available", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => ({
        available: false,
        provider: "openbb-mcp",
        endpoint: null,
        lastToolCallOk: null,
        lastError: null,
      }),
    });
    await openbbMcpPlugin.initialize({
      dataDir: "/tmp/openbb-mcp",
      settings: {},
      sidecarBaseUrl: "http://127.0.0.1:0",
      hostVersion: "0.4.0",
      secrets: {},
    });
    const status = await openbbMcpPlugin.healthCheck();
    expect(status.status).toBe("unavailable");
    expect(status.message).toContain("falling back");
  });

  it("healthCheck reports degraded when last tool call failed", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => ({
        available: true,
        provider: "openbb-mcp",
        endpoint: "http://127.0.0.1:9000/mcp/",
        lastToolCallOk: false,
        lastError: "boom",
      }),
    });
    await openbbMcpPlugin.initialize({
      dataDir: "/tmp/openbb-mcp",
      settings: {},
      sidecarBaseUrl: "http://127.0.0.1:0",
      hostVersion: "0.4.0",
      secrets: {},
    });
    const status = await openbbMcpPlugin.healthCheck();
    expect(status.status).toBe("degraded");
    expect(status.message).toContain("boom");
  });

  it("healthCheck reports unavailable when the sidecar is unreachable", async () => {
    fetchMock.mockRejectedValue(new Error("ECONNREFUSED"));
    await openbbMcpPlugin.initialize({
      dataDir: "/tmp/openbb-mcp",
      settings: {},
      sidecarBaseUrl: "http://127.0.0.1:0",
      hostVersion: "0.4.0",
      secrets: {},
    });
    const status = await openbbMcpPlugin.healthCheck();
    expect(status.status).toBe("unavailable");
    expect(status.message).toContain("Sidecar unreachable");
  });
});
