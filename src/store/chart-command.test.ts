import { beforeEach, describe, expect, it } from "vitest";

import { resetChartCommandStoreForTests, useChartCommandStore } from "./chart-command";

beforeEach(() => {
  resetChartCommandStoreForTests();
});

describe("useChartCommandStore", () => {
  it("starts empty", () => {
    const state = useChartCommandStore.getState();
    expect(state.command).toBeNull();
    expect(state.activeSymbol).toBeNull();
    expect(state.indicatorCommand).toBeNull();
    expect(state.activeIndicators).toEqual([]);
    expect(state.comparisonCommand).toBeNull();
    expect(state.activeComparison).toBeNull();
  });

  describe("loadSymbol", () => {
    it("issues a command and bumps seq on every call", () => {
      const { loadSymbol } = useChartCommandStore.getState();
      loadSymbol("AAPL", "1h");
      expect(useChartCommandStore.getState().command).toEqual({
        symbol: "AAPL",
        timeframe: "1h",
        seq: 1,
      });
      loadSymbol("AAPL");
      expect(useChartCommandStore.getState().command).toMatchObject({ symbol: "AAPL", seq: 2 });
    });
  });

  describe("reportActiveSymbol", () => {
    it("records the chart's displayed symbol", () => {
      useChartCommandStore.getState().reportActiveSymbol("MSFT");
      expect(useChartCommandStore.getState().activeSymbol).toBe("MSFT");
    });
  });

  describe("setIndicators", () => {
    it("carries the indicators and bumps seq on every call", () => {
      const { setIndicators } = useChartCommandStore.getState();
      setIndicators(["rsi", "macd"]);
      expect(useChartCommandStore.getState().indicatorCommand).toEqual({
        symbol: undefined,
        indicators: ["rsi", "macd"],
        seq: 1,
      });
      setIndicators(["rsi", "macd"]);
      expect(useChartCommandStore.getState().indicatorCommand?.seq).toBe(2);
    });

    it("scopes the command to a symbol when provided", () => {
      useChartCommandStore.getState().setIndicators(["ema"], "NVDA");
      expect(useChartCommandStore.getState().indicatorCommand).toEqual({
        symbol: "NVDA",
        indicators: ["ema"],
        seq: 1,
      });
    });
  });

  describe("reportActiveIndicators", () => {
    it("records the chart's selected indicator keys", () => {
      useChartCommandStore.getState().reportActiveIndicators(["sma", "vwap"]);
      expect(useChartCommandStore.getState().activeIndicators).toEqual(["sma", "vwap"]);
    });
  });

  describe("setComparison", () => {
    it("carries the symbol and bumps seq on every call", () => {
      const { setComparison } = useChartCommandStore.getState();
      setComparison("QQQ");
      expect(useChartCommandStore.getState().comparisonCommand).toEqual({ symbol: "QQQ", seq: 1 });
      setComparison("QQQ");
      expect(useChartCommandStore.getState().comparisonCommand?.seq).toBe(2);
    });
  });

  describe("reportActiveComparison", () => {
    it("records the comparison-overlay symbol (and clears to null)", () => {
      useChartCommandStore.getState().reportActiveComparison("SPY");
      expect(useChartCommandStore.getState().activeComparison).toBe("SPY");
      useChartCommandStore.getState().reportActiveComparison(null);
      expect(useChartCommandStore.getState().activeComparison).toBeNull();
    });
  });

  describe("resetChartCommandStoreForTests", () => {
    it("clears every field", () => {
      const store = useChartCommandStore.getState();
      store.loadSymbol("AAPL");
      store.reportActiveSymbol("AAPL");
      store.setIndicators(["rsi"]);
      store.reportActiveIndicators(["rsi"]);
      store.setComparison("QQQ");
      store.reportActiveComparison("QQQ");

      resetChartCommandStoreForTests();

      const state = useChartCommandStore.getState();
      expect(state.command).toBeNull();
      expect(state.activeSymbol).toBeNull();
      expect(state.indicatorCommand).toBeNull();
      expect(state.activeIndicators).toEqual([]);
      expect(state.comparisonCommand).toBeNull();
      expect(state.activeComparison).toBeNull();
    });
  });
});
