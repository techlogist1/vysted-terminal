"use client";

import { useEffect, useMemo, useState } from "react";
import { Calendar, ChevronDown, ChevronRight } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useEarningsStore } from "@/store/earnings";

import type { EarningsEvent } from "../../../types/earnings";
import { EarningsSurpriseChart } from "./EarningsSurpriseChart";
import { EpsEstimateGrid } from "./EpsEstimateGrid";

type SortKey =
  | "scheduled_date"
  | "symbol"
  | "time_of_day"
  | "consensus"
  | "dispersion"
  | "analysts";
type SortDirection = "asc" | "desc";

const TIME_OF_DAY_LABEL: Record<string, string> = {
  "before-open": "Pre-open",
  "during-market": "Intraday",
  "after-close": "After close",
  unknown: "—",
};

function fmt(value: number | null, digits = 2): string {
  if (value === null) return "—";
  return value.toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

function fmtDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function compare(a: number | string, b: number | string, direction: SortDirection): number {
  if (a === b) return 0;
  const cmp = a < b ? -1 : 1;
  return direction === "asc" ? cmp : -cmp;
}

function sortValue(event: EarningsEvent, key: SortKey): number | string {
  switch (key) {
    case "scheduled_date":
      return event.scheduled_date;
    case "symbol":
      return event.symbol;
    case "time_of_day":
      return event.time_of_day;
    case "consensus":
      return event.eps_estimate_mean ?? Number.NEGATIVE_INFINITY;
    case "dispersion":
      return event.eps_estimate_stddev ?? Number.NEGATIVE_INFINITY;
    case "analysts":
      return event.estimate_analyst_count;
  }
}

/**
 * Earnings Calendar panel — Phase 6 (Teammate E).
 *
 * Loads the upcoming-earnings window via the earnings store on mount,
 * lets the user pick the day-window (1–60) and a comma-separated
 * watchlist filter, and renders a sortable table of events. Clicking a
 * row expands an inline drill-down with the surprise-history chart +
 * EPS estimate grid for that symbol.
 */
export function EarningsCalendarPanel() {
  const upcoming = useEarningsStore((s) => s.upcoming);
  const upcomingStatus = useEarningsStore((s) => s.upcomingStatus);
  const upcomingError = useEarningsStore((s) => s.upcomingError);
  const lastDays = useEarningsStore((s) => s.lastDays);
  const lastWatchlist = useEarningsStore((s) => s.lastWatchlist);
  const loadUpcoming = useEarningsStore((s) => s.loadUpcoming);
  const histories = useEarningsStore((s) => s.histories);
  const surprises = useEarningsStore((s) => s.surprises);
  const estimates = useEarningsStore((s) => s.estimates);
  const getHistory = useEarningsStore((s) => s.getHistory);
  const getSurprises = useEarningsStore((s) => s.getSurprises);
  const getEstimates = useEarningsStore((s) => s.getEstimates);

  const [daysDraft, setDaysDraft] = useState<string>(String(lastDays));
  const [watchlistDraft, setWatchlistDraft] = useState<string>(
    lastWatchlist ? lastWatchlist.join(",") : "",
  );
  const [sortKey, setSortKey] = useState<SortKey>("scheduled_date");
  const [sortDirection, setSortDirection] = useState<SortDirection>("asc");
  const [expandedSymbol, setExpandedSymbol] = useState<string | null>(null);

  useEffect(() => {
    if (upcomingStatus === "idle") {
      void loadUpcoming();
    }
  }, [upcomingStatus, loadUpcoming]);

  useEffect(() => {
    if (!expandedSymbol) return;
    void getHistory(expandedSymbol);
    void getSurprises(expandedSymbol);
    void getEstimates(expandedSymbol);
  }, [expandedSymbol, getHistory, getSurprises, getEstimates]);

  const sortedEvents = useMemo(() => {
    if (!upcoming) return [];
    return [...upcoming.events].sort((a, b) =>
      compare(sortValue(a, sortKey), sortValue(b, sortKey), sortDirection),
    );
  }, [upcoming, sortKey, sortDirection]);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDirection((dir) => (dir === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDirection("asc");
    }
  };

  const handleApply = (event: React.FormEvent) => {
    event.preventDefault();
    const days = Math.max(1, Math.min(60, Number.parseInt(daysDraft, 10) || 7));
    const watchlist = watchlistDraft
      .split(",")
      .map((s) => s.trim())
      .filter((s) => s.length > 0);
    void loadUpcoming(days, watchlist.length > 0 ? watchlist : null);
  };

  return (
    <div className="bg-charcoal-900 flex h-full w-full flex-col">
      <form
        onSubmit={handleApply}
        className="border-charcoal-700 flex flex-wrap items-center gap-2 border-b p-3"
      >
        <label className="text-charcoal-300 font-mono text-xs">
          Window (days)
          <input
            type="number"
            min={1}
            max={60}
            value={daysDraft}
            onChange={(e) => setDaysDraft(e.target.value)}
            className="bg-charcoal-800 text-charcoal-100 ml-2 h-7 w-16 rounded-md px-2 font-mono text-xs outline-none focus:ring-1 focus:ring-amber-400"
            aria-label="Window in days"
          />
        </label>
        <label className="text-charcoal-300 flex-1 font-mono text-xs">
          Watchlist (comma-separated)
          <input
            type="text"
            value={watchlistDraft}
            onChange={(e) => setWatchlistDraft(e.target.value)}
            placeholder="AAPL, MSFT, NVDA"
            className="bg-charcoal-800 text-charcoal-100 placeholder:text-charcoal-500 ml-2 h-7 w-full max-w-xs rounded-md px-2 font-mono text-xs outline-none focus:ring-1 focus:ring-amber-400"
            aria-label="Watchlist"
          />
        </label>
        <Button type="submit" size="sm" variant="outline" disabled={upcomingStatus === "loading"}>
          <Calendar />
          Apply
        </Button>
      </form>

      {upcomingError !== null && (
        <p className="text-negative border-charcoal-700 border-b px-3 py-2 font-mono text-xs">
          {upcomingError}
        </p>
      )}

      <div className="flex-1 [scrollbar-gutter:stable] overflow-x-hidden overflow-y-auto p-3">
        {upcomingStatus === "loading" ? (
          <p className="text-charcoal-400 font-mono text-xs">Loading earnings calendar…</p>
        ) : sortedEvents.length === 0 ? (
          <p className="text-charcoal-400 font-mono text-xs">
            No upcoming earnings in this window.
          </p>
        ) : (
          <table className="w-full table-fixed border-collapse">
            <colgroup>
              <col style={{ width: "5%" }} />
              <col style={{ width: "16%" }} />
              <col style={{ width: "14%" }} />
              <col style={{ width: "23%" }} />
              <col style={{ width: "16%" }} />
              <col style={{ width: "14%" }} />
              <col style={{ width: "12%" }} />
            </colgroup>
            <thead>
              <tr className="text-charcoal-400 border-charcoal-800 border-b text-left font-mono text-[0.6rem] uppercase">
                <th aria-hidden className="px-1 py-1.5" />
                <SortableHeader
                  label="Symbol"
                  active={sortKey === "symbol"}
                  direction={sortDirection}
                  onSort={() => handleSort("symbol")}
                />
                <SortableHeader
                  label="Date"
                  active={sortKey === "scheduled_date"}
                  direction={sortDirection}
                  onSort={() => handleSort("scheduled_date")}
                />
                <SortableHeader label="Company" active={false} direction="asc" disabled />
                <SortableHeader
                  label="Time"
                  active={sortKey === "time_of_day"}
                  direction={sortDirection}
                  onSort={() => handleSort("time_of_day")}
                />
                <SortableHeader
                  label="Consensus EPS"
                  active={sortKey === "consensus"}
                  direction={sortDirection}
                  onSort={() => handleSort("consensus")}
                  align="right"
                />
                <SortableHeader
                  label="Dispersion / # analysts"
                  active={sortKey === "dispersion"}
                  direction={sortDirection}
                  onSort={() => handleSort("dispersion")}
                  align="right"
                />
              </tr>
            </thead>
            <tbody>
              {sortedEvents.map((event) => {
                const isExpanded = expandedSymbol === event.symbol;
                return (
                  <>
                    <tr
                      key={event.symbol}
                      onClick={() =>
                        setExpandedSymbol((current) =>
                          current === event.symbol ? null : event.symbol,
                        )
                      }
                      className="border-charcoal-800 hover:bg-charcoal-800 cursor-pointer border-b font-mono text-xs"
                      data-testid={`earnings-row-${event.symbol}`}
                    >
                      <td className="text-charcoal-400 px-1 py-1.5">
                        {isExpanded ? (
                          <ChevronDown className="size-3" />
                        ) : (
                          <ChevronRight className="size-3" />
                        )}
                      </td>
                      <td className="px-3 py-1.5 font-semibold text-amber-400">{event.symbol}</td>
                      <td className="text-charcoal-100 px-3 py-1.5">
                        {fmtDate(event.scheduled_date)}
                      </td>
                      <td
                        className="text-charcoal-200 truncate px-3 py-1.5"
                        title={event.company_name ?? ""}
                      >
                        {event.company_name ?? "—"}
                      </td>
                      <td className="text-charcoal-200 px-3 py-1.5">
                        {TIME_OF_DAY_LABEL[event.time_of_day] ?? event.time_of_day}
                      </td>
                      <td className="text-charcoal-100 px-3 py-1.5 text-right">
                        {fmt(event.eps_estimate_mean)}
                      </td>
                      <td className="text-charcoal-200 px-3 py-1.5 text-right">
                        {fmt(event.eps_estimate_stddev, 3)} / {event.estimate_analyst_count}
                      </td>
                    </tr>
                    {isExpanded && (
                      <tr key={`${event.symbol}-drill`} className="border-charcoal-800 border-b">
                        <td colSpan={7} className="bg-charcoal-950 px-4 py-3">
                          <div className="flex flex-col gap-3">
                            <div className="flex flex-col gap-1">
                              <h4 className="text-charcoal-200 font-mono text-xs uppercase">
                                {event.symbol} — Last quarters&apos; surprises
                              </h4>
                              <EarningsSurpriseChart
                                surprises={surprises[event.symbol]?.surprises ?? []}
                              />
                            </div>
                            <div className="flex flex-col gap-1">
                              <h4 className="text-charcoal-200 font-mono text-xs uppercase">
                                Next-quarter estimate detail
                              </h4>
                              <EpsEstimateGrid estimate={estimates[event.symbol] ?? null} />
                            </div>
                            {histories[event.symbol] !== undefined && (
                              <p className="text-charcoal-500 font-mono text-[0.65rem]">
                                History rows cached: {histories[event.symbol]?.history.length ?? 0}
                              </p>
                            )}
                          </div>
                        </td>
                      </tr>
                    )}
                  </>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function SortableHeader({
  label,
  active,
  direction,
  onSort,
  disabled,
  align,
}: {
  label: string;
  active: boolean;
  direction: SortDirection;
  onSort?: () => void;
  disabled?: boolean;
  align?: "right";
}) {
  return (
    <th
      className={`px-3 py-1.5 font-medium ${align === "right" ? "text-right" : "text-left"} ${
        disabled ? "cursor-default" : "cursor-pointer"
      }`}
      onClick={disabled ? undefined : onSort}
      aria-sort={active ? (direction === "asc" ? "ascending" : "descending") : "none"}
    >
      {label}
      {active && <span className="text-amber-400"> {direction === "asc" ? "▲" : "▼"}</span>}
    </th>
  );
}
