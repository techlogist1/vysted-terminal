"use client";

/**
 * OrderConfirmationDialog — BLUEPRINT §6.5 #2 + #6 UI surface.
 *
 * One dialog handles BOTH variants:
 *
 *   - **Manual** (`proposal.source === "manual"`) — Confirm enabled by
 *     default; user reviews, clicks Confirm.
 *   - **AI-initiated** (`proposal.source === "ai-agent" | "workflow"`) —
 *     Confirm DISABLED by default + top banner naming the agent. User MUST
 *     check "I reviewed this AI-proposed order" before Confirm enables.
 *
 * v0.5.0 Tier-3 tightening: NO auto-approve mode. The checkbox is the only
 * path from AI proposal to confirmed placement.
 *
 * The first-live-order disclaimer is fired by this dialog: when the user is
 * about to confirm AND the broker is in live mode AND the session ack is
 * missing, the dialog intercepts with the per-session live-order ack prompt.
 */

import { useCallback, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useOrdersStore, type PendingProposal } from "@/store/orders";
import { useBrokersStore } from "@/store/brokers";
import { useSafetyStore } from "@/store/safety";

import type { BrokerOrderProposal } from "../../../types/broker";

function describeSource(proposal: BrokerOrderProposal): {
  variant: "manual" | "ai";
  banner: string | null;
} {
  if (proposal.source === "manual") {
    return { variant: "manual", banner: null };
  }
  const details = proposal.sourceDetails ?? {};
  const agentName =
    (details["agentName"] as string | undefined) ??
    (details["originatorName"] as string | undefined) ??
    (details["workflowId"] as string | undefined) ??
    "AI agent";
  if (proposal.source === "workflow") {
    return {
      variant: "ai",
      banner: `Workflow '${agentName}' is requesting this order.`,
    };
  }
  return {
    variant: "ai",
    banner: `AI agent '${agentName}' is requesting this order.`,
  };
}

export function OrderConfirmationDialog() {
  const activeProposalId = useOrdersStore((s) => s.activeProposalId);
  const findProposal = useOrdersStore((s) => s.findProposal);
  const closeProposal = useOrdersStore((s) => s.closeProposal);
  const confirmProposal = useOrdersStore((s) => s.confirmProposal);
  const declineProposal = useOrdersStore((s) => s.declineProposal);

  const ackFirstLiveOrder = useSafetyStore((s) => s.ackFirstLiveOrderThisSession);
  const hasSessionAck = useSafetyStore((s) => s.hasSessionAck);

  const brokersById = useBrokersStore((s) => s.byId);

  const pending = activeProposalId !== null ? findProposal(activeProposalId) : undefined;

  if (pending === undefined) {
    return null;
  }

  return (
    <OrderConfirmationDialogContent
      pending={pending}
      onClose={closeProposal}
      onConfirm={confirmProposal}
      onDecline={declineProposal}
      brokerMode={brokersById[pending.proposal.broker]?.mode ?? "paper"}
      hasSessionAck={hasSessionAck}
      ackFirstLiveOrder={ackFirstLiveOrder}
    />
  );
}

interface ContentProps {
  pending: PendingProposal;
  brokerMode: "paper" | "live";
  onClose: () => void;
  onConfirm: (proposalId: string) => Promise<unknown>;
  onDecline: (proposalId: string, note?: string) => Promise<void>;
  hasSessionAck: (broker: BrokerOrderProposal["broker"]) => boolean;
  ackFirstLiveOrder: (broker: BrokerOrderProposal["broker"]) => Promise<unknown>;
}

