"use client";

import { Star } from "lucide-react";

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

function fmt(value: number | null, digits = 2): string {
  if (value === null) return "—";
  return value.toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

function StarRow({ rating }: { rating: number | null }) {
  if (rating === null) {
    return <span className="text-charcoal-500 font-mono text-[0.65rem]">—</span>;
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

interface Props {
  analysts: IndividualAnalystForecast[];
}

export function IndividualAnalystTable({ analysts }: Props) {
  if (analysts.length === 0) {
    return (
      <p className="text-charcoal-400 font-mono text-xs" data-testid="individual-analyst-empty">
        No per-firm forecasts available.
      </p>
    );
  }
  return (
    <table className="w-full table-fixed border-collapse" data-testid="individual-analyst-table">
      <colgroup>
        <col style={{ width: "26%" }} />
        <col style={{ width: "16%" }} />
        <col style={{ width: "14%" }} />
        <col style={{ width: "14%" }} />
        <col style={{ width: "14%" }} />
        <col style={{ width: "16%" }} />
      </colgroup>
      <thead>
        <tr className="text-charcoal-400 border-charcoal-800 border-b text-left font-mono text-[0.6rem] uppercase">
          <th className="px-3 py-1.5 font-medium">Firm</th>
          <th className="px-3 py-1.5 font-medium">Rating</th>
          <th className="px-3 py-1.5 text-right font-medium">Target</th>
          <th className="px-3 py-1.5 font-medium">Issued</th>
          <th className="px-3 py-1.5 text-right font-medium">1y accuracy</th>
          <th className="px-3 py-1.5 font-medium">Stars</th>
        </tr>
      </thead>
      <tbody>
        {analysts.map((entry, index) => (
          <tr
            key={`${entry.symbol}-${entry.firm}-${index}`}
            className="border-charcoal-800 border-b font-mono text-xs"
          >
            <td className="text-charcoal-100 truncate px-3 py-1.5" title={entry.firm}>
              {entry.firm}
            </td>
            <td
              className={`px-3 py-1.5 ${RATING_COLOR[entry.current_rating] ?? "text-charcoal-100"}`}
            >
              {RATING_LABEL[entry.current_rating] ?? entry.current_rating}
            </td>
            <td className="text-charcoal-100 px-3 py-1.5 text-right">
              {fmt(entry.current_price_target)}
            </td>
            <td className="text-charcoal-200 px-3 py-1.5">{fmtDate(entry.rating_issued_date)}</td>
            <td className="text-charcoal-200 px-3 py-1.5 text-right">
              {entry.one_year_accuracy === null
                ? "—"
                : `${(entry.one_year_accuracy * 100).toFixed(1)}%`}
            </td>
            <td className="px-3 py-1.5">
              <StarRow rating={entry.star_rating} />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
