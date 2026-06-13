/**
 * Proposed-changes store — the diff/accept trust gate (FR-010, US4).
 *
 * Agent-proposed host-action mutations are staged here as `ProposedChange`s
 * instead of being applied immediately. The user reviews each as an old→new
 * diff and accepts/rejects per-item or in bulk (keyboard-driven, in the agent
 * surface). NOTHING lands before acceptance — accepting applies the mutation
 * (or, for an order, routes it to the §6.5 confirm dialog); rejecting leaves
 * state unchanged. There is no auto-apply path (Constitution / spec US4).
 */

import { create } from "zustand";

import {
  ackPublishBrief,
  applyHostActionAsync,
  describeHostAction,
  publishAckStatus,
  routeOrderProposal,
} from "@/lib/host-actions";
import { useAgentAutonomyStore } from "@/store/agent-autonomy";
import { useBriefStore } from "@/store/brief";

import type { ProposedChange } from "../../types/proposed-change";

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
  /** Accept one change — apply it (or route an order to the §6.5 dialog). */
  accept: (id: string) => Promise<void>;
  /** Reject one change — leaves cockpit state unchanged. */
  reject: (id: string) => void;
  /** Accept every still-pending change in a batch, in proposal order. */
  acceptBatch: (batchId: string) => Promise<void>;
  rejectBatch: (batchId: string) => void;
  acceptAll: () => Promise<void>;
  rejectAll: () => void;
  clear: () => void;
  pending: () => ProposedChange[];
  pendingInBatch: (batchId: string) => ProposedChange[];
}

export const useProposedChangesStore = create<ProposedChangesState>((set, get) => ({
  changes: [],

  enqueue: ({ toolCallId, name, input, batchId, agentId, agentName }) => {
    const id = nextId();
    const described = describeHostAction(name, input);
    const change: ProposedChange = {
      id,
      toolCallId,
      action: { name, input },
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
    // Autonomy: in AUTO mode, the UI/layout/chart/watchlist host-actions apply
    // without a per-action confirmation (still recorded in the transcript).
    // HARD SAFETY LINE — an ORDER is NEVER auto-applied in any mode: it is
    // excluded here AND `accept()` would route it through the §6.5 confirm dialog
    // anyway. `auto` changes confirmation friction, never the safety enforcement.
    if (described.kind !== "order" && useAgentAutonomyStore.getState().autonomy === "auto") {
      void get().accept(id);
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
    // no double-apply, no double-route of an order.
    set((state) => ({
      changes: state.changes.map((c) =>
        c.id === id ? { ...c, status: "accepted", detail: undefined } : c,
      ),
    }));
    let ok = true;
    let detail: string | undefined;
    if (change.kind === "order") {
      // The §6.5 dialog (mandatory review checkbox + Confirm) now governs
      // placement; the AI never reaches confirm_and_place.
      const result = await routeOrderProposal(change.action.input, {
        agentId: change.agentId,
        agentName: change.agentName,
      });
      ok = result.ok;
      detail = result.error;
    } else {
      const label = await applyHostActionAsync(change.action.name, change.action.input);
      ok = label !== null;
      if (!ok) {
        detail = "Could not apply this change — its arguments were incomplete.";
      }
      // Publish read-back (R10 D39 §4): the sidecar's action ledger learns how
      // the panel REALLY resolved this publish (applied | kept_previous |
      // failed) so the runtime's end-of-stream divergence check has truth to
      // compare against. Fire-and-forget — never blocks the gate.
      if (change.action.name === "publish_brief") {
        ackPublishBrief(change.toolCallId, publishAckStatus(label));
      }
    }
    if (!ok) {
      // Re-pend so the user sees the failure and can retry; the change did NOT land.
      set((state) => ({
        changes: state.changes.map((c) => (c.id === id ? { ...c, status: "pending", detail } : c)),
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
