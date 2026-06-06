"use client";

import { Star, Users } from "lucide-react";

import { DataTable, type DataColumn } from "@/components/DataTable";
import { EmptyState } from "@/components/EmptyState";
import { formatPercent, formatPrice } from "@/lib/format";

import type { IndividualAnalystForecast } from "../../../types/analyst";

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

function StarRow({ rating }: { rating: number | null }) {
  if (rating === null) {
    return <span className="text-charcoal-600 text-caption">—</span>;
  }
  const stars = Math.round(rating);
  return (
    <span aria-label={`${stars} stars`} className="inline-flex items-center text-amber-400">
      {Array.from({ length: 5 }).map((_, idx) => (
        <Star
          key={idx}
          className="size-3"
          fill={idx < stars ? "currentColor" : "none"}
          stroke="currentColor"
        />
      ))}
    </span>
  );
}

const COLUMNS: DataColumn<IndividualAnalystForecast>[] = [
  { key: "firm", header: "Firm", truncate: true, width: "26%", format: (e) => e.firm },
  {
    key: "current_rating",
    header: "Rating",
    width: "16%",
    cell: (e) => (
      <span className={RATING_COLOR[e.current_rating] ?? "text-charcoal-100"}>
        {RATING_LABEL[e.current_rating] ?? e.current_rating}
      </span>
    ),
  },
  {
    key: "current_price_target",
    header: "Target",
    numeric: true,
    width: "14%",
    format: (e) => (e.current_price_target === null ? null : formatPrice(e.current_price_target)),
  },
  {
    key: "rating_issued_date",
    header: "Issued",
    tier: "secondary",
    width: "14%",
    format: (e) => fmtDate(e.rating_issued_date),
  },
  {
    key: "one_year_accuracy",
    header: "1y accuracy",
    numeric: true,
    tier: "secondary",
    width: "14%",
    format: (e) =>
      e.one_year_accuracy === null
        ? null
        : formatPercent(e.one_year_accuracy * 100).replace("+", ""),
  },
  {
    key: "star_rating",
    header: "Stars",
    width: "16%",
    cell: (e) => <StarRow rating={e.star_rating} />,
  },
];

interface Props {
  analysts: IndividualAnalystForecast[];
}

export function IndividualAnalystTable({ analysts }: Props) {
  if (analysts.length === 0) {
    return (
      <div data-testid="individual-analyst-empty">
        <EmptyState
          icon={Users}
          headline="No per-firm forecasts"
          hint="Individual analyst targets and ratings will appear here once a covering firm publishes."
        />
      </div>
    );
  }
  return (
    <DataTable
      columns={COLUMNS}
      rows={analysts}
      rowKey={(entry, i) => `${entry.symbol}-${entry.firm}-${i}`}
      data-testid="individual-analyst-table"
    />
  );
}
