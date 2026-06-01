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

  it("toBundle / searchSettingsBundle snapshot the persistence shape", () => {
    useSearchSettingsStore.getState().setTier("byok-exa");
    useSearchSettingsStore.getState().setSearxngUrl("http://127.0.0.1:8080");

    const bundle = searchSettingsBundle();
    expect(bundle).toEqual({ tier: "byok-exa", searxngUrl: "http://127.0.0.1:8080" });
    // The snapshot is a fresh object, not a live reference into the store.
    expect(bundle).not.toBe(useSearchSettingsStore.getState());
    expect(useSearchSettingsStore.getState().toBundle()).toEqual(bundle);
  });
});
