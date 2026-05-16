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
