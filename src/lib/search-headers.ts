/**
 * Search-header assembly — the web-search request contract.
 *
 * Single source for the search headers every chat / agent request carries so
 * the sidecar can dispatch web search to the right backend (FR-080/083/084).
 * The legacy trio:
 *  - `X-Vysted-Search-Tier` — the active tier (native / byok-exa / local-searxng);
 *  - `X-Vysted-Exa-Key`     — the BYOK Exa API key, read from the OS keychain at
 *                             request time (FR-036 BYOK: secret in a header,
 *                             never the body/query, never persisted);
 *  - `X-Vysted-Searxng-Url` — the local SearXNG base URL for the local tier.
 *
 * The ADDITIVE R7 research-tier trio (Track R Component 3 — the legacy trio
 * above stays untouched):
 *  - `X-Vysted-Research-Tier`  — the R7 search tier (t1_local / t2_searxng /
 *                                t3_hosted), always sent;
 *  - `X-Vysted-Search-Engine`  — the t3 hosted engine (firecrawl / exa), sent
 *                                only on t3 (the sidecar defaults Firecrawl);
 *  - `X-Vysted-Openrouter-Key` — the t3 BYOK OpenRouter key, read from the OS
 *                                keychain (the AI-Providers `llm-provider:
 *                                openrouter` slot) at request time, sent only
 *                                on t3 and only when present.
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

/** The LLM-provider id whose keychain slot holds the t3 BYOK OpenRouter key. */
const OPENROUTER_PROVIDER_ID = "openrouter";

/**
 * Read the BYOK OpenRouter key from the OS keychain — the SAME `llm-provider:
 * openrouter` slot the Settings AI-Providers section writes, so configuring the
 * provider once lights up the t3 hosted-search tier with no second key entry.
 * Returns `null` when no key is stored or the keychain is unreachable (a miss
 * must never throw into a request), and never an empty string.
 */
export async function getOpenrouterApiKey(): Promise<string | null> {
  try {
    const value = await getSecret(KEYCHAIN_NAMESPACES.llmProvider(OPENROUTER_PROVIDER_ID));
    return value && value.length > 0 ? value : null;
  } catch {
    return null;
  }
}

/**
 * Build the search headers for a sidecar request. Reads the tiers + SearXNG URL
 * from the search-settings store (at call time, so a change reflects
 * immediately) and the BYOK keys from the keychain. Header values are
 * `undefined` when absent so the caller's header-merge drops them (never an
 * empty string). The OpenRouter key is read ONLY when the t3 hosted tier is
 * selected — t1/t2 requests never touch that keychain slot.
 */
export async function buildSearchHeaders(): Promise<Record<string, string | undefined>> {
  const { tier, searxngUrl, researchTier, hostedEngine } = useSearchSettingsStore.getState();
  const exaKey = await getExaApiKey();
  const trimmedUrl = searxngUrl.trim();
  const hosted = researchTier === "t3_hosted";
  const openrouterKey = hosted ? await getOpenrouterApiKey() : null;
  return {
    "X-Vysted-Search-Tier": tier,
    "X-Vysted-Exa-Key": exaKey ?? undefined,
    "X-Vysted-Searxng-Url": trimmedUrl !== "" ? trimmedUrl : undefined,
    "X-Vysted-Research-Tier": researchTier,
    "X-Vysted-Search-Engine": hosted ? hostedEngine : undefined,
    "X-Vysted-Openrouter-Key": hosted ? (openrouterKey ?? undefined) : undefined,
  };
}
