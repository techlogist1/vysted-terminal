/**
 * Macro store tests (Teammate M, Phase 6).
 *
 * The sidecar surface (``sidecarGet``) is mocked; tests cover the load /
 * search / catalog flows, the cache-by-key behaviour, and the
 * referentially-stable selector contract.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { MacroCatalog, MacroSearchResult, MacroSeriesExtended } from "../../types/macro";

vi.mock("@/lib/sidecar-client", () => ({
  SidecarError: class extends Error {
    status: number;
    constructor(status: number, message: string) {
      super(message);
      this.status = status;
    }
  },
  sidecarGet: vi.fn(),
}));

import { sidecarGet } from "@/lib/sidecar-client";

import {
  selectCatalog,
  selectSearchResults,
  selectSelected,
  selectSeriesStatus,
  useMacroStore,
} from "./macro";

const SAMPLE_SERIES: MacroSeriesExtended = {
  series_id: "DGS10",
  title: "10-Year Treasury",
  units: "Percent",
  observations: [{ date: "2026-05-14T00:00:00Z", value: 4.25 }],
  provider: "fred",
  frequency: "daily",
  last_updated: "2026-05-14T09:00:00Z",
  seasonal_adjustment: "not-adjusted",
  source_url: "https://fred.stlouisfed.org/series/DGS10",
  notes: null,
};

const SAMPLE_SEARCH: MacroSearchResult[] = [
  {
    provider: "fred",
    series_id: "DGS10",
    title: "10-Year Treasury",
    frequency: "daily",
    units: "Percent",
    score: 0.95,
  },
];

const SAMPLE_CATALOG: MacroCatalog = {
  provider: "fred",
  entries: [
    {
      provider: "fred",
      series_id: "DGS10",
      title: "10-Year Treasury",
      category: "Interest Rates",
      frequency: "daily",
      units: "Percent",
    },
  ],
};

beforeEach(() => {
  useMacroStore.getState().reset();
  vi.clearAllMocks();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("useMacroStore — loadSeries", () => {
  it("caches a successfully loaded series", async () => {
    vi.mocked(sidecarGet).mockResolvedValueOnce(SAMPLE_SERIES);
    await useMacroStore.getState().loadSeries("fred", "DGS10");
    const status = selectSeriesStatus(useMacroStore.getState(), "fred", "DGS10");
    expect(status?.status).toBe("ready");
    expect(status?.series?.series_id).toBe("DGS10");
  });

  it("records an error when the sidecar fails", async () => {
    vi.mocked(sidecarGet).mockRejectedValueOnce(new Error("network is gone"));
    await useMacroStore.getState().loadSeries("fred", "DGS10");
    const status = selectSeriesStatus(useMacroStore.getState(), "fred", "DGS10");
    expect(status?.status).toBe("error");
    expect(status?.error).toContain("network is gone");
  });

  it("returns undefined status for an unknown (provider, series)", () => {
    const status = selectSeriesStatus(useMacroStore.getState(), "fred", "X");
    expect(status).toBeUndefined();
  });

  it("does nothing when seriesId is empty", async () => {
    await useMacroStore.getState().loadSeries("fred", "");
    expect(sidecarGet).not.toHaveBeenCalled();
  });
});

describe("useMacroStore — search", () => {
  it("caches results by (provider, query)", async () => {
    vi.mocked(sidecarGet).mockResolvedValueOnce(SAMPLE_SEARCH);
    await useMacroStore.getState().search("fred", "treasury");
    const rows = selectSearchResults(useMacroStore.getState(), "fred", "treasury");
    expect(rows).toHaveLength(1);
    expect(rows[0].series_id).toBe("DGS10");
  });

  it("returns the same frozen empty array reference for an unseen query", () => {
    const a = selectSearchResults(useMacroStore.getState(), "fred", "rare-query");
    const b = selectSearchResults(useMacroStore.getState(), "imf", "another");
    expect(a).toBe(b);
    expect(a).toHaveLength(0);
  });

  it("captures empty results on search failure", async () => {
    vi.mocked(sidecarGet).mockRejectedValueOnce(new Error("nope"));
    await useMacroStore.getState().search("fred", "treasury");
    const rows = selectSearchResults(useMacroStore.getState(), "fred", "treasury");
    expect(rows).toHaveLength(0);
  });

  it("does nothing when query is empty", async () => {
    await useMacroStore.getState().search("fred", "");
    expect(sidecarGet).not.toHaveBeenCalled();
  });
});

describe("useMacroStore — loadCatalog", () => {
  it("caches the catalog on first load", async () => {
    vi.mocked(sidecarGet).mockResolvedValueOnce(SAMPLE_CATALOG);
    await useMacroStore.getState().loadCatalog("fred");
    expect(selectCatalog(useMacroStore.getState(), "fred")?.entries).toHaveLength(1);
  });

  it("returns the same cached catalog and does not re-fetch", async () => {
    vi.mocked(sidecarGet).mockResolvedValueOnce(SAMPLE_CATALOG);
    await useMacroStore.getState().loadCatalog("fred");
    await useMacroStore.getState().loadCatalog("fred");
    expect(sidecarGet).toHaveBeenCalledTimes(1);
  });
});

describe("useMacroStore — select", () => {
  it("records the current selection", () => {
    useMacroStore.getState().select("ecb", "FM.D.U2.EUR.4F.KR.MRR_FR.LEV");
    const sel = selectSelected(useMacroStore.getState());
    expect(sel?.provider).toBe("ecb");
    expect(sel?.seriesId).toBe("FM.D.U2.EUR.4F.KR.MRR_FR.LEV");
  });

  it("reset clears every cache and the selection", async () => {
    vi.mocked(sidecarGet).mockResolvedValueOnce(SAMPLE_SERIES);
    await useMacroStore.getState().loadSeries("fred", "DGS10");
    useMacroStore.getState().reset();
    expect(useMacroStore.getState().seriesStatus).toEqual({});
    expect(useMacroStore.getState().selected).toBeNull();
  });
});
