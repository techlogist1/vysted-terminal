/**
 * Per-message chat annotations the history store does not carry (R10):
 *   - the STRUCTURED part of an error frame (D43 — `action`/`detail`/`code`
 *     behind the transcript's "Details" disclosure; the plain `message` rides
 *     `ChatMessage.error` as before, so legacy errors render unchanged);
 *   - the runtime's notices (`step_kind: "notice"` — publish divergence,
 *     staged actions, truncation, compaction), rendered as quiet system chips
 *     under the message.
 *
 * Lives beside the chat surface (not in the shared history store) because it
 * is presentation truth for THIS surface only — keyed by message id, session
 * scoped, never persisted.
 */

import { create } from "zustand";

/** The structured fields of one error frame (the message string rides the
 *  chat-history message itself). */
export interface MessageErrorFrame {
  action?: string;
  detail?: string;
  code?: string;
}

interface MessageNoticesState {
  errorFrames: Record<string, MessageErrorFrame>;
  notices: Record<string, string[]>;
  /** Per message: the runtime's history-compaction notice (R15-AGENT-040),
   *  rendered as an "older turns summarised" marker in the transcript. */
  compactions: Record<string, string>;
  setErrorFrame: (messageId: string, frame: MessageErrorFrame) => void;
  addNotice: (messageId: string, notice: string) => void;
  setCompaction: (messageId: string, detail: string) => void;
  clear: () => void;
}

/** The notice `tool` the runtime tags a history compaction with. */
export const HISTORY_NOTICE_TOOL = "history";

export const useMessageNoticesStore = create<MessageNoticesState>((set) => ({
  errorFrames: {},
  notices: {},
  compactions: {},

  setErrorFrame: (messageId, frame) =>
    set((state) => ({ errorFrames: { ...state.errorFrames, [messageId]: frame } })),

  addNotice: (messageId, notice) =>
    set((state) => ({
      notices: {
        ...state.notices,
        [messageId]: [...(state.notices[messageId] ?? []), notice],
      },
    })),

  setCompaction: (messageId, detail) =>
    set((state) => ({ compactions: { ...state.compactions, [messageId]: detail } })),

  clear: () => set({ errorFrames: {}, notices: {}, compactions: {} }),
}));

/**
 * A runtime notice (C9): the sidecar marks every notice it emits — publish
 * divergence, staged actions, truncation, history compaction — with the
 * `notice` step kind, so the chat renders it as a transcript chip by KIND.
 * Matching the copy drifted twice (R15-AGENT-031 / R15-UI-054).
 */
export function isRuntimeNotice(stepKind: string): boolean {
  return stepKind === "notice";
}

/** Test helper: reset the per-message annotations. */
export function resetMessageNoticesForTests(): void {
  useMessageNoticesStore.setState({ errorFrames: {}, notices: {}, compactions: {} });
}
