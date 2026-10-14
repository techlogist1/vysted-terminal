import { beforeEach, describe, expect, it } from "vitest";

import {
  RESEARCH_DEPTHS,
  isResearchDepth,
  resetResearchDepthStoreForTests,
  useResearchDepthStore,
} from "./research-depth";

describe("research-depth store", () => {
  beforeEach(() => {
    resetResearchDepthStoreForTests();
  });

  it("defaults to normal", () => {
    expect(useResearchDepthStore.getState().depth).toBe("normal");
  });

  it("setDepth moves between the three stops", () => {
    useResearchDepthStore.getState().setDepth("deep");
    expect(useResearchDepthStore.getState().depth).toBe("deep");
    useResearchDepthStore.getState().setDepth("ultra");
    expect(useResearchDepthStore.getState().depth).toBe("ultra");
    useResearchDepthStore.getState().setDepth("normal");
    expect(useResearchDepthStore.getState().depth).toBe("normal");
  });

  it("exposes exactly three ordered stops", () => {
    expect(RESEARCH_DEPTHS).toEqual(["normal", "deep", "ultra"]);
  });

  it("isResearchDepth guards the union", () => {
    expect(isResearchDepth("deep")).toBe(true);
    expect(isResearchDepth("heavy")).toBe(false); // BriefDepth vocabulary, not this knob
    expect(isResearchDepth(undefined)).toBe(false);
  });
});
