/**
 * Shared analyst-ratings / earnings display helpers (R15-CODE-DATA-016).
 *
 * One rating label + colour map and one date formatter, instead of the
 * byte-identical copies that had drifted across AnalystRatingsPanel's
 * child tables and EarningsCalendarPanel.
 */

export const RATING_LABEL: Record<string, string> = {
  "strong-buy": "Strong Buy",
  buy: "Buy",
  hold: "Hold",
  sell: "Sell",
  "strong-sell": "Strong Sell",
};

export const RATING_COLOR: Record<string, string> = {
  "strong-buy": "text-positive",
  buy: "text-positive",
  hold: "text-charcoal-200",
  sell: "text-negative",
  "strong-sell": "text-negative",
};

/**
 * Formats an ISO date string for display.
 *
 * A bare `YYYY-MM-DD` calendar date (what the sidecar sends for rating /
 * earnings dates) is parsed as a LOCAL date, never as UTC midnight —
 * `new Date("YYYY-MM-DD")` parses as UTC, so a viewer west of UTC would see
 * the previous day. A full ISO datetime (carries its own instant) falls
 * back to the normal `Date` parse.
 */
export function fmtDate(iso: string): string {
  const dateOnly = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);
  const d = dateOnly
    ? new Date(Number(dateOnly[1]), Number(dateOnly[2]) - 1, Number(dateOnly[3]))
    : new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}
