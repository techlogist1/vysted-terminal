import { beforeEach, describe, expect, it, vi } from "vitest";

// The diff gate's apply side effects live in `@/lib/host-actions`; mock them so
// this suite tests the gate's state machine (stage → accept/reject →
// apply-once) in isolation. `host-actions.test.ts` covers the real apply.
const { applyHostActionMock, describeHostActionMock, ackHostActionMock } = vi.hoisted(() => ({
  applyHostActionMock: vi.fn<
    (name: string, input: Record<string, unknown>) => Promise<string | null>
  >(async () => "applied"),
  describeHostActionMock: vi.fn((name: string) => ({
    kind: name.startsWith("portfolio_")
      ? "data-write"
      : name === "set_chart_symbol"
        ? "chart"
        : "panel",
    title: `do ${name}`,
    before: "before",
    after: "after",
  })),
  ackHostActionMock: vi.fn(),
}));

vi.mock("@/lib/host-actions", () => ({
  // The gate applies through the ASYNC seam (network-backed cases await).
  applyHostActionAsync: applyHostActionMock,
  describeHostAction: describeHostActionMock,
  ackHostAction: ackHostActionMock,
  hostActionAckDetail: (name: string, input: Record<string, unknown>) => ({
    action: name,
    ...(typeof input.symbol === "string" && input.symbol ? { symbol: input.symbol } : {}),
    ...(typeof input.panel === "string" && input.panel ? { panel: input.panel } : {}),
  }),
  publishAckStatus: (label: string | null) =>
    label === null ? "failed" : label.startsWith("Kept") ? "kept_previous" : "applied",
}));

import { resetAgentAutonomyStoreForTests, useAgentAutonomyStore } from "@/store/agent-autonomy";
import { resetBriefStoreForTests, useBriefStore } from "@/store/brief";
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
    ackHostActionMock.mockClear();
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

  it("accept applies a mutation exactly once and marks it accepted", async () => {
    const id = enqueue("set_chart_symbol", { symbol: "NVDA" });
    await useProposedChangesStore.getState().accept(id);
    expect(applyHostActionMock).toHaveBeenCalledTimes(1);
    expect(applyHostActionMock).toHaveBeenCalledWith("set_chart_symbol", { symbol: "NVDA" });
    expect(useProposedChangesStore.getState().changes[0].status).toBe("accepted");
    // A second accept is a no-op (no double-apply).
    await useProposedChangesStore.getState().accept(id);
    expect(applyHostActionMock).toHaveBeenCalledTimes(1);
  });

  it("reject leaves cockpit state unchanged — nothing is applied", () => {
    const id = enqueue("add_to_watchlist", { symbol: "TSLA" });
    useProposedChangesStore.getState().reject(id);
    expect(applyHostActionMock).not.toHaveBeenCalled();
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

  // --- autonomy (item 7) — AUTO auto-applies every kind; ASK gates everything ---

  it("ASK mode (default) leaves a change pending — no auto-apply", () => {
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

  it("AUTO mode applies a tracked-portfolio data-write on enqueue too (no exempt kind)", async () => {
    useAgentAutonomyStore.getState().setAutonomy("auto");
    enqueue("portfolio_add_position", { symbol: "AAPL", quantity: 1 });
    await Promise.resolve(); // flush the void accept() microtask
    expect(applyHostActionMock).toHaveBeenCalledWith("portfolio_add_position", {
      symbol: "AAPL",
      quantity: 1,
    });
    expect(useProposedChangesStore.getState().changes[0].kind).toBe("data-write");
    expect(useProposedChangesStore.getState().changes[0].status).toBe("accepted");
  });

  // --- publish read-back + lifecycle settlement (R10 D39) --------------------

  it("acks a publish_brief accept with the apply outcome (read-back, D39 §4)", async () => {
    ackHostActionMock.mockClear();
    applyHostActionMock.mockResolvedValueOnce("Published the DEEP research brief");
    const id = enqueue("publish_brief", { markdown: "## x" });
    await useProposedChangesStore.getState().accept(id);
    expect(ackHostActionMock).toHaveBeenCalledWith("tc-publish_brief", "applied", {
      action: "publish_brief",
    });
  });

  it("acks kept_previous when the apply kept the richer brief", async () => {
    ackHostActionMock.mockClear();
    applyHostActionMock.mockResolvedValueOnce("Kept the richer research brief already on screen");
    const id = enqueue("publish_brief", { markdown: "## x" });
    await useProposedChangesStore.getState().accept(id);
    expect(ackHostActionMock).toHaveBeenCalledWith("tc-publish_brief", "kept_previous", {
      action: "publish_brief",
    });
  });

  it("acks failed when the publish could not apply", async () => {
    ackHostActionMock.mockClear();
    applyHostActionMock.mockResolvedValueOnce(null);
    const id = enqueue("publish_brief", {});
    await useProposedChangesStore.getState().accept(id);
    expect(ackHostActionMock).toHaveBeenCalledWith("tc-publish_brief", "failed", {
      action: "publish_brief",
    });
  });

  it("acks EVERY host action on accept — not just publish_brief (R13 JARVIS 1a)", async () => {
    ackHostActionMock.mockClear();
    applyHostActionMock.mockResolvedValueOnce("Loaded SPY into the chart");
    const id = enqueue("set_chart_symbol", { symbol: "SPY" });
    await useProposedChangesStore.getState().accept(id);
    expect(ackHostActionMock).toHaveBeenCalledWith("tc-set_chart_symbol", "applied", {
      action: "set_chart_symbol",
      symbol: "SPY",
    });
  });

  it("acks a rejected host action as failed (R13 JARVIS 1a)", () => {
    ackHostActionMock.mockClear();
    const id = enqueue("open_panel", { panel: "news" });
    useProposedChangesStore.getState().reject(id);
    expect(ackHostActionMock).toHaveBeenCalledWith("tc-open_panel", "failed", {
      action: "open_panel",
      panel: "news",
    });
  });

  it("rejecting a publish_brief settles an in-flight brief run (archived run_failed)", () => {
    resetBriefStoreForTests();
    useBriefStore.getState().setBrief({
      query: "prior",
      mode: "FAST",
      markdown: "## prior",
      sources: [],
      sourceCount: 0,
      webAvailable: false,
      createdAt: Date.now(),
    });
    useBriefStore.getState().beginRun({ runId: "run-1", query: "next", depth: "deep" });
    const id = enqueue("publish_brief", { markdown: "## next" });
    useProposedChangesStore.getState().reject(id);
    const panel = useBriefStore.getState().panel;
    expect(panel.phase).toBe("archived");
    expect(panel.phase === "archived" && panel.reason).toBe("run_failed");
    expect(useBriefStore.getState().brief?.query).toBe("prior");
    resetBriefStoreForTests();
  });
});
