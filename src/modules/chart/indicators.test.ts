import { describe, expect, it } from "vitest";

import { indicatorByKey } from "./indicators";

describe("indicatorByKey (R15-UI-091)", () => {
  it("resolves an exact base key unchanged", () => {
    const def = indicatorByKey("rsi");
    expect(def?.key).toBe("rsi");
    expect(def?.label).toBe("RSI");
  });

  it("resolves a numeric base:param spec, keeping the full spec as key", () => {
    const def = indicatorByKey("ema:9");
    expect(def).toBeDefined();
    expect(def?.key).toBe("ema:9");
    expect(def?.label).toBe("EMA 9");
    expect(def?.panel).toBe("price");
  });

  it("distinct params on the same base resolve to distinct defs (ema:9 vs ema:21)", () => {
    const nine = indicatorByKey("ema:9");
    const twentyOne = indicatorByKey("ema:21");
    expect(nine?.key).not.toBe(twentyOne?.key);
    expect(nine?.label).not.toBe(twentyOne?.label);
  });

  it("resolves a non-numeric anchor spec (vwap:week)", () => {
    const def = indicatorByKey("vwap:week");
    expect(def?.key).toBe("vwap:week");
    expect(def?.label).toBe("VWAP (week)");
  });

  it("returns undefined for an unknown base", () => {
    expect(indicatorByKey("bogus:9")).toBeUndefined();
    expect(indicatorByKey("bogus")).toBeUndefined();
  });
});
