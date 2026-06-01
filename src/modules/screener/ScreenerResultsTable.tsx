"use client";

import { useMemo, useState } from "react";
import { SlidersHorizontal, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useScreenerStore } from "@/store/screener";

import type { ScreenerResultRow } from "../../../types/screener";

type SortKey =
  | "symbol"
  | "name"
  | "sector"
  | "industry"
  | "market_cap"
  | "pe_ratio"
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
  { key: "price", label: "Price", numeric: true },
  { key: "change_percent_1d", label: "1d %", numeric: true },
  { key: "volume", label: "Volume", numeric: true },
];

function fmtMarketCap(value: number | null): string {
  if (value === null) return "—";
  if (value >= 1_000_000_000_000) return `${(value / 1_000_000_000_000).toFixed(2)}T`;
  if (value >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(2)}B`;
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(2)}M`;
  return value.toLocaleString("en-US");
}

function fmtNumber(value: number | null, digits = 2): string {
  if (value === null) return "—";
  return value.toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

function fmtVolume(value: number | null): string {
  if (value === null) return "—";
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return value.toLocaleString("en-US");
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
  if (av === null && bv === null) return 0;
  if (av === null) return 1; // nulls always last, regardless of direction
  if (bv === null) return -1;
  const base =
    typeof av === "number" && typeof bv === "number"
      ? av - bv
      : String(av).localeCompare(String(bv));
  return base * dir;
}

const TABLE_HEADER_COLS = (
  <colgroup>
    <col style={{ width: "60px" }} />
    <col style={{ width: "30%" }} />
    <col style={{ width: "15%" }} />
    <col style={{ width: "80px" }} />
    <col style={{ width: "56px" }} />
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
        <span className="font-mono tracking-wide uppercase">{result.universe}</span>
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
                <tr key={row.symbol} className="border-border/60 hover:bg-muted/30 border-b">
                  <td className="px-3 py-2 font-mono font-semibold whitespace-nowrap">
                    {row.symbol}
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
