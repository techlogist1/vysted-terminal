"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";
import { Newspaper } from "lucide-react";

import { EmptyState } from "@/components/EmptyState";
import { Button } from "@/components/ui/button";
import { loadSymbolIntoChart } from "@/lib/host-actions";
import { STAGGER, tween } from "@/lib/motion";
import { SidecarError } from "@/lib/sidecar-client";
import { useRetryOnSidecarReady } from "@/lib/use-sidecar-retry";
import { usePanelContextBus } from "@/store/panel-context";
import { useSettingsStore } from "@/store/settings";
import { toNewsSymbol, useSymbolsStore } from "@/store/symbols";

import type { NewsItem } from "../../../types/data";
import { fetchNews, fetchNewsSourcesStatus } from "./api";

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; items: NewsItem[] };

/** Format an ISO-8601 timestamp as a compact relative age (e.g. "3h", "2d"). */
function relativeTime(iso: string | null): string {
  if (iso === null) {
    return "date unknown";
  }
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) {
    return "";
  }
  const seconds = Math.max(0, Math.floor((Date.now() - then) / 1000));
  if (seconds < 60) {
    return "now";
  }
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) {
    return `${minutes}m`;
  }
  const hours = Math.floor(minutes / 60);
  if (hours < 24) {
    return `${hours}h`;
  }
  const days = Math.floor(hours / 24);
  return `${days}d`;
}

/** Resolve the Tailwind text colour token for a sentiment label. */
function sentimentColor(label: string | null): string {
  if (label === "positive") {
    return "text-positive";
  }
  if (label === "negative") {
    return "text-negative";
  }
  // `neutral` is a scored, in-range result — 1 stop brighter than unscored null
  if (label === "neutral") {
    return "text-charcoal-300";
  }
  return "text-charcoal-400";
}

/** A small per-item sentiment badge: coloured dot, label, and signed score. */
function SentimentBadge({ item }: { item: NewsItem }) {
  const color = sentimentColor(item.sentiment_label);
  const label = item.sentiment_label ?? "unscored";
  const score = item.sentiment;
  const scored = item.sentiment_label !== null;
  return (
    <span
      className={`text-micro flex shrink-0 items-center gap-1 whitespace-nowrap ${color}`}
      title={score !== null ? `Sentiment score ${score.toFixed(2)}` : "No sentiment score"}
      data-testid="sentiment-badge"
    >
      {/* A filled dot reads as a confident signal; the unscored state instead
          shows a hollow outline so a near-invisible muted fill never implies a
          neutral/positive read where none was computed. */}
      <span
        aria-hidden="true"
        className={
          scored
            ? "size-2 shrink-0 rounded-full bg-current"
            : "size-2 shrink-0 rounded-full border border-current bg-transparent"
        }
      />
      <span className="tracking-wide uppercase">{label}</span>
      {score !== null ? (
        <span className="text-charcoal-400 tabular-nums">
          {score > 0 ? "+" : ""}
          {score.toFixed(2)}
        </span>
      ) : null}
    </span>
  );
}

