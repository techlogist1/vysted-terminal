import { writeFileSync } from "node:fs";
import { it, expect } from "vitest";
import { resetProposedChangesStoreForTests, useProposedChangesStore } from "@/store/proposed-changes";
import { useAgentAutonomyStore } from "@/store/agent-autonomy";
import { usePortfoliosStore } from "@/store/portfolios";
const OUT = "/Users/lokavyasingh/Documents/dev/vysted-terminal/docs/redesign/verification/r15/final-pass/reproof/gate8/G8-3-harness.json";
const B = "http://127.0.0.1:52895";
const acks: unknown[] = [];
const realFetch = globalThis.fetch;
globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
  const url = String(input instanceof Request ? input.url : input);
  if (url.includes("/agents/actions/ack")) acks.push(init?.body ? JSON.parse(String(init.body)) : null);
  return realFetch(input, init);
}) as typeof fetch;
const j = async (p: string) => (await realFetch(B + p)).text();
const rows: unknown[] = [];
it("G8-3 order-shaped and malformed writes fail closed (ask, auto)", async () => {
  resetProposedChangesStoreForTests();
  usePortfoliosStore.getState().setAll([]);
  const pid = usePortfoliosStore.getState().createPortfolio("RP");
  usePortfoliosStore.getState().setActive(pid);
  usePortfoliosStore.getState().addHolding(pid, { symbol: "TCS.NS", quantity: 4, costBasis: 3300, assetClass: "equity" });
  const cases = [
    { name: "place_order", input: { symbol: "RELIANCE", side: "buy", quantity: 10, order_type: "market" } },
    { name: "submit_order", input: { symbol: "INFY", side: "buy", quantity: 5, order_type: "limit", limit_price: 1400 } },
    { name: "portfolio_add_position", input: { symbol: "INFY", quantity: "five", cost_basis: -1 } },
    { name: "portfolio_update_position", input: { position_id: "does-not-exist", quantity: 0 } },
  ];
  for (const autonomy of ["ask", "auto"] as const) {
    useAgentAutonomyStore.setState({ autonomy });
    for (const [i, c] of cases.entries()) {
      const store0 = JSON.stringify(usePortfoliosStore.getState().portfolios);
      const pos0 = await j("/portfolio/positions"); const ws0 = await j("/workspace");
      acks.length = 0;
      const { id, outcome } = useProposedChangesStore.getState().enqueue({ toolCallId: `rp-${autonomy}-${i}`, name: c.name, input: c.input, batchId: `rp-${autonomy}` });
      const enq = await outcome;
      const ch0 = useProposedChangesStore.getState().changes.find((x) => x.id === id)!;
      const st0 = { kind: ch0.kind, status: ch0.status, title: ch0.title, detail: ch0.detail ?? null };
      const acc = await useProposedChangesStore.getState().accept(id);
      await new Promise((r) => setTimeout(r, 400));
      const ch = useProposedChangesStore.getState().changes.find((x) => x.id === id)!;
      const row = { autonomy, tool: c.name, input: c.input, enqueueOutcome: enq, afterEnqueue: st0, humanAccept: acc, statusAfter: ch.status, detail: ch.detail ?? null,
        storeUnchanged: store0 === JSON.stringify(usePortfoliosStore.getState().portfolios),
        positionsUnchanged: pos0 === (await j("/portfolio/positions")), workspaceBlobsUnchanged: ws0 === (await j("/workspace")), acks: [...acks] };
      rows.push(row); writeFileSync(OUT, JSON.stringify(rows, null, 1));
      expect(enq).not.toBe("applied");
      expect(acc).toBe("failed");
      expect(ch.status).toBe("pending");
      expect(ch.detail).toBeTruthy();
      expect(row.storeUnchanged && row.positionsUnchanged && row.workspaceBlobsUnchanged).toBe(true);
    }
  }
});
