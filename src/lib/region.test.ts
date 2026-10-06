import { describe, expect, it } from "vitest";

import { DEFAULT_REGION, regionConfig } from "@/lib/region";

// R15-DATA-092: the default region is India, not REGIONS[0] (US) — a copy or
// fallback that assumes US is stale/wrong.
describe("region", () => {
  it("DEFAULT_REGION is India", () => {
    expect(DEFAULT_REGION).toBe("IN");
  });

  it("regionConfig falls back to DEFAULT_REGION (India), not REGIONS[0]", () => {
    expect(regionConfig("does-not-exist" as never).id).toBe("IN");
  });

  it("regionConfig resolves a known region to itself", () => {
    expect(regionConfig("US").id).toBe("US");
  });
});
