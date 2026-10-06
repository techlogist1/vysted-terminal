import { vi, test } from "vitest";
import fs from "fs";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";

vi.mock("@/lib/sidecar-client", async () => {
  const base = "http://127.0.0.1:52219";
  return {
    getSidecarBaseUrl: vi.fn().mockResolvedValue(base),
    sidecarGet: vi.fn(async (path: string, params?: Record<string, string>) => {
      const u = new URL(path, base);
      for (const [k, v] of Object.entries(params ?? {})) u.searchParams.set(k, String(v));
      const r = await fetch(u.toString());
      if (!r.ok) throw new Error("GET " + path + " " + r.status);
      return r.json();
    }),
  };
});
vi.mock("@/lib/host-actions", () => ({ loadSymbolIntoChart: vi.fn(), openCompanyOverview: vi.fn() }));

import { useScreenerStore } from "@/store/screener";
import { ScreenerPanel } from "@/modules/screener/ScreenerPanel";

const OUT = "/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/s2b/replay-screener-2.json";
const log: Record<string, unknown> = {};
const realFetch = globalThis.fetch;
const sent: unknown[] = [];
globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
  if (init?.body && String(input).includes("/screener/")) sent.push({ url: String(input), body: JSON.parse(String(init.body)) });
  return realFetch(input as any, init);
}) as typeof fetch;

function panelText(): string {
  cleanup();
  const { container } = render(<ScreenerPanel />);
  return (container.textContent ?? "").replace(/\s+/g, " ");
}
function snap(label: string, extra: Record<string, unknown> = {}) {
  const s = useScreenerStore.getState();
  const r = s.lastResult;
  log[label] = { status: s.status, error: s.error, result: r ? { evaluated: r.evaluated_count, result_count: r.result_count, rows: r.rows.length, partial: r.partial, throttled: r.throttled, coverage: r.coverage } : null, panelText: (() => { const t = panelText(); return t.slice(0, 700) + " ..... " + t.slice(-900); })(), ...extra };
  fs.writeFileSync(OUT, JSON.stringify(log, null, 1));
}

test("S1 default mount state -> real run", async () => {
  useScreenerStore.getState().__resetForTests();
  await useScreenerStore.getState().runScreener();
  snap("S1-default-sp500", { request: sent.at(-1) });
});

test("S2 india-all loose (truncation line)", async () => {
  useScreenerStore.getState().__resetForTests();
  useScreenerStore.setState({ universe: "india-all", criteria: [{ field: "pe_ratio", operator: "between", value: { min: 0, max: 40 } } as any] });
  await useScreenerStore.getState().runScreener();
  snap("S2-indiaall-loose");
});

test("S3 malformed formula pre-flight", async () => {
  useScreenerStore.getState().__resetForTests();
  const before = sent.length;
  useScreenerStore.setState({ universe: "nifty50", formula: "pe < 20 and roe > 15%" });
  await useScreenerStore.getState().runScreener();
  snap("S3-malformed-formula", { network_calls: sent.length - before });
});

test("S4 preset clicked while an advanced nested group + formula are set", async () => {
  useScreenerStore.getState().__resetForTests();
  useScreenerStore.setState({
    universe: "nifty50", advanced: true, formula: "pe < 12",
    group: { combinator: "and", criteria: [ { combinator: "or", criteria: [ { field: "pe_ratio", operator: "lt", value: 12 }, { field: "dividend_yield", operator: "gt", value: 0.04 } ] } ] } as any,
  });
  cleanup();
  render(<ScreenerPanel />);
  const before = sent.length;
  fireEvent.click(screen.getByText("Founder-aligned (NSE)"));
  for (let i = 0; i < 200 && useScreenerStore.getState().status !== "ready" && useScreenerStore.getState().status !== "error"; i++) await new Promise((r) => setTimeout(r, 100));
  const s = useScreenerStore.getState();
  snap("S4-preset-after-advanced", { request: sent.slice(before), state_after: { universe: s.universe, criteria: s.criteria, advanced: s.advanced, formula: s.formula, group: s.group }, symbols: s.lastResult?.rows.map((r) => [r.symbol, r.pe_ratio, r.dividend_yield, (r as any).held_percent_insiders ?? null, r.roe]) });
});