/** One row in the feed: headline, source · time, sentiment, symbol tags. */
function NewsRow({
  item,
  index,
  onFocus,
}: {
  item: NewsItem;
  index: number;
  onFocus: (id: string) => void;
}) {
  return (
    <motion.li
      className="border-charcoal-800 border-b last:border-b-0"
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      // Staggered fade-in so a fresh feed cascades in rather than popping (the
      // global MotionConfig reducedMotion="user" gate zeroes this when the user
      // prefers reduced motion). Capped so a long feed doesn't crawl in.
      transition={{ ...tween(0.2), delay: Math.min(index, 8) * STAGGER }}
    >
      <a
        href={item.url}
        target="_blank"
        rel="noreferrer"
        onMouseEnter={() => onFocus(item.id)}
        onFocus={() => onFocus(item.id)}
        className="hover:bg-charcoal-850 flex flex-col gap-2 px-4 py-3 transition-colors"
      >
        <p className="text-charcoal-100 text-body leading-snug">{item.title}</p>
        {/* Meta row (R8 §3.4): the source truncates honestly, the sentiment
            chip never shrinks, and at widths where both can't share the line
            the row WRAPS to a second line — it never clips vertically. */}
        <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
          <span className="text-charcoal-500 text-caption min-w-0 flex-1 basis-32 truncate">
            {item.source}
            <span className="text-charcoal-500 mx-2">·</span>
            {relativeTime(item.published_at)}
          </span>
          <SentimentBadge item={item} />
        </div>
      </a>
      {item.symbols.length > 0 ? (
        // Sibling of the anchor, not nested inside it (R15-AGENT-053): a
        // <button> inside an <a> is invalid interactive nesting, and it was
        // swallowing every symbol click as a navigation to the article.
        <div className="flex flex-wrap gap-1 px-4 pb-3">
          {item.symbols.map((symbol) => (
            <button
              key={symbol}
              type="button"
              aria-label={`Load ${symbol} in chart`}
              title={`Load ${symbol} into the chart`}
              onClick={() => loadSymbolIntoChart(symbol)}
              className="bg-charcoal-800 rounded-control text-micro text-charcoal-300 hover:text-charcoal-100 focus-visible:ring-charcoal-500/70 px-1 py-0.5 transition-colors focus-visible:ring-1 focus-visible:outline-none"
            >
              {symbol}
            </button>
          ))}
        </div>
      ) : null}
    </motion.li>
  );
}

/** Map any fetch rejection to a user-facing error message. */
function errorMessage(error: unknown): string {
  return error instanceof SidecarError
    ? `Sidecar error ${error.status}: ${error.message}`
    : "Could not reach the news service.";
}

/**
 * News Feed panel — a scrollable feed of news items, each scored with a
 * lexicon sentiment indicator and tagged with the watchlist symbols it
 * mentions. Filtered to the current shared watchlist (`useSymbolsStore`):
 * adding or removing a symbol re-fetches the feed.
 */