function OrderConfirmationDialogContent({
  pending,
  brokerMode,
  onClose,
  onConfirm,
  onDecline,
  hasSessionAck,
  ackFirstLiveOrder,
}: ContentProps) {
  const { proposal } = pending;
  const meta = useMemo(() => describeSource(proposal), [proposal]);
  const [reviewedAi, setReviewedAi] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [liveAckPrompt, setLiveAckPrompt] = useState(false);

  const confirmEnabled = meta.variant === "manual" || reviewedAi;

  const handleConfirm = useCallback(async () => {
    if (!confirmEnabled || busy) {
      return;
    }
    if (brokerMode === "live" && !hasSessionAck(proposal.broker)) {
      setLiveAckPrompt(true);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await onConfirm(proposal.proposalId);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Confirm failed");
    } finally {
      setBusy(false);
    }
  }, [
    brokerMode,
    busy,
    confirmEnabled,
    hasSessionAck,
    onConfirm,
    proposal.broker,
    proposal.proposalId,
  ]);

  const handleLiveAck = useCallback(async () => {
    setBusy(true);
    try {
      await ackFirstLiveOrder(proposal.broker);
      setLiveAckPrompt(false);
      await onConfirm(proposal.proposalId);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Live order ack failed");
    } finally {
      setBusy(false);
    }
  }, [ackFirstLiveOrder, onConfirm, proposal.broker, proposal.proposalId]);

  const handleDecline = useCallback(async () => {
    setBusy(true);
    try {
      await onDecline(proposal.proposalId, "user-declined");
    } finally {
      setBusy(false);
    }
  }, [onDecline, proposal.proposalId]);

  return (
    <Dialog
      open
      onOpenChange={(value) => {
        if (!value) {
          onClose();
        }
      }}
    >
      <DialogContent data-testid="order-confirmation-dialog" data-variant={meta.variant}>
        <DialogHeader>
          <DialogTitle>
            {meta.variant === "ai" ? "Confirm AI-proposed order" : "Confirm order"}
          </DialogTitle>
          <DialogDescription>
            Review the order shape before sending it to {proposal.broker}.
          </DialogDescription>
        </DialogHeader>

        {meta.banner !== null && (
          <div
            data-testid="ai-agent-banner"
            className="rounded-md border border-amber-500/60 bg-amber-950/30 px-3 py-2 text-xs text-amber-200"
          >
            {meta.banner}
          </div>
        )}

        <dl className="grid grid-cols-2 gap-x-3 gap-y-1 font-mono text-xs">
          <Field label="Broker" value={proposal.broker} />
          <Field label="Account" value={proposal.accountId} />
          <Field label="Symbol" value={proposal.symbol} />
          <Field label="Side" value={proposal.side.toUpperCase()} />
          <Field label="Type" value={proposal.type} />
          <Field label="Quantity" value={String(proposal.quantity)} />
          {proposal.limitPrice !== undefined && (
            <Field label="Limit price" value={String(proposal.limitPrice)} />
          )}
          {proposal.stopPrice !== undefined && (
            <Field label="Stop price" value={String(proposal.stopPrice)} />
          )}
          <Field label="Currency" value={proposal.currency} />
          <Field label="Estimated value" value={proposal.estimatedValue.toFixed(2)} />
          <Field label="Mode" value={brokerMode} />
        </dl>

        {meta.variant === "ai" && (
          <label
            data-testid="ai-review-checkbox-label"
            className="mt-2 flex items-center gap-2 text-xs"
          >
            <input
              type="checkbox"
              aria-label="I reviewed this AI-proposed order"
              data-testid="ai-review-checkbox"
              checked={reviewedAi}
              onChange={(e) => setReviewedAi(e.target.checked)}
            />
            I reviewed this AI-proposed order
          </label>
        )}

        {liveAckPrompt && (
          <div
            data-testid="live-order-ack-prompt"
            className="mt-2 rounded-md border border-amber-500/60 bg-amber-950/30 px-3 py-2 text-xs text-amber-200"
          >
            <p className="mb-2">
              You are about to place your first <strong>live</strong> order at {proposal.broker}{" "}
              this session. Live orders execute against real money — confirm you understand the
              risk.
            </p>
            <div className="flex gap-2">
              <Button size="xs" variant="destructive" onClick={handleLiveAck} disabled={busy}>
                I understand — place live order
              </Button>
              <Button size="xs" variant="ghost" onClick={() => setLiveAckPrompt(false)}>
                Cancel
              </Button>
            </div>
          </div>
        )}

        {error !== null && <p className="text-xs text-red-400">{error}</p>}

        <DialogFooter>
          <Button variant="ghost" onClick={handleDecline} disabled={busy}>
            Decline
          </Button>
          <Button
            data-testid="confirm-button"
            variant="default"
            onClick={handleConfirm}
            disabled={!confirmEnabled || busy}
          >
            {busy ? "Sending…" : "Confirm"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <>
      <dt className="text-muted-foreground">{label}</dt>
      <dd>{value}</dd>
    </>
  );
}
