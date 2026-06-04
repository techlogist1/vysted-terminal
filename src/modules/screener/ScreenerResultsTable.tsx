"use client";

import { useMemo, useState } from "react";
import { Download, SlidersHorizontal, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
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

const COLUMNS: { key: SortKey; label: string; numeric: boolean }[] = [
  { key: "symbol", label: "Symbol", numeric: false },
  { key: "name", label: "Name", numeric: false },
  { key: "sector", label: "Sector", numeric: false },
  { key: "market_cap", label: "Market cap", numeric: true },
  { key: "pe_ratio", label: "P/E", numeric: true },
  { key: "forward_pe", label: "Fwd P/E", numeric: true },
  { key: "roe", label: "ROE", numeric: true },
  { key: "debt_to_equity", label: "D/E", numeric: true },
  { key: "dividend_yield", label: "Div", numeric: true },
  { key: "price", label: "Price", numeric: true },
  { key: "change_percent_1d", label: "1d %", numeric: true },
  { key: "volume", label: "Volume", numeric: true },
];

function fmtMarketCap(value: number | null | undefined): string {
  if (value == null) return "—";
  if (value >= 1_000_000_000_000) return `${(value / 1_000_000_000_000).toFixed(2)}T`;
  if (value >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(2)}B`;
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(2)}M`;
  return value.toLocaleString("en-US");
}

function fmtNumber(value: number | null | undefined, digits = 2): string {
  if (value == null) return "—";
  return value.toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

function fmtVolume(value: number | null | undefined): string {
  if (value == null) return "—";
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return value.toLocaleString("en-US");
}

/** Format a fraction (0.21) as a percent ("21.0%"). */
function fmtPct(value: number | null | undefined): string {
  return value == null || Number.isNaN(value) ? "—" : `${(value * 100).toFixed(1)}%`;
}

/** Display label for a routed symbol — strips the Yahoo `.NS`/`.BO` suffix so the
 *  Symbol column reads "RELIANCE", not "RELIANCE.NS" (the leak the operator saw),
 *  while the routed `row.symbol` is kept for the click handler. */
function displaySymbol(symbol: string): string {
  return symbol.replace(/\.(NS|BO)$/i, "");
}

/** Serialise the current result rows to CSV (RFC-4180 quoting) for Excel/Sheets. */
function rowsToCsv(rows: ScreenerResultRow[]): string {
  const headers = [
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
  ];
  const esc = (v: unknown): string => {
    const s = v === null || v === undefined ? "" : String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const lines = [headers.join(",")];
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
// directions. The previous code sorted ascending then `.reverse()`d the whole
// array, which flipped the null partition to the TOP on the default desc sort —
// so unknown-market-cap rows (common for crypto) floated above real results
// (hunt-state-logic). Applying the direction factor only to the value
// comparison keeps nulls sinking regardless of direction.
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

const TABLE_HEADER_COLS = (
  <colgroup>
    <col style={{ width: "60px" }} />
    <col style={{ width: "22%" }} />
    <col style={{ width: "13%" }} />
    <col style={{ width: "80px" }} />
    <col style={{ width: "56px" }} />
    <col style={{ width: "64px" }} />
    <col style={{ width: "56px" }} />
    <col style={{ width: "52px" }} />
    <col style={{ width: "52px" }} />
    <col style={{ width: "72px" }} />
    <col style={{ width: "64px" }} />
    <col style={{ width: "72px" }} />
  </colgroup>
);

export function ScreenerResultsTable() {
  const result = useScreenerStore((s) => s.lastResult);
  const status = useScreenerStore((s) => s.status);
  const runScreener = useScreenerStore((s) => s.runScreener);
  const [sortKey, setSortKey] = useState<SortKey>("market_cap");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");

  const rows = useMemo(() => {
    if (!result) return [];
    const dir = sortDirection === "asc" ? 1 : -1;
    return [...result.rows].sort((a, b) => compareValue(a, b, sortKey, dir));
  }, [result, sortKey, sortDirection]);

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
        <div className="border-border min-h-0 flex-1 overflow-auto rounded-md border">
          <table className="w-full text-sm">
            {TABLE_HEADER_COLS}
            <thead className="bg-muted/40">
              <tr>
                {COLUMNS.map((col) => (
                  <th
                    key={col.key}
                    scope="col"
                    className={`border-border border-b px-3 py-2 text-xs tracking-wide uppercase ${
                      col.numeric ? "text-right" : "text-left"
                    }`}
                  >
                    {col.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {Array.from({ length: 8 }).map((_, i) => (
                <tr key={i} className="border-border/60 border-b">
                  {COLUMNS.map((col) => (
                    <td key={col.key} className="px-3 py-2">
                      <div
                        className={`bg-muted/20 h-4 animate-pulse rounded ${col.numeric ? "ml-auto" : ""}`}
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
        <div className="text-muted-foreground flex items-center gap-2 text-xs">
          <Loader2 className="size-3 animate-spin" />
          Running screener…
        </div>
      </div>
    );
  }

  if (status === "error" && !result) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 text-center">
        <SlidersHorizontal className="text-muted-foreground size-6" />
        <p className="text-destructive text-sm">Could not load results.</p>
        <Button size="sm" variant="outline" onClick={() => void runScreener()}>
          Retry
        </Button>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 text-center">
        <SlidersHorizontal className="text-muted-foreground size-6" />
        <p className="text-foreground text-sm font-semibold">No results yet</p>
        <p className="text-muted-foreground text-xs">
          Set your criteria above and run the screener to find matching stocks.
        </p>
        <Button size="sm" variant="outline" onClick={() => void runScreener()}>
          Run screener
        </Button>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col gap-2">
      <div className="text-muted-foreground flex shrink-0 items-center justify-between text-xs">
        <span>
          <span className="text-foreground font-semibold">{result.result_count}</span> rows (
          <span className="font-mono">{result.evaluated_count}</span> evaluated
          {result.skipped_count > 0 && (
            <>
              , <span className="text-warning font-mono">{result.skipped_count} skipped</span>
            </>
          )}
          ,<span className="font-mono"> {result.duration_ms.toFixed(0)} ms</span>)
        </span>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => downloadScreenerCsv(rows, result.universe)}
            disabled={rows.length === 0}
            className="text-charcoal-300 flex items-center gap-1 font-mono text-xs transition-colors hover:text-amber-300 disabled:opacity-40"
            title="Export results to CSV (open in Excel / Sheets)"
          >
            <Download className="size-3" /> Export CSV
          </button>
          <span className="font-mono tracking-wide uppercase">{result.universe}</span>
        </div>
      </div>
      <div className="border-border min-h-0 flex-1 overflow-auto rounded-md border">
        <table className="w-full table-fixed text-sm">
          {TABLE_HEADER_COLS}
          <thead className="bg-muted/40">
            <tr>
              {COLUMNS.map((col) => (
                <th
                  key={col.key}
                  scope="col"
                  className={`border-border cursor-pointer border-b px-3 py-2 text-xs tracking-wide whitespace-nowrap uppercase select-none ${
                    col.numeric ? "text-right" : "text-left"
                  }`}
                  onClick={() => onHeaderClick(col.key)}
                  data-testid={`column-${col.key}`}
                >
                  {col.label}
                  {sortKey === col.key && (
                    <span aria-hidden className="ml-1">
                      {sortDirection === "asc" ? "▲" : "▼"}
                    </span>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td
                  colSpan={COLUMNS.length}
                  className="text-muted-foreground px-3 py-6 text-center text-sm"
                >
                  No rows matched the criteria.
                </td>
              </tr>
            ) : (
              rows.map((row) => (
                <tr
                  key={row.symbol}
                  className="border-border/60 hover:bg-muted/30 cursor-pointer border-b"
                  onClick={() => {
                    // Row click → the full company overview (the operator's
                    // "click any company → one overview page") AND the chart, so
                    // the cockpit drills to the row in one click.
                    openCompanyOverview(row.symbol);
                    loadSymbolIntoChart(row.symbol);
                  }}
                  title={`Open ${displaySymbol(row.symbol)} — overview + chart`}
                >
                  <td className="px-3 py-2 font-mono font-semibold whitespace-nowrap text-amber-300">
                    {displaySymbol(row.symbol)}
                  </td>
                  <td className="max-w-0 truncate overflow-hidden px-3 py-2" title={row.name ?? ""}>
                    {row.name ?? "—"}
                  </td>
                  <td
                    className="text-muted-foreground max-w-0 truncate overflow-hidden px-3 py-2"
                    title={row.sector ?? ""}
                  >
                    {row.sector ?? "—"}
                  </td>
                  <td className="px-3 py-2 text-right font-mono whitespace-nowrap tabular-nums">
                    {fmtMarketCap(row.market_cap)}
                  </td>
                  <td className="px-3 py-2 text-right font-mono whitespace-nowrap tabular-nums">
                    {fmtNumber(row.pe_ratio)}
                  </td>
                  <td className="px-3 py-2 text-right font-mono whitespace-nowrap tabular-nums">
                    {fmtNumber(row.forward_pe)}
                  </td>
                  <td className="px-3 py-2 text-right font-mono whitespace-nowrap tabular-nums">
                    {fmtPct(row.roe)}
                  </td>
                  <td className="px-3 py-2 text-right font-mono whitespace-nowrap tabular-nums">
                    {fmtNumber(row.debt_to_equity)}
                  </td>
                  <td className="px-3 py-2 text-right font-mono whitespace-nowrap tabular-nums">
                    {fmtPct(row.dividend_yield)}
                  </td>
                  <td className="px-3 py-2 text-right font-mono whitespace-nowrap tabular-nums">
                    {fmtNumber(row.price)}
                  </td>
                  <td
                    className={`px-3 py-2 text-right font-mono whitespace-nowrap tabular-nums ${
                      row.change_percent_1d === null
                        ? "text-muted-foreground"
                        : row.change_percent_1d >= 0
                          ? "text-positive"
                          : "text-negative"
                    }`}
                  >
                    {row.change_percent_1d === null
                      ? "—"
                      : `${row.change_percent_1d >= 0 ? "+" : ""}${row.change_percent_1d.toFixed(2)}%`}
                  </td>
                  <td className="px-3 py-2 text-right font-mono whitespace-nowrap tabular-nums">
                    {fmtVolume(row.volume)}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
