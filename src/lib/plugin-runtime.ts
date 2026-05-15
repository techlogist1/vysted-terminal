/**
 * Plugin runtime — discovers, supervises, and surfaces `VystedPlugin`s.
 *
 * The locked `VystedPlugin` contract (`types/plugin.ts`) is the *what* every
 * plugin implements; this runtime is the *how* the host loads, lifecycle-
 * supervises, capability-negotiates, and health-checks them. It owns no UI —
 * the plugin manager panel subscribes to its events and renders the state.
 *
 * Design points:
 *
 * - **Capability negotiation by flag, not by method shape.** The contract says
 *   the host checks `capabilities.contributesPanels`, *not* whether
 *   `getPanels` is defined. A plugin that sets the flag but forgets the getter
 *   transitions to `error`; a plugin that defines the getter without the flag
 *   stays silent.
 * - **Lifecycle supervision.** Each loaded plugin has a `LoadedPlugin` record
 *   tracking `state`, `healthHistory`, and `errorMessage`. State transitions
 *   emit `PluginRuntimeEvent`s.
 * - **Health rollover.** `healthHistory` is bounded to `HEALTH_HISTORY_LIMIT`
 *   samples, oldest-first. The plugin manager renders a trend, not just the
 *   latest sample.
 * - **No browser storage.** Per-plugin config (settings, granted secret ids,
 *   enabled flag) is fetched from / pushed to the sidecar `/plugins/{id}/config`
 *   endpoint via the supplied `PluginRuntimeContext.persistence` adapter.
 *
 * Phase 2 ships the bundled-import loader (decision A1 in the plan): plugins
 * live under `plugins/<id>/`, exporting a `VystedPlugin` instance the runtime
 * imports statically. Filesystem-installed / signed plugins are out of scope.
 */

import type {
  AgentSpec,
  CommandSpec,
  DataSource,
  HealthStatus,
  NodeSpec,
  PanelSpec,
  PluginConfig,
  PluginCapabilities,
  VystedPlugin,
} from "../../types/plugin";
import type {
  HealthSample,
  LoadedPlugin,
  LoadedPluginState,
  PluginManifest,
  PluginPersistedConfig,
  PluginRuntimeEvent,
  PluginRuntimeEventKind,
} from "../../types/plugin-runtime";

/** How many health samples the runtime retains per plugin. */
export const HEALTH_HISTORY_LIMIT = 20;

/** A plugin source the runtime loads — manifest + the actual instance. */
export interface DiscoveredPlugin {
  manifest: PluginManifest;
  instance: VystedPlugin;
}

/**
 * Adapter the host injects so the runtime can persist per-plugin config
 * without depending on the sidecar client directly. The sidecar client is the
 * production implementation; tests pass an in-memory fake.
 */
export interface PluginPersistenceAdapter {
  load(pluginId: string): Promise<PluginPersistedConfig | null>;
  save(config: PluginPersistedConfig): Promise<void>;
}

/** Optional clock + id resolver — exists so tests can pin time and the dataDir. */
export interface PluginRuntimeContext {
  /** Returns the current time in epoch ms; defaults to `Date.now`. */
  now?: () => number;
  /** Returns the per-plugin private data directory; receives the plugin id. */
  resolveDataDir?: (pluginId: string) => string;
  /** Sidecar base URL handed to the plugin via `PluginConfig.sidecarBaseUrl`. */
  sidecarBaseUrl?: string;
  /** Host (Vysted Terminal) semver handed to the plugin via `PluginConfig.hostVersion`. */
  hostVersion?: string;
  /** Persistence adapter for per-plugin config. */
  persistence?: PluginPersistenceAdapter;
  /** Resolves granted secret ids to actual values; defaults to a no-op (empty map). */
  resolveSecrets?: (ids: string[]) => Promise<Record<string, string>>;
}

interface RuntimeListener {
  (event: PluginRuntimeEvent): void;
}

/** Default in-memory adapter — used when no persistence is supplied (tests). */
class InMemoryPersistence implements PluginPersistenceAdapter {
  private readonly store = new Map<string, PluginPersistedConfig>();
  async load(pluginId: string): Promise<PluginPersistedConfig | null> {
    return this.store.get(pluginId) ?? null;
  }
  async save(config: PluginPersistedConfig): Promise<void> {
    this.store.set(config.pluginId, { ...config });
  }
}

