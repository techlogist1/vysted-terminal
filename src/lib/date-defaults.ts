/**
 * Mount-time date defaults for panels that used to ship frozen literal
 * dates (R15-UI-062, R15-UI-063) — every open showed an expired example
 * instead of a usable one. Each helper derives its dates from `now`
 * (defaulting to `new Date()`) — call these in a `useState(() => ...)`
 * lazy initializer so the panel picks up "today" on the render that
 * mounts it, not at module-load / authoring time.
 */

function toISODate(d: Date): string {
  // Local-date formatting — toISOString() shifts by the UTC offset, which
  // is wrong for a plain calendar-date input default.
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function addDays(d: Date, days: number): Date {
  const copy = new Date(d);
  copy.setDate(copy.getDate() + days);
  return copy;
}

function addYears(d: Date, years: number): Date {
  const copy = new Date(d);
  copy.setFullYear(copy.getFullYear() + years);
  return copy;
}

/** Option Pricer / Greeks Dashboard: valuation = today, expiry = today + 45d. */
export function optionDateDefaults(now: Date = new Date()): {
  valuationDate: string;
  expiryDate: string;
} {
  return {
    valuationDate: toISODate(now),
    expiryDate: toISODate(addDays(now, 45)),
  };
}

/** Bond Pricer: issue/settlement = today, maturity = today + 10y. */
export function bondDateDefaults(now: Date = new Date()): {
  issueDate: string;
  maturityDate: string;
  settlementDate: string;
} {
  const issueDate = toISODate(now);
  return {
    issueDate,
    maturityDate: toISODate(addYears(now, 10)),
    settlementDate: issueDate,
  };
}

/** Yield Curve Panel: valuation = today. */
export function yieldCurveDateDefaults(now: Date = new Date()): { valuationDate: string } {
  return { valuationDate: toISODate(now) };
}

/** Backtest Panel: end = today, start = end - 2y. */
export function backtestDateDefaults(now: Date = new Date()): {
  startDate: string;
  endDate: string;
} {
  return {
    startDate: toISODate(addYears(now, -2)),
    endDate: toISODate(now),
  };
}
