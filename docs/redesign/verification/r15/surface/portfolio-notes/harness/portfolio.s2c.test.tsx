import { vi, test } from "vitest";
import fs from "fs";
import { render, screen, fireEvent, cleanup, act } from "@testing-library/react";

const SCR = "/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/s2c";
const PORT = 52221;
window.history.replaceState({}, "", `/?sidecar-port=${PORT}`);

const csvCaptured: { name: string; content: string }[] = [];
vi.mock("@/lib/csv", async (orig) => {
  const real = (await orig()) as Record<string, unknown>;
  return { ...real, downloadCsv: vi.fn((name: string, content: string) => { csvCaptured.push({ name, content }); }) };
});

import { usePortfoliosStore } from "@/store/portfolios";
import { useSettingsStore } from "@/store/settings";
import { usePanelContextBus } from "@/store/panel-context";
import { PortfolioPanel } from "@/modules/portfolio/PortfolioPanel";
import { captureTerminalState } from "@/modules/chat/context-provider";
import { applyHostActionAsync, describeHostAction } from "@/lib/host-actions";

const OUT = `${SCR}/out/portfolio-replay.json`;
const log: Record<string, unknown> = {};
const realFetch = globalThis.fetch;
const netlog: { t: number; method: string; url: string; status: number | string; ms: number; body?: unknown }[] = [];
let inflight = 0;
let failQuotes = false;
globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
  const url = String(input);
  const t0 = Date.now();
  inflight++;
  try {
    if (failQuotes && url.includes("/quotes")) throw new TypeError("Failed to fetch (induced)");
    const r = await realFetch(input as any, init);
    netlog.push({ t: t0, method: init?.method ?? "GET", url: url.replace(/^http:\/\/127\.0\.0\.1:\d+/, ""), status: r.status, ms: Date.now() - t0, ...(init?.body ? { body: JSON.parse(String(init.body)) } : {}) });
    return r;
  } catch (e) {
    netlog.push({ t: t0, method: init?.method ?? "GET", url: url.replace(/^http:\/\/127\.0\.0\.1:\d+/, ""), status: String(e), ms: Date.now() - t0 });
    throw e;
  } finally { inflight--; }
}) as typeof fetch;

async function settle(maxMs = 180000) {
  const t0 = Date.now();
  await act(async () => { await new Promise((r) => setTimeout(r, 50)); });
  while (Date.now() - t0 < maxMs) {
    await act(async () => { await new Promise((r) => setTimeout(r, 200)); });
    if (inflight === 0) { await act(async () => { await new Promise((r) => setTimeout(r, 100)); }); if (inflight === 0) break; }
  }
  return Date.now() - t0;
}
const text = (el: Element) => (el.textContent ?? "").replace(/\s+/g, " ").trim();
function save(label: string, v: unknown) { log[label] = v; fs.writeFileSync(OUT, JSON.stringify(log, null, 1)); }
function reset() {
  usePortfoliosStore.setState({ portfolios: [{ id: "default", name: "Portfolio", holdings: [] }], activeId: "default" });
  usePanelContextBus.setState({ lastEventBySource: {}, focusedSource: null, updatedAt: 0 } as any);
}
async function addViaForm(symbol: string, qty: string, cost: string, cls: "equity" | "crypto" = "equity", note = "") {
  fireEvent.change(screen.getByLabelText("Symbol"), { target: { value: symbol } });
  fireEvent.change(screen.getByLabelText("Quantity"), { target: { value: qty } });
  fireEvent.change(screen.getByLabelText("Cost basis"), { target: { value: cost } });
  fireEvent.change(screen.getByLabelText("Asset class"), { target: { value: cls } });
  fireEvent.change(screen.getByLabelText("Note"), { target: { value: note } });
  await act(async () => { fireEvent.submit(screen.getByLabelText("Symbol").closest("form")!); });
}
const active = () => { const s = usePortfoliosStore.getState(); return s.portfolios.find((p) => p.id === s.activeId)!; };
const summaryLine = (c: Element) => { const t = text(c); const i = t.indexOf("Market value:"); return i < 0 ? null : t.slice(i, i + 260); };