function defaultContext(context?: PluginRuntimeContext): Required<PluginRuntimeContext> {
  return {
    now: context?.now ?? (() => Date.now()),
    resolveDataDir: context?.resolveDataDir ?? ((id) => `plugins/${id}`),
    sidecarBaseUrl: context?.sidecarBaseUrl ?? "http://127.0.0.1:0",
    hostVersion: context?.hostVersion ?? "0.0.0",
    persistence: context?.persistence ?? new InMemoryPersistence(),
    resolveSecrets: context?.resolveSecrets ?? (async () => ({})),
  };
}

/** Read-only snapshot of one plugin's runtime state — what UI subscribers see. */
export type LoadedPluginSnapshot = Readonly<LoadedPlugin>;

/**
 * Plugin lifecycle supervisor. One instance per host process. Pure TypeScript
 * — no Tauri invoke required (decision A1).
 */
export class PluginRuntime {
  private readonly context: Required<PluginRuntimeContext>;
  private readonly plugins = new Map<string, LoadedPlugin>();
  private readonly listeners = new Set<RuntimeListener>();

  constructor(context?: PluginRuntimeContext) {
    this.context = defaultContext(context);
  }

  // ----- Discovery -----

  /**
   * Register a manifest+instance pair so the runtime knows about it. Does not
   * call `initialize()`; transitions the record to `discovered` state and
   * emits a `discovered` event so the plugin manager can show "loadable"
   * plugins before the user (or the auto-load step) actually starts them.
   */
  discover(plugin: DiscoveredPlugin): LoadedPluginSnapshot {
    const existing = this.plugins.get(plugin.manifest.id);
    if (existing) {
      // Re-discovery is idempotent — useful when manifests are re-scanned at
      // dev-server reload time. Keeps the existing health history.
      return existing;
    }
    const record: LoadedPlugin = {
      manifest: plugin.manifest,
      instance: plugin.instance,
      state: "discovered",
      healthHistory: [],
      stateChangedAt: this.context.now(),
    };
    this.plugins.set(plugin.manifest.id, record);
    this.emit("discovered", plugin.manifest.id);
    return record;
  }

  // ----- Lifecycle -----

  /**
   * Load a plugin: discover (if needed), then call `initialize()` with the
   * resolved `PluginConfig`. Capability negotiation is deferred to the getter
   * accessors (`getDataSources` / `getPanels` / `getCommands` / etc.) — the
   * runtime calls them only when the matching `capabilities` flag is set.
   *
   * On success, transitions the record to `active`; on failure, to `error`
   * with the captured message.
   */
  async loadPlugin(plugin: DiscoveredPlugin): Promise<LoadedPluginSnapshot> {
    let record = this.plugins.get(plugin.manifest.id);
    if (!record) {
      record = this.discover(plugin) as LoadedPlugin;
    } else if (record.state === "active" || record.state === "initializing") {
      // Already running — nothing to do; surface the current snapshot.
      return record;
    }

    this.transition(plugin.manifest.id, "initializing");

    let persisted: PluginPersistedConfig;
    try {
      const stored = await this.context.persistence.load(plugin.manifest.id);
      persisted = stored ?? {
        pluginId: plugin.manifest.id,
        enabled: true,
        settings: {},
        grantedSecretIds: [],
      };
      // Persist the default the first time we see this plugin so a second
      // launch finds an explicit row (not falling back through the default).
      if (!stored) {
        await this.context.persistence.save(persisted);
      }
    } catch (error) {
      return this.transitionToError(plugin.manifest.id, error, "config-load");
    }

    if (!persisted.enabled) {
      // Honour the persisted disabled state — keep the record in `stopped` so
      // the manager UI can show "disabled" without ever calling `initialize()`.
      return this.transition(plugin.manifest.id, "stopped");
    }

    let secrets: Record<string, string>;
    try {
      secrets = await this.context.resolveSecrets(persisted.grantedSecretIds);
    } catch (error) {
      return this.transitionToError(plugin.manifest.id, error, "secret-resolve");
    }

    const config: PluginConfig = {
      dataDir: this.context.resolveDataDir(plugin.manifest.id),
      settings: persisted.settings,
      sidecarBaseUrl: this.context.sidecarBaseUrl,
      hostVersion: this.context.hostVersion,
      secrets,
    };

    try {
      await plugin.instance.initialize(config);
    } catch (error) {
      return this.transitionToError(plugin.manifest.id, error, "initialize");
    }

    return this.transition(plugin.manifest.id, "active", "loaded");
  }

