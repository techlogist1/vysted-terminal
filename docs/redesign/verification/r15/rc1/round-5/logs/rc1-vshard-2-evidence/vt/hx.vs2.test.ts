import { afterAll, describe, expect, it, vi } from "vitest";
vi.mock("@/lib/sidecar-client", () => ({
  getSidecarBaseUrl: () => Promise.resolve("http://127.0.0.1:1"),
  sidecarGet: vi.fn(),
}));
import { writeFileSync } from "node:fs";
import { describeHostAction, parseHostAction, describeIntent, applyIntentAsync, undoPreImage } from "@/lib/host-actions";
import { useScreenerStore } from "@/store/screener";
import { usePortfoliosStore } from "@/store/portfolios";
import { useWorkspaceStore } from "@/store/workspace";
import { useSettingsStore } from "@/store/settings";
import { useProposedChangesStore, resetProposedChangesStoreForTests } from "@/store/proposed-changes";

const out: Record<string, unknown> = {};
afterAll(() => writeFileSync(__dirname + "/hx.json", JSON.stringify(out, null, 1)));
vi.stubGlobal("fetch", vi.fn(async () => ({ ok: true, json: async () => ({}) })) as unknown as typeof fetch);

async function propose(name: string, input: Record<string, unknown>) {
  const { id } = useProposedChangesStore.getState().enqueue({ toolCallId: `tc-${Math.random()}`, name, input, batchId: "b", agentId: "a", agentName: "A" } as never);
  const ch = useProposedChangesStore.getState().changes.find((c) => c.id === id)!;
  const outcome = await useProposedChangesStore.getState().accept(id);
  const after = useProposedChangesStore.getState().changes.find((c) => c.id === id)!;
  return { diffBefore: ch.before, diffAfter: ch.after, outcome, detail: after.detail ?? null, preImage: after.preImage ?? null };
}

describe("CODE-FRONTEND-009 fresh", () => {
  it("nested group + formula saved; draft side-effect recorded", async () => {
    resetProposedChangesStoreForTests();
    useScreenerStore.getState().__resetForTests();
    useWorkspaceStore.setState({ openPanel: vi.fn(), dockviewApi: null } as never);
    // user's own on-screen draft
    useScreenerStore.getState().applyFilters({ criteria: [{ field: "dividend_yield", operator: "gt", value: 0.03 }] as never, group: null, universe: "nifty50" as never, formula: "roe > 0.2" });
    const draftBefore = (({ criteria, formula, universe }) => ({ criteria, formula, universe }))(useScreenerStore.getState());
    const input = {
      name: "Quality growth",
      group: { combinator: "and", criteria: [{ field: "roe", operator: "gt", value: 0.15 }, { combinator: "or", criteria: [{ field: "pe_ratio", operator: "lt", value: 25 }, { field: "revenue_growth", operator: "gt", value: 0.1 }] }] },
      formula: "debt_to_equity < 1",
      criteria: [{ field: "bogus_field", operator: "zz", value: 1 }],
    };
    const r1 = await propose("save_screen", input);
    const saved1 = useScreenerStore.getState().savedScreens.find((s) => s.name === "Quality growth");
    const draftAfter = (({ criteria, formula, universe, group, advanced }) => ({ criteria, formula, universe, group, advanced }))(useScreenerStore.getState());
    // same name, different case, then exact same name
    const r2 = await propose("save_screen", { name: "quality growth", criteria: [{ field: "pe_ratio", operator: "lt", value: 12 }] });
    const r3 = await propose("save_screen", { name: "Quality growth", criteria: [{ field: "pe_ratio", operator: "lt", value: 9 }] });
    const names = useScreenerStore.getState().savedScreens.map((s) => s.name);
    const saved3 = useScreenerStore.getState().savedScreens.find((s) => s.name === "Quality growth");
    // undo the replace
    const undo = r3.preImage ? undoPreImage(r3.preImage as never) : null;
    const savedUndo = useScreenerStore.getState().savedScreens.find((s) => s.name === "Quality growth");
    const draftAfterUndo = (({ criteria, formula, universe }) => ({ criteria, formula, universe }))(useScreenerStore.getState());
    out.f009 = { r1, saved1, draftBefore, draftAfter, r2, r3, names, saved3, undo: undo?.label, savedUndo, draftAfterUndo };
    expect(saved1?.group).toBeTruthy();
    expect(saved1?.formula).toBe("debt_to_equity < 1");
    expect(r3.diffAfter).toMatch(/replaced/);
    expect(saved3?.criteria).toEqual([{ field: "pe_ratio", operator: "lt", value: 9 }]);
  });
});

