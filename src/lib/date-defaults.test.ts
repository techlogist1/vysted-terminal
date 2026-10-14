import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  backtestDateDefaults,
  bondDateDefaults,
  optionDateDefaults,
  yieldCurveDateDefaults,
} from "./date-defaults";

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date(2026, 8, 25)); // 2026-09-25, local time
});

afterEach(() => {
  vi.useRealTimers();
});

describe("date-defaults", () => {
  it("optionDateDefaults: valuation = today, expiry = today + 45d", () => {
    expect(optionDateDefaults(new Date())).toEqual({
      valuationDate: "2026-09-25",
      expiryDate: "2026-11-09",
    });
  });

  it("bondDateDefaults: issue/settlement = today, maturity = today + 10y", () => {
    expect(bondDateDefaults(new Date())).toEqual({
      issueDate: "2026-09-25",
      maturityDate: "2036-09-25",
      settlementDate: "2026-09-25",
    });
  });

  it("yieldCurveDateDefaults: valuation = today", () => {
    expect(yieldCurveDateDefaults(new Date())).toEqual({ valuationDate: "2026-09-25" });
  });

  it("backtestDateDefaults: end = today, start = end - 2y", () => {
    expect(backtestDateDefaults(new Date())).toEqual({
      startDate: "2024-09-25",
      endDate: "2026-09-25",
    });
  });

  it("defaults `now` to the current system time when omitted", () => {
    expect(optionDateDefaults().valuationDate).toBe("2026-09-25");
  });
});
