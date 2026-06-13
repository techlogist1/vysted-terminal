/**
 * Per-message chat annotations the history store does not carry (R10):
 *   - the STRUCTURED part of an error frame (D43 — `action`/`detail`/`code`
 *     behind the transcript's "Details" disclosure; the plain `message` rides
 *     `ChatMessage.error` as before, so legacy errors render unchanged);
 *   - end-of-stream DIVERGENCE notices from the runtime's publish ledger
 *     check (D39 — "the panel kept the previous, richer brief"), rendered as
 *     quiet system chips under the message.
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
  setErrorFrame: (messageId: string, frame: MessageErrorFrame) => void;
  addNotice: (messageId: string, notice: string) => void;
  clear: () => void;
}

export const useMessageNoticesStore = create<MessageNoticesState>((set) => ({
  errorFrames: {},
  notices: {},

  setErrorFrame: (messageId, frame) =>
    set((state) => ({ errorFrames: { ...state.errorFrames, [messageId]: frame } })),

  addNotice: (messageId, notice) =>
    set((state) => ({
      notices: {
        ...state.notices,
        [messageId]: [...(state.notices[messageId] ?? []), notice],
      },
    })),

  clear: () => set({ errorFrames: {}, notices: {} }),
}));

/**
 * The runtime reuses the engine-step channel for its end-of-stream publish
 * divergence notices (Team RUNTIME §3) — these two stated lines are the
 * contract copy. Matched verbatim-insensitively so a divergence renders as a
 * quiet transcript chip instead of a telemetry row in the step trace.
 */
const DIVERGENCE_RE = /did not confirm the publish|kept the previous, richer brief/i;

export function isDivergenceNotice(stepKind: string, detail: string): boolean {
  return stepKind === "engine" && DIVERGENCE_RE.test(detail);
}

/** Test helper: reset the per-message annotations. */
export function resetMessageNoticesForTests(): void {
  useMessageNoticesStore.setState({ errorFrames: {}, notices: {} });
}
