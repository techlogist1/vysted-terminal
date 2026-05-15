"use client";

import { useCallback, useEffect, useState } from "react";
import { Plus, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { SidecarError } from "@/lib/sidecar-client";
import { cn } from "@/lib/utils";
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
  const [draftAssetClass, setDraftAssetClass] = useState<"equity" | "crypto">("equity");

  const refresh = useCallback(async () => {
    try {
      const next = await fetchWatchlistQuotes(entries);
      setRows(next);
      setError(null);
    } catch (err) {
      const message = err instanceof SidecarError ? err.message : "Failed to load watchlist quotes";
      setError(message);
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
        <select
          aria-label="Asset class"
          value={draftAssetClass}
          onChange={(event) =>
            setDraftAssetClass(event.target.value === "crypto" ? "crypto" : "equity")
          }
          className="bg-charcoal-800 text-charcoal-200 h-8 rounded-md px-2 font-mono text-xs outline-none"
        >
          <option value="equity">Equity</option>
          <option value="crypto">Crypto</option>
        </select>
        <Button type="submit" size="icon-sm" variant="outline" aria-label="Add to watchlist">
          <Plus />
        </Button>
      </form>

      {error !== null && (
        <p className="text-negative border-charcoal-700 border-b px-3 py-2 font-mono text-xs">
          {error}
        </p>
      )}

      <div className="flex-1 [scrollbar-gutter:stable] overflow-x-hidden overflow-y-auto">
        {rows === null ? (
          <p className="text-charcoal-400 p-4 font-mono text-xs">Loading quotes…</p>
        ) : rows.length === 0 ? (
          <p className="text-charcoal-400 p-4 font-mono text-xs">No symbols tracked.</p>
        ) : (
          <table className="w-full table-fixed border-collapse">
            <thead>
              <tr className="text-charcoal-400 border-charcoal-700 border-b text-left font-mono text-[0.65rem] uppercase">
                <th className="px-3 py-2 font-medium">Symbol</th>
                <th className="px-3 py-2 text-right font-medium">Price</th>
                <th className="px-3 py-2 text-right font-medium">Change</th>
                <th className="px-3 py-2" />
              </tr>
            </thead>
            <tbody>
              {rows.map(({ entry, quote }) => {
                const change = quote?.change_percent ?? 0;
                const positive = change >= 0;
                return (
                  <tr
                    key={entry.symbol}
                    className="border-charcoal-800 hover:bg-charcoal-800/50 border-b"
                  >
                    <td className="text-charcoal-100 truncate px-3 py-2 font-mono text-sm">
                      {entry.symbol}
                    </td>
                    <td className="text-charcoal-200 px-3 py-2 text-right font-mono text-sm">
                      {quote !== null ? formatPrice(quote.price) : "—"}
                    </td>
                    <td
                      className={cn(
                        "px-3 py-2 text-right font-mono text-sm",
                        quote === null
                          ? "text-charcoal-400"
                          : positive
                            ? "text-positive"
                            : "text-negative",
                      )}
                    >
                      {quote !== null ? formatPercent(change) : "—"}
                    </td>
                    <td className="px-3 py-2 text-right">
                      <Button
                        type="button"
                        size="icon-xs"
                        variant="ghost"
                        aria-label={`Remove ${entry.symbol}`}
                        onClick={() => removeSymbol(entry.symbol)}
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
