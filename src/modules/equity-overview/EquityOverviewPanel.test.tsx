import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";

import { SidecarError } from "@/lib/sidecar-client";
import { resetEquityCommandStoreForTests, useEquityCommandStore } from "@/store/equity-command";
import type {
  AnalystRating,
  FieldMeta,
  FinancialStatement,
  Fundamentals,
  Quote,
} from "../../../types/data";
import { EquityOverviewPanel } from "./EquityOverviewPanel";
import type { EquityOverview } from "./api";

vi.mock("./api", () => ({
  loadEquityOverview: vi.fn(),
  autocompleteSymbols: vi.fn(() => Promise.resolve([])),
}));

const { loadEquityOverview } = await import("./api");
const mockLoad = vi.mocked(loadEquityOverview);

function quote(): Quote {
  return {
    symbol: "AAPL",
    price: 192.5,
    change: 2.5,
    change_percent: 1.31,
    volume: 51_000_000,
    currency: "USD",
    market_state: null,
    timestamp: "2026-05-15T00:00:00Z",
    provider: "yfinance",
  };
}

function fundamentals(overrides: Partial<Fundamentals> = {}): Fundamentals {
  return {
    symbol: "AAPL",
    name: "Apple Inc.",
    sector: "Technology",
    industry: "Consumer Electronics",
    currency: "USD",
    market_cap: 3_000_000_000_000,
    pe_ratio: 31.2,
    forward_pe: 28.4,
    peg_ratio: 2.1,
    price_to_book: 47,
    price_to_sales: 8.1,
    ev_to_ebitda: 24,
    book_value: 4.4,
    dividend_yield: 0.0044,
    dividend_per_share: 1.0,
    eps: 6.17,
    beta: 1.25,
    fifty_two_week_high: 220,
    fifty_two_week_low: 160,
    fifty_two_week_change: 0.18,
    roe: 1.5,
    roa: 0.28,
    gross_margin: 0.46,
    operating_margin: 0.3,
    profit_margin: 0.25,
    debt_to_equity: 1.5,
    current_ratio: 0.95,
    quick_ratio: 0.85,
    revenue_ttm: 400_000_000_000,
    net_income_ttm: 100_000_000_000,
    free_cash_flow: 95_000_000_000,
    shares_outstanding: 15_500_000_000,
    revenue_growth: 0.05,
    earnings_growth: 0.11,
    held_percent_insiders: 0.0007,
    held_percent_institutions: 0.61,
    provider: "yfinance",
    ...overrides,
  };
}

function statement(): FinancialStatement {
  return {
    symbol: "AAPL",
    periods: ["2025", "2024"],
    lines: [
      { label: "Total Revenue", values: { "2025": 400_000, "2024": 380_000 } },
      { label: "Net Income", values: { "2025": 100_000, "2024": 95_000 } },
    ],
    provider: "yfinance",
  };
}

function ratings(): AnalystRating {
  return {
    symbol: "AAPL",
    consensus: "buy",
    target_mean: 225,
    target_high: 260,
    target_low: 170,
    strong_buy: 12,
    buy: 20,
    hold: 8,
    sell: 1,
    strong_sell: 0,
    provider: "yfinance",
  };
}

function overview(overrides: Partial<EquityOverview> = {}): EquityOverview {
  return {
    symbol: "AAPL",
    quote: quote(),
    fundamentals: fundamentals(),
    fundamentalsError: null,
    income: statement(),
    balance: statement(),
    cashFlow: statement(),
    ratings: ratings(),
    allFailed: false,
    ...overrides,
  };
}

async function loadSymbol(value = "aapl"): Promise<void> {
  fireEvent.change(screen.getByLabelText("Symbol"), { target: { value } });
  await act(async () => {
    fireEvent.submit(screen.getByLabelText("Symbol").closest("form")!);
  });
}

beforeEach(() => {
  vi.clearAllMocks();
  resetEquityCommandStoreForTests();
});

afterEach(() => {
  cleanup();
});

/** Flush the panel's deferred (setTimeout 0) command consumption. */
async function flushCommandTick(): Promise<void> {
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
}