export function NewsFeedPanel() {
  const entries = useSymbolsStore((state) => state.entries);
  // Project stored entries into the news feed's symbol form (crypto pairs
  // collapse to their base asset, e.g. `BTC/USDT` → `BTC`). Memoised so the
  // fetch effect's dependency is stable as long as the symbol list does not
  // change.
  const newsSymbols = useMemo(() => entries.map(toNewsSymbol), [entries]);
  // The active region (Pass A/B locale + region-first feeds). Switching it must
  // re-fetch: the header is already locale-aware, but the feed itself becomes
  // region-first as the sidecar grows region routing, so a region change should
  // pull a fresh list — not leave a stale US feed under an India locale.
  const region = useSettingsStore((s) => s.region);

  const [state, setState] = useState<LoadState>({ status: "loading" });
  // R15-DATA-094: a saved NewsAPI key can go bad (revoked, quota reset) without
  // the feed itself erroring — RSS keeps the panel populated, so the only sign
  // is this badge. `null` = not yet checked or the check itself failed; never
  // blocks the feed, it is purely informational.
  const [newsApiStatus, setNewsApiStatus] = useState<
    "ok" | "unauthorized" | "error" | "absent" | null
  >(null);
  // Tracks the article the user last hovered/focused on; `null` when nothing
  // is focused. Surfaced through the panel-context bus so the chat sidebar
  // can mention the focused headline in the agent's preamble.
  const [focusedArticleId, setFocusedArticleId] = useState<string | null>(null);

  // --- panel-context bus: publish snapshot on change ----------------------
  const publishPanelContext = usePanelContextBus((s) => s.publish);
  const unregisterPanelContext = usePanelContextBus((s) => s.unregisterSource);

  useEffect(() => {
    publishPanelContext({
      source: "news",
      kind: "snapshot",
      payload: {
        watchedSymbols: newsSymbols,
        focusedArticleId,
      },
      emittedAt: Date.now(),
    });
    // Effect deps:
    //   - `newsSymbols` is memoised from `entries` so it's stable per list
    //   - `focusedArticleId` is a primitive
    //   - `publishPanelContext` is a stable Zustand action ref
  }, [publishPanelContext, newsSymbols, focusedArticleId]);

  useEffect(() => {
    return () => {
      unregisterPanelContext("news");
    };
  }, [unregisterPanelContext]);

  // Manual-refresh nonce — bumping it re-runs the fetch effect. Kept as state
  // (not a ref) so the effect that owns the fetch lifecycle reacts to it.
  const [refreshNonce, setRefreshNonce] = useState(0);

  // Fetch the feed on mount, whenever the projected symbol list changes, on a
  // region switch (region-first feed) and on a manual refresh. The shared
  // cold-boot hook retries only while the engine is not up yet; an answer it
  // gave (a 502 from every news source) settles at once in the error state
  // (R15-UI-015). Only the newest load commits, so a superseded symbol list's
  // late response never overwrites the current feed.
  const loadGenerationRef = useRef(0);
  const loadFeed = useCallback(async () => {
    const generation = ++loadGenerationRef.current;
    try {
      const items = await fetchNews(newsSymbols);
      if (generation === loadGenerationRef.current) {
        setState({ status: "ready", items });
      }
    } catch (error: unknown) {
      if (generation === loadGenerationRef.current) {
        setState({ status: "error", message: errorMessage(error) });
      }
      throw error;
    }
  }, [newsSymbols]);
  useRetryOnSidecarReady(loadFeed, [newsSymbols, region, refreshNonce]);

  // A lightweight, independent probe (R15-DATA-094) — never blocks/affects the
  // feed load above; a rejection just leaves the badge unset.
  useEffect(() => {
    let cancelled = false;
    fetchNewsSourcesStatus()
      .then((status) => {
        if (!cancelled) setNewsApiStatus(status.newsapi);
      })
      .catch(() => {
        if (!cancelled) setNewsApiStatus(null);
      });
    return () => {
      cancelled = true;
    };
  }, [refreshNonce]);

  // Manual refresh / retry — surface the loading state, then re-run the effect.
  const refresh = useCallback(() => {
    setState({ status: "loading" });
    setRefreshNonce((n) => n + 1);
  }, []);

  return (
    <div className="bg-charcoal-900 flex h-full w-full flex-col">
      <header className="border-charcoal-700 flex items-center justify-between border-b px-4 py-2">
        <div className="flex items-center gap-2">
          <h2 className="text-charcoal-200 text-micro">News Feed</h2>
          {(newsApiStatus === "unauthorized" || newsApiStatus === "error") && (
            <span
              className="text-negative text-micro"
              data-testid="newsapi-status-badge"
              title="Your saved NewsAPI key is no longer working — check it in Settings → Marketplace"
            >
              NewsAPI key rejected
            </span>
          )}
        </div>
        <Button
          type="button"
          size="xs"
          variant="ghost"
          onClick={refresh}
          disabled={state.status === "loading"}
        >
          {state.status === "loading" ? "Loading…" : "Refresh"}
        </Button>
      </header>

      {state.status === "loading" ? (
        <ul className="flex-1 overflow-y-auto">
          {Array.from({ length: 6 }).map((_, i) => (
            <li
              key={i}
              className="border-charcoal-800 flex animate-pulse flex-col gap-2 border-b px-4 py-3"
            >
              <div className="bg-charcoal-800 h-4 w-3/4 rounded-none" />
              <div className="flex gap-3">
                <div className="bg-charcoal-800 h-3 w-1/3 rounded-none" />
                <div className="bg-charcoal-800 ml-auto h-3 w-1/5 rounded-none" />
              </div>
            </li>
          ))}
        </ul>
      ) : null}

      {state.status === "error" ? (
        <div className="min-h-0 flex-1 overflow-y-auto">
          <EmptyState
            icon={Newspaper}
            headline="Could not load the news feed"
            hint={state.message}
            cta={{ label: "Retry", primary: true, onClick: refresh }}
          />
        </div>
      ) : null}

      {state.status === "ready" ? (
        state.items.length === 0 ? (
          <div className="min-h-0 flex-1 overflow-y-auto">
            <EmptyState
              icon={Newspaper}
              headline="No headlines for your watchlist."
              hint="Add a NewsAPI key in Settings to pull live articles, or add more symbols to your watchlist."
              cta={{ label: "Refresh feed", onClick: refresh }}
            />
          </div>
        ) : (
          <ul className="flex-1 overflow-y-auto">
            {state.items.map((item, index) => (
              <NewsRow key={item.id} item={item} index={index} onFocus={setFocusedArticleId} />
            ))}
          </ul>
        )
      ) : null}
    </div>
  );
}
