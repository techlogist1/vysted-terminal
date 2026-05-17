/**
 * InsiderTradingTable — load + render + form-filter tests.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import * as sidecarClient from "@/lib/sidecar-client";
import { useSecStore } from "@/store/sec";

import type { InsiderTransactionsResponse } from "../../../types/sec";

import { InsiderTradingTable } from "./InsiderTradingTable";

const FIXTURE: InsiderTransactionsResponse = {
  cik: "0000320193",
  issuer_name: "Apple Inc.",
  transactions: [
    {
      accession: "0000320193-24-001000",
      reporter_name: "Cook Timothy D",
      reporter_cik: "0001214156",
      issuer_cik: "0000320193",
      issuer_name: "Apple Inc.",
      issuer_symbol: "AAPL",
      form_type: "4",
      transaction_date: "2024-12-01",
      direction: "disposed",
      shares: "511000",
      price_per_share: "190.50",
      transaction_value: "97345500",
      transaction_code: "S",
      reporter_title: "CEO",
    },
    {
      accession: "0000320193-24-001001",
      reporter_name: "Maestri Luca",
      reporter_cik: "0001545330",
      issuer_cik: "0000320193",
      issuer_name: "Apple Inc.",
      issuer_symbol: "AAPL",
      form_type: "4",
      transaction_date: "2024-11-20",
      direction: "acquired",
      shares: "75000",
      price_per_share: null,
      transaction_value: null,
      transaction_code: "A",
      reporter_title: "SVP and CFO",
    },
  ],
};

beforeEach(() => {
  vi.spyOn(sidecarClient, "getSidecarBaseUrl").mockResolvedValue("http://127.0.0.1:9999");
  vi.spyOn(sidecarClient, "sidecarGet").mockResolvedValue(FIXTURE);
  useSecStore.getState().__resetForTests();
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("InsiderTradingTable", () => {
  it("renders the table chrome", () => {
    render(<InsiderTradingTable identifier={null} />);
    expect(screen.getByTestId("insider-trading-table")).toBeInTheDocument();
  });

  it("loads insider transactions for an identifier and renders rows", async () => {
    render(<InsiderTradingTable identifier="AAPL" />);
    await waitFor(() => {
      expect(screen.getByTestId("insider-row-0000320193-24-001000-0001214156")).toBeInTheDocument();
    });
    expect(screen.getByText("Cook Timothy D")).toBeInTheDocument();
    // Comma-formatted shares
    expect(screen.getByText(/511,000/)).toBeInTheDocument();
  });

  it("colours acquired and disposed differently (via class assertion)", async () => {
    const { container } = render(<InsiderTradingTable identifier="AAPL" />);
    await waitFor(() => screen.getByTestId("insider-row-0000320193-24-001000-0001214156"));
    const disposed = container.querySelector(".text-rose-300");
    const acquired = container.querySelector(".text-emerald-300");
    expect(disposed).not.toBeNull();
    expect(acquired).not.toBeNull();
  });

  it("changing the form filter re-fetches", async () => {
    render(<InsiderTradingTable identifier="AAPL" />);
    await waitFor(() => screen.getByTestId("insider-form-filter"));

    const select = screen.getByTestId("insider-form-filter") as HTMLSelectElement;
    fireEvent.change(select, { target: { value: "all" } });

    await waitFor(() => {
      const calls = (sidecarClient.sidecarGet as ReturnType<typeof vi.fn>).mock.calls;
      // Find a call where the params object lacks the `form` key (i.e. "all").
      const allCall = calls.find(
        (c) =>
          typeof c[0] === "string" &&
          c[0].startsWith("/sec/insider/") &&
          !(c[1] && Object.prototype.hasOwnProperty.call(c[1], "form")),
      );
      expect(allCall).toBeTruthy();
    });
  });
});
