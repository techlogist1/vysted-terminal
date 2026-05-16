import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { _setAdapterForTests, type TradingBotReadAdapter } from "./connection";
import { tradesaPlugin } from "./index";
import manifest from "./manifest.json";
import { useTradesaStore } from "./store";

import type { PluginManifest } from "../../types/plugin-runtime";
import type { TradesaConnectionState } from "../../types/tradesa_v2";

// ---------------------------------------------------------------------------
// Stub adapter
// ---------------------------------------------------------------------------

function makeStubAdapter(
  overrides: Partial<TradingBotReadAdapter> = {},
): TradingBotReadAdapter {
  const defaultState: TradesaConnectionState = {
    status: "healthy",
    message: "ok",
    checked_at: 0,
    last_heartbeat_at: 0,
    heartbeat_age_s: 10,
    bot_mode: "paper",
    kill_switch_engaged: false,
  };
  const probe = vi.fn(async () => defaultState);
  return {
    probeStatus: probe,
    listOpenPositions: vi.fn(async () => []),
    listClosedTrades: vi.fn(async () => []),
    listDecisions: vi.fn(async () => []),
    listMetaAgentRuns: vi.fn(async () => []),
    getCostToday: vi.fn(async () => ({
      date: "2026-05-17",
      by_model: {},
      total_usd: 0,
    })),
    getHealth: vi.fn(async () => ({
      latest: null,
      recent_kill_switch_events: [],
    })),
    listKillSwitchEvents: vi.fn(async () => []),
    listSentinelBlocks: vi.fn(async () => []),
    listSettings: vi.fn(async () => []),
    getSettingsDrift: vi.fn(async () => []),
    listTuningProposals: vi.fn(async () => []),
    listDiscoveryHypotheses: vi.fn(async () => []),
    listReflectionNotes: vi.fn(async () => []),
    ...overrides,
  };
}

beforeEach(() => {
  _setAdapterForTests(makeStubAdapter());
});

afterEach(() => {
  _setAdapterForTests(null);
  useTradesaStore.getState().reset();
});

// ---------------------------------------------------------------------------
// Identity
// ---------------------------------------------------------------------------

describe("tradesa-v2 plugin identity", () => {
  it("manifest matches plugin instance identity", () => {
    const typed = manifest as PluginManifest;
    expect(typed.id).toBe(tradesaPlugin.pluginId);
    expect(typed.version).toBe(tradesaPlugin.version);
    expect(typed.name).toBe(tradesaPlugin.pluginName);
  });

  it("plugin id is the canonical kebab-case 'tradesa-v2'", () => {
    expect(tradesaPlugin.pluginId).toBe("tradesa-v2");
  });

  it("pluginType is 'trading-bot'", () => {
    expect(tradesaPlugin.pluginType).toBe("trading-bot");
  });
});

// ---------------------------------------------------------------------------
// Capability negotiation — v0.6.5 READ-ONLY contract
// ---------------------------------------------------------------------------

describe("tradesa-v2 capability flags (v0.6.5 read-only)", () => {
  it("contributes data + panels + commands", () => {
    expect(tradesaPlugin.capabilities.contributesData).toBe(true);
    expect(tradesaPlugin.capabilities.contributesPanels).toBe(true);
    expect(tradesaPlugin.capabilities.contributesCommands).toBe(true);
  });

  it("does NOT contribute agents or nodes (v0.6.5 scope)", () => {
    expect(tradesaPlugin.capabilities.contributesAgents).toBe(false);
    expect(tradesaPlugin.capabilities.contributesNodes).toBe(false);
  });

  it("does NOT support control plane — enforces READ-ONLY (audit invariant)", () => {
    // supportsControlPlane=false means the runtime never calls
    // executeCommand on this plugin even if such a method existed.
    expect(tradesaPlugin.capabilities.supportsControlPlane).toBe(false);
    expect(tradesaPlugin.executeCommand).toBeUndefined();
  });

  it("declares no real-time subscribe surface", () => {
    expect(tradesaPlugin.subscribe).toBeUndefined();
  });
});

// ---------------------------------------------------------------------------
// Contributions
// ---------------------------------------------------------------------------

