/**
 * Web-search contracts — the three-tier search layer (FR-080/083/084).
 *
 * Vysted offers web search across three user-selectable tiers, each a search
 * backend behind a common interface:
 *  - `native`        — the active model's server-side web search on the user's
 *                      existing provider key (FR-081);
 *  - `byok-exa`      — a BYOK search API (Exa is the default backend, FR-083);
 *  - `local-searxng` — a local/private SearXNG instance, no data leaving the
 *                      machine (FR-084).
 *
 * This module is the FRONTEND contract: the tier id and the normalized citation
 * shapes a search result carries. The sidecar mirrors these by hand (the
 * `types/data.ts ⇄ sidecar/models/` discipline). Kept dependency-free so any
 * panel, the chat sources tray (B4), or a plugin can import it without a cycle.
 */

/**
 * The three user-selectable search tiers (FR-080). The tier rides every chat /
 * agent request as the `X-Vysted-Search-Tier` header; the sidecar dispatches to
 * the matching backend. `native` is the default where the active model supports
 * server-side web search.
 */
export type SearchTier = "native" | "byok-exa" | "local-searxng";

/** The complete, ordered set of tiers — for pickers and validation. */
export const SEARCH_TIERS: readonly SearchTier[] = ["native", "byok-exa", "local-searxng"];

/** The default tier a fresh install starts from (native-on-your-key, FR-081). */
export const DEFAULT_SEARCH_TIER: SearchTier = "native";

/** Human-readable labels for the search-tier picker. */
export const SEARCH_TIER_LABELS: Record<SearchTier, string> = {
  native: "Native (model's web search)",
  "byok-exa": "BYOK search API (Exa)",
  "local-searxng": "Local / private (SearXNG)",
};

/** Type guard for restoring a persisted tier (older/garbled blobs → default). */
export function isSearchTier(value: unknown): value is SearchTier {
  return typeof value === "string" && (SEARCH_TIERS as readonly string[]).includes(value);
}

/**
 * One normalized web-search citation, backend-agnostic. Every tier (native /
 * Exa / SearXNG) maps its raw result into this shape so the chat sources tray
 * (B4) and any agent rendering stays backend-neutral.
 */
export interface Citation {
  /** The canonical URL of the cited source. */
  url: string;
  /** The page / document title. */
  title: string;
  /** A short snippet supporting the claim it backs. */
  excerpt: string;
}

/**
 * A search-result row as surfaced in the future sources tray (B4 builds the
 * tray; this type just defines its shape). Extends a {@link Citation} with the
 * provenance + relevance metadata a tray row renders, all optional so a sparse
 * backend response still maps cleanly.
 */
export interface SearchSourceItem extends Citation {
  /** Which tier produced this result — for a per-row provenance badge. */
  tier?: SearchTier;
  /** The publication / source name (e.g. "Reuters"), when the backend reports it. */
  source?: string;
  /** ISO-8601 publish timestamp, when known. */
  publishedAt?: string;
  /** Backend relevance score (0–1), when the backend reports one. */
  score?: number;
}
