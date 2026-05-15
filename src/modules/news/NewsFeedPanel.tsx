"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { SidecarError } from "@/lib/sidecar-client";
import { usePanelContextBus } from "@/store/panel-context";
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
  return "text-charcoal-400";
}

/** A small per-item sentiment badge: coloured dot, label, and signed score. */
function SentimentBadge({ item }: { item: NewsItem }) {
  const color = sentimentColor(item.sentiment_label);
  const label = item.sentiment_label ?? "unscored";
  const score = item.sentiment;
  return (
    <span
      className={`flex items-center gap-1.5 font-mono text-[11px] ${color}`}
      title={score !== null ? `Sentiment score ${score.toFixed(2)}` : "No sentiment score"}
      data-testid="sentiment-badge"
    >
      <span aria-hidden="true" className="size-1.5 rounded-full bg-current" />
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
          <span className="text-charcoal-400 truncate font-mono text-[11px]">
            {item.source}
            <span className="text-charcoal-600 mx-1.5">·</span>
            {relativeTime(item.published_at)}
          </span>
          <SentimentBadge item={item} />
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
  // Stable string key for the symbol list — used as the effect dependency so
  // the fetch re-runs only when the projected list actually changes.
  const symbolsKey = newsSymbols.join(",");

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

  // Fetch the feed and route the result into state. `applyResult` is gated by
  // the caller's cancellation flag so an in-flight request from an unmounted
  // panel (or a superseded refresh) is dropped silently.
  const runFetch = useCallback(
    (applyResult: (next: LoadState) => void) => {
      fetchNews(newsSymbols)
        .then((items) => applyResult({ status: "ready", items }))
        .catch((error: unknown) => applyResult({ status: "error", message: errorMessage(error) }));
    },
    [newsSymbols],
  );

  // Re-fetch whenever the projected symbol list changes (initial mount, plus
  // any add/remove from the shared store). The effect only updates state
  // asynchronously, never synchronously, so the panel renders its initial
  // "loading" state directly and previous results stay on screen until the
  // next fetch resolves (no jarring loading flash when the watchlist mutates).
  useEffect(() => {
    let cancelled = false;
    runFetch((next) => {
      if (!cancelled) {
        setState(next);
      }
    });
    return () => {
      cancelled = true;
    };
    // `runFetch` already closes over `newsSymbols`; depending on `symbolsKey`
    // keeps the effect stable across renders that produce an equal symbol list.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [symbolsKey]);

  // Manual refresh / retry — an event handler, so a synchronous reset to the
  // loading state is fine here.
  const refresh = useCallback(() => {
    setState({ status: "loading" });
    runFetch(setState);
  }, [runFetch]);

  return (
    <div className="bg-charcoal-900 flex h-full w-full flex-col">
      <header className="border-charcoal-700 flex items-center justify-between border-b px-4 py-2.5">
        <h2 className="text-charcoal-200 font-mono text-xs font-medium tracking-wide uppercase">
          News Feed
        </h2>
        <button
          type="button"
          onClick={refresh}
          className="text-charcoal-400 font-mono text-[11px] transition-colors hover:text-amber-400"
        >
          Refresh
        </button>
      </header>

      {state.status === "loading" ? (
        <p className="text-charcoal-400 px-4 py-6 font-mono text-xs">Loading news…</p>
      ) : null}

      {state.status === "error" ? (
        <div className="flex flex-col items-start gap-2 px-4 py-6">
          <p className="text-negative font-mono text-xs">{state.message}</p>
          <button
            type="button"
            onClick={refresh}
            className="text-charcoal-400 font-mono text-[11px] transition-colors hover:text-amber-400"
          >
            Retry
          </button>
        </div>
      ) : null}

      {state.status === "ready" ? (
        state.items.length === 0 ? (
          <p className="text-charcoal-400 px-4 py-6 font-mono text-xs">
            No news for the current watchlist.
          </p>
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
