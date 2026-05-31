/**
 * News module sidecar API.
 *
 * Thin typed wrapper over `sidecarGet` for the `/news` endpoint. Built on the
 * shared low-level client (`src/lib/sidecar-client.ts`).
 *
 * FR-036 BYOK: the optional NewsAPI key (declared on the `vysted-news` data
 * plugin's marketplace entry) is read from the OS keychain and sent as the
 * `X-Vysted-Newsapi-Key` HEADER — never the body/query, never persisted. Absent
 * a key the sidecar serves RSS only, so the header is simply omitted.
 */

import { getSecret, KEYCHAIN_NAMESPACES } from "@/lib/keychain";
import { sidecarGet } from "@/lib/sidecar-client";

import type { NewsItem } from "../../../types/data";

const NEWS_PLUGIN_ID = "vysted-news";
const NEWSAPI_KEY_FIELD = "newsapi_key";

/**
 * Fetch scored, symbol-tagged news from the sidecar, newest first.
 *
 * @param symbols - watchlist symbols to tag/filter by. When empty, the sidecar
 *   returns general market news tagged against its default watchlist.
 * @param limit - maximum number of items to return (sidecar caps at 200).
 */
export async function fetchNews(symbols: string[], limit = 50): Promise<NewsItem[]> {
  // Read the optional BYOK NewsAPI key from the keychain (null when the user
  // never supplied one — RSS-only is the keyless default). A keychain miss must
  // not fail the fetch.
  let newsapiKey: string | null = null;
  try {
    newsapiKey = await getSecret(
      KEYCHAIN_NAMESPACES.pluginSecret(NEWS_PLUGIN_ID, NEWSAPI_KEY_FIELD),
    );
  } catch {
    newsapiKey = null;
  }
  return sidecarGet<NewsItem[]>(
    "/news",
    {
      symbols: symbols.length > 0 ? symbols.join(",") : undefined,
      limit,
    },
    { "X-Vysted-Newsapi-Key": newsapiKey ?? undefined },
  );
}
