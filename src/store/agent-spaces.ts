import { create } from "zustand";

import { type ChatMessage, useChatHistoryStore } from "./chat-history";

/**
 * Agent spaces (multiple chat threads/pages) — Perplexity/Cursor-style. Each
 * space is an independent transcript; switching archives the live transcript and
 * restores the target's. The chat-history store stays single-active (the live
 * thread); this store owns the off-screen threads + the swap. Session-scoped for
 * now — persisting spaces into the workspace blob is a follow-up (task #11).
 */
export interface AgentSpace {
  id: string;
  title: string;
}

interface AgentSpacesState {
  spaces: AgentSpace[];
  activeId: string;
  /** Transcripts for the NON-active spaces (the active one lives in chat-history). */
  archived: Record<string, ChatMessage[]>;
  newSpace: () => void;
  switchTo: (id: string) => void;
  closeSpace: (id: string) => void;
  /** Rename the active space (e.g. auto-titled from the first prompt). */
  renameActive: (title: string) => void;
}

function uid(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2, 11)}`;
}

const FIRST_ID = uid();

export const useAgentSpacesStore = create<AgentSpacesState>((set, get) => ({
  spaces: [{ id: FIRST_ID, title: "Chat 1" }],
  activeId: FIRST_ID,
  archived: {},

  newSpace: () => {
    const { activeId, spaces, archived } = get();
    const liveMessages = useChatHistoryStore.getState().messages;
    const id = uid();
    set({
      spaces: [...spaces, { id, title: `Chat ${spaces.length + 1}` }],
      activeId: id,
      archived: { ...archived, [activeId]: liveMessages },
    });
    useChatHistoryStore.getState().clear();
  },

  switchTo: (id) => {
    const { activeId, archived } = get();
    if (id === activeId) {
      return;
    }
    const liveMessages = useChatHistoryStore.getState().messages;
    const target = archived[id] ?? [];
    set({ activeId: id, archived: { ...archived, [activeId]: liveMessages } });
    useChatHistoryStore.getState().loadMessages(target);
  },

  closeSpace: (id) => {
    const { spaces, activeId, archived } = get();
    if (spaces.length <= 1) {
      return; // never close the last space
    }
    const remaining = spaces.filter((s) => s.id !== id);
    const nextArchived = { ...archived };
    delete nextArchived[id];
    let nextActive = activeId;
    if (id === activeId) {
      nextActive = remaining[remaining.length - 1].id;
      useChatHistoryStore.getState().loadMessages(nextArchived[nextActive] ?? []);
      delete nextArchived[nextActive]; // it's now the live thread, not archived
    }
    set({ spaces: remaining, activeId: nextActive, archived: nextArchived });
  },

  renameActive: (title) =>
    set((state) => ({
      spaces: state.spaces.map((s) => (s.id === state.activeId ? { ...s, title } : s)),
    })),
}));
