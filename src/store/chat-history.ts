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

/**
 * One live research-pipeline step (Track A) — the camelCase view of a sidecar
 * ``research_step`` SSE event. Streamed WHILE a long research tool runs so the
 * transcript can animate a "working" trace (plan → search → synthesize) instead
 * of sitting silent for the whole multi-second round. UI-only, never persisted.
 */
export interface ResearchStepView {
  /** plan | tool | search | compress | reflect | synthesize. */
  stepKind: string;
  /** A short human line describing what the step did. */
  detail: string;
  /** Wall-clock latency of the stage in ms, when measured. */
  latencyMs?: number;
  /** "ok" | "error" | "skipped". */
  status: string;
  /** Monotonic 1-based step counter within the run. */
  index: number;
}

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
  /** Human-readable tool-use steps the copilot took (e.g. "Reading your
   *  portfolio…", "Pulling AAPL fundamentals…", "Opening chart"). UI-only. */
  toolSteps?: string[];
  /** Live research-pipeline steps streamed during a research tool round (Track
   *  A). The agent surface renders these as an animated "working" trace. */
  researchSteps?: ResearchStepView[];
  /** Epoch ms the first research step arrived — drives the live elapsed timer. */
  researchStartedAt?: number;
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
  appendToolStep: (id: string, step: string) => void;
  appendResearchStep: (id: string, step: ResearchStepView) => void;
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
  appendToolStep: (id, step) =>
    set((state) => ({
      messages: state.messages.map((message) =>
        message.id === id
          ? { ...message, toolSteps: [...(message.toolSteps ?? []), step] }
          : message,
      ),
    })),
  appendResearchStep: (id, step) =>
    set((state) => ({
      messages: state.messages.map((message) =>
        message.id === id
          ? {
              ...message,
              researchSteps: [...(message.researchSteps ?? []), step],
              researchStartedAt: message.researchStartedAt ?? Date.now(),
            }
          : message,
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
