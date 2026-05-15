import { beforeEach, describe, expect, it } from "vitest";

import {
  selectEventBySource,
  selectSnapshot,
  usePanelContextBus,
} from "@/store/panel-context";
import type { PanelContextEvent } from "../../types/panel-context";

function event(source: string, payload: unknown, kind: "symbol" | "snapshot" = "snapshot"): PanelContextEvent {
  return { source, kind, payload, emittedAt: Date.now() };
}

describe("panel-context bus", () => {
  beforeEach(() => {
    usePanelContextBus.setState({
      lastEventBySource: {},
      focusedSource: null,
      updatedAt: 0,
    });
  });

  it("publish stores the event keyed by source", () => {
    const e = event("chart-abc", { symbol: "AAPL" });
    usePanelContextBus.getState().publish(e);
    expect(usePanelContextBus.getState().lastEventBySource["chart-abc"]).toEqual(e);
  });

  it("publish overwrites the prior event from the same source", () => {
    usePanelContextBus.getState().publish(event("chart-abc", { symbol: "AAPL" }));
    const second = event("chart-abc", { symbol: "MSFT" });
    usePanelContextBus.getState().publish(second);
    expect(usePanelContextBus.getState().lastEventBySource["chart-abc"]).toEqual(second);
  });

  it("multiple sources coexist in lastEventBySource", () => {
    usePanelContextBus.getState().publish(event("chart-abc", { symbol: "AAPL" }));
    usePanelContextBus.getState().publish(event("watchlist", { selectedSymbol: "MSFT" }));
    const map = usePanelContextBus.getState().lastEventBySource;
    expect(Object.keys(map).sort()).toEqual(["chart-abc", "watchlist"]);
  });

  it("setFocusedSource is a no-op when the source did not change", () => {
    usePanelContextBus.getState().setFocusedSource("chart-abc");
    const updatedAtA = usePanelContextBus.getState().updatedAt;
    usePanelContextBus.getState().setFocusedSource("chart-abc");
    const updatedAtB = usePanelContextBus.getState().updatedAt;
    expect(updatedAtA).toBe(updatedAtB);
  });

  it("unregisterSource drops the event and clears focus if it pointed at that source", () => {
    usePanelContextBus.getState().publish(event("chart-abc", { symbol: "AAPL" }));
    usePanelContextBus.getState().setFocusedSource("chart-abc");
    usePanelContextBus.getState().unregisterSource("chart-abc");
    const state = usePanelContextBus.getState();
    expect(state.lastEventBySource["chart-abc"]).toBeUndefined();
    expect(state.focusedSource).toBeNull();
  });

  it("unregisterSource is a no-op for sources that never published", () => {
    const before = usePanelContextBus.getState();
    usePanelContextBus.getState().unregisterSource("nothing-here");
    const after = usePanelContextBus.getState();
    expect(after).toBe(before);
  });
});

describe("selectSnapshot", () => {
  beforeEach(() => {
    usePanelContextBus.setState({
      lastEventBySource: {},
      focusedSource: null,
      updatedAt: 0,
    });
  });

  it("returns a frozen empty snapshot before any publish — referentially stable", () => {
    const a = selectSnapshot(usePanelContextBus.getState());
    const b = selectSnapshot(usePanelContextBus.getState());
    expect(a).toBe(b);
    expect(a.focusedSource).toBeNull();
    expect(Object.keys(a.lastEventBySource)).toHaveLength(0);
  });

  it("returns the live snapshot once a panel has published", () => {
    usePanelContextBus.getState().publish(event("watchlist", { selectedSymbol: "AAPL" }));
    usePanelContextBus.getState().setFocusedSource("watchlist");
    const snap = selectSnapshot(usePanelContextBus.getState());
    expect(snap.focusedSource).toBe("watchlist");
    expect(snap.lastEventBySource.watchlist?.payload).toEqual({ selectedSymbol: "AAPL" });
  });
});

describe("selectEventBySource", () => {
  beforeEach(() => {
    usePanelContextBus.setState({
      lastEventBySource: {},
      focusedSource: null,
      updatedAt: 0,
    });
  });

  it("returns the latest event from a known source", () => {
    const e = event("chart-abc", { symbol: "AAPL" });
    usePanelContextBus.getState().publish(e);
    expect(selectEventBySource(usePanelContextBus.getState(), "chart-abc")).toEqual(e);
  });

  it("returns null for an unknown source", () => {
    expect(selectEventBySource(usePanelContextBus.getState(), "nothing")).toBeNull();
  });
});
