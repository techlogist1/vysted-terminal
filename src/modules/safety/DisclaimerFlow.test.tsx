import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import * as keychain from "@/lib/keychain";
import { resetSafetyStoreForTests, useSafetyStore } from "@/store/safety";

import { DisclaimerFlow, FirstLaunchTosDialog } from "./DisclaimerFlow";

const keychainStore: Record<string, string> = {};

beforeEach(() => {
  for (const key of Object.keys(keychainStore)) {
    delete keychainStore[key];
  }
  vi.spyOn(keychain, "getSecret").mockImplementation(
    async (account) => keychainStore[account] ?? null,
  );
  vi.spyOn(keychain, "setSecret").mockImplementation(async (account, secret) => {
    keychainStore[account] = secret;
  });
  resetSafetyStoreForTests();
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("FirstLaunchTosDialog", () => {
  it("renders the dialog when no TOS ack is in keychain (cold launch)", async () => {
    render(<FirstLaunchTosDialog />);
    await waitFor(() => {
      expect(screen.getByTestId("first-launch-tos-dialog")).toBeInTheDocument();
    });
  });

  it("does NOT render when the keychain already has the ack (warm launch)", async () => {
    keychainStore["app-meta:first-launch-terms"] = new Date().toISOString();
    render(<FirstLaunchTosDialog />);
    await waitFor(() => {
      expect(useSafetyStore.getState().firstLaunchTosAcked).toBe(true);
    });
    expect(screen.queryByTestId("first-launch-tos-dialog")).toBeNull();
  });

  it("Accept writes the ack to keychain and dismisses the dialog", async () => {
    render(<FirstLaunchTosDialog />);
    const button = await screen.findByTestId("first-launch-tos-accept");
    await act(async () => {
      fireEvent.click(button);
    });
    await waitFor(() => {
      expect(useSafetyStore.getState().firstLaunchTosAcked).toBe(true);
    });
    expect(keychainStore["app-meta:first-launch-terms"]).toBeTruthy();
  });

  it("states research-only terms and promises no order routing or kill switch", async () => {
    render(<FirstLaunchTosDialog />);
    const dialog = await screen.findByTestId("first-launch-tos-dialog");
    const text = dialog.textContent ?? "";
    expect(text).toMatch(/not provide investment advice/i);
    expect(text).toMatch(/no brokerage connection/i);
    expect(text).toMatch(/cannot place, route or simulate orders/i);
    expect(text).toMatch(/before you start/i);
    expect(text).not.toMatch(/kill switch|Cmd\/Ctrl\+Shift\+K/i);
    expect(text).not.toMatch(/connecting a broker/i);
  });
});

describe("DisclaimerFlow host", () => {
  it("mounts the TOS modal at the app shell level (cold launch)", async () => {
    render(<DisclaimerFlow />);
    await waitFor(() => {
      expect(screen.getByTestId("first-launch-tos-dialog")).toBeInTheDocument();
    });
  });
});
