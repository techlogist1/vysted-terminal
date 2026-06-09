import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// The store self-persists via `autosaveLayout`. Mock it so a setter call in a
// unit test (no dockview) is observable and never touches the network.
vi.mock("@/lib/workspace", () => ({
  autosaveLayout: vi.fn(() => Promise.resolve()),
}));

import { autosaveLayout } from "@/lib/workspace";
import {
  DEFAULT_SEARCH_SETTINGS,
  resetSearchSettingsStoreForTests,
  searchSettingsBundle,
  useSearchSettingsStore,
} from "@/store/search-settings";

const autosaveMock = vi.mocked(autosaveLayout);

describe("search-settings store", () => {
  beforeEach(() => {
    resetSearchSettingsStoreForTests();
    autosaveMock.mockClear();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("defaults to the native tier with an empty SearXNG URL", () => {
    const s = useSearchSettingsStore.getState();
    expect(s.tier).toBe("native");
    expect(s.searxngUrl).toBe("");
    expect(s.tier).toBe(DEFAULT_SEARCH_SETTINGS.tier);
  });

  it("defaults the research tier to the keyless t1 floor and the hosted engine to Firecrawl", () => {
    const s = useSearchSettingsStore.getState();
    expect(s.researchTier).toBe("t1_local");
    expect(s.hostedEngine).toBe("firecrawl");
    expect(DEFAULT_SEARCH_SETTINGS.researchTier).toBe("t1_local");
    expect(DEFAULT_SEARCH_SETTINGS.hostedEngine).toBe("firecrawl");
  });

  it("setResearchTier updates state and triggers persistence", () => {
    useSearchSettingsStore.getState().setResearchTier("t2_searxng");
    expect(useSearchSettingsStore.getState().researchTier).toBe("t2_searxng");
    expect(autosaveMock).toHaveBeenCalledTimes(1);

    useSearchSettingsStore.getState().setResearchTier("t3_hosted");
    expect(useSearchSettingsStore.getState().researchTier).toBe("t3_hosted");
    expect(autosaveMock).toHaveBeenCalledTimes(2);
  });

  it("setHostedEngine updates state and triggers persistence", () => {
    useSearchSettingsStore.getState().setHostedEngine("exa");
    expect(useSearchSettingsStore.getState().hostedEngine).toBe("exa");
    expect(autosaveMock).toHaveBeenCalledTimes(1);
  });

  it("setTier updates state and triggers persistence", () => {
    useSearchSettingsStore.getState().setTier("byok-exa");
    expect(useSearchSettingsStore.getState().tier).toBe("byok-exa");
    expect(autosaveMock).toHaveBeenCalledTimes(1);

    useSearchSettingsStore.getState().setTier("local-searxng");
    expect(useSearchSettingsStore.getState().tier).toBe("local-searxng");
    expect(autosaveMock).toHaveBeenCalledTimes(2);
  });

  it("setSearxngUrl updates state and triggers persistence", () => {
    useSearchSettingsStore.getState().setSearxngUrl("http://127.0.0.1:8080");
    expect(useSearchSettingsStore.getState().searxngUrl).toBe("http://127.0.0.1:8080");
    expect(autosaveMock).toHaveBeenCalledTimes(1);
  });

  it("does not mutate the frozen default when a setter runs", () => {
    useSearchSettingsStore.getState().setTier("local-searxng");
    expect(DEFAULT_SEARCH_SETTINGS.tier).toBe("native");
    expect(DEFAULT_SEARCH_SETTINGS.searxngUrl).toBe("");
  });

  it("setAll merges over the seed and drops a garbled tier", () => {
    useSearchSettingsStore.getState().setAll({ tier: "byok-exa", searxngUrl: "http://local:8888" });
    expect(useSearchSettingsStore.getState().tier).toBe("byok-exa");
    expect(useSearchSettingsStore.getState().searxngUrl).toBe("http://local:8888");

    // A garbled tier falls back to the default; a missing field keeps the seed.
    useSearchSettingsStore.getState().setAll({ tier: "nonsense" as never });
    expect(useSearchSettingsStore.getState().tier).toBe("native");
    expect(useSearchSettingsStore.getState().searxngUrl).toBe("");
  });

  it("setAll round-trips the research tier + hosted engine and drops garbage", () => {
    useSearchSettingsStore.getState().setAll({ researchTier: "t3_hosted", hostedEngine: "exa" });
    expect(useSearchSettingsStore.getState().researchTier).toBe("t3_hosted");
    expect(useSearchSettingsStore.getState().hostedEngine).toBe("exa");

    // Garbled values (hand-edited import, future-version blob) fall back to the
    // defaults — never an unknown id leaking into a request header.
    useSearchSettingsStore.getState().setAll({
      researchTier: "t9_quantum" as never,
      hostedEngine: 42 as never,
    });
    expect(useSearchSettingsStore.getState().researchTier).toBe("t1_local");
    expect(useSearchSettingsStore.getState().hostedEngine).toBe("firecrawl");

    // An older blob (fields absent entirely) keeps the seed values.
    useSearchSettingsStore.getState().setResearchTier("t2_searxng");
    useSearchSettingsStore.getState().setAll({ tier: "byok-exa" });
    expect(useSearchSettingsStore.getState().researchTier).toBe("t1_local");
    expect(useSearchSettingsStore.getState().hostedEngine).toBe("firecrawl");
  });

  it("toBundle / searchSettingsBundle snapshot the persistence shape", () => {
    useSearchSettingsStore.getState().setTier("byok-exa");
    useSearchSettingsStore.getState().setSearxngUrl("http://127.0.0.1:8080");
    useSearchSettingsStore.getState().setResearchTier("t2_searxng");
    useSearchSettingsStore.getState().setHostedEngine("exa");

    const bundle = searchSettingsBundle();
    expect(bundle).toEqual({
      tier: "byok-exa",
      searxngUrl: "http://127.0.0.1:8080",
      researchTier: "t2_searxng",
      hostedEngine: "exa",
    });
    // The snapshot is a fresh object, not a live reference into the store.
    expect(bundle).not.toBe(useSearchSettingsStore.getState());
    expect(useSearchSettingsStore.getState().toBundle()).toEqual(bundle);
  });
});
