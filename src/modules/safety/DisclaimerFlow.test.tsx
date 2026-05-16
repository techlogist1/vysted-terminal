import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import * as keychain from "@/lib/keychain";
import { resetSafetyStoreForTests, useSafetyStore } from "@/store/safety";

import {
  BrokerFirstConnectDialog,
  DisclaimerFlow,
  FirstLaunchTosDialog,
} from "./DisclaimerFlow";

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
    keychainStore["broker:_meta:first-launch-tos"] = new Date().toISOString();
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
    expect(keychainStore["broker:_meta:first-launch-tos"]).toBeTruthy();
  });
});

describe("BrokerFirstConnectDialog", () => {
  it("does not render when open=false", () => {
    render(
      <BrokerFirstConnectDialog
        broker="alpaca"
        open={false}
        onAccept={() => undefined}
        onCancel={() => undefined}
      />,
    );
    expect(screen.queryByTestId("broker-first-connect-dialog-alpaca")).toBeNull();
  });

  it("renders, accepts, persists keychain ack, and calls onAccept", async () => {
    const onAccept = vi.fn();
    render(
      <BrokerFirstConnectDialog
        broker="alpaca"
        open
        onAccept={onAccept}
        onCancel={() => undefined}
      />,
    );
    await waitFor(() => {
      expect(screen.getByTestId("broker-first-connect-dialog-alpaca")).toBeInTheDocument();
    });
    const accept = screen.getByTestId("broker-first-connect-accept");
    await act(async () => {
      fireEvent.click(accept);
    });
    await waitFor(() => {
      expect(onAccept).toHaveBeenCalled();
    });
    expect(keychainStore["broker:alpaca:_meta:first-connect-ack"]).toBeTruthy();
  });

  it("Cancel calls onCancel without writing the ack", async () => {
    const onCancel = vi.fn();
    render(
      <BrokerFirstConnectDialog
        broker="kite"
        open
        onAccept={() => undefined}
        onCancel={onCancel}
      />,
    );
    const cancel = await screen.findByRole("button", { name: /cancel/i });
    await act(async () => {
      fireEvent.click(cancel);
    });
    expect(onCancel).toHaveBeenCalled();
    expect(keychainStore["broker:kite:_meta:first-connect-ack"]).toBeUndefined();
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
