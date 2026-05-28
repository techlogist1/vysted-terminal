import { describe, expect, it } from "vitest";

import {
  formatCompactMoney,
  formatCompactNumber,
  formatMoney,
  formatPercent,
  formatSignedMoney,
} from "./format";

describe("formatMoney", () => {
  it("formats with cents", () => {
    expect(formatMoney(1234.5)).toBe("$1,234.50");
    expect(formatMoney(0)).toBe("$0.00");
  });
  it("degrades non-finite to em-dash", () => {
    expect(formatMoney(NaN)).toBe("—");
    expect(formatMoney(Infinity)).toBe("—");
    expect(formatMoney(-Infinity)).toBe("—");
  });
});

describe("formatCompactMoney", () => {
  it("keeps full cents below $1M", () => {
    expect(formatCompactMoney(1234.5)).toBe("$1,234.50");
    expect(formatCompactMoney(999_999)).toBe("$999,999.00");
  });
  it("abbreviates at M/B/T/Q", () => {
    expect(formatCompactMoney(1_500_000)).toBe("$1.50M");
    expect(formatCompactMoney(2_300_000_000)).toBe("$2.30B");
    expect(formatCompactMoney(4.2e12)).toBe("$4.20T");
    // The F-GUI-1 quadrillion overflow case — 3 sig figs, no row overflow.
    expect(formatCompactMoney(621_700_012_207_018_900)).toBe("$622Q");
    expect(formatCompactMoney(62_170_001_220_701)).toBe("$62.2T");
  });
  it("handles negatives and non-finite", () => {
    expect(formatCompactMoney(-3_400_000)).toBe("-$3.40M");
    expect(formatCompactMoney(NaN)).toBe("—");
  });
});

describe("formatSignedMoney", () => {
  it("adds a leading + for positives", () => {
    expect(formatSignedMoney(500)).toBe("+$500.00");
    expect(formatSignedMoney(-500)).toBe("-$500.00");
    expect(formatSignedMoney(0)).toBe("$0.00");
  });
  it("supports compact mode", () => {
    expect(formatSignedMoney(2_500_000, true)).toBe("+$2.50M");
  });
});

describe("formatPercent", () => {
  it("formats with two decimals and sign", () => {
    expect(formatPercent(33.33)).toBe("+33.33%");
    expect(formatPercent(-5)).toBe("-5.00%");
    expect(formatPercent(0)).toBe("0.00%");
  });
  it("falls back to exponential for absurd magnitudes (F-GUI-1)", () => {
    expect(formatPercent(2_855_345_159_126.89)).toBe("+2.86e+12%");
  });
  it("degrades non-finite", () => {
    expect(formatPercent(NaN)).toBe("—");
  });
});

describe("formatCompactNumber", () => {
  it("abbreviates large counts", () => {
    expect(formatCompactNumber(1_200_000)).toBe("1.20M");
    expect(formatCompactNumber(500)).toBe("500");
  });
});
