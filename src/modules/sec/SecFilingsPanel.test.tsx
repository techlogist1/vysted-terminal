/**
 * SecFilingsPanel — mount + interaction tests.
 *
 * Mocks the sidecar client at the module boundary so the panel runs
 * without a live sidecar. The store is reset between tests.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

vi.mock("@/lib/host-actions", () => ({
  loadSymbolIntoChart: vi.fn(),
}));

import { loadSymbolIntoChart } from "@/lib/host-actions";
import * as sidecarClient from "@/lib/sidecar-client";
import { usePanelContextBus } from "@/store/panel-context";
import { useSecStore } from "@/store/sec";

import type { FilingsListResponse } from "../../../types/sec";

import { SecFilingsPanel } from "./SecFilingsPanel";

const AAPL_FILINGS: FilingsListResponse = {
  cik: "0000320193",
  company_name: "Apple Inc.",
  symbol: "AAPL",
  filings: [
    {
      accession: "0000320193-24-000123",
      cik: "0000320193",
      company_name: "Apple Inc.",
      symbol: "AAPL",
      form_type: "10-K",
      filed_date: "2024-11-01",
      period_of_report: "2024-09-28",
      edgar_url: "https://www.sec.gov/Archives/edgar/data/320193/123/",
    },
    {
      accession: "0000320193-24-000100",
      cik: "0000320193",
      company_name: "Apple Inc.",
      symbol: "AAPL",
      form_type: "10-Q",
      filed_date: "2024-08-02",
      period_of_report: "2024-06-29",
      edgar_url: "https://www.sec.gov/Archives/edgar/data/320193/100/",
    },
  ],
};

beforeEach(() => {
  vi.spyOn(sidecarClient, "getSidecarBaseUrl").mockResolvedValue("http://127.0.0.1:9999");
  vi.spyOn(sidecarClient, "sidecarGet").mockResolvedValue(AAPL_FILINGS);
  useSecStore.getState().__resetForTests();
  usePanelContextBus.setState({ lastEventBySource: {}, focusedSource: null, updatedAt: 0 });
  vi.mocked(loadSymbolIntoChart).mockClear();
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("SecFilingsPanel", () => {
  it("renders the panel chrome on mount", async () => {
    render(<SecFilingsPanel />);
    expect(screen.getByTestId("sec-filings-panel")).toBeInTheDocument();
    expect(screen.getByTestId("sec-symbol-input")).toBeInTheDocument();
    expect(screen.getByTestId("sec-form-filter")).toBeInTheDocument();
  });

  it("auto-loads filings for AAPL on first mount", async () => {
    render(<SecFilingsPanel />);
    await waitFor(() => {
      expect(screen.getByTestId("filings-list-table")).toBeInTheDocument();
    });
    expect(screen.getByTestId("filings-row-0000320193-24-000123")).toBeInTheDocument();
    expect(screen.getByTestId("filings-row-0000320193-24-000100")).toBeInTheDocument();
  });

  it("R15-CODE-DATA-014: a filingsByIdentifier update after mount re-renders the row count", async () => {
    render(<SecFilingsPanel />);
    await waitFor(() => screen.getByTestId("filings-list-table"));
    expect(screen.getByTestId("filings-row-0000320193-24-000123")).toBeInTheDocument();

    // Write straight into the store, bypassing loadFilings entirely — the
    // panel must pick this up via its own subscription, not a stale
    // getState() snapshot taken at some earlier render.
    useSecStore.setState((state) => ({
      filingsByIdentifier: {
        ...state.filingsByIdentifier,
        "AAPL::all": {
          ...AAPL_FILINGS,
          filings: [
            ...AAPL_FILINGS.filings,
            {
              accession: "0000320193-24-000099",
              cik: "0000320193",
              company_name: "Apple Inc.",
              symbol: "AAPL",
              form_type: "8-K",
              filed_date: "2024-05-01",
              period_of_report: "2024-04-29",
              edgar_url: "https://www.sec.gov/Archives/edgar/data/320193/99/",
            },
          ],
        },
      },
    }));

    await waitFor(() => {
      expect(screen.getByTestId("filings-row-0000320193-24-000099")).toBeInTheDocument();
    });
  });

  it("submits a new symbol via the form", async () => {
    render(<SecFilingsPanel />);
    await waitFor(() => screen.getByTestId("filings-list-table"));

    const input = screen.getByTestId("sec-symbol-input") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "MSFT" } });
    fireEvent.click(screen.getByTestId("sec-symbol-submit"));

    await waitFor(() => {
      expect(sidecarClient.sidecarGet).toHaveBeenCalledWith(
        "/sec/filings",
        expect.objectContaining({ symbol: "MSFT" }),
      );
    });
  });

  it("R15-UI-032: typing shows company-search suggestions; picking one loads it", async () => {
    render(<SecFilingsPanel />);
    await waitFor(() => screen.getByTestId("filings-list-table"));

    (sidecarClient.sidecarGet as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      results: [{ cik: "0000789019", name: "Microsoft Corporation", ticker: "MSFT" }],
    });

    const input = screen.getByTestId("sec-symbol-input") as HTMLInputElement;
    input.focus();
    fireEvent.change(input, { target: { value: "micro" } });

    await waitFor(() => {
      expect(screen.getByTestId("sec-symbol-suggestions")).toBeInTheDocument();
    });
    expect(screen.getByText("Microsoft Corporation")).toBeInTheDocument();

    (sidecarClient.sidecarGet as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ...AAPL_FILINGS,
      cik: "0000789019",
      company_name: "Microsoft Corporation",
      symbol: "MSFT",
    });
    fireEvent.mouseDown(screen.getByText("Microsoft Corporation"));

    await waitFor(() => {
      expect(sidecarClient.sidecarGet).toHaveBeenCalledWith(
        "/sec/filings",
        expect.objectContaining({ symbol: "MSFT" }),
      );
    });
    expect(screen.queryByTestId("sec-symbol-suggestions")).toBeNull();
  });

  it("switches to the insider tab", async () => {
    render(<SecFilingsPanel />);
    await waitFor(() => screen.getByTestId("filings-list-table"));

    // The insider tab dispatches a separate fetch; return an insider-
    // shaped payload so InsiderTradingTable renders without re-using
    // the filings-shaped default mock above.
    (sidecarClient.sidecarGet as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      cik: "0000320193",
      issuer_name: "Apple Inc.",
      transactions: [],
    });

    fireEvent.click(screen.getByTestId("sec-tab-insider"));
    await waitFor(() => {
      expect(screen.getByTestId("insider-trading-table")).toBeInTheDocument();
    });
  });

  it("clicking a filing row opens the FilingViewer", async () => {
    render(<SecFilingsPanel />);
    await waitFor(() => screen.getByTestId("filings-list-table"));

    // Stub the detail fetch — the panel will dispatch it on click.
    (sidecarClient.sidecarGet as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      filing: AAPL_FILINGS.filings[0],
      sections: [{ id: "item-1", title: "Item 1", text: "Body", word_count: 1 }],
      total_chars: 4,
    });

    fireEvent.click(screen.getByTestId("filings-row-0000320193-24-000123"));
    await waitFor(() => {
      expect(screen.getByTestId("filing-viewer")).toBeInTheDocument();
    });
  });

  it("publishes the active identifier + tab to the panel context bus (R15-AGENT-053)", async () => {
    render(<SecFilingsPanel />);
    await waitFor(() => {
      expect(usePanelContextBus.getState().lastEventBySource["sec-filings"]).toBeDefined();
    });
    const payload = usePanelContextBus.getState().lastEventBySource["sec-filings"]!.payload as {
      identifier: string | null;
      tab: string;
    };
    expect(payload).toMatchObject({ identifier: "AAPL", tab: "filings" });
  });

  it("clicking the company name/identifier loads it into the chart (R15-AGENT-053)", async () => {
    render(<SecFilingsPanel />);
    fireEvent.click(await screen.findByTestId("sec-symbol-AAPL"));
    expect(loadSymbolIntoChart).toHaveBeenCalledWith("AAPL");
  });
});