test("S5 same preset from a clean state (control)", async () => {
  useScreenerStore.getState().__resetForTests();
  cleanup();
  render(<ScreenerPanel />);
  const before = sent.length;
  fireEvent.click(screen.getByText("Founder-aligned (NSE)"));
  for (let i = 0; i < 200 && useScreenerStore.getState().status !== "ready" && useScreenerStore.getState().status !== "error"; i++) await new Promise((r) => setTimeout(r, 100));
  const s = useScreenerStore.getState();
  snap("S5-preset-clean", { request: sent.slice(before), symbols: s.lastResult?.rows.map((r) => [r.symbol, r.pe_ratio, r.roe, r.debt_to_equity]) });
});

test("S6 error frame from the stream (server shape routers/screener.py:123-131)", async () => {
  useScreenerStore.getState().__resetForTests();
  const enc = new TextEncoder();
  const body = new ReadableStream({ start(c) {
    c.enqueue(enc.encode('data: {"event":"progress","phase":"universe","done":1,"total":1,"detail":"NIFTY 50: 50 symbols"}\n\n'));
    c.enqueue(enc.encode('data: {"event":"error","message":"missing universe snapshot \'nifty50.json\'"}\n\n'));
    c.close();
  } });
  const saved = globalThis.fetch;
  globalThis.fetch = (async () => new Response(body, { status: 200, headers: { "content-type": "text/event-stream" } })) as typeof fetch;
  useScreenerStore.setState({ universe: "nifty50" });
  await useScreenerStore.getState().runScreener();
  globalThis.fetch = saved;
  snap("S6-error-frame");
});

test("S7 custom universe empty -> Run disabled; bare tickers run", async () => {
  useScreenerStore.getState().__resetForTests();
  useScreenerStore.setState({ universe: "custom", customSymbols: "" });
  cleanup();
  render(<ScreenerPanel />);
  const disabled = (screen.getByTestId("run-screener-button") as HTMLButtonElement).disabled;
  useScreenerStore.setState({ customSymbols: "reliance, tcs infy", criteria: [{ field: "pe_ratio", operator: "gt", value: 0 } as any] });
  await useScreenerStore.getState().runScreener();
  snap("S7-custom", { run_disabled_when_empty: disabled, request: sent.at(-1) });
});

test("S8 cancel mid-run", async () => {
  useScreenerStore.getState().__resetForTests();
  useScreenerStore.setState({ universe: "sp500" });
  const p = useScreenerStore.getState().runScreener();
  await new Promise((r) => setTimeout(r, 400));
  const mid = useScreenerStore.getState().status;
  useScreenerStore.getState().cancelRun();
  const ret = await p;
  snap("S8-cancel", { status_mid: mid, returned: ret === null ? null : "result" });
});

test("S9 save / load / delete screen (session state)", async () => {
  useScreenerStore.getState().__resetForTests();
  useScreenerStore.setState({ universe: "nse-all", formula: "roe > 0.2" });
  useScreenerStore.getState().saveScreen("roe20");
  useScreenerStore.getState().__resetForTests.call(null);
  const afterReset = useScreenerStore.getState().savedScreens.length;
  useScreenerStore.setState({ savedScreens: [] });
  useScreenerStore.setState({ universe: "nse-all", formula: "roe > 0.2" });
  useScreenerStore.getState().saveScreen("roe20");
  useScreenerStore.setState({ universe: "sp500", formula: "" });
  useScreenerStore.getState().loadScreen("roe20");
  const loaded = { universe: useScreenerStore.getState().universe, formula: useScreenerStore.getState().formula };
  useScreenerStore.getState().deleteScreen("roe20");
  snap("S9-saved-screens", { loaded, after_delete: useScreenerStore.getState().savedScreens.length, after_reset_count: afterReset });
});
