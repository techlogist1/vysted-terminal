/**
 * Plugin bootstrap — drives the marketplace catalog at host startup.
 *
 * Every compiled-in plugin lives in `CATALOG_ROWS` (`src/lib/marketplace.ts`).
 * On boot the runtime DISCOVERS all of them (so they're loadable + visible in
 * the marketplace) but LOADS only those that are installed + enabled — first-
 * party entries are pre-installed by default (populated first run, FR-032); the
 * seven broker entries are available-but-not-pre-installed (FR-051: no broker
 * registered at boot). Install/enable/disable/remove afterwards is driven by
 * `useMarketplaceStore` over the same runtime.
 *
 * The runtime's persistence adapter is wired here to the sidecar `/plugins`
 * endpoint, so per-plugin install/enable/settings survive across launches with
 * no browser storage.
 */

import { CATALOG_ROWS, CATALOG_BY_ID, type CatalogRow } from "@/lib/marketplace";

import type { VystedModule } from "@/lib/module-registry";
import {
  type DiscoveredPlugin,
  type PluginPersistenceAdapter,
  PluginRuntime,
} from "@/lib/plugin-runtime";
import { getSecret } from "@/lib/keychain";
import { getSidecarBaseUrl, sidecarGet, SidecarError } from "@/lib/sidecar-client";
import { useModulesStore } from "@/store/modules";
import { usePluginsStore } from "@/store/plugins";
import { useWorkspaceStore } from "@/store/workspace";

import type { FunctionComponent } from "react";

import type { CommandResult } from "../../types/plugin";
import type { PluginPersistedConfig } from "../../types/plugin-runtime";

/** Host (Vysted Terminal) semver — handed to plugins via `PluginConfig.hostVersion`. */
export const HOST_VERSION = "0.8.0";

/** How often the runtime polls every active plugin's `healthCheck()`. */
const HEALTH_POLL_INTERVAL_MS = 30_000;

interface PluginConfigUpdateBody {
  installed: boolean;
  enabled: boolean;
  settings: Record<string, unknown>;
  granted_secret_ids: string[];
}

interface PluginConfigResponse {
  plugin_id: string;
  installed?: boolean;
  enabled: boolean;
  settings: Record<string, unknown>;
  granted_secret_ids: string[];
}

/** Persistence adapter that proxies the runtime through the sidecar `/plugins` endpoint. */
function createSidecarPersistence(): PluginPersistenceAdapter {
  return {
    async load(pluginId: string): Promise<PluginPersistedConfig | null> {
      try {
        const response = await sidecarGet<PluginConfigResponse>(
          `/plugins/${encodeURIComponent(pluginId)}/config`,
        );
        return {
          pluginId: response.plugin_id,
          // Older sidecars (pre-marketplace) omit `installed`; default true so a
          // config written before the column existed reads as installed.
          installed: response.installed ?? true,
          enabled: response.enabled,
          settings: response.settings ?? {},
          grantedSecretIds: response.granted_secret_ids ?? [],
        };
      } catch (error) {
        if (error instanceof SidecarError && error.status === 404) {
          return null;
        }
        throw error;
      }
    },
    async save(config: PluginPersistedConfig): Promise<void> {
      const base = await getSidecarBaseUrl();
      const url = new URL(`/plugins/${encodeURIComponent(config.pluginId)}/config`, base);
      const body: PluginConfigUpdateBody = {
        installed: config.installed,
        enabled: config.enabled,
        settings: config.settings,
        granted_secret_ids: config.grantedSecretIds,
      };
      const response = await fetch(url.toString(), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!response.ok) {
        throw new SidecarError(response.status, response.statusText);
      }
    },
  };
}

/** Browser-dev fallback: in-memory persistence used outside the Tauri shell. */
function createInMemoryPersistence(): PluginPersistenceAdapter {
  const store = new Map<string, PluginPersistedConfig>();
  return {
    async load(pluginId: string): Promise<PluginPersistedConfig | null> {
      return store.get(pluginId) ?? null;
    },
    async save(config: PluginPersistedConfig): Promise<void> {
      store.set(config.pluginId, { ...config });
    },
  };
}

async function resolvePersistence(): Promise<PluginPersistenceAdapter> {
  try {
    await getSidecarBaseUrl();
    return createSidecarPersistence();
  } catch {
    console.warn(
      "[plugin-bootstrap] no Tauri sidecar detected — falling back to in-memory plugin config persistence",
    );
    return createInMemoryPersistence();
  }
}

/**
 * Build a `VystedModule` surfacing a catalog row's panels + commands through the
 * dockview host + cmd+K palette. Plugins without panels and commands return
 * `null` so the caller skips them. The companion panel components come from the
 * catalog row (the locked contract stays serializable; host glue wires React).
 */
