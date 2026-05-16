"use client";

/**
 * DisclaimerFlow — BLUEPRINT §6.5 #8, three layered surfaces.
 *
 *   1. **First-launch TOS** — keychain-backed
 *      (`broker:_meta:first-launch-tos`). Renders a blocking modal on the
 *      very first launch.
 *   2. **Per-broker first-connect** — keychain-backed
 *      (`broker:<id>:_meta:first-connect-ack`). The BrokerConnectPanel
 *      surfaces this dialog when the user clicks Connect on a broker that
 *      has never been acked.
 *   3. **First-live-order-per-session** — sidecar in-memory; resets on
 *      sidecar restart. Fired by the `OrderConfirmationDialog` when the
 *      user confirms a live order AND `hasSessionAck(broker) === false`.
 *
 * No `localStorage` / `sessionStorage`. Persistent acks live in the OS
 * keychain via `KEYCHAIN_NAMESPACES.broker(id, field)`.
 */

import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useSafetyStore } from "@/store/safety";

import type { BrokerId } from "../../../types/broker";

const TOS_BODY = `Vysted Terminal connects to live trading venues using credentials you supply. Vysted does not custody funds, does not provide investment advice, and is not a registered broker-dealer.

By continuing you acknowledge:

- All orders sent to your broker are your own. The terminal will surface a confirmation dialog before any order is placed.
- AI-generated proposals are AI-generated; you remain solely responsible for any order you confirm.
- Live trading mode requires per-broker disclaimer acknowledgment.
- The AGPL-3.0 license attaches to every distribution of the terminal source.
- A kill switch (Cmd/Ctrl+Shift+K) halts all order routing globally; use it in any emergency.`;

export function FirstLaunchTosDialog() {
  const firstLaunchTosAcked = useSafetyStore((s) => s.firstLaunchTosAcked);
  const refreshFirstLaunchAck = useSafetyStore((s) => s.refreshFirstLaunchAck);
  const ackFirstLaunchTos = useSafetyStore((s) => s.ackFirstLaunchTos);
  const [busy, setBusy] = useState(false);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    void (async () => {
      await refreshFirstLaunchAck();
      setHydrated(true);
    })();
  }, [refreshFirstLaunchAck]);

  const handleAck = useCallback(async () => {
    setBusy(true);
    try {
      await ackFirstLaunchTos();
    } finally {
      setBusy(false);
    }
  }, [ackFirstLaunchTos]);

  if (!hydrated || firstLaunchTosAcked) {
    return null;
  }

  return (
    <Dialog open>
      <DialogContent
        data-testid="first-launch-tos-dialog"
        showCloseButton={false}
        onEscapeKeyDown={(e) => e.preventDefault()}
        onPointerDownOutside={(e) => e.preventDefault()}
      >
        <DialogHeader>
          <DialogTitle>Welcome to Vysted Terminal</DialogTitle>
          <DialogDescription>
            Please review the operating terms before connecting a broker.
          </DialogDescription>
        </DialogHeader>
        <pre className="text-muted-foreground max-h-64 overflow-y-auto whitespace-pre-wrap text-xs leading-snug">
          {TOS_BODY}
        </pre>
        <DialogFooter>
          <Button
            data-testid="first-launch-tos-accept"
            variant="default"
            onClick={handleAck}
            disabled={busy}
          >
            I understand — continue
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

interface BrokerFirstConnectDialogProps {
  broker: BrokerId;
  open: boolean;
  onAccept: () => void;
  onCancel: () => void;
}

export function BrokerFirstConnectDialog({
  broker,
  open,
  onAccept,
  onCancel,
}: BrokerFirstConnectDialogProps) {
  const refreshBrokerFirstConnectAck = useSafetyStore((s) => s.refreshBrokerFirstConnectAck);
  const ackBrokerFirstConnect = useSafetyStore((s) => s.ackBrokerFirstConnect);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (open) {
      void refreshBrokerFirstConnectAck(broker);
    }
  }, [open, broker, refreshBrokerFirstConnectAck]);

  const handleAccept = useCallback(async () => {
    setBusy(true);
    try {
      await ackBrokerFirstConnect(broker);
      onAccept();
    } finally {
      setBusy(false);
    }
  }, [ackBrokerFirstConnect, broker, onAccept]);

  if (!open) {
    return null;
  }

  return (
    <Dialog
      open
      onOpenChange={(value) => {
        if (!value) {
          onCancel();
        }
      }}
    >
      <DialogContent data-testid={`broker-first-connect-dialog-${broker}`}>
        <DialogHeader>
          <DialogTitle>Connect to {broker}</DialogTitle>
          <DialogDescription>
            Broker-specific terms reminder for {broker}. Acknowledge once per broker.
          </DialogDescription>
        </DialogHeader>
        <p className="text-muted-foreground text-xs leading-relaxed">
          You are about to connect Vysted Terminal to your <strong>{broker}</strong> account.
          Vysted will store your credentials in the OS keychain (never in plain files); your
          credentials never leave the local machine. By accepting you confirm you have read{" "}
          {brokerHandle(broker)} terms of service.
        </p>
        <DialogFooter>
          <Button variant="ghost" onClick={onCancel} disabled={busy}>
            Cancel
          </Button>
          <Button
            data-testid="broker-first-connect-accept"
            variant="default"
            onClick={handleAccept}
            disabled={busy}
          >
            I have read {brokerHandle(broker)} terms — continue
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function brokerHandle(broker: BrokerId): string {
  switch (broker) {
    case "dhan":
      return "Dhan's";
    case "angelone":
      return "Angel One's";
    case "kite":
      return "Kite's";
    case "alpaca":
      return "Alpaca's";
    case "ib":
      return "Interactive Brokers'";
    case "oanda":
      return "OANDA's";
    default:
      return "the exchange's";
  }
}

/**
 * Host component — renders the TOS modal at the app shell level. The other
 * two surfaces are rendered inline where they belong.
 */
export function DisclaimerFlow() {
  return <FirstLaunchTosDialog />;
}
