import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { Editor } from "@tiptap/core";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/sidecar-client", () => ({
  getSidecarBaseUrl: vi.fn().mockResolvedValue("http://127.0.0.1:9000"),
}));

import { applyHostAction, describeHostAction } from "@/lib/host-actions";
import { useNotesStore } from "@/store/notes";
import { usePortfoliosStore } from "@/store/portfolios";
import { useSettingsStore } from "@/store/settings";
import { resetQuantStoreForTests } from "@/store/quant";
import { useSymbolsStore, DEFAULT_SYMBOLS } from "@/store/symbols";
import { useWorkspaceStore } from "@/store/workspace";
import { NotesPanel } from "@/modules/notes/NotesPanel";
import { BondPricerPanel } from "@/modules/quant/BondPricerPanel";
import { buildPortfolioSummary } from "@/modules/portfolio/metrics";
import type { Position, Quote } from "../types/data";

function editorOf(): Editor {
  return (document.querySelector(".ProseMirror") as unknown as { editor: Editor }).editor;
}
function md(): string {
  return (editorOf() as unknown as { getMarkdown: () => string }).getMarkdown();
}

describe("UI-001 fresh", () => {
  beforeEach(() => {
    useWorkspaceStore.setState({ openPanel: vi.fn() } as never);
  });
  afterEach(() => {
    cleanup();
    vi.useRealTimers();
    useNotesStore.setState({ general: "", bySymbol: {}, focusSymbol: "" });
    useSymbolsStore.setState({ entries: [...DEFAULT_SYMBOLS] });
  });
  async function mount() {
    const r = render(<NotesPanel />);
    await waitFor(() => expect(document.querySelector(".ProseMirror")).not.toBeNull());
    vi.useFakeTimers();
    return r;
  }
  it("agent write_note REPLACE into the open SYMBOL note shows, and a keystroke keeps it", async () => {
    useNotesStore.setState({ general: "", bySymbol: { NVDA: "old nvda view" }, focusSymbol: "NVDA" });
    await mount();
    expect(md()).toContain("old nvda view");
    act(() => {
      applyHostAction("write_note", { scope: "nvda", text: "Agent replaced.", mode: "replace" });
    });
    expect(md()).toContain("Agent replaced.");
    act(() => {
      editorOf().commands.insertContent("Z");
    });
    act(() => {
      vi.advanceTimersByTime(700);
    });
    const saved = useNotesStore.getState().bySymbol.NVDA;
    expect(saved).toContain("Agent replaced.");
    expect(saved).not.toContain("old nvda view");
    expect(saved).toContain("Z");
  });
  it("select-all + delete persists an empty note", async () => {
    useNotesStore.setState({ general: "to be cleared", bySymbol: {}, focusSymbol: "" });
    await mount();
    act(() => {
      editorOf().commands.selectAll();
      editorOf().commands.deleteSelection();
    });
    act(() => {
      vi.advanceTimersByTime(700);
    });
    expect(useNotesStore.getState().general).toBe("");
  });
  it("closing the panel inside the debounce window still saves", async () => {
    useNotesStore.setState({ general: "a", bySymbol: {}, focusSymbol: "" });
    const r = await mount();
    act(() => {
      editorOf().commands.insertContent("QQ");
    });
    r.unmount();
    expect(useNotesStore.getState().general).toContain("QQ");
  });
});

describe("FRONTEND-014 / AGENT-022 fresh", () => {
  it("write_note scope 'GLOBAL ' and 'General' land in General, never a ticker bucket", () => {
    useNotesStore.setState({ general: "", bySymbol: {}, focusSymbol: "" });
    applyHostAction("write_note", { scope: "GLOBAL ", text: "one" });
    applyHostAction("write_note", { scope: "General", text: "two" });
    const s = useNotesStore.getState();
    expect(Object.keys(s.bySymbol)).toEqual([]);
    expect(s.general).toContain("one");
    expect(s.general).toContain("two");
  });
  it("portfolio_add_position without cost: card says no price, apply adds nothing; cost 0 is shown", () => {
    usePortfoliosStore.getState().setAll([], undefined);
    const d = describeHostAction("portfolio_add_position", { symbol: "INFY.NS", quantity: 40 });
    console.log("card:", JSON.stringify(d));
    expect(JSON.stringify(d)).toMatch(/no price/i);
    applyHostAction("portfolio_add_position", { symbol: "INFY.NS", quantity: 40, cost_basis: "1500" });
    const holdings = usePortfoliosStore.getState().portfolios.flatMap((p) => p.holdings);
    expect(holdings.length).toBe(0);
    const d0 = describeHostAction("portfolio_add_position", { symbol: "INFY.NS", quantity: 40, cost_basis: 0 });
    console.log("card0:", JSON.stringify(d0));
    expect(JSON.stringify(d0)).toMatch(/@/);
  });
});

describe("PLATFORM-053 fresh", () => {
  const pos = (symbol: string, q: number, c: number): Position => ({ id: null, symbol, quantity: q, cost_basis: c, asset_class: "equity", opened_at: null, note: null });
  const quote = (symbol: string, price: number, currency: string): Quote => ({ symbol, price, change: 0, change_percent: 0, volume: null, currency, market_state: null, timestamp: "2026-09-26T00:00:00Z", provider: "t" } as unknown as Quote);
  it("JPY + EUR holdings -> concentration and weights null", () => {
    const s = buildPortfolioSummary([pos("7203.T", 100, 2500), pos("SAP.DE", 3, 200)], new Map([["7203.T", quote("7203.T", 2800, "JPY")], ["SAP.DE", quote("SAP.DE", 210, "EUR")]]));
    expect(s.mixedCurrencies).toBe(true);
    expect(s.concentration).toBeNull();
    expect(s.rows.every((r) => r.weight === null)).toBe(true);
  });
});

describe("DATA-100 fresh", () => {
  beforeEach(() => {
    resetQuantStoreForTests();
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 200, statusText: "OK", json: async () => ({ clean_price: 998.1, dirty_price: 1001.2, accrued_interest: 3.1, duration: 4, modified_duration: 3.9, convexity: 20, duration_ms: 1 }) }));
  });
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });
  it("region switched to IN while the panel is open -> prices still in $ ?", async () => {
    useSettingsStore.setState({ region: "US" });
    render(<BondPricerPanel />);
    act(() => {
      useSettingsStore.setState({ region: "IN" });
    });
    fireEvent.click(screen.getByTestId("price-bond"));
    await screen.findByTestId("bond-pricing-result");
    const txt = screen.getByTestId("bond-clean").textContent ?? "";
    console.log("after region switch:", txt, (screen.getByTestId("field-display-currency") as HTMLSelectElement).value);
    expect(txt).toContain("₹");
  });
});
