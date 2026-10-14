import { describe, expect, it } from "vitest";

import { useAgentSpacesStore } from "./agent-spaces";
import { type ChatMessage, useChatHistoryStore } from "./chat-history";
import { useResearchSpacesStore } from "./research-spaces";

function msg(role: "user" | "assistant", content: string, createdAt = 0): ChatMessage {
  return { id: `${content}-${Math.random()}`, role, content, createdAt };
}
const R = { name: "Research: NVDA", symbol: "NVDA" };
const live = () => useChatHistoryStore.getState().messages.map((m) => m.content);

describe("vshard0 fresh variant: chat-tab click while a research space is open", () => {
  it("clicking another chat tab inside a research space, then leaving it", () => {
    useResearchSpacesStore.setState({ byName: {} });
    useAgentSpacesStore.setState({
      spaces: [{ id: "A", title: "Chat 1" }, { id: "B", title: "Chat 2" }],
      activeId: "A",
      archived: { B: [msg("user", "B question", 1)] },
    });
    useChatHistoryStore.getState().loadMessages([msg("user", "A question", 1)]);

    useResearchSpacesStore.getState().switchSpace(null, R); // enter research space from tab A
    useChatHistoryStore.getState().loadMessages([msg("user", "R question", 2), msg("assistant", "R answer", 3)]);
    useAgentSpacesStore.getState().switchTo("B"); // user clicks the 'Chat 2' tab in the always-visible strip
    console.log("after tab click: live=", live(), "archived=", Object.fromEntries(Object.entries(useAgentSpacesStore.getState().archived).map(([k, v]) => [k, v.map((m) => m.content)])));
    useResearchSpacesStore.getState().switchSpace(R, null); // leave the research space
    const mem = useResearchSpacesStore.getState().getMemory(R.name)?.transcript.map((t) => t.content);
    console.log("after leaving: live=", live(), "R memory=", mem, "activeId=", useAgentSpacesStore.getState().activeId,
      "archived=", Object.fromEntries(Object.entries(useAgentSpacesStore.getState().archived).map(([k, v]) => [k, v.map((m) => m.content)])));
    expect(mem).toEqual(["R question", "R answer"]);
    expect(live()).toEqual(["B question"]);
  });

  it("'+' new tab inside a research space, then leaving it", () => {
    useResearchSpacesStore.setState({ byName: {} });
    useAgentSpacesStore.setState({ spaces: [{ id: "A", title: "Chat 1" }], activeId: "A", archived: {} });
    useChatHistoryStore.getState().loadMessages([msg("user", "A question", 1)]);
    useResearchSpacesStore.getState().switchSpace(null, R);
    useChatHistoryStore.getState().loadMessages([msg("user", "R question", 2)]);
    useAgentSpacesStore.getState().newSpace();
    useResearchSpacesStore.getState().switchSpace(R, null);
    const mem = useResearchSpacesStore.getState().getMemory(R.name)?.transcript.map((t) => t.content);
    console.log("newSpace variant: R memory=", mem, "live=", live());
    expect(mem).toEqual(["R question"]);
  });
});
