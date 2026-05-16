/**
 * Safety store — kill switch state, audit log live tail, disclaimer ack state,
 * static-IP status.
 *
 * BLUEPRINT §6.5 surfaces, in one Zustand store so the toolbar, dialog,
 * disclaimer flow, audit log viewer, and broker-connect banner all read
 * consistent values without N parallel polling loops.
 *
 * Source-of-truth split (matches `types/safety.ts`):
 *
 *   - **Kill switch** — `POST /safety/kill-switch` writes to the sidecar
 *     bus; `GET /safety/kill-switch/status` returns the current state.
 *     The Tauri side emits `kill-switch:requested` from the OS-wide
 *     `Cmd/Ctrl+Shift+K` shortcut (`src-tauri/src/kill_switch.rs`); the
 *     `KillSwitchToolbar` listens and fires the POST.
 *   - **Audit log live tail** — `GET /safety/audit-log?limit=200`, polled
 *     every 2s. Polling beats SSE for v0.5.0 because the safety router
 *     does not (yet) expose an audit-log SSE channel; the audit log is
 *     append-only so a poll-shaped fetch is correct.
 *   - **Disclaimer acks**:
 *       * `first-launch-tos` — persisted in keychain under
 *         `broker:_meta:first-launch-tos`; this store mirrors the read.
 *       * `broker-first-connect` — persisted per broker in keychain under
 *         `broker:<id>:_meta:first-connect-ack`; this store mirrors.
 *       * `first-live-order-this-session` — sidecar-resident
 *         (`GET /safety/disclaimer-status`); resets on sidecar restart.
 *   - **Static-IP status** — `GET /safety/static-ip-status?configured=<ip>`.
 *
 * No `localStorage` / `sessionStorage`. Disclaimer ack reads/writes go through
 * the `KEYCHAIN_NAMESPACES.broker(id, field)` wrapper (`src/lib/keychain.ts`).
 */

import { create } from "zustand";

import { getSecret, KEYCHAIN_NAMESPACES, setSecret } from "@/lib/keychain";
import { getSidecarBaseUrl, sidecarGet } from "@/lib/sidecar-client";

import type { BrokerId } from "../../types/broker";
import type {
  AuditLogAction,
  AuditLogEntry,
  DisclaimerAcknowledgment,
  DisclaimerKind,
  KillSwitchFiredBy,
  KillSwitchFireResult,
  StaticIpStatus,
} from "../../types/safety";

// ---------------------------------------------------------------------------
// Keychain helpers — disclaimer ack persistence
// ---------------------------------------------------------------------------

/** Keychain account for the first-launch TOS ack. */
export const FIRST_LAUNCH_TOS_ACCOUNT = KEYCHAIN_NAMESPACES.broker("_meta", "first-launch-tos");

/** Keychain account for a per-broker first-connect ack. */
export function brokerFirstConnectAccount(broker: BrokerId): string {
  return KEYCHAIN_NAMESPACES.broker(broker, "_meta:first-connect-ack");
}

/** Read whether the user has acked the first-launch TOS. */
export async function hasFirstLaunchTosAck(): Promise<boolean> {
  const value = await getSecret(FIRST_LAUNCH_TOS_ACCOUNT);
  return value !== null && value.length > 0;
}

/** Write the first-launch TOS ack to the keychain (ISO timestamp value). */
export async function recordFirstLaunchTosAck(): Promise<void> {
  await setSecret(FIRST_LAUNCH_TOS_ACCOUNT, new Date().toISOString());
}

/** Read whether the user has acked a broker's first-connect dialog. */
export async function hasBrokerFirstConnectAck(broker: BrokerId): Promise<boolean> {
  const value = await getSecret(brokerFirstConnectAccount(broker));
  return value !== null && value.length > 0;
}

/** Write the per-broker first-connect ack to the keychain. */
export async function recordBrokerFirstConnectAck(broker: BrokerId): Promise<void> {
  await setSecret(brokerFirstConnectAccount(broker), new Date().toISOString());
}

// ---------------------------------------------------------------------------
// Wire shapes (mirror sidecar Pydantic models)
// ---------------------------------------------------------------------------

interface KillSwitchStatusWire {
  fired: boolean;
  lastResult: KillSwitchFireResult | null;
}

interface DisclaimerStatusWire {
  sessionAcks: DisclaimerAcknowledgment[];
}

interface AuditLogTailWire {
  entries: AuditLogEntry[];
}

