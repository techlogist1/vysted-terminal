/**
 * Onboarding store (Track 2) — the first-run "completed/seen" gate.
 *
 * The first-run flow is an UPGRADE, not a gate: the terminal works keyless out of
 * the box, so onboarding is dismissible and shows exactly once. "Seen" is durable
 * in the OS keychain (`app-meta:onboarding-complete`) — the same durability the
 * disclaimer acks use, so a workspace-layout reset or an imported older blob does
 * NOT re-trigger it (and there is no workspace-restore-timing flash, unlike a blob
 * field). `seen === null` means "not probed yet" so the overlay can wait before
 * deciding to render. `forceOpen` lets a CTA (e.g. the keyless chat empty-state)
 * re-open the flow on demand even after it was seen.
 */

import { create } from "zustand";

import { getSecret, KEYCHAIN_NAMESPACES, setSecret } from "@/lib/keychain";

const ONBOARDING_ACCOUNT = KEYCHAIN_NAMESPACES.appMeta("onboarding-complete");

interface OnboardingState {
  /** Whether the first-run flow has been completed/skipped. `null` until probed. */
  seen: boolean | null;
  /** Force the flow open from a CTA, regardless of `seen`. */
  forceOpen: boolean;
  /** Probe the keychain for the completion marker (call once on boot). */
  refresh: () => Promise<void>;
  /** Persist completion (durable) + close. `choice` records the path taken. */
  markSeen: (choice: string) => Promise<void>;
  /** Re-open the flow on demand (CTA). */
  open: () => void;
  /** Close without marking seen (used internally; markSeen is the real exit). */
  close: () => void;
}

export const useOnboardingStore = create<OnboardingState>((set) => ({
  seen: null,
  forceOpen: false,
  refresh: async () => {
    try {
      const value = await getSecret(ONBOARDING_ACCOUNT);
      set({ seen: Boolean(value && value.length > 0) });
    } catch {
      // Outside the Tauri shell (browser dev) the keychain rejects — treat as
      // "not seen" so the flow is exercisable in dev, harmless in production.
      set({ seen: false });
    }
  },
  markSeen: async (choice) => {
    try {
      await setSecret(ONBOARDING_ACCOUNT, choice || "seen");
    } catch {
      // Non-Tauri / keychain unavailable — still close for the session.
    }
    set({ seen: true, forceOpen: false });
  },
  open: () => set({ forceOpen: true }),
  close: () => set({ forceOpen: false }),
}));