  /**
   * Stop a plugin: call `shutdown()`, deregister, and transition to
   * `stopped`. Errors during shutdown still drive the record to `error` so
   * the manager UI can surface them.
   */
  async unloadPlugin(pluginId: string): Promise<LoadedPluginSnapshot | undefined> {
    const record = this.plugins.get(pluginId);
    if (!record || !record.instance) {
      return undefined;
    }
    if (record.state !== "active" && record.state !== "error") {
      // Nothing to shut down (already stopped / stopping / discovered).
      return record;
    }

    this.transition(pluginId, "stopping");
    try {
      await record.instance.shutdown();
    } catch (error) {
      return this.transitionToError(pluginId, error, "shutdown");
    }
    return this.transition(pluginId, "stopped", "stopped");
  }

  // ----- Capability accessors (negotiation by flag) -----

  /**
   * Helper used by all four capability accessors below. Returns the result of
   * the getter only when the matching flag is set AND the getter exists. A
   * flag set with a missing getter logs a warning to the runtime listener via
   * the `errored` event but does not throw — the rest of the plugin's
   * capabilities still work.
   */
  private callIfFlagged<R>(
    record: LoadedPlugin,
    flag: keyof PluginCapabilities,
    getter: keyof VystedPlugin,
  ): R[] {
    if (!record.instance) {
      return [];
    }
    if (!record.instance.capabilities[flag]) {
      return [];
    }
    const fn = record.instance[getter];
    if (typeof fn !== "function") {
      this.emit(
        "errored",
        record.manifest.id,
        `capability ${String(flag)} declared but ${String(getter)}() is not implemented`,
      );
      return [];
    }
    try {
      return (fn as unknown as () => R[]).call(record.instance) ?? [];
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      this.emit("errored", record.manifest.id, `${String(getter)}() threw: ${message}`);
      return [];
    }
  }

  /** Aggregate every active plugin's contributed `DataSource`s, post-flag-check. */
  collectDataSources(): DataSource[] {
    const out: DataSource[] = [];
    for (const record of this.activePlugins()) {
      out.push(...this.callIfFlagged<DataSource>(record, "contributesData", "getDataSources"));
    }
    return out;
  }

  /** Aggregate every active plugin's contributed `PanelSpec`s, post-flag-check. */
  collectPanels(): PanelSpec[] {
    const out: PanelSpec[] = [];
    for (const record of this.activePlugins()) {
      out.push(...this.callIfFlagged<PanelSpec>(record, "contributesPanels", "getPanels"));
    }
    return out;
  }

  /** Aggregate every active plugin's contributed `CommandSpec`s, post-flag-check. */
  collectCommands(): CommandSpec[] {
    const out: CommandSpec[] = [];
    for (const record of this.activePlugins()) {
      out.push(...this.callIfFlagged<CommandSpec>(record, "contributesCommands", "getCommands"));
    }
    return out;
  }

  /** Aggregate every active plugin's contributed `AgentSpec`s, post-flag-check. */
  collectAgents(): AgentSpec[] {
    const out: AgentSpec[] = [];
    for (const record of this.activePlugins()) {
      out.push(...this.callIfFlagged<AgentSpec>(record, "contributesAgents", "getAgents"));
    }
    return out;
  }

  /** Aggregate every active plugin's contributed `NodeSpec`s, post-flag-check. */
  collectNodes(): NodeSpec[] {
    const out: NodeSpec[] = [];
    for (const record of this.activePlugins()) {
      out.push(...this.callIfFlagged<NodeSpec>(record, "contributesNodes", "getNodes"));
    }
    return out;
  }