test("P1 empty portfolio", async () => {
  reset();
  useSettingsStore.getState().setRegion?.("IN" as any);
  const { container } = render(<PortfolioPanel />);
  await settle();
  const exportBtn = screen.getByLabelText("Export portfolio to CSV") as HTMLButtonElement;
  save("P1-empty", { panelText: text(container), exportDisabled: exportBtn.disabled, net: netlog.length });
  cleanup();
});

test("P2 form validation", async () => {
  reset();
  const { container } = render(<PortfolioPanel />);
  const out: Record<string, unknown> = {};
  for (const [label, s, q, c] of [["empty", "", "", ""], ["qty0", "TCS.NS", "0", "100"], ["negcost", "TCS.NS", "5", "-1"], ["qtyabc", "TCS.NS", "abc", "100"], ["qty-neg", "TCS.NS", "-3", "100"], ["qty-1e20", "TCS.NS", "1e20", "100"], ["cost-blank", "TCS.NS", "5", ""], ["qty-comma", "TCS.NS", "1,000", "100"]] as const) {
    await addViaForm(s, q, c);
    const err = container.querySelector("p.text-negative");
    out[label] = { error: err ? err.textContent : null, holdings: active().holdings.map((h) => [h.symbol, h.quantity, h.costBasis]) };
    usePortfoliosStore.setState({ portfolios: [{ id: "default", name: "Portfolio", holdings: [] }], activeId: "default" });
  }
  save("P2-validation", out);
  cleanup();
});

test("P3 INR-only portfolio, P&L math vs independent quotes", async () => {
  reset();
  const { container } = render(<PortfolioPanel />);
  await addViaForm("RELIANCE.NS", "10", "1200");
  await addViaForm("TCS.NS", "5", "2500");
  const ms = await settle();
  const ref: Record<string, number> = {};
  for (const s of ["RELIANCE.NS", "TCS.NS"]) { const r = await realFetch(`http://127.0.0.1:${PORT}/quotes/${s}?asset_class=equity`); ref[s] = (await r.json()).price; }
  const mv = ref["RELIANCE.NS"] * 10 + ref["TCS.NS"] * 5; const cost = 12000 + 12500; const pnl = mv - cost;
  const rows = Array.from(container.querySelectorAll('[data-testid="portfolio-holdings-table"] [role="row"], [data-testid="portfolio-holdings-table"] tr')).map(text);
  save("P3-inr", { settleMs: ms, ref, expected: { mv, pnl, pnlPct: (pnl / cost) * 100, wRel: ref["RELIANCE.NS"] * 10 / mv }, summary: summaryLine(container), rows, bus: captureTerminalState().portfolio });
  cleanup();
});

test("P4 stale-closure: delete/edit after switching to a portfolio created after mount", async () => {
  reset();
  const { container } = render(<PortfolioPanel />);
  await addViaForm("RELIANCE.NS", "10", "1200");
  await settle();
  // create a second portfolio through the header UI
  fireEvent.click(screen.getByLabelText("New portfolio"));
  fireEvent.change(screen.getByLabelText("New portfolio name"), { target: { value: "Second" } });
  await act(async () => { fireEvent.click(screen.getByLabelText("Confirm")); });
  await addViaForm("TCS.NS", "5", "2500");
  await settle();
  const before = { active: active().name, holdings: active().holdings.map((h) => h.symbol) };
  await act(async () => { fireEvent.click(screen.getByLabelText("Delete TCS.NS")); });
  const afterDelete = { active: active().name, holdings: active().holdings.map((h) => h.symbol), all: usePortfoliosStore.getState().portfolios.map((p) => [p.name, p.holdings.map((h) => h.symbol)]) };
  // Edit path in the second portfolio
  await act(async () => { fireEvent.click(screen.getByLabelText("Edit TCS.NS")); });
  fireEvent.change(screen.getByLabelText("Quantity"), { target: { value: "7" } });
  await act(async () => { fireEvent.submit(screen.getByLabelText("Symbol").closest("form")!); });
  const afterEdit = active().holdings.map((h) => [h.symbol, h.quantity]);
  // Switch back to the first portfolio via the select and delete there (control)
  const sel = screen.getByLabelText("Active portfolio") as HTMLSelectElement;
  await act(async () => { fireEvent.change(sel, { target: { value: "default" } }); });
  await settle();
  await act(async () => { fireEvent.click(screen.getByLabelText("Delete RELIANCE.NS")); });
  const controlDelete = active().holdings.map((h) => h.symbol);
  save("P4-stale-closure", { before, afterDelete, afterEdit, controlDeleteInFirstPortfolio: controlDelete, panelText: text(container).slice(0, 400) });
  cleanup();
});

