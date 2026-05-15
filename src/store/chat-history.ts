/**
 * Chat history store — current conversation state, streaming buffer.
 *
 * In-memory only. The sidecar-owned SQLite persistence layer (Phase 4) is
 * the long-term home for chat history; Phase 3 keeps it scoped to the
 * session because the chat sidebar is meant to be an ambient assistant
 * rather than a long-running thread. No ``localStorage`` per the CLAUDE.md
 * constraint.
 *
 * A message ``id`` is a UUID-ish string generated at create time; the
 * streaming reducer appends delta text into ``content`` on a single
 * "in-flight" assistant message identified by ``streamingMessageId``.
 */

import { create } from "zustand";

import type { LLMProviderId, LLMUsage } from "../../types/ai";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  /** Optional metadata surfaced in the UI (agent that produced it, model). */
  agentId?: string | null;
  providerId?: LLMProviderId | null;
  modelId?: string | null;
  /** Token usage if the provider supplied it. */
  usage?: LLMUsage | null;
  /** ``true`` while the message is still being streamed. */
  pending?: boolean;
  /** Error string if streaming failed. */
  error?: string | null;
  createdAt: number;
}

interface ChatHistoryState {
  messages: ChatMessage[];
  /** Id of the assistant message currently receiving deltas, or ``null``. */
  streamingMessageId: string | null;
  appendUserMessage: (content: string) => string;
  beginAssistantMessage: (params: {
    agentId?: string;
    providerId?: LLMProviderId;
    modelId?: string;
  }) => string;
  appendAssistantDelta: (id: string, text: string) => void;
  finalizeAssistantMessage: (id: string, usage?: LLMUsage | null) => void;
  failAssistantMessage: (id: string, error: string) => void;
  clear: () => void;
}

function _uuid(): string {
  // Math.random-backed fallback for environments where ``crypto.randomUUID``
  // is unavailable (Node test runner). Collision risk is negligible at the
  // per-session scope this is used for.
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2, 11)}`;
}

export const useChatHistoryStore = create<ChatHistoryState>((set) => ({
  messages: [],
  streamingMessageId: null,
  appendUserMessage: (content) => {
    const id = _uuid();
    set((state) => ({
      messages: [...state.messages, { id, role: "user", content, createdAt: Date.now() }],
    }));
    return id;
  },
  beginAssistantMessage: ({ agentId, providerId, modelId }) => {
    const id = _uuid();
    set((state) => ({
      messages: [
        ...state.messages,
        {
          id,
          role: "assistant",
          content: "",
          agentId: agentId ?? null,
          providerId: providerId ?? null,
          modelId: modelId ?? null,
          pending: true,
          createdAt: Date.now(),
        },
      ],
      streamingMessageId: id,
    }));
    return id;
  },
  appendAssistantDelta: (id, text) =>
    set((state) => ({
      messages: state.messages.map((message) =>
        message.id === id ? { ...message, content: message.content + text } : message,
      ),
    })),
  finalizeAssistantMessage: (id, usage) =>
    set((state) => ({
      messages: state.messages.map((message) =>
        message.id === id ? { ...message, pending: false, usage: usage ?? null } : message,
      ),
      streamingMessageId: state.streamingMessageId === id ? null : state.streamingMessageId,
    })),
  failAssistantMessage: (id, error) =>
    set((state) => ({
      messages: state.messages.map((message) =>
        message.id === id ? { ...message, pending: false, error } : message,
      ),
      streamingMessageId: state.streamingMessageId === id ? null : state.streamingMessageId,
    })),
  clear: () => set({ messages: [], streamingMessageId: null }),
}));