describe("tradesa-v2 contributions", () => {
  it("getDataSources returns 3 read-only data sources", () => {
    const sources = tradesaPlugin.getDataSources?.() ?? [];
    expect(sources).toHaveLength(3);
    expect(sources.map((s) => s.id).sort()).toEqual([
      "tradesa-v2-decisions",
      "tradesa-v2-health",
      "tradesa-v2-trades",
    ]);
    // None of the data sources advertise realtime (v0.6.5 ships polling-only).
    expect(sources.every((s) => s.realtime === false)).toBe(true);
  });

  it("getPanels returns the 7 v0.6.5 panels", () => {
    const panels = tradesaPlugin.getPanels?.() ?? [];
    expect(panels.map((p) => p.id).sort()).toEqual([
      "tradesa-v2.brain",
      "tradesa-v2.health",
      "tradesa-v2.meta-agents",
      "tradesa-v2.positions",
      "tradesa-v2.sentinel",
      "tradesa-v2.settings",
      "tradesa-v2.trade-history",
    ]);
  });

  it("every panel id and command opensPanel match between getPanels and getCommands", () => {
    const panels = tradesaPlugin.getPanels?.() ?? [];
    const commands = tradesaPlugin.getCommands?.() ?? [];
    const panelIds = new Set(panels.map((p) => p.id));
    for (const command of commands) {
      if (command.opensPanel) {
        expect(panelIds).toContain(command.opensPanel);
      }
    }
  });

  it("every panel has a singleton flag (one of each visible at a time)", () => {
    const panels = tradesaPlugin.getPanels?.() ?? [];
    expect(panels.every((p) => p.singleton === true)).toBe(true);
  });

  it("getCommands returns one command per panel (7 cmd+K entries)", () => {
    const commands = tradesaPlugin.getCommands?.() ?? [];
    expect(commands).toHaveLength(7);
    // Every command opens a panel (none execute control-plane commands —
    // that would imply write capability).
    expect(commands.every((c) => Boolean(c.opensPanel))).toBe(true);
    expect(commands.every((c) => !c.commandId)).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// Lifecycle
// ---------------------------------------------------------------------------

describe("tradesa-v2 lifecycle", () => {
  const baseConfig = {
    dataDir: "/tmp/tradesa-v2",
    settings: {},
    sidecarBaseUrl: "http://127.0.0.1:0",
    hostVersion: "0.6.5",
    secrets: {},
  };

  it("healthCheck is unavailable before initialize", async () => {
    await tradesaPlugin.shutdown();
    const before = await tradesaPlugin.healthCheck();
    expect(before.status).toBe("unavailable");
  });

  it("initialize probes the adapter and sets connection state", async () => {
    await tradesaPlugin.shutdown();
    await tradesaPlugin.initialize(baseConfig);
    const probe = useTradesaStore.getState().connection;
    expect(probe?.status).toBe("healthy");
  });

  it("healthCheck maps probe status to host-side HealthStatus", async () => {
    await tradesaPlugin.shutdown();
    await tradesaPlugin.initialize(baseConfig);
    const health = await tradesaPlugin.healthCheck();
    expect(health.status).toBe("healthy");
  });

  it("healthCheck maps 'bot-offline' to degraded", async () => {
    _setAdapterForTests(
      makeStubAdapter({
        probeStatus: vi.fn(
          async (): Promise<TradesaConnectionState> => ({
            status: "bot-offline",
            message: "stale heartbeat",
            checked_at: 0,
            last_heartbeat_at: 0,
            heartbeat_age_s: 600,
            bot_mode: "paper",
            kill_switch_engaged: false,
          }),
        ),
      }),
    );
    await tradesaPlugin.shutdown();
    await tradesaPlugin.initialize(baseConfig);
    const health = await tradesaPlugin.healthCheck();
    expect(health.status).toBe("degraded");
  });

  it("healthCheck maps 'supabase-error' to unavailable", async () => {
    _setAdapterForTests(
      makeStubAdapter({
        probeStatus: vi.fn(
          async (): Promise<TradesaConnectionState> => ({
            status: "supabase-error",
            message: "auth failed",
            checked_at: 0,
            last_heartbeat_at: null,
            heartbeat_age_s: null,
            bot_mode: null,
            kill_switch_engaged: null,
          }),
        ),
      }),
    );
    await tradesaPlugin.shutdown();
    await tradesaPlugin.initialize(baseConfig);
    const health = await tradesaPlugin.healthCheck();
    expect(health.status).toBe("unavailable");
  });

  it("healthCheck maps 'unauthenticated' to unavailable", async () => {
    _setAdapterForTests(
      makeStubAdapter({
        probeStatus: vi.fn(
          async (): Promise<TradesaConnectionState> => ({
            status: "unauthenticated",
            message: "no creds",
            checked_at: 0,
            last_heartbeat_at: null,
            heartbeat_age_s: null,
            bot_mode: null,
            kill_switch_engaged: null,
          }),
        ),
      }),
    );
    await tradesaPlugin.shutdown();
    await tradesaPlugin.initialize(baseConfig);
    const health = await tradesaPlugin.healthCheck();
    expect(health.status).toBe("unavailable");
  });

  it("initialize tolerates an adapter that throws (graceful degradation)", async () => {
    _setAdapterForTests(
      makeStubAdapter({
        probeStatus: vi.fn(async () => {
          throw new Error("network down");
        }),
      }),
    );
    await tradesaPlugin.shutdown();
    await tradesaPlugin.initialize(baseConfig);
    const health = await tradesaPlugin.healthCheck();
    expect(health.status).toBe("unavailable");
    expect(health.message).toContain("network down");
  });

  it("shutdown resets store and lifecycle state", async () => {
    await tradesaPlugin.initialize(baseConfig);
    expect(useTradesaStore.getState().connection).not.toBeNull();
    await tradesaPlugin.shutdown();
    expect(useTradesaStore.getState().connection).toBeNull();
  });
});
