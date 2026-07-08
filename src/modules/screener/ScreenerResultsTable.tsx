"use client";

import { useMemo, useState } from "react";
import { Download, SlidersHorizontal, FilterX, Loader2 } from "lucide-react";

import { cn, DataTable, type DataColumn, type DataTableSort } from "@/components/DataTable";
import { EmptyState } from "@/components/EmptyState";
import {
  currencyAffix,
  formatCompactMoney,
  formatMoney,
  formatPercent,
  formatPrice,
  formatUnit,
} from "@/lib/format";
import { loadSymbolIntoChart, openCompanyOverview } from "@/lib/host-actions";
import { useScreenerStore } from "@/store/screener";

import type { ScreenerResultRow } from "../../../types/screener";

type SortKey =
  | "symbol"
  | "name"
  | "sector"
  | "industry"
  | "market_cap"
  | "pe_ratio"
  | "forward_pe"
  | "roe"
  | "debt_to_equity"
  | "dividend_yield"
  | "price"
  | "change_percent_1d"
  | "volume";

type SortDirection = "asc" | "desc";

/** Format a fraction (0.21) as a percent ("21.0%") with one decimal. */
function fmtFractionPct(value: number | null | undefined): string | null {
  return value == null || Number.isNaN(value) ? null : formatPercent(value * 100).replace("+", "");
}

/** A bare price/ratio (P/E, D/E) — 2dp, graceful null. */
function fmtNumber(value: number | null | undefined): string | null {
  return value == null || Number.isNaN(value) ? null : formatPrice(value, 2);
}

/**
 * A money cell in the ROW's currency (R11 / D57 — the V6 fix: ₹1,293 must
 * never render as $1,293). Sub-unit magnitudes (micro-cap crypto) keep
 * significant digits with the instrument's Intl-derived symbol instead of
 * collapsing to "$0.00"; everything else is the standard money format. A row
 * without a currency (older payload) falls back to the region default,
 * byte-identical to before.
 */
function fmtMoneyCell(
  value: number | null | undefined,
  currency: string | null | undefined,
): string | null {
  if (value == null || Number.isNaN(value)) return null;
  if (value !== 0 && Math.abs(value) < 1) {
    const { prefix, suffix } = currencyAffix(currency);
    return `${prefix}${formatPrice(value)}${suffix}`;
  }
  return formatMoney(value, currency);
}

/** Display label for a routed symbol — strips the Yahoo `.NS`/`.BO` suffix so the
 *  Symbol column reads "RELIANCE", not "RELIANCE.NS" (the leak the operator saw),
 *  while the routed `row.symbol` is kept for the click handler. */
function displaySymbol(symbol: string): string {
  return symbol.replace(/\.(NS|BO)$/i, "");
}

/** Epoch seconds → a short "as of" date ("Jun 16", year appended when not the
 *  current year) for staleness titles. */
function fmtAsOfDate(epochSec: number): string {
  const d = new Date(epochSec * 1000);
  const opts: Intl.DateTimeFormatOptions = { month: "short", day: "numeric" };
  if (d.getFullYear() !== new Date().getFullYear()) {
    opts.year = "numeric";
  }
  return d.toLocaleDateString("en-US", opts);
}

/** True when the row's values were served from a non-live basis (D52). */
function isStaleBasis(r: ScreenerResultRow): boolean {
  return r.data_basis === "snapshot" || r.data_basis === "mixed";
}

/** The staleness marker's hover text — names the basis and the honest as-of. */
function basisTitle(r: ScreenerResultRow): string {
  const what =
    r.data_basis === "snapshot"
      ? "Snapshot basis — served from cached/seed data"
      : "Mixed basis — some fields cached/seed, some live";
  return r.data_as_of ? `${what}, as of ${fmtAsOfDate(r.data_as_of)}` : what;
}

