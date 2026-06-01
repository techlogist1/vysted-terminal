"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Newspaper } from "lucide-react";

import { SidecarError } from "@/lib/sidecar-client";
import { usePanelContextBus } from "@/store/panel-context";
import { useSettingsStore } from "@/store/settings";
import { toNewsSymbol, useSymbolsStore } from "@/store/symbols";

import type { NewsItem } from "../../../types/data";
import { fetchNews } from "./api";

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; items: NewsItem[] };

/** Format an ISO-8601 timestamp as a compact relative age (e.g. "3h", "2d"). */
function relativeTime(iso: string): string {
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
      className={`flex items-center gap-1.5 font-mono text-[11px] ${color}`}
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
            ? "size-1.5 rounded-full bg-current"
            : "size-1.5 rounded-full border border-current bg-transparent"
        }
      />
      <span className="tracking-wide uppercase">{label}</span>
      {score !== null ? (
        <span className="text-charcoal-400">
          {score > 0 ? "+" : ""}
          {score.toFixed(2)}
        </span>
      ) : null}
    </span>
  );
}

/** One row in the feed: headline, source · time, sentiment, symbol tags. */
function NewsRow({ item, onFocus }: { item: NewsItem; onFocus: (id: string) => void }) {
  return (
    <li className="border-charcoal-800 border-b last:border-b-0">
      <a
        href={item.url}
        target="_blank"
        rel="noreferrer"
        onMouseEnter={() => onFocus(item.id)}
        onFocus={() => onFocus(item.id)}
        className="hover:bg-charcoal-850 flex flex-col gap-1.5 px-4 py-3 transition-colors"
      >
        <p className="text-charcoal-100 font-serif text-sm leading-snug">{item.title}</p>
        <div className="flex items-center justify-between gap-3">
          <span className="text-charcoal-400 min-w-0 truncate font-mono text-[11px]">
            {item.source}
            <span className="text-charcoal-600 mx-1.5">·</span>
            {relativeTime(item.published_at)}
          </span>
          <span className="flex-shrink-0">
            <SentimentBadge item={item} />
          </span>
        </div>
        {item.symbols.length > 0 ? (
          <div className="flex flex-wrap gap-1">
            {item.symbols.map((symbol) => (
              <span
                key={symbol}
                className="bg-charcoal-800 rounded-sm px-1.5 py-0.5 font-mono text-[10px] text-amber-400"
              >
                {symbol}
              </span>
            ))}
          </div>
        ) : null}
      </a>
    </li>
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

  // Fetch the feed on mount, whenever the projected symbol list changes, and on
  // a manual refresh. A failed load auto-retries with backoff (1s, 2s, 4s, then
  // capped at 5s for ~12 attempts ≈ 50s) so a cold-boot sidecar bind — the
  // PyInstaller `_MEI` re-exec can take ~30s — self-heals before the terminal
  // error block shows, matching Watchlist's poll-based resilience. The per-run
  // `cancelled` flag drops a superseded/unmounted run's result, and the local
  // `timer` is cleared on cleanup — no setState-after-unmount, no leak.
  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | null = null;
    const attempt = (n: number) => {
      fetchNews(newsSymbols)
        .then((items) => {
          if (!cancelled) {
            setState({ status: "ready", items });
          }
        })
        .catch((error: unknown) => {
          if (cancelled) {
            return;
          }
          if (n < 12) {
            timer = setTimeout(() => attempt(n + 1), Math.min(1000 * 2 ** n, 5000));
            return;
          }
          setState({ status: "error", message: errorMessage(error) });
        });
    };
    attempt(0);
    return () => {
      cancelled = true;
      if (timer) {
        clearTimeout(timer);
      }
    };
    // `newsSymbols` is memoised per symbol list; `refreshNonce` re-triggers a
    // manual refresh; `region` re-fetches on a region switch (region-first feed).
    // (setState lives in async callbacks, never synchronously.)
  }, [newsSymbols, region, refreshNonce]);

  // Manual refresh / retry — surface the loading state, then re-run the effect.
  const refresh = useCallback(() => {
    setState({ status: "loading" });
    setRefreshNonce((n) => n + 1);
  }, []);

  return (
    <div className="bg-charcoal-900 flex h-full w-full flex-col">
      <header className="border-charcoal-700 flex items-center justify-between border-b px-4 py-2.5">
        <h2 className="text-charcoal-200 font-mono text-xs font-medium tracking-wide uppercase">
          News Feed
        </h2>
        <button
          type="button"
          onClick={refresh}
          disabled={state.status === "loading"}
          className="text-charcoal-400 font-mono text-[11px] transition-colors hover:text-amber-400 disabled:pointer-events-none disabled:opacity-40"
        >
          {state.status === "loading" ? "Loading…" : "Refresh"}
        </button>
      </header>

      {state.status === "loading" ? (
        <ul className="flex-1 overflow-y-auto">
          {Array.from({ length: 6 }).map((_, i) => (
            <li
              key={i}
              className="border-charcoal-800 flex animate-pulse flex-col gap-1.5 border-b px-4 py-3"
            >
              <div className="bg-charcoal-800 h-3.5 w-3/4 rounded" />
              <div className="flex gap-3">
                <div className="bg-charcoal-800 h-2.5 w-1/3 rounded" />
                <div className="bg-charcoal-800 ml-auto h-2.5 w-1/5 rounded" />
              </div>
            </li>
          ))}
        </ul>
      ) : null}

      {state.status === "error" ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-3 px-4 text-center">
          <p className="text-negative font-mono text-xs">{state.message}</p>
          <button
            type="button"
            onClick={refresh}
            className="font-mono text-[11px] text-amber-400 transition-colors hover:text-amber-300"
          >
            Retry
          </button>
        </div>
      ) : null}

      {state.status === "ready" ? (
        state.items.length === 0 ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-3 px-6 text-center">
            <Newspaper className="text-charcoal-600 size-8" />
            <p className="text-charcoal-300 font-mono text-xs">No headlines for your watchlist.</p>
            <p className="text-charcoal-500 font-mono text-[11px]">
              Add a NewsAPI key in Settings to pull live articles, or add more symbols to your
              watchlist.
            </p>
            <button
              type="button"
              onClick={refresh}
              className="font-mono text-[11px] text-amber-400 transition-colors hover:text-amber-300"
            >
              Refresh feed
            </button>
          </div>
        ) : (
          <ul className="flex-1 overflow-y-auto">
            {state.items.map((item) => (
              <NewsRow key={item.id} item={item} onFocus={setFocusedArticleId} />
            ))}
          </ul>
        )
      ) : null}
    </div>
  );
}
