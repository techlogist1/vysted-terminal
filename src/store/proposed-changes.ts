/**
 * Proposed-changes store — the diff/accept trust gate (FR-010, US4).
 *
 * Agent-proposed host-action mutations are staged here as `ProposedChange`s
 * instead of being applied immediately. The user reviews each as an old→new
 * diff and accepts/rejects per-item or in bulk (keyboard-driven, in the agent
 * surface). NOTHING lands before acceptance — accepting applies the mutation;
 * rejecting leaves state unchanged. The only auto-apply path is the user's own
 * AUTO autonomy choice, and only for the kinds `autoApplies` allows (panel,
 * chart, watchlist — spec SC-025); data writes and settings still wait.
 */

import { create } from "zustand";

import {
  ackHostAction,
  applyIntentAsync,
  describeIntent,
  hostActionAckDetail,
  parseHostAction,
  publishAckStatus,
  undoPreImage,
} from "@/lib/host-actions";
import { useAgentAutonomyStore } from "@/store/agent-autonomy";
import { useBriefStore } from "@/store/brief";

import { autoApplies, type ProposedChange } from "../../types/proposed-change";

let _seq = 0;
function nextId(): string {
  _seq += 1;
  return `change-${_seq}`;
}

/**
 * A REJECTED publish_brief settles the brief lifecycle (R10 D39): the run in
 * flight will never publish, so the panel restores the prior brief as
 * archived(run_failed) instead of spinning until the watchdog. No-op when no
 * run is in flight (the rejection simply leaves the published brief standing).
 */
function settleRejectedPublishes(rejected: readonly ProposedChange[]): void {
  if (!rejected.some((c) => c.action.name === "publish_brief")) {
    return;
  }
  const brief = useBriefStore.getState();
  if (brief.panel.phase === "in_flight") {
    brief.failRun();
  }
}

/**
 * Ack every REJECTED host action as `failed` (R13 JARVIS 1a): the user
 * declined it, so the sidecar's action ledger reflects the change did NOT land
 * and any read-back reads the honest outcome. Fire-and-forget.
 */
function ackRejectedHostActions(rejected: readonly ProposedChange[]): void {
  for (const c of rejected) {
    ackHostAction(c.toolCallId, "failed", hostActionAckDetail(c.action.name, c.action.input));
  }
}

export interface EnqueueInput {
  toolCallId: string;
  name: string;
  input: Record<string, unknown>;
  /** Groups every change from one agent turn for bulk accept/reject. */
  batchId: string;
  agentId?: string;
  agentName?: string;
}

interface ProposedChangesState {
  changes: ProposedChange[];
  /** Stage a host-action mutation as a reviewable diff. Returns its id. */
  enqueue: (input: EnqueueInput) => string;
  /** Accept one change — apply it. */
  accept: (id: string) => Promise<void>;
  /** Reject one change — leaves cockpit state unchanged. */
  reject: (id: string) => void;
  /** Accept every still-pending change in a batch, in proposal order. */
  acceptBatch: (batchId: string) => Promise<void>;
  rejectBatch: (batchId: string) => void;
  acceptAll: () => Promise<void>;
  rejectAll: () => void;
  /** Restore an applied data write's pre-image (session Undo). Acks nothing:
   *  the runtime already holds the applied outcome of that tool call. */
  undo: (id: string) => void;
  clear: () => void;
  pending: () => ProposedChange[];
  pendingInBatch: (batchId: string) => ProposedChange[];
}

