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

/**
 * Host glue the runtime drives so a plugin's contributions (dockview panels,
 * cmd+K commands, custom agents) follow its lifecycle: `attach` runs whenever
 * the plugin becomes active, `detach` when it is disabled or removed. A
 * rejection marks the plugin errored with the reason.
 */
export interface PluginHostBridge {
  attach(pluginId: string): Promise<void>;
  detach(pluginId: string): Promise<void>;
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
  /** Surfaces/withdraws plugin contributions; defaults to a no-op. */
  host?: PluginHostBridge;
  /** Whether a never-persisted plugin is installed + enabled. The host passes
   *  the catalog's `enabledByDefault`; a bare runtime (tests) defaults to on. */
  defaultEnabled?: (pluginId: string) => boolean;
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
    host: context?.host ?? { attach: async () => {}, detach: async () => {} },
    defaultEnabled: context?.defaultEnabled ?? (() => true),
  };
}

/** Parse a `major.minor.patch` semver into a numeric triple (pre-release/build ignored).
 *  Strips a leading `>=`/`>`/`^`/`~`/`=` first so a manifest written as `">=0.8.0"`
 *  parses to its floor `[0,8,0]` instead of `[0,0,0]`. `<` is deliberately NOT
 *  stripped (R15-CODE-PLATFORM-048): every comparison this feeds
 *  ({@link hostSatisfies}) is `>=`, so silently stripping `<` would parse
 *  `"<0.9.0"` as `0.9.0` and then apply `>=`, inverting the manifest's actual
 *  constraint — an unsupported operator must fail loudly instead. */
function parseSemver(version: string): [number, number, number] {
  const cleaned = version.trim().replace(/^[\^~>=\s]+/, "");
  const core = cleaned.split("+")[0].split("-")[0];
  const parts = core.split(".").map((p) => Number.parseInt(p, 10));
  return [
    Number.isFinite(parts[0]) ? parts[0] : 0,
    Number.isFinite(parts[1]) ? parts[1] : 0,
    Number.isFinite(parts[2]) ? parts[2] : 0,
  ];
}

/**
 * True iff `host` >= `required` by major.minor.patch comparison. The host
 * (Vysted Terminal) satisfies a plugin's `requiredHostVersion` only when it is
 * at least that version. Deliberately simple — Vysted versions are plain
 * `x.y.z`; ranges/caret/tilde are not part of the manifest contract. A `<`
 * prefix is an unsupported range operator, not a satisfiable requirement —
 * always false, regardless of the host version.
 */
