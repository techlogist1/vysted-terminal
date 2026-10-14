import { describe, it, expect } from "vitest";
import { usePanelContextBus } from "@/store/panel-context";
import { captureTerminalState } from "@/modules/chat/context-provider";

describe("AGENT-053 news snapshot at HEAD", () => {
  it("what the agent receives for an open News panel", () => {
    // Exactly the payload NewsFeedPanel.tsx:207-215 publishes: the watched
    // symbols and the hovered article's id (a sha1 of url+title, news_provider.py:138).
    usePanelContextBus.getState().publish({
      source: "news",
      kind: "snapshot",
      payload: { watchedSymbols: ["RELIANCE.NS", "TCS.NS"], focusedArticleId: "3f1c2a9d0b7e4c55a8e1d2f3b4c5d6e7f8091a2b" },
      emittedAt: Date.now(),
    });
    const state = captureTerminalState();
    const news = state.otherPanels.find((p) => p.source === "news");
    console.log("NEWS otherPanels entry:", JSON.stringify(news));
    console.log("FULL snapshot keys:", Object.keys(state).join(","));
    expect(news).toBeDefined();
  });
});
