import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CCXT_BROKER_IDS, ccxtExecPlugin } from "./index";
import manifest from "./manifest.json";

import type { PluginManifest } from "../../../types/plugin-runtime";

type FetchMock = ReturnType<typeof vi.fn>;

describe("ccxt-exec plugin", () => {
  let fetchMock: FetchMock;

  beforeEach(async () => {
    fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    await ccxtExecPlugin.shutdown();
  });

  afterEach(async () => {
    await ccxtExecPlugin.shutdown();
    vi.unstubAllGlobals();
  });

  it("manifest matches the plugin instance identity", () => {
    const typed = manifest as PluginManifest;
    expect(typed.id).toBe(ccxtExecPlugin.pluginId);
    expect(typed.version).toBe(ccxtExecPlugin.version);
    expect(typed.name).toBe(ccxtExecPlugin.pluginName);
  });

  it("declares contributesData and contributesCommands without control plane", () => {
    expect(ccxtExecPlugin.capabilities.contributesData).toBe(true);
    expect(ccxtExecPlugin.capabilities.contributesCommands).toBe(true);
    expect(ccxtExecPlugin.capabilities.contributesPanels).toBe(false);
    expect(ccxtExecPlugin.capabilities.contributesAgents).toBe(false);
    expect(ccxtExecPlugin.capabilities.contributesNodes).toBe(false);
    // §6.5 #6: order placement does NOT route through executeCommand — that
    // path is the safety-layer routes only. The flag stays false.
    expect(ccxtExecPlugin.capabilities.supportsControlPlane).toBe(false);
  });

  it("getDataSources returns one source per ccxt broker id", () => {
    const sources = ccxtExecPlugin.getDataSources?.() ?? [];
    expect(sources.length).toBe(CCXT_BROKER_IDS.length);
    for (const brokerId of CCXT_BROKER_IDS) {
      const match = sources.find((s) => s.id === `${brokerId}-account`);
      expect(match).toBeDefined();
      expect(match?.kinds).toContain("crypto");
    }
  });

  it("getCommands returns one connect command per broker id plus a halt-all", () => {
    const commands = ccxtExecPlugin.getCommands?.() ?? [];
    const connectIds = commands.filter((c) => c.id.startsWith("ccxt-exec.connect."));
    expect(connectIds.length).toBe(CCXT_BROKER_IDS.length);
    for (const brokerId of CCXT_BROKER_IDS) {
      const match = commands.find((c) => c.id === `ccxt-exec.connect.${brokerId}`);
      expect(match).toBeDefined();
      expect(match?.opensPanel).toBe("broker-connect");
    }
    const halt = commands.find((c) => c.id === "ccxt-exec.halt-all");
    expect(halt).toBeDefined();
    expect(halt?.commandId).toBe("ccxt-exec.halt-all");
  });

  it("healthCheck reports unavailable before initialize", async () => {
    const status = await ccxtExecPlugin.healthCheck();
    expect(status.status).toBe("unavailable");
    expect(status.message).toContain("not initialised");
  });

  it("healthCheck reports healthy when /brokers/ccxt-bybit/state returns 200", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({}),
    });
    await ccxtExecPlugin.initialize({
      dataDir: "/tmp/ccxt-exec",
      settings: {},
      sidecarBaseUrl: "http://127.0.0.1:0",
      hostVersion: "0.5.0",
      secrets: {},
    });
    const status = await ccxtExecPlugin.healthCheck();
    expect(status.status).toBe("healthy");
    expect(fetchMock).toHaveBeenCalled();
  });

  it("healthCheck reports degraded on 404 (sidecar up but ccxt registry not yet booted)", async () => {
    fetchMock.mockResolvedValue({
      ok: false,
      status: 404,
    });
    await ccxtExecPlugin.initialize({
      dataDir: "/tmp/ccxt-exec",
      settings: {},
      sidecarBaseUrl: "http://127.0.0.1:0",
      hostVersion: "0.5.0",
      secrets: {},
    });
    const status = await ccxtExecPlugin.healthCheck();
    expect(status.status).toBe("degraded");
    expect(status.message).toContain("ccxt adapters not registered");
  });

  it("healthCheck reports unavailable when the sidecar is unreachable", async () => {
    fetchMock.mockRejectedValue(new Error("ECONNREFUSED"));
    await ccxtExecPlugin.initialize({
      dataDir: "/tmp/ccxt-exec",
      settings: {},
      sidecarBaseUrl: "http://127.0.0.1:0",
      hostVersion: "0.5.0",
      secrets: {},
    });
    const status = await ccxtExecPlugin.healthCheck();
    expect(status.status).toBe("unavailable");
    expect(status.message).toContain("Sidecar unreachable");
  });

  it("executeCommand rejects unknown command ids", async () => {
    fetchMock.mockResolvedValue({ ok: true, status: 200, json: async () => ({}) });
    await ccxtExecPlugin.initialize({
      dataDir: "/tmp/ccxt-exec",
      settings: {},
      sidecarBaseUrl: "http://127.0.0.1:0",
      hostVersion: "0.5.0",
      secrets: {},
    });
    const result = await ccxtExecPlugin.executeCommand?.("does.not.exist", undefined);
    expect(result?.ok).toBe(false);
    expect(result?.error).toContain("unknown command");
  });

  it("executeCommand('ccxt-exec.halt-all') POSTs the kill-switch endpoint", async () => {
    // The initialize health-probe consumes the first fetch call;
    // the halt-all command consumes the second.
    fetchMock
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({}) })
      .mockResolvedValueOnce({ ok: true, status: 200 });
    await ccxtExecPlugin.initialize({
      dataDir: "/tmp/ccxt-exec",
      settings: {},
      sidecarBaseUrl: "http://127.0.0.1:0",
      hostVersion: "0.5.0",
      secrets: {},
    });
    const result = await ccxtExecPlugin.executeCommand?.("ccxt-exec.halt-all", undefined);
    expect(result?.ok).toBe(true);
    const lastCall = fetchMock.mock.calls.at(-1);
    expect(lastCall?.[0]).toContain("/safety/kill-switch");
    expect(lastCall?.[1]?.method).toBe("POST");
    const data = result?.data as { halted: boolean; brokerIds: string[] };
    expect(data.halted).toBe(true);
    expect(data.brokerIds).toEqual([...CCXT_BROKER_IDS]);
  });

  it("executeCommand('ccxt-exec.halt-all') surfaces sidecar failure as ok=false", async () => {
    fetchMock
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({}) })
      .mockResolvedValueOnce({ ok: false, status: 500 });
    await ccxtExecPlugin.initialize({
      dataDir: "/tmp/ccxt-exec",
      settings: {},
      sidecarBaseUrl: "http://127.0.0.1:0",
      hostVersion: "0.5.0",
      secrets: {},
    });
    const result = await ccxtExecPlugin.executeCommand?.("ccxt-exec.halt-all", undefined);
    expect(result?.ok).toBe(false);
    expect(result?.error).toContain("500");
  });
});
