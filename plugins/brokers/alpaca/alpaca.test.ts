import { describe, expect, it, beforeEach, vi, afterEach } from "vitest";

import { alpacaPlugin } from "./index";
import manifest from "./manifest.json";

import type { PluginManifest } from "../../../types/plugin-runtime";

type FetchMock = ReturnType<typeof vi.fn>;

describe("alpaca broker plugin", () => {
  let fetchMock: FetchMock;

  beforeEach(async () => {
    fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    await alpacaPlugin.shutdown();
  });

  afterEach(async () => {
    await alpacaPlugin.shutdown();
    vi.unstubAllGlobals();
  });

  it("manifest matches the plugin instance identity", () => {
    const typed = manifest as PluginManifest;
    expect(typed.id).toBe(alpacaPlugin.pluginId);
    expect(typed.version).toBe(alpacaPlugin.version);
    expect(typed.name).toBe(alpacaPlugin.pluginName);
  });

  it("declares data + commands + control plane capabilities", () => {
    expect(alpacaPlugin.capabilities.contributesData).toBe(true);
    expect(alpacaPlugin.capabilities.contributesCommands).toBe(true);
    expect(alpacaPlugin.capabilities.supportsControlPlane).toBe(true);
    expect(alpacaPlugin.capabilities.contributesPanels).toBe(false);
    expect(alpacaPlugin.capabilities.contributesAgents).toBe(false);
    expect(alpacaPlugin.capabilities.contributesNodes).toBe(false);
  });

  it("getCommands returns the Alpaca slash-command set", () => {
    const commands = alpacaPlugin.getCommands?.() ?? [];
    const ids = commands.map((c) => c.id);
    expect(ids).toContain("alpaca.connect");
    expect(ids).toContain("alpaca.account");
    expect(ids).toContain("alpaca.set-mode-paper");
    expect(ids).toContain("alpaca.set-mode-live");
    expect(ids).toContain("alpaca.halt");
  });

  it("healthCheck reports unavailable before initialize", async () => {
    const status = await alpacaPlugin.healthCheck();
    expect(status.status).toBe("unavailable");
    expect(status.message).toContain("not initialised");
  });

  it("healthCheck reports healthy when /health is OK", async () => {
    fetchMock.mockResolvedValue({ ok: true, status: 200, text: async () => "{}" });
    await alpacaPlugin.initialize({
      dataDir: "/tmp/alpaca",
      settings: {},
      sidecarBaseUrl: "http://127.0.0.1:0",
      hostVersion: "0.5.0",
      secrets: {},
    });
    const status = await alpacaPlugin.healthCheck();
    expect(status.status).toBe("healthy");
  });

  it("executeCommand without initialize returns error", async () => {
    const result = await alpacaPlugin.executeCommand?.("alpaca.connect", {});
    expect(result?.ok).toBe(false);
    expect(result?.error).toContain("not initialised");
  });

  it("executeCommand 'alpaca.connect' POSTs to /brokers/alpaca/connect", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      text: async () => JSON.stringify({ ok: true }),
    });
    await alpacaPlugin.initialize({
      dataDir: "/tmp/alpaca",
      settings: {},
      sidecarBaseUrl: "http://127.0.0.1:0",
      hostVersion: "0.5.0",
      secrets: {},
    });
    fetchMock.mockClear();
    fetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      text: async () => JSON.stringify({ broker: "alpaca", status: "connected" }),
    });
    const result = await alpacaPlugin.executeCommand?.("alpaca.connect", {
      credentials: { api_key: "ak", api_secret: "sk" },
    });
    expect(result?.ok).toBe(true);
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toContain("/brokers/alpaca/connect");
    expect(init?.method).toBe("POST");
    expect(JSON.parse(init?.body as string).credentials).toEqual({
      api_key: "ak",
      api_secret: "sk",
    });
  });

  it("executeCommand 'alpaca.set-mode-live' POSTs mode=live", async () => {
    fetchMock.mockResolvedValue({ ok: true, status: 200, text: async () => "{}" });
    await alpacaPlugin.initialize({
      dataDir: "/tmp/alpaca",
      settings: {},
      sidecarBaseUrl: "http://127.0.0.1:0",
      hostVersion: "0.5.0",
      secrets: {},
    });
    fetchMock.mockClear();
    fetchMock.mockResolvedValue({ ok: true, status: 200, text: async () => "{}" });
    await alpacaPlugin.executeCommand?.("alpaca.set-mode-live", {});
    const [, init] = fetchMock.mock.calls[0];
    expect(JSON.parse(init?.body as string)).toEqual({ mode: "live" });
  });

  it("executeCommand on unknown id returns error", async () => {
    fetchMock.mockResolvedValue({ ok: true, status: 200, text: async () => "{}" });
    await alpacaPlugin.initialize({
      dataDir: "/tmp/alpaca",
      settings: {},
      sidecarBaseUrl: "http://127.0.0.1:0",
      hostVersion: "0.5.0",
      secrets: {},
    });
    const result = await alpacaPlugin.executeCommand?.("alpaca.unknown", {});
    expect(result?.ok).toBe(false);
    expect(result?.error).toContain("unknown command");
  });
});
