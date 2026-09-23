import { beforeEach, describe, expect, it, vi } from "vitest";

import * as keychain from "@/lib/keychain";

import { FIRST_LAUNCH_TOS_ACCOUNT, resetSafetyStoreForTests, useSafetyStore } from "@/store/safety";

describe("useSafetyStore", () => {
  beforeEach(() => {
    resetSafetyStoreForTests();
    vi.restoreAllMocks();
  });

  it("starts with the empty default shape", () => {
    const state = useSafetyStore.getState();
    expect(state.firstLaunchTosAcked).toBe(false);
  });

  it("first-launch terms ack: keychain read + write round-trip", async () => {
    const store: Record<string, string> = {};
    vi.spyOn(keychain, "getSecret").mockImplementation(async (account) => store[account] ?? null);
    vi.spyOn(keychain, "setSecret").mockImplementation(async (account, secret) => {
      store[account] = secret;
    });

    expect(FIRST_LAUNCH_TOS_ACCOUNT).toBe("app-meta:first-launch-terms");

    await useSafetyStore.getState().refreshFirstLaunchAck();
    expect(useSafetyStore.getState().firstLaunchTosAcked).toBe(false);
    await useSafetyStore.getState().ackFirstLaunchTos();
    expect(useSafetyStore.getState().firstLaunchTosAcked).toBe(true);
    expect(store[FIRST_LAUNCH_TOS_ACCOUNT]).toBeTruthy();
  });

  it("never accesses localStorage / sessionStorage", () => {
    const src = useSafetyStore.toString();
    expect(src.includes("localStorage")).toBe(false);
    expect(src.includes("sessionStorage")).toBe(false);
  });
});
