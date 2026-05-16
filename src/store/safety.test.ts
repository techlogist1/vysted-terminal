import { beforeEach, describe, expect, it, vi } from "vitest";

import type {
  AuditLogEntry,
  KillSwitchFireResult,
  StaticIpStatus,
} from "../../types/safety";

import * as keychain from "@/lib/keychain";
import * as sidecarClient from "@/lib/sidecar-client";

import {
  brokerFirstConnectAccount,
  defaultAuditFilter,
  FIRST_LAUNCH_TOS_ACCOUNT,
  resetSafetyStoreForTests,
  useSafetyStore,
} from "@/store/safety";

const baseUrl = "http://127.0.0.1:1234";

function stubSidecar(): void {
  vi.spyOn(sidecarClient, "getSidecarBaseUrl").mockResolvedValue(baseUrl);
}

function mockFetchSequence(responses: Array<{ ok: boolean; body: unknown; status?: number }>): void {
  let i = 0;
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => {
      const r = responses[i] ?? { ok: false, body: {}, status: 500 };
      i += 1;
      return {
        ok: r.ok,
        status: r.status ?? (r.ok ? 200 : 500),
        statusText: r.ok ? "OK" : "Error",
        json: async () => r.body,
      } as Response;
    }),
  );
}

function makeAudit(partial: Partial<AuditLogEntry>): AuditLogEntry {
  return {
    id: 1,
    timestampMs: 0,
    broker: "alpaca",
    accountId: "acc-1",
    action: "order-proposed",
    payload: {},
    source: "manual",
    outcome: "ok",
    ...partial,
  };
}

describe("useSafetyStore", () => {
  beforeEach(() => {
    resetSafetyStoreForTests();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    stubSidecar();
  });

  it("starts with the empty default shape", () => {
    const state = useSafetyStore.getState();
    expect(state.killSwitchFired).toBe(false);
    expect(state.lastKillSwitchResult).toBeNull();
    expect(state.auditEntries).toHaveLength(0);
    expect(state.auditFilter).toEqual(defaultAuditFilter);
    expect(state.firstLaunchTosAcked).toBe(false);
    expect(state.brokerFirstConnectAcked).toEqual({});
    expect(state.sessionAcks).toHaveLength(0);
  });

  it("refreshKillSwitchStatus mirrors the sidecar response", async () => {
    vi.spyOn(sidecarClient, "sidecarGet").mockResolvedValueOnce({
      fired: true,
      lastResult: {
        event: { firedAt: 1, reason: "test", firedBy: "user-toolbar" },
        ackTimesMs: { alpaca: 1.5 },
        p50AckMs: 1.5,
        p95AckMs: 1.5,
        maxAckMs: 1.5,
      } satisfies KillSwitchFireResult,
    });
    await useSafetyStore.getState().refreshKillSwitchStatus();
    const state = useSafetyStore.getState();
    expect(state.killSwitchFired).toBe(true);
    expect(state.lastKillSwitchResult?.maxAckMs).toBe(1.5);
    expect(state.killSwitchStatus).toBe("ready");
  });

  it("fireKillSwitch POSTs and updates state", async () => {
    const fireResult: KillSwitchFireResult = {
      event: { firedAt: 5, reason: "panic", firedBy: "user-toolbar" },
      ackTimesMs: { alpaca: 0.4 },
      p50AckMs: 0.4,
      p95AckMs: 0.4,
      maxAckMs: 0.4,
    };
    mockFetchSequence([{ ok: true, body: fireResult }]);
    const result = await useSafetyStore.getState().fireKillSwitch("panic", "user-toolbar");
    expect(result.maxAckMs).toBe(0.4);
    expect(useSafetyStore.getState().killSwitchFired).toBe(true);
  });

  it("refreshAuditLog stores entries and filteredAuditEntries respects filter", async () => {
    const entries = [
      makeAudit({ id: 3, broker: "alpaca", action: "order-placed", timestampMs: 100 }),
      makeAudit({ id: 2, broker: "kite", action: "order-proposed", timestampMs: 80 }),
      makeAudit({ id: 1, broker: "alpaca", action: "order-proposed", timestampMs: 60 }),
    ];
    vi.spyOn(sidecarClient, "sidecarGet").mockResolvedValueOnce({ entries });
    await useSafetyStore.getState().refreshAuditLog();
    expect(useSafetyStore.getState().auditEntries).toHaveLength(3);

    useSafetyStore.getState().setAuditFilter({ broker: "alpaca" });
    expect(useSafetyStore.getState().filteredAuditEntries()).toHaveLength(2);

    useSafetyStore.getState().setAuditFilter({ action: "order-placed" });
    expect(useSafetyStore.getState().filteredAuditEntries()).toHaveLength(1);

    useSafetyStore.getState().setAuditFilter({ action: "all", startMs: 70 });
    expect(useSafetyStore.getState().filteredAuditEntries()).toHaveLength(1);
  });

  it("disclaimer acks: keychain read + write round-trip", async () => {
    const store: Record<string, string> = {};
    vi.spyOn(keychain, "getSecret").mockImplementation(async (account) => store[account] ?? null);
    vi.spyOn(keychain, "setSecret").mockImplementation(async (account, secret) => {
      store[account] = secret;
    });

    expect(FIRST_LAUNCH_TOS_ACCOUNT).toBe("broker:_meta:first-launch-tos");
    expect(brokerFirstConnectAccount("alpaca")).toBe("broker:alpaca:_meta:first-connect-ack");

    await useSafetyStore.getState().refreshFirstLaunchAck();
    expect(useSafetyStore.getState().firstLaunchTosAcked).toBe(false);
    await useSafetyStore.getState().ackFirstLaunchTos();
    expect(useSafetyStore.getState().firstLaunchTosAcked).toBe(true);
    expect(store[FIRST_LAUNCH_TOS_ACCOUNT]).toBeTruthy();

    await useSafetyStore.getState().ackBrokerFirstConnect("alpaca");
    expect(useSafetyStore.getState().brokerFirstConnectAcked.alpaca).toBe(true);
  });

  it("session acks: refresh from sidecar + ack one", async () => {
    vi.spyOn(sidecarClient, "sidecarGet").mockResolvedValueOnce({
      sessionAcks: [{ kind: "first-live-order-this-session", broker: "alpaca", ackedAt: 1 }],
    });
    await useSafetyStore.getState().refreshSessionAcks();
    expect(useSafetyStore.getState().hasSessionAck("alpaca")).toBe(true);
    expect(useSafetyStore.getState().hasSessionAck("kite")).toBe(false);

    mockFetchSequence([
      {
        ok: true,
        body: { kind: "first-live-order-this-session", broker: "kite", ackedAt: 2 },
      },
    ]);
    await useSafetyStore.getState().ackFirstLiveOrderThisSession("kite");
    expect(useSafetyStore.getState().hasSessionAck("kite")).toBe(true);
  });

  it("static-ip status persists in store on refresh", async () => {
    const status: StaticIpStatus = {
      detectedIp: "1.2.3.4",
      configuredIp: "1.2.3.4",
      matches: true,
      message: "matched",
      detectedAt: 0,
    };
    vi.spyOn(sidecarClient, "sidecarGet").mockResolvedValueOnce(status);
    await useSafetyStore.getState().refreshStaticIpStatus("kite", "1.2.3.4");
    expect(useSafetyStore.getState().staticIpStatus.kite?.matches).toBe(true);
  });

  it("never accesses localStorage / sessionStorage", () => {
    const src = useSafetyStore.toString();
    expect(src.includes("localStorage")).toBe(false);
    expect(src.includes("sessionStorage")).toBe(false);
  });
});
