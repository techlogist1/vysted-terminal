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
import { useSymbolAutocomplete } from "@/lib/symbol-autocomplete";
import { useContainerWidth } from "@/lib/use-container-width";
import { useTickFlash } from "@/lib/use-flash-value";
import { cn } from "@/lib/utils";
import { usePanelContextBus } from "@/store/panel-context";
import { fetchWatchlistQuotes, type WatchlistRow } from "./api";
import { useSymbolsStore as useWatchlistStore } from "@/store/symbols";

/** Poll interval for quote refreshes — a few seconds keeps it near-real-time. */
const POLL_INTERVAL_MS = 5_000;

/**
 * R8 overflow law §3.2 — the watchlist's explicit column tracks. Price/change
 * are fixed px tracks sized to their widest sane content at the caption step
 * (12px mono · tabular), with the cells' own px-3 padding supplying a ≥8px
 * gutter — price and change can never collide. The symbol column is the one
 * flexible track. When the measured panel is narrower than the tracks' minimum
 * the row drops a column by priority: provenance chips first, then change%;
 * price always survives.
 */
const PRICE_TRACK = "6.5rem"; // fits "61,446.08" + padding at caption/mono
const CHANGE_TRACK = "5.25rem"; // fits "+100.00%" + padding
const ACTION_TRACK = "3rem"; // the 24px remove control + padding
/** Below this measured width the provenance/freshness chips drop (priority 1).
 *  The chips live in the flexible symbol column — the fixed tracks total
 *  ~236px, so this floor leaves the column ≥ ~104px (the "YF" + "EOD" pair). */
