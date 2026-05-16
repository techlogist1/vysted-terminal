import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import * as keychain from "@/lib/keychain";
import * as sidecarClient from "@/lib/sidecar-client";
import { resetBrokersStoreForTests, useBrokersStore } from "@/store/brokers";
import { resetSafetyStoreForTests, useSafetyStore } from "@/store/safety";

import { BrokerConnectPanel } from "./BrokerConnectPanel";

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
  vi.spyOn(sidecarClient, "getSidecarBaseUrl").mockResolvedValue("http://127.0.0.1:9999");

  resetSafetyStoreForTests();
  resetBrokersStoreForTests();
  keychainStore["broker:_meta:first-launch-tos"] = new Date().toISOString();
  useSafetyStore.setState({ firstLaunchTosAcked: true });
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

function seedBrokers(): void {
  useBrokersStore.setState({
    byId: {
      alpaca: {
        broker: "alpaca",
        status: "disconnected",
        mode: "paper",
        readOnly: false,
        capabilities: {
          supportsEquity: true,
          supportsOptions: false,
          supportsCrypto: false,
          supportsForex: false,
          supportsFutures: false,
          requiresStaticIp: false,
        },
      },
      kite: {
        broker: "kite",
        status: "connected",
        mode: "paper",
        readOnly: false,
        capabilities: {
          supportsEquity: true,
          supportsOptions: false,
          supportsCrypto: false,
          supportsForex: false,
          supportsFutures: false,
          requiresStaticIp: true,
        },
      },
      "ccxt-binance": {
        broker: "ccxt-binance",
        status: "disconnected",
        mode: "paper",
        readOnly: false,
        capabilities: {
          supportsEquity: false,
          supportsOptions: false,
          supportsCrypto: true,
          supportsForex: false,
          supportsFutures: false,
          requiresStaticIp: false,
        },
      },
    },
    status: "ready",
    error: null,
  });
}

describe("BrokerConnectPanel", () => {
  it("renders rows for each broker with status + mode badges", async () => {
    vi.spyOn(sidecarClient, "sidecarGet").mockImplementation(async (path: string) => {
      if (path === "/brokers") {
        return {
          brokers: Object.values(useBrokersStore.getState().byId).filter((s) => s !== undefined),
        };
      }
      return {};
    });
    seedBrokers();
    render(<BrokerConnectPanel />);
    await waitFor(() => {
      expect(screen.getByTestId("broker-row-alpaca")).toBeInTheDocument();
      expect(screen.getByTestId("broker-row-kite")).toBeInTheDocument();
      expect(screen.getByTestId("broker-row-ccxt-binance")).toBeInTheDocument();
    });
    const badges = screen.getAllByTestId("broker-status-badge");
    expect(badges.length).toBeGreaterThanOrEqual(3);
  });

  it("Connect opens the broker first-connect dialog when not yet acked", async () => {
    vi.spyOn(sidecarClient, "sidecarGet").mockImplementation(async (path: string) => {
      if (path === "/brokers") {
        return {
          brokers: Object.values(useBrokersStore.getState().byId).filter((s) => s !== undefined),
        };
      }
      return {};
    });
    seedBrokers();
    render(<BrokerConnectPanel />);
    const connectBtn = await screen.findByTestId("connect-alpaca");
    await act(async () => {
      fireEvent.click(connectBtn);
    });
    await waitFor(() => {
      expect(screen.getByTestId("broker-first-connect-dialog-alpaca")).toBeInTheDocument();
    });
  });

  it("blocks connect when TOS is not acked", async () => {
    vi.spyOn(sidecarClient, "sidecarGet").mockImplementation(async (path: string) => {
      if (path === "/brokers") {
        return {
          brokers: Object.values(useBrokersStore.getState().byId).filter((s) => s !== undefined),
        };
      }
      return {};
    });
    seedBrokers();
    delete keychainStore["broker:_meta:first-launch-tos"];
    useSafetyStore.setState({ firstLaunchTosAcked: false });
    render(<BrokerConnectPanel />);
    const connectBtn = await screen.findByTestId("connect-alpaca");
    expect(connectBtn).toBeDisabled();
  });
});
