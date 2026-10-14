import { beforeEach, describe, expect, it, vi } from "vitest";

import * as keychain from "@/lib/keychain";

import {
  FIRST_LAUNCH_TERMS_KEY,
  FIRST_LAUNCH_TOS_ACCOUNT,
  resetSafetyStoreForTests,
  useSafetyStore,
} from "@/store/safety";

describe("useSafetyStore", () => {
  const secrets: Record<string, string> = {};
  const meta: Record<string, string> = {};

  beforeEach(() => {
    resetSafetyStoreForTests();
    vi.restoreAllMocks();
    for (const store of [secrets, meta]) {
      for (const key of Object.keys(store)) delete store[key];
    }
    vi.spyOn(keychain, "getSecret").mockImplementation(async (account) => secrets[account] ?? null);
    vi.spyOn(keychain, "setSecret").mockImplementation(async (account, secret) => {
      secrets[account] = secret;
    });
    vi.spyOn(keychain, "getAppMeta").mockImplementation(async (key) => meta[key] ?? null);
    vi.spyOn(keychain, "setAppMeta").mockImplementation(async (key, value) => {
      meta[key] = value;
    });
  });

  it("starts with the empty default shape", () => {
    expect(useSafetyStore.getState().firstLaunchTosAcked).toBe(false);
  });

  it("first-launch terms ack: app-meta read + write round-trip", async () => {
    expect(FIRST_LAUNCH_TERMS_KEY).toBe("first-launch-terms");
    await useSafetyStore.getState().refreshFirstLaunchAck();
    expect(useSafetyStore.getState().firstLaunchTosAcked).toBe(false);
    await useSafetyStore.getState().ackFirstLaunchTos();
    expect(useSafetyStore.getState().firstLaunchTosAcked).toBe(true);
    expect(meta[FIRST_LAUNCH_TERMS_KEY]).toBeTruthy();
    // A fresh launch reads it back.
    resetSafetyStoreForTests();
    await useSafetyStore.getState().refreshFirstLaunchAck();
    expect(useSafetyStore.getState().firstLaunchTosAcked).toBe(true);
  });

  it("reads the legacy keychain ack and carries it into app-meta", async () => {
    expect(FIRST_LAUNCH_TOS_ACCOUNT).toBe("app-meta:first-launch-terms");
    secrets[FIRST_LAUNCH_TOS_ACCOUNT] = "2026-06-01T00:00:00.000Z";
    await useSafetyStore.getState().refreshFirstLaunchAck();
    expect(useSafetyStore.getState().firstLaunchTosAcked).toBe(true);
    expect(meta[FIRST_LAUNCH_TERMS_KEY]).toBe("2026-06-01T00:00:00.000Z");
  });

  it("a secret store that is unavailable still keeps the ack (Linux without Secret Service)", async () => {
    vi.mocked(keychain.getSecret).mockRejectedValue(new Error("secret-store-unavailable"));
    await useSafetyStore.getState().ackFirstLaunchTos();
    resetSafetyStoreForTests();
    await useSafetyStore.getState().refreshFirstLaunchAck();
    expect(useSafetyStore.getState().firstLaunchTosAcked).toBe(true);
  });

  it("a failed save rejects and leaves the terms un-acked", async () => {
    vi.mocked(keychain.setAppMeta).mockRejectedValue(new Error("disk full"));
    await expect(useSafetyStore.getState().ackFirstLaunchTos()).rejects.toThrow("disk full");
    expect(useSafetyStore.getState().firstLaunchTosAcked).toBe(false);
  });

  it("never accesses localStorage / sessionStorage", () => {
    const src = useSafetyStore.toString();
    expect(src.includes("localStorage")).toBe(false);
    expect(src.includes("sessionStorage")).toBe(false);
  });
});