export const useProposedChangesStore = create<ProposedChangesState>((set, get) => ({
  changes: [],

  enqueue: ({ toolCallId, name, input, batchId, agentId, agentName }) => {
    const id = nextId();
    const intent = parseHostAction(name, input);
    const described = describeIntent(intent);
    const change: ProposedChange = {
      id,
      toolCallId,
      action: { name, input },
      intent,
      kind: described.kind,
      title: described.title,
      before: described.before,
      after: described.after,
      status: "pending",
      batchId,
      agentId,
      agentName,
      createdAt: Date.now(),
    };
    set((state) => ({ changes: [...state.changes, change] }));
    // Autonomy: in AUTO mode an auto-applicable kind applies without a
    // per-action confirmation (still recorded in the transcript). Any other
    // kind stays pending, and the ledger learns it is awaiting review, not failed.
    if (useAgentAutonomyStore.getState().autonomy === "auto") {
      if (autoApplies(change.kind)) {
        void get().accept(id);
      } else {
        ackHostAction(toolCallId, "staged", hostActionAckDetail(name, input));
      }
    }
    return id;
  },

  accept: async (id) => {
    const change = get().changes.find((c) => c.id === id);
    if (!change || change.status !== "pending") {
      return;
    }
    // Claim the change SYNCHRONOUSLY before any await so a concurrent accept(id)
    // (or acceptAll racing a manual click) sees status !== "pending" and bails —
    // no double-apply.
    set((state) => ({
      changes: state.changes.map((c) =>
        c.id === id ? { ...c, status: "accepted", detail: undefined } : c,
      ),
    }));
    const { label, reason, preImage } = await applyIntentAsync(change.intent);
    const ok = label !== null;
    const detail = ok
      ? undefined
      : reason || "Could not apply this change — its arguments were incomplete.";
    // Read-back (R10 D39 §4, generalized in R13 JARVIS 1a): the sidecar's
    // action ledger learns how the panel REALLY resolved EVERY host action
    // (applied | kept_previous | failed) so the runtime's grounded
    // tool-result + divergence check compare against ground truth, not the
    // optimistic "dispatched". Fire-and-forget — never blocks the gate.
    ackHostAction(
      change.toolCallId,
      publishAckStatus(label),
      hostActionAckDetail(change.action.name, change.action.input),
    );
    if (!ok) {
      // Re-pend so the user sees the failure and can retry; the change did NOT land.
      set((state) => ({
        changes: state.changes.map((c) => (c.id === id ? { ...c, status: "pending", detail } : c)),
      }));
    } else if (preImage) {
      set((state) => ({
        changes: state.changes.map((c) => (c.id === id ? { ...c, preImage } : c)),
      }));
    }
  },

  reject: (id) => {
    const target = get().changes.find((c) => c.id === id && c.status === "pending");
    set((state) => ({
      changes: state.changes.map((c) =>
        c.id === id && c.status === "pending" ? { ...c, status: "rejected" } : c,
      ),
    }));
    if (target) {
      settleRejectedPublishes([target]);
      ackRejectedHostActions([target]);
    }
  },

  acceptBatch: async (batchId) => {
    // Sequential so changes apply in proposal order (open a panel before
    // setting its symbol). `accept` re-reads state, so a removed/resolved
    // change is a safe no-op.
    const ids = get()
      .changes.filter((c) => c.batchId === batchId && c.status === "pending")
      .map((c) => c.id);
    for (const id of ids) {
      await get().accept(id);
    }
  },

  rejectBatch: (batchId) => {
    const targets = get().changes.filter((c) => c.batchId === batchId && c.status === "pending");
    set((state) => ({
      changes: state.changes.map((c) =>
        c.batchId === batchId && c.status === "pending" ? { ...c, status: "rejected" } : c,
      ),
    }));
    settleRejectedPublishes(targets);
    ackRejectedHostActions(targets);
  },

  acceptAll: async () => {
    const ids = get()
      .changes.filter((c) => c.status === "pending")
      .map((c) => c.id);
    for (const id of ids) {
      await get().accept(id);
    }
  },

  rejectAll: () => {
    const targets = get().changes.filter((c) => c.status === "pending");
    set((state) => ({
      changes: state.changes.map((c) =>
        c.status === "pending" ? { ...c, status: "rejected" } : c,
      ),
    }));
    settleRejectedPublishes(targets);
    ackRejectedHostActions(targets);
  },

  undo: (id) => {
    const change = get().changes.find((c) => c.id === id);
    if (!change || change.status !== "accepted" || !change.preImage) {
      return;
    }
    const { label, reason } = undoPreImage(change.preImage);
    set((state) => ({
      changes: state.changes.map((c) =>
        c.id !== id
          ? c
          : label !== null
            ? { ...c, status: "undone", detail: undefined }
            : { ...c, detail: reason || "Could not undo this change." },
      ),
    }));
  },

  clear: () => set({ changes: [] }),

  pending: () => get().changes.filter((c) => c.status === "pending"),
  pendingInBatch: (batchId) =>
    get().changes.filter((c) => c.batchId === batchId && c.status === "pending"),
}));

/** Test helper: reset the proposed-changes store. */
export function resetProposedChangesStoreForTests(): void {
  useProposedChangesStore.setState({ changes: [] });
  _seq = 0;
}
