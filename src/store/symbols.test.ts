import { beforeEach, describe, expect, it } from "vitest";

import {
  assetClassOf,
  DEFAULT_SYMBOLS,
  defaultSymbolsForRegion,
  toNewsSymbol,
  useSymbolsStore,
} from "./symbols";

beforeEach(() => {
  useSymbolsStore.setState({ entries: [...DEFAULT_SYMBOLS] });
});

describe("assetClassOf", () => {
  it("treats a slash pair as crypto and everything else as equity", () => {
    expect(assetClassOf("BTC/USDT")).toBe("crypto");
    expect(assetClassOf("RELIANCE.NS")).toBe("equity");
    expect(assetClassOf("SPY")).toBe("equity");
  });
});

describe("defaultSymbolsForRegion (R15-UI-076)", () => {
  it("seeds IN with NSE names, not the US watchlist", () => {
    const symbols = defaultSymbolsForRegion("IN").map((e) => e.symbol);
    expect(symbols).toEqual(["^NSEI", "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS"]);
  });

  it("keeps SPY/QQQ for US", () => {
    const symbols = defaultSymbolsForRegion("US").map((e) => e.symbol);
    expect(symbols).toContain("SPY");
    expect(symbols).toContain("QQQ");
  });

  it("DEFAULT_SYMBOLS follows the app's default region (IN)", () => {
    expect(DEFAULT_SYMBOLS).toEqual(defaultSymbolsForRegion("IN"));
  });
});

describe("useSymbolsStore", () => {
  it("seeds with the default (region-IN) watchlist", () => {
    expect(useSymbolsStore.getState().entries).toEqual(DEFAULT_SYMBOLS);
  });

  it("adds a normalized, de-duplicated symbol", () => {
    const { addSymbol } = useSymbolsStore.getState();
    addSymbol(" msft ", "equity");
    addSymbol("MSFT", "equity");
    const symbols = useSymbolsStore.getState().entries.map((e) => e.symbol);
    expect(symbols.filter((s) => s === "MSFT")).toHaveLength(1);
  });

  it("removes a symbol case-insensitively", () => {
    const { removeSymbol } = useSymbolsStore.getState();
    removeSymbol("reliance.ns");
    expect(useSymbolsStore.getState().entries.map((e) => e.symbol)).not.toContain("RELIANCE.NS");
  });
});

describe("toNewsSymbol", () => {
  it("returns the base asset for a crypto pair", () => {
    expect(toNewsSymbol({ symbol: "BTC/USDT", assetClass: "crypto" })).toBe("BTC");
  });

  it("returns the symbol unchanged for an equity", () => {
    expect(toNewsSymbol({ symbol: "TCS.NS", assetClass: "equity" })).toBe("TCS.NS");
  });
});
