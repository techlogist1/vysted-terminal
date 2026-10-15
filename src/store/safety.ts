/**
 * Safety store — the first-launch research terms ack.
 *
 * The ack lives in the data-dir app-meta file under `first-launch-terms`, so a
 * machine without a usable OS secret store (Linux with no Secret Service) shows
 * the terms once, not every launch. The keychain item it used to live under
 * (`KEYCHAIN_NAMESPACES.appMeta("first-launch-terms")`) is read as a legacy
 * fallback and carried over (same pattern as `onboarding-complete`). This store
 * mirrors the read so `DisclaimerFlow` and `OnboardingFlow` agree on one value.
 *
 * No `localStorage` / `sessionStorage`.
 */

import { create } from "zustand";

import { KEYCHAIN_NAMESPACES, setAppMeta } from "@/lib/keychain";
import { readFlag } from "@/store/onboarding";

/** App-meta key for the first-launch terms ack. */
export const FIRST_LAUNCH_TERMS_KEY = "first-launch-terms";
/** Legacy keychain account the ack used to live under (read once, carried over). */
export const FIRST_LAUNCH_TOS_ACCOUNT = KEYCHAIN_NAMESPACES.appMeta(FIRST_LAUNCH_TERMS_KEY);

/** Read whether the user has acked the first-launch terms. */
export async function hasFirstLaunchTosAck(): Promise<boolean> {
  return Boolean(await readFlag(FIRST_LAUNCH_TERMS_KEY));
}

/** Persist the first-launch terms ack (ISO timestamp value). Rejects when it
 *  could not be saved, so the terms stay up rather than silently re-showing. */
export async function recordFirstLaunchTosAck(): Promise<void> {
  await setAppMeta(FIRST_LAUNCH_TERMS_KEY, new Date().toISOString());
}

interface SafetyState {
  firstLaunchTosAcked: boolean;
  refreshFirstLaunchAck: () => Promise<void>;
  ackFirstLaunchTos: () => Promise<void>;
}

export const useSafetyStore = create<SafetyState>((set) => ({
  firstLaunchTosAcked: false,

  refreshFirstLaunchAck: async () => {
    const acked = await hasFirstLaunchTosAck();
    set({ firstLaunchTosAcked: acked });
  },

  ackFirstLaunchTos: async () => {
    await recordFirstLaunchTosAck();
    set({ firstLaunchTosAcked: true });
  },
}));

/** Test helper: reset the safety store to its initial shape. */
export function resetSafetyStoreForTests(): void {
  useSafetyStore.setState({ firstLaunchTosAcked: false });
}
