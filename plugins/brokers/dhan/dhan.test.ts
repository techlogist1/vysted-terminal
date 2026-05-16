import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { dhanPlugin } from "./index";
import manifest from "./manifest.json";

import type { PluginManifest } from "../../../types/plugin-runtime";

type FetchMock = ReturnType<typeof vi.fn>;

describe("dhan plugin", () => {
  let fetchMock: FetchMock;

  beforeEach(async () => {
    fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    await dhanPlugin.shutdown();
  });

  afterEach(async () => {
    await dhanPlugin.shutdown();
    vi.unstubAllGlobals();
  });

  it("manifest matches the plugin instance identity", () => {
    const typed = manifest as PluginManifest;
    expect(typed.id).toBe(dhanPlugin.pluginId);
    expect(typed.version).toBe(dhanPlugin.version);
    expect(typed.name).toBe(dhanPlugin.pluginName);
  });

  it("declares data + commands + control plane", () => {
    expect(dhanPlugin.capabilities.contributesData).toBe(true);
    expect(dhanPlugin.capabilities.contributesCommands).toBe(true);
    expect(dhanPlugin.capabilities.supportsControlPlane).toBe(true);
    expect(dhanPlugin.capabilities.contributesPanels).toBe(false);
    expect(dhanPlugin.capabilities.contributesAgents).toBe(false);
    expect(dhanPlugin.capabilities.contributesNodes).toBe(false);
  });

  it("exposes a Dhan account data source", () => {
    const sources = dhanPlugin.getDataSources?.() ?? [];
    expect(sources.length).toBeGreaterThan(0);
    expect(sources[0].id).toBe("dhan-account");
  });

  it("exposes connect + account + halt commands", () => {
    const commands = dhanPlugin.getCommands?.() ?? [];
    const ids = commands.map((c) => c.id);
    expect(ids).toContain("dhan.connect");
    expect(ids).toContain("dhan.account");
    expect(ids).toContain("dhan.halt");
  });

  it("healthCheck reports unavailable before initialize", async () => {
    const status = await dhanPlugin.healthCheck();
    expect(status.status).toBe("unavailable");
  });

  it("executeCommand routes connect through /brokers/dhan/connect", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      text: async () => JSON.stringify({ broker: "dhan", mode: "paper", status: "connected" }),
    });
    await dhanPlugin.initialize({
      dataDir: "/tmp/dhan",
      settings: {},
      sidecarBaseUrl: "http://127.0.0.1:0",
      hostVersion: "0.5.0",
      secrets: {},
    });
    const result = await dhanPlugin.executeCommand?.("connect", {
      credentials: { client_id: "x", access_token: "y" },
    });
    expect(result?.ok).toBe(true);
    const calledUrl = fetchMock.mock.calls[0][0] as string;
    expect(calledUrl).toContain("/brokers/dhan/connect");
  });

  it("executeCommand place-order POSTs to /orders (propose)", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      text: async () => JSON.stringify({ proposalId: "abc", broker: "dhan", symbol: "RELIANCE" }),
    });
    await dhanPlugin.initialize({
      dataDir: "/tmp/dhan",
      settings: {},
      sidecarBaseUrl: "http://127.0.0.1:0",
      hostVersion: "0.5.0",
      secrets: {},
    });
    const result = await dhanPlugin.executeCommand?.("place-order", {
      symbol: "RELIANCE",
      side: "buy",
      type: "limit",
      quantity: 5,
      limitPrice: 100,
      currency: "INR",
      source: "manual",
      sourceDetails: {},
    });
    expect(result?.ok).toBe(true);
    const calledUrl = fetchMock.mock.calls[0][0] as string;
    expect(calledUrl).toContain("/brokers/dhan/orders");
    expect(calledUrl).not.toContain("/confirm");
  });

  it("executeCommand halt-trading sets read-only to true", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      text: async () => JSON.stringify({ broker: "dhan", readOnly: true }),
    });
    await dhanPlugin.initialize({
      dataDir: "/tmp/dhan",
      settings: {},
      sidecarBaseUrl: "http://127.0.0.1:0",
      hostVersion: "0.5.0",
      secrets: {},
    });
    await dhanPlugin.executeCommand?.("halt-trading", {});
    const body = JSON.parse(fetchMock.mock.calls[0][1].body as string);
    expect(body.readOnly).toBe(true);
  });

  it("executeCommand unknown id returns ok:false", async () => {
    await dhanPlugin.initialize({
      dataDir: "/tmp/dhan",
      settings: {},
      sidecarBaseUrl: "http://127.0.0.1:0",
      hostVersion: "0.5.0",
      secrets: {},
    });
    const result = await dhanPlugin.executeCommand?.("nonsense", {});
    expect(result?.ok).toBe(false);
    expect(result?.error).toContain("unknown command");
  });
});
