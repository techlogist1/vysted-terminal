/**
 * Chat pending-prompt queue.
 *
 * A real FIFO (R7 Track C): prompts typed while a stream is in flight queue
 * here as visible, removable chips above the composer field, and `ChatSidebar`
 * — the single owner of the send pipeline — drains them IN ORDER, one at a
 * time, through `handleSend` when the stream ends.
 *
 * The original one-shot palette semantics are a strict subset and keep
 * working unchanged: `queuePrompt` enqueues, `consumePrompt` dequeues the
 * head exactly once (returns `null` when empty), so a single queued "Ask AI"
 * prompt still fires exactly once on the next ChatSidebar drain pass.
 *
 * Self-contained by design — no change to the Tier-1 plugin contract or the
 * chat-history store. Session-state only.
 */

import { create } from "zustand";

interface ChatPendingState {
  /** Prompts waiting to send, oldest first (rendered as the queue chips). */
  queue: string[];
  /** Push a prompt onto the BACK of the queue. */
  queuePrompt: (prompt: string) => void;
  /** Dequeue the HEAD prompt (FIFO). Returns the prompt, or null when empty. */
  consumePrompt: () => string | null;
  /** Remove one queued prompt by index (the chip's [x]). */
  removePrompt: (index: number) => void;
  /** Drop every queued prompt. */
  clearQueue: () => void;
}

export const useChatPendingStore = create<ChatPendingState>((set, get) => ({
  queue: [],
  queuePrompt: (prompt) => set((state) => ({ queue: [...state.queue, prompt] })),
  consumePrompt: () => {
    const { queue } = get();
    if (queue.length === 0) {
      return null;
    }
    set({ queue: queue.slice(1) });
    return queue[0];
  },
  removePrompt: (index) => set((state) => ({ queue: state.queue.filter((_, i) => i !== index) })),
  clearQueue: () => set({ queue: [] }),
}));
