import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { kitePlugin } from "./index";
import manifest from "./manifest.json";

import type { PluginManifest } from "../../../types/plugin-runtime";

type FetchMock = ReturnType<typeof vi.fn>;

describe("kite plugin", () => {
  let fetchMock: FetchMock;

  beforeEach(async () => {
    fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    await kitePlugin.shutdown();
  });

  afterEach(async () => {
    await kitePlugin.shutdown();
    vi.unstubAllGlobals();
  });

  it("manifest matches the plugin identity AND declares requiresStaticIp", () => {
    const typed = manifest as PluginManifest & { requiresStaticIp?: boolean };
    expect(typed.id).toBe(kitePlugin.pluginId);
    expect(typed.requiresStaticIp).toBe(true);
  });

  it("declares data + commands + control plane", () => {
    expect(kitePlugin.capabilities.contributesData).toBe(true);
    expect(kitePlugin.capabilities.contributesCommands).toBe(true);
    expect(kitePlugin.capabilities.supportsControlPlane).toBe(true);
  });

  it("exposes the static-ip-status command", () => {
    const commands = kitePlugin.getCommands?.() ?? [];
    const ids = commands.map((c) => c.id);
    expect(ids).toContain("kite.static-ip-status");
  });

  it("executeCommand connect routes through /brokers/kite/connect", async () => {
    fetchMock.mockResolvedValue({ ok: true, text: async () => "{}" });
    await kitePlugin.initialize({
      dataDir: "/tmp/kite",
      settings: {},
      sidecarBaseUrl: "http://127.0.0.1:0",
      hostVersion: "0.5.0",
      secrets: {},
    });
    const result = await kitePlugin.executeCommand?.("connect", {
      credentials: { api_key: "k", access_token: "t" },
    });
    expect(result?.ok).toBe(true);
    expect(fetchMock.mock.calls[0][0]).toContain("/brokers/kite/connect");
  });

  it("executeCommand set-static-ip posts /brokers/kite/static-ip", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      text: async () => JSON.stringify({ configuredIp: "203.0.113.5" }),
    });
    await kitePlugin.initialize({
      dataDir: "/tmp/kite",
      settings: {},
      sidecarBaseUrl: "http://127.0.0.1:0",
      hostVersion: "0.5.0",
      secrets: {},
    });
    const result = await kitePlugin.executeCommand?.("set-static-ip", {
      staticIp: "203.0.113.5",
    });
    expect(result?.ok).toBe(true);
    expect(fetchMock.mock.calls[0][0]).toContain("/brokers/kite/static-ip");
    const body = JSON.parse(fetchMock.mock.calls[0][1].body as string);
    expect(body.staticIp).toBe("203.0.113.5");
  });

  it("executeCommand static-ip-status pulls configured then safety status", async () => {
    fetchMock
      .mockResolvedValueOnce({
        ok: true,
        text: async () => JSON.stringify({ configuredIp: "203.0.113.5" }),
      })
      .mockResolvedValueOnce({
        ok: true,
        text: async () =>
          JSON.stringify({
            detectedIp: "203.0.113.5",
            configuredIp: "203.0.113.5",
            matches: true,
            message: "match",
            detectedAt: 1,
          }),
      });
    await kitePlugin.initialize({
      dataDir: "/tmp/kite",
      settings: {},
      sidecarBaseUrl: "http://127.0.0.1:0",
      hostVersion: "0.5.0",
      secrets: {},
    });
    const result = await kitePlugin.executeCommand?.("static-ip-status", {});
    expect(result?.ok).toBe(true);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(fetchMock.mock.calls[0][0]).toContain("/brokers/kite/static-ip");
    // Second call to /safety/static-ip-status carries the configured IP in
    // the query string.
    expect(String(fetchMock.mock.calls[1][0])).toContain("/safety/static-ip-status");
    expect(String(fetchMock.mock.calls[1][0])).toContain("configured=203.0.113.5");
  });

  it("executeCommand place-order POSTs the propose endpoint (NOT confirm)", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      text: async () => JSON.stringify({ proposalId: "abc" }),
    });
    await kitePlugin.initialize({
      dataDir: "/tmp/kite",
      settings: {},
      sidecarBaseUrl: "http://127.0.0.1:0",
      hostVersion: "0.5.0",
      secrets: {},
    });
    await kitePlugin.executeCommand?.("place-order", {
      symbol: "INFY",
      side: "buy",
      type: "limit",
      quantity: 5,
      limitPrice: 100,
      currency: "INR",
      source: "manual",
      sourceDetails: {},
    });
    const url = String(fetchMock.mock.calls[0][0]);
    expect(url).toContain("/brokers/kite/orders");
    expect(url).not.toContain("/confirm");
  });

  it("executeCommand halt-trading sets read-only true", async () => {
    fetchMock.mockResolvedValue({ ok: true, text: async () => "{}" });
    await kitePlugin.initialize({
      dataDir: "/tmp/kite",
      settings: {},
      sidecarBaseUrl: "http://127.0.0.1:0",
      hostVersion: "0.5.0",
      secrets: {},
    });
    await kitePlugin.executeCommand?.("halt-trading", {});
    const body = JSON.parse(fetchMock.mock.calls[0][1].body as string);
    expect(body.readOnly).toBe(true);
  });

  it("executeCommand unknown id returns ok:false", async () => {
    await kitePlugin.initialize({
      dataDir: "/tmp/kite",
      settings: {},
      sidecarBaseUrl: "http://127.0.0.1:0",
      hostVersion: "0.5.0",
      secrets: {},
    });
    const result = await kitePlugin.executeCommand?.("does-not-exist", {});
    expect(result?.ok).toBe(false);
  });
});
