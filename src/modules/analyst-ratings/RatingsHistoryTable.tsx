"use client";

import { useMemo, useState } from "react";
import { History } from "lucide-react";

import { DataTable, type DataColumn, type DataTableSort } from "@/components/DataTable";
import { EmptyState } from "@/components/EmptyState";

import type { RatingsHistoryEntry } from "../../../types/analyst";

type SortKey = "date" | "firm" | "rating_to";
type ColumnKey = SortKey | "raw_rating" | "note";
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

const COLUMNS: DataColumn<RatingsHistoryEntry, ColumnKey>[] = [
  { key: "date", header: "Date", sortable: true, width: "16%", format: (e) => fmtDate(e.date) },
  {
    key: "firm",
    header: "Firm",
    sortable: true,
    truncate: true,
    width: "24%",
    format: (e) => e.firm,
  },
  {
    key: "rating_to",
    header: "Rating",
    sortable: true,
    width: "20%",
    cell: (e) => {
      const fromLabel = e.rating_from ? RATING_LABEL[e.rating_from] : "Initiated";
      return (
        <span>
          <span className="text-charcoal-400">{fromLabel}</span>
          <span className="text-charcoal-500"> → </span>
          <span className={RATING_COLOR[e.rating_to] ?? "text-charcoal-100"}>
            {RATING_LABEL[e.rating_to] ?? e.rating_to}
          </span>
        </span>
      );
    },
  },
  {
    key: "raw_rating",
    header: "Raw",
    tier: "secondary",
    truncate: true,
    width: "20%",
    format: (e) => e.raw_rating || null,
  },
  {
    key: "note",
    header: "Note",
    tier: "secondary",
    truncate: true,
    width: "20%",
    format: (e) => e.note ?? null,
  },
];

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

  // Only the three real sort keys cycle the sort; the Raw / Note columns are
  // display-only (no comparable order), so a click on them is a no-op.
  const onSort = (key: ColumnKey) => {
    if (key !== "date" && key !== "firm" && key !== "rating_to") return;
    if (sortKey === key) {
      setSortDirection((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDirection("desc");
    }
  };

  if (history.length === 0) {
    return (
      <div data-testid="ratings-history-empty">
        <EmptyState
          icon={History}
          headline="No ratings history"
          hint="Upgrades, downgrades, and initiations will list here as firms revise their calls."
        />
      </div>
    );
  }

  const sort: DataTableSort<ColumnKey> = { key: sortKey, direction: sortDirection };

  return (
    <DataTable
      columns={COLUMNS}
      rows={sorted}
      rowKey={(entry, i) => `${entry.symbol}-${entry.date}-${entry.firm}-${i}`}
      sort={sort}
      onSort={onSort}
      data-testid="ratings-history-table"
    />
  );
}
