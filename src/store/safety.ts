/**
 * Safety store — the first-launch research terms ack.
 *
 * The ack is persisted in the OS keychain under
 * `KEYCHAIN_NAMESPACES.appMeta("first-launch-terms")`; this store mirrors the
 * read so `DisclaimerFlow` and `OnboardingFlow` agree on one value.
 *
 * No `localStorage` / `sessionStorage`. Ack reads/writes go through the
 * keychain wrapper (`src/lib/keychain.ts`).
 */

import { create } from "zustand";

import { getSecret, KEYCHAIN_NAMESPACES, setSecret } from "@/lib/keychain";

/** Keychain account for the first-launch terms ack. */
export const FIRST_LAUNCH_TOS_ACCOUNT = KEYCHAIN_NAMESPACES.appMeta("first-launch-terms");

/** Read whether the user has acked the first-launch terms. */
export async function hasFirstLaunchTosAck(): Promise<boolean> {
  const value = await getSecret(FIRST_LAUNCH_TOS_ACCOUNT);
  return value !== null && value.length > 0;
}

/** Write the first-launch terms ack to the keychain (ISO timestamp value). */
export async function recordFirstLaunchTosAck(): Promise<void> {
  await setSecret(FIRST_LAUNCH_TOS_ACCOUNT, new Date().toISOString());
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
