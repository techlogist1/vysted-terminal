import { beforeEach, describe, expect, it, vi } from "vitest";

import { resetAgentRunsStoreForTests, useAgentRunsStore } from "@/store/agent-runs";

describe("agent-runs store — the agents rail (FR-027 / US3 AS3)", () => {
  beforeEach(() => resetAgentRunsStoreForTests());

  it("starts a run as running and surfaces it in activeRuns", () => {
    const id = useAgentRunsStore.getState().startRun({
      agentId: "copilot",
      agentName: "Copilot",
      mode: "delegate",
    });
    const runs = useAgentRunsStore.getState().activeRuns();
    expect(runs).toHaveLength(1);
    expect(runs[0]).toMatchObject({ id, status: "running", mode: "delegate" });
  });

  it("ends a run with a terminal status and drops it from activeRuns", () => {
    const id = useAgentRunsStore.getState().startRun({
      agentId: null,
      agentName: "Direct chat",
      mode: "ask",
    });
    useAgentRunsStore.getState().endRun(id, "done");
    expect(useAgentRunsStore.getState().activeRuns()).toHaveLength(0);
    expect(useAgentRunsStore.getState().runs[0].status).toBe("done");
  });

  it("cancelRun invokes the run's abort and marks it cancelled", () => {
    const abort = vi.fn();
    const id = useAgentRunsStore.getState().startRun({
      agentId: "copilot",
      agentName: "Copilot",
      mode: "build",
      abort,
    });
    useAgentRunsStore.getState().cancelRun(id);
    expect(abort).toHaveBeenCalledTimes(1);
    expect(useAgentRunsStore.getState().runs[0].status).toBe("cancelled");
  });

  it("clearFinished keeps only running runs", () => {
    const a = useAgentRunsStore.getState().startRun({ agentId: "x", agentName: "X", mode: "ask" });
    useAgentRunsStore.getState().startRun({ agentId: "y", agentName: "Y", mode: "ask" });
    useAgentRunsStore.getState().endRun(a, "done");
    useAgentRunsStore.getState().clearFinished();
    expect(useAgentRunsStore.getState().runs).toHaveLength(1);
    expect(useAgentRunsStore.getState().runs[0].status).toBe("running");
  });
});
