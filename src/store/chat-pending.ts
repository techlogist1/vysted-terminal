/**
 * Chat pending-prompt store.
 *
 * A minimal one-shot signal: when the command palette's "Ask AI" row is
 * selected, it writes a `pendingPrompt` here then opens the chat panel.
 * `ChatSidebar` consumes it on mount/update via a `useEffect`, submits it
 * to `handleSend`, then clears it so it fires only once.
 *
 * Self-contained by design — no change to the Tier-1 plugin contract or the
 * chat-history store.  Resets automatically on clear.
 */

import { create } from "zustand";

interface ChatPendingState {
  /** Prompt queued for auto-submit, or null if none pending. */
  pendingPrompt: string | null;
  /** Queue a prompt for the next ChatSidebar mount/update to submit. */
  queuePrompt: (prompt: string) => void;
  /** Consume and clear the pending prompt.  Returns the prompt or null. */
  consumePrompt: () => string | null;
}

export const useChatPendingStore = create<ChatPendingState>((set, get) => ({
  pendingPrompt: null,
  queuePrompt: (prompt) => set({ pendingPrompt: prompt }),
  consumePrompt: () => {
    const { pendingPrompt } = get();
    if (pendingPrompt !== null) {
      set({ pendingPrompt: null });
    }
    return pendingPrompt;
  },
}));
