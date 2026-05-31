/**
 * Marketplace store — the install/enable/configure/remove lifecycle over the
 * plugin runtime (FR-050, US10). It reads each catalog plugin's persisted
 * install/enable state + runtime lifecycle state, and drives transitions:
 *   - install/enable → runtime loads the plugin + bridges its panels/commands
 *   - disable        → runtime unloads it + its panels/commands drop
 *   - remove         → runtime unloads + marks not-installed
 *   - configure      → writes BYOK creds to the OS keychain (FR-034/FR-036),
 *                      grants them, and reloads so secrets resolve at use
 * Safety is host-enforced regardless of any plugin (FR-055) — the §6.5 gate
 * governs every mutation; the marketplace only manages plugin lifecycle + creds.
 */

import { create } from "zustand";

import { CATALOG_BY_ID } from "@/lib/marketplace";
import { bridgePluginModule, unbridgePluginModule } from "@/lib/plugin-bootstrap";
import { deleteSecret, getSecret, KEYCHAIN_NAMESPACES, setSecret } from "@/lib/keychain";
import { syncPluginAgents } from "@/lib/plugin-agents";
import { getSidecarBaseUrl } from "@/lib/sidecar-client";
import { usePluginsStore } from "@/store/plugins";

import type { MarketplaceEntry, MarketplacePluginState } from "../../types/marketplace";

function secretAccount(entry: MarketplaceEntry, fieldKey: string): string {
  if (entry.secretNamespace === "broker" && entry.brokerId) {
    return KEYCHAIN_NAMESPACES.broker(entry.brokerId, fieldKey);
  }
  return KEYCHAIN_NAMESPACES.pluginSecret(entry.pluginId, fieldKey);
}

/** Disconnect a broker plugin's sidecar adapter (best-effort) on disable/remove
 *  so the adapter doesn't linger "connected" after the plugin is gone. */
async function disconnectBroker(entry: MarketplaceEntry): Promise<void> {
  if (entry.category !== "broker" || !entry.brokerId) return;
  try {
    const base = await getSidecarBaseUrl();
    await fetch(
      new URL(`/brokers/${encodeURIComponent(entry.brokerId)}/disconnect`, base).toString(),
      { method: "POST" },
    );
  } catch {
    // Best-effort — a transient failure or already-disconnected is non-fatal.
  }
}

interface PersistedFlags {
  installed: boolean;
  enabled: boolean;
}

interface MarketplaceState {
  /** Per-plugin install/enable flags (persisted config merged with catalog defaults). */
  flags: Record<string, PersistedFlags>;
  /** Per-plugin "all required credential fields have a stored value". */
  configured: Record<string, boolean>;
  /** Per-plugin in-flight guard so a double-click can't double-transition. */
  busy: Record<string, boolean>;
  refresh: () => Promise<void>;
  stateFor: (pluginId: string) => MarketplacePluginState;
  install: (pluginId: string) => Promise<void>;
  enable: (pluginId: string) => Promise<void>;
  disable: (pluginId: string) => Promise<void>;
  remove: (pluginId: string) => Promise<void>;
  configure: (pluginId: string, values: Record<string, string>) => Promise<void>;
}

async function isConfigured(entry: MarketplaceEntry): Promise<boolean> {
  const required = (entry.credentialFields ?? []).filter((f) => f.required);
  if (required.length === 0) return true;
  for (const field of required) {
    try {
      const value = await getSecret(secretAccount(entry, field.key));
      if (!value) return false;
    } catch {
      return false;
    }
  }
  return true;
}

