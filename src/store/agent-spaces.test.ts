import { beforeEach, describe, expect, it } from "vitest";

import { useAgentSpacesStore } from "./agent-spaces";
import { type ChatMessage, useChatHistoryStore } from "./chat-history";

function msg(content: string): ChatMessage {
  return { id: `${content}-${Math.random()}`, role: "user", content, createdAt: 0 };
}

describe("agent spaces", () => {
  beforeEach(() => {
    useChatHistoryStore.getState().clear();
    useAgentSpacesStore.setState({
      spaces: [{ id: "a", title: "A" }],
      activeId: "a",
      archived: {},
    });
  });

  it("new space archives the live transcript and starts empty; switching restores it", () => {
    useChatHistoryStore.getState().loadMessages([msg("hello A")]);

    useAgentSpacesStore.getState().newSpace();
    // The new space is empty + active; A's transcript is archived.
    expect(useChatHistoryStore.getState().messages).toHaveLength(0);
    const st = useAgentSpacesStore.getState();
    expect(st.spaces).toHaveLength(2);
    expect(st.activeId).not.toBe("a");
    expect(st.archived.a).toHaveLength(1);

    useAgentSpacesStore.getState().switchTo("a");
    expect(useChatHistoryStore.getState().messages[0]?.content).toBe("hello A");
  });

  it("closing the active space restores a remaining one and never drops the last", () => {
    useAgentSpacesStore.setState({
      spaces: [
        { id: "a", title: "A" },
        { id: "b", title: "B" },
      ],
      activeId: "b",
      archived: { a: [msg("in A")] },
    });
    useChatHistoryStore.getState().loadMessages([msg("in B")]);

    useAgentSpacesStore.getState().closeSpace("b");
    const st = useAgentSpacesStore.getState();
    expect(st.spaces).toHaveLength(1);
    expect(st.activeId).toBe("a");
    expect(useChatHistoryStore.getState().messages[0]?.content).toBe("in A");

    // The last remaining space cannot be closed.
    useAgentSpacesStore.getState().closeSpace("a");
    expect(useAgentSpacesStore.getState().spaces).toHaveLength(1);
  });
});