  // ----- Health -----

  /**
   * Poll every active plugin's `healthCheck()`, append the result to its
   * rolling history (bounded to `HEALTH_HISTORY_LIMIT`), and emit a
   * `health-changed` event whenever the latest sample's `status` differs from
   * the previous one. A health-check that throws drives the record to
   * `error` (the plugin is unsupervised at that point).
   */
  async healthCheckAll(): Promise<void> {
    for (const record of this.activePlugins()) {
      await this.healthCheckOne(record);
    }
  }

  private async healthCheckOne(record: LoadedPlugin): Promise<void> {
    if (!record.instance) {
      return;
    }
    let status: HealthStatus;
    try {
      status = await record.instance.healthCheck();
    } catch (error) {
      this.transitionToError(record.manifest.id, error, "healthCheck");
      return;
    }
    const sample: HealthSample = {
      status: status.status,
      message: status.message,
      recordedAt: this.context.now(),
    };
    const previous = record.healthHistory[record.healthHistory.length - 1];
    const newHistory = [...record.healthHistory, sample].slice(-HEALTH_HISTORY_LIMIT);
    this.plugins.set(record.manifest.id, {
      ...record,
      healthHistory: newHistory,
    });
    if (!previous || previous.status !== sample.status) {
      this.emit("health-changed", record.manifest.id, status.message);
    }
  }

  // ----- Snapshots / introspection -----

  /** All loaded plugins, in discovery order. Returns immutable snapshots. */
  getPlugins(): LoadedPluginSnapshot[] {
    return [...this.plugins.values()];
  }

  /** Snapshot of one plugin by id, or `undefined`. */
  getPlugin(pluginId: string): LoadedPluginSnapshot | undefined {
    return this.plugins.get(pluginId);
  }

  /** All plugins currently in `active` state. */
  activePlugins(): LoadedPlugin[] {
    return [...this.plugins.values()].filter((record) => record.state === "active");
  }

  // ----- Events -----

  /** Subscribe to runtime events. Returns the unsubscribe function. */
  subscribe(listener: RuntimeListener): () => void {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  }

  // ----- Internals -----

  private emit(kind: PluginRuntimeEventKind, pluginId: string, message?: string): void {
    const event: PluginRuntimeEvent = {
      kind,
      pluginId,
      message,
      emittedAt: this.context.now(),
    };
    for (const listener of this.listeners) {
      try {
        listener(event);
      } catch {
        // Listener errors must never poison runtime state.
      }
    }
  }

  private transition(
    pluginId: string,
    state: LoadedPluginState,
    eventKind?: PluginRuntimeEventKind,
  ): LoadedPlugin {
    const record = this.plugins.get(pluginId);
    if (!record) {
      throw new Error(`PluginRuntime: cannot transition unknown plugin ${pluginId}`);
    }
    const next: LoadedPlugin = {
      ...record,
      state,
      stateChangedAt: this.context.now(),
      // Clear errorMessage on any non-error transition so a recovering plugin
      // doesn't carry a stale error indefinitely.
      errorMessage: state === "error" ? record.errorMessage : undefined,
    };
    this.plugins.set(pluginId, next);
    if (eventKind) {
      switch (eventKind) {
        case "loaded":
          this.emit("loaded", pluginId);
          this.emit("started", pluginId);
          break;
        case "started":
          this.emit("started", pluginId);
          break;
        case "stopped":
          this.emit("stopped", pluginId);
          break;
        default:
          this.emit(eventKind, pluginId);
      }
    }
    return next;
  }

  private transitionToError(pluginId: string, error: unknown, phase: string): LoadedPlugin {
    const message = error instanceof Error ? error.message : String(error);
    const record = this.plugins.get(pluginId);
    if (!record) {
      throw new Error(`PluginRuntime: cannot mark unknown plugin ${pluginId} as errored`);
    }
    const next: LoadedPlugin = {
      ...record,
      state: "error",
      stateChangedAt: this.context.now(),
      errorMessage: `${phase}: ${message}`,
    };
    this.plugins.set(pluginId, next);
    this.emit("errored", pluginId, next.errorMessage);
    return next;
  }
}
