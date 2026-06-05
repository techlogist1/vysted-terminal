import { beforeEach, describe, expect, it } from "vitest";

import { resetAgentCommandStoreForTests, sendToAgent, useAgentCommandStore } from "./agent-command";

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
    expect(useAgentCommandStore.getState().command).toEqual({
      prompt: "research AAPL — go all out",
      seq: 1,
    });
  });
});