describe("CODE-FRONTEND-010 fresh", () => {
  it("run:true nested group runs once with the new state; run:'true' string and malformed do not", async () => {
    resetProposedChangesStoreForTests();
    useScreenerStore.getState().__resetForTests();
    const real = useScreenerStore.getState().runScreener;
    const seen: unknown[] = [];
    const runScreener = vi.fn(async () => { const s = useScreenerStore.getState(); seen.push({ group: s.group, advanced: s.advanced, formula: s.formula, universe: s.universe }); return null; });
    useScreenerStore.setState({ runScreener });
    useWorkspaceStore.setState({ openPanel: vi.fn(), dockviewApi: null } as never);
    const nested = { group: { combinator: "or", criteria: [{ field: "roe", operator: "gt", value: 0.2 }, { combinator: "and", criteria: [{ field: "pe_ratio", operator: "lt", value: 10 }, { field: "dividend_yield", operator: "gt", value: 0.04 }] }] }, universe: "nifty50", run: true };
    const a = await propose("write_screener_filters", nested);
    const callsA = runScreener.mock.calls.length;
    const b = await propose("write_screener_filters", { criteria: [{ field: "roe", operator: "gt", value: 0.1 }], run: "true" });
    const callsB = runScreener.mock.calls.length;
    const c = await propose("write_screener_filters", { criteria: [{ field: "nope", operator: "??", value: 1 }], run: true });
    const callsC = runScreener.mock.calls.length;
    const d = await propose("write_screener_filters", { formula: "roe > 0.3", run: true });
    const callsD = runScreener.mock.calls.length;
    useScreenerStore.setState({ runScreener: real });
    out.f010 = { a, callsA, b, callsB, c, callsC, d, callsD, seen };
    expect(callsA).toBe(1);
    expect(callsB).toBe(1);
    expect(callsC).toBe(1);
    expect(callsD).toBe(2);
  });
});

describe("CODE-FRONTEND-011 fresh", () => {
  function ws(openIds: string[]) {
    const mk = (id: string) => ({ id, api: { component: `${id}-panel`, close: vi.fn(), setActive: vi.fn() } });
    const panels = openIds.map(mk);
    useWorkspaceStore.setState({ openPanel: vi.fn(), dockviewApi: { panels, getPanel: (id: string) => panels.find((p) => p.api.component === `${id}-panel`), toJSON: () => ({}) } } as never);
    return panels;
  }
  it("parity table on fresh inputs", async () => {
    resetProposedChangesStoreForTests();
    usePortfoliosStore.getState().setAll([
      { id: "P1", name: "Main", holdings: [{ id: "h-1", symbol: "HDFCBANK", quantity: 7, costBasis: 1500, assetClass: "equity" }, { id: "h-2", symbol: "HDFCBANK", quantity: 3, costBasis: 1650, assetClass: "equity" }] },
    ] as never);
    const rows: Record<string, unknown> = {};
    ws(["chart"]);
    rows.update_cost_only_lot2 = await propose("portfolio_update_position", { position_id: "h-2", cost_basis: 1720 });
    rows.lot2_after = usePortfoliosStore.getState().portfolios?.[0]?.holdings ?? usePortfoliosStore.getState();
    rows.update_qty_only = await propose("portfolio_update_position", { position_id: "h-1", quantity: 9 });
    // target gone between enqueue and accept
    const { id } = useProposedChangesStore.getState().enqueue({ toolCallId: "tc-gone", name: "portfolio_update_position", input: { position_id: "h-1", cost_basis: 1400 }, batchId: "b", agentId: "a", agentName: "A" } as never);
    usePortfoliosStore.getState().removeHolding("P1", "h-1");
    const outcome = await useProposedChangesStore.getState().accept(id);
    rows.update_target_gone = { outcome, detail: useProposedChangesStore.getState().changes.find((c) => c.id === id)?.detail };
    rows.close_screener_not_open = await propose("close_panel", { panel: "screener" });
    const p = ws(["chart", "screener"]);
    rows.close_screener_open = { ...(await propose("close_panel", { panel: "Screener" })), closeCalls: (p[1].api.close as ReturnType<typeof vi.fn>).mock.calls.length };
    rows.open_chart_already_open = await propose("open_panel", { panel: "chart" });
    ws([]);
    rows.open_unknown = await propose("open_panel", { panel: "warp-drive" });
    const regionBefore = useSettingsStore.getState().region;
    rows.set_region_EU = await propose("set_region", { region: "EU" });
    rows.set_region_blank = await propose("set_region", { region: "" });
    rows.region_unchanged = useSettingsStore.getState().region === regionBefore;
    rows.unknown_action = describeIntent(parseHostAction("teleport_user", {}));
    out.f011 = rows;
    const u = rows.update_cost_only_lot2 as { diffAfter: string; outcome: string };
    expect(u.diffAfter).toMatch(/×3 @/);
    expect(rows.update_target_gone).toMatchObject({ outcome: "failed" });
    expect((rows.close_screener_open as { closeCalls: number }).closeCalls).toBe(1);
  });
});