// ---------------------------------------------------------------------------
// Store state
// ---------------------------------------------------------------------------

export type SafetyLoadStatus = "idle" | "loading" | "ready" | "error";

/** Filter applied to the audit log tail in the viewer. */
export interface AuditLogFilter {
  broker: BrokerId | "_meta" | "all";
  action: AuditLogAction | "all";
  /** Closed range in epoch-ms; `null` means unbounded on that side. */
  startMs: number | null;
  endMs: number | null;
}

export const defaultAuditFilter: AuditLogFilter = {
  broker: "all",
  action: "all",
  startMs: null,
  endMs: null,
};

interface SafetyState {
  // Kill switch
  killSwitchFired: boolean;
  lastKillSwitchResult: KillSwitchFireResult | null;
  killSwitchStatus: SafetyLoadStatus;
  killSwitchError: string | null;

  // Audit log
  auditEntries: AuditLogEntry[];
  auditFilter: AuditLogFilter;
  auditStatus: SafetyLoadStatus;
  auditError: string | null;

  // Disclaimer acks
  firstLaunchTosAcked: boolean;
  brokerFirstConnectAcked: Partial<Record<BrokerId, boolean>>;
  sessionAcks: DisclaimerAcknowledgment[];

  // Static-IP status, last fetched per broker
  staticIpStatus: Record<BrokerId, StaticIpStatus | null>;

  // Actions
  refreshKillSwitchStatus: () => Promise<void>;
  fireKillSwitch: (reason: string, firedBy: KillSwitchFiredBy) => Promise<KillSwitchFireResult>;
  resetKillSwitch: () => Promise<void>;

  refreshAuditLog: (limit?: number) => Promise<void>;
  setAuditFilter: (filter: Partial<AuditLogFilter>) => void;
  filteredAuditEntries: () => AuditLogEntry[];

  refreshFirstLaunchAck: () => Promise<void>;
  ackFirstLaunchTos: () => Promise<void>;
  refreshBrokerFirstConnectAck: (broker: BrokerId) => Promise<void>;
  ackBrokerFirstConnect: (broker: BrokerId) => Promise<void>;

  refreshSessionAcks: () => Promise<void>;
  ackFirstLiveOrderThisSession: (broker: BrokerId) => Promise<DisclaimerAcknowledgment>;
  hasSessionAck: (broker: BrokerId) => boolean;

  refreshStaticIpStatus: (broker: BrokerId, configuredIp: string | null) => Promise<StaticIpStatus>;
}

const EMPTY_STATIC_IP_STATUS: Record<BrokerId, StaticIpStatus | null> = {
  dhan: null,
  angelone: null,
  kite: null,
  alpaca: null,
  ib: null,
  oanda: null,
  "ccxt-bybit": null,
  "ccxt-binance": null,
  "ccxt-kraken": null,
  "ccxt-coinbase": null,
};

