import { vi, test } from "vitest";
import fs from "fs";
import { render, screen, fireEvent, cleanup, act } from "@testing-library/react";

const W = "/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/454f42d1-ac9f-4d44-ba99-216c6bad682f/scratchpad/fdpn/vt";
const PORT = 52844;
window.history.replaceState({}, "", `/?sidecar-port=${PORT}`);

const csvCaptured: { name: string; content: string }[] = [];
vi.mock("@/lib/csv", async (orig) => {
  const real = (await orig()) as Record<string, unknown>;
  return { ...real, downloadCsv: vi.fn(async (name: string, content: string) => { csvCaptured.push({ name, content }); return { path: `/fake/${name}` }; }) };
});

import { usePortfoliosStore } from "@/store/portfolios";
import { useSettingsStore } from "@/store/settings";
import { usePanelContextBus } from "@/store/panel-context";
import { PortfolioPanel } from "@/modules/portfolio/PortfolioPanel";
import { captureTerminalState } from "@/modules/chat/context-provider";
import { applyHostActionAsync, describeHostAction } from "@/lib/host-actions";
import { fetchLegacyPositions } from "@/modules/portfolio/api";

const OUT = `${W}/out/portfolio-replay.json`;
const log: Record<string, unknown> = {};
const realFetch = globalThis.fetch;
const netlog: { t: number; method: string; url: string; status: number | string; ms: number }[] = [];
let inflight = 0;
let failQuotes = false;
globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
  const url = String(input);
  const t0 = Date.now();
  inflight++;
  try {
    if (failQuotes && url.includes("/quotes")) throw new TypeError("Failed to fetch (induced)");
    const r = await realFetch(input as any, init);
    netlog.push({ t: t0, method: init?.method ?? "GET", url: url.replace(/^http:\/\/127\.0\.0\.1:\d+/, ""), status: r.status, ms: Date.now() - t0 });
    return r;
  } catch (e) {
    netlog.push({ t: t0, method: init?.method ?? "GET", url: url.replace(/^http:\/\/127\.0\.0\.1:\d+/, ""), status: String(e), ms: Date.now() - t0 });
    throw e;
  } finally { inflight--; }
}) as typeof fetch;

async function settle(maxMs = 90000) {
  const t0 = Date.now();
  await act(async () => { await new Promise((r) => setTimeout(r, 50)); });
  while (Date.now() - t0 < maxMs) {
    await act(async () => { await new Promise((r) => setTimeout(r, 200)); });
    if (inflight === 0) { await act(async () => { await new Promise((r) => setTimeout(r, 150)); }); if (inflight === 0) break; }
  }
  return Date.now() - t0;
}
const text = (el: Element | null) => ((el?.textContent) ?? "").replace(/\s+/g, " ").trim();
function save(label: string, v: unknown) { log[label] = v; fs.writeFileSync(OUT, JSON.stringify(log, null, 1)); }
function reset() {
  usePortfoliosStore.setState({ portfolios: [{ id: "default", name: "Portfolio", holdings: [] }], activeId: "default" });
  usePanelContextBus.setState({ lastEventBySource: {}, focusedSource: null, updatedAt: 0 } as any);
}
async function addViaForm(symbol: string, qty: string, cost: string, cls: "equity" | "crypto" = "equity", note = "") {
  fireEvent.change(screen.getByLabelText("Symbol"), { target: { value: symbol } });
  fireEvent.change(screen.getByLabelText("Quantity"), { target: { value: qty } });
  fireEvent.change(screen.getByLabelText("Avg cost / share"), { target: { value: cost } });
  fireEvent.change(screen.getByLabelText("Asset class"), { target: { value: cls } });
  fireEvent.change(screen.getByLabelText("Note"), { target: { value: note } });
  await act(async () => { fireEvent.submit(screen.getByLabelText("Symbol").closest("form")!); });
}
async function confirmClick(label: string) {
  await act(async () => { fireEvent.click(screen.getByLabelText(label)); });
  await act(async () => { fireEvent.click(screen.getByLabelText("Confirm: this cannot be undone")); });
}
const active = () => { const s = usePortfoliosStore.getState(); return s.portfolios.find((p) => p.id === s.activeId)!; };
const tableText = (c: Element) => text(c.querySelector('[data-testid="portfolio-holdings-table"]'));
const errText = (c: Element) => { const e = c.querySelector('[role="alert"], p.text-negative'); return e ? text(e) : null; };