// The screener columns, expressed once for both the table and the CSV. Numeric
// columns right-align + tabular via DataTable; every value runs through format.ts.
const COLUMNS: DataColumn<ScreenerResultRow, SortKey>[] = [
  {
    key: "symbol",
    header: "Symbol",
    sortable: true,
    truncate: true,
    width: "104px",
    // D52: a row served from a stale/seed basis carries a quiet text-micro
    // marker ("snap"/"mixed") whose title states the basis + honest as-of —
    // a snapshot row must never look identical to a live one.
    cell: (r) => (
      <span className="flex items-baseline gap-1">
        <span className="text-charcoal-100 truncate font-medium">{displaySymbol(r.symbol)}</span>
        {isStaleBasis(r) && (
          <span
            className="text-charcoal-500 text-micro shrink-0"
            title={basisTitle(r)}
            data-testid={`basis-marker-${r.symbol}`}
          >
            {r.data_basis === "snapshot" ? "snap" : "mixed"}
          </span>
        )}
      </span>
    ),
    title: (r) => (isStaleBasis(r) ? `${r.symbol} — ${basisTitle(r)}` : r.symbol),
  },
  {
    key: "name",
    header: "Name",
    sortable: true,
    truncate: true,
    width: "22%",
    format: (r) => r.name ?? null,
  },
  {
    key: "sector",
    header: "Sector",
    sortable: true,
    tier: "secondary",
    truncate: true,
    width: "13%",
    format: (r) => r.sector ?? null,
  },
  {
    key: "market_cap",
    header: "Market cap",
    numeric: true,
    sortable: true,
    width: "116px",
    // D57: money formats in the ROW's listing currency, never the region's.
    format: (r) => (r.market_cap == null ? null : formatCompactMoney(r.market_cap, r.currency)),
  },
  {
    key: "pe_ratio",
    header: "P/E",
    numeric: true,
    sortable: true,
    width: "56px",
    format: (r) => fmtNumber(r.pe_ratio),
  },
  {
    key: "forward_pe",
    header: "Fwd P/E",
    numeric: true,
    sortable: true,
    width: "78px",
    format: (r) => fmtNumber(r.forward_pe),
  },
  {
    key: "roe",
    header: "ROE",
    numeric: true,
    sortable: true,
    width: "56px",
    format: (r) => fmtFractionPct(r.roe),
  },
  {
    key: "debt_to_equity",
    header: "D/E",
    numeric: true,
    sortable: true,
    width: "52px",
    format: (r) => fmtNumber(r.debt_to_equity),
  },
  {
    key: "dividend_yield",
    header: "Div",
    numeric: true,
    sortable: true,
    width: "52px",
    format: (r) => fmtFractionPct(r.dividend_yield),
  },
  {
    key: "price",
    header: "Price",
    numeric: true,
    sortable: true,
    width: "84px",
    // D57: a real money format in the row's currency (was a bare number with
    // no symbol at all — the V6 ambiguity).
    format: (r) => fmtMoneyCell(r.price, r.currency),
  },
  {
    key: "change_percent_1d",
    header: "1d %",
    numeric: true,
    sortable: true,
    width: "64px",
    // The one signed/coloured column — green/red by direction, never the accent.
    cell: (r) =>
      r.change_percent_1d === null ? null : (
        <span className={r.change_percent_1d >= 0 ? "text-positive" : "text-negative"}>
          {`${r.change_percent_1d >= 0 ? "+" : ""}${r.change_percent_1d.toFixed(2)}%`}
        </span>
      ),
  },
  {
    key: "volume",
    header: "Volume",
    numeric: true,
    sortable: true,
    width: "78px",
    format: (r) => (r.volume == null ? null : formatUnit(r.volume, 1)),
  },
];

// CSV header order mirrors the on-wire fields (incl. Industry, which is exported
// but not shown). Kept independent of COLUMNS so the export shape never drifts.
// Money values export as RAW numbers; the trailing Currency column (D57) names
// their unit so a mixed-currency universe export is never ambiguous.
const CSV_HEADERS = [
  "Symbol",
  "Name",
  "Sector",
  "Industry",
  "Market cap",
  "P/E",
  "Fwd P/E",
  "ROE",
  "D/E",
  "Div yield",
  "Price",
  "1d %",
  "Volume",
  "Currency",
];

