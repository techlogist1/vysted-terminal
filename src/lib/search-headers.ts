/**
 * Search-header assembly — the web-search request contract (R9 two-tier).
 *
 * Single source for the search headers every chat / agent request carries so
 * the sidecar can route retrieval + research honestly. The R9 research tier is
 * the ONE authoritative selection:
 *
 *  - `X-Vysted-Research-Tier`   — `tier_a` (Unlimited Local — the default) or
 *                                 `tier_b` (Hosted research model). Sent on
 *                                 every request.
 *  - `X-Vysted-Searxng-Url`     — the custom SearXNG instance URL, sent only
 *                                 when the user set one (empty = the managed
 *                                 instance). Retrieval is ONE local lane, so
 *                                 this rides under either tier.
 *  - `X-Vysted-Openrouter-Key`  — the Tier B BYOK OpenRouter key, read from
 *                                 the OS keychain (the AI-Providers
 *                                 `llm-provider:openrouter` slot) at request
 *                                 time, sent only on tier_b and only when
 *                                 present (FR-036: secret in a header, never
 *                                 the body/query, never persisted/logged).
 *  - `X-Vysted-Research-Models` — the Tier B per-stop research-model map
 *                                 (`normal=…,deep=…,ultra=…`), sent only on
 *                                 tier_b. The sidecar parse mirrors
 *                                 {@link encodeResearchModels} in
 *                                 `config.parse_research_models`.
 *
 * The R7/R8 lanes are dead: no `X-Vysted-Search-Tier`, no `X-Vysted-Exa-Key`,
 * no `X-Vysted-Search-Engine` ride any request anymore (the sidecar still
 * MAPS those legacy headers from third-party callers; this client never sends
 * them).
 *
 * Every value is OMITTED when absent (undefined, never an empty string) so the
 * sidecar sees "no key" / "managed instance" rather than a blank override.
 * Both the REST client (`sidecar-client`) and the SSE client
 * (`chat/streaming`) call this so the header set can never drift between the
 * two transports.
 */

import { getSecret, KEYCHAIN_NAMESPACES } from "@/lib/keychain";
import {
  RESEARCH_STOPS,
  type ResearchModelMap,
  useSearchSettingsStore,
} from "@/store/search-settings";

/** The LLM-provider id whose keychain slot holds the Tier B OpenRouter key. */
const OPENROUTER_PROVIDER_ID = "openrouter";

/**
 * Read the BYOK OpenRouter key from the OS keychain — the SAME `llm-provider:
 * openrouter` slot the Settings AI-Providers section writes, so configuring the
 * provider once lights up the Tier B research lane with no second key entry.
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
 * Encode the per-stop research-model map for the `X-Vysted-Research-Models`
 * header: ordered `stop=slug` pairs joined by commas, e.g.
 * `normal=perplexity/sonar,deep=perplexity/sonar-reasoning-pro,ultra=…`.
 * OpenRouter slugs never contain `,` or `=`, so the encoding needs no escaping;
 * the sidecar drops any malformed pair and floors that stop to its default.
 */
export function encodeResearchModels(models: ResearchModelMap): string {
  return RESEARCH_STOPS.map((stop) => `${stop}=${models[stop]}`).join(",");
}

/**
 * Build the search headers for a sidecar request. Reads the tier + per-stop
 * models + SearXNG URL from the search-settings store (at call time, so a
 * change reflects immediately) and the BYOK key from the keychain. Header
 * values are `undefined` when absent so the caller's header-merge drops them
 * (never an empty string). The keychain is read ONLY for the lane that needs
 * it — tier_a requests never touch the OpenRouter slot.
 */
export async function buildSearchHeaders(): Promise<Record<string, string | undefined>> {
  const { researchTier, searxngUrl, researchModels } = useSearchSettingsStore.getState();

  const tierB = researchTier === "tier_b";
  // A missing key is OMITTED, never sent blank — the sidecar's research lane
  // then stops honestly naming the unlock (retrieval still serves locally).
  const openrouterKey = tierB ? await getOpenrouterApiKey() : null;
  const trimmedUrl = searxngUrl.trim();

  return {
    "X-Vysted-Research-Tier": researchTier,
    "X-Vysted-Searxng-Url": trimmedUrl !== "" ? trimmedUrl : undefined,
    "X-Vysted-Openrouter-Key": tierB ? (openrouterKey ?? undefined) : undefined,
    "X-Vysted-Research-Models": tierB ? encodeResearchModels(researchModels) : undefined,
  };
}