export const useSafetyStore = create<SafetyState>((set, get) => ({
  killSwitchFired: false,
  lastKillSwitchResult: null,
  killSwitchStatus: "idle",
  killSwitchError: null,

  auditEntries: [],
  auditFilter: defaultAuditFilter,
  auditStatus: "idle",
  auditError: null,

  firstLaunchTosAcked: false,
  brokerFirstConnectAcked: {},
  sessionAcks: [],

  staticIpStatus: { ...EMPTY_STATIC_IP_STATUS },

  refreshKillSwitchStatus: async () => {
    set({ killSwitchStatus: "loading", killSwitchError: null });
    try {
      const status = await sidecarGet<KillSwitchStatusWire>("/safety/kill-switch/status");
      set({
        killSwitchFired: status.fired,
        lastKillSwitchResult: status.lastResult,
        killSwitchStatus: "ready",
        killSwitchError: null,
      });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "kill-switch status fetch failed";
      set({ killSwitchStatus: "error", killSwitchError: message });
    }
  },

  fireKillSwitch: async (reason, firedBy) => {
    const base = await getSidecarBaseUrl();
    const response = await fetch(new URL("/safety/kill-switch", base).toString(), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reason, firedBy }),
    });
    if (!response.ok) {
      throw new Error(`kill-switch fire failed (${response.status})`);
    }
    const result = (await response.json()) as KillSwitchFireResult;
    set({
      killSwitchFired: true,
      lastKillSwitchResult: result,
      killSwitchStatus: "ready",
      killSwitchError: null,
    });
    return result;
  },

  resetKillSwitch: async () => {
    const base = await getSidecarBaseUrl();
    const response = await fetch(new URL("/safety/kill-switch/reset", base).toString(), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ acknowledged: true }),
    });
    if (!response.ok) {
      throw new Error(`kill-switch reset failed (${response.status})`);
    }
    set({ killSwitchFired: false, lastKillSwitchResult: null });
  },

  refreshAuditLog: async (limit = 200) => {
    set({ auditStatus: "loading", auditError: null });
    try {
      const wire = await sidecarGet<AuditLogTailWire>("/safety/audit-log", { limit });
      set({
        auditEntries: wire.entries,
        auditStatus: "ready",
        auditError: null,
      });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "audit-log fetch failed";
      set({ auditStatus: "error", auditError: message });
    }
  },

  setAuditFilter: (filter) => {
    set((state) => ({ auditFilter: { ...state.auditFilter, ...filter } }));
  },

  filteredAuditEntries: () => {
    const { auditEntries, auditFilter } = get();
    return auditEntries.filter((entry) => {
      if (auditFilter.broker !== "all" && entry.broker !== auditFilter.broker) {
        return false;
      }
      if (auditFilter.action !== "all" && entry.action !== auditFilter.action) {
        return false;
      }
      if (auditFilter.startMs !== null && entry.timestampMs < auditFilter.startMs) {
        return false;
      }
      if (auditFilter.endMs !== null && entry.timestampMs > auditFilter.endMs) {
        return false;
      }
      return true;
    });
  },

  refreshFirstLaunchAck: async () => {
    const acked = await hasFirstLaunchTosAck();
    set({ firstLaunchTosAcked: acked });
  },

  ackFirstLaunchTos: async () => {
    await recordFirstLaunchTosAck();
    set({ firstLaunchTosAcked: true });
  },

  refreshBrokerFirstConnectAck: async (broker) => {
    const acked = await hasBrokerFirstConnectAck(broker);
    set((state) => ({
      brokerFirstConnectAcked: { ...state.brokerFirstConnectAcked, [broker]: acked },
    }));
  },

  ackBrokerFirstConnect: async (broker) => {
    await recordBrokerFirstConnectAck(broker);
    set((state) => ({
      brokerFirstConnectAcked: { ...state.brokerFirstConnectAcked, [broker]: true },
    }));
  },

  refreshSessionAcks: async () => {
    try {
      const wire = await sidecarGet<DisclaimerStatusWire>("/safety/disclaimer-status");
      set({ sessionAcks: wire.sessionAcks });
    } catch {
      // Best-effort: sidecar may not be up yet at first mount.
    }
  },

  ackFirstLiveOrderThisSession: async (broker) => {
    const base = await getSidecarBaseUrl();
    const response = await fetch(new URL("/safety/disclaimer-ack", base).toString(), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        kind: "first-live-order-this-session" as DisclaimerKind,
        broker,
      }),
    });
    if (!response.ok) {
      throw new Error(`disclaimer ack failed (${response.status})`);
    }
    const ack = (await response.json()) as DisclaimerAcknowledgment;
    set((state) => ({ sessionAcks: [...state.sessionAcks, ack] }));
    return ack;
  },

  hasSessionAck: (broker) => {
    return get().sessionAcks.some(
      (ack) => ack.kind === "first-live-order-this-session" && ack.broker === broker,
    );
  },

  refreshStaticIpStatus: async (broker, configuredIp) => {
    const params: { configured?: string } = {};
    if (configuredIp !== null && configuredIp.length > 0) {
      params.configured = configuredIp;
    }
    const status = await sidecarGet<StaticIpStatus>("/safety/static-ip-status", params);
    set((state) => ({
      staticIpStatus: { ...state.staticIpStatus, [broker]: status },
    }));
    return status;
  },
}));

/** Test helper: reset the safety store to its initial shape. */
export function resetSafetyStoreForTests(): void {
  useSafetyStore.setState({
    killSwitchFired: false,
    lastKillSwitchResult: null,
    killSwitchStatus: "idle",
    killSwitchError: null,
    auditEntries: [],
    auditFilter: defaultAuditFilter,
    auditStatus: "idle",
    auditError: null,
    firstLaunchTosAcked: false,
    brokerFirstConnectAcked: {},
    sessionAcks: [],
    staticIpStatus: { ...EMPTY_STATIC_IP_STATUS },
  });
}
