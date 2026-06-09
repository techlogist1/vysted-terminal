import { beforeEach, describe, expect, it } from "vitest";

import { useChatHistoryStore } from "./chat-history";

describe("chat-history — agent plan (Track 6 #2)", () => {
  beforeEach(() => {
    useChatHistoryStore.getState().clear();
  });

  it("attaches a visible plan to the owning assistant message", () => {
    const store = useChatHistoryStore.getState();
    const id = store.beginAssistantMessage({ agentId: "copilot" });
    store.setPlan(id, {
      goal: "open a chart and add to watchlist",
      steps: [
        {
          action: "set_chart_symbol",
          args: { symbol: "AAPL" },
          rationale: "chart it",
          staged: true,
        },
        { action: "research", args: { query: "bull case" }, rationale: "dig in", staged: false },
      ],
      note: undefined,
    });
    const msg = useChatHistoryStore.getState().messages.find((m) => m.id === id);
    expect(msg?.plan?.steps).toHaveLength(2);
    expect(msg?.plan?.steps[0].staged).toBe(true);
    expect(msg?.plan?.steps[1].action).toBe("research");
  });
});

describe("chat-history — user-stopped streams (R7 Track C)", () => {
  beforeEach(() => {
    useChatHistoryStore.getState().clear();
  });

  it("stopAssistantMessage keeps the partial content and marks it stopped, not errored", () => {
    const store = useChatHistoryStore.getState();
    const id = store.beginAssistantMessage({ agentId: "copilot" });
    store.appendAssistantDelta(id, "Partial answer about SPY…");

    useChatHistoryStore.getState().stopAssistantMessage(id);

    const msg = useChatHistoryStore.getState().messages.find((m) => m.id === id);
    expect(msg?.content).toBe("Partial answer about SPY…");
    expect(msg?.stopped).toBe(true);
    expect(msg?.pending).toBe(false);
    expect(msg?.error).toBeFalsy();
    expect(useChatHistoryStore.getState().streamingMessageId).toBeNull();
  });

  it("stopAssistantMessage on a non-streaming id leaves streamingMessageId for the live one", () => {
    const store = useChatHistoryStore.getState();
    const finished = store.beginAssistantMessage({ agentId: "copilot" });
    useChatHistoryStore.getState().finalizeAssistantMessage(finished, null);
    const live = useChatHistoryStore.getState().beginAssistantMessage({ agentId: "copilot" });

    useChatHistoryStore.getState().stopAssistantMessage(finished);

    expect(useChatHistoryStore.getState().streamingMessageId).toBe(live);
  });
});

describe("chat-history — research steps (Track A)", () => {
  beforeEach(() => {
    useChatHistoryStore.getState().clear();
  });

  it("accumulates research steps onto the owning message in order", () => {
    const store = useChatHistoryStore.getState();
    const id = store.beginAssistantMessage({ agentId: "copilot" });

    store.appendResearchStep(id, {
      stepKind: "plan",
      detail: "decomposed",
      status: "ok",
      index: 1,
    });
    store.appendResearchStep(id, {
      stepKind: "search",
      detail: "searched",
      status: "ok",
      index: 2,
      latencyMs: 42,
    });

    const msg = useChatHistoryStore.getState().messages.find((m) => m.id === id);
    expect(msg?.researchSteps?.map((s) => s.stepKind)).toEqual(["plan", "search"]);
    expect(msg?.researchSteps?.[1].latencyMs).toBe(42);
  });

  it("stamps researchStartedAt once (on the first step, not later ones)", () => {
    const store = useChatHistoryStore.getState();
    const id = store.beginAssistantMessage({ agentId: "copilot" });

    store.appendResearchStep(id, { stepKind: "plan", detail: "a", status: "ok", index: 1 });
    const first = useChatHistoryStore
      .getState()
      .messages.find((m) => m.id === id)?.researchStartedAt;
    expect(typeof first).toBe("number");

    store.appendResearchStep(id, { stepKind: "search", detail: "b", status: "ok", index: 2 });
    const second = useChatHistoryStore
      .getState()
      .messages.find((m) => m.id === id)?.researchStartedAt;
    expect(second).toBe(first); // set-once — the elapsed timer anchors on the first step
  });

  it("keeps research steps independent of the plain tool-step list", () => {
    const store = useChatHistoryStore.getState();
    const id = store.beginAssistantMessage({ agentId: "copilot" });

    store.appendToolStep(id, "Using fundamentals");
    store.appendResearchStep(id, { stepKind: "plan", detail: "a", status: "ok", index: 1 });

    const msg = useChatHistoryStore.getState().messages.find((m) => m.id === id);
    expect(msg?.toolSteps).toEqual(["Using fundamentals"]);
    expect(msg?.researchSteps).toHaveLength(1);
  });
});
