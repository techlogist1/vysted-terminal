import { describe, expect, it } from "vitest";

import {
  META_ROW_BREAKPOINTS,
  metaRowPlan,
  metaRowStepForWidth,
  type MetaRowStep,
} from "./meta-row-collapse";

describe("metaRowStepForWidth", () => {
  it("selects each ladder step by measured width", () => {
    expect(metaRowStepForWidth(800)).toBe("full");
    expect(metaRowStepForWidth(470)).toBe("full");
    expect(metaRowStepForWidth(469)).toBe("short");
    expect(metaRowStepForWidth(380)).toBe("short");
    expect(metaRowStepForWidth(379)).toBe("icons");
    expect(metaRowStepForWidth(250)).toBe("icons");
    expect(metaRowStepForWidth(249)).toBe("overflow");
    expect(metaRowStepForWidth(170)).toBe("overflow");
    expect(metaRowStepForWidth(169)).toBe("two-row");
    expect(metaRowStepForWidth(1)).toBe("two-row");
  });

  it("lands the 280px dock minimum (≈256px row width) on icons — all controls visible", () => {
    // 280px dock − 2 × 12px row padding.
    expect(metaRowStepForWidth(256)).toBe("icons");
  });

  it("assumes room when unmeasured (0 / NaN / negative) so SSR and tests render full", () => {
    expect(metaRowStepForWidth(0)).toBe("full");
    expect(metaRowStepForWidth(-5)).toBe("full");
    expect(metaRowStepForWidth(Number.NaN)).toBe("full");
  });

  it("is monotonic: a narrower row never yields a LESS collapsed step", () => {
    const order: MetaRowStep[] = ["full", "short", "icons", "overflow", "two-row"];
    let prev = order.indexOf(metaRowStepForWidth(1000));
    for (let w = 1000; w >= 1; w--) {
      const idx = order.indexOf(metaRowStepForWidth(w));
      expect(idx).toBeGreaterThanOrEqual(prev);
      prev = idx;
    }
  });
});

describe("metaRowPlan", () => {
  it("full: everything labeled, depth label shown", () => {
    expect(metaRowPlan("full")).toEqual({
      labels: "full",
      showDepthLabel: true,
      overflowMenu: false,
      twoRow: false,
    });
  });

  it("short: labels stay, the depth text label is the first thing to drop", () => {
    expect(metaRowPlan("short")).toEqual({
      labels: "short",
      showDepthLabel: false,
      overflowMenu: false,
      twoRow: false,
    });
  });

  it("icons: icon+tooltip chips, no overflow yet", () => {
    expect(metaRowPlan("icons")).toEqual({
      labels: "icons",
      showDepthLabel: false,
      overflowMenu: false,
      twoRow: false,
    });
  });

  it("overflow: autonomy + model fold behind the ⋯ popover", () => {
    expect(metaRowPlan("overflow")).toEqual({
      labels: "icons",
      showDepthLabel: false,
      overflowMenu: true,
      twoRow: false,
    });
  });

  it("two-row: nothing hides — the row wraps instead of clipping", () => {
    expect(metaRowPlan("two-row")).toEqual({
      labels: "icons",
      showDepthLabel: false,
      overflowMenu: false,
      twoRow: true,
    });
  });

  it("breakpoints descend with the ladder", () => {
    expect(META_ROW_BREAKPOINTS.full).toBeGreaterThan(META_ROW_BREAKPOINTS.short);
    expect(META_ROW_BREAKPOINTS.short).toBeGreaterThan(META_ROW_BREAKPOINTS.icons);
    expect(META_ROW_BREAKPOINTS.icons).toBeGreaterThan(META_ROW_BREAKPOINTS.overflow);
  });
});
