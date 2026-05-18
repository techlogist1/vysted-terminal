/**
 * Plugin bootstrap — discovers, loads, and wires bundled plugins into the
 * runtime + the React-facing stores at host startup.
 *
 * This is the Phase-2 "bundled-import loader" (decision A1): bundled plugins
 * live under `plugins/<id>/`, exporting a `VystedPlugin` instance the host
 * imports statically. The bootstrap runs once on mount; tests can build their
 * own runtime without going through this entry.
 *
 * The runtime's persistence adapter is wired here to the sidecar `/plugins`
 * endpoint, so per-plugin config survives across launches without any browser
 * storage.
 */

import { examplePlugin } from "../../plugins/example";
import exampleManifest from "../../plugins/example/manifest.json";
import { openbbMcpPlugin } from "../../plugins/openbb-mcp";
import openbbMcpManifest from "../../plugins/openbb-mcp/manifest.json";
import { tradesaPlugin } from "../../plugins/tradesa-v2";
import tradesaManifest from "../../plugins/tradesa-v2/manifest.json";
import tradesaPanelComponents from "../../plugins/tradesa-v2/panels";

import type { VystedModule } from "@/lib/module-registry";
import {
  type DiscoveredPlugin,
  type PluginPersistenceAdapter,
  PluginRuntime,
} from "@/lib/plugin-runtime";
import { getSidecarBaseUrl, sidecarGet, SidecarError } from "@/lib/sidecar-client";
import { useModulesStore } from "@/store/modules";
import { usePluginsStore } from "@/store/plugins";

import type { FunctionComponent } from "react";

import type { CommandResult } from "../../types/plugin";
import type { PluginManifest, PluginPersistedConfig } from "../../types/plugin-runtime";

/** Host (Vysted Terminal) semver — handed to plugins via `PluginConfig.hostVersion`. */
const HOST_VERSION = "0.8.0";

/** How often the runtime polls every active plugin's `healthCheck()`. */
const HEALTH_POLL_INTERVAL_MS = 30_000;

/** Bundled-import discovery list. New first-party plugins append here. */
const BUNDLED_PLUGINS: DiscoveredPlugin[] = [
  { manifest: exampleManifest as PluginManifest, instance: examplePlugin },
  { manifest: openbbMcpManifest as PluginManifest, instance: openbbMcpPlugin },
  { manifest: tradesaManifest as PluginManifest, instance: tradesaPlugin },
];

/**
 * Per-plugin companion panel-components map.
 *
 * Plugins that contribute panels ship a ``plugins/<id>/panels.ts`` file
 * exporting a ``Record<string, FunctionComponent>`` mapping each
 * ``PanelSpec.component`` id to the React component dockview renders.
 * This is the **"Trading-System Wrapper" plugin pattern** documented in
 * ``docs/PLUGIN_DEVELOPMENT.md``: the locked ``VystedPlugin`` contract
 * stays serializable (no React types leak in), and host-side glue
 * (this map) wires the companion components.
 *
 * The map is static at the host-build level (not dynamic-imported at
 * runtime) because Next.js static export can't resolve plugin-id-based
 * dynamic imports without filesystem-installed plugins (a v0.7+ scope
 * decision). First-party plugins are bundled into the host build; this
 * mirrors how ``BUNDLED_PLUGINS`` above already statically imports
 * each plugin's ``index.ts``.
 *
 * To add a new plugin with panels:
 *   1. Write ``plugins/<id>/index.ts`` exporting a ``VystedPlugin``.
 *   2. Write ``plugins/<id>/panels.ts`` exporting a
 *      ``Record<string, FunctionComponent>``.
 *   3. Add the plugin to ``BUNDLED_PLUGINS`` above.
 *   4. Add the entry below mapping ``manifest.id`` →
 *      ``{ panelComponents: <plugin>PanelComponents }``.
 *
 * Plugins that don't contribute panels (the ``example`` data-source
 * plugin, the ``openbb-mcp`` plugin) are omitted here; ``moduleForPlugin``
 * tolerates absence gracefully.
 */
const PLUGIN_COMPANIONS: Record<string, { panelComponents: Record<string, FunctionComponent> }> = {
  "tradesa-v2": { panelComponents: tradesaPanelComponents },
};

interface PluginConfigUpdateBody {
  enabled: boolean;
  settings: Record<string, unknown>;
  granted_secret_ids: string[];
}

