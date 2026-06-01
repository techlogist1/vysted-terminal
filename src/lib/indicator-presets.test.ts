import { describe, expect, it } from "vitest";

import { INDICATOR_CATALOG } from "@/modules/chart/indicators";

import {
  type AssetClass,
  CRYPTO_DEFAULT,
  EQUITY_DAILY,
  EQUITY_INTRADAY,
  ETF_DAILY,
  presetFor,
} from "./indicator-presets";

const CATALOG_KEYS = new Set(INDICATOR_CATALOG.map((indicator) => indicator.key));

describe("presetFor", () => {
  it("returns the equity daily set for daily timeframes", () => {
    for (const timeframe of ["1d", "1wk", "1mo"]) {
      expect(presetFor("equity", timeframe)).toEqual(["ma", "volume", "rsi", "macd"]);
    }
  });

  it("returns the equity intraday set for 1h and below", () => {
    for (const timeframe of ["1h", "30m", "15m", "5m", "1m"]) {
      expect(presetFor("equity", timeframe)).toEqual(["ema", "vwap", "rsi", "volume"]);
    }
  });

  it("returns the etf daily set (no MACD) for etf daily timeframes", () => {
    expect(presetFor("etf", "1d")).toEqual(["ma", "volume", "rsi"]);
  });

  it("uses the intraday set for etf intraday timeframes", () => {
    expect(presetFor("etf", "1h")).toEqual(["ema", "vwap", "rsi", "volume"]);
  });

  it("returns the crypto set regardless of timeframe", () => {
    for (const timeframe of ["1d", "1wk", "1mo", "1h", "5m", "1m"]) {
      expect(presetFor("crypto", timeframe)).toEqual(["ema", "vwap", "rsi", "volume"]);
    }
  });

  it("ignores region (no key-set change in v1)", () => {
    expect(presetFor("equity", "1d", "IN")).toEqual(presetFor("equity", "1d", "US"));
    expect(presetFor("crypto", "1h", "GLOBAL")).toEqual(presetFor("crypto", "1h"));
  });

  it("returns a fresh mutable array (callers may sort/splice safely)", () => {
    const first = presetFor("equity", "1d");
    first.push("rsi");
    expect(presetFor("equity", "1d")).toEqual(["ma", "volume", "rsi", "macd"]);
  });
});

describe("preset constants reference real catalog keys", () => {
  const presets: Record<string, readonly string[]> = {
    EQUITY_DAILY,
    EQUITY_INTRADAY,
    ETF_DAILY,
    CRYPTO_DEFAULT,
  };

  for (const [name, keys] of Object.entries(presets)) {
    it(`every key in ${name} exists in INDICATOR_CATALOG`, () => {
      for (const key of keys) {
        expect(CATALOG_KEYS.has(key)).toBe(true);
      }
    });
  }

  it("every key returned by presetFor exists in INDICATOR_CATALOG", () => {
    const cases: [AssetClass, string][] = [
      ["equity", "1d"],
      ["equity", "1h"],
      ["etf", "1d"],
      ["etf", "1h"],
      ["crypto", "1d"],
      ["crypto", "5m"],
    ];
    for (const [assetClass, timeframe] of cases) {
      for (const key of presetFor(assetClass, timeframe)) {
        expect(CATALOG_KEYS.has(key)).toBe(true);
      }
    }
  });
});
