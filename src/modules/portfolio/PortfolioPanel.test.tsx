import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";

import { SidecarError } from "@/lib/sidecar-client";
import type { Position, Quote } from "../../../types/data";
import { PortfolioPanel } from "./PortfolioPanel";

vi.mock("./api", () => ({
  fetchPositions: vi.fn(),
  createPosition: vi.fn(),
  updatePosition: vi.fn(),
  deletePosition: vi.fn(),
  fetchPositionQuotes: vi.fn(),
}));

const api = await import("./api");
const mockFetchPositions = vi.mocked(api.fetchPositions);
const mockCreatePosition = vi.mocked(api.createPosition);
const mockUpdatePosition = vi.mocked(api.updatePosition);
const mockDeletePosition = vi.mocked(api.deletePosition);
const mockFetchQuotes = vi.mocked(api.fetchPositionQuotes);

function position(overrides: Partial<Position> = {}): Position {
  return {
    id: 1,
    symbol: "AAPL",
    quantity: 10,
    cost_basis: 150,
    asset_class: "equity",
    opened_at: null,
    note: null,
    ...overrides,
  };
}

function quote(symbol: string, price: number): Quote {
  return {
    symbol,
    price,
    change: 0,
    change_percent: 0,
    volume: null,
    currency: "USD",
    market_state: null,
    timestamp: "2026-05-15T00:00:00Z",
    provider: "yfinance",
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  mockFetchPositions.mockResolvedValue([]);
  mockFetchQuotes.mockResolvedValue(new Map());
});

afterEach(() => {
  cleanup();
});

describe("PortfolioPanel", () => {
  it("shows a loading state then the empty message", async () => {
    render(<PortfolioPanel />);
    expect(screen.getByText("Loading portfolio…")).toBeInTheDocument();
    expect(await screen.findByText("No positions yet — add one above.")).toBeInTheDocument();
  });

  it("lists positions with computed P&L and weight", async () => {
    mockFetchPositions.mockResolvedValue([position()]);
    mockFetchQuotes.mockResolvedValue(new Map([["AAPL", quote("AAPL", 200)]]));
    render(<PortfolioPanel />);
    expect(await screen.findByText("AAPL")).toBeInTheDocument();
    // 10 shares, cost 150 → cost 1500; price 200 → mkt 2000; P&L +500 (+33.33%).
    // The value appears in both the summary header and the position row.
    expect(screen.getAllByText("+$500.00 (+33.33%)").length).toBeGreaterThanOrEqual(2);
    // Single position → 100% weight; the row cell sits in the positions table.
    const weightCell = screen.getAllByText("100.0%").find((node) => node.tagName === "TD");
    expect(weightCell).toBeDefined();
  });

  it("surfaces a SidecarError from the initial load", async () => {
    mockFetchPositions.mockRejectedValueOnce(new SidecarError(502, "sidecar offline"));
    render(<PortfolioPanel />);
    expect(await screen.findByText("sidecar offline")).toBeInTheDocument();
  });

  it("creates a position through the form", async () => {
    mockCreatePosition.mockResolvedValue(position());
    render(<PortfolioPanel />);
    await screen.findByText("No positions yet — add one above.");

    fireEvent.change(screen.getByLabelText("Symbol"), { target: { value: "nvda" } });
    fireEvent.change(screen.getByLabelText("Quantity"), { target: { value: "5" } });
    fireEvent.change(screen.getByLabelText("Cost basis"), { target: { value: "900" } });
    await act(async () => {
      fireEvent.submit(screen.getByLabelText("Symbol").closest("form")!);
    });

    expect(mockCreatePosition).toHaveBeenCalledWith(
      expect.objectContaining({ symbol: "NVDA", quantity: 5, cost_basis: 900 }),
    );
  });

  it("deletes a position through the row control", async () => {
    mockFetchPositions.mockResolvedValue([position()]);
    mockDeletePosition.mockResolvedValue(undefined);
    render(<PortfolioPanel />);
    await screen.findByText("AAPL");

    await act(async () => {
      fireEvent.click(screen.getByLabelText("Delete AAPL"));
    });
    expect(mockDeletePosition).toHaveBeenCalledWith(1);
  });

  it("loads a position into the form for editing and updates it", async () => {
    mockFetchPositions.mockResolvedValue([position()]);
    mockUpdatePosition.mockResolvedValue(position({ quantity: 20 }));
    render(<PortfolioPanel />);
    await screen.findByText("AAPL");

    fireEvent.click(screen.getByLabelText("Edit AAPL"));
    expect((screen.getByLabelText("Symbol") as HTMLInputElement).value).toBe("AAPL");

    fireEvent.change(screen.getByLabelText("Quantity"), { target: { value: "20" } });
    await act(async () => {
      fireEvent.submit(screen.getByLabelText("Symbol").closest("form")!);
    });
    expect(mockUpdatePosition).toHaveBeenCalledWith(
      1,
      expect.objectContaining({ symbol: "AAPL", quantity: 20 }),
    );
  });
});
