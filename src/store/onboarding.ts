/**
 * Onboarding store (Track 2) — the first-run "completed/seen" gate.
 *
 * The first-run flow is an UPGRADE, not a gate: the terminal works keyless out of
 * the box, so onboarding is dismissible and shows exactly once. "Seen" is durable
 * in the data-dir app-meta file (`onboarding-complete`), outside the workspace
 * blob, so a workspace-layout reset or an imported older blob does NOT re-trigger
 * it (and there is no workspace-restore-timing flash). It is not a secret, so it
 * is kept out of the OS keychain: without a usable secret store (Linux with no
 * Secret Service provider) it would reappear every launch (R15-CROSS-PLATFORM-011).
 * The keychain id it used to live under is read as a fallback and carried over.
 * `seen === null` means "not probed yet" so the overlay can wait before
 * deciding to render. `forceOpen` lets a CTA (e.g. the keyless chat empty-state)
 * re-open the flow on demand even after it was seen.
 */

import { create } from "zustand";

import { getAppMeta, getSecret, KEYCHAIN_NAMESPACES, setAppMeta } from "@/lib/keychain";

const ONBOARDING_KEY = "onboarding-complete";
/** The setup banner's dismissal, kept beside the "seen" marker (R15-UI-019). */
const BANNER_KEY = "onboarding-banner-dismissed";

/**
 * A flag's value from the app-meta file, else from its legacy keychain item
 * (carried over into the file once found). `null` when neither has it or
 * neither store is reachable (outside the Tauri shell).
 */
async function readFlag(key: string): Promise<string | null> {
  const value = await getAppMeta(key).catch(() => null);
  if (value) return value;
  const legacy = await getSecret(KEYCHAIN_NAMESPACES.appMeta(key)).catch(() => null);
  if (legacy) await setAppMeta(key, legacy).catch(() => undefined);
  return legacy;
}

interface OnboardingState {
  /** Whether the first-run flow has been completed/skipped. `null` until probed. */
  seen: boolean | null;
  /** Whether the setup banner was dismissed (durable). `null` until probed. */
  bannerDismissed: boolean | null;
  /** Force the flow open from a CTA, regardless of `seen`. */
  forceOpen: boolean;
  /** The step a forced open lands on (`local` = the model download step). */
  forceStep: "local" | null;
  /** Probe the app-meta file for the completion marker (call once on boot). */
  refresh: () => Promise<void>;
  /** Probe the app-meta file for the banner-dismissed marker. */
  refreshBanner: () => Promise<void>;
  /** Persist the banner's dismissal (durable across relaunches). */
  dismissBanner: () => Promise<void>;
  /** Persist completion (durable) + close. `choice` records the path taken. */
  markSeen: (choice: string) => Promise<void>;
  /** Re-open the flow on demand (CTA), optionally at the local-model step. */
  open: (step?: "local") => void;
  /** Close without marking seen (used internally; markSeen is the real exit). */
  close: () => void;
}

export const useOnboardingStore = create<OnboardingState>((set) => ({
  seen: null,
  bannerDismissed: null,
  forceOpen: false,
  forceStep: null,
  // Outside the Tauri shell (browser dev) both stores reject — "not seen", so
  // the flow is exercisable in dev.
  refresh: async () => {
    set({ seen: Boolean(await readFlag(ONBOARDING_KEY)) });
  },
  refreshBanner: async () => {
    set({ bannerDismissed: Boolean(await readFlag(BANNER_KEY)) });
  },
  dismissBanner: async () => {
    set({ bannerDismissed: true });
    try {
      await setAppMeta(BANNER_KEY, "dismissed");
    } catch {
      // Non-Tauri — dismissed for the session.
    }
  },
  markSeen: async (choice) => {
    try {
      await setAppMeta(ONBOARDING_KEY, choice || "seen");
    } catch {
      // Non-Tauri — still close for the session.
    }
    set({ seen: true, forceOpen: false, forceStep: null });
  },
  open: (step) => set({ forceOpen: true, forceStep: step ?? null }),
  close: () => set({ forceOpen: false, forceStep: null }),
}));
