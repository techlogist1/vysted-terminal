import { beforeEach, describe, expect, it } from "vitest";

import {
  isRuntimeNotice,
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

  // The old test pinned the regex's own stale copy ("kept the previous, richer
  // brief"), which the runtime had already reworded (R15-AGENT-031): a notice is
  // now recognised by its kind, whatever its copy says.
  it("recognises a runtime notice by its step kind, never its copy", () => {
    expect(isRuntimeNotice("notice")).toBe(true);
    expect(isRuntimeNotice("engine")).toBe(false);
    expect(isRuntimeNotice("search")).toBe(false);
  });
});
