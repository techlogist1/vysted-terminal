import { beforeEach, describe, expect, it, vi } from "vitest";

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

  it("switching tab mid-stream stops the run first and archives the partial as stopped (R15-CODE-FRONTEND-002)", () => {
    const chat = useChatHistoryStore.getState();
    useAgentSpacesStore.setState({
      spaces: [
        { id: "a", title: "A" },
        { id: "b", title: "B" },
      ],
      activeId: "a",
      archived: { b: [msg("in B")] },
    });
    const replyId = chat.beginAssistantMessage({});
    chat.appendAssistantDelta(replyId, "Partial ");
    // The abort must fire while thread A is still the live transcript.
    const abort = vi.fn(() => expect(useChatHistoryStore.getState().messages[0]?.id).toBe(replyId));
    chat.setLiveAbort(abort);

    useAgentSpacesStore.getState().switchTo("b");

    expect(abort).toHaveBeenCalledTimes(1);
    const partial = useAgentSpacesStore.getState().archived.a?.[0];
    expect(partial).toMatchObject({
      id: replyId,
      content: "Partial ",
      pending: false,
      stopped: true,
    });
    expect(useChatHistoryStore.getState().streamingMessageId).toBeNull();
    expect(useChatHistoryStore.getState().liveAbort).toBeNull();
    // A late delta of the stopped run never lands in thread B.
    useChatHistoryStore.getState().appendAssistantDelta(replyId, "late");
    expect(useChatHistoryStore.getState().messages.map((m) => m.content)).toEqual(["in B"]);
  });
});
