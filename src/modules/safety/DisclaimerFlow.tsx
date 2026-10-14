"use client";

/**
 * DisclaimerFlow — the first-launch research terms (onboarding gate).
 *
 * The ack lives in app-meta `first-launch-terms` (legacy keychain item read as a
 * fallback, see `src/store/safety.ts`).
 * Renders a blocking modal on the very first launch; `OnboardingFlow`
 * sequences after the ack. It is the product's only in-app
 * "not investment advice" notice.
 *
 * No `localStorage` / `sessionStorage`. Nothing dismisses it but the explicit
 * accept button, and only a saved ack closes it.
 */

import { useCallback, useEffect, useState } from "react";
import { AlertCircle } from "lucide-react";

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

const TOS_BODY = `Vysted Terminal is a data and analysis tool. It does not provide investment advice and is not a registered broker-dealer or investment adviser.

By continuing you acknowledge:

- Vysted has no brokerage connection. It cannot place, route or simulate orders.
- Market data may be delayed, incomplete or wrong. Check anything you rely on against the source.
- AI-generated analysis can be wrong. You remain solely responsible for your own decisions.
- Vysted Terminal is source-available under PolyForm Strict 1.0.0 (noncommercial use) or a commercial license — see LICENSING.md.`;

export function FirstLaunchTosDialog() {
  const firstLaunchTosAcked = useSafetyStore((s) => s.firstLaunchTosAcked);
  const refreshFirstLaunchAck = useSafetyStore((s) => s.refreshFirstLaunchAck);
  const ackFirstLaunchTos = useSafetyStore((s) => s.ackFirstLaunchTos);
  const [busy, setBusy] = useState(false);
  const [hydrated, setHydrated] = useState(false);
  const [ackError, setAckError] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      await refreshFirstLaunchAck();
      setHydrated(true);
    })();
  }, [refreshFirstLaunchAck]);

  const handleAck = useCallback(async () => {
    setBusy(true);
    setAckError(null);
    try {
      await ackFirstLaunchTos();
    } catch (err: unknown) {
      setAckError(err instanceof Error ? err.message : "Couldn't save your answer. Try again.");
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
        className="bg-charcoal-900 border-charcoal-700"
        showCloseButton={false}
        onEscapeKeyDown={(e) => e.preventDefault()}
        onPointerDownOutside={(e) => e.preventDefault()}
      >
        <DialogHeader>
          <DialogTitle>Welcome to Vysted</DialogTitle>
          <DialogDescription>Please review the terms before you start.</DialogDescription>
        </DialogHeader>
        <pre
          className={
            "text-charcoal-400 text-caption max-h-64 overflow-y-auto leading-snug whitespace-pre-wrap" /* tokens-ok: TOS-body scroll cap — layout */
          }
        >
          {TOS_BODY}
        </pre>
        {ackError !== null && (
          <div className="border-negative/40 bg-negative/10 text-negative text-caption flex items-start gap-2 rounded-none border px-3 py-2">
            <AlertCircle className="mt-0.5 size-3 shrink-0" aria-hidden="true" />
            <p>{ackError}</p>
          </div>
        )}
        <DialogFooter>
          <Button
            data-testid="first-launch-tos-accept"
            variant="default"
            onClick={handleAck}
            disabled={busy}
          >
            {busy ? "Saving…" : "I understand — continue"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/**
 * Host component — renders the terms modal at the app shell level.
 */
export function DisclaimerFlow() {
  return <FirstLaunchTosDialog />;
}