describe("EquityOverviewPanel", () => {
  it("shows a composed empty state with quick-load chips before a symbol is loaded", () => {
    render(<EquityOverviewPanel />);
    // The shared composed EmptyState — never instructional copy as content.
    expect(screen.getByTestId("empty-state")).toBeInTheDocument();
    expect(screen.getByTestId("empty-state-headline").textContent).toBe("Equity overview");
    expect(
      screen.getByText(/Screener-grade fundamentals, statements, and ratings/),
    ).toBeInTheDocument();
    const chips = screen.getByTestId("quick-load-chips");
    for (const t of ["AAPL", "RELIANCE", "NVDA"]) {
      expect(chips.textContent).toContain(t);
    }
  });

  it("a quick-load chip loads its symbol", async () => {
    mockLoad.mockResolvedValue(overview());
    render(<EquityOverviewPanel />);
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "AAPL" }));
    });
    expect(mockLoad).toHaveBeenCalledWith("AAPL");
    expect(screen.getByRole("heading", { name: "AAPL" })).toBeInTheDocument();
  });

  it("loads and displays fundamentals, ratios, statements, and ratings", async () => {
    mockLoad.mockResolvedValue(overview());
    render(<EquityOverviewPanel />);
    await loadSymbol();

    expect(mockLoad).toHaveBeenCalledWith("AAPL");
    expect(screen.getByRole("heading", { name: "AAPL" })).toBeInTheDocument();
    expect(screen.getByText("Apple Inc.")).toBeInTheDocument();
    // Valuation ratio.
    expect(screen.getByText("31.20")).toBeInTheDocument();
    // Analyst consensus.
    expect(screen.getByText("buy")).toBeInTheDocument();
    // Statement sections + line items.
    expect(screen.getByText("Income statement")).toBeInTheDocument();
    expect(screen.getByText("Balance sheet")).toBeInTheDocument();
    expect(screen.getByText("Cash flow")).toBeInTheDocument();
    expect(screen.getAllByText("Total Revenue").length).toBeGreaterThan(0);
  });

  it("formats every magnitude with a unit (checklist #1: the missing-B fix)", async () => {
    mockLoad.mockResolvedValue(overview());
    render(<EquityOverviewPanel />);
    await loadSymbol();

    // Currency magnitudes carry a unit suffix — never a bare overflow.
    expect(screen.getByText("$3.00T")).toBeInTheDocument(); // market cap
    expect(screen.getByText("$400B")).toBeInTheDocument(); // revenue (TTM)
    expect(screen.getByText("$95.0B")).toBeInTheDocument(); // free cash flow
    // Bare share count is B-suffixed (the "14.698" bug), not a raw integer.
    expect(screen.getByText("15.50B")).toBeInTheDocument();
    // Curated labels — no snake_case ever renders.
    expect(screen.queryByText(/free_cash_flow|shares_outstanding/)).toBeNull();
  });

  it("formats money fields in the INSTRUMENT's currency, not the region default (R8 §6 / D10)", async () => {
    const f = fundamentals();
    f.currency = "INR";
    const q = quote();
    q.currency = "INR";
    mockLoad.mockResolvedValue(overview({ fundamentals: f, quote: q }));
    render(<EquityOverviewPanel />);
    await loadSymbol("reliance");

    // Market cap / revenue / FCF carry the instrument's ₹ even though the
    // active region default is USD — and vice versa (no ₹ on AAPL).
    expect(screen.getByText("₹3.00T")).toBeInTheDocument();
    expect(screen.getByText("₹400B")).toBeInTheDocument();
    expect(screen.getByText("₹95.0B")).toBeInTheDocument();
    expect(screen.queryByText("$3.00T")).toBeNull();
  });

  it("closes the symbol autocomplete on selection and never re-opens over content (D10)", async () => {
    const { autocompleteSymbols } = await import("./api");
    vi.mocked(autocompleteSymbols).mockResolvedValue([
      {
        symbol: "SAKSOFT.NS",
        name: "Saksoft Limited",
        exchange: "NSE",
        region: "IN",
        asset_class: "equity",
        yahoo_symbol: "SAKSOFT.NS",
        confidence: 0.99,
      },
    ]);
    mockLoad.mockResolvedValue(overview());
    render(<EquityOverviewPanel />);

    const input = screen.getByLabelText("Symbol");
    input.focus();
    fireEvent.change(input, { target: { value: "saksoft" } });
    // Let the 140ms debounce + the mocked fetch resolve.
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 200));
    });
    const option = screen.getByText("Saksoft Limited");

    // onMouseDown selects (fires before blur) — the list must close at once…
    await act(async () => {
      fireEvent.mouseDown(option);
    });
    expect(screen.queryByText("Saksoft Limited")).toBeNull();

    // …and STAY closed: the programmatic draft write ("SAKSOFT.NS") re-runs
    // the debounced autocomplete effect, which used to re-open the dropdown
    // and leave it stuck over the loaded overview.
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 250));
    });
    expect(screen.queryByText("Saksoft Limited")).toBeNull();
  });

  it("degrades gracefully when a section is missing", async () => {
    mockLoad.mockResolvedValue(overview({ ratings: null }));
    render(<EquityOverviewPanel />);
    await loadSymbol();

    expect(screen.getByText("Analyst ratings")).toBeInTheDocument();
    // The failed section renders a composed dense empty state, never bare prose.
    expect(screen.getByText("Ratings unavailable")).toBeInTheDocument();
  });

  it("renders analyst ratings as a labelled metric strip", async () => {
    mockLoad.mockResolvedValue(overview());
    render(<EquityOverviewPanel />);
    await loadSymbol();

    const strip = screen.getByTestId("ratings-strip");
    expect(strip.textContent).toContain("Consensus");
    expect(strip.textContent).toContain("buy");
    expect(strip.textContent).toContain("Target mean");
    expect(strip.textContent).toContain("SB · B · H · S · SS");
    expect(strip.textContent).toContain("12 · 20 · 8 · 1 · 0");
  });

  it("shows an error when every section fails", async () => {
    mockLoad.mockResolvedValue(
      overview({
        quote: null,
        fundamentals: null,
        income: null,
        balance: null,
        cashFlow: null,
        ratings: null,
        allFailed: true,
      }),
    );
    render(<EquityOverviewPanel />);
    await loadSymbol("zzzz");

    expect(screen.getByText("No data available for ZZZZ")).toBeInTheDocument();
  });

  it("surfaces a SidecarError thrown by the loader", async () => {
    mockLoad.mockRejectedValueOnce(new SidecarError(502, "upstream down"));
    render(<EquityOverviewPanel />);
    await loadSymbol();

    expect(screen.getByText("upstream down")).toBeInTheDocument();
  });

  // --- equity-command consumption (R8 seams deliverable 4) -------------------

  it("consumes a command issued BEFORE it mounted (the open-then-command host action race)", async () => {
    mockLoad.mockResolvedValue(overview());
    // The host action fires loadSymbol FIRST (openCompanyOverview / open_panel
    // with a symbol), and the freshly-opened panel subscribes a tick later.
    useEquityCommandStore.getState().loadSymbol("SAKSOFT.NS");
    render(<EquityOverviewPanel />);
    await flushCommandTick();
    expect(mockLoad).toHaveBeenCalledWith("SAKSOFT.NS");
  });

  it("re-issuing the SAME symbol re-triggers the load (seq-keyed consumption)", async () => {
    mockLoad.mockResolvedValue(overview());
    render(<EquityOverviewPanel />);

    await act(async () => {
      useEquityCommandStore.getState().loadSymbol("AAPL");
    });
    await flushCommandTick();
    expect(mockLoad).toHaveBeenCalledTimes(1);

    await act(async () => {
      useEquityCommandStore.getState().loadSymbol("AAPL");
    });
    await flushCommandTick();
    expect(mockLoad).toHaveBeenCalledTimes(2);
    expect(mockLoad).toHaveBeenLastCalledWith("AAPL");
  });

  // --- R13: honest fundamentals coverage — never a silent blank --------------

  describe("R13 — honest fundamentals coverage", () => {
    it("still renders an all-null group's field rows instead of hiding the section", async () => {
      // Ownership is entirely null (no field_meta) — the group used to vanish;
      // it must now still render its section header AND both field rows, each
      // showing the bare glyph (no field_meta -> no reason chip).
      const f = fundamentals({ held_percent_insiders: null, held_percent_institutions: null });
      mockLoad.mockResolvedValue(overview({ fundamentals: f }));
      render(<EquityOverviewPanel />);
      await loadSymbol();

      expect(screen.getByText("Ownership")).toBeInTheDocument();
      expect(screen.getByText("Insiders")).toBeInTheDocument();
      expect(screen.getByText("Institutions")).toBeInTheDocument();
      // Both rows fall back to the plain glyph — no fabricated reason chip.
      expect(screen.queryByText("withheld — implausible")).toBeNull();
      expect(screen.queryByText("unavailable")).toBeNull();
    });

    it("shows a withheld field's short reason chip and the full reason on hover", async () => {
      const reason =
        "84.55 is outside the valid ownership fraction range [0, 1] (8455% — likely a " +
        "percent served as a fraction or a bad source value); withheld";
      const meta: Record<string, FieldMeta> = {
        held_percent_insiders: {
          status: "withheld",
          provider: "yfinance",
          reason,
        },
      };
      const f = fundamentals({ held_percent_insiders: null, field_meta: meta });
      mockLoad.mockResolvedValue(overview({ fundamentals: f }));
      render(<EquityOverviewPanel />);
      await loadSymbol();

      // The dense, always-visible chip — never the full sentence inline.
      const chip = screen.getByText("withheld — implausible");
      expect(chip).toBeInTheDocument();
      // The full backend reason rides the cell's hover tooltip.
      const cell = chip.closest("td");
      expect(cell?.getAttribute("title")).toBe(reason);
    });

    it("an unavailable field with a 'not published' reason chips that phrase; otherwise the generic one", async () => {
      const meta: Record<string, FieldMeta> = {
        peg_ratio: {
          status: "unavailable",
          reason: "PEG is not published for this listing's exchange.",
        },
        price_to_sales: { status: "unavailable" },
      };
      const f = fundamentals({ peg_ratio: null, price_to_sales: null, field_meta: meta });
      mockLoad.mockResolvedValue(overview({ fundamentals: f }));
      render(<EquityOverviewPanel />);
      await loadSymbol();

      expect(screen.getByText("not published")).toBeInTheDocument();
      expect(screen.getByText("unavailable")).toBeInTheDocument();
    });

    it("a served ('ok') field's tooltip states provider · as-of", async () => {
      const meta: Record<string, FieldMeta> = {
        pe_ratio: { status: "ok", provider: "yfinance", as_of: "2026-07-09T12:00:00Z" },
      };
      const f = fundamentals({ field_meta: meta });
      mockLoad.mockResolvedValue(overview({ fundamentals: f }));
      render(<EquityOverviewPanel />);
      await loadSymbol();

      const cell = screen.getByText("31.20").closest("td");
      expect(cell?.getAttribute("title")).toBe("yfinance · 2026-07-09T12:00:00Z");
    });

    it("a flagged-but-kept ('ok' + reason) field's tooltip states the reason, not provider · as-of", async () => {
      const flagReason =
        "market cap 3,000,000,000,000 diverges more than 5% from price x shares " +
        "outstanding; kept, flagged";
      const meta: Record<string, FieldMeta> = {
        market_cap: { status: "ok", provider: "yfinance", reason: flagReason },
      };
      const f = fundamentals({ field_meta: meta });
      mockLoad.mockResolvedValue(overview({ fundamentals: f }));
      render(<EquityOverviewPanel />);
      await loadSymbol();

      const cell = screen.getByText("$3.00T").closest("td");
      expect(cell?.getAttribute("title")).toBe(flagReason);
    });

    it("shows the API rejection reason when fundamentals 404s, not a bare 'unavailable'", async () => {
      mockLoad.mockResolvedValue(
        overview({ fundamentals: null, fundamentalsError: "No fundamentals found for ZZZZ." }),
      );
      render(<EquityOverviewPanel />);
      await loadSymbol("zzzz");

      expect(screen.getByText("No fundamentals found for ZZZZ.")).toBeInTheDocument();
    });

    it("falls back to the fundamentals snapshot's as-of date when the quote carries no freshness", async () => {
      // This file's quote() fixture already omits `freshness` (optional on the
      // wire) — the default case the badge must still handle honestly.
      const meta: Record<string, FieldMeta> = {
        pe_ratio: { status: "ok", provider: "yfinance", as_of: "2026-07-08T09:30:00Z" },
      };
      const f = fundamentals({ field_meta: meta });
      mockLoad.mockResolvedValue(overview({ fundamentals: f }));
      render(<EquityOverviewPanel />);
      await loadSymbol();

      expect(screen.getByText(/as of 2026-07-08/)).toBeInTheDocument();
    });
  });
});
