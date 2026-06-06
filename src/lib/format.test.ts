import { describe, expect, it } from "vitest";

import {
  formatCompactMoney,
  formatCompactNumber,
  formatMoney,
  formatPercent,
  formatPrice,
  formatSignedMoney,
  formatUnit,
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

describe("formatUnit", () => {
  it("abbreviates at K/M/B/T/Q boundaries (the missing-B class)", () => {
    // The 14.698 shares-out bug: a raw count must read with a unit.
    expect(formatUnit(14_698_000_000)).toBe("14.70B");
    expect(formatUnit(1_500)).toBe("1.50K");
    expect(formatUnit(2_300_000)).toBe("2.30M");
    expect(formatUnit(4.2e12)).toBe("4.20T");
    expect(formatUnit(6.217e15)).toBe("6.22Q");
  });
  it("drops the mantissa decimals once it reads >= 100", () => {
    expect(formatUnit(622_000_000_000_000_000)).toBe("622Q");
    expect(formatUnit(150_000_000)).toBe("150M");
  });
  it("locale-groups below the K tier and keeps a sign", () => {
    expect(formatUnit(999)).toBe("999");
    expect(formatUnit(-2_500_000)).toBe("-2.50M");
  });
  it("degrades non-finite to em-dash", () => {
    expect(formatUnit(NaN)).toBe("—");
    expect(formatUnit(Infinity)).toBe("—");
  });
  it("honours an explicit decimal precision", () => {
    expect(formatUnit(1_234_000, 1)).toBe("1.2M");
  });
});

describe("formatPrice", () => {
  it("renders >= 1 at 2dp by default", () => {
    expect(formatPrice(35.927)).toBe("35.93");
    expect(formatPrice(1)).toBe("1.00");
  });
  it("keeps significant digits for sub-unit magnitudes", () => {
    expect(formatPrice(0.000021)).toBe("0.000021");
  });
  it("respects a custom decimal count", () => {
    expect(formatPrice(35.927, 3)).toBe("35.927");
  });
  it("degrades non-finite", () => {
    expect(formatPrice(NaN)).toBe("—");
  });
});
