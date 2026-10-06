import { describe, expect, it } from "vitest";

import {
  deriveMarketSession,
  humanizeMarketState,
  isLiveQuote,
  sessionLabelFromFreshness,
  type MarketSessionLabel,
} from "./market-session";

// A weekday (Wed 2026-01-14) and a weekend (Sat 2026-01-17) anchor for the
// calendar-aware CLOSED disambiguation. getDay() is local; noon avoids any
// timezone day-rollover ambiguity.
const WEEKDAY = new Date(2026, 0, 14, 12, 0, 0);
const SATURDAY = new Date(2026, 0, 17, 12, 0, 0);
const SUNDAY = new Date(2026, 0, 18, 12, 0, 0);

describe("humanizeMarketState", () => {
  it("maps REGULAR / open to Market open (case-insensitive)", () => {
    expect(humanizeMarketState("REGULAR", WEEKDAY)).toBe("Market open");
    expect(humanizeMarketState("open", WEEKDAY)).toBe("Market open");
    expect(humanizeMarketState("Regular", WEEKDAY)).toBe("Market open");
  });

  it("maps PRE / PREPRE to Pre-market", () => {
    expect(humanizeMarketState("PRE", WEEKDAY)).toBe("Pre-market");
    expect(humanizeMarketState("PREPRE", WEEKDAY)).toBe("Pre-market");
  });

  it("maps POST / POSTPOST to After-hours", () => {
    expect(humanizeMarketState("POST", WEEKDAY)).toBe("After-hours");
    expect(humanizeMarketState("POSTPOST", WEEKDAY)).toBe("After-hours");
  });

  it("maps CLOSED on a weekday to Market closed", () => {
    expect(humanizeMarketState("CLOSED", WEEKDAY)).toBe("Market closed");
  });

  it("disambiguates CLOSED on Sat/Sun to Weekend", () => {
    expect(humanizeMarketState("CLOSED", SATURDAY)).toBe("Weekend");
    expect(humanizeMarketState("CLOSED", SUNDAY)).toBe("Weekend");
  });

  it("returns null for an unknown / empty state", () => {
    expect(humanizeMarketState(null, WEEKDAY)).toBeNull();
    expect(humanizeMarketState(undefined, WEEKDAY)).toBeNull();
    expect(humanizeMarketState("   ", WEEKDAY)).toBeNull();
  });

  it("never echoes a raw unknown token (falls back to a neutral closed label)", () => {
    const out = humanizeMarketState("SOMETHING_WEIRD", WEEKDAY);
    expect(out).toBe("Market closed");
    // It is one of the friendly labels, not the raw provider string.
    const friendly: MarketSessionLabel[] = [
      "Market open",
      "Market closed",
      "Weekend",
      "Pre-market",
      "After-hours",
    ];
    expect(friendly).toContain(out);
  });
});

describe("isLiveQuote (stale guard)", () => {
  it("is true ONLY for freshness === 'live'", () => {
    expect(isLiveQuote("live")).toBe(true);
  });

  it("is false for eod, stale, null, and undefined", () => {
    expect(isLiveQuote("eod")).toBe(false);
    expect(isLiveQuote("stale")).toBe(false);
    expect(isLiveQuote(null)).toBe(false);
    expect(isLiveQuote(undefined)).toBe(false);
  });
});

describe("deriveMarketSession", () => {
  it("is live-toned only when open AND fresh", () => {
    const s = deriveMarketSession("REGULAR", "live", WEEKDAY);
    expect(s.label).toBe("Market open");
    expect(s.tone).toBe("live");
    expect(s.isClosed).toBe(false);
  });

  it("stays muted when the state is open but the value is stale", () => {
    // The VALUE, not the calendar, is the authority on liveness — a REGULAR
    // state riding a stale read must not read as a live tick.
    const s = deriveMarketSession("REGULAR", "stale", WEEKDAY);
    expect(s.label).toBe("Market open");
    expect(s.tone).toBe("muted");
  });

  it("flags a closed session as muted + isClosed", () => {
    const s = deriveMarketSession("CLOSED", "eod", WEEKDAY);
    expect(s.label).toBe("Market closed");
    expect(s.tone).toBe("muted");
    expect(s.isClosed).toBe(true);
  });

  it("pre-market and after-hours are closed-tier (muted, isClosed)", () => {
    expect(deriveMarketSession("PRE", "live", WEEKDAY).isClosed).toBe(true);
    expect(deriveMarketSession("POST", "live", WEEKDAY).tone).toBe("muted");
  });

  it("an unknown state yields a null label and is not closed", () => {
    const s = deriveMarketSession(null, "live", WEEKDAY);
    expect(s.label).toBeNull();
    expect(s.isClosed).toBe(false);
  });
});

describe("sessionLabelFromFreshness (chart, market_state-less surfaces)", () => {
  it("maps eod to Market closed and stale to Stale data", () => {
    expect(sessionLabelFromFreshness("eod")).toBe("Market closed");
    expect(sessionLabelFromFreshness("stale")).toBe("Stale data");
  });

  it("returns null for a live or unknown freshness (no caution label needed)", () => {
    expect(sessionLabelFromFreshness("live")).toBeNull();
    expect(sessionLabelFromFreshness(null)).toBeNull();
    expect(sessionLabelFromFreshness(undefined)).toBeNull();
  });
});
