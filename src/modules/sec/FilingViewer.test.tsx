/**
 * FilingViewer — section navigation + EDGAR link tests.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import * as sidecarClient from "@/lib/sidecar-client";
import { useSecStore } from "@/store/sec";

import type { FilingDetail } from "../../../types/sec";

import { FilingViewer } from "./FilingViewer";

const DETAIL: FilingDetail = {
  filing: {
    accession: "0000320193-24-000123",
    cik: "0000320193",
    company_name: "Apple Inc.",
    symbol: "AAPL",
    form_type: "10-K",
    filed_date: "2024-11-01",
    period_of_report: "2024-09-28",
    edgar_url: "https://www.sec.gov/Archives/edgar/data/320193/123/",
  },
  sections: [
    { id: "item-1", title: "Item 1. Business", text: "We design", word_count: 2 },
    { id: "item-1a", title: "Item 1A. Risk Factors", text: "Macro risk", word_count: 2 },
    { id: "item-7", title: "Item 7. MD&A", text: "Revenue grew", word_count: 2 },
  ],
  total_chars: 30,
};

beforeEach(() => {
  vi.spyOn(sidecarClient, "getSidecarBaseUrl").mockResolvedValue("http://127.0.0.1:9999");
  vi.spyOn(sidecarClient, "sidecarGet").mockResolvedValue(DETAIL);
  useSecStore.getState().__resetForTests();
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("FilingViewer", () => {
  it("renders an empty state when no accession is selected", () => {
    render(<FilingViewer accession={null} identifier="AAPL" onClose={() => {}} />);
    expect(screen.getByText(/Select a filing/i)).toBeInTheDocument();
  });

  it("loads detail and renders the first section by default", async () => {
    render(
      <FilingViewer
        accession="0000320193-24-000123"
        identifier="AAPL"
        onClose={() => {}}
      />,
    );
    await waitFor(() => {
      expect(screen.getByTestId("filing-viewer")).toBeInTheDocument();
    });
    await waitFor(() => {
      expect(screen.getByTestId("filing-section-item-1")).toBeInTheDocument();
    });
    expect(screen.getAllByText(/Item 1\. Business/i).length).toBeGreaterThan(0);
  });

  it("switches the body when a different section is clicked", async () => {
    render(
      <FilingViewer
        accession="0000320193-24-000123"
        identifier="AAPL"
        onClose={() => {}}
      />,
    );
    await waitFor(() => screen.getByTestId("filing-section-item-1a"));
    fireEvent.click(screen.getByTestId("filing-section-item-1a"));
    await waitFor(() => {
      const body = screen.getByTestId("filing-viewer-body");
      expect(body.textContent).toContain("Macro risk");
    });
  });

  it("the EDGAR link button is rendered with the canonical URL", async () => {
    render(
      <FilingViewer
        accession="0000320193-24-000123"
        identifier="AAPL"
        onClose={() => {}}
      />,
    );
    const btn = await waitFor(() => screen.getByTestId("filing-viewer-edgar-link"));
    expect(btn).toBeInTheDocument();
  });

  it("clicking back fires onClose", async () => {
    const onClose = vi.fn();
    render(
      <FilingViewer
        accession="0000320193-24-000123"
        identifier="AAPL"
        onClose={onClose}
      />,
    );
    const btn = await waitFor(() => screen.getByTestId("filing-viewer-close"));
    fireEvent.click(btn);
    expect(onClose).toHaveBeenCalled();
  });
});
