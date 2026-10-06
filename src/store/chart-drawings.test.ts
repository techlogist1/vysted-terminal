import { beforeEach, describe, expect, it } from "vitest";

import {
  DEFAULT_CHART_SYMBOL,
  defaultChartSymbolForRegion,
  drawingsFor,
  newDrawingId,
  useChartDrawingsStore,
} from "./chart-drawings";
import type { DrawingSpec } from "../../types/drawings";

function makeDrawing(panelId: string, kind: DrawingSpec["kind"], id: string): DrawingSpec {
  return {
    id,
    panelId,
    symbol: "SPY",
    timeframe: "1d",
    kind,
    points: [{ time: 1700000000, price: 100 }],
    style: { color: "#e9a94d", lineWidth: 1 },
    createdAt: 0,
  };
}

beforeEach(() => {
  useChartDrawingsStore.setState({ byPanel: {}, views: {} });
});

describe("useChartDrawingsStore", () => {
  it("starts empty", () => {
    expect(useChartDrawingsStore.getState().byPanel).toEqual({});
  });

  it("adds drawings keyed by panel id", () => {
    const { addDrawing, getDrawings } = useChartDrawingsStore.getState();
    addDrawing("chart-1", makeDrawing("chart-1", "trendline", "a"));
    addDrawing("chart-1", makeDrawing("chart-1", "rectangle", "b"));
    addDrawing("chart-2", makeDrawing("chart-2", "horizontal-line", "c"));

    const panel1 = useChartDrawingsStore.getState().getDrawings("chart-1");
    expect(panel1).toHaveLength(2);
    expect(panel1.map((d) => d.id)).toEqual(["a", "b"]);
    expect(useChartDrawingsStore.getState().getDrawings("chart-2")).toHaveLength(1);
    void getDrawings;
  });

  it("removes a drawing by id without disturbing siblings", () => {
    const { addDrawing, removeDrawing } = useChartDrawingsStore.getState();
    addDrawing("p", makeDrawing("p", "trendline", "x"));
    addDrawing("p", makeDrawing("p", "rectangle", "y"));

    removeDrawing("p", "x");

    const remaining = useChartDrawingsStore.getState().getDrawings("p");
    expect(remaining).toHaveLength(1);
    expect(remaining[0]!.id).toBe("y");
  });

  it("updates a drawing in-place by id", () => {
    const { addDrawing, updateDrawing } = useChartDrawingsStore.getState();
    addDrawing("p", makeDrawing("p", "trendline", "x"));

    updateDrawing("p", "x", (drawing) => ({ ...drawing, locked: true }));

    expect(useChartDrawingsStore.getState().getDrawings("p")[0]!.locked).toBe(true);
  });

  it("returns a panel's drawings only for the symbol/timeframe they were made on (R15-UI-020)", () => {
    const { addDrawing } = useChartDrawingsStore.getState();
    addDrawing("chart", {
      ...makeDrawing("chart", "horizontal-line", "rel"),
      symbol: "RELIANCE.NS",
    });
    addDrawing("chart", {
      ...makeDrawing("chart", "trendline", "rel-1h"),
      symbol: "RELIANCE.NS",
      timeframe: "1h",
    });
    const all = useChartDrawingsStore.getState().getDrawings("chart");

    expect(drawingsFor(all, "TCS.NS", "1d")).toEqual([]);
    expect(drawingsFor(all, "RELIANCE.NS", "1d").map((d) => d.id)).toEqual(["rel"]);
    expect(drawingsFor(all, "RELIANCE.NS", "1h").map((d) => d.id)).toEqual(["rel-1h"]);
  });

  it("setView records a panel's view and is a no-op when nothing changed", () => {
    const { setView } = useChartDrawingsStore.getState();
    const view = { symbol: "TCS.NS", timeframe: "1d", indicators: ["rsi"], compare: null };
    setView("chart", view);
    const first = useChartDrawingsStore.getState().views;
    setView("chart", { ...view, indicators: ["rsi"] });
    expect(useChartDrawingsStore.getState().views).toBe(first);
    expect(first["chart"]).toEqual(view);
  });

  it("snapshots in WorkspaceDrawings shape and restores via replaceAll", () => {
    const { addDrawing, snapshot, replaceAll } = useChartDrawingsStore.getState();
    addDrawing("p1", makeDrawing("p1", "ellipse", "e1"));
    addDrawing("p2", makeDrawing("p2", "ray", "r1"));

    const snap = snapshot();
    expect(Object.keys(snap.byPanel).sort()).toEqual(["p1", "p2"]);

    useChartDrawingsStore.setState({ byPanel: {} });
    replaceAll(snap);

    expect(useChartDrawingsStore.getState().getDrawings("p1")[0]!.kind).toBe("ellipse");
    expect(useChartDrawingsStore.getState().getDrawings("p2")[0]!.kind).toBe("ray");
  });

  it("clears one panel's drawings without affecting others", () => {
    const { addDrawing, clearPanel } = useChartDrawingsStore.getState();
    addDrawing("p1", makeDrawing("p1", "trendline", "a"));
    addDrawing("p2", makeDrawing("p2", "trendline", "b"));

    clearPanel("p1");

    expect(useChartDrawingsStore.getState().getDrawings("p1")).toHaveLength(0);
    expect(useChartDrawingsStore.getState().getDrawings("p2")).toHaveLength(1);
  });

  it("generates distinct drawing ids", () => {
    const ids = new Set([newDrawingId(), newDrawingId(), newDrawingId()]);
    expect(ids.size).toBe(3);
  });

  it("defaultChartSymbolForRegion opens IN on the NIFTY 50 index, US on SPY (R15-UI-076)", () => {
    expect(defaultChartSymbolForRegion("IN")).toBe("^NSEI");
    expect(defaultChartSymbolForRegion("US")).toBe("SPY");
    expect(defaultChartSymbolForRegion("GLOBAL")).toBe("SPY");
  });

  it("DEFAULT_CHART_SYMBOL follows the app's default region (IN)", () => {
    expect(DEFAULT_CHART_SYMBOL).toBe(defaultChartSymbolForRegion("IN"));
  });
});
