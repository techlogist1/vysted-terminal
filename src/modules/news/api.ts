/**
 * News module sidecar API.
 *
 * Thin typed wrapper over `sidecarGet` for the `/news` endpoint. Built on the
 * shared low-level client (`src/lib/sidecar-client.ts`) rather than editing it,
 * so the news feed owns its own accessor without touching the Phase 1.A
 * contract.
 */

import { sidecarGet } from "@/lib/sidecar-client";

import type { NewsItem } from "../../../types/data";

/**
 * Fetch scored, symbol-tagged news from the sidecar, newest first.
 *
 * @param symbols - watchlist symbols to tag/filter by. When empty, the sidecar
 *   returns general market news tagged against its default watchlist.
 * @param limit - maximum number of items to return (sidecar caps at 200).
 */
export function fetchNews(symbols: string[], limit = 50): Promise<NewsItem[]> {
  return sidecarGet<NewsItem[]>("/news", {
    symbols: symbols.length > 0 ? symbols.join(",") : undefined,
    limit,
  });
}
