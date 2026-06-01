"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ArrowUp, ChevronDown, Plus, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { SidecarError } from "@/lib/sidecar-client";
import { cn } from "@/lib/utils";
import { usePanelContextBus } from "@/store/panel-context";
import { fetchWatchlistQuotes, type WatchlistRow } from "./api";
import { useSymbolsStore as useWatchlistStore } from "@/store/symbols";

/** Poll interval for quote refreshes — a few seconds keeps it near-real-time. */
const POLL_INTERVAL_MS = 5_000;

function formatPrice(value: number): string {
  return value.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function formatPercent(value: number): string {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}%`;
}

/**
 * Watchlist panel — pre-loaded symbols with polled near-real-time quotes.
 *
 * Equity quotes refresh through a batched `/quotes` call; crypto quotes poll
 * `/crypto/ticker`. The tracked symbol list lives in the module-local Zustand
 * store so it survives panel remounts.
 */
export function WatchlistPanel() {
  const entries = useWatchlistStore((state) => state.entries);
  const addSymbol = useWatchlistStore((state) => state.addSymbol);
  const removeSymbol = useWatchlistStore((state) => state.removeSymbol);

  // `rows` is `null` until the first refresh resolves — that drives the loading
  // state without a synchronous setState inside the effect. Subsequent entry
  // changes refresh in place rather than flashing the loading view.
  const [rows, setRows] = useState<WatchlistRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [inFlight, setInFlight] = useState(false);
  const inFlightRef = useRef(false);
  const [draftAssetClass, setDraftAssetClass] = useState<"equity" | "crypto">("equity");
  // Tracks the symbol the user last interacted with via the row hover; null
  // when the user has not selected anything yet. Used as the publisher's
  // `selectedSymbol` payload field.
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);

  // --- panel-context bus: publish selection on change ---------------------
  const publishPanelContext = usePanelContextBus((state) => state.publish);
  const unregisterPanelContext = usePanelContextBus((state) => state.unregisterSource);

  // Project the entry list into a primitive-friendly tuple of symbol strings
  // so the effect's deps array stays referentially stable across re-renders
  // that don't actually change the symbol list. The snapshot is re-memoised
  // off `symbolsKey` (a primitive string) so a re-rendered identical list
  // does not mint a fresh array.
  const symbolsKey = useMemo(() => entries.map((e) => e.symbol).join(","), [entries]);
  const symbolsSnapshot = useMemo(
    () => (symbolsKey === "" ? [] : symbolsKey.split(",")),
    [symbolsKey],
  );

  useEffect(() => {
    publishPanelContext({
      source: "watchlist",
      kind: "selection",
      payload: {
        symbols: symbolsSnapshot,
        selectedSymbol,
      },
      emittedAt: Date.now(),
    });
  }, [publishPanelContext, symbolsSnapshot, selectedSymbol]);

  useEffect(() => {
    return () => {
      unregisterPanelContext("watchlist");
    };
  }, [unregisterPanelContext]);

  const refresh = useCallback(async () => {
    if (inFlightRef.current) {
      return;
    }
    inFlightRef.current = true;
    setInFlight(true);
    try {
      const next = await fetchWatchlistQuotes(entries);
      setRows(next);
      setError(null);
    } catch (err) {
      const message = err instanceof SidecarError ? err.message : "Failed to load watchlist quotes";
      setError(message);
    } finally {
      inFlightRef.current = false;
      setInFlight(false);
    }
  }, [entries]);

  useEffect(() => {
    // Polling effect: `refresh` only sets state after an awaited fetch resolves
    // (never synchronously), so the cascading-render concern does not apply.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void refresh();
    const timer = setInterval(() => {
      void refresh();
    }, POLL_INTERVAL_MS);
    return () => {
      clearInterval(timer);
    };
  }, [refresh]);

  const handleAdd = (event: React.FormEvent) => {
    event.preventDefault();
    if (draft.trim() === "") {
      return;
    }
    addSymbol(draft, draftAssetClass);
    setDraft("");
  };

  return (
    <div className="bg-charcoal-900 flex h-full w-full flex-col">
      <form
        onSubmit={handleAdd}
        className="border-charcoal-700 flex items-center gap-2 border-b p-3"
      >
        <input
          aria-label="Add symbol"
          placeholder="Add symbol"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          className="bg-charcoal-800 text-charcoal-100 placeholder:text-charcoal-400 h-8 flex-1 rounded-md px-2 font-mono text-sm outline-none focus:ring-1 focus:ring-amber-400"
        />
        <div className="relative">
          <select
            aria-label="Asset class"
            value={draftAssetClass}
            onChange={(event) =>
              setDraftAssetClass(event.target.value === "crypto" ? "crypto" : "equity")
            }
            className="bg-charcoal-800 text-charcoal-200 h-8 appearance-none rounded-md px-2 pr-6 font-mono text-xs outline-none focus:ring-1 focus:ring-amber-400"
          >
            <option value="equity">Equity</option>
            <option value="crypto">Crypto</option>
          </select>
          <ChevronDown className="text-charcoal-400 pointer-events-none absolute top-1/2 right-1.5 size-3 -translate-y-1/2" />
        </div>
        <Button type="submit" size="icon-sm" variant="outline" aria-label="Add to watchlist">
          <Plus />
        </Button>
      </form>

      {error !== null && (
        <div className="border-charcoal-700 flex items-center justify-between border-b px-3 py-2">
          <span className="text-negative font-mono text-xs">Could not refresh quotes</span>
          <Button
            type="button"
            size="sm"
            variant="ghost"
            onClick={() => void refresh()}
            disabled={inFlight}
          >
            Retry
          </Button>
        </div>
      )}

      <div className="flex-1 [scrollbar-gutter:stable] overflow-x-hidden overflow-y-auto">
        {rows === null ? (
          <table className="w-full table-fixed border-collapse">
            <colgroup>
              <col className="w-[36%]" />
              <col className="w-[32%]" />
              <col className="w-[22%]" />
              <col className="w-[10%]" />
            </colgroup>
            <tbody>
              {Array.from({ length: 5 }).map((_, i) => (
                <tr key={i} className="border-charcoal-800 border-b">
                  <td className="px-2.5 py-2">
                    <div className="bg-charcoal-800 h-3 w-3/4 animate-pulse rounded" />
                  </td>
                  <td className="px-2.5 py-2">
                    <div className="bg-charcoal-800 ml-auto h-3 w-full animate-pulse rounded" />
                  </td>
                  <td className="px-2.5 py-2">
                    <div className="bg-charcoal-800 ml-auto h-3 w-full animate-pulse rounded" />
                  </td>
                  <td className="px-1 py-2" />
                </tr>
              ))}
            </tbody>
          </table>
        ) : rows.length === 0 ? (
          <div className="flex flex-col items-center justify-center gap-2 p-6 text-center">
            <span className="text-charcoal-400 font-mono text-xs">Your watchlist is empty</span>
            <span className="text-charcoal-500 flex items-center gap-1 font-mono text-[0.65rem]">
              <ArrowUp className="size-3" />
              Type a ticker above to start tracking
            </span>
          </div>
        ) : (
          <table
            className={cn("w-full table-fixed border-collapse", error !== null && "opacity-50")}
          >
            {/* Explicit column widths so a squeezed panel never lets Price and
                Change collide (the host-side min-width is the first guard; this
                colgroup + per-cell clip is the second). Symbol gives way first
                (it truncates); the numeric columns hold their room. */}
            <colgroup>
              <col className="w-[36%]" />
              <col className="w-[32%]" />
              <col className="w-[22%]" />
              <col className="w-[10%]" />
            </colgroup>
            <thead>
              <tr className="text-charcoal-400 border-charcoal-700 border-b text-left font-mono text-[0.65rem] uppercase">
                <th className="px-2.5 py-2 font-medium">Symbol</th>
                <th className="px-2.5 py-2 text-right font-medium">Price</th>
                <th className="px-2.5 py-2 text-right font-medium">Change</th>
                <th className="px-1 py-2" />
              </tr>
            </thead>
            <tbody>
              {rows.map(({ entry, quote }) => {
                const change = quote?.change_percent ?? 0;
                const positive = change >= 0;
                const isSelected = selectedSymbol === entry.symbol;
                return (
                  <tr
                    key={entry.symbol}
                    onClick={() => setSelectedSymbol(entry.symbol)}
                    className={cn(
                      "border-charcoal-800 hover:bg-charcoal-800/50 cursor-pointer border-b",
                      isSelected && "bg-charcoal-800/40",
                    )}
                  >
                    <td className="text-charcoal-100 truncate px-2.5 py-2 font-mono text-sm">
                      {entry.symbol}
                    </td>
                    <td className="text-charcoal-200 overflow-hidden px-2.5 py-2 text-right font-mono text-sm text-ellipsis whitespace-nowrap tabular-nums">
                      {quote !== null ? formatPrice(quote.price) : "—"}
                    </td>
                    <td
                      className={cn(
                        "overflow-hidden px-2.5 py-2 text-right font-mono text-sm text-ellipsis whitespace-nowrap tabular-nums",
                        quote === null
                          ? "text-charcoal-400"
                          : positive
                            ? "text-positive"
                            : "text-negative",
                      )}
                    >
                      {quote !== null ? formatPercent(change) : "—"}
                    </td>
                    <td className="px-1 py-2 text-right">
                      <Button
                        type="button"
                        size="icon-xs"
                        variant="ghost"
                        aria-label={`Remove ${entry.symbol}`}
                        onClick={(e) => {
                          e.stopPropagation();
                          removeSymbol(entry.symbol);
                        }}
                      >
                        <X />
                      </Button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
