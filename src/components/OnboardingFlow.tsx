"use client";

/**
 * First-run wizard (R16). Order: the first-launch terms (`DisclaimerFlow`, the
 * only terms surface — this waits on `firstLaunchTosAcked`) → "How should
 * Vysted think?" (on this computer / my own key / skip) → a short tour ending
 * in one example that works on the chosen path.
 *
 * Shows once: it opens while app-meta `onboarding-complete` is absent, and
 * every exit writes it (the tour's start, Skip, Close). A CTA (the chat empty
 * state, the model strip) re-opens it on demand via `useOnboardingStore.open`,
 * optionally straight at the model list or the key step; a re-open skips the
 * tour.
 */

import { useCallback, useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";

import { ChooseStep, type ThinkPath } from "@/components/onboarding/ChooseStep";
import { KeyStep } from "@/components/onboarding/KeyStep";
import { LocalStep } from "@/components/onboarding/LocalStep";
import { TourStep } from "@/components/onboarding/TourStep";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { tween } from "@/lib/motion";
import { useOnboardingStore } from "@/store/onboarding";
import { useSafetyStore } from "@/store/safety";

type Step = "choose" | "local" | "key" | "tour";

export function OnboardingFlow() {
  const tosAcked = useSafetyStore((s) => s.firstLaunchTosAcked);
  const seen = useOnboardingStore((s) => s.seen);
  const forceOpen = useOnboardingStore((s) => s.forceOpen);
  const forceStep = useOnboardingStore((s) => s.forceStep);
  const refresh = useOnboardingStore((s) => s.refresh);
  const markSeen = useOnboardingStore((s) => s.markSeen);
  const closeForce = useOnboardingStore((s) => s.close);

  const [open, setOpen] = useState(false);
  const [firstRun, setFirstRun] = useState(false);
  const [step, setStep] = useState<Step>("choose");
  const [path, setPath] = useState<ThinkPath>("skip");
  const [localModelId, setLocalModelId] = useState<string | null>(null);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  // `seen === null` = not probed yet → wait. The local `open` latch keeps the
  // dialog up after the tour's start writes the marker.
  const shouldOpen = tosAcked && (seen === false || forceOpen);
  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    if (!shouldOpen) return;
    setOpen(true);
    setFirstRun(seen === false);
    setStep(forceOpen && forceStep ? forceStep : "choose");
    // Latch only on the open transition; later `seen` changes must not reset the step.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [shouldOpen, forceStep]);
  /* eslint-enable react-hooks/set-state-in-effect */

  const finish = useCallback(
    async (choice: string) => {
      // Await the durable write before closing so a quit right after can't lose it.
      await markSeen(choice);
      setOpen(false);
      closeForce();
    },
    [markSeen, closeForce],
  );

  /** A path is set up (or skipped): first run → the tour; a re-open → close. */
  const chosen = useCallback(
    (next: ThinkPath, modelId: string | null = null) => {
      setPath(next);
      setLocalModelId(modelId);
      if (!firstRun) {
        void finish(next);
        return;
      }
      void markSeen(next);
      setStep("tour");
    },
    [firstRun, finish, markSeen],
  );

  if (!open) return null;

  const back = firstRun || !forceStep ? () => setStep("choose") : () => void finish("seen");

  return (
    <Dialog open onOpenChange={(value) => (value ? undefined : void finish(path))}>
      <DialogContent
        data-testid="onboarding-flow"
        showCloseButton={false}
        // Only its own buttons close it — a stray click or Escape during boot must not.
        onEscapeKeyDown={(e) => e.preventDefault()}
        onPointerDownOutside={(e) => e.preventDefault()}
        onInteractOutside={(e) => e.preventDefault()}
        className="border-charcoal-700 bg-charcoal-950 max-w-2xl gap-0 overflow-hidden p-0"
      >
        <DialogTitle className="sr-only">Welcome to Vysted</DialogTitle>
        <DialogDescription className="sr-only">
          Choose how the assistant thinks: on this computer, with your own key, or skip for now.
        </DialogDescription>
        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={step}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={tween(0.22)}
          >
            {step === "choose" && (
              <ChooseStep onPick={(p) => (p === "skip" ? chosen("skip") : setStep(p))} />
            )}
            {step === "local" && (
              <LocalStep
                onBack={back}
                onContinue={(id) => chosen("local", id)}
                onUseKey={() => setStep("key")}
                onSkip={() => chosen("skip")}
              />
            )}
            {step === "key" && <KeyStep onBack={back} onDone={() => chosen("key")} />}
            {step === "tour" && (
              <TourStep
                path={path}
                localModelId={localModelId}
                onFinish={() => void finish(path)}
              />
            )}
          </motion.div>
        </AnimatePresence>
      </DialogContent>
    </Dialog>
  );
}