interface PluginConfigResponse {
  plugin_id: string;
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
          enabled: response.enabled,
          settings: response.settings ?? {},
          grantedSecretIds: response.granted_secret_ids ?? [],
        };
      } catch (error) {
        // 404 is the "never persisted yet" path — treat it as null so the
        // runtime falls back to the default config and writes it back.
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

/**
 * Browser-dev fallback: in-memory persistence used when the host runs outside
 * Tauri (e.g. `pnpm dev` for visual verification). Plugins still load and
 * surface their capabilities; settings just don't survive a refresh. This
 * keeps the dev workflow honest — the runtime behaves the same shape, only
 * the persistence layer is swapped.
 */
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

/**
 * Resolve the persistence adapter for the current environment. Tauri runs
 * the sidecar so we use the sidecar-backed adapter; a browser-only
 * `pnpm dev` falls back to in-memory persistence so the runtime still works
 * for visual verification and module-level smoke tests.
 */
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
 * Builds a `VystedModule` that surfaces a plugin's contributed panels and
 * commands through the existing dockview host + cmd+K palette. This is how
 * plugin contributions reach the rest of the app — there is no second
 * registry the host has to special-case.
 *
 * Plugins without panels and without commands return `null` so the caller
 * skips them; appending an empty module would still create a settings row
 * for it, which is misleading.
 */
function moduleForPlugin(plugin: DiscoveredPlugin): VystedModule | null {
  const instance = plugin.instance;
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
        // Fire-and-forget: command palette execution is synchronous from the
        // user's perspective; the plugin owns any UI feedback. Errors are
        // logged so the dev console captures them.
        void instance.executeCommand!(id, undefined).then((result: CommandResult) => {
          if (!result.ok) {
            console.warn(`[plugin ${instance.pluginId}] command ${id} failed:`, result.error);
          }
        });
      };
    }
  }
  // Look up the per-plugin companion panel-components map. Plugins that
  // contribute panels but don't ship a companion render with no React
  // component bound — dockview will report "no component registered for
  // <id>" in the panel header, which makes the wiring gap visible during
  // development. Plugins that don't contribute panels at all simply have
  // no entry in PLUGIN_COMPANIONS and skip this step.
  const companion = PLUGIN_COMPANIONS[plugin.manifest.id];
  const panelComponents: Record<string, FunctionComponent> = companion
    ? { ...companion.panelComponents }
    : {};
  if (panels.length > 0 && Object.keys(panelComponents).length === 0) {
    // Surface the wiring gap loud and clear so future plugin authors
    // notice they forgot the companion file.
    console.warn(
      `[plugin-bootstrap] plugin ${instance.pluginId} contributes panels but has no entry in ` +
        `PLUGIN_COMPANIONS — panels will render without a component. Add a panels.ts file + an ` +
        `entry in src/lib/plugin-bootstrap.ts PLUGIN_COMPANIONS.`,
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
 * Bootstrap the plugin runtime: builds the runtime, attaches it to
 * `usePluginsStore`, loads every bundled plugin, bridges their contributions
 * into `useModulesStore`, and starts the periodic health-check loop.
 *
 * Returns a teardown function — call it from a React `useEffect` cleanup so
 * a hot-reload or unmount tears the runtime + interval down cleanly.
 */
export async function bootstrapPlugins(): Promise<() => void> {
  const persistence = await resolvePersistence();
  const sidecarBaseUrl = await getSidecarBaseUrl().catch(() => "http://127.0.0.1:0");
  const runtime = new PluginRuntime({
    sidecarBaseUrl,
    hostVersion: HOST_VERSION,
    persistence,
  });

  const detachStore = usePluginsStore.getState().attachRuntime(runtime);

  for (const plugin of BUNDLED_PLUGINS) {
    runtime.discover(plugin);
    await runtime.loadPlugin(plugin);
    const pluginModule = moduleForPlugin(plugin);
    if (pluginModule) {
      useModulesStore.getState().appendModules([pluginModule]);
    }
  }

  // Periodic health checks keep the manager UI's history strip live.
  const interval = setInterval(() => {
    void runtime.healthCheckAll();
  }, HEALTH_POLL_INTERVAL_MS);

  // Run one health check immediately so the panel doesn't sit on
  // "awaiting first health check" for 30 seconds after launch.
  void runtime.healthCheckAll();

  return () => {
    clearInterval(interval);
    detachStore();
    // Best-effort shutdown of every loaded plugin on teardown — fire-and-
    // forget so cleanup never blocks unmount.
    for (const plugin of BUNDLED_PLUGINS) {
      void runtime.unloadPlugin(plugin.manifest.id);
    }
  };
}
