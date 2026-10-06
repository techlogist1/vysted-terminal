import { beforeEach, describe, expect, it } from "vitest";

import {
  escalateResearchDepth,
  researchDepthPrompt,
  resetAgentCommandStoreForTests,
  sendToAgent,
  useAgentCommandStore,
} from "./agent-command";

beforeEach(() => {
  resetAgentCommandStoreForTests();
});

describe("useAgentCommandStore", () => {
  it("starts empty", () => {
    expect(useAgentCommandStore.getState().command).toBeNull();
  });

  it("issues a prompt command and bumps seq on every send (so a repeat re-fires)", () => {
    const { send } = useAgentCommandStore.getState();
    send("research NVDA — go deeper");
    expect(useAgentCommandStore.getState().command).toEqual({
      prompt: "research NVDA — go deeper",
      seq: 1,
    });
    // An identical prompt still re-triggers (clicking "Go deeper" twice).
    send("research NVDA — go deeper");
    expect(useAgentCommandStore.getState().command).toMatchObject({
      prompt: "research NVDA — go deeper",
      seq: 2,
    });
  });

  it("sendToAgent is a non-reactive shortcut for the same channel", () => {
    sendToAgent("research AAPL — go all out");
    expect(useAgentCommandStore.getState().command).toMatchObject({
      prompt: "research AAPL — go all out",
      seq: 1,
    });
    // A plain prompt carries no depth (only a research escalation does).
    expect(useAgentCommandStore.getState().command?.depth).toBeUndefined();
  });

  it("researchDepthPrompt composes a deterministic explicit-tier directive", () => {
    // The chat composes the prompt from {subject, depth} — the tier word is
    // load-bearing DATA, not a fuzzy phrase the model has to interpret.
    expect(researchDepthPrompt("NVDA", "deep")).toBe("research NVDA at depth=deep");
    expect(researchDepthPrompt("Apple's moat", "heavy")).toBe(
      "research Apple's moat at depth=heavy",
    );
  });

  it("escalateResearchDepth carries the explicit next tier as structured data", () => {
    escalateResearchDepth("NVDA", "heavy");
    expect(useAgentCommandStore.getState().command).toEqual({
      prompt: "research NVDA at depth=heavy",
      depth: "heavy",
      seq: 1,
    });
  });
});
