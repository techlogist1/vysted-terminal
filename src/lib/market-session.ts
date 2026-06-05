/**
 * Market-session awareness (FR-118) — never present a closed / weekend / stale
 * price as if it were a live tick.
 *
 * The sidecar already computes the heavy lifting: every {@link Quote} carries a
 * raw provider `market_state` string (yfinance `REGULAR`/`PRE`/`POST`/`CLOSED`,
 * ccxt `open`, India `REGULAR`/`CLOSED`) and a calendar-aware `freshness`
 * (`"live" | "eod" | "stale"`). This module is the FRONTEND projection:
 *
 *  - {@link humanizeMarketState} turns the raw, inconsistent-case provider string
 *    into one of a small, friendly label set ("Market open", "Market closed",
 *    "Weekend", "Pre-market", "After-hours") so a panel never echoes a raw
 *    `POSTPOST` token at the user.
 *  - {@link isLiveQuote} is the single stale-guard predicate: a price reads as a
 *    live tick ONLY when `freshness === "live"`. Everywhere a quote drives a
 *    green/red flash or a coloured change %, gate it on this — a stale or EOD
 *    value must render neutral, never as a live move.
 *
 * Pure + dependency-free so it is trivially unit-testable; the React hook
 * {@link useMarketSession} is a thin wrapper that supplies "now".
 */

import { useMemo } from "react";

/** The friendly session label a price surface shows beside a non-live quote. */
export type MarketSessionLabel =
  | "Market open"
  | "Market closed"
  | "Weekend"
  | "Pre-market"
  | "After-hours";

/** Tier of a session label — drives whether it reads as a quiet caution. */
export type MarketSessionTone = "live" | "muted";

export interface MarketSession {
  /** The humanized, display-ready label (null when the state is unknown). */
  label: MarketSessionLabel | null;
  /** `"live"` only when the market is actively open; otherwise `"muted"`. */
  tone: MarketSessionTone;
  /** True when the session is anything other than regular trading hours. */
  isClosed: boolean;
}

/**
 * Map a raw provider `market_state` to a friendly label. Case-insensitive so
 * yfinance's `REGULAR`/`CLOSED` and ccxt's lowercase `open` both resolve. A
 * weekend is surfaced when the state is closed AND `now` falls on Sat/Sun —
 * yfinance reports a plain `CLOSED` on weekends, so the calendar disambiguates.
 *
 * @param marketState the raw provider string (or null/undefined when unknown).
 * @param now         injected for deterministic tests; defaults to the present.
 */
export function humanizeMarketState(
  marketState: string | null | undefined,
  now: Date = new Date(),
): MarketSessionLabel | null {
  if (marketState == null || marketState.trim() === "") {
    return null;
  }
  const state = marketState.trim().toUpperCase();

  // Regular trading hours — the only "live" session.
  if (state === "REGULAR" || state === "OPEN") {
    return "Market open";
  }
  // Pre-market (yfinance PRE / PREPRE).
  if (state === "PRE" || state === "PREPRE") {
    return "Pre-market";
  }
  // After-hours (yfinance POST / POSTPOST).
  if (state === "POST" || state === "POSTPOST") {
    return "After-hours";
  }
  if (state === "CLOSED" || state === "CLOSE") {
    const day = now.getDay(); // 0 = Sun, 6 = Sat
    return day === 0 || day === 6 ? "Weekend" : "Market closed";
  }
  // Unknown / provider-specific state — surface a neutral closed-ish label
  // rather than echoing the raw token.
  return "Market closed";
}

/**
 * The single stale-guard predicate. A quote may drive a live affordance (a
 * green/red price flash, a coloured change %) ONLY when its freshness is
 * exactly `"live"`. `eod`, `stale`, and an absent freshness all read as NOT
 * live, so a closed/weekend/cached price never animates as if it just ticked.
 */
export function isLiveQuote(freshness: string | null | undefined): boolean {
  return freshness === "live";
}

/**
 * Derive the display session from a raw provider state + freshness. `tone` is
 * `"live"` only when the market is open AND the value is fresh — so even a
 * "REGULAR" state riding a stale value reads muted (the value, not the calendar,
 * is the authority on liveness).
 */
export function deriveMarketSession(
  marketState: string | null | undefined,
  freshness: string | null | undefined,
  now: Date = new Date(),
): MarketSession {
  const label = humanizeMarketState(marketState, now);
  const open = label === "Market open";
  const live = open && isLiveQuote(freshness);
  return {
    label,
    tone: live ? "live" : "muted",
    isClosed: label !== null && !open,
  };
}

/**
 * Freshness-only session hint — for surfaces that have a calendar-aware
 * `freshness` but no provider `market_state` (e.g. the chart's OHLCV series,
 * whose contract carries freshness but not market_state). `eod` reads as a
 * closed-session "Market closed", `stale` as "Stale data"; `live` and unknown
 * return null (the live case needs no caution label, the unknown case stays
 * silent rather than guessing). Kept distinct from {@link humanizeMarketState}
 * so neither has to invent the other's missing input.
 */
export function sessionLabelFromFreshness(
  freshness: string | null | undefined,
): "Market closed" | "Stale data" | null {
  if (freshness === "eod") {
    return "Market closed";
  }
  if (freshness === "stale") {
    return "Stale data";
  }
  return null;
}

/**
 * React hook wrapper — memoizes {@link deriveMarketSession} for a quote's
 * `market_state` + `freshness`. "Now" is captured per render via the default,
 * which is acceptable for a label that only needs day-of-week granularity.
 */
export function useMarketSession(
  marketState: string | null | undefined,
  freshness: string | null | undefined,
): MarketSession {
  return useMemo(() => deriveMarketSession(marketState, freshness), [marketState, freshness]);
}
