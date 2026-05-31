import { describe, expect, it, vi } from "vitest";

import { applyDefaultLayout } from "@/config/default-layout";

interface AddPanelCall {
  id: string;
  position?: { referencePanel: string; direction: string };
}

function fakeApi() {
  const calls: AddPanelCall[] = [];
  const api = {
    addPanel: vi.fn((opts: AddPanelCall) => {
      calls.push(opts);
    }),
  };
  return { api, calls };
}

const ALL_PANELS = new Set(["chart", "equity-overview", "watchlist", "news", "portfolio", "chat"]);

describe("applyDefaultLayout", () => {
  it("places the five-panel starter cockpit and never opens Settings (FR-032)", () => {
    const { api, calls } = fakeApi();
    applyDefaultLayout(api as never, ALL_PANELS);
    expect(calls.map((call) => call.id)).toEqual([
      "chart",
      "equity-overview",
      "watchlist",
      "news",
      "portfolio",
    ]);
    expect(calls.some((call) => call.id === "settings")).toBe(false);
  });

  it("no longer opens the agent as a panel — it is the shell column (FR-001)", () => {
    const { api, calls } = fakeApi();
    applyDefaultLayout(api as never, ALL_PANELS);
    expect(calls.some((call) => call.id === "chat")).toBe(false);
  });

  it("skips panels whose module is disabled", () => {
    const { api, calls } = fakeApi();
    applyDefaultLayout(api as never, new Set(["chart", "watchlist"]));
    expect(calls.map((call) => call.id)).toEqual(["chart", "watchlist"]);
  });

  it("drops a reference position when the reference panel was not placed", () => {
    const { api, calls } = fakeApi();
    // news references watchlist; with watchlist disabled, news must still place.
    applyDefaultLayout(api as never, new Set(["chart", "news"]));
    const news = calls.find((call) => call.id === "news");
    expect(news).toBeDefined();
    expect(news?.position).toBeUndefined();
  });
});
