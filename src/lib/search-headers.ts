/**
 * Search-header assembly — the three-tier web-search request contract.
 *
 * Single source for the three headers every chat / agent request carries so the
 * sidecar can dispatch web search to the right backend (FR-080/083/084):
 *  - `X-Vysted-Search-Tier` — the active tier (native / byok-exa / local-searxng);
 *  - `X-Vysted-Exa-Key`     — the BYOK Exa API key, read from the OS keychain at
 *                             request time (FR-036 BYOK: secret in a header,
 *                             never the body/query, never persisted);
 *  - `X-Vysted-Searxng-Url` — the local SearXNG base URL for the local tier.
 *
 * Every value is OMITTED when absent (undefined, never an empty string) so the
 * sidecar sees "no key" / "autodetect" rather than a blank override. Both the
 * REST client (`sidecar-client`) and the SSE client (`chat/streaming`) call this
 * so the header set can never drift between the two transports.
 */

import { getSecret, KEYCHAIN_NAMESPACES } from "@/lib/keychain";
import { useSearchSettingsStore } from "@/store/search-settings";

/** The search-source plugin id the Exa BYOK key is namespaced under. */
const EXA_PLUGIN_ID = "vysted-search-exa";
/** The keychain field the Exa API key is stored under. */
const EXA_KEY_FIELD = "exa_api_key";

/**
 * Read the BYOK Exa API key from the OS keychain. Returns `null` when no key is
 * stored (the keyless default) — a keychain miss must never throw into a request.
 */
export async function getExaApiKey(): Promise<string | null> {
  try {
    return await getSecret(KEYCHAIN_NAMESPACES.pluginSecret(EXA_PLUGIN_ID, EXA_KEY_FIELD));
  } catch {
    return null;
  }
}

/** The keychain account the Exa key lives under — for the Settings add/remove UI. */
export const EXA_KEYCHAIN_ACCOUNT = KEYCHAIN_NAMESPACES.pluginSecret(EXA_PLUGIN_ID, EXA_KEY_FIELD);

/**
 * Build the three search headers for a sidecar request. Reads the tier + SearXNG
 * URL from the search-settings store (at call time, so a change reflects
 * immediately) and the Exa key from the keychain. Header values are `undefined`
 * when absent so the caller's header-merge drops them (never an empty string).
 */
export async function buildSearchHeaders(): Promise<Record<string, string | undefined>> {
  const { tier, searxngUrl } = useSearchSettingsStore.getState();
  const exaKey = await getExaApiKey();
  const trimmedUrl = searxngUrl.trim();
  return {
    "X-Vysted-Search-Tier": tier,
    "X-Vysted-Exa-Key": exaKey ?? undefined,
    "X-Vysted-Searxng-Url": trimmedUrl !== "" ? trimmedUrl : undefined,
  };
}