export function moduleForPlugin(row: CatalogRow): VystedModule | null {
  const instance = row.discovered.instance;
  const panels = instance.capabilities.contributesPanels ? (instance.getPanels?.() ?? []) : [];
  const commands = instance.capabilities.contributesCommands
    ? (instance.getCommands?.() ?? [])
    : [];
  if (panels.length === 0 && commands.length === 0) {
    return null;
  }
  const commandHandlers: Record<string, () => void> = {};
  if (instance.capabilities.supportsControlPlane && instance.executeCommand) {
    for (const command of commands) {
      const id = command.commandId;
      if (!id) continue;
      commandHandlers[id] = () => {
        void instance.executeCommand!(id, undefined).then((result: CommandResult) => {
          if (!result.ok) {
            console.warn(`[plugin ${instance.pluginId}] command ${id} failed:`, result.error);
          }
        });
      };
    }
  }
  const panelComponents: Record<string, FunctionComponent> = row.panelComponents
    ? { ...row.panelComponents }
    : {};
  if (panels.length > 0 && Object.keys(panelComponents).length === 0) {
    console.warn(
      `[plugin-bootstrap] plugin ${instance.pluginId} contributes panels but the catalog row has ` +
        `no panelComponents — panels will render without a component.`,
    );
  }
  return {
    id: `plugin:${instance.pluginId}`,
    title: instance.pluginName,
    panels,
    commands,
    panelComponents,
    commandHandlers: Object.keys(commandHandlers).length > 0 ? commandHandlers : undefined,
  };
}

/**
 * Bridge a loaded plugin's panels/commands into the module registry + enable
 * them. Idempotent (`appendModules` de-dupes); used by the boot loop AND the
 * marketplace store on enable/install so a freshly-enabled plugin's panels +
 * commands appear immediately.
 */
export function bridgePluginModule(pluginId: string): void {
  const row = CATALOG_BY_ID[pluginId];
  if (!row) return;
  const mod = moduleForPlugin(row);
  if (!mod) return;
  useModulesStore.getState().appendModules([mod]);
  useModulesStore.getState().setModuleEnabled(mod.id, true);
}

/** Drop a plugin's panels/commands from the registry projections AND close any
 *  of its open dockview panels, so its capabilities disappear cleanly on
 *  disable/remove (US10 AS2). */
export function unbridgePluginModule(pluginId: string): void {
  useModulesStore.getState().setModuleEnabled(`plugin:${pluginId}`, false);
  const row = CATALOG_BY_ID[pluginId];
  const api = useWorkspaceStore.getState().dockviewApi;
  if (!row || !api) return;
  const mod = moduleForPlugin(row);
  const panelIds = new Set((mod?.panels ?? []).map((p) => p.id));
  if (panelIds.size === 0) return;
  // dockview singleton panels keep their spec id; close every open panel of this
  // plugin so no orphan surface lingers after the plugin is gone.
  for (const panel of [...api.panels]) {
    if (panelIds.has(panel.id)) {
      try {
        panel.api.close();
      } catch {
        // dockview may already have disposed it (HMR/StrictMode) — ignore.
      }
    }
  }
}

/**
 * Bootstrap the plugin runtime: build the runtime, attach it to
 * `usePluginsStore`, DISCOVER every catalog plugin, LOAD the installed+enabled
 * ones (first-party pre-installed by default; brokers none), bridge their
 * contributions, and start the health-check loop. Returns a teardown function.
 */
export async function bootstrapPlugins(): Promise<() => void> {
  const persistence = await resolvePersistence();
  const sidecarBaseUrl = await getSidecarBaseUrl().catch((err: unknown) => {
    console.warn(
      "[plugin-bootstrap] sidecar base URL unavailable — plugins start in a degraded, " +
        "unreachable state (port 0); expected outside the Tauri shell.",
      err,
    );
    return "http://127.0.0.1:0";
  });
  const runtime = new PluginRuntime({
    sidecarBaseUrl,
    hostVersion: HOST_VERSION,
    persistence,
    // FR-054/SC-015: resolve a plugin's granted secret ids from the OS keychain
    // at load. Best-effort per id (skip on a keychain miss outside Tauri).
    resolveSecrets: async (ids) => {
      const resolved: Record<string, string> = {};
      for (const id of ids) {
        try {
          const value = await getSecret(id);
          if (value !== null) resolved[id] = value;
        } catch {
          // Keychain unreachable (non-Tauri dev) — skip this secret.
        }
      }
      return resolved;
    },
  });

  const detachStore = usePluginsStore.getState().attachRuntime(runtime);

  for (const row of CATALOG_ROWS) {
    const plugin: DiscoveredPlugin = row.discovered;
    // Always discover so the plugin is loadable + appears in the marketplace.
    runtime.discover(plugin);
    let persisted: PluginPersistedConfig | null = null;
    try {
      persisted = await persistence.load(plugin.manifest.id);
    } catch {
      persisted = null;
    }
    const installed = persisted?.installed ?? row.entry.preinstalled;
    const enabled = persisted?.enabled ?? row.entry.preinstalled;
    if (installed && enabled) {
      await runtime.loadPlugin(plugin);
      const pluginModule = moduleForPlugin(row);
      if (pluginModule) {
        useModulesStore.getState().appendModules([pluginModule]);
      }
    }
  }

  const interval = setInterval(() => {
    void runtime.healthCheckAll();
  }, HEALTH_POLL_INTERVAL_MS);
  void runtime.healthCheckAll();

  return () => {
    clearInterval(interval);
    detachStore();
    for (const row of CATALOG_ROWS) {
      void runtime.unloadPlugin(row.discovered.manifest.id);
    }
  };
}
