import { beforeEach, describe, expect, it } from "vitest";

import { selectSubscriptions, useChartSyncBus } from "./chart-sync";

beforeEach(() => {
  useChartSyncBus.setState({
    crosshair: null,
    visibleRange: null,
    symbol: null,
    subscriptions: {},
  });
});

describe("useChartSyncBus", () => {
  it("starts with no broadcasts and no subscriptions", () => {
    const state = useChartSyncBus.getState();
    expect(state.crosshair).toBeNull();
    expect(state.visibleRange).toBeNull();
    expect(state.symbol).toBeNull();
    expect(state.subscriptions).toEqual({});
  });

  it("records the source on every broadcast and bumps seq", () => {
    const { setCrosshair, setVisibleRange, setSymbol } = useChartSyncBus.getState();
    setCrosshair("p1", 1700000000);
    expect(useChartSyncBus.getState().crosshair).toMatchObject({
      source: "p1",
      time: 1700000000,
      seq: 1,
    });
    setCrosshair("p2", 1700000060);
    expect(useChartSyncBus.getState().crosshair?.seq).toBe(2);

    setVisibleRange("p1", 1, 2);
    expect(useChartSyncBus.getState().visibleRange).toMatchObject({ source: "p1", from: 1, to: 2 });

    setSymbol("p1", "AAPL");
    expect(useChartSyncBus.getState().symbol).toMatchObject({ source: "p1", symbol: "AAPL" });
  });

  it("toggles per-panel subscriptions independently", () => {
    const { setSubscription } = useChartSyncBus.getState();
    setSubscription("chart-1", "crosshair", true);
    setSubscription("chart-1", "symbol", true);
    setSubscription("chart-2", "visibleRange", true);

    const subs1 = selectSubscriptions(useChartSyncBus.getState(), "chart-1");
    expect(subs1).toEqual({ crosshair: true, visibleRange: false, symbol: true });

    const subs2 = selectSubscriptions(useChartSyncBus.getState(), "chart-2");
    expect(subs2).toEqual({ crosshair: false, visibleRange: true, symbol: false });
  });

  it("returns default subscriptions for unknown panels", () => {
    const subs = selectSubscriptions(useChartSyncBus.getState(), "ghost");
    expect(subs).toEqual({ crosshair: false, visibleRange: false, symbol: false });
  });

  it("unregisters a panel's subscriptions cleanly", () => {
    const { setSubscription, unregisterPanel } = useChartSyncBus.getState();
    setSubscription("chart-1", "crosshair", true);
    setSubscription("chart-2", "symbol", true);

    unregisterPanel("chart-1");

    expect(useChartSyncBus.getState().subscriptions["chart-1"]).toBeUndefined();
    expect(useChartSyncBus.getState().subscriptions["chart-2"]).toEqual({
      crosshair: false,
      visibleRange: false,
      symbol: true,
    });
  });
});
