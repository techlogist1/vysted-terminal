/**
 * Web-search contracts — citation shapes + the LEGACY tier vocabulary.
 *
 * R8 (settings-truth): the R7 research tier (`t1_local` / `t2_searxng` /
 * `t3_hosted`, `src/store/search-settings.ts`) is the ONE authoritative
 * web-search preference. The legacy three-tier vocabulary below survives for
 * two jobs only:
 *  - migrating pre-R8 workspace blobs (`tier` → `researchTier`, see
 *    `migrateSearchSettings`), and
 *  - the `X-Vysted-Search-Tier: byok-exa` wire lane the t3 "Exa direct"
 *    sub-mode rides (the sidecar maps it onto the Exa backend).
 *
 * This module is the FRONTEND contract: the legacy tier id and the normalized
 * citation shapes a search result carries. The sidecar mirrors these by hand
 * (the `types/data.ts ⇄ sidecar/models/` discipline). Kept dependency-free so
 * any panel, the chat sources tray (B4), or a plugin can import it without a
 * cycle.
 */

/**
 * The LEGACY (pre-R8) search tiers. No UI writes this anymore — it persists in
 * old workspace blobs (migrated on restore) and as the wire value of the
 * `X-Vysted-Search-Tier` header for the Exa-direct lane.
 */
export type SearchTier = "native" | "byok-exa" | "local-searxng";

/** The complete set of legacy tiers — for blob validation/migration. */
export const SEARCH_TIERS: readonly SearchTier[] = ["native", "byok-exa", "local-searxng"];

/** The legacy default (what a pre-R8 blob means when the field is absent). */
export const DEFAULT_SEARCH_TIER: SearchTier = "native";

/** Type guard for a persisted legacy tier (older/garbled blobs → default). */
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
