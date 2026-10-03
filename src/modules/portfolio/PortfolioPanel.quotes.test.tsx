import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";

import { usePortfoliosStore } from "@/store/portfolios";
import { useSettingsStore } from "@/store/settings";
import { PortfolioPanel } from "./PortfolioPanel";

// The real quote client (api.ts -> sidecar-client) against a stubbed `fetch`, so
// these tests see the exact /quotes requests the panel sends. The browser-dev
// `?sidecar-port=` seam names the sidecar; the stub answers its /health probe.
window.history.replaceState({}, "", "/?sidecar-port=9999");
vi.mock("./api", async (importActual) => ({
  ...(await importActual<typeof import("./api")>()),
  fetchDailyCloses: vi.fn(() => Promise.resolve(null)),
}));
vi.mock("@/lib/csv", async (importActual) => ({
  ...(await importActual<typeof import("@/lib/csv")>()),
  downloadCsv: vi.fn(() => Promise.resolve({ path: "/tmp/out.csv", fellBack: false })),
}));

const csvModule = await import("@/lib/csv");
const mockDownloadCsv = vi.mocked(csvModule.downloadCsv);

interface QuoteRequest {
  symbols: string[];
  region: string | undefined;
}

/** Listing prices per region: INFY is NSE (INR) under IN, the NYSE ADR under US. */
const LISTINGS: Record<string, Record<string, { price: number; currency: string }>> = {
  IN: { INFY: { price: 1035, currency: "INR" }, TCS: { price: 3900, currency: "INR" } },
  US: { INFY: { price: 11.04, currency: "USD" }, TCS: { price: 7.5, currency: "USD" } },
};

let requests: QuoteRequest[] = [];
let respond: (req: QuoteRequest) => Promise<Response> = defaultRespond;

function quoteRow(symbol: string, region: string | undefined) {
  const listing = LISTINGS[region ?? ""]?.[symbol];
  return listing
    ? {
        symbol,
        price: listing.price,
        change: 0,
        change_percent: 0,
        volume: null,
        currency: listing.currency,
        market_state: null,
        timestamp: "2026-10-02T10:00:00Z",
        provider: "yfinance",
      }
    : null;
}

function defaultRespond(req: QuoteRequest): Promise<Response> {
  const rows = req.symbols.map((s) => quoteRow(s, req.region)).filter((r) => r !== null);
  return Promise.resolve(new Response(JSON.stringify(rows), { status: 200 }));
}

function stubFetch(): void {
  vi.stubGlobal(
    "fetch",
    vi.fn((input: string, init?: RequestInit) => {
      const url = new URL(input);
      const region = (init?.headers as Record<string, string> | undefined)?.["X-Vysted-Region"];
      if (url.pathname === "/health") {
        return Promise.resolve(new Response("{}", { status: 200 }));
      }
      if (url.pathname === "/quotes") {
        const req = { symbols: (url.searchParams.get("symbols") ?? "").split(","), region };
        requests.push(req);
        return respond(req);
      }
      if (url.pathname.startsWith("/quotes/")) {
        const symbol = decodeURIComponent(url.pathname.slice("/quotes/".length));
        const req = { symbols: [symbol], region };
        requests.push(req);
        const row = quoteRow(symbol, region);
        return Promise.resolve(
          row
            ? new Response(JSON.stringify(row), { status: 200 })
            : new Response(JSON.stringify({ detail: "not_found" }), { status: 404 }),
        );
      }
      return Promise.resolve(new Response("{}", { status: 404 }));
    }),
  );
}

async function addHolding(symbol: string, quantity: string, costBasis: string) {
  fireEvent.change(screen.getByLabelText("Symbol"), { target: { value: symbol } });
  fireEvent.change(screen.getByLabelText("Quantity"), { target: { value: quantity } });
  fireEvent.change(screen.getByLabelText("Avg cost / share"), { target: { value: costBasis } });
  await act(async () => {
    fireEvent.submit(screen.getByLabelText("Symbol").closest("form")!);
  });
}

async function tick(ms = 5_100) {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });
}

function requestsFor(symbol: string): QuoteRequest[] {
  return requests.filter((r) => r.symbols.includes(symbol));
}

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  vi.clearAllMocks();
  requests = [];
  respond = defaultRespond;
  stubFetch();
  usePortfoliosStore.setState({
    portfolios: [{ id: "default", name: "Portfolio", holdings: [] }],
    activeId: "default",
  });
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("PortfolioPanel live quotes (real client)", () => {
  it("R15-FINAL-001: a holding keeps its own listing's quote after the session region switches", async () => {
    useSettingsStore.setState({ region: "IN" });
    render(<PortfolioPanel />);
    await addHolding("infy", "20", "1500");
    await tick(100);

    act(() => useSettingsStore.setState({ region: "US" }));
    await tick();
    await tick();

    // Every INFY quote request rode the holding's region, never the session's.
    expect(requestsFor("INFY").length).toBeGreaterThanOrEqual(2);
    expect(requestsFor("INFY").every((r) => r.region === "IN")).toBe(true);

    await act(async () => {
      fireEvent.click(screen.getByLabelText("Export portfolio to CSV"));
    });
    const [, csv] = mockDownloadCsv.mock.calls[0];
    expect(csv.split("\n")[1].split(",").slice(0, 7)).toEqual([
      "INFY",
      "20",
      "1500",
      "equity",
      "INR",
      "1035",
      "20700",
    ]);
  });

  it("R15-FINAL-001: a holding added under US stays on the US listing after a switch to IN", async () => {
    useSettingsStore.setState({ region: "US" });
    render(<PortfolioPanel />);
    await addHolding("tcs", "2", "7");
    await tick(100);
    act(() => useSettingsStore.setState({ region: "IN" }));
    await tick();
    expect(requestsFor("TCS").length).toBeGreaterThanOrEqual(2);
    expect(requestsFor("TCS").every((r) => r.region === "US")).toBe(true);
  });

  it("R15-FINAL-006: 100 holdings refresh as ONE request, never re-sent while it is in flight", async () => {
    usePortfoliosStore.setState({
      portfolios: [
        {
          id: "default",
          name: "Portfolio",
          holdings: Array.from({ length: 100 }, (_, i) => ({
            id: `h${i}`,
            symbol: `NSE${i}`,
            quantity: 1,
            costBasis: 100,
            assetClass: "equity" as const,
            region: "IN" as const,
          })),
        },
      ],
      activeId: "default",
    });
    respond = () => new Promise<Response>(() => {}); // a cold sidecar that never answers
    render(<PortfolioPanel />);
    await tick(100);
    await tick();
    await tick();
    await tick();
    expect(requests).toHaveLength(1);
    expect(requests[0].symbols).toHaveLength(100);
    expect(requests[0].region).toBe("IN");
  });

  it("R15-FINAL-006: a failed refresh backs off instead of re-sending every 5 s", async () => {
    useSettingsStore.setState({ region: "IN" });
    respond = () =>
      Promise.resolve(new Response(JSON.stringify({ detail: "boom" }), { status: 502 }));
    render(<PortfolioPanel />);
    await addHolding("infy", "20", "1500");
    requests = [];
    for (let i = 0; i < 6; i += 1) {
      await tick(5_000);
    }
    // 30 s of 5 s ticks: 6 re-sends without a backoff; 10 s then 20 s with it.
    expect(requests.length).toBeLessThanOrEqual(2);
    expect(await screen.findByText(/Couldn.t refresh live quotes/)).toBeInTheDocument();
  });
});
