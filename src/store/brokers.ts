/**
 * Brokers store — connection state aggregator for the broker-connect panel.
 *
 * Reads `GET /brokers` (Teammate I owns the route + the ccxt sub-list when X
 * lands) and `GET /brokers/{id}/state` for per-broker state, then maintains
 * a typed snapshot keyed by `BrokerId`. The `BrokerConnectPanel` and the
 * `BrokerOrderEntry` surface both read from here.
 *
 * Credentials NEVER live in this store — credential reads/writes go through
 * `KEYCHAIN_NAMESPACES.broker(id, field)` (`src/lib/keychain.ts`) and only
 * hit this store as a transient `connect()` argument that lives only on the
 * call stack.
 */

import { create } from "zustand";

import { getSidecarBaseUrl, sidecarGet } from "@/lib/sidecar-client";

import type { BrokerId, BrokerMode, BrokerState } from "../../types/broker";

interface BrokersListWire {
  brokers: BrokerState[];
}

export type BrokersLoadStatus = "idle" | "loading" | "ready" | "error";

interface BrokersStoreState {
  byId: Partial<Record<BrokerId, BrokerState>>;
  status: BrokersLoadStatus;
  error: string | null;

  refresh: () => Promise<void>;
  refreshOne: (broker: BrokerId) => Promise<BrokerState | null>;
  connect: (broker: BrokerId, credentials: Record<string, string>) => Promise<void>;
  disconnect: (broker: BrokerId) => Promise<void>;
  setMode: (broker: BrokerId, mode: BrokerMode) => Promise<void>;
  setReadOnly: (broker: BrokerId, readOnly: boolean) => Promise<void>;

  brokers: () => BrokerState[];
  cryptoBrokers: () => BrokerState[];
  primaryBrokers: () => BrokerState[];
}

function isCryptoBrokerId(id: BrokerId): boolean {
  return id.startsWith("ccxt-");
}

export const useBrokersStore = create<BrokersStoreState>((set, get) => ({
  byId: {},
  status: "idle",
  error: null,

  refresh: async () => {
    set({ status: "loading", error: null });
    try {
      const wire = await sidecarGet<BrokersListWire>("/brokers");
      const byId: Partial<Record<BrokerId, BrokerState>> = {};
      for (const state of wire.brokers) {
        byId[state.broker] = state;
      }
      set({ byId, status: "ready", error: null });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "brokers list fetch failed";
      set({ status: "error", error: message });
    }
  },

  refreshOne: async (broker) => {
    try {
      const state = await sidecarGet<BrokerState>(
        `/brokers/${encodeURIComponent(broker)}/state`,
      );
      set((s) => ({ byId: { ...s.byId, [broker]: state } }));
      return state;
    } catch {
      return null;
    }
  },

  connect: async (broker, credentials) => {
    const base = await getSidecarBaseUrl();
    const response = await fetch(
      new URL(`/brokers/${encodeURIComponent(broker)}/connect`, base).toString(),
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ credentials }),
      },
    );
    if (!response.ok) {
      throw new Error(`connect failed (${response.status})`);
    }
    await get().refreshOne(broker);
  },

  disconnect: async (broker) => {
    const base = await getSidecarBaseUrl();
    const response = await fetch(
      new URL(`/brokers/${encodeURIComponent(broker)}/disconnect`, base).toString(),
      { method: "POST" },
    );
    if (!response.ok) {
      throw new Error(`disconnect failed (${response.status})`);
    }
    await get().refreshOne(broker);
  },

  setMode: async (broker, mode) => {
    const base = await getSidecarBaseUrl();
    const response = await fetch(
      new URL(`/brokers/${encodeURIComponent(broker)}/mode`, base).toString(),
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode }),
      },
    );
    if (!response.ok) {
      throw new Error(`set-mode failed (${response.status})`);
    }
    await get().refreshOne(broker);
  },

  setReadOnly: async (broker, readOnly) => {
    const base = await getSidecarBaseUrl();
    const response = await fetch(
      new URL(`/brokers/${encodeURIComponent(broker)}/read-only`, base).toString(),
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ readOnly }),
      },
    );
    if (!response.ok) {
      throw new Error(`set-read-only failed (${response.status})`);
    }
    await get().refreshOne(broker);
  },

  brokers: () => {
    const map = get().byId;
    return Object.values(map).filter((s): s is BrokerState => s !== undefined);
  },

  primaryBrokers: () => get().brokers().filter((s) => !isCryptoBrokerId(s.broker)),

  cryptoBrokers: () => get().brokers().filter((s) => isCryptoBrokerId(s.broker)),
}));

/** Test helper: reset the brokers store. */
export function resetBrokersStoreForTests(): void {
  useBrokersStore.setState({ byId: {}, status: "idle", error: null });
}
