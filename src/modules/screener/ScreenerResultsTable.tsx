"use client";

import { useMemo, useState } from "react";

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

function compareValue(a: ScreenerResultRow, b: ScreenerResultRow, key: SortKey): number {
  const av = a[key];
  const bv = b[key];
  if (av === null && bv === null) return 0;
  if (av === null) return 1;
  if (bv === null) return -1;
  if (typeof av === "number" && typeof bv === "number") return av - bv;
  return String(av).localeCompare(String(bv));
}

export function ScreenerResultsTable() {
  const result = useScreenerStore((s) => s.lastResult);
  const status = useScreenerStore((s) => s.status);
  const [sortKey, setSortKey] = useState<SortKey>("market_cap");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");

  const rows = useMemo(() => {
    if (!result) return [];
    const sorted = [...result.rows].sort((a, b) => compareValue(a, b, sortKey));
    return sortDirection === "asc" ? sorted : sorted.reverse();
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
      <div className="rounded-md border border-dashed border-border p-6 text-center text-sm text-muted-foreground">
        Running screener…
      </div>
    );
  }

  if (!result) {
    return (
      <div className="rounded-md border border-dashed border-border p-6 text-center text-sm text-muted-foreground">
        Run the screener to populate results.
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>
          <span className="font-semibold text-foreground">{result.result_count}</span> rows
          (
          <span className="font-mono">{result.evaluated_count}</span> evaluated,
          <span className="font-mono"> {result.duration_ms.toFixed(0)} ms</span>)
        </span>
        <span className="font-mono uppercase tracking-wide">{result.universe}</span>
      </div>
      <div className="overflow-auto rounded-md border border-border">
        <table className="w-full text-sm">
          <thead className="bg-muted/40">
            <tr>
              {COLUMNS.map((col) => (
                <th
                  key={col.key}
                  scope="col"
                  className={`cursor-pointer select-none border-b border-border px-3 py-2 text-xs uppercase tracking-wide ${
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
                  className="px-3 py-6 text-center text-sm text-muted-foreground"
                >
                  No rows matched the criteria.
                </td>
              </tr>
            ) : (
              rows.map((row) => (
                <tr key={row.symbol} className="border-b border-border/60 hover:bg-muted/30">
                  <td className="px-3 py-2 font-mono font-semibold">{row.symbol}</td>
                  <td className="px-3 py-2">{row.name ?? "—"}</td>
                  <td className="px-3 py-2 text-muted-foreground">{row.sector ?? "—"}</td>
                  <td className="px-3 py-2 text-right font-mono">{fmtMarketCap(row.market_cap)}</td>
                  <td className="px-3 py-2 text-right font-mono">{fmtNumber(row.pe_ratio)}</td>
                  <td className="px-3 py-2 text-right font-mono">{fmtNumber(row.price)}</td>
                  <td
                    className={`px-3 py-2 text-right font-mono ${
                      (row.change_percent_1d ?? 0) >= 0
                        ? "text-emerald-400"
                        : "text-rose-400"
                    }`}
                  >
                    {row.change_percent_1d === null
                      ? "—"
                      : `${row.change_percent_1d >= 0 ? "+" : ""}${row.change_percent_1d.toFixed(2)}%`}
                  </td>
                  <td className="px-3 py-2 text-right font-mono">{fmtVolume(row.volume)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