test("P1 empty portfolio", async () => {
  reset();
  useSettingsStore.getState().setRegion?.("IN" as any);
  const n0 = netlog.length;
  const { container } = render(<PortfolioPanel />);
  await settle();
  const exportBtn = screen.getByLabelText("Export portfolio to CSV") as HTMLButtonElement;
  save("P1-empty", { panelText: text(container).slice(0, 600), exportDisabled: exportBtn.disabled, net: netlog.slice(n0) });
  cleanup();
});

test("P2 form validation", async () => {
  reset();
  const { container } = render(<PortfolioPanel />);
  const out: Record<string, unknown> = {};
  const cases = [["empty", "", "", ""], ["qty0", "TCS.NS", "0", "100"], ["negcost", "TCS.NS", "5", "-1"], ["qtyabc", "TCS.NS", "abc", "100"], ["qty-neg", "TCS.NS", "-3", "100"], ["qty-1e20", "TCS.NS", "1e20", "100"], ["cost-blank", "TCS.NS", "5", ""], ["cost-spaces", "TCS.NS", "5", "   "], ["qty-spaces", "TCS.NS", "   ", "100"], ["qty-comma", "TCS.NS", "1,000", "100"], ["qty-hex", "TCS.NS", "0x10", "100"], ["cost-zero", "TCS.NS", "5", "0"], ["ok", "tcs.ns", " 5 ", "2500.5"]] as const;
  for (const [label, s, q, c] of cases) {
    await addViaForm(s, q, c);
    out[label] = { input: { s, q, c }, error: errText(container), holdings: active().holdings.map((h) => [h.symbol, h.quantity, h.costBasis]) };
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
  save("P3-inr", { settleMs: ms, ref, expected: { mv, pnl, pnlPct: (pnl / cost) * 100, wRel: ref["RELIANCE.NS"] * 10 / mv }, panel: text(container).slice(0, 900), bus: captureTerminalState().portfolio });
  cleanup();
});

test("P4 delete/edit after switching to a portfolio created after mount", async () => {
  reset();
  const { container } = render(<PortfolioPanel />);
  await addViaForm("RELIANCE.NS", "10", "1200");
  await settle();
  fireEvent.click(screen.getByLabelText("New portfolio"));
  fireEvent.change(screen.getByLabelText("New portfolio name"), { target: { value: "Second" } });
  await act(async () => { fireEvent.click(screen.getByLabelText("Confirm")); });
  await addViaForm("TCS.NS", "5", "2500");
  await addViaForm("INFY.NS", "3", "1500");
  await settle();
  const before = { active: active().name, holdings: active().holdings.map((h) => h.symbol) };
  // single click must NOT delete (ConfirmButton arm)
  await act(async () => { fireEvent.click(screen.getByLabelText("Delete INFY.NS")); });
  const afterSingleClick = active().holdings.map((h) => h.symbol);
  await act(async () => { fireEvent.click(screen.getByLabelText("Confirm: this cannot be undone")); });
  const afterConfirm = active().holdings.map((h) => h.symbol);
  await act(async () => { fireEvent.click(screen.getByLabelText("Edit TCS.NS")); });
  fireEvent.change(screen.getByLabelText("Quantity"), { target: { value: "7" } });
  await act(async () => { fireEvent.submit(screen.getByLabelText("Symbol").closest("form")!); });
  const afterEdit = active().holdings.map((h) => [h.symbol, h.quantity, h.costBasis]);
  // edit, then switch portfolio mid-edit, then save (R15-UI-034)
  await act(async () => { fireEvent.click(screen.getByLabelText("Edit TCS.NS")); });
  fireEvent.change(screen.getByLabelText("Quantity"), { target: { value: "9" } });
  const sel = screen.getByLabelText("Active portfolio") as HTMLSelectElement;
  await act(async () => { fireEvent.change(sel, { target: { value: "default" } }); });
  const formAfterSwitch = (screen.getByLabelText("Symbol") as HTMLInputElement).value;
  await act(async () => { fireEvent.submit(screen.getByLabelText("Symbol").closest("form")!); });
  const afterSwitchSave = { err: errText(container), all: usePortfoliosStore.getState().portfolios.map((p) => [p.name, p.holdings.map((h) => [h.symbol, h.quantity])]) };
  await settle();
  await confirmClick("Delete RELIANCE.NS");
  const controlDelete = active().holdings.map((h) => h.symbol);
  save("P4-delete-edit", { before, afterSingleClick, afterConfirm, afterEdit, formAfterSwitch, afterSwitchSave, controlDeleteInFirstPortfolio: controlDelete });
  cleanup();
});

test("P4c portfolio header: rename, delete portfolio, delete last", async () => {
  reset();
  render(<PortfolioPanel />);
  const r: Record<string, unknown> = {};
  fireEvent.click(screen.getByLabelText("Rename portfolio"));
  fireEvent.change(screen.getByLabelText("Rename portfolio"), { target: { value: "  Core  " } });
  await act(async () => { fireEvent.click(screen.getByLabelText("Confirm")); });
  r.afterRename = usePortfoliosStore.getState().portfolios.map((p) => p.name);
  fireEvent.click(screen.getByLabelText("Rename portfolio"));
  fireEvent.change(screen.getByLabelText("Rename portfolio"), { target: { value: "   " } });
  await act(async () => { fireEvent.click(screen.getByLabelText("Confirm")); });
  r.afterBlankRename = usePortfoliosStore.getState().portfolios.map((p) => p.name);
  fireEvent.click(screen.getByLabelText("New portfolio"));
  fireEvent.change(screen.getByLabelText("New portfolio name"), { target: { value: "Spec" } });
  await act(async () => { fireEvent.click(screen.getByLabelText("Confirm")); });
  r.afterCreate = { names: usePortfoliosStore.getState().portfolios.map((p) => p.name), active: active().name };
  await act(async () => { fireEvent.click(screen.getByLabelText("Delete portfolio")); });
  r.afterSingleClickDelete = usePortfoliosStore.getState().portfolios.map((p) => p.name);
  await act(async () => { fireEvent.click(screen.getByLabelText("Confirm: this cannot be undone")); });
  r.afterConfirmDelete = { names: usePortfoliosStore.getState().portfolios.map((p) => p.name), active: active().name };
  await confirmClick("Delete portfolio");
  r.afterDeleteLast = { names: usePortfoliosStore.getState().portfolios.map((p) => p.name), count: usePortfoliosStore.getState().portfolios.length };
  save("P4c-header", r);
  cleanup();
});

test("P5 unresolved-only + crypto slash symbol", async () => {
  reset();
  const { container } = render(<PortfolioPanel />);
  await addViaForm("ZZZZNOTREAL", "10", "100");
  await settle();
  const unresolved = { panel: text(container).slice(0, 700), bus: captureTerminalState().portfolio };
  usePortfoliosStore.setState({ portfolios: [{ id: "default", name: "Portfolio", holdings: [] }], activeId: "default" });
  await settle();
  await addViaForm("BTC/USDT", "0.5", "60000", "crypto");
  await settle();
  const cryptoSlash = { table: tableText(container) };
  usePortfoliosStore.setState({ portfolios: [{ id: "default", name: "Portfolio", holdings: [] }], activeId: "default" });
  await settle();
  await addViaForm("BTCUSDT", "0.5", "60000", "crypto");
  await settle();
  const cryptoNoSlash = { table: tableText(container) };
  save("P5-unresolved-crypto", { unresolved, cryptoSlash, cryptoNoSlash, net: netlog.filter((n) => n.url.startsWith("/quotes")).slice(-4) });
  cleanup();
});

test("P6 mixed currency + CSV export (formula notes, comma)", async () => {
  reset();
  const { container } = render(<PortfolioPanel />);
  await addViaForm("RELIANCE.NS", "10", "1200", "equity", "=HYPERLINK(\"http://example.invalid\",\"x\")");
  await addViaForm("AAPL", "3", "300", "equity", "core, long");
  await addViaForm("TCS.NS", "1", "9000", "equity", "@SUM(1+1)");
  await addViaForm("INFY.NS", "1", "10", "equity", "+cmd|' /C calc'!A0");
  await addViaForm("ZZZZNOTREAL", "1", "10", "equity", "-2+3");
  await settle();
  await act(async () => { fireEvent.click(screen.getByLabelText("Export portfolio to CSV")); });
  await settle(3000);
  save("P6-mixed-csv", { panel: text(container).slice(0, 500), csv: csvCaptured.at(-1), exportStatus: text(container).match(/Saved [^ ]+/)?.[0] ?? null, bus: captureTerminalState().portfolio });
  cleanup();
});

test("P7 quote transport failure (induced) -> banner + retry", async () => {
  reset();
  failQuotes = true;
  const { container } = render(<PortfolioPanel />);
  await addViaForm("RELIANCE.NS", "10", "1200");
  await settle();
  const down = { panelText: text(container).slice(0, 700), bus: captureTerminalState().portfolio };
  failQuotes = false;
  const retry = Array.from(container.querySelectorAll("button")).find((b) => /retry/i.test(b.textContent ?? ""));
  if (retry) await act(async () => { fireEvent.click(retry); });
  await settle();
  save("P7-quotes-down", { down, retryFound: !!retry, afterRetry: text(container).slice(0, 500) });
  cleanup();
});

test("P9 agent context + portfolio host actions", async () => {
  reset();
  render(<PortfolioPanel />);
  await addViaForm("RELIANCE.NS", "10", "1200");
  await addViaForm("TCS.NS", "5", "2500");
  await addViaForm("TCS.NS", "20", "3900", "equity", "second lot");
  await addViaForm("AAPL", "2", "190");
  await settle();
  const openSnap = captureTerminalState().portfolio;
  const r: Record<string, unknown> = {};
  const tcsSecondLotId = active().holdings[2].id;
  r.describe_update_by_symbol = describeHostAction("portfolio_update_position", { symbol: "TCS.NS", quantity: 25 });
  r.update_by_symbol_ambiguous = await applyHostActionAsync("portfolio_update_position", { symbol: "TCS.NS", quantity: 25 });
  r.update_by_real_id = await applyHostActionAsync("portfolio_update_position", { position_id: tcsSecondLotId, quantity: 21, cost_basis: 3900 });
  r.after_update_real = active().holdings.map((h) => [h.symbol, h.quantity, h.costBasis, h.note ?? null]);
  r.add_neg_cost = await applyHostActionAsync("portfolio_add_position", { symbol: "INFY.NS", quantity: 4, cost_basis: -1500 });
  r.add_cost_string_spaces = await applyHostActionAsync("portfolio_add_position", { symbol: "INFY.NS", quantity: 4, cost_basis: "   " });
  r.add_no_cost = await applyHostActionAsync("portfolio_add_position", { symbol: "INFY.NS", quantity: 4 });
  r.add_qty_bool = await applyHostActionAsync("portfolio_add_position", { symbol: "INFY.NS", quantity: true, cost_basis: 1500 });
  r.add_qty_huge = await applyHostActionAsync("portfolio_add_position", { symbol: "INFY.NS", quantity: 1e20, cost_basis: 1500 });
  r.add_ok = await applyHostActionAsync("portfolio_add_position", { symbol: "HDFCBANK.NS", quantity: 2, cost_basis: 1600 });
  r.delete_by_symbol = await applyHostActionAsync("portfolio_delete_position", { symbol: "HDFCBANK.NS" });
  r.delete_unknown_id = await applyHostActionAsync("portfolio_delete_position", { position_id: "h-nope" });
  r.after_all = active().holdings.map((h) => [h.symbol, h.quantity, h.costBasis]);
  r.ledger = await (await realFetch(`http://127.0.0.1:${PORT}/portfolio/positions`)).json();
  r.legacyImport = await fetchLegacyPositions();
  cleanup();
  usePanelContextBus.getState().unregisterSource?.("portfolio");
  const closedSnap = captureTerminalState().portfolio;
  save("P9-agent", { openPanelSnapshot: openSnap, closedPanelSnapshot: closedSnap, ...r });
});
