import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import * as keychain from "@/lib/keychain";
import { resetSafetyStoreForTests, useSafetyStore } from "@/store/safety";

import { DisclaimerFlow, FirstLaunchTosDialog } from "./DisclaimerFlow";

const keychainStore: Record<string, string> = {};
const appMeta: Record<string, string> = {};

beforeEach(() => {
  for (const store of [keychainStore, appMeta]) {
    for (const key of Object.keys(store)) delete store[key];
  }
  vi.spyOn(keychain, "getSecret").mockImplementation(
    async (account) => keychainStore[account] ?? null,
  );
  vi.spyOn(keychain, "setSecret").mockImplementation(async (account, secret) => {
    keychainStore[account] = secret;
  });
  vi.spyOn(keychain, "getAppMeta").mockImplementation(async (key) => appMeta[key] ?? null);
  vi.spyOn(keychain, "setAppMeta").mockImplementation(async (key, value) => {
    appMeta[key] = value;
  });
  resetSafetyStoreForTests();
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("FirstLaunchTosDialog", () => {
  it("renders the dialog when no terms ack is stored (cold launch)", async () => {
    render(<FirstLaunchTosDialog />);
    await waitFor(() => {
      expect(screen.getByTestId("first-launch-tos-dialog")).toBeInTheDocument();
    });
  });

  it("does NOT render when app-meta already has the ack (warm launch)", async () => {
    appMeta["first-launch-terms"] = new Date().toISOString();
    render(<FirstLaunchTosDialog />);
    await waitFor(() => {
      expect(useSafetyStore.getState().firstLaunchTosAcked).toBe(true);
    });
    expect(screen.queryByTestId("first-launch-tos-dialog")).toBeNull();
  });

  it("does NOT render when only the legacy keychain ack exists, and carries it over", async () => {
    keychainStore["app-meta:first-launch-terms"] = "2026-06-01T00:00:00.000Z";
    render(<FirstLaunchTosDialog />);
    await waitFor(() => {
      expect(useSafetyStore.getState().firstLaunchTosAcked).toBe(true);
    });
    expect(screen.queryByTestId("first-launch-tos-dialog")).toBeNull();
    expect(appMeta["first-launch-terms"]).toBe("2026-06-01T00:00:00.000Z");
  });

  it("Accept writes the ack to app-meta and dismisses the dialog", async () => {
    render(<FirstLaunchTosDialog />);
    const button = await screen.findByTestId("first-launch-tos-accept");
    await act(async () => {
      fireEvent.click(button);
    });
    await waitFor(() => {
      expect(useSafetyStore.getState().firstLaunchTosAcked).toBe(true);
    });
    expect(appMeta["first-launch-terms"]).toBeTruthy();
    expect(screen.queryByTestId("first-launch-tos-dialog")).toBeNull();
  });

  it("a failed save keeps the terms up with a plain error (no way around them)", async () => {
    vi.mocked(keychain.setAppMeta).mockRejectedValue(new Error("disk full"));
    render(<FirstLaunchTosDialog />);
    const button = await screen.findByTestId("first-launch-tos-accept");
    await act(async () => {
      fireEvent.click(button);
    });
    expect(useSafetyStore.getState().firstLaunchTosAcked).toBe(false);
    expect(screen.getByTestId("first-launch-tos-dialog")).toBeInTheDocument();
    expect(screen.getByText(/disk full/)).toBeInTheDocument();
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
  it("mounts the terms modal at the app shell level (cold launch)", async () => {
    render(<DisclaimerFlow />);
    await waitFor(() => {
      expect(screen.getByTestId("first-launch-tos-dialog")).toBeInTheDocument();
    });
  });
});
