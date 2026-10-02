"use client";

import { Star, Users } from "lucide-react";

import { DataTable, type DataColumn } from "@/components/DataTable";
import { EmptyState } from "@/components/EmptyState";
import { currencyAffix, formatPercent, formatPrice } from "@/lib/format";

import type { IndividualAnalystForecast } from "../../../types/analyst";

import { fmtDate, RATING_COLOR, RATING_LABEL } from "./format";

function StarRow({ rating }: { rating: number | null }) {
  if (rating === null) {
    return <span className="text-charcoal-500 text-caption">—</span>;
  }
  const stars = Math.round(rating);
  return (
    <span aria-label={`${stars} stars`} className="text-charcoal-300 inline-flex items-center">
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
    // R15-DATA-031: the Target column rendered a bare number with no
    // currency, so a USD and an INR target read as the same magnitude.
    format: (e) => {
      if (e.current_price_target === null) return null;
      const { prefix, suffix } = currencyAffix(e.currency);
      return `${prefix}${formatPrice(e.current_price_target)}${suffix}`;
    },
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
