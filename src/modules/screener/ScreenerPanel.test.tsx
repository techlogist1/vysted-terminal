/**
 * ScreenerPanel tests — Phase 6 (Teammate Sc backend; v0.6.1 lead-completed frontend).
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import type { ScreenerResult, ScreenerUniverse } from "../../../types/screener";

vi.mock("@/lib/sidecar-client", () => ({
  getSidecarBaseUrl: vi.fn().mockResolvedValue("http://127.0.0.1:9000"),
  sidecarGet: vi.fn(),
}));

import { sidecarGet } from "@/lib/sidecar-client";

import { useScreenerStore } from "@/store/screener";

import { ScreenerPanel } from "./ScreenerPanel";

const UNIVERSE_SAMPLE: ScreenerUniverse = {
  id: "sp500",
  label: "S&P 500",
  symbols: ["AAPL", "MSFT", "NVDA", "GOOGL", "META"],
  asset_class: "equity",
};

const RESULT_SAMPLE: ScreenerResult = {
  universe: "sp500",
  evaluated_count: 100,
  result_count: 2,
  rows: [
    {
      symbol: "AAPL",
      name: "Apple Inc.",
      sector: "Technology",
      industry: "Consumer Electronics",
      market_cap: 3_000_000_000_000,
      pe_ratio: 18.5,
      price: 192.5,
      change_percent_1d: 1.5,
      volume: 51_000_000,
      matched_criteria: [0, 1, 2],
    },
    {
      symbol: "GOOGL",
      name: "Alphabet Inc.",
      sector: "Technology",
      industry: "Internet Content",
      market_cap: 2_100_000_000_000,
      pe_ratio: 19.0,
      price: 175.0,
      change_percent_1d: -0.3,
      volume: 18_000_000,
      matched_criteria: [0, 1, 2],
    },
  ],
  duration_ms: 320.0,
};

beforeEach(() => {
  useScreenerStore.getState().__resetForTests();
  vi.mocked(sidecarGet).mockResolvedValue(UNIVERSE_SAMPLE);
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify(RESULT_SAMPLE), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("ScreenerPanel", () => {
  it("renders the universe picker + default criteria + run button", () => {
    render(<ScreenerPanel />);
    expect(screen.getByLabelText(/universe/i)).toBeInTheDocument();
    expect(screen.getByTestId("run-screener-button")).toBeInTheDocument();
    // default seeded criteria
    expect(screen.getByTestId("criterion-row-0")).toBeInTheDocument();
    expect(screen.getByTestId("criterion-row-1")).toBeInTheDocument();
    expect(screen.getByTestId("criterion-row-2")).toBeInTheDocument();
  });

  it("shows the ticker count after universe load", async () => {
    render(<ScreenerPanel />);
    await waitFor(() => {
      expect(screen.getByText(/5 tickers/i)).toBeInTheDocument();
    });
  });

  it("clicking Run posts to /screener/run and renders the results table", async () => {
    render(<ScreenerPanel />);
    fireEvent.click(screen.getByTestId("run-screener-button"));
    await waitFor(() => {
      expect(screen.getByText(/Apple Inc\./)).toBeInTheDocument();
      expect(screen.getByText(/Alphabet Inc\./)).toBeInTheDocument();
    });
    // the universe id is rendered as a status label on the results header
    expect(screen.getByText(/sp500/i)).toBeInTheDocument();
  });

  it("switching to the custom universe reveals the symbols input", () => {
    render(<ScreenerPanel />);
    fireEvent.change(screen.getByLabelText(/universe/i), { target: { value: "custom" } });
    expect(screen.getByLabelText(/symbols/i)).toBeInTheDocument();
  });

  it("an error response surfaces as an inline banner", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: "universe unreachable" }), { status: 502 }),
    );
    render(<ScreenerPanel />);
    fireEvent.click(screen.getByTestId("run-screener-button"));
    await waitFor(() => {
      expect(screen.getByText(/universe unreachable/)).toBeInTheDocument();
    });
  });
});
