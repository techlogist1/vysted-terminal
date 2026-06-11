/**
 * Marketplace / unified-extension types (FR-050–054, US10).
 *
 * The marketplace is the app's PRIMARY extensibility model: brokers, data
 * providers/connectors, panels, and agents are all install/enable/configure/
 * remove marketplace plugins — one model, not hardcoded first-class citizens.
 * These types are the host-side companion metadata for the locked, serializable
 * `VystedPlugin` contract (`types/plugin.ts`) — they live HERE, never on the
 * locked contract (adding fields there is Tier-4). A `MarketplaceEntry` maps a
 * compiled-in plugin to its catalog metadata: category, pre-installed state, and
 * the declarative BYOK credential shape the credentials hub renders generically.
 */

import type { BrokerId } from "./broker";

/** The extension categories the marketplace governs — all under one lifecycle. */
export type MarketplaceCategory = "broker" | "data" | "panel" | "agent" | "analytics";

export type CredentialFieldType = "text" | "password";

/**
 * One declarative credential field (FR-034). The credentials hub renders the
 * field generically — label, masking (`secret`/`type === "password"`), and the
 * keychain account it persists to — with zero per-source UI code.
 */
export interface CredentialField {
  /** Field key; also the keychain sub-account under the plugin's namespace. */
  key: string;
  label: string;
  type: CredentialFieldType;
  /** Stored in the OS keychain, masked, never echoed/logged (FR-036). */
  secret: boolean;
  required: boolean;
  placeholder?: string;
  help?: string;
}

/**
 * One marketplace catalog entry — the host-side metadata for a compiled-in
 * plugin. The runtime loads the plugin on enable; this entry describes how the
 * marketplace presents + configures it.
 */
export interface MarketplaceEntry {
  /** Matches `VystedPlugin.pluginId` and the plugin manifest `id`. */
  pluginId: string;
  name: string;
  category: MarketplaceCategory;
  description: string;
  version: string;
  author?: string;
  /** Lucide icon name. */
  icon?: string;
  /**
   * Pre-installed + enabled by default (first-party). Brokers are ALWAYS false
   * (FR-051 — no broker registered at boot; the user installs the one they want).
   */
  preinstalled: boolean;
  /** Declarative BYOK credentials the configure form renders (FR-034). */
  credentialFields?: CredentialField[];
  /** Keychain namespace for this plugin's secrets ("broker" | "plugin"). */
  secretNamespace?: "plugin" | "broker";
  /** For broker entries: the sidecar broker id (e.g. "kite") for keychain + routes. */
  brokerId?: BrokerId;
  /** Where-to-get-credentials link + instructions (FR-034 "needs no key" surface). */
  website?: string;
  instructions?: string;
  /** Data slice (FR-053): standard-model keys served + provider preference rank. */
  standardModelKeys?: string[];
  preferenceRank?: number;
}

/** Per-plugin marketplace state derived from persisted config + runtime state. */
export interface MarketplacePluginState {
  pluginId: string;
  installed: boolean;
  enabled: boolean;
  /** Runtime lifecycle state from the plugin runtime ("active"/"stopped"/"error"/…). */
  runtimeState?: string;
  /** Whether every required credential field has a stored value. */
  configured: boolean;
  errorMessage?: string;
}
