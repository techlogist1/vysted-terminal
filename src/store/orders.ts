/**
 * Orders store — pending order proposals inbox.
 *
 * BLUEPRINT §6.5 #2 ("every order is confirmed") + #6 ("AI-order gate") in
 * one place. Every order — manual OR AI-initiated — flows through the same
 * propose → confirm/decline → place path. The proposal lands here as a
 * pending item; the `OrderConfirmationDialog` reads it; on Confirm the UI
 * POSTs `/brokers/{id}/orders/{proposal_id}/confirm` (per Teammate I's
 * router shape); on decline the UI posts the same with `human_confirmed=false`.
 *
 * v0.5.0 tightening (Tier-3, per plan): NO auto-approve mode. AI-initiated
 * proposals open the dialog with Confirm disabled by default — the user
 * MUST click the "I reviewed this AI-proposed order" checkbox to enable
 * Confirm. The store does not enforce this directly; the dialog component
 * does, but the source field is the structural signal.
 */

import { create } from "zustand";

import { getSidecarBaseUrl } from "@/lib/sidecar-client";

import type { BrokerId, BrokerOrderProposal, BrokerOrderResult } from "../../types/broker";

/** Lifecycle state of a proposal in the inbox. */
export type ProposalStatus = "pending" | "confirming" | "placed" | "declined" | "rejected";

/** A proposal in the inbox, plus the UI-side lifecycle metadata. */
export interface PendingProposal {
  proposal: BrokerOrderProposal;
  status: ProposalStatus;
  /** Error text if status is `"rejected"`. */
  error: string | null;
  /** Broker-side result once placed. */
  result: BrokerOrderResult | null;
}

interface OrdersState {
  /** Pending + recently-resolved proposals, newest first. */
  proposals: PendingProposal[];
  /** Currently-open proposal (the dialog reads this), or `null` if none. */
  activeProposalId: string | null;

  addProposal: (proposal: BrokerOrderProposal) => void;
  openProposal: (proposalId: string) => void;
  closeProposal: () => void;
  confirmProposal: (proposalId: string) => Promise<BrokerOrderResult>;
  declineProposal: (proposalId: string, note?: string) => Promise<void>;
  removeProposal: (proposalId: string) => void;

  pendingProposals: () => PendingProposal[];
  aiPendingProposals: () => PendingProposal[];
  manualPendingProposals: () => PendingProposal[];
  findProposal: (proposalId: string) => PendingProposal | undefined;
}

export const useOrdersStore = create<OrdersState>((set, get) => ({
  proposals: [],
  activeProposalId: null,

  addProposal: (proposal) => {
    set((state) => {
      const exists = state.proposals.some((p) => p.proposal.proposalId === proposal.proposalId);
      if (exists) {
        return state;
      }
      const pending: PendingProposal = {
        proposal,
        status: "pending",
        error: null,
        result: null,
      };
      return { proposals: [pending, ...state.proposals] };
    });
  },

  openProposal: (proposalId) => set({ activeProposalId: proposalId }),

  closeProposal: () => set({ activeProposalId: null }),

  confirmProposal: async (proposalId) => {
    const proposal = get().findProposal(proposalId);
    if (proposal === undefined) {
      throw new Error(`proposal ${proposalId} not found`);
    }
    set((state) => ({
      proposals: state.proposals.map((p) =>
        p.proposal.proposalId === proposalId ? { ...p, status: "confirming" } : p,
      ),
    }));
    try {
      const result = await confirmAtBroker(proposal.proposal.broker, proposalId, true);
      set((state) => ({
        proposals: state.proposals.map((p) =>
          p.proposal.proposalId === proposalId
            ? { ...p, status: "placed", result, error: null }
            : p,
        ),
        activeProposalId: state.activeProposalId === proposalId ? null : state.activeProposalId,
      }));
      return result;
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "place failed";
      set((state) => ({
        proposals: state.proposals.map((p) =>
          p.proposal.proposalId === proposalId ? { ...p, status: "rejected", error: message } : p,
        ),
      }));
      throw err;
    }
  },

  declineProposal: async (proposalId, note) => {
    const proposal = get().findProposal(proposalId);
    if (proposal === undefined) {
      throw new Error(`proposal ${proposalId} not found`);
    }
    try {
      await confirmAtBroker(proposal.proposal.broker, proposalId, false, note);
    } catch {
      // The decline is logical: best-effort to inform the sidecar, but if
      // the call fails the user's intent is still recorded locally.
    }
    set((state) => ({
      proposals: state.proposals.map((p) =>
        p.proposal.proposalId === proposalId ? { ...p, status: "declined" } : p,
      ),
      activeProposalId: state.activeProposalId === proposalId ? null : state.activeProposalId,
    }));
  },

  removeProposal: (proposalId) => {
    set((state) => ({
      proposals: state.proposals.filter((p) => p.proposal.proposalId !== proposalId),
      activeProposalId: state.activeProposalId === proposalId ? null : state.activeProposalId,
    }));
  },

  pendingProposals: () => get().proposals.filter((p) => p.status === "pending"),

  aiPendingProposals: () =>
    get().proposals.filter(
      (p) =>
        p.status === "pending" &&
        (p.proposal.source === "ai-agent" || p.proposal.source === "workflow"),
    ),

  manualPendingProposals: () =>
    get().proposals.filter((p) => p.status === "pending" && p.proposal.source === "manual"),

  findProposal: (proposalId) => get().proposals.find((p) => p.proposal.proposalId === proposalId),
}));

// ---------------------------------------------------------------------------
// Broker-side call — Teammate I's router shape is:
//   POST /brokers/{broker_id}/orders/{proposal_id}/confirm
// with body { human_confirmed: bool, confirm_note?: string }.
// Decline = same route with human_confirmed=false.
// ---------------------------------------------------------------------------

async function confirmAtBroker(
  broker: BrokerId,
  proposalId: string,
  humanConfirmed: boolean,
  note?: string,
): Promise<BrokerOrderResult> {
  const base = await getSidecarBaseUrl();
  const response = await fetch(
    new URL(
      `/brokers/${encodeURIComponent(broker)}/orders/${encodeURIComponent(proposalId)}/confirm`,
      base,
    ).toString(),
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ humanConfirmed, confirmNote: note }),
    },
  );
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail !== undefined) {
        detail = body.detail;
      }
    } catch {
      // ignore non-JSON body
    }
    throw new Error(detail);
  }
  return (await response.json()) as BrokerOrderResult;
}

/** Test helper: reset the orders store. */
export function resetOrdersStoreForTests(): void {
  useOrdersStore.setState({ proposals: [], activeProposalId: null });
}