test("P4b fresh mount on the second portfolio (control for P4)", async () => {
  const s = usePortfoliosStore.getState();
  const second = s.portfolios.find((p) => p.name === "Second");
  if (!second) { save("P4b", "no second portfolio"); return; }
  usePortfoliosStore.getState().setActive(second.id);
  render(<PortfolioPanel />);
  await settle();
  await act(async () => { fireEvent.click(screen.getByLabelText("Delete TCS.NS")); });
  save("P4b-fresh-mount-delete", { holdings: active().holdings.map((h) => h.symbol) });
  cleanup();
});

test("P5 unresolved-only + crypto slash symbol", async () => {
  reset();
  const { container } = render(<PortfolioPanel />);
  await addViaForm("ZZZZNOTREAL", "10", "100");
  await settle();
  const unresolved = { summary: summaryLine(container), rows: text(container.querySelector('[data-testid="portfolio-holdings-table"]')!), bus: captureTerminalState().portfolio };
  usePortfoliosStore.setState({ portfolios: [{ id: "default", name: "Portfolio", holdings: [] }], activeId: "default" });
  await settle();
  await addViaForm("BTC/USDT", "0.5", "60000", "crypto");
  await settle();
  const cryptoSlash = { summary: summaryLine(container), rows: text(container.querySelector('[data-testid="portfolio-holdings-table"]')!) };
  usePortfoliosStore.setState({ portfolios: [{ id: "default", name: "Portfolio", holdings: [] }], activeId: "default" });
  await settle();
  await addViaForm("BTCUSDT", "0.5", "60000", "crypto");
  await settle();
  const cryptoNoSlash = { summary: summaryLine(container), rows: text(container.querySelector('[data-testid="portfolio-holdings-table"]')!) };
  save("P5-unresolved-crypto", { unresolved, cryptoSlash, cryptoNoSlash, net: netlog.filter((n) => n.url.startsWith("/quotes")).slice(-4) });
  cleanup();
});

test("P6 mixed currency + CSV export (note with formula + comma)", async () => {
  reset();
  const { container } = render(<PortfolioPanel />);
  await addViaForm("RELIANCE.NS", "10", "1200", "equity", "=HYPERLINK(\"http://example.invalid\",\"x\")");
  await addViaForm("AAPL", "3", "300", "equity", "core, long");
  await addViaForm("ZZZZNOTREAL", "1", "10");
  await settle();
  await act(async () => { fireEvent.click(screen.getByLabelText("Export portfolio to CSV")); });
  save("P6-mixed-csv", { summary: summaryLine(container), header: text(container.querySelector('[data-testid="portfolio-holdings-table"]')!).slice(0, 120), csv: csvCaptured.at(-1), bus: captureTerminalState().portfolio });
  cleanup();
});

test("P7 quote transport failure (induced) -> banner?", async () => {
  reset();
  failQuotes = true;
  const { container } = render(<PortfolioPanel />);
  await addViaForm("RELIANCE.NS", "10", "1200");
  await settle();
  save("P7-quotes-down", { panelText: text(container), bannerShown: text(container).includes("Couldn") });
  failQuotes = false;
  cleanup();
});

