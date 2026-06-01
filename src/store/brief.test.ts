import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// The store self-persists via `autosaveLayout`. Mock it so a setter call in a
// unit test (no dockview) is observable and never touches the network.
vi.mock("@/lib/workspace", () => ({
  autosaveLayout: vi.fn(() => Promise.resolve()),
}));

import { autosaveLayout } from "@/lib/workspace";
import { briefBundle, resetBriefStoreForTests, useBriefStore } from "@/store/brief";
import type { ResearchBriefData } from "../../types/brief";

const autosaveMock = vi.mocked(autosaveLayout);

function sampleBrief(overrides: Partial<ResearchBriefData> = {}): ResearchBriefData {
  return {
    query: "What is Apple's moat?",
    symbol: "AAPL",
    mode: "DEEP",
    markdown: "Apple's moat is its ecosystem [1] and brand [2].",
    sources: [
      { url: "https://sec.gov/aapl", title: "10-K", excerpt: "Risk factors…", domain: "sec.gov" },
      { url: "https://example.com/brand", title: "Brand study", excerpt: "Loyalty…" },
    ],
    sourceCount: 2,
    cost: { tokens: 12400, spendUsd: 0.03 },
    webAvailable: true,
    steps: [{ kind: "plan", detail: "Decompose the query", latencyMs: 120, status: "ok" }],
    createdAt: 1_700_000_000_000,
    ...overrides,
  };
}

describe("brief store", () => {
  beforeEach(() => {
    resetBriefStoreForTests();
    autosaveMock.mockClear();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("starts with no brief", () => {
    expect(useBriefStore.getState().brief).toBeNull();
    expect(briefBundle()).toBeNull();
  });

  it("setBrief stores the brief and triggers persistence", () => {
    const brief = sampleBrief();
    useBriefStore.getState().setBrief(brief);

    expect(useBriefStore.getState().brief).toEqual(brief);
    expect(autosaveMock).toHaveBeenCalledTimes(1);
  });

  it("setBrief replaces a prior brief (latest run wins)", () => {
    useBriefStore.getState().setBrief(sampleBrief({ query: "first" }));
    useBriefStore.getState().setBrief(sampleBrief({ query: "second" }));

    expect(useBriefStore.getState().brief?.query).toBe("second");
    expect(autosaveMock).toHaveBeenCalledTimes(2);
  });

  it("clearBrief resets to empty and triggers persistence", () => {
    useBriefStore.getState().setBrief(sampleBrief());
    autosaveMock.mockClear();

    useBriefStore.getState().clearBrief();

    expect(useBriefStore.getState().brief).toBeNull();
    expect(autosaveMock).toHaveBeenCalledTimes(1);
  });

  it("toBundle / briefBundle snapshot the persistence shape", () => {
    const brief = sampleBrief();
    useBriefStore.getState().setBrief(brief);

    expect(briefBundle()).toEqual(brief);
    expect(useBriefStore.getState().toBundle()).toEqual(brief);
  });

  it("fromBundle round-trips a serialised brief and triggers persistence", () => {
    const brief = sampleBrief();
    const bundle = brief; // what would ride SerializedWorkspace.brief

    useBriefStore.getState().fromBundle(bundle);

    expect(useBriefStore.getState().brief).toEqual(brief);
    expect(briefBundle()).toEqual(bundle);
    expect(autosaveMock).toHaveBeenCalledTimes(1);
  });

  it("fromBundle(null) restores the empty state", () => {
    useBriefStore.getState().setBrief(sampleBrief());

    useBriefStore.getState().fromBundle(null);

    expect(useBriefStore.getState().brief).toBeNull();
  });

  it("fromBundle rejects a garbled/partial bundle by restoring to empty", () => {
    useBriefStore.getState().setBrief(sampleBrief());

    // Missing the load-bearing markdown/sources fields — must not half-populate.
    useBriefStore.getState().fromBundle({ query: "broken" } as unknown as ResearchBriefData);

    expect(useBriefStore.getState().brief).toBeNull();
  });

  it("persists a webAvailable=false brief faithfully (honest no-web state)", () => {
    const brief = sampleBrief({
      webAvailable: false,
      note: "No web-search backend configured.",
      sources: [],
      sourceCount: 0,
      cost: undefined,
    });
    useBriefStore.getState().setBrief(brief);

    const round = briefBundle();
    expect(round?.webAvailable).toBe(false);
    expect(round?.note).toBe("No web-search backend configured.");
    expect(round).toEqual(brief);
  });
});