export const useMarketplaceStore = create<MarketplaceState>((set, get) => ({
  flags: {},
  configured: {},
  busy: {},

  refresh: async () => {
    const runtime = usePluginsStore.getState().runtime;
    const rows = Object.values(CATALOG_BY_ID);
    const flags: Record<string, PersistedFlags> = {};
    const configured: Record<string, boolean> = {};
    await Promise.all(
      rows.map(async (row) => {
        const id = row.entry.pluginId;
        let persisted = null;
        if (runtime) {
          try {
            persisted = await runtime.readConfig(id);
          } catch {
            persisted = null;
          }
        }
        flags[id] = {
          installed: persisted?.installed ?? row.entry.preinstalled,
          enabled: persisted?.enabled ?? row.entry.preinstalled,
        };
        configured[id] = await isConfigured(row.entry);
      }),
    );
    set({ flags, configured });
  },

  stateFor: (pluginId) => {
    const row = CATALOG_BY_ID[pluginId];
    const flags = get().flags[pluginId] ?? {
      installed: row?.entry.preinstalled ?? false,
      enabled: row?.entry.preinstalled ?? false,
    };
    const record = usePluginsStore.getState().plugins.find((p) => p.manifest.id === pluginId);
    return {
      pluginId,
      installed: flags.installed,
      enabled: flags.enabled,
      runtimeState: record?.state,
      configured: get().configured[pluginId] ?? false,
      errorMessage: record?.errorMessage,
    };
  },

  install: async (pluginId) => {
    const row = CATALOG_BY_ID[pluginId];
    const runtime = usePluginsStore.getState().runtime;
    if (!row || !runtime) return;
    set((s) => ({ busy: { ...s.busy, [pluginId]: true } }));
    try {
      const snap = await runtime.installPlugin(row.discovered);
      // Only bridge panels/commands if the plugin actually loaded — a compat
      // rejection (FR-054) leaves it in `error`/`stopped` and contributes nothing.
      if (snap.state === "active") {
        bridgePluginModule(pluginId);
        await syncPluginAgents(pluginId, true);
      }
      usePluginsStore.getState().refreshFromRuntime();
      await get().refresh();
    } finally {
      set((s) => ({ busy: { ...s.busy, [pluginId]: false } }));
    }
  },

  enable: async (pluginId) => {
    const row = CATALOG_BY_ID[pluginId];
    const runtime = usePluginsStore.getState().runtime;
    if (!row || !runtime) return;
    set((s) => ({ busy: { ...s.busy, [pluginId]: true } }));
    try {
      const snap = await runtime.enablePlugin(row.discovered);
      if (snap.state === "active") {
        bridgePluginModule(pluginId);
        await syncPluginAgents(pluginId, true);
      }
      usePluginsStore.getState().refreshFromRuntime();
      await get().refresh();
    } finally {
      set((s) => ({ busy: { ...s.busy, [pluginId]: false } }));
    }
  },

  disable: async (pluginId) => {
    const row = CATALOG_BY_ID[pluginId];
    const runtime = usePluginsStore.getState().runtime;
    if (!runtime) return;
    set((s) => ({ busy: { ...s.busy, [pluginId]: true } }));
    try {
      await runtime.disablePlugin(pluginId);
      unbridgePluginModule(pluginId);
      await syncPluginAgents(pluginId, false);
      if (row) await disconnectBroker(row.entry);
      usePluginsStore.getState().refreshFromRuntime();
      await get().refresh();
    } finally {
      set((s) => ({ busy: { ...s.busy, [pluginId]: false } }));
    }
  },

  remove: async (pluginId) => {
    const row = CATALOG_BY_ID[pluginId];
    const runtime = usePluginsStore.getState().runtime;
    if (!runtime) return;
    set((s) => ({ busy: { ...s.busy, [pluginId]: true } }));
    try {
      await runtime.removePlugin(pluginId);
      unbridgePluginModule(pluginId);
      await syncPluginAgents(pluginId, false);
      if (row) await disconnectBroker(row.entry);
      usePluginsStore.getState().refreshFromRuntime();
      await get().refresh();
    } finally {
      set((s) => ({ busy: { ...s.busy, [pluginId]: false } }));
    }
  },

  configure: async (pluginId, values) => {
    const row = CATALOG_BY_ID[pluginId];
    const runtime = usePluginsStore.getState().runtime;
    if (!row || !runtime) return;
    set((s) => ({ busy: { ...s.busy, [pluginId]: true } }));
    try {
      // MERGE with the existing grants — a partial re-configure (submitting only
      // some fields) must not wipe previously-stored secrets (FR-036).
      const current = await runtime.readConfig(pluginId);
      const granted = new Set(current?.grantedSecretIds ?? []);
      for (const field of row.entry.credentialFields ?? []) {
        const account = secretAccount(row.entry, field.key);
        const value = values[field.key];
        if (value && value.length > 0) {
          await setSecret(account, value);
          granted.add(account);
        } else if (!field.required) {
          // An explicitly-emptied optional field clears its secret + grant.
          await deleteSecret(account).catch(() => undefined);
          granted.delete(account);
        }
        // A required field left blank keeps its existing secret + grant untouched.
      }
      await runtime.updateConfig(pluginId, {
        grantedSecretIds: [...granted],
        installed: true,
      });
      const enabled = get().flags[pluginId]?.enabled ?? row.entry.preinstalled;
      if (enabled) {
        // Reload so the plugin resolves the new secrets via PluginConfig.secrets.
        const snap = await runtime.enablePlugin(row.discovered);
        if (snap.state === "active") {
          bridgePluginModule(pluginId);
        }
      }
      usePluginsStore.getState().refreshFromRuntime();
      await get().refresh();
    } finally {
      set((s) => ({ busy: { ...s.busy, [pluginId]: false } }));
    }
  },
}));

/** Test helper: reset the marketplace store. */
export function resetMarketplaceStoreForTests(): void {
  useMarketplaceStore.setState({ flags: {}, configured: {}, busy: {} });
}
