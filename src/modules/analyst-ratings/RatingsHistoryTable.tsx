"use client";

import { useMemo, useState } from "react";

import type { RatingsHistoryEntry } from "../../../types/analyst";

type SortKey = "date" | "firm" | "rating_to";
type SortDirection = "asc" | "desc";

const RATING_LABEL: Record<string, string> = {
  "strong-buy": "Strong Buy",
  buy: "Buy",
  hold: "Hold",
  sell: "Sell",
  "strong-sell": "Strong Sell",
};

const RATING_COLOR: Record<string, string> = {
  "strong-buy": "text-positive",
  buy: "text-positive",
  hold: "text-charcoal-200",
  sell: "text-negative",
  "strong-sell": "text-negative",
};

function fmtDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

interface Props {
  history: RatingsHistoryEntry[];
}

export function RatingsHistoryTable({ history }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>("date");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");

  const sorted = useMemo(() => {
    return [...history].sort((a, b) => {
      const av = a[sortKey] ?? "";
      const bv = b[sortKey] ?? "";
      if (av === bv) return 0;
      const cmp = av < bv ? -1 : 1;
      return sortDirection === "asc" ? cmp : -cmp;
    });
  }, [history, sortKey, sortDirection]);

  const onSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDirection((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDirection("desc");
    }
  };

  if (history.length === 0) {
    return (
      <p className="text-charcoal-400 font-mono text-xs" data-testid="ratings-history-empty">
        No ratings history available.
      </p>
    );
  }

  return (
    <table className="w-full table-fixed border-collapse" data-testid="ratings-history-table">
      <colgroup>
        <col style={{ width: "16%" }} />
        <col style={{ width: "24%" }} />
        <col style={{ width: "20%" }} />
        <col style={{ width: "20%" }} />
        <col style={{ width: "20%" }} />
      </colgroup>
      <thead>
        <tr className="text-charcoal-400 border-charcoal-800 border-b text-left font-mono text-[0.6rem] uppercase">
          <SortableHeader
            label="Date"
            active={sortKey === "date"}
            direction={sortDirection}
            onSort={() => onSort("date")}
          />
          <SortableHeader
            label="Firm"
            active={sortKey === "firm"}
            direction={sortDirection}
            onSort={() => onSort("firm")}
          />
          <SortableHeader
            label="Rating"
            active={sortKey === "rating_to"}
            direction={sortDirection}
            onSort={() => onSort("rating_to")}
          />
          <th className="px-3 py-1.5 font-medium">Raw</th>
          <th className="px-3 py-1.5 font-medium">Note</th>
        </tr>
      </thead>
      <tbody>
        {sorted.map((entry, index) => {
          const ratingFromLabel = entry.rating_from ? RATING_LABEL[entry.rating_from] : "Initiated";
          return (
            <tr
              key={`${entry.symbol}-${entry.date}-${entry.firm}-${index}`}
              className="border-charcoal-800 border-b font-mono text-xs"
            >
              <td className="text-charcoal-100 px-3 py-1.5">{fmtDate(entry.date)}</td>
              <td className="text-charcoal-100 truncate px-3 py-1.5" title={entry.firm}>
                {entry.firm}
              </td>
              <td className="px-3 py-1.5">
                <span className="text-charcoal-400">{ratingFromLabel}</span>
                <span className="text-charcoal-500"> → </span>
                <span className={RATING_COLOR[entry.rating_to] ?? "text-charcoal-100"}>
                  {RATING_LABEL[entry.rating_to] ?? entry.rating_to}
                </span>
              </td>
              <td className="text-charcoal-400 truncate px-3 py-1.5" title={entry.raw_rating}>
                {entry.raw_rating || "—"}
              </td>
              <td className="text-charcoal-400 truncate px-3 py-1.5" title={entry.note ?? ""}>
                {entry.note ?? "—"}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

function SortableHeader({
  label,
  active,
  direction,
  onSort,
}: {
  label: string;
  active: boolean;
  direction: SortDirection;
  onSort: () => void;
}) {
  return (
    <th
      className="cursor-pointer px-3 py-1.5 font-medium"
      onClick={onSort}
      aria-sort={active ? (direction === "asc" ? "ascending" : "descending") : "none"}
    >
      {label}
      {active && <span className="text-amber-400"> {direction === "asc" ? "▲" : "▼"}</span>}
    </th>
  );
}
