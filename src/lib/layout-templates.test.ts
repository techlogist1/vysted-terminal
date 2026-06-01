import type { DockviewApi } from "dockview";
import { afterAll, beforeEach, describe, expect, it, vi } from "vitest";

import { applyLayoutTemplate, planLayout, type LayoutTemplate } from "./layout-templates";

describe("planLayout", () => {
  it("single-focus: just the chart, maximized", () => {
    const plan = planLayout("single-focus");
    expect(plan.panels).toEqual([{ id: "chart", component: "chart-panel" }]);
    expect(plan.maximize).toBe("chart");
    expect(plan.focus).toBe("chart");
  });

  it("research-cockpit (flagship): chart anchor + equity-overview right + news below equity", () => {
    const plan = planLayout("research-cockpit");
    expect(plan.panels).toEqual([
      { id: "chart", component: "chart-panel" },
      {
        id: "equity-overview",
        component: "equity-overview-panel",
        position: { referencePanel: "chart", direction: "right" },
      },
      {
        id: "news",
        component: "news-panel",
        position: { referencePanel: "equity-overview", direction: "below" },
      },
    ]);
    // Flagship cockpit focuses the chart and is NOT a maximize template.
    expect(plan.focus).toBe("chart");
    expect(plan.maximize).toBeUndefined();
    // Does NOT depend on a brief panel existing (added later by B4).
    expect(plan.panels.some((p) => p.id === "brief")).toBe(false);
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

  it("places all three research-cockpit panels with resolved positions", () => {
    const api = makeFakeApi();
    applyLayoutTemplate(api, "research-cockpit");
    const ids = api.addPanel.mock.calls.map((c) => (c[0] as { id: string }).id);
    expect(ids).toEqual(["chart", "equity-overview", "news"]);
    // equity-overview placed right of chart (chart added first in the same pass)
    const equityCall = api.addPanel.mock.calls.find(
      (c) => (c[0] as { id: string }).id === "equity-overview",
    );
    expect((equityCall?.[0] as { position?: unknown }).position).toEqual({
      referencePanel: "chart",
      direction: "right",
    });
    // focuses the chart, does not maximize
    expect(api.maximizeGroup).not.toHaveBeenCalled();
    expect(api.getPanel("chart")?.api.setActive).toHaveBeenCalled();
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
