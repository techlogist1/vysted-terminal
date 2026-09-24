/**
 * Marketplace store — the install/enable/configure/remove lifecycle over the
 * plugin runtime (FR-050, US10). It reads each catalog plugin's persisted
 * install/enable state + runtime lifecycle state, and drives transitions:
 *   - install/enable → runtime persists + loads the plugin + attaches its
 *                      panels/commands/agents
 *   - disable        → runtime persists, unloads it + detaches them
 *   - remove         → the same, and marks it not-installed
 * The runtime owns persistence, bridging and agent sync (`pluginHost`); every
 * caller — this store, the Plugin Manager toggle — stays thin.
 *   - configure      → writes BYOK creds to the OS keychain (FR-034/FR-036),
 *                      grants them, and reloads so secrets resolve at use
 * Safety is host-enforced regardless of any plugin (FR-055) — the §6.5 gate
 * governs every mutation; the marketplace only manages plugin lifecycle + creds.
 */

import { create } from "zustand";

import { CATALOG_BY_ID } from "@/lib/marketplace";
import { deleteSecret, getSecret, KEYCHAIN_NAMESPACES, setSecret } from "@/lib/keychain";
import { sidecarGet } from "@/lib/sidecar-client";
import { usePluginsStore } from "@/store/plugins";

import type { MarketplaceEntry, MarketplacePluginState } from "../../types/marketplace";

function secretAccount(entry: MarketplaceEntry, fieldKey: string): string {
  return KEYCHAIN_NAMESPACES.pluginSecret(entry.pluginId, fieldKey);
}

/**
 * R15-DATA-094: NewsAPI silently swallowed a 401 and the key still read as
 * "configured" — probe the key against the sidecar before it is saved so a
 * bad key is rejected at save time instead of three fetches later. Scoped to
 * this one field (the only credential the marketplace currently BYOKs against
 * a probe-able endpoint) rather than a generic per-field probe mechanism
 * nothing else needs yet.
 */
async function probeNewsApiKeyOrThrow(key: string): Promise<void> {
  try {
    const status = await sidecarGet<{ newsapi: string }>("/news/sources/status", undefined, {
      "X-Vysted-Newsapi-Key": key,
    });
    if (status.newsapi === "unauthorized") {
      throw new Error("NewsAPI rejected this key");
    }
  } catch (err) {
    if (err instanceof Error && err.message === "NewsAPI rejected this key") {
      throw err;
    }
    // ponytail: a probe that can't reach the sidecar (offline, cold boot) fails
    // open — only an explicit 401 blocks the save, never a transport hiccup.
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
  /** True while the initial refresh() is in flight (first open of the panel). */
  refreshing: boolean;
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
  refreshing: false,

  refresh: async () => {
    set({ refreshing: true });
    try {
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
      set({ flags, configured, refreshing: false });
    } catch {
      set({ refreshing: false });
    }
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
      await runtime.installPlugin(row.discovered);
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
      await runtime.enablePlugin(row.discovered);
      usePluginsStore.getState().refreshFromRuntime();
      await get().refresh();
    } finally {
      set((s) => ({ busy: { ...s.busy, [pluginId]: false } }));
    }
  },

  disable: async (pluginId) => {
    const runtime = usePluginsStore.getState().runtime;
    if (!runtime) return;
    set((s) => ({ busy: { ...s.busy, [pluginId]: true } }));
    try {
      await runtime.disablePlugin(pluginId);
      usePluginsStore.getState().refreshFromRuntime();
      await get().refresh();
    } finally {
      set((s) => ({ busy: { ...s.busy, [pluginId]: false } }));
    }
  },

  remove: async (pluginId) => {
    const runtime = usePluginsStore.getState().runtime;
    if (!runtime) return;
    set((s) => ({ busy: { ...s.busy, [pluginId]: true } }));
    try {
      await runtime.removePlugin(pluginId);
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
      try {
        for (const field of row.entry.credentialFields ?? []) {
          const account = secretAccount(row.entry, field.key);
          const value = values[field.key];
          if (value && value.length > 0) {
            if (pluginId === "vysted-news" && field.key === "newsapi_key") {
              await probeNewsApiKeyOrThrow(value);
            }
            await setSecret(account, value);
            granted.add(account);
          } else if (!field.required) {
            // An explicitly-emptied optional field clears its secret + grant.
            await deleteSecret(account).catch(() => undefined);
            granted.delete(account);
          }
          // A required field left blank keeps its existing secret + grant untouched.
        }
      } finally {
        // R15-DATA-094: persist whatever grants succeeded even if a later
        // field's probe/write threw — a partial failure must not un-grant
        // secrets that were already written to the keychain. The `finally`
        // re-throws (JS never swallows on a bare `finally`), so the caller
        // still sees the error and skips the enable/reload below.
        await runtime.updateConfig(pluginId, {
          grantedSecretIds: [...granted],
          installed: true,
        });
      }
      const enabled = get().flags[pluginId]?.enabled ?? row.entry.preinstalled;
      if (enabled) {
        // Restart so initialize() receives the new secrets via PluginConfig.secrets.
        await runtime.reloadPlugin(row.discovered);
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
  useMarketplaceStore.setState({ flags: {}, configured: {}, busy: {}, refreshing: false });
}