/** Serialise the current result rows to CSV (RFC-4180 quoting) for Excel/Sheets. */
function rowsToCsv(rows: ScreenerResultRow[]): string {
  const esc = (v: unknown): string => {
    const s = v === null || v === undefined ? "" : String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const lines = [CSV_HEADERS.join(",")];
  for (const r of rows) {
    lines.push(
      [
        r.symbol,
        r.name,
        r.sector,
        r.industry,
        r.market_cap,
        r.pe_ratio,
        r.forward_pe,
        r.roe,
        r.debt_to_equity,
        r.dividend_yield,
        r.price,
        r.change_percent_1d,
        r.volume,
        r.currency,
      ]
        .map(esc)
        .join(","),
    );
  }
  return lines.join("\n");
}

function downloadScreenerCsv(rows: ScreenerResultRow[], universe: string): void {
  const blob = new Blob([rowsToCsv(rows)], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `vysted-screener-${universe}.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

// Direction-aware comparator that always pins null/unknown values LAST, in both
// directions. Applying the direction factor only to the value comparison keeps
// nulls sinking regardless of direction (crypto with unknown market cap, etc.).
function compareValue(
  a: ScreenerResultRow,
  b: ScreenerResultRow,
  key: SortKey,
  dir: number,
): number {
  const av = a[key];
  const bv = b[key];
  if (av == null && bv == null) return 0;
  if (av == null) return 1; // null/undefined always last, regardless of direction
  if (bv == null) return -1;
  const base =
    typeof av === "number" && typeof bv === "number"
      ? av - bv
      : String(av).localeCompare(String(bv));
  return base * dir;
}

// Sum of the fixed-px columns plus a floor for the percentage text columns. Below
// this the panel scrolls horizontally; above it the % columns absorb the slack.
const TABLE_MIN_WIDTH = "min-w-[932px]";

export function ScreenerResultsTable() {
  const result = useScreenerStore((s) => s.lastResult);
  const status = useScreenerStore((s) => s.status);
  const runScreener = useScreenerStore((s) => s.runScreener);
  const resetCriteria = useScreenerStore((s) => s.resetCriteria);
  const [sortKey, setSortKey] = useState<SortKey>("market_cap");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");

  const rows = useMemo(() => {
    if (!result) return [];
    const dir = sortDirection === "asc" ? 1 : -1;
    return [...result.rows].sort((a, b) => compareValue(a, b, sortKey, dir));
  }, [result, sortKey, sortDirection]);

  const sort: DataTableSort<SortKey> = { key: sortKey, direction: sortDirection };

  function onHeaderClick(key: SortKey) {
    if (sortKey === key) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    } else {
      setSortKey(key);
      setSortDirection("desc");
    }
  }

  if (status === "loading") {
    return (
      <div className="flex h-full flex-col gap-2">
        <div className="border-charcoal-700 min-h-0 flex-1 overflow-auto rounded-none border">
          <table className={cn("w-full table-fixed", TABLE_MIN_WIDTH)}>
            <colgroup>
              {COLUMNS.map((col) => (
                <col key={col.key} style={col.width ? { width: col.width } : undefined} />
              ))}
            </colgroup>
            <thead className="bg-charcoal-900">
              <tr className="border-charcoal-800 border-b">
                {COLUMNS.map((col) => (
                  <th
                    key={col.key}
                    scope="col"
                    className={cn(
                      "text-micro text-charcoal-400 px-3 py-1",
                      col.numeric ? "text-right" : "text-left",
                    )}
                  >
                    {col.header}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {Array.from({ length: 8 }).map((_, i) => (
                <tr key={i} className="border-charcoal-800 border-b">
                  {COLUMNS.map((col) => (
                    <td key={col.key} className="px-3 py-1">
                      <div
                        className={cn(
                          "bg-charcoal-800 h-4 animate-pulse rounded-none",
                          col.numeric && "ml-auto",
                        )}
                        style={{
                          width: col.numeric
                            ? "60%"
                            : `${50 + ((i * 7 + col.key.length * 3) % 40)}%`,
                        }}
                      />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="text-charcoal-400 text-caption flex items-center gap-2">
          <Loader2 className="size-3 animate-spin" />
          Running screener…
        </div>
      </div>
    );
  }

  if (status === "error" && !result) {
    return (
      <EmptyState
        icon={SlidersHorizontal}
        headline="Could not load results"
        hint="The screener run failed. Retry — if it persists, loosen a criterion or check the data engine."
        cta={{ label: "Retry", onClick: () => void runScreener(), primary: true }}
      />
    );
  }

  if (!result) {
    return (
      <EmptyState
        icon={SlidersHorizontal}
        headline="No results yet"
        hint="Set your criteria above and run the screener to find matching stocks."
        cta={{ label: "Run screener", onClick: () => void runScreener(), primary: true }}
      />
    );
  }

  return (
    <div className="flex h-full flex-col gap-2">
      <div className="text-charcoal-400 text-caption flex shrink-0 flex-wrap items-center justify-between gap-x-3 gap-y-1">
        <span>
          <span className="text-charcoal-100 font-medium">{result.result_count}</span> rows (
          <span className="tabular-nums">{result.evaluated_count}</span> evaluated
          {result.skipped_count > 0 && (
            <>
              , <span className="text-warning tabular-nums">{result.skipped_count} skipped</span>
            </>
          )}
          ,<span className="tabular-nums"> {result.duration_ms.toFixed(0)} ms</span>)
        </span>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => downloadScreenerCsv(rows, result.universe)}
            disabled={rows.length === 0}
            className="text-charcoal-300 text-caption hover:text-charcoal-100 flex items-center gap-1 transition-colors disabled:opacity-40"
            title="Export results to CSV (open in Excel / Sheets)"
          >
            <Download className="size-3" /> Export CSV
          </button>
          <span className="text-micro">{result.universe}</span>
        </div>
      </div>
      <div className="border-charcoal-700 min-h-0 flex-1 overflow-auto rounded-none border">
        {rows.length === 0 ? (
          <EmptyState
            icon={FilterX}
            headline="No rows matched the criteria"
            hint="No stocks in this universe passed every filter. Loosen a threshold or reset to the defaults."
            cta={{ label: "Reset filters", onClick: () => resetCriteria() }}
          />
        ) : (
          <DataTable
            columns={COLUMNS}
            rows={rows}
            rowKey={(r) => r.symbol}
            sort={sort}
            onSort={onHeaderClick}
            stickyHeader
            minWidth={TABLE_MIN_WIDTH}
            onRowClick={(r) => {
              // Row click → the full company overview (the operator's "click any
              // company → one overview page") AND the chart, so the cockpit drills
              // to the row in one click.
              openCompanyOverview(r.symbol);
              loadSymbolIntoChart(r.symbol);
            }}
            data-testid="screener-results-table"
          />
        )}
      </div>
    </div>
  );
}
