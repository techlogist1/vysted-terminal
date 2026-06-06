"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ChevronDown, Download, ListPlus, Plus, X } from "lucide-react";

import { DataTable, type DataColumn } from "@/components/DataTable";
import { Button } from "@/components/ui/button";
import { ProvenanceBadge, StalenessBadge } from "@/components/DataBadges";
import { EmptyState } from "@/components/EmptyState";
import { buildCsv, downloadCsv } from "@/lib/csv";
import { formatPercent, formatPrice } from "@/lib/format";
import { openCompanyOverview } from "@/lib/host-actions";
import { isLiveQuote, useMarketSession } from "@/lib/market-session";
import { SidecarError } from "@/lib/sidecar-client";
import { useTickFlash } from "@/lib/use-flash-value";
import { cn } from "@/lib/utils";
import { usePanelContextBus } from "@/store/panel-context";
import { fetchWatchlistQuotes, type WatchlistRow } from "./api";
import { useSymbolsStore as useWatchlistStore } from "@/store/symbols";

/** Poll interval for quote refreshes — a few seconds keeps it near-real-time. */
const POLL_INTERVAL_MS = 5_000;

/** A signed percent ("+1.31%") — the watchlist change column. */
function fmtChange(value: number): string {
  return formatPercent(value);
}

/** A brief green/red wash on the cell when its number ticks (reduced-motion
 *  aware via {@link useTickFlash}); fades out over the same duration. */
function flashClass(dir: "up" | "down" | null): string {
  if (dir === "up") return "bg-positive/15";
  if (dir === "down") return "bg-negative/15";
  return "bg-transparent";
}

/**
 * The Symbol cell — the ticker plus its provenance / freshness badges and the
 * humanized session label, so a closed/weekend/after-hours price is plainly
 * flagged as not-live (FR-041 / FR-118 / SC-019).
 */
function SymbolCell({ row }: { row: WatchlistRow }) {
  const { entry, quote } = row;
  const session = useMarketSession(quote?.market_state ?? null, quote?.freshness ?? null);
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-charcoal-100 text-body truncate">{entry.symbol}</span>
      {quote !== null && (
        <span className="flex items-center gap-1 overflow-hidden">
          <ProvenanceBadge provider={quote.provider} />
          {quote.freshness != null && <StalenessBadge freshness={quote.freshness} />}
        </span>
      )}
      {session.label !== null && session.tone === "muted" && (
        <span className="text-charcoal-500 text-micro truncate" title={`Session: ${session.label}`}>
          {session.label}
        </span>
      )}
    </div>
  );
}

/**
 * The Price cell — owns its own `useTickFlash` hook so a live tick paints a
 * transient up/down wash (the Bloomberg "it moved" signal a polled terminal
 * otherwise lacks). A stale / closed-session quote never flashes.
 */
function PriceCell({ row }: { row: WatchlistRow }) {
  const { quote } = row;
  const live = isLiveQuote(quote?.freshness);
  const flash = useTickFlash(live ? (quote?.price ?? null) : null);
  return (
    <span
      className={cn(
        "text-charcoal-200 block rounded-sm text-right tabular-nums transition-colors duration-700",
        flashClass(flash),
      )}
    >
      {quote !== null ? formatPrice(quote.price) : "—"}
    </span>
  );
}

/** The Change cell — only a LIVE quote carries the green/red sign colour; a stale
 *  or closed-session change greys to the muted tier so it never reads as a move. */
