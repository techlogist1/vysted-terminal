import { test } from "vitest";
import fs from "fs";
import { render, screen, cleanup, act } from "@testing-library/react";

const W = "/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/454f42d1-ac9f-4d44-ba99-216c6bad682f/scratchpad/fdpn/vt";
const PORT = 52844;
window.history.replaceState({}, "", `/?sidecar-port=${PORT}`);
import { usePortfoliosStore } from "@/store/portfolios";
import { PortfolioPanel } from "@/modules/portfolio/PortfolioPanel";
import { captureTerminalState } from "@/modules/chat/context-provider";

const realFetch = globalThis.fetch;
const q: { t0: number; t1: number; url: string; status: number | string }[] = [];
let inflight = 0; let maxInflight = 0;
globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
  const url = String(input).replace(/^http:\/\/127\.0\.0\.1:\d+/, "");
  const t0 = Date.now(); inflight++; maxInflight = Math.max(maxInflight, inflight);
  try { const r = await realFetch(input as any, init); if (url.startsWith("/quotes")) q.push({ t0, t1: Date.now(), url, status: r.status }); return r; }
  catch (e) { if (url.startsWith("/quotes")) q.push({ t0, t1: Date.now(), url, status: String(e) }); throw e; }
  finally { inflight--; }
}) as typeof fetch;
const wait = (ms: number) => act(async () => { await new Promise((r) => setTimeout(r, ms)); });

test("P8 100-position portfolio (tenth item, overflow, fan-out, overlap guard)", async () => {
  const syms: string[] = JSON.parse(fs.readFileSync(`${W}/sym100.json`, "utf8"));
  usePortfoliosStore.getState().setAll([{ id: "big", name: "Big", holdings: syms.map((s, i) => ({ id: `h${i}`, symbol: s, quantity: 1 + i, costBasis: 100, assetClass: "equity" })) }], "big");
  const tStart = Date.now();
  const { container } = render(<PortfolioPanel />);
  // first fan-out settles when 100 quote responses are in
  while (q.length < 100 && Date.now() - tStart < 300000) await wait(500);
  const firstFanOutMs = Date.now() - tStart;
  const firstMaxMs = Math.max(...q.map((x) => x.t1 - x.t0));
  // watch 20 s more: with the guard, a tick only fires once the previous fan-out settled
  const n1 = q.length; maxInflight = inflight;
  await wait(20000);
  const later = q.slice(n1);
  const statusCounts: Record<string, number> = {}; q.forEach((n) => { statusCounts[String(n.status)] = (statusCounts[String(n.status)] ?? 0) + 1; });
  const t = (container.textContent ?? "").replace(/\s+/g, " ");
  const rows = container.querySelectorAll('[data-testid="portfolio-holdings-table"] [role="row"]').length;
  const snap = captureTerminalState().portfolio as any;
  fs.writeFileSync(`${W}/out/p8-replay.json`, JSON.stringify({
    firstFanOutMs, firstMaxMs, totalQuoteReqs: q.length, statusCounts, laterReqs20s: later.length, maxInflightLater20s: maxInflight,
    renderedRows: rows, tenthRow: syms[9], tenthRowRendered: t.includes(syms[9]), lastRowRendered: t.includes(syms[99]),
    optionLabel: (screen.getByLabelText("Active portfolio") as HTMLSelectElement).options[0].text,
    summary: t.slice(t.indexOf("Market value"), t.indexOf("Market value") + 260),
    unresolvedText: t.match(/[^.]{0,80}(no quote|unresolved|not found)[^.]{0,80}/i)?.[0] ?? null,
    snapshot: snap ? { keys: Object.keys(snap), holdingsCount: snap.holdings?.length, first: snap.holdings?.[0], totalValue: snap.totalValue, totalValueNote: snap.totalValueNote } : null,
  }, null, 1));
  cleanup();
});
