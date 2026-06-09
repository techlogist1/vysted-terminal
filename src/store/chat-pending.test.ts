import { beforeEach, describe, expect, it } from "vitest";

import { useChatPendingStore } from "./chat-pending";

describe("chat-pending — FIFO prompt queue (R7 Track C)", () => {
  beforeEach(() => {
    useChatPendingStore.setState({ queue: [] });
  });

  it("drains queued prompts in FIFO order", () => {
    const store = useChatPendingStore.getState();
    store.queuePrompt("first");
    store.queuePrompt("second");
    store.queuePrompt("third");
    expect(useChatPendingStore.getState().queue).toEqual(["first", "second", "third"]);
    expect(useChatPendingStore.getState().consumePrompt()).toBe("first");
    expect(useChatPendingStore.getState().consumePrompt()).toBe("second");
    expect(useChatPendingStore.getState().consumePrompt()).toBe("third");
    expect(useChatPendingStore.getState().consumePrompt()).toBeNull();
  });

  it("keeps the palette one-shot contract: one queued prompt consumes exactly once", () => {
    useChatPendingStore.getState().queuePrompt("ask ai prompt");
    expect(useChatPendingStore.getState().consumePrompt()).toBe("ask ai prompt");
    // Second consume finds nothing — the prompt fires only once.
    expect(useChatPendingStore.getState().consumePrompt()).toBeNull();
    expect(useChatPendingStore.getState().queue).toEqual([]);
  });

  it("removePrompt deletes one chip by index without disturbing order", () => {
    const store = useChatPendingStore.getState();
    store.queuePrompt("a");
    store.queuePrompt("b");
    store.queuePrompt("c");
    useChatPendingStore.getState().removePrompt(1);
    expect(useChatPendingStore.getState().queue).toEqual(["a", "c"]);
  });

  it("clearQueue empties everything", () => {
    useChatPendingStore.getState().queuePrompt("a");
    useChatPendingStore.getState().queuePrompt("b");
    useChatPendingStore.getState().clearQueue();
    expect(useChatPendingStore.getState().queue).toEqual([]);
    expect(useChatPendingStore.getState().consumePrompt()).toBeNull();
  });
});