export function hostSatisfies(host: string, required: string): boolean {
  if (required.trim().startsWith("<")) {
    return false;
  }
  const [h0, h1, h2] = parseSemver(host);
  const [r0, r1, r2] = parseSemver(required);
  if (h0 !== r0) return h0 > r0;
  if (h1 !== r1) return h1 > r1;
  return h2 >= r2;
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
   * `preloadedConfig` (R15-LIFECYCLE-027): pass the persisted config the
   * caller already fetched (or `null` when it fetched and found none) so this
   * call skips its own `persistence.load` round-trip — the boot loop reads
   * every plugin's config once to decide whether to load it, and previously
   * loaded it again here, serially, for every installed+enabled plugin. Omit
   * the argument to have this call fetch it itself (the default, and what
   * `installPlugin`/`enablePlugin`/`reloadPlugin` still do after their own
   * config write).
   *
   * On success, transitions the record to `active`; on failure, to `error`
   * with the captured message.
   */
  async loadPlugin(
    plugin: DiscoveredPlugin,
    preloadedConfig?: PluginPersistedConfig | null,
  ): Promise<LoadedPluginSnapshot> {
    let record = this.plugins.get(plugin.manifest.id);
    if (!record) {
      record = this.discover(plugin) as LoadedPlugin;
    } else if (record.state === "active" || record.state === "initializing") {
      // Already running — nothing to do; surface the current snapshot.
      return record;
    }

    // FR-054 / SC-015: reject an incompatible plugin AT LOAD — never silently
    // load it. Surfaces as `error` with the reason; the plugin never reaches
    // `active` and contributes nothing.
    const incompatibility = this.checkCompatibility(plugin);
    if (incompatibility) {
      return this.transitionToError(
        plugin.manifest.id,
        new Error(incompatibility),
        "compatibility",
      );
    }

    this.transition(plugin.manifest.id, "initializing");

    let persisted: PluginPersistedConfig;
    try {
      const stored =
        preloadedConfig !== undefined
          ? preloadedConfig
          : await this.context.persistence.load(plugin.manifest.id);
      persisted = stored ?? this.defaultConfig(plugin.manifest.id);
      // Persist the default the first time we see this plugin so a second
      // launch finds an explicit row (not falling back through the default).
      if (!stored) {
        await this.context.persistence.save(persisted);
      }
    } catch (error) {
      return this.transitionToError(plugin.manifest.id, error, "config-load");
    }

    if (!persisted.installed) {
      // Not installed via the marketplace — keep it discovered/stopped and
      // contribute nothing (FR-050). The marketplace `installPlugin` flips this.
      return this.transition(plugin.manifest.id, "stopped");
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

    const active = this.transition(plugin.manifest.id, "active", "loaded");
    try {
      await this.context.host.attach(plugin.manifest.id);
    } catch (error) {
      return this.transitionToError(plugin.manifest.id, error, "attach");
    }
    return active;
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

  /**
   * Restart a plugin (shutdown, then a fresh `initialize()`) so it picks up
   * changed settings or newly granted secrets. A disabled plugin stays stopped.
   */
  async reloadPlugin(plugin: DiscoveredPlugin): Promise<LoadedPluginSnapshot> {
    await this.unloadPlugin(plugin.manifest.id);
    return this.loadPlugin(plugin);
  }

  // ----- Marketplace lifecycle (FR-050) -----

  /** The config of a never-persisted plugin — the one shared default. */
  private defaultConfig(pluginId: string): PluginPersistedConfig {
    const on = this.context.defaultEnabled(pluginId);
    return { pluginId, installed: on, enabled: on, settings: {}, grantedSecretIds: [] };
  }

  /** Load (or update) the per-plugin persisted config, merging `patch` over
   *  the stored row or, for a never-seen plugin, the shared default. */
  private async patchConfig(
    pluginId: string,
    patch: Partial<PluginPersistedConfig>,
  ): Promise<void> {
    const current = (await this.context.persistence.load(pluginId)) ?? this.defaultConfig(pluginId);
    await this.context.persistence.save({ ...current, ...patch, pluginId });
  }

  /** Marketplace: merge a patch into the plugin's persisted config (e.g. the
   *  granted secret ids set by the credentials hub on configure). */
  async updateConfig(pluginId: string, patch: Partial<PluginPersistedConfig>): Promise<void> {
    await this.patchConfig(pluginId, patch);
  }

  /** Read the plugin's persisted config (the shared default if never persisted). */
  async readConfig(pluginId: string): Promise<PluginPersistedConfig> {
    return (await this.context.persistence.load(pluginId)) ?? this.defaultConfig(pluginId);
  }

  /** Install a plugin via the marketplace: persist installed+enabled, then load. */
  async installPlugin(plugin: DiscoveredPlugin): Promise<LoadedPluginSnapshot> {
    await this.patchConfig(plugin.manifest.id, { installed: true, enabled: true });
    this.discover(plugin);
    return this.loadPlugin(plugin);
  }

  /** Enable an installed plugin: persist enabled, then load it. */
  async enablePlugin(plugin: DiscoveredPlugin): Promise<LoadedPluginSnapshot> {
    await this.patchConfig(plugin.manifest.id, { installed: true, enabled: true });
    return this.loadPlugin(plugin);
  }

  /** Disable a plugin: persist enabled:false, unload it and withdraw its
   *  contributions (it stays installed). */
  async disablePlugin(pluginId: string): Promise<void> {
    await this.patchConfig(pluginId, { enabled: false });
    await this.unloadPlugin(pluginId);
    await this.detach(pluginId);
  }

  /** Remove a plugin entirely: persist installed:false + enabled:false, unload
   *  it and withdraw its contributions. */
  async removePlugin(pluginId: string): Promise<void> {
    await this.patchConfig(pluginId, { installed: false, enabled: false });
    await this.unloadPlugin(pluginId);
    await this.detach(pluginId);
  }

  private async detach(pluginId: string): Promise<void> {
    try {
      await this.context.host.detach(pluginId);
    } catch (error) {
      // A not-yet-discovered id (boot still discovering) has no record to mark.
      if (this.plugins.has(pluginId)) {
        this.transitionToError(pluginId, error, "detach");
      }
    }
  }

  /**
   * Validate that a discovered plugin is compatible with the host BEFORE it is
   * initialized (FR-054 / SC-015). Returns an error message describing the
   * incompatibility, or `null` when the plugin is safe to load:
   *  - the manifest id MUST equal the instance `pluginId`;
   *  - the manifest version MUST equal the instance `version`;
   *  - the host version MUST satisfy the manifest `requiredHostVersion`.
   * The marketplace cannot be trusted without these — a mismatched or
   * host-incompatible plugin is rejected at load, not silently run.
   */
  private checkCompatibility(plugin: DiscoveredPlugin): string | null {
    const { manifest, instance } = plugin;
    if (manifest.id !== instance.pluginId) {
      return `manifest id "${manifest.id}" does not match plugin instance id "${instance.pluginId}"`;
    }
    if (manifest.version !== instance.version) {
      return `manifest version "${manifest.version}" does not match plugin instance version "${instance.version}"`;
    }
    if (!hostSatisfies(this.context.hostVersion, manifest.requiredHostVersion)) {
      // Name the real operator (R15-CODE-PLATFORM-048): hardcoding ">=" here
      // read as if a "<0.9.0" manifest asked for ">= <0.9.0" — nonsense that
      // hid the fact that "<" is simply unsupported.
      const required = manifest.requiredHostVersion.trim();
      const detail = required.startsWith("<")
        ? `"${required}" (an unsupported range operator — only a floor, ">=", is supported)`
        : `>= ${required}`;
      return `plugin requires host version ${detail} but host is ${this.context.hostVersion}`;
    }
    return null;
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
    // R15-CODE-PLATFORM-047: re-read the CURRENT record post-await rather than
    // writing back the pre-await `record` — a disable/error transition that
    // landed while `healthCheck()` was in flight must not be reverted to
    // `active` by this stale-record overwrite. Bail if the plugin is gone or
    // no longer active; only `healthHistory` is mutated otherwise.
    const current = this.plugins.get(record.manifest.id);
    if (!current || current.state !== "active") {
      return;
    }
    const sample: HealthSample = {
      status: status.status,
      message: status.message,
      recordedAt: this.context.now(),
    };
    const previous = current.healthHistory[current.healthHistory.length - 1];
    const newHistory = [...current.healthHistory, sample].slice(-HEALTH_HISTORY_LIMIT);
    this.plugins.set(current.manifest.id, {
      ...current,
      healthHistory: newHistory,
    });
    if (!previous || previous.status !== sample.status) {
      this.emit("health-changed", current.manifest.id, status.message);
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
