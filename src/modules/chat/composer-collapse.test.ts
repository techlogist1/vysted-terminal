import { describe, expect, it } from "vitest";

import {
  COMPOSER_CONTROLS_BREAKPOINTS,
  composerControlsPlan,
  composerControlsStepForWidth,
  type ComposerControlsStep,
} from "./composer-collapse";

describe("composerControlsStepForWidth", () => {
  it("selects each ladder step by measured width", () => {
    expect(composerControlsStepForWidth(800)).toBe("full");
    expect(composerControlsStepForWidth(380)).toBe("full");
    expect(composerControlsStepForWidth(379)).toBe("compact");
    expect(composerControlsStepForWidth(310)).toBe("compact");
    expect(composerControlsStepForWidth(309)).toBe("icons");
    expect(composerControlsStepForWidth(1)).toBe("icons");
  });

  it("lands the 280px dock minimum (≈238px row width) on icons — all controls usable", () => {
    // 280px dock − 2 × 12px form padding − 2 × 1px field border − 2 × 8px row padding.
    expect(composerControlsStepForWidth(238)).toBe("icons");
  });

  it("lands a 320px dock (≈278px row width) on icons — nothing overlaps", () => {
    expect(composerControlsStepForWidth(278)).toBe("icons");
  });

  it("assumes room when unmeasured (0 / NaN / negative) so SSR and tests render full", () => {
    expect(composerControlsStepForWidth(0)).toBe("full");
    expect(composerControlsStepForWidth(-5)).toBe("full");
    expect(composerControlsStepForWidth(Number.NaN)).toBe("full");
  });

  it("is monotonic: a narrower row never yields a LESS collapsed step", () => {
    const order: ComposerControlsStep[] = ["full", "compact", "icons"];
    let prev = order.indexOf(composerControlsStepForWidth(1000));
    for (let w = 1000; w >= 1; w--) {
      const idx = order.indexOf(composerControlsStepForWidth(w));
      expect(idx).toBeGreaterThanOrEqual(prev);
      prev = idx;
    }
  });
});

describe("composerControlsPlan", () => {
  it("full: designed model text, depth expands on hover/focus", () => {
    expect(composerControlsPlan("full")).toEqual({ model: "full", depthExpands: true });
  });

  it("compact: model text tightens first, depth still expands", () => {
    expect(composerControlsPlan("compact")).toEqual({ model: "short", depthExpands: true });
  });

  it("icons: model → icon + tooltip, depth → active stop only", () => {
    expect(composerControlsPlan("icons")).toEqual({ model: "icon", depthExpands: false });
  });

  it("breakpoints descend with the ladder", () => {
    expect(COMPOSER_CONTROLS_BREAKPOINTS.full).toBeGreaterThan(
      COMPOSER_CONTROLS_BREAKPOINTS.compact,
    );
  });
});
