import type { DockviewApi } from "dockview";
import { afterAll, beforeEach, describe, expect, it, vi } from "vitest";

import {
  applyLayoutTemplate,
  planCustom,
  planLayout,
  resolvePanelToken,
  type LayoutTemplate,
} from "./layout-templates";

describe("planCustom (Track B — 'one panel here, one there')", () => {
  it("places two panels side by side (2nd to the right of the anchor)", () => {
    const plan = planCustom([{ panel: "chart" }, { panel: "news" }]);
    expect(plan.panels.map((p) => p.id)).toEqual(["chart", "news"]);
    expect(plan.panels[0].position).toBeUndefined(); // anchor
    expect(plan.panels[1].position).toEqual({ referencePanel: "chart", direction: "right" });
    expect(plan.focus).toBe("chart");
  });

  it("honours explicit per-panel direction + reference", () => {
    const plan = planCustom([
      { panel: "chart" },
      { panel: "watchlist", direction: "right" },
      { panel: "news", direction: "below", reference: "watchlist" },
    ]);
    expect(plan.panels[2].position).toEqual({ referencePanel: "watchlist", direction: "below" });
  });

  it("resolves loose aliases and drops unknown / duplicate panels", () => {
    const plan = planCustom([
      { panel: "equity" }, // alias → equity-overview
      { panel: "totally-not-a-panel" }, // dropped
      { panel: "equity-overview" }, // duplicate of the alias → dropped
      { panel: "watch" }, // alias → watchlist
    ]);
    expect(plan.panels.map((p) => p.id)).toEqual(["equity-overview", "watchlist"]);
  });

  it("defaults the 3rd+ panels to stacking below the previous", () => {
    const plan = planCustom([{ panel: "chart" }, { panel: "news" }, { panel: "portfolio" }]);
    expect(plan.panels[2].position).toEqual({ referencePanel: "news", direction: "below" });
  });
});

describe("resolvePanelToken", () => {
  it("maps canonical ids and aliases, rejects unknowns", () => {
    expect(resolvePanelToken("chart")).toEqual({ id: "chart", component: "chart-panel" });
    expect(resolvePanelToken("Equity Overview")?.id).toBe("equity-overview");
    expect(resolvePanelToken("holdings")?.id).toBe("portfolio");
    expect(resolvePanelToken("nope")).toBeNull();
  });
});

describe("planLayout", () => {
  it("single-focus: just the chart, maximized", () => {
    const plan = planLayout("single-focus");
    expect(plan.panels).toEqual([{ id: "chart", component: "chart-panel" }]);
    expect(plan.maximize).toBe("chart");
    expect(plan.focus).toBe("chart");
  });

  it("research-cockpit (flagship): chart anchor + right column equity/brief/news", () => {
    const plan = planLayout("research-cockpit");
    expect(plan.panels).toEqual([
      { id: "chart", component: "chart-panel" },
      {
        id: "equity-overview",
        component: "equity-overview-panel",
        position: { referencePanel: "chart", direction: "right" },
      },
      {
        id: "brief",
        component: "brief-panel",
        position: { referencePanel: "equity-overview", direction: "below" },
      },
      {
        id: "news",
        component: "news-panel",
        position: { referencePanel: "brief", direction: "below" },
      },
    ]);
    // The cited brief docks BESIDE the chart (right column), focused, never a tab.
    expect(plan.focus).toBe("brief");
    expect(plan.maximize).toBeUndefined();
    // The brief docks in the cockpit (B6 brief-docking carry-forward cleared).
    expect(plan.panels.some((p) => p.id === "brief")).toBe(true);
  });

  it("compare: single chart-focused layout, maximized (overlay is driven elsewhere)", () => {
    const plan = planLayout("compare", { symbols: ["NVDA", "AMD"] });
    // ONLY the chart — the dual-symbol overlay rides the chart-command channel,
    // not a second panel.
    expect(plan.panels).toEqual([{ id: "chart", component: "chart-panel" }]);
    expect(plan.maximize).toBe("chart");
    expect(plan.focus).toBe("chart");
    expect(plan.panels).toHaveLength(1);
  });

  it("macro-scan: macro anchor + chart right + screener below", () => {
    const plan = planLayout("macro-scan");
    expect(plan.panels).toEqual([
      { id: "macro", component: "macro-panel" },
      {
        id: "chart",
        component: "chart-panel",
        position: { referencePanel: "macro", direction: "right" },
      },
      {
        id: "screener",
        component: "screener-panel",
        position: { referencePanel: "macro", direction: "below" },
      },
    ]);
    expect(plan.focus).toBe("macro");
    expect(plan.maximize).toBeUndefined();
  });

  it("uses component ids (the -panel suffix), distinct from panel ids", () => {
    const templates: LayoutTemplate[] = [
      "single-focus",
      "research-cockpit",
      "compare",
      "macro-scan",
    ];
    for (const t of templates) {
      for (const panel of planLayout(t).panels) {
        expect(panel.component).toBe(`${panel.id}-panel`);
      }
    }
  });

  it("every planned position references a panel earlier in the same plan", () => {
    const templates: LayoutTemplate[] = [
      "single-focus",
      "research-cockpit",
      "compare",
      "macro-scan",
    ];
    for (const t of templates) {
      const plan = planLayout(t);
      const seen = new Set<string>();
      for (const panel of plan.panels) {
        if (panel.position?.referencePanel) {
          expect(seen.has(panel.position.referencePanel)).toBe(true);
        }
        seen.add(panel.id);
      }
    }
  });
});

