import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { angelOnePlugin } from "./index";
import manifest from "./manifest.json";

import type { PluginManifest } from "../../../types/plugin-runtime";

type FetchMock = ReturnType<typeof vi.fn>;

describe("angelone plugin", () => {
  let fetchMock: FetchMock;

  beforeEach(async () => {
    fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    await angelOnePlugin.shutdown();
  });

  afterEach(async () => {
    await angelOnePlugin.shutdown();
    vi.unstubAllGlobals();
  });

  it("manifest matches the plugin instance identity", () => {
    const typed = manifest as PluginManifest;
    expect(typed.id).toBe(angelOnePlugin.pluginId);
    expect(typed.version).toBe(angelOnePlugin.version);
    expect(typed.name).toBe(angelOnePlugin.pluginName);
  });

  it("declares data + commands + control plane", () => {
    expect(angelOnePlugin.capabilities.contributesData).toBe(true);
    expect(angelOnePlugin.capabilities.contributesCommands).toBe(true);
    expect(angelOnePlugin.capabilities.supportsControlPlane).toBe(true);
  });

  it("exposes an Angel One account data source", () => {
    const sources = angelOnePlugin.getDataSources?.() ?? [];
    expect(sources[0].id).toBe("angelone-account");
  });

  it("exposes connect + account + halt commands", () => {
    const commands = angelOnePlugin.getCommands?.() ?? [];
    const ids = commands.map((c) => c.id);
    expect(ids).toContain("angelone.connect");
    expect(ids).toContain("angelone.account");
    expect(ids).toContain("angelone.halt");
  });

  it("executeCommand routes connect through /brokers/angelone/connect", async () => {
    fetchMock.mockResolvedValue({ ok: true, text: async () => "{}" });
    await angelOnePlugin.initialize({
      dataDir: "/tmp/angelone",
      settings: {},
      sidecarBaseUrl: "http://127.0.0.1:0",
      hostVersion: "0.5.0",
      secrets: {},
    });
    const result = await angelOnePlugin.executeCommand?.("connect", {
      credentials: { api_key: "k", client_code: "c", password: "p", totp: "123456" },
    });
    expect(result?.ok).toBe(true);
    expect(fetchMock.mock.calls[0][0]).toContain("/brokers/angelone/connect");
  });

  it("executeCommand place-order POSTs the propose endpoint", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      text: async () => JSON.stringify({ proposalId: "abc" }),
    });
    await angelOnePlugin.initialize({
      dataDir: "/tmp/angelone",
      settings: {},
      sidecarBaseUrl: "http://127.0.0.1:0",
      hostVersion: "0.5.0",
      secrets: {},
    });
    const result = await angelOnePlugin.executeCommand?.("place-order", {
      symbol: "HDFCBANK",
      side: "buy",
      type: "limit",
      quantity: 5,
      limitPrice: 100,
      currency: "INR",
      source: "manual",
      sourceDetails: {},
    });
    expect(result?.ok).toBe(true);
    expect(fetchMock.mock.calls[0][0]).toContain("/brokers/angelone/orders");
  });

  it("executeCommand set-mode posts the requested mode", async () => {
    fetchMock.mockResolvedValue({ ok: true, text: async () => "{}" });
    await angelOnePlugin.initialize({
      dataDir: "/tmp/angelone",
      settings: {},
      sidecarBaseUrl: "http://127.0.0.1:0",
      hostVersion: "0.5.0",
      secrets: {},
    });
    await angelOnePlugin.executeCommand?.("set-mode", { mode: "live" });
    const body = JSON.parse(fetchMock.mock.calls[0][1].body as string);
    expect(body.mode).toBe("live");
  });

  it("executeCommand unknown id returns ok:false", async () => {
    await angelOnePlugin.initialize({
      dataDir: "/tmp/angelone",
      settings: {},
      sidecarBaseUrl: "http://127.0.0.1:0",
      hostVersion: "0.5.0",
      secrets: {},
    });
    const result = await angelOnePlugin.executeCommand?.("nope", {});
    expect(result?.ok).toBe(false);
  });
});
