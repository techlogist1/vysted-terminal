/**
 * Search-header assembly — the web-search request contract (R8).
 *
 * Single source for the search headers every chat / agent request carries so
 * the sidecar can dispatch web search to the right backend. The R7 research
 * tier is the ONE authoritative selection:
 *  - `X-Vysted-Research-Tier`  — the tier (t1_local / t2_searxng / t3_hosted),
 *                                sent on every request EXCEPT the t3
 *                                "Exa direct" sub-mode (below);
 *  - `X-Vysted-Searxng-Url`    — the t2 custom-instance URL, sent only on t2
 *                                and only when the user set one (empty =
 *                                managed instance / autodetect);
 *  - `X-Vysted-Search-Engine`  — the t3 hosted engine (firecrawl / exa), sent
 *                                only on t3 hosted (the sidecar defaults
 *                                Firecrawl);
 *  - `X-Vysted-Openrouter-Key` — the t3 BYOK OpenRouter key, read from the OS
 *                                keychain (the AI-Providers `llm-provider:
 *                                openrouter` slot) at request time, sent only
 *                                on t3 hosted and only when present.
 *
 * The t3 "Exa direct" sub-mode rides the LEGACY wire lane instead: the R7 tier
 * header is deliberately OMITTED (an explicit R7 header always wins on the
 * sidecar) and the request carries `X-Vysted-Search-Tier: byok-exa` +
 * `X-Vysted-Exa-Key` (keychain-sourced, FR-036: secret in a header, never the
 * body/query, never persisted) — the sidecar's mapped legacy lane serves it
 * via the Exa backend.
 *
 * Every value is OMITTED when absent (undefined, never an empty string) so the
 * sidecar sees "no key" / "autodetect" rather than a blank override. Both the
 * REST client (`sidecar-client`) and the SSE client (`chat/streaming`) call
 * this so the header set can never drift between the two transports.
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
 * Build the search headers for a sidecar request. Reads the tier + sub-mode +
 * SearXNG URL from the search-settings store (at call time, so a change
 * reflects immediately) and the BYOK keys from the keychain. Header values are
 * `undefined` when absent so the caller's header-merge drops them (never an
 * empty string). Keychain slots are read ONLY for the lane that needs them —
 * t1/t2 requests never touch the OpenRouter or Exa slots.
 */
export async function buildSearchHeaders(): Promise<Record<string, string | undefined>> {
  const { researchTier, hostedEngine, exaDirect, searxngUrl } = useSearchSettingsStore.getState();

  if (researchTier === "t3_hosted" && exaDirect) {
    // Exa-direct rides the legacy byok-exa lane; the R7 tier header is omitted
    // so the sidecar's legacy mapping (byok-exa → Exa backend) serves it. A
    // missing key is omitted too — the sidecar floors honestly (managed
    // SearXNG when ready, else keyless) and the Settings card names the unlock.
    const exaKey = await getExaApiKey();
    return {
      "X-Vysted-Search-Tier": "byok-exa",
      "X-Vysted-Exa-Key": exaKey ?? undefined,
    };
  }

  const hosted = researchTier === "t3_hosted";
  const openrouterKey = hosted ? await getOpenrouterApiKey() : null;
  const trimmedUrl = searxngUrl.trim();
  return {
    "X-Vysted-Research-Tier": researchTier,
    "X-Vysted-Searxng-Url":
      researchTier === "t2_searxng" && trimmedUrl !== "" ? trimmedUrl : undefined,
    "X-Vysted-Search-Engine": hosted ? hostedEngine : undefined,
    "X-Vysted-Openrouter-Key": hosted ? (openrouterKey ?? undefined) : undefined,
  };
}
