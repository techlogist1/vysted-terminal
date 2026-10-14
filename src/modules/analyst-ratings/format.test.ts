/**
 * format.ts — fmtDate must never lose a day to a UTC-midnight parse
 * (R15-CODE-DATA-016). Run with TZ=America/Los_Angeles to exercise the
 * west-of-UTC case the bug affected.
 */

import { describe, expect, it } from "vitest";

import { fmtDate, RATING_COLOR, RATING_LABEL } from "./format";

describe("fmtDate", () => {
  it("parses a YYYY-MM-DD date as a local calendar date, never UTC midnight", () => {
    // Under TZ=America/Los_Angeles (UTC-8), `new Date("2024-01-01")` parses
    // as UTC midnight and renders as "Dec 31, 2023" locally — the bug this
    // pins against.
    expect(fmtDate("2024-01-01")).toBe("Jan 1, 2024");
    expect(fmtDate("2026-05-20")).toBe("May 20, 2026");
  });

  it("falls back to a normal Date parse for a full ISO datetime", () => {
    const iso = "2024-01-01T12:00:00.000Z";
    const expected = new Date(iso).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
    expect(fmtDate(iso)).toBe(expected);
  });

  it("returns the raw string on an unparseable date", () => {
    expect(fmtDate("not-a-date")).toBe("not-a-date");
  });
});

describe("RATING_LABEL / RATING_COLOR", () => {
  it("cover the same rating keys", () => {
    expect(Object.keys(RATING_LABEL).sort()).toEqual(Object.keys(RATING_COLOR).sort());
  });

  it("label the five ratings", () => {
    expect(RATING_LABEL["strong-buy"]).toBe("Strong Buy");
    expect(RATING_LABEL["strong-sell"]).toBe("Strong Sell");
  });
});
