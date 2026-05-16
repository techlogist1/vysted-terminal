/**
 * SEC EDGAR filings store tests — load paths, caching, selectors.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";

import type {
  FilingDetail,
  FilingsListResponse,
  InsiderTransactionsResponse,
} from "../../types/sec";

import { selectFilingDetail, selectFilings, selectInsider, useSecStore } from "./sec";

vi.mock("@/lib/sidecar-client", () => ({
  getSidecarBaseUrl: vi.fn().mockResolvedValue("http://127.0.0.1:9000"),
  sidecarGet: vi.fn(),
}));

import { sidecarGet } from "@/lib/sidecar-client";

const FILINGS_FIXTURE: FilingsListResponse = {
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

const DETAIL_FIXTURE: FilingDetail = {
  filing: FILINGS_FIXTURE.filings[0],
  sections: [
    { id: "item-1", title: "Item 1. Business", text: "Body 1", word_count: 50 },
    { id: "item-1a", title: "Item 1A. Risk Factors", text: "Body 2", word_count: 100 },
  ],
  total_chars: 14,
};

const INSIDER_FIXTURE: InsiderTransactionsResponse = {
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
  ],
};

beforeEach(() => {
  useSecStore.getState().__resetForTests();
  (sidecarGet as ReturnType<typeof vi.fn>).mockReset();
});

describe("useSecStore.loadFilings", () => {
  it("hits /sec/filings with the right params for a symbol", async () => {
    (sidecarGet as ReturnType<typeof vi.fn>).mockResolvedValueOnce(FILINGS_FIXTURE);
    await useSecStore.getState().loadFilings("AAPL", "10-K");
    expect(sidecarGet).toHaveBeenCalledWith("/sec/filings", {
      limit: 40,
      symbol: "AAPL",
      form_type: "10-K",
    });
    expect(useSecStore.getState().filingsStatus).toBe("ready");
    expect(useSecStore.getState().activeIdentifier).toBe("AAPL");
  });

  it("hits /sec/filings with cik= for a numeric identifier", async () => {
    (sidecarGet as ReturnType<typeof vi.fn>).mockResolvedValueOnce(FILINGS_FIXTURE);
    await useSecStore.getState().loadFilings("320193");
    expect(sidecarGet).toHaveBeenCalledWith("/sec/filings", { limit: 40, cik: "320193" });
  });

  it("captures network errors in filingsError", async () => {
    (sidecarGet as ReturnType<typeof vi.fn>).mockRejectedValueOnce(new Error("boom"));
    await useSecStore.getState().loadFilings("AAPL");
    expect(useSecStore.getState().filingsStatus).toBe("error");
    expect(useSecStore.getState().filingsError).toBe("boom");
  });
});

describe("useSecStore.loadFilingDetail", () => {
  it("hits /sec/filings/{accession}?identifier=", async () => {
    (sidecarGet as ReturnType<typeof vi.fn>).mockResolvedValueOnce(DETAIL_FIXTURE);
    await useSecStore.getState().loadFilingDetail("0000320193-24-000123", "AAPL");
    expect(sidecarGet).toHaveBeenCalledWith("/sec/filings/0000320193-24-000123", {
      identifier: "AAPL",
    });
    expect(useSecStore.getState().filingDetailStatus).toBe("ready");
    expect(useSecStore.getState().activeAccession).toBe("0000320193-24-000123");
  });
});

describe("useSecStore.loadInsider", () => {
  it("hits /sec/insider/{identifier}?form=", async () => {
    (sidecarGet as ReturnType<typeof vi.fn>).mockResolvedValueOnce(INSIDER_FIXTURE);
    await useSecStore.getState().loadInsider("AAPL", "4");
    expect(sidecarGet).toHaveBeenCalledWith("/sec/insider/AAPL", { limit: 50, form: "4" });
    expect(useSecStore.getState().insiderStatus).toBe("ready");
  });
});

describe("selectors", () => {
  it("selectFilings returns the frozen empty when nothing is loaded", () => {
    const fst = selectFilings("AAPL", undefined);
    const snd = selectFilings("AAPL", undefined);
    expect(fst).toBe(snd); // referential equality (frozen empty)
    expect(fst.filings).toHaveLength(0);
  });

  it("selectFilings returns the loaded payload by identifier+form", async () => {
    (sidecarGet as ReturnType<typeof vi.fn>).mockResolvedValueOnce(FILINGS_FIXTURE);
    await useSecStore.getState().loadFilings("AAPL", "10-K");
    const sel = selectFilings("AAPL", "10-K");
    expect(sel.filings).toHaveLength(2);
    expect(sel.company_name).toBe("Apple Inc.");
  });

  it("selectFilingDetail returns null on miss and the detail on hit", async () => {
    expect(selectFilingDetail("0000320193-24-000123")).toBeNull();
    (sidecarGet as ReturnType<typeof vi.fn>).mockResolvedValueOnce(DETAIL_FIXTURE);
    await useSecStore.getState().loadFilingDetail("0000320193-24-000123", "AAPL");
    expect(selectFilingDetail("0000320193-24-000123")?.sections).toHaveLength(2);
  });

  it("selectInsider returns frozen empty on miss", () => {
    expect(selectInsider("AAPL", "4")).toBe(selectInsider("AAPL", "4"));
  });
});

describe("searchCompanies", () => {
  it("hits /sec/filings/search and stores results", async () => {
    (sidecarGet as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      results: [{ cik: "0000320193", name: "Apple Inc.", ticker: "AAPL" }],
    });
    await useSecStore.getState().searchCompanies("apple");
    expect(useSecStore.getState().searchResults).toHaveLength(1);
    expect(useSecStore.getState().searchStatus).toBe("ready");
  });

  it("skips the network call for an empty query", async () => {
    await useSecStore.getState().searchCompanies("  ");
    expect(sidecarGet).not.toHaveBeenCalled();
    expect(useSecStore.getState().searchResults).toHaveLength(0);
  });
});
