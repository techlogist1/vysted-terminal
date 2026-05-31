import { beforeEach, describe, expect, it } from "vitest";

import { resetAgentModeStoreForTests, useAgentModeStore } from "@/store/agent-mode";

describe("agent-mode store (FR-003)", () => {
  beforeEach(() => resetAgentModeStoreForTests());

  it("defaults to Ask (read-only) so the agent never mutates by default", () => {
    expect(useAgentModeStore.getState().mode).toBe("ask");
  });

  it("switches between the four modes", () => {
    for (const mode of ["edit", "build", "delegate", "ask"] as const) {
      useAgentModeStore.getState().setMode(mode);
      expect(useAgentModeStore.getState().mode).toBe(mode);
    }
  });

  it("coerces an unknown mode back to Ask (safe default)", () => {
    useAgentModeStore.getState().setMode("nonsense" as never);
    expect(useAgentModeStore.getState().mode).toBe("ask");
  });
});
