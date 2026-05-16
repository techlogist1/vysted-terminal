import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import * as sidecarClient from "@/lib/sidecar-client";
import { resetBrokersStoreForTests, useBrokersStore } from "@/store/brokers";
import { resetOrdersStoreForTests, useOrdersStore } from "@/store/orders";

import { BrokerOrderEntry } from "./BrokerOrderEntry";

const fetchMock = vi.fn();

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockReset();
  vi.spyOn(sidecarClient, "getSidecarBaseUrl").mockResolvedValue("http://127.0.0.1:9999");
  resetBrokersStoreForTests();
  resetOrdersStoreForTests();
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

function seedConnectedBroker(): void {
  useBrokersStore.setState({
    byId: {
      alpaca: {
        broker: "alpaca",
        status: "connected",
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
    },
  });
}

describe("BrokerOrderEntry", () => {
  it("requires a broker selection before submit", async () => {
    seedConnectedBroker();
    render(<BrokerOrderEntry />);
    const submit = screen.getByTestId("propose-order");
    await act(async () => {
      fireEvent.click(submit);
    });
    await waitFor(() => {
      expect(screen.getByText(/select a broker/i)).toBeInTheDocument();
    });
  });

  it("proposes an order, pushes into the orders inbox, and opens the dialog", async () => {
    seedConnectedBroker();
    fetchMock.mockResolvedValueOnce({
      ok: true,
      status: 200,
      statusText: "OK",
      json: async () => ({
        proposalId: "p-1",
        broker: "alpaca",
        accountId: "acc-1",
        symbol: "AAPL",
        side: "buy",
        type: "limit",
        quantity: 5,
        limitPrice: 150,
        currency: "USD",
        estimatedValue: 750,
        source: "manual",
        sourceDetails: {},
        proposedAt: 1,
      }),
    } as Response);
    render(<BrokerOrderEntry />);
    const brokerSelect = screen.getByLabelText(/broker/i).parentElement!.querySelector("select")!;
    await act(async () => {
      fireEvent.change(brokerSelect, { target: { value: "alpaca" } });
    });
    const symbolInput = screen.getByLabelText(/symbol/i).parentElement!.querySelector("input")!;
    await act(async () => {
      fireEvent.change(symbolInput, { target: { value: "AAPL" } });
    });
    const qtyInput = screen.getByLabelText(/quantity/i).parentElement!.querySelector("input")!;
    await act(async () => {
      fireEvent.change(qtyInput, { target: { value: "5" } });
    });
    const limitInput = screen.getByLabelText(/limit/i).parentElement!.querySelector("input")!;
    await act(async () => {
      fireEvent.change(limitInput, { target: { value: "150" } });
    });
    const submit = screen.getByTestId("propose-order");
    await act(async () => {
      fireEvent.click(submit);
    });
    await waitFor(() => {
      expect(useOrdersStore.getState().proposals).toHaveLength(1);
      expect(useOrdersStore.getState().activeProposalId).toBe("p-1");
    });
  });

  it("surfaces a propose error from the sidecar", async () => {
    seedConnectedBroker();
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 422,
      statusText: "Unprocessable",
      json: async () => ({ detail: "exceeds limit" }),
    } as Response);
    render(<BrokerOrderEntry />);
    const brokerSelect = screen.getByLabelText(/broker/i).parentElement!.querySelector("select")!;
    await act(async () => {
      fireEvent.change(brokerSelect, { target: { value: "alpaca" } });
    });
    const qtyInput = screen.getByLabelText(/quantity/i).parentElement!.querySelector("input")!;
    await act(async () => {
      fireEvent.change(qtyInput, { target: { value: "10000" } });
    });
    const submit = screen.getByTestId("propose-order");
    await act(async () => {
      fireEvent.click(submit);
    });
    await waitFor(() => {
      expect(screen.getByText(/exceeds limit/i)).toBeInTheDocument();
    });
  });
});
