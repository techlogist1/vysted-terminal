import { beforeEach, describe, expect, it } from "vitest";

import { DEFAULT_REGION } from "@/lib/region";
import { useSettingsStore } from "@/store/settings";

import {
  formatCompactMoney,
  formatCompactNumber,
  formatMoney,
  formatPercent,
  formatPrice,
  formatSignedMoney,
  formatUnit,
  groupDigits,
  providerShortLabel,
} from "./format";

// R10 (E1): the shipped default region flipped US→IN, so the no-currency
// fallback now resolves INR/en-IN. These baseline blocks pin the formatters
// against an EXPLICIT US region — the unit under test is the instrument-currency
// law (R8 §6) and the magnitude/precision behavior, not the shipped default
// (that truth is pinned in "R10 IN-first region default" below).
beforeEach(() => {
  useSettingsStore.setState({ region: "US" });
});

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
  it("follows the instrument currency in both modes", () => {
    expect(formatSignedMoney(500, false, "EUR")).toBe("+€500.00");
    expect(formatSignedMoney(2_500_000, true, "INR")).toBe("+₹2.50M");
  });
});

// R8 §6 — "currency formats by the INSTRUMENT's currency, never the locale
// default (no ₹ on AAPL)". The instrument's quote/fundamentals currency code
// threads through every money formatter; absent → region default (USD here).
describe("currency-by-instrument", () => {
  it("formatMoney renders the instrument currency", () => {
    expect(formatMoney(1234.5, "USD")).toBe("$1,234.50");
    expect(formatMoney(1234.5, "INR")).toBe("₹1,234.50");
    expect(formatMoney(1234.5, "EUR")).toBe("€1,234.50");
    expect(formatMoney(1234.5, "JPY")).toBe("¥1,234.5");
  });
  it("formatCompactMoney carries the instrument currency through the compact path", () => {
    // The live D10 defect: AAPL market cap rendered "₹4.27T" — the instrument
    // (USD) must win over the region default.
    expect(formatCompactMoney(4.27e12, "USD")).toBe("$4.27T");
    expect(formatCompactMoney(4.27e12, "INR")).toBe("₹4.27T");
    expect(formatCompactMoney(-3_400_000, "EUR")).toBe("-€3.40M");
    // Below the compact threshold it still respects the instrument.
    expect(formatCompactMoney(999_999, "INR")).toBe("₹999,999.00");
  });
  it("falls back to the region default on a null/blank/garbage code", () => {
    expect(formatMoney(10, null)).toBe("$10.00");
    expect(formatMoney(10, "")).toBe("$10.00");
    expect(formatMoney(10, "   ")).toBe("$10.00");
    expect(formatMoney(10, "rupees")).toBe("$10.00");
    expect(formatCompactMoney(1_500_000, undefined)).toBe("$1.50M");
  });
  it("normalises a lowercase ISO code", () => {
    expect(formatMoney(10, "inr")).toBe("₹10.00");
  });
});

// R10 (E1): the IN-first default — `src/lib/region.ts` DEFAULT_REGION mirrors
// the sidecar's `config._DEFAULT_REGION` flip (brief §2, same commit). Under the
// shipped default an instrument-less money render falls back to INR with en-IN
// (lakh/crore) digit grouping; an explicit instrument currency still wins.
describe("R10 IN-first region default", () => {
  it("ships IN as the default region", () => {
    expect(DEFAULT_REGION).toBe("IN");
  });
  it("falls back to INR/en-IN when no instrument currency is given", () => {
    useSettingsStore.setState({ region: DEFAULT_REGION });
    expect(formatMoney(10, null)).toBe("₹10.00");
    expect(formatMoney(123456.7)).toBe("₹1,23,456.70");
    expect(formatCompactMoney(1_500_000)).toBe("₹1.50M");
  });
  it("instrument currency beats the IN region default (R8 §6 — no ₹ on AAPL)", () => {
    useSettingsStore.setState({ region: DEFAULT_REGION });
    expect(formatCompactMoney(4.27e12, "USD")).toBe("$4.27T");
  });
});

describe("providerShortLabel", () => {
  it("maps known providers to their designed short forms (no CSS mid-word clips)", () => {
    // The live D3 defect: "yfinance" clipped to "YFINAN" in the watchlist chip.
    expect(providerShortLabel("yfinance")).toBe("YF");
    expect(providerShortLabel("newsapi")).toBe("NewsAPI");
    expect(providerShortLabel("sec.gov")).toBe("SEC");
    expect(providerShortLabel("fred")).toBe("FRED");
    expect(providerShortLabel("nse")).toBe("NSE");
    expect(providerShortLabel("bse")).toBe("BSE");
    expect(providerShortLabel("ccxt")).toBe("CCXT");
  });
  it("is case/whitespace-insensitive on lookup", () => {
    expect(providerShortLabel("YFinance")).toBe("YF");
    expect(providerShortLabel(" yfinance ")).toBe("YF");
  });
  it("passes an unknown provider through unchanged", () => {
    expect(providerShortLabel("my-custom-feed")).toBe("my-custom-feed");
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

describe("groupDigits", () => {
  it("groups a precision-string without parsing to a (lossy) number", () => {
    // Larger than Number.MAX_SAFE_INTEGER — must NOT round-trip through Number.
    expect(groupDigits("90071992547409910")).toBe("90,071,992,547,409,910");
    expect(groupDigits("1500")).toBe("1,500");
    expect(groupDigits("-2500000")).toBe("-2,500,000");
    expect(groupDigits("1234.56")).toBe("1,234.56");
  });
  it("passes a non-numeric string through and degrades empty/null to em-dash", () => {
    expect(groupDigits("n/a")).toBe("n/a");
    expect(groupDigits("")).toBe("—");
    expect(groupDigits(null)).toBe("—");
    expect(groupDigits(undefined)).toBe("—");
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
