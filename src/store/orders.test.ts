import { beforeEach, describe, expect, it, vi } from "vitest";

import * as sidecarClient from "@/lib/sidecar-client";

import { resetOrdersStoreForTests, useOrdersStore } from "@/store/orders";

import type { BrokerOrderProposal, BrokerOrderResult } from "../../types/broker";

const baseUrl = "http://127.0.0.1:1234";

function stubSidecar(): void {
  vi.spyOn(sidecarClient, "getSidecarBaseUrl").mockResolvedValue(baseUrl);
}

function makeProposal(partial: Partial<BrokerOrderProposal>): BrokerOrderProposal {
  return {
    proposalId: "p-1",
    broker: "alpaca",
    accountId: "acc-1",
    symbol: "AAPL",
    side: "buy",
    type: "limit",
    quantity: 10,
    limitPrice: 100,
    currency: "USD",
    estimatedValue: 1000,
    source: "manual",
    sourceDetails: {},
    proposedAt: 1,
    ...partial,
  };
}

function makeResult(partial: Partial<BrokerOrderResult>): BrokerOrderResult {
  return {
    proposalId: "p-1",
    broker: "alpaca",
    brokerOrderId: "b-1",
    status: "filled",
    requestPayload: {},
    responsePayload: {},
    placedAt: 2,
    ...partial,
  };
}

function mockFetchSequence(responses: Array<{ ok: boolean; body: unknown }>): void {
  let i = 0;
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => {
      const r = responses[i] ?? { ok: false, body: {} };
      i += 1;
      return {
        ok: r.ok,
        status: r.ok ? 200 : 500,
        statusText: r.ok ? "OK" : "Error",
        json: async () => r.body,
      } as Response;
    }),
  );
}

describe("useOrdersStore", () => {
  beforeEach(() => {
    resetOrdersStoreForTests();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    stubSidecar();
  });

  it("addProposal adds and is idempotent on duplicate id", () => {
    const proposal = makeProposal({});
    useOrdersStore.getState().addProposal(proposal);
    useOrdersStore.getState().addProposal(proposal);
    expect(useOrdersStore.getState().proposals).toHaveLength(1);
  });

  it("selectors split manual vs AI proposals", () => {
    const a = makeProposal({ proposalId: "manual-1" });
    const b = makeProposal({
      proposalId: "ai-1",
      source: "ai-agent",
      sourceDetails: { agentId: "strategy-critic", agentName: "Strategy Critic" },
    });
    const c = makeProposal({
      proposalId: "wf-1",
      source: "workflow",
      sourceDetails: { workflowId: "wf-1" },
    });
    useOrdersStore.getState().addProposal(a);
    useOrdersStore.getState().addProposal(b);
    useOrdersStore.getState().addProposal(c);
    expect(useOrdersStore.getState().manualPendingProposals()).toHaveLength(1);
    expect(useOrdersStore.getState().aiPendingProposals()).toHaveLength(2);
    expect(useOrdersStore.getState().pendingProposals()).toHaveLength(3);
  });

  it("openProposal + closeProposal toggle activeProposalId", () => {
    useOrdersStore.getState().addProposal(makeProposal({ proposalId: "p-1" }));
    useOrdersStore.getState().openProposal("p-1");
    expect(useOrdersStore.getState().activeProposalId).toBe("p-1");
    useOrdersStore.getState().closeProposal();
    expect(useOrdersStore.getState().activeProposalId).toBeNull();
  });

  it("confirmProposal POSTs and updates status to placed", async () => {
    useOrdersStore.getState().addProposal(makeProposal({ proposalId: "p-1" }));
    mockFetchSequence([{ ok: true, body: makeResult({}) }]);
    const result = await useOrdersStore.getState().confirmProposal("p-1");
    expect(result.status).toBe("filled");
    expect(useOrdersStore.getState().findProposal("p-1")?.status).toBe("placed");
  });

  it("confirmProposal records the rejection on broker error", async () => {
    useOrdersStore.getState().addProposal(makeProposal({ proposalId: "p-1" }));
    mockFetchSequence([{ ok: false, body: { detail: "insufficient margin" } }]);
    await expect(useOrdersStore.getState().confirmProposal("p-1")).rejects.toThrow(
      /insufficient margin/,
    );
    expect(useOrdersStore.getState().findProposal("p-1")?.status).toBe("rejected");
    expect(useOrdersStore.getState().findProposal("p-1")?.error).toMatch(/insufficient/);
  });

  it("declineProposal marks the proposal declined even on sidecar error", async () => {
    useOrdersStore.getState().addProposal(makeProposal({ proposalId: "p-1" }));
    mockFetchSequence([{ ok: false, body: {} }]);
    await useOrdersStore.getState().declineProposal("p-1", "rejected by user");
    expect(useOrdersStore.getState().findProposal("p-1")?.status).toBe("declined");
  });

  it("removeProposal drops a resolved entry and clears activeProposalId when matched", () => {
    useOrdersStore.getState().addProposal(makeProposal({ proposalId: "p-1" }));
    useOrdersStore.getState().openProposal("p-1");
    useOrdersStore.getState().removeProposal("p-1");
    expect(useOrdersStore.getState().proposals).toHaveLength(0);
    expect(useOrdersStore.getState().activeProposalId).toBeNull();
  });

  it("AI proposals carry source=ai-agent for the dialog banner", () => {
    const proposal = makeProposal({
      proposalId: "ai-1",
      source: "ai-agent",
      sourceDetails: { agentId: "strategy-critic", agentName: "Strategy Critic" },
    });
    useOrdersStore.getState().addProposal(proposal);
    const found = useOrdersStore.getState().findProposal("ai-1");
    expect(found?.proposal.source).toBe("ai-agent");
    expect(found?.proposal.sourceDetails.agentName).toBe("Strategy Critic");
  });
});
