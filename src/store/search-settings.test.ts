import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// The store self-persists via `autosaveLayout`. Mock it so a setter call in a
// unit test (no dockview) is observable and never touches the network.
vi.mock("@/lib/workspace", () => ({
  autosaveLayout: vi.fn(() => Promise.resolve()),
}));

import { autosaveLayout } from "@/lib/workspace";
import {
  DEFAULT_SEARCH_SETTINGS,
  migrateSearchSettings,
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

  it("defaults to the keyless t1 floor, Firecrawl hosted engine, no Exa direct", () => {
    const s = useSearchSettingsStore.getState();
    expect(s.researchTier).toBe("t1_local");
    expect(s.hostedEngine).toBe("firecrawl");
    expect(s.exaDirect).toBe(false);
    expect(s.searxngUrl).toBe("");
    // The legacy passthrough field keeps its pre-R8 default for blob parity.
    expect(s.tier).toBe("native");
    expect(DEFAULT_SEARCH_SETTINGS.researchTier).toBe("t1_local");
    expect(DEFAULT_SEARCH_SETTINGS.exaDirect).toBe(false);
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

  it("setExaDirect updates state and triggers persistence", () => {
    useSearchSettingsStore.getState().setExaDirect(true);
    expect(useSearchSettingsStore.getState().exaDirect).toBe(true);
    expect(autosaveMock).toHaveBeenCalledTimes(1);
  });

  it("setSearxngUrl updates state and triggers persistence", () => {
    useSearchSettingsStore.getState().setSearxngUrl("http://127.0.0.1:8080");
    expect(useSearchSettingsStore.getState().searxngUrl).toBe("http://127.0.0.1:8080");
    expect(autosaveMock).toHaveBeenCalledTimes(1);
  });

  it("does not mutate the frozen default when a setter runs", () => {
    useSearchSettingsStore.getState().setResearchTier("t3_hosted");
    useSearchSettingsStore.getState().setExaDirect(true);
    expect(DEFAULT_SEARCH_SETTINGS.researchTier).toBe("t1_local");
    expect(DEFAULT_SEARCH_SETTINGS.exaDirect).toBe(false);
  });

  // --- Pre-R8 blob migration (legacy tier → R7 vocabulary) -------------------

  it("migrateSearchSettings maps each legacy tier onto its R7 lane", () => {
    expect(migrateSearchSettings({ tier: "native" })).toMatchObject({
      researchTier: "t1_local",
      exaDirect: false,
    });
    expect(migrateSearchSettings({ tier: "local-searxng" })).toMatchObject({
      researchTier: "t2_searxng",
      exaDirect: false,
    });
    expect(migrateSearchSettings({ tier: "byok-exa" })).toMatchObject({
      researchTier: "t3_hosted",
      exaDirect: true,
    });
  });

  it("migrateSearchSettings never overwrites an existing researchTier", () => {
    const bundle = { tier: "byok-exa", researchTier: "t2_searxng" } as const;
    expect(migrateSearchSettings(bundle)).toBe(bundle);
  });

  it("migrateSearchSettings leaves a garbled legacy tier alone (seed applies)", () => {
    const bundle = { tier: "warpdrive" as never };
    expect(migrateSearchSettings(bundle)).toBe(bundle);
  });

  it("setAll migrates a pre-R8 native blob to the t1 floor", () => {
    useSearchSettingsStore.getState().setAll({ tier: "native", searxngUrl: "" });
    const s = useSearchSettingsStore.getState();
    expect(s.researchTier).toBe("t1_local");
    expect(s.exaDirect).toBe(false);
    expect(s.tier).toBe("native");
  });

  it("setAll migrates a pre-R8 local-searxng blob to t2 and keeps the URL", () => {
    useSearchSettingsStore.getState().setAll({
      tier: "local-searxng",
      searxngUrl: "http://localhost:8080",
    });
    const s = useSearchSettingsStore.getState();
    expect(s.researchTier).toBe("t2_searxng");
    expect(s.searxngUrl).toBe("http://localhost:8080");
    expect(s.exaDirect).toBe(false);
  });

  it("setAll migrates a pre-R8 byok-exa blob to t3 + Exa direct", () => {
    useSearchSettingsStore.getState().setAll({ tier: "byok-exa", searxngUrl: "" });
    const s = useSearchSettingsStore.getState();
    expect(s.researchTier).toBe("t3_hosted");
    expect(s.exaDirect).toBe(true);
  });

  it("setAll keeps an R7-era blob verbatim — migration never reroutes it", () => {
    useSearchSettingsStore.getState().setAll({
      tier: "byok-exa", // stale legacy leftover in a current blob
      researchTier: "t1_local",
      hostedEngine: "exa",
      exaDirect: false,
    });
    const s = useSearchSettingsStore.getState();
    expect(s.researchTier).toBe("t1_local");
    expect(s.exaDirect).toBe(false);
    expect(s.hostedEngine).toBe("exa");
  });

  it("setAll merges over the seed and drops garbled values", () => {
    useSearchSettingsStore.getState().setAll({
      researchTier: "t9_quantum" as never,
      hostedEngine: 42 as never,
      exaDirect: "yes" as never,
      tier: "nonsense" as never,
    });
    const s = useSearchSettingsStore.getState();
    expect(s.researchTier).toBe("t1_local");
    expect(s.hostedEngine).toBe("firecrawl");
    expect(s.exaDirect).toBe(false);
    expect(s.tier).toBe("native");
  });

  it("setAll with fields absent entirely keeps the seed values", () => {
    useSearchSettingsStore.getState().setResearchTier("t2_searxng");
    useSearchSettingsStore.getState().setAll({});
    const s = useSearchSettingsStore.getState();
    expect(s.researchTier).toBe("t1_local");
    expect(s.hostedEngine).toBe("firecrawl");
    expect(s.exaDirect).toBe(false);
  });

  it("toBundle / searchSettingsBundle snapshot the persistence shape", () => {
    useSearchSettingsStore.getState().setSearxngUrl("http://127.0.0.1:8080");
    useSearchSettingsStore.getState().setResearchTier("t2_searxng");
    useSearchSettingsStore.getState().setHostedEngine("exa");

    const bundle = searchSettingsBundle();
    expect(bundle).toEqual({
      tier: "native",
      searxngUrl: "http://127.0.0.1:8080",
      researchTier: "t2_searxng",
      hostedEngine: "exa",
      exaDirect: false,
    });
    // The snapshot is a fresh object, not a live reference into the store.
    expect(bundle).not.toBe(useSearchSettingsStore.getState());
    expect(useSearchSettingsStore.getState().toBundle()).toEqual(bundle);
  });
});
