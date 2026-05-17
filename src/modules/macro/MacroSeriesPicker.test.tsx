import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { MacroCatalog, MacroSearchResult } from "../../../types/macro";

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

import { useMacroStore } from "@/store/macro";

import { MacroSeriesPicker } from "./MacroSeriesPicker";

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
    {
      provider: "fred",
      series_id: "GDP",
      title: "Gross Domestic Product",
      category: "National Accounts",
      frequency: "quarterly",
      units: "Billions of Dollars",
    },
  ],
};

const SAMPLE_SEARCH: MacroSearchResult[] = [
  {
    provider: "fred",
    series_id: "DGS2",
    title: "2-Year Treasury",
    frequency: "daily",
    units: "Percent",
    score: 0.8,
  },
];

beforeEach(() => {
  useMacroStore.getState().reset();
  vi.clearAllMocks();
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("MacroSeriesPicker", () => {
  it("renders the four provider tabs", () => {
    vi.mocked(sidecarGet).mockResolvedValueOnce(SAMPLE_CATALOG);
    render(
      <MacroSeriesPicker
        provider="fred"
        onProviderChange={() => undefined}
        onSelect={() => undefined}
      />,
    );
    expect(screen.getByTestId("macro-provider-fred")).toBeInTheDocument();
    expect(screen.getByTestId("macro-provider-ecb")).toBeInTheDocument();
    expect(screen.getByTestId("macro-provider-imf")).toBeInTheDocument();
    expect(screen.getByTestId("macro-provider-world-bank")).toBeInTheDocument();
  });

  it("loads the catalog on mount", async () => {
    vi.mocked(sidecarGet).mockResolvedValueOnce(SAMPLE_CATALOG);
    render(
      <MacroSeriesPicker
        provider="fred"
        onProviderChange={() => undefined}
        onSelect={() => undefined}
      />,
    );
    await waitFor(() =>
      expect(sidecarGet).toHaveBeenCalledWith("/macro/catalog", { provider: "fred" }),
    );
    await waitFor(() => expect(screen.getByText("10-Year Treasury")).toBeInTheDocument());
  });

  it("fires onProviderChange when a tab is clicked", () => {
    vi.mocked(sidecarGet).mockResolvedValue(SAMPLE_CATALOG);
    const onProviderChange = vi.fn();
    render(
      <MacroSeriesPicker
        provider="fred"
        onProviderChange={onProviderChange}
        onSelect={() => undefined}
      />,
    );
    fireEvent.click(screen.getByTestId("macro-provider-ecb"));
    expect(onProviderChange).toHaveBeenCalledWith("ecb");
  });

  it("fires onSelect when a catalog row is clicked", async () => {
    vi.mocked(sidecarGet).mockResolvedValueOnce(SAMPLE_CATALOG);
    const onSelect = vi.fn();
    render(
      <MacroSeriesPicker provider="fred" onProviderChange={() => undefined} onSelect={onSelect} />,
    );
    await waitFor(() => expect(screen.getByText("10-Year Treasury")).toBeInTheDocument());
    fireEvent.click(screen.getByTestId("macro-result-DGS10"));
    expect(onSelect).toHaveBeenCalledWith("fred", "DGS10");
  });

  it("debounces searches and renders the result rows", async () => {
    // First call resolves the catalog mount load.
    vi.mocked(sidecarGet)
      .mockResolvedValueOnce(SAMPLE_CATALOG)
      .mockResolvedValueOnce(SAMPLE_SEARCH);
    render(
      <MacroSeriesPicker
        provider="fred"
        onProviderChange={() => undefined}
        onSelect={() => undefined}
      />,
    );
    fireEvent.change(screen.getByTestId("macro-search-input"), { target: { value: "treasury" } });
    // After the 200ms debounce + a tick of microtask, the search fires.
    await waitFor(
      () =>
        expect(sidecarGet).toHaveBeenCalledWith("/macro/search", {
          q: "treasury",
          provider: "fred",
          limit: 25,
        }),
      { timeout: 1500 },
    );
    await waitFor(() => expect(screen.getByText("2-Year Treasury")).toBeInTheDocument());
  });
});