function ChangeCell({ row }: { row: WatchlistRow }) {
  const { quote } = row;
  const change = quote?.change_percent ?? 0;
  const positive = change >= 0;
  const live = isLiveQuote(quote?.freshness);
  return (
    <span
      className={cn(
        "block text-right tabular-nums",
        quote === null || !live
          ? "text-charcoal-400"
          : positive
            ? "text-positive"
            : "text-negative",
      )}
      title={quote !== null && !live ? "Not a live tick — last known change" : undefined}
    >
      {quote !== null ? fmtChange(change) : "—"}
    </span>
  );
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
  // that don't actually change the symbol list.
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

  // Export the watchlist to CSV — uses the live quotes when they've loaded, else
  // falls back to the tracked symbols alone. No-op on an empty watchlist.
  const handleExport = () => {
    const source: { entry: (typeof entries)[number]; quote: WatchlistRow["quote"] }[] =
      rows ?? entries.map((entry) => ({ entry, quote: null }));
    if (source.length === 0) {
      return;
    }
    const csv = buildCsv(
      ["Symbol", "Asset class", "Price", "Change %", "Provider"],
      source.map(({ entry, quote }) => [
        entry.symbol,
        entry.assetClass,
        quote?.price ?? "",
        quote?.change_percent ?? "",
        quote?.provider ?? "",
      ]),
    );
    downloadCsv("vysted-watchlist.csv", csv);
  };

  const columns = useMemo<DataColumn<WatchlistRow>[]>(
    () => [
      { key: "symbol", header: "Symbol", width: "36%", cell: (row) => <SymbolCell row={row} /> },
      {
        key: "price",
        header: "Price",
        numeric: true,
        width: "32%",
        cell: (row) => <PriceCell row={row} />,
      },
      {
        key: "change",
        header: "Change",
        numeric: true,
        width: "22%",
        cell: (row) => <ChangeCell row={row} />,
      },
      {
        key: "remove",
        action: true,
        width: "10%",
        cell: (row) => (
          <Button
            type="button"
            size="icon-xs"
            variant="ghost"
            aria-label={`Remove ${row.entry.symbol}`}
            onClick={(e) => {
              e.stopPropagation();
              removeSymbol(row.entry.symbol);
            }}
          >
            <X />
          </Button>
        ),
      },
    ],
    [removeSymbol],
  );

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
          className="bg-charcoal-800 text-charcoal-100 placeholder:text-charcoal-400 text-body h-9 flex-1 rounded-md px-3 outline-none focus:ring-1 focus:ring-amber-400"
        />
        <div className="relative">
          <select
            aria-label="Asset class"
            value={draftAssetClass}
            onChange={(event) =>
              setDraftAssetClass(event.target.value === "crypto" ? "crypto" : "equity")
            }
            className="bg-charcoal-800 text-charcoal-200 text-caption h-9 appearance-none rounded-md px-3 pr-6 outline-none focus:ring-1 focus:ring-amber-400"
          >
            <option value="equity">Equity</option>
            <option value="crypto">Crypto</option>
          </select>
          <ChevronDown className="text-charcoal-400 pointer-events-none absolute top-1/2 right-1.5 size-3 -translate-y-1/2" />
        </div>
        <Button type="submit" size="icon-sm" variant="outline" aria-label="Add to watchlist">
          <Plus />
        </Button>
        <Button
          type="button"
          size="icon-sm"
          variant="ghost"
          aria-label="Export watchlist to CSV"
          title="Export watchlist to CSV"
          onClick={handleExport}
          disabled={entries.length === 0}
        >
          <Download />
        </Button>
      </form>

      {error !== null && (
        <div className="border-charcoal-700 flex items-center justify-between border-b px-3 py-2">
          <span className="text-negative text-caption">Could not refresh quotes</span>
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
                  <td className="px-3 py-1.5">
                    <div className="bg-charcoal-800 h-3 w-3/4 animate-pulse rounded-sm" />
                  </td>
                  <td className="px-3 py-1.5">
                    <div className="bg-charcoal-800 ml-auto h-3 w-full animate-pulse rounded-sm" />
                  </td>
                  <td className="px-3 py-1.5">
                    <div className="bg-charcoal-800 ml-auto h-3 w-full animate-pulse rounded-sm" />
                  </td>
                  <td className="px-1 py-1.5" />
                </tr>
              ))}
            </tbody>
          </table>
        ) : rows.length === 0 ? (
          <EmptyState
            icon={ListPlus}
            headline="Your watchlist is empty"
            hint="Add a ticker in the field above to start tracking live quotes."
          />
        ) : (
          <DataTable
            columns={columns}
            rows={rows}
            rowKey={(row) => row.entry.symbol}
            isRowSelected={(row) => selectedSymbol === row.entry.symbol}
            onRowClick={(row) => {
              setSelectedSymbol(row.entry.symbol);
              openCompanyOverview(row.entry.symbol);
            }}
            className={cn(error !== null && "opacity-50")}
            data-testid="watchlist-table"
          />
        )}
      </div>
    </div>
  );
}