const DROP_CHIPS_BELOW = 340;
/** Below this measured width the change% column drops too (priority 2). */
const DROP_CHANGE_BELOW = 300;

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
function SymbolCell({ row, showChips }: { row: WatchlistRow; showChips: boolean }) {
  const { entry, quote } = row;
  const session = useMarketSession(quote?.market_state ?? null, quote?.freshness ?? null);
  return (
    <div className="flex min-w-0 flex-col gap-0.5">
      <span className="text-charcoal-100 text-caption truncate">{entry.symbol}</span>
      {/* Drop-priority 1 (law §3.2): the provenance/freshness chips drop WHOLE
          at narrow widths — never a mid-word clip ("YFINAN"). flex-wrap stacks
          whole chips if an unusually long provider outgrows the column. */}
      {showChips && quote !== null && (
        <span className="flex flex-wrap items-center gap-1 overflow-hidden">
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
        "text-charcoal-200 block text-right tabular-nums transition-colors duration-700",
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
  // Live name/ticker autocomplete (R7): the resolver knows "Route Mobile" ->
  // ROUTE; until now this input never asked it. Equity-only (crypto pairs
  // aren't in the masters); keyboard-navigable; escape/blur dismisses.
  const candidates = useSymbolAutocomplete(draftAssetClass === "equity" ? draft : "");
  const [acOpen, setAcOpen] = useState(false);
  const [acActive, setAcActive] = useState(0);
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

  const pickCandidate = (symbol: string) => {
    addSymbol(symbol, "equity");
    setDraft("");
    setAcOpen(false);
    setAcActive(0);
  };

  const handleAdd = (event: React.FormEvent) => {
    event.preventDefault();
    if (acOpen && candidates.length > 0) {
      pickCandidate(candidates[Math.min(acActive, candidates.length - 1)].symbol);
      return;
    }
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

  // Measured panel width drives the §3.2 drop-priority ladder. `null` (first
  // paint) renders the full layout; the observer corrects on the next frame.
  const { ref: tableAreaRef, width: tableWidth } = useContainerWidth<HTMLDivElement>();
  const showChips = tableWidth === null || tableWidth >= DROP_CHIPS_BELOW;
  const showChange = tableWidth === null || tableWidth >= DROP_CHANGE_BELOW;

  const columns = useMemo<DataColumn<WatchlistRow>[]>(() => {
    const cols: DataColumn<WatchlistRow>[] = [
      // The one flexible track — takes whatever the fixed tracks leave.
      {
        key: "symbol",
        header: "Symbol",
        cell: (row) => <SymbolCell row={row} showChips={showChips} />,
      },
      {
        key: "price",
        header: "Price",
        numeric: true,
        width: PRICE_TRACK,
        cell: (row) => <PriceCell row={row} />,
      },
    ];
    if (showChange) {
      cols.push({
        key: "change",
        header: "Change",
        numeric: true,
        width: CHANGE_TRACK,
        cell: (row) => <ChangeCell row={row} />,
      });
    }
    cols.push({
      key: "remove",
      action: true,
      width: ACTION_TRACK,
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
    });
    return cols;
  }, [removeSymbol, showChips, showChange]);

  return (
    <div className="bg-charcoal-900 flex h-full w-full flex-col">
      <form
        onSubmit={handleAdd}
        className="border-charcoal-700 flex items-center gap-2 border-b p-3"
      >
        <div className="relative flex-1">
          <input
            aria-label="Add symbol"
            placeholder="Add symbol"
            title="Add a ticker or company name"
            value={draft}
            onChange={(event) => {
              setDraft(event.target.value);
              setAcOpen(true);
              setAcActive(0);
            }}
            onFocus={() => setAcOpen(true)}
            onBlur={() => setTimeout(() => setAcOpen(false), 120)}
            onKeyDown={(event) => {
              if (!acOpen || candidates.length === 0) return;
              if (event.key === "ArrowDown") {
                event.preventDefault();
                setAcActive((i) => Math.min(i + 1, candidates.length - 1));
              } else if (event.key === "ArrowUp") {
                event.preventDefault();
                setAcActive((i) => Math.max(i - 1, 0));
              } else if (event.key === "Escape") {
                setAcOpen(false);
              }
            }}
            className="bg-charcoal-800 text-charcoal-100 placeholder:text-charcoal-400 text-body rounded-control focus:ring-charcoal-500 h-8 w-full truncate px-3 outline-none focus:ring-1"
          />
          {acOpen && candidates.length > 0 && (
            <ul
              role="listbox"
              aria-label="Symbol matches"
              className="bg-charcoal-875 border-charcoal-700 rounded-control absolute top-full right-0 left-0 z-20 mt-1 overflow-hidden border"
            >
              {candidates.map((c, i) => (
                <li key={`${c.symbol}-${c.exchange}`}>
                  <button
                    type="button"
                    role="option"
                    aria-selected={i === acActive}
                    onMouseDown={(e) => {
                      e.preventDefault();
                      pickCandidate(c.symbol);
                    }}
                    onMouseEnter={() => setAcActive(i)}
                    className={cn(
                      "flex w-full items-center gap-2 px-3 py-1 text-left",
                      i === acActive ? "bg-charcoal-800" : "bg-transparent",
                    )}
                  >
                    <span className="text-charcoal-100 text-body shrink-0">{c.symbol}</span>
                    <span className="text-charcoal-500 text-micro shrink-0">{c.exchange}</span>
                    <span className="text-charcoal-400 text-caption min-w-0 flex-1 truncate">
                      {c.name}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="relative">
          <select
            aria-label="Asset class"
            value={draftAssetClass}
            onChange={(event) =>
              setDraftAssetClass(event.target.value === "crypto" ? "crypto" : "equity")
            }
            className="bg-charcoal-800 text-charcoal-200 text-caption rounded-control focus:ring-charcoal-500 h-8 appearance-none px-3 pr-6 outline-none focus:ring-1"
          >
            <option value="equity">Equity</option>
            <option value="crypto">Crypto</option>
          </select>
          <ChevronDown className="text-charcoal-400 pointer-events-none absolute top-1/2 right-1.5 size-3 -translate-y-1/2" />
        </div>
        <Button type="submit" size="icon-xs" variant="outline" aria-label="Add to watchlist">
          <Plus />
        </Button>
        <Button
          type="button"
          size="icon-xs"
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

      <div
        ref={tableAreaRef}
        className="flex-1 [scrollbar-gutter:stable] overflow-x-hidden overflow-y-auto"
      >
        {rows === null ? (
          <table className="w-full table-fixed border-collapse">
            <colgroup>
              <col />
              <col style={{ width: PRICE_TRACK }} />
              {showChange && <col style={{ width: CHANGE_TRACK }} />}
              <col style={{ width: ACTION_TRACK }} />
            </colgroup>
            <tbody>
              {Array.from({ length: 5 }).map((_, i) => (
                <tr key={i} className="border-charcoal-800 border-b">
                  <td className="px-3 py-1">
                    <div className="bg-charcoal-800 h-3 w-3/4 animate-pulse rounded-none" />
                  </td>
                  <td className="px-3 py-1">
                    <div className="bg-charcoal-800 ml-auto h-3 w-full animate-pulse rounded-none" />
                  </td>
                  {showChange && (
                    <td className="px-3 py-1">
                      <div className="bg-charcoal-800 ml-auto h-3 w-full animate-pulse rounded-none" />
                    </td>
                  )}
                  <td className="px-1 py-1" />
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
