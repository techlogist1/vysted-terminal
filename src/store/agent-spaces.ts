import { create } from "zustand";

import { type ChatMessage, useChatHistoryStore } from "./chat-history";

/**
 * Agent spaces (multiple chat threads/pages) — Perplexity/Cursor-style. Each
 * space is an independent transcript; switching archives the live transcript and
 * restores the target's. The chat-history store stays single-active (the live
 * thread); this store owns the off-screen threads + the swap. The tabs and the
 * off-screen transcripts ride the workspace blob ({@link AgentSpacesBundle});
 * the live thread stays session-scoped like the chat history itself.
 */
export interface AgentSpace {
  id: string;
  title: string;
}

/** The agent spaces as persisted in the workspace blob. */
export interface AgentSpacesBundle {
  spaces: AgentSpace[];
  activeId: string;
  archived: Record<string, ChatMessage[]>;
}

/** A settled message from a blob: the fields the transcript renders, never pending. */
function isArchivedMessage(value: unknown): value is ChatMessage {
  const m = value as Partial<ChatMessage> | null;
  return (
    !!m &&
    typeof m.id === "string" &&
    (m.role === "user" || m.role === "assistant" || m.role === "system") &&
    typeof m.content === "string" &&
    typeof m.createdAt === "number" &&
    !m.pending
  );
}

interface AgentSpacesState {
  spaces: AgentSpace[];
  activeId: string;
  /** Transcripts for the NON-active spaces (the active one lives in chat-history),
   *  plus the ACTIVE space's own while a research space holds the live chat. */
  archived: Record<string, ChatMessage[]>;
  newSpace: () => void;
  switchTo: (id: string) => void;
  closeSpace: (id: string) => void;
  /** Entering a research space: park the active space's live transcript. */
  parkActive: () => void;
  /** Leaving a research space: bring the parked transcript back live (empty if none). */
  unparkActive: () => void;
  /** Append a finished message to a space's transcript, live or archived (a
   *  Delegate run's answer, R15-AGENT-013). An unknown or closed space's message
   *  lands in the live transcript, never dropped. */
  deliverTo: (spaceId: string | undefined, message: ChatMessage) => void;
  /** Rename the active space (e.g. auto-titled from the first prompt). */
  renameActive: (title: string) => void;
  /** Snapshot the tabs + off-screen transcripts for the workspace blob. */
  toBundle: () => AgentSpacesBundle;
  /** Restore a blob's bundle (launch only); a garbled one keeps the live tabs.
   *  A transcript the active tab had parked (a research space held the live
   *  chat) comes back live — re-entering the space parks it again. */
  fromBundle: (bundle: unknown) => void;
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
    useChatHistoryStore.getState().stopLive();
    const { activeId, spaces, archived } = get();
    // A parked transcript (a research space holds the live chat) is this space's.
    const liveMessages = archived[activeId] ?? useChatHistoryStore.getState().messages;
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
    useChatHistoryStore.getState().stopLive();
    const liveMessages = archived[activeId] ?? useChatHistoryStore.getState().messages;
    const { [id]: target = [], ...rest } = archived;
    set({ activeId: id, archived: { ...rest, [activeId]: liveMessages } });
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

  parkActive: () =>
    set((state) => ({
      archived: { ...state.archived, [state.activeId]: useChatHistoryStore.getState().messages },
    })),

  unparkActive: () => {
    const { activeId, archived } = get();
    const { [activeId]: parked = [], ...rest } = archived;
    set({ archived: rest });
    useChatHistoryStore.getState().loadMessages(parked);
  },

  deliverTo: (spaceId, message) => {
    const { archived } = get();
    if (spaceId !== undefined && spaceId in archived) {
      set({ archived: { ...archived, [spaceId]: [...archived[spaceId], message] } });
    } else {
      useChatHistoryStore.setState((state) => ({ messages: [...state.messages, message] }));
    }
  },

  renameActive: (title) =>
    set((state) => ({
      spaces: state.spaces.map((s) => (s.id === state.activeId ? { ...s, title } : s)),
    })),

  toBundle: () => {
    const { spaces, activeId, archived } = get();
    return { spaces, activeId, archived };
  },

  fromBundle: (bundle) => {
    const b = (bundle ?? {}) as Partial<AgentSpacesBundle>;
    const spaces = Array.isArray(b.spaces)
      ? b.spaces.filter(
          (s): s is AgentSpace => typeof s?.id === "string" && typeof s?.title === "string",
        )
      : [];
    if (spaces.length === 0) {
      return;
    }
    const activeId = spaces.some((s) => s.id === b.activeId) ? b.activeId! : spaces[0].id;
    const archived: Record<string, ChatMessage[]> = {};
    for (const space of spaces) {
      const list: unknown = b.archived?.[space.id];
      if (Array.isArray(list)) {
        archived[space.id] = list.filter(isArchivedMessage);
      }
    }
    const { [activeId]: parked, ...rest } = archived;
    set({ spaces, activeId, archived: rest });
    if (parked) {
      useChatHistoryStore.getState().loadMessages(parked);
    }
  },
}));
