/**
 * Vysted Terminal — plugin runtime support types.
 *
 * The locked `VystedPlugin` contract in `types/plugin.ts` is the *what* every
 * plugin implements. This file defines the *how* the runtime loads, supervises,
 * and surfaces them — manifest format, lifecycle states, health snapshots, and
 * the events a plugin-manager UI can subscribe to.
 *
 * IMPORTANT: this file MUST NOT modify or extend `VystedPlugin` itself. It
 * wraps the contract; it does not change it. Adding a runtime concept here is
 * a Tier-2/3 decision; touching `types/plugin.ts` is Tier-4 (CLAUDE.md).
 */

import type { HealthStatus, VystedPlugin } from "./plugin";

// ---------------------------------------------------------------------------
// Manifest — declarative discovery metadata
// ---------------------------------------------------------------------------

/**
 * The on-disk manifest the runtime reads to discover and validate a plugin
 * before instantiating it. Bundled first-party plugins ship their manifest as
 * `plugins/<id>/manifest.json`; the loader imports the entry module only after
 * the manifest has been validated.
 */
export interface PluginManifest {
  /** Stable plugin identifier; must match the `VystedPlugin.pluginId` exported by the entry. */
  id: string;
  /** Plugin semver; must match `VystedPlugin.version`. */
  version: string;
  /** Human-readable plugin name; mirrored from `VystedPlugin.pluginName`. */
  name: string;
  /** Path to the plugin's TypeScript entry, relative to its manifest. */
  entry: string;
  /** Minimum host (Vysted Terminal) semver this plugin supports. */
  requiredHostVersion: string;
  /** Optional one-line description shown in the plugin manager. */
  description?: string;
  /** Optional author label (e.g. "Vysted Team", "OpenBB"). */
  author?: string;
  /** Optional homepage / repository URL. */
  homepage?: string;
}

// ---------------------------------------------------------------------------
// Lifecycle states + health
// ---------------------------------------------------------------------------

/** Lifecycle state of a plugin tracked by the runtime supervisor. */
export type LoadedPluginState =
  | "discovered" // manifest validated, entry not yet imported
  | "initializing" // `initialize()` is in flight
  | "active" // `initialize()` resolved, plugin contributing capabilities
  | "stopping" // `shutdown()` is in flight
  | "stopped" // `shutdown()` resolved, capabilities deregistered
  | "error"; // initialise / shutdown / health-check threw

/**
 * One health-check sample retained in a plugin's rolling history. The runtime
 * polls `VystedPlugin.healthCheck()` on a schedule and stores the most recent
 * N samples so the plugin manager can show a trend, not just a current state.
 */
export interface HealthSample {
  status: HealthStatus["status"];
  message?: string;
  /** Epoch milliseconds the sample was recorded. */
  recordedAt: number;
}

// ---------------------------------------------------------------------------
// Runtime record
// ---------------------------------------------------------------------------

/**
 * The runtime's record of one loaded plugin. Combines the immutable manifest,
 * the live `VystedPlugin` instance, the supervised lifecycle state, and the
 * recent health history. Held in `usePluginsStore` (Teammate B).
 */
export interface LoadedPlugin {
  manifest: PluginManifest;
  /** The instantiated plugin; `undefined` while in `discovered` state. */
  instance?: VystedPlugin;
  state: LoadedPluginState;
  /** Most recent health samples, oldest-first; bounded length set by the runtime. */
  healthHistory: HealthSample[];
  /** Last error message, if `state === "error"`. */
  errorMessage?: string;
  /** Epoch milliseconds when the state was last transitioned. */
  stateChangedAt: number;
}

// ---------------------------------------------------------------------------
// Runtime events — the plugin-manager UI subscribes to these
// ---------------------------------------------------------------------------

/** Events emitted by `PluginRuntime` as plugins move through the lifecycle. */
export type PluginRuntimeEventKind =
  | "discovered"
  | "loaded"
  | "started"
  | "stopped"
  | "health-changed"
  | "errored";

export interface PluginRuntimeEvent {
  kind: PluginRuntimeEventKind;
  /** The affected plugin id. */
  pluginId: string;
  /** Optional human-readable detail. */
  message?: string;
  /** Epoch milliseconds when the event was emitted. */
  emittedAt: number;
}

// ---------------------------------------------------------------------------
// Persistence — sidecar-owned per-plugin config
// ---------------------------------------------------------------------------

/**
 * Shape of the per-plugin config blob persisted by the sidecar (Teammate B
 * defines the route and the SQLite-backed store). Browser storage is NOT used
 * for plugin config — the sidecar-owned-persistence pattern from Phase 1
 * (workspace_store, portfolio_db) extends here.
 */
export interface PluginPersistedConfig {
  pluginId: string;
  /** Whether the user enabled the plugin; defaults to `true` once first loaded. */
  enabled: boolean;
  /** Plugin-private settings; opaque to the host, mirrored into `PluginConfig.settings`. */
  settings: Record<string, unknown>;
  /** Secret ids the user has granted to this plugin (resolved to values via OS keychain). */
  grantedSecretIds: string[];
}
