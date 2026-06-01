import { beforeEach, describe, expect, it } from "vitest";

import { resetAgentModeStoreForTests, useAgentModeStore } from "@/store/agent-mode";

describe("agent-mode store (FR-003; JARVIS sprint Track B — inferred-intent collapse)", () => {
  beforeEach(() => resetAgentModeStoreForTests());

  it("defaults to the inferred Agent surface (read/edit/build inferred server-side)", () => {
    expect(useAgentModeStore.getState().mode).toBe("agent");
  });

  it("switches between the two surfaces (Agent / Delegate)", () => {
    for (const mode of ["delegate", "agent"] as const) {
      useAgentModeStore.getState().setMode(mode);
      expect(useAgentModeStore.getState().mode).toBe(mode);
    }
  });

  it("coerces an unknown mode back to Agent (safe default)", () => {
    useAgentModeStore.getState().setMode("nonsense" as never);
    expect(useAgentModeStore.getState().mode).toBe("agent");
  });
});