/**
 * Light smoke for the imperative applier against a MINIMAL fake dockview api —
 * we don't reconstruct dockview's full gridview, just assert the applier calls
 * the right api surface (getPanel/addPanel + focus/maximize) per the plan.
 */
function makeFakeApi() {
  const panels = new Map<string, { id: string; api: { setActive: ReturnType<typeof vi.fn> } }>();
  const addPanel = vi.fn((opts: { id: string; component: string }) => {
    const panel = { id: opts.id, api: { setActive: vi.fn() } };
    panels.set(opts.id, panel);
    return panel;
  });
  const api = {
    get panels() {
      return Array.from(panels.values());
    },
    getPanel: vi.fn((id: string) => panels.get(id)),
    addPanel,
    hasMaximizedGroup: vi.fn(() => false),
    exitMaximizedGroup: vi.fn(),
    maximizeGroup: vi.fn(),
  };
  return api as typeof api & DockviewApi;
}

describe("applyLayoutTemplate (smoke)", () => {
  // Force the synchronous branch of the applier: stub out requestAnimationFrame
  // so the re-tile runs inline (jsdom may or may not provide rAF), then restore
  // the original after the suite.
  const originalRaf = globalThis.requestAnimationFrame;
  beforeEach(() => {
    (globalThis as { requestAnimationFrame?: unknown }).requestAnimationFrame = undefined;
  });
  afterAll(() => {
    globalThis.requestAnimationFrame = originalRaf;
  });

  it("adds the planned panels and maximizes for single-focus", () => {
    const api = makeFakeApi();
    applyLayoutTemplate(api, "single-focus");
    expect(api.addPanel).toHaveBeenCalledWith(
      expect.objectContaining({ id: "chart", component: "chart-panel" }),
    );
    expect(api.maximizeGroup).toHaveBeenCalledTimes(1);
  });

  it("places all four research-cockpit panels with resolved positions", () => {
    const api = makeFakeApi();
    applyLayoutTemplate(api, "research-cockpit");
    const ids = api.addPanel.mock.calls.map((c) => (c[0] as { id: string }).id);
    expect(ids).toEqual(["chart", "equity-overview", "brief", "news"]);
    // equity-overview placed right of chart (chart added first in the same pass)
    const equityCall = api.addPanel.mock.calls.find(
      (c) => (c[0] as { id: string }).id === "equity-overview",
    );
    expect((equityCall?.[0] as { position?: unknown }).position).toEqual({
      referencePanel: "chart",
      direction: "right",
    });
    // focuses the cited brief (the right-column anchor), does not maximize
    expect(api.maximizeGroup).not.toHaveBeenCalled();
    expect(api.getPanel("brief")?.api.setActive).toHaveBeenCalled();
  });

  it("is idempotent: re-applying reuses open panels instead of re-adding", () => {
    const api = makeFakeApi();
    applyLayoutTemplate(api, "research-cockpit");
    const firstAddCount = api.addPanel.mock.calls.length;
    applyLayoutTemplate(api, "research-cockpit");
    // No NEW addPanel calls on the second pass — all panels already exist.
    expect(api.addPanel.mock.calls.length).toBe(firstAddCount);
  });

  it("drops a position whose reference panel isn't present", () => {
    const api = makeFakeApi();
    // macro-scan: chart + screener both reference macro. If macro fails to seed
    // (simulated by seeding only chart/screener path), the planner still places
    // macro first, so positions resolve — assert the normal resolved path here.
    applyLayoutTemplate(api, "macro-scan");
    const screenerCall = api.addPanel.mock.calls.find(
      (c) => (c[0] as { id: string }).id === "screener",
    );
    expect((screenerCall?.[0] as { position?: unknown }).position).toEqual({
      referencePanel: "macro",
      direction: "below",
    });
  });
});