test("P8 100-position portfolio (tenth item + overflow + quote fan-out)", async () => {
  reset();
  const syms: string[] = JSON.parse(fs.readFileSync(`${SCR}/vt/sym100.json`, "utf8"));
  usePortfoliosStore.getState().setAll([{ id: "big", name: "Big", holdings: syms.map((s, i) => ({ id: `h${i}`, symbol: s, quantity: 1 + i, costBasis: 100, assetClass: "equity" })) }], "big");
  const n0 = netlog.length; const t0 = Date.now();
  const { container } = render(<PortfolioPanel />);
  const ms = await settle(600000);
  const q = netlog.slice(n0).filter((n) => n.url.startsWith("/quotes"));
  const statusCounts: Record<string, number> = {}; q.forEach((n) => { statusCounts[String(n.status)] = (statusCounts[String(n.status)] ?? 0) + 1; });
  const rows = container.querySelectorAll('[data-testid="portfolio-holdings-table"] [role="row"]').length || container.querySelectorAll('[data-testid="portfolio-holdings-table"] tr').length;
  const t = text(container);
  save("P8-100", { settleMs: ms, wallMs: Date.now() - t0, quoteRequests: q.length, statusCounts, maxMs: Math.max(...q.map((n) => n.ms)), renderedRows: rows, tenthRow: syms[9], tenthRowRendered: t.includes(syms[9]), summary: summaryLine(container), optionLabel: (screen.getByLabelText("Active portfolio") as HTMLSelectElement).options[0].text });
  cleanup();
});

test("P9 agent context + portfolio host actions", async () => {
  reset();
  const { container } = render(<PortfolioPanel />);
  await addViaForm("RELIANCE.NS", "10", "1200");
  await addViaForm("TCS.NS", "5", "2500");
  await addViaForm("TCS.NS", "20", "3900", "equity", "second lot");
  await settle();
  const openSnap = captureTerminalState().portfolio;
  const storeIds = active().holdings.map((h) => [h.id, h.symbol, h.quantity]);
  const n0 = netlog.length;
  const r: Record<string, unknown> = {};
  // agent reads get_portfolio (panel open) -> holdings carry no id -> the best it can pass is a symbol
  const tcsSecondLotId = active().holdings[2].id;
  r.describe_update_by_symbol = describeHostAction("portfolio_update_position", { position_id: "2", symbol: "TCS.NS", quantity: 25 });
  r.update_by_symbol = await applyHostActionAsync("portfolio_update_position", { position_id: "2", symbol: "TCS.NS", quantity: 25 });
  r.after_update = active().holdings.map((h) => [h.symbol, h.quantity, h.costBasis, h.note ?? null]);
  r.update_by_real_id = await applyHostActionAsync("portfolio_update_position", { position_id: tcsSecondLotId, quantity: 21 });
  r.after_update_real = active().holdings.map((h) => [h.symbol, h.quantity, h.costBasis, h.note ?? null]);
  r.add_neg_cost = await applyHostActionAsync("portfolio_add_position", { symbol: "INFY.NS", quantity: 4, cost_basis: -1500 });
  r.add_qty_string = await applyHostActionAsync("portfolio_add_position", { symbol: "INFY.NS", quantity: "4", cost_basis: 1500 });
  r.add_ok = await applyHostActionAsync("portfolio_add_position", { symbol: "HDFCBANK.NS", quantity: 2, cost_basis: 1600, purchased_at: "2026-01-05" });
  r.delete_by_symbol = await applyHostActionAsync("portfolio_delete_position", { position_id: "x", symbol: "HDFCBANK.NS" });
  r.after_all = active().holdings.map((h) => [h.symbol, h.quantity, h.costBasis]);
  r.net = netlog.slice(n0).filter((n) => n.url.startsWith("/portfolio"));
  const ledger = await (await realFetch(`http://127.0.0.1:${PORT}/portfolio/positions`)).json();
  r.sidecarLedger = ledger;
  cleanup();
  usePanelContextBus.getState().unregisterSource?.("portfolio");
  const closedSnap = captureTerminalState().portfolio;
  save("P9-agent", { openPanelSnapshot: openSnap, storeIds, closedPanelSnapshot: closedSnap, ...r });
});
