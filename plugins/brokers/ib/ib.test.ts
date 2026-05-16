import { describe, expect, it, beforeEach, vi, afterEach } from "vitest";

import { ibPlugin } from "./index";
import manifest from "./manifest.json";

import type { PluginManifest } from "../../../types/plugin-runtime";

type FetchMock = ReturnType<typeof vi.fn>;

describe("ib broker plugin", () => {
  let fetchMock: FetchMock;

  beforeEach(async () => {
    fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    await ibPlugin.shutdown();
  });

  afterEach(async () => {
    await ibPlugin.shutdown();
    vi.unstubAllGlobals();
  });

  it("manifest matches the plugin instance identity", () => {
    const typed = manifest as PluginManifest;
    expect(typed.id).toBe(ibPlugin.pluginId);
    expect(typed.version).toBe(ibPlugin.version);
    expect(typed.name).toBe(ibPlugin.pluginName);
  });

  it("declares data + commands + control plane capabilities", () => {
    expect(ibPlugin.capabilities.contributesData).toBe(true);
    expect(ibPlugin.capabilities.contributesCommands).toBe(true);
    expect(ibPlugin.capabilities.supportsControlPlane).toBe(true);
  });

  it("getCommands surfaces the IB slash-command set", () => {
    const commands = ibPlugin.getCommands?.() ?? [];
    const ids = commands.map((c) => c.id);
    expect(ids).toContain("ib.connect");
    expect(ids).toContain("ib.account");
    expect(ids).toContain("ib.set-mode-paper");
    expect(ids).toContain("ib.set-mode-live");
    expect(ids).toContain("ib.halt");
  });

  it("healthCheck reports unavailable before initialize", async () => {
    const status = await ibPlugin.healthCheck();
    expect(status.status).toBe("unavailable");
  });

  it("healthCheck mentions TWS / IB Gateway requirement when healthy", async () => {
    fetchMock.mockResolvedValue({ ok: true, status: 200, text: async () => "{}" });
    await ibPlugin.initialize({
      dataDir: "/tmp/ib",
      settings: {},
      sidecarBaseUrl: "http://127.0.0.1:0",
      hostVersion: "0.5.0",
      secrets: {},
    });
    const status = await ibPlugin.healthCheck();
    expect(status.status).toBe("healthy");
    expect(status.message).toContain("TWS");
  });

  it("executeCommand 'ib.connect' POSTs to /brokers/ib/connect", async () => {
    fetchMock.mockResolvedValue({ ok: true, status: 200, text: async () => "{}" });
    await ibPlugin.initialize({
      dataDir: "/tmp/ib",
      settings: {},
      sidecarBaseUrl: "http://127.0.0.1:0",
      hostVersion: "0.5.0",
      secrets: {},
    });
    fetchMock.mockClear();
    fetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      text: async () => JSON.stringify({ broker: "ib", status: "connected" }),
    });
    const result = await ibPlugin.executeCommand?.("ib.connect", {
      credentials: { host: "127.0.0.1", port: "7497" },
    });
    expect(result?.ok).toBe(true);
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toContain("/brokers/ib/connect");
    expect(init?.method).toBe("POST");
    const body = JSON.parse(init?.body as string);
    expect(body.credentials.port).toBe("7497");
  });

  it("executeCommand 'ib.halt' POSTs read-only=true", async () => {
    fetchMock.mockResolvedValue({ ok: true, status: 200, text: async () => "{}" });
    await ibPlugin.initialize({
      dataDir: "/tmp/ib",
      settings: {},
      sidecarBaseUrl: "http://127.0.0.1:0",
      hostVersion: "0.5.0",
      secrets: {},
    });
    fetchMock.mockClear();
    fetchMock.mockResolvedValue({ ok: true, status: 200, text: async () => "{}" });
    await ibPlugin.executeCommand?.("ib.halt", {});
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toContain("/brokers/ib/read-only");
    expect(JSON.parse(init?.body as string)).toEqual({ readOnly: true });
  });
});
