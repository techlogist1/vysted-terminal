import { describe, expect, it, beforeEach, vi, afterEach } from "vitest";

import { oandaPlugin } from "./index";
import manifest from "./manifest.json";

import type { PluginManifest } from "../../../types/plugin-runtime";

type FetchMock = ReturnType<typeof vi.fn>;

describe("oanda broker plugin", () => {
  let fetchMock: FetchMock;

  beforeEach(async () => {
    fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    await oandaPlugin.shutdown();
  });

  afterEach(async () => {
    await oandaPlugin.shutdown();
    vi.unstubAllGlobals();
  });

  it("manifest matches the plugin instance identity", () => {
    const typed = manifest as PluginManifest;
    expect(typed.id).toBe(oandaPlugin.pluginId);
    expect(typed.version).toBe(oandaPlugin.version);
    expect(typed.name).toBe(oandaPlugin.pluginName);
  });

  it("declares data + commands + control plane capabilities", () => {
    expect(oandaPlugin.capabilities.contributesData).toBe(true);
    expect(oandaPlugin.capabilities.contributesCommands).toBe(true);
    expect(oandaPlugin.capabilities.supportsControlPlane).toBe(true);
  });

  it("getCommands surfaces the OANDA slash-command set including demo + live mode", () => {
    const commands = oandaPlugin.getCommands?.() ?? [];
    const ids = commands.map((c) => c.id);
    expect(ids).toContain("oanda.connect");
    expect(ids).toContain("oanda.account");
    expect(ids).toContain("oanda.set-mode-paper");
    expect(ids).toContain("oanda.set-mode-live");
    expect(ids).toContain("oanda.halt");
  });

  it("healthCheck reports unavailable before initialize", async () => {
    const status = await oandaPlugin.healthCheck();
    expect(status.status).toBe("unavailable");
  });

  it("executeCommand 'oanda.connect' POSTs to /brokers/oanda/connect", async () => {
    fetchMock.mockResolvedValue({ ok: true, status: 200, text: async () => "{}" });
    await oandaPlugin.initialize({
      dataDir: "/tmp/oanda",
      settings: {},
      sidecarBaseUrl: "http://127.0.0.1:0",
      hostVersion: "0.5.0",
      secrets: {},
    });
    fetchMock.mockClear();
    fetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      text: async () => JSON.stringify({ broker: "oanda", status: "connected" }),
    });
    const result = await oandaPlugin.executeCommand?.("oanda.connect", {
      credentials: { access_token: "tok", account_id: "101-001-1-001" },
    });
    expect(result?.ok).toBe(true);
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toContain("/brokers/oanda/connect");
    expect(init?.method).toBe("POST");
  });

  it("executeCommand 'oanda.set-mode-paper' POSTs mode=paper", async () => {
    fetchMock.mockResolvedValue({ ok: true, status: 200, text: async () => "{}" });
    await oandaPlugin.initialize({
      dataDir: "/tmp/oanda",
      settings: {},
      sidecarBaseUrl: "http://127.0.0.1:0",
      hostVersion: "0.5.0",
      secrets: {},
    });
    fetchMock.mockClear();
    fetchMock.mockResolvedValue({ ok: true, status: 200, text: async () => "{}" });
    await oandaPlugin.executeCommand?.("oanda.set-mode-paper", {});
    const [, init] = fetchMock.mock.calls[0];
    expect(JSON.parse(init?.body as string)).toEqual({ mode: "paper" });
  });
});
