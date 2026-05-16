import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import { resetOrdersStoreForTests, useOrdersStore } from "@/store/orders";
import { resetSafetyStoreForTests, useSafetyStore } from "@/store/safety";
import { resetBrokersStoreForTests, useBrokersStore } from "@/store/brokers";

import { OrderConfirmationDialog } from "./OrderConfirmationDialog";

import type { BrokerOrderProposal } from "../../../types/broker";

vi.mock("@/lib/sidecar-client", async () => {
  const actual =
    await vi.importActual<typeof import("@/lib/sidecar-client")>("@/lib/sidecar-client");
  return {
    ...actual,
    getSidecarBaseUrl: vi.fn(async () => "http://127.0.0.1:9999"),
  };
});

const fetchMock = vi.fn();

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockReset();
  resetSafetyStoreForTests();
  resetOrdersStoreForTests();
  resetBrokersStoreForTests();
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

function makeProposal(partial: Partial<BrokerOrderProposal> = {}): BrokerOrderProposal {
  return {
    proposalId: "p-1",
    broker: "alpaca",
    accountId: "acc-1",
    symbol: "AAPL",
    side: "buy",
    type: "limit",
    quantity: 10,
    limitPrice: 150,
    currency: "USD",
    estimatedValue: 1500,
    source: "manual",
    sourceDetails: {},
    proposedAt: 0,
    ...partial,
  };
}

function setBrokerMode(broker: BrokerOrderProposal["broker"], mode: "paper" | "live"): void {
  useBrokersStore.setState({
    byId: {
      [broker]: {
        broker,
        status: "connected",
        mode,
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

describe("OrderConfirmationDialog", () => {
  it("returns null when no active proposal is set", () => {
    const { container } = render(<OrderConfirmationDialog />);
    expect(container.firstChild).toBeNull();
  });

  it("renders the manual variant with Confirm enabled by default", async () => {
    setBrokerMode("alpaca", "paper");
    useOrdersStore.getState().addProposal(makeProposal({ source: "manual" }));
    useOrdersStore.getState().openProposal("p-1");
    render(<OrderConfirmationDialog />);
    await waitFor(() => {
      expect(screen.getByTestId("order-confirmation-dialog")).toBeInTheDocument();
    });
    expect(screen.getByTestId("order-confirmation-dialog").getAttribute("data-variant")).toBe(
      "manual",
    );
    const confirm = screen.getByTestId("confirm-button");
    expect(confirm).not.toBeDisabled();
    expect(screen.queryByTestId("ai-review-checkbox")).toBeNull();
    expect(screen.queryByTestId("ai-agent-banner")).toBeNull();
  });

  it("renders the AI variant with the banner, checkbox, and Confirm disabled", async () => {
    setBrokerMode("alpaca", "paper");
    useOrdersStore.getState().addProposal(
      makeProposal({
        proposalId: "p-ai",
        source: "ai-agent",
        sourceDetails: { agentId: "strategy-critic", agentName: "Strategy Critic" },
      }),
    );
    useOrdersStore.getState().openProposal("p-ai");
    render(<OrderConfirmationDialog />);
    await waitFor(() => {
      expect(screen.getByTestId("order-confirmation-dialog")).toBeInTheDocument();
    });
    expect(screen.getByTestId("order-confirmation-dialog").getAttribute("data-variant")).toBe("ai");
    expect(screen.getByTestId("ai-agent-banner").textContent).toContain("Strategy Critic");
    expect(screen.getByTestId("confirm-button")).toBeDisabled();

    const checkbox = screen.getByTestId("ai-review-checkbox") as HTMLInputElement;
    expect(checkbox.checked).toBe(false);

    await act(async () => {
      fireEvent.click(checkbox);
    });
    expect(screen.getByTestId("confirm-button")).not.toBeDisabled();
  });

  it("AI variant for workflow source labels the banner with the workflow id", async () => {
    setBrokerMode("alpaca", "paper");
    useOrdersStore.getState().addProposal(
      makeProposal({
        proposalId: "p-wf",
        source: "workflow",
        sourceDetails: { workflowId: "wf-rebalance", nodeId: "n-1" },
      }),
    );
    useOrdersStore.getState().openProposal("p-wf");
    render(<OrderConfirmationDialog />);
    await waitFor(() => {
      expect(screen.getByTestId("ai-agent-banner")).toBeInTheDocument();
    });
    expect(screen.getByTestId("ai-agent-banner").textContent).toContain("wf-rebalance");
  });

  it("confirming a manual order calls confirmProposal", async () => {
    setBrokerMode("alpaca", "paper");
    useOrdersStore.getState().addProposal(makeProposal({ source: "manual" }));
    useOrdersStore.getState().openProposal("p-1");
    fetchMock.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({
        proposalId: "p-1",
        broker: "alpaca",
        status: "filled",
        requestPayload: {},
        responsePayload: {},
        placedAt: 1,
      }),
    } as Response);
    render(<OrderConfirmationDialog />);
    const confirm = await screen.findByTestId("confirm-button");
    await act(async () => {
      fireEvent.click(confirm);
    });
    await waitFor(() => {
      expect(useOrdersStore.getState().findProposal("p-1")?.status).toBe("placed");
    });
  });

  it("declining the proposal updates status without throwing on sidecar error", async () => {
    setBrokerMode("alpaca", "paper");
    useOrdersStore.getState().addProposal(makeProposal({ source: "manual" }));
    useOrdersStore.getState().openProposal("p-1");
    fetchMock.mockResolvedValueOnce({ ok: false, status: 500 } as Response);
    render(<OrderConfirmationDialog />);
    const decline = await screen.findByRole("button", { name: /decline/i });
    await act(async () => {
      fireEvent.click(decline);
    });
    await waitFor(() => {
      expect(useOrdersStore.getState().findProposal("p-1")?.status).toBe("declined");
    });
  });

  it("triggers the live-order ack prompt when broker is in live mode and session ack missing", async () => {
    setBrokerMode("alpaca", "live");
    useOrdersStore.getState().addProposal(makeProposal({ source: "manual" }));
    useOrdersStore.getState().openProposal("p-1");
    render(<OrderConfirmationDialog />);
    const confirm = await screen.findByTestId("confirm-button");
    await act(async () => {
      fireEvent.click(confirm);
    });
    await waitFor(() => {
      expect(screen.getByTestId("live-order-ack-prompt")).toBeInTheDocument();
    });
  });

  it("skips the live-order ack prompt when session ack is present", async () => {
    setBrokerMode("alpaca", "live");
    useSafetyStore.setState({
      sessionAcks: [{ kind: "first-live-order-this-session", broker: "alpaca", ackedAt: 1 }],
    });
    useOrdersStore.getState().addProposal(makeProposal({ source: "manual" }));
    useOrdersStore.getState().openProposal("p-1");
    fetchMock.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({
        proposalId: "p-1",
        broker: "alpaca",
        status: "filled",
        requestPayload: {},
        responsePayload: {},
        placedAt: 1,
      }),
    } as Response);
    render(<OrderConfirmationDialog />);
    const confirm = await screen.findByTestId("confirm-button");
    await act(async () => {
      fireEvent.click(confirm);
    });
    await waitFor(() => {
      expect(useOrdersStore.getState().findProposal("p-1")?.status).toBe("placed");
    });
    expect(screen.queryByTestId("live-order-ack-prompt")).toBeNull();
  });
});
