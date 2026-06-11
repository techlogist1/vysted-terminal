/**
 * Frontend keychain wrapper.
 *
 * Thin typed bindings over the Tauri Rust `keychain_set` / `keychain_get` /
 * `keychain_delete` commands (`src-tauri/src/keychain.rs`). Every Vysted
 * secret — LLM provider API keys, MCP server endpoints, plugin-granted
 * secrets — flows through here. The `KEYCHAIN_NAMESPACES` helpers build the
 * canonical secret-id strings so the namespace conventions stay consistent
 * across the AI core, the MCP layer, and plugin authors.
 *
 * The CLAUDE.md BYOK constraint is enforced by structure: this module is
 * the ONLY frontend path that reads or writes credentials, and it never
 * touches `localStorage` / `sessionStorage` / cookies. Provider adapters in
 * the sidecar receive the resolved secret in the request body (read here,
 * sent via fetch, never persisted server-side beyond the request lifetime).
 */

import { invoke } from "@tauri-apps/api/core";

/**
 * Canonical namespace builders for the four secret categories Vysted
 * persists in the OS keychain. Frontend, sidecar, and plugin authors all
 * read these strings — keep them stable across releases unless coordinating
 * a migration.
 */
export const KEYCHAIN_NAMESPACES = {
  /** API key for an LLM provider (id is the `LLMProviderId` from `types/ai.ts`). */
  llmProvider: (id: string): string => `llm-provider:${id}`,

  /** Endpoint / credential for an external MCP server (id from `types/mcp.ts`). */
  mcpServer: (id: string): string => `mcp-server:${id}`,

  /** Plugin-private secret granted to a specific plugin under a user-chosen key. */
  pluginSecret: (pluginId: string, key: string): string => `plugin-secret:${pluginId}:${key}`,

  /**
   * Broker credential (Phase 5). One entry per broker × field — e.g.
   * `broker:alpaca:api_key`, `broker:kite:access_token`,
   * `broker:dhan:client_id`. Brokers with multiple OAuth-style fields
   * store each under its own `field` so revoking one does not require
   * re-entering the others. The disclaimer-ack persisted state
   * (`first-launch-tos`, per-broker `first-connect-ack`) lives under
   * `broker:_meta:first-launch-tos` and
   * `broker:<broker-id>:_meta:first-connect-ack` respectively.
   */
  broker: (brokerId: string, field: string): string => `broker:${brokerId}:${field}`,

  /**
   * App-level meta flag (not a credential) — e.g. `app-meta:onboarding-complete`.
   * Used for durable first-run state that must survive a workspace-layout reset
   * or an imported older blob (the same durability reason the disclaimer acks use
   * the keychain). Carries no secret; the stored value is a timestamp/choice tag.
   */
  appMeta: (key: string): string => `app-meta:${key}`,
} as const;

/** Persist a secret to the OS keychain under `account`. Overwrites any prior value. */
export async function setSecret(account: string, secret: string): Promise<void> {
  await invoke<void>("keychain_set", { account, secret });
}

/** Read a secret from the OS keychain. Returns `null` if no value is stored. */
export async function getSecret(account: string): Promise<string | null> {
  const value = await invoke<string | null>("keychain_get", { account });
  return value ?? null;
}

/** Remove a secret from the OS keychain. No-op if the secret was never set. */
export async function deleteSecret(account: string): Promise<void> {
  await invoke<void>("keychain_delete", { account });
}

/** Report from {@link migrateDevKeystore}. */
export interface KeychainMigrateReport {
  /** `"dev-keystore"` in dev builds, `"os-keychain"` in release. */
  backend: string;
  /** How many accounts were copied keychain→file on this call. */
  migrated: number;
  /** True when migration had already run (no-op) or in release (nothing to do). */
  already_done: boolean;
}

/**
 * Every account the dev keystore migration should sweep from the OS keychain on
 * first dev boot. Generous by design — reading a non-existent account is a
 * harmless `None`. Covers the four named items plus every provider, the known
 * brokers, and the plugin/news/tradesa secrets, so the operator's configured
 * keys carry over without a single extra dialog after the migration read.
 */
export function devKeystoreMigrationAccounts(): string[] {
  const providers = [
    "anthropic",
    "openai",
    "gemini",
    "groq",
    "ollama",
    "deepseek",
    "xai",
    "openrouter",
    "perplexity",
    "mistral",
  ];
  const brokers = ["kite", "alpaca", "dhan"];
  const brokerFields = [
    "api_key",
    "api_secret",
    "access_token",
    "client_id",
    "_meta:first-connect-ack",
  ];
  const accounts = new Set<string>();
  for (const id of providers) accounts.add(KEYCHAIN_NAMESPACES.llmProvider(id));
  accounts.add("broker:_meta:first-launch-tos");
  for (const b of brokers) {
    for (const f of brokerFields) accounts.add(`broker:${b}:${f}`);
  }
  accounts.add(KEYCHAIN_NAMESPACES.appMeta("onboarding-complete"));
  // Plugin / external-service secrets that have shipped.
  accounts.add(KEYCHAIN_NAMESPACES.pluginSecret("vysted-news", "newsapi_key"));
  accounts.add(KEYCHAIN_NAMESPACES.pluginSecret("tradesa-v2", "supabase_url"));
  accounts.add(KEYCHAIN_NAMESPACES.pluginSecret("tradesa-v2", "supabase_service_key"));
  accounts.add(KEYCHAIN_NAMESPACES.mcpServer("openbb"));
  return [...accounts];
}

/**
 * Run the one-time dev-keystore migration: in a dev build, copy any existing
 * secrets from the OS keychain into the git-ignored local keystore file so
 * `tauri dev` never reads the keychain again (no per-cdhash SecurityAgent
 * dialog). Idempotent — the Rust side guards with a `migrated` flag, so this is
 * safe to call on every boot. A pure no-op in release. Best-effort: a failure
 * (e.g. the operator denies the one final dialog) leaves the keystore empty and
 * the user re-adds keys through Settings — it never throws into boot.
 */
let devKeystoreMigrationInFlight: Promise<KeychainMigrateReport | null> | null = null;

export async function migrateDevKeystore(): Promise<KeychainMigrateReport | null> {
  // De-dupe concurrent calls: React StrictMode double-invokes the boot effect in
  // dev, which would otherwise fire two migrations racing the keystore file (and
  // the one keychain ACL evaluation). Both concurrent calls share the in-flight
  // promise; it's cleared once settled (the Rust `migrated` flag is the durable
  // once-only guard, so a later explicit call is harmless).
  if (devKeystoreMigrationInFlight) return devKeystoreMigrationInFlight;
  devKeystoreMigrationInFlight = (async () => {
    try {
      return await invoke<KeychainMigrateReport>("keychain_migrate", {
        accounts: devKeystoreMigrationAccounts(),
      });
    } catch {
      // Migration is best-effort; a denied dialog or missing store must not
      // break boot. The Settings UI remains the fallback for (re-)entering keys.
      return null;
    }
  })().finally(() => {
    devKeystoreMigrationInFlight = null;
  });
  return devKeystoreMigrationInFlight;
}
