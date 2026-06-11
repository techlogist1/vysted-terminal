import { beforeEach, describe, expect, it } from "vitest";

import {
  isDivergenceNotice,
  resetMessageNoticesForTests,
  useMessageNoticesStore,
} from "./message-notices";

describe("message-notices store (R10 D39/D43)", () => {
  beforeEach(() => {
    resetMessageNoticesForTests();
  });

  it("keeps error frames and notices keyed by message id", () => {
    const s = useMessageNoticesStore.getState();
    s.setErrorFrame("m1", { action: "Top up.", detail: "raw", code: "provider_402" });
    s.addNotice("m1", "The panel kept the previous, richer brief.");
    s.addNotice("m1", "The brief panel did not confirm the publish.");
    expect(useMessageNoticesStore.getState().errorFrames.m1?.code).toBe("provider_402");
    expect(useMessageNoticesStore.getState().notices.m1).toHaveLength(2);
    expect(useMessageNoticesStore.getState().notices.m2).toBeUndefined();
    s.clear();
    expect(useMessageNoticesStore.getState().errorFrames).toEqual({});
    expect(useMessageNoticesStore.getState().notices).toEqual({});
  });

  it("recognises ONLY the runtime's divergence notices on the engine channel", () => {
    expect(isDivergenceNotice("engine", "The brief panel did not confirm the publish")).toBe(true);
    expect(isDivergenceNotice("engine", "The panel kept the previous, richer brief.")).toBe(true);
    // Ordinary engine lines + non-engine steps stay in the step trace.
    expect(isDivergenceNotice("engine", "backend searxng ready")).toBe(false);
    expect(isDivergenceNotice("search", "kept the previous, richer brief")).toBe(false);
  });
});
