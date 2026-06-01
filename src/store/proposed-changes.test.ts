import { beforeEach, describe, expect, it, vi } from "vitest";

// The diff gate's apply/route side effects live in `@/lib/host-actions`; mock
// them so this suite tests the gate's state machine (stage → accept/reject →
// apply-once) in isolation. `host-actions.test.ts` covers the real apply.
const { applyHostActionMock, routeOrderProposalMock, describeHostActionMock } = vi.hoisted(() => ({
  applyHostActionMock: vi.fn<(name: string, input: Record<string, unknown>) => string | null>(
    () => "applied",
  ),
  routeOrderProposalMock: vi.fn<() => Promise<{ ok: boolean; error?: string }>>(async () => ({
    ok: true,
  })),
  describeHostActionMock: vi.fn((name: string) => ({
    kind: name === "propose_order" ? "order" : name === "set_chart_symbol" ? "chart" : "panel",
    title: `do ${name}`,
    before: "before",
    after: "after",
  })),
}));

vi.mock("@/lib/host-actions", () => ({
  applyHostAction: applyHostActionMock,
  routeOrderProposal: routeOrderProposalMock,
  describeHostAction: describeHostActionMock,
}));

import { resetAgentAutonomyStoreForTests, useAgentAutonomyStore } from "@/store/agent-autonomy";
import {
  resetProposedChangesStoreForTests,
  useProposedChangesStore,
} from "@/store/proposed-changes";

function enqueue(name: string, input: Record<string, unknown> = {}, batchId = "batch-1"): string {
  return useProposedChangesStore.getState().enqueue({
    toolCallId: `tc-${name}`,
    name,
    input,
    batchId,
  });
}

describe("proposed-changes store — the diff/accept trust gate (FR-010)", () => {
  beforeEach(() => {
    resetProposedChangesStoreForTests();
    resetAgentAutonomyStoreForTests();
    applyHostActionMock.mockClear();
    routeOrderProposalMock.mockClear();
  });

  it("enqueue stages a pending change with the described old→new diff", () => {
    const id = enqueue("open_panel", { panel: "news" });
    const change = useProposedChangesStore.getState().changes.find((c) => c.id === id);
    expect(change).toMatchObject({
      status: "pending",
      kind: "panel",
      title: "do open_panel",
      before: "before",
      after: "after",
      action: { name: "open_panel", input: { panel: "news" } },
    });
    // Nothing is applied at stage time.
    expect(applyHostActionMock).not.toHaveBeenCalled();
  });

  it("accept applies a non-order mutation exactly once and marks it accepted", async () => {
    const id = enqueue("set_chart_symbol", { symbol: "NVDA" });
    await useProposedChangesStore.getState().accept(id);
    expect(applyHostActionMock).toHaveBeenCalledTimes(1);
    expect(applyHostActionMock).toHaveBeenCalledWith("set_chart_symbol", { symbol: "NVDA" });
    expect(useProposedChangesStore.getState().changes[0].status).toBe("accepted");
    // A second accept is a no-op (no double-apply).
    await useProposedChangesStore.getState().accept(id);
    expect(applyHostActionMock).toHaveBeenCalledTimes(1);
  });

  it("accept routes an ORDER through the §6.5 path, never a direct apply (FR-011)", async () => {
    const id = enqueue("propose_order", { symbol: "AAPL", side: "buy", quantity: 1 });
    await useProposedChangesStore.getState().accept(id);
    expect(routeOrderProposalMock).toHaveBeenCalledTimes(1);
    expect(applyHostActionMock).not.toHaveBeenCalled();
    expect(useProposedChangesStore.getState().changes[0].status).toBe("accepted");
  });

  it("re-pends an order whose §6.5 route fails, surfacing the error (no silent accept)", async () => {
    routeOrderProposalMock.mockResolvedValueOnce({ ok: false, error: "kill switch fired" });
    const id = enqueue("propose_order", { symbol: "AAPL", side: "buy", quantity: 1 });
    await useProposedChangesStore.getState().accept(id);
    const change = useProposedChangesStore.getState().changes[0];
    expect(change.status).toBe("pending");
    expect(change.detail).toBe("kill switch fired");
  });

  it("reject leaves cockpit state unchanged — nothing is applied", () => {
    const id = enqueue("add_to_watchlist", { symbol: "TSLA" });
    useProposedChangesStore.getState().reject(id);
    expect(applyHostActionMock).not.toHaveBeenCalled();
    expect(routeOrderProposalMock).not.toHaveBeenCalled();
    expect(useProposedChangesStore.getState().changes[0].status).toBe("rejected");
  });

  it("acceptBatch applies every pending change in one turn, in order", async () => {
    enqueue("open_panel", { panel: "chart" }, "turn-A");
    enqueue("set_chart_symbol", { symbol: "MSFT" }, "turn-A");
    enqueue("open_panel", { panel: "news" }, "turn-B");
    await useProposedChangesStore.getState().acceptBatch("turn-A");
    expect(applyHostActionMock).toHaveBeenCalledTimes(2);
    const byBatchB = useProposedChangesStore.getState().pendingInBatch("turn-B");
    expect(byBatchB).toHaveLength(1); // turn-B untouched
  });

  it("rejectAll rejects every pending change without applying", () => {
    enqueue("open_panel", { panel: "chart" });
    enqueue("add_to_watchlist", { symbol: "QQQ" });
    useProposedChangesStore.getState().rejectAll();
    expect(useProposedChangesStore.getState().pending()).toHaveLength(0);
    expect(applyHostActionMock).not.toHaveBeenCalled();
  });

  // --- autonomy (item 7) — AUTO auto-applies non-order; ASK gates everything ---

  it("ASK mode (default) leaves a non-order change pending — no auto-apply", () => {
    useAgentAutonomyStore.getState().setAutonomy("ask");
    enqueue("set_chart_symbol", { symbol: "NVDA" });
    expect(applyHostActionMock).not.toHaveBeenCalled();
    expect(useProposedChangesStore.getState().pending()).toHaveLength(1);
  });

  it("AUTO mode applies a UI/chart/watchlist change on enqueue, no manual accept", async () => {
    useAgentAutonomyStore.getState().setAutonomy("auto");
    enqueue("set_chart_symbol", { symbol: "NVDA" });
    await Promise.resolve(); // flush the void accept() microtask
    expect(applyHostActionMock).toHaveBeenCalledTimes(1);
    expect(applyHostActionMock).toHaveBeenCalledWith("set_chart_symbol", { symbol: "NVDA" });
    expect(useProposedChangesStore.getState().changes[0].status).toBe("accepted");
  });

  it("AUTO mode NEVER auto-applies an ORDER — it stays gated (hard safety line)", async () => {
    useAgentAutonomyStore.getState().setAutonomy("auto");
    enqueue("propose_order", { symbol: "AAPL", side: "buy", quantity: 1 });
    await Promise.resolve();
    // The order is NOT auto-accepted: no route, no apply, still pending for the
    // explicit §6.5 confirm path. `auto` changes friction, not safety.
    expect(routeOrderProposalMock).not.toHaveBeenCalled();
    expect(applyHostActionMock).not.toHaveBeenCalled();
    expect(useProposedChangesStore.getState().changes[0].status).toBe("pending");
  });
});
