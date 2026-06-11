import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// The store self-persists via `autosaveLayout`. Mock it so a setter call in a
// unit test (no dockview) is observable and never touches the network.
vi.mock("@/lib/workspace", () => ({
  autosaveLayout: vi.fn(() => Promise.resolve()),
}));

// Keychain: the tier_b migration confirmation reads the OpenRouter slot; stub
// the Tauri-backed reads (default: no key stored).
vi.mock("@/lib/keychain", async (importActual) => {
  const actual = await importActual<typeof import("@/lib/keychain")>();
  return {
    ...actual,
    getSecret: vi.fn(() => Promise.resolve(null)),
    setSecret: vi.fn(() => Promise.resolve()),
    deleteSecret: vi.fn(() => Promise.resolve()),
  };
});

import { getSecret, KEYCHAIN_NAMESPACES } from "@/lib/keychain";
import { autosaveLayout } from "@/lib/workspace";
import {
  DEFAULT_RESEARCH_MODELS,
  DEFAULT_SEARCH_SETTINGS,
  migrateSearchSettings,
  reconcileMigratedTierB,
  RESEARCH_MODEL_OPTIONS,
  RESEARCH_STOPS,
  resetSearchSettingsStoreForTests,
  searchSettingsBundle,
  useSearchSettingsStore,
} from "@/store/search-settings";

const autosaveMock = vi.mocked(autosaveLayout);
const getSecretMock = vi.mocked(getSecret);
const OPENROUTER_ACCOUNT = KEYCHAIN_NAMESPACES.llmProvider("openrouter");

/** Flush pending microtasks (the fire-and-forget key confirmation). */
async function flush(): Promise<void> {
  await Promise.resolve();
  await Promise.resolve();
  await Promise.resolve();
}

describe("search-settings store (R9 two-tier)", () => {
  beforeEach(() => {
    resetSearchSettingsStoreForTests();
    autosaveMock.mockClear();
    getSecretMock.mockReset();
    getSecretMock.mockResolvedValue(null);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("defaults to tier_a with the verified per-stop research models", () => {
    const s = useSearchSettingsStore.getState();
    expect(s.researchTier).toBe("tier_a");
    expect(s.searxngUrl).toBe("");
    expect(s.researchModels).toEqual({
      normal: "perplexity/sonar",
      deep: "perplexity/sonar-reasoning-pro",
      ultra: "perplexity/sonar-deep-research",
    });
    expect(DEFAULT_SEARCH_SETTINGS.researchTier).toBe("tier_a");
  });

  it("exposes NO legacy tier vocabulary — the keyless/Exa era is dead", () => {
    const s = useSearchSettingsStore.getState() as unknown as Record<string, unknown>;
    expect(s.tier).toBeUndefined();
    expect(s.hostedEngine).toBeUndefined();
    expect(s.exaDirect).toBeUndefined();
    expect(s.setHostedEngine).toBeUndefined();
    expect(s.setExaDirect).toBeUndefined();
  });

  it("the picker constant carries a pricing hint for every model (Team D renders it)", () => {
    expect(RESEARCH_MODEL_OPTIONS.length).toBeGreaterThanOrEqual(8);
    for (const option of RESEARCH_MODEL_OPTIONS) {
      expect(option.id).toBeTruthy();
      expect(option.label).toBeTruthy();
      expect(option.priceHint).toBeTruthy();
    }
    // The three per-stop defaults are pickable and price-verified.
    for (const stop of RESEARCH_STOPS) {
      const slug = DEFAULT_RESEARCH_MODELS[stop];
      const option = RESEARCH_MODEL_OPTIONS.find((o) => o.id === slug);
      expect(option, slug).toBeTruthy();
      expect(option?.priceVerified).toBe(true);
    }
  });

  it("setResearchTier updates state and triggers persistence", () => {
    useSearchSettingsStore.getState().setResearchTier("tier_b");
    expect(useSearchSettingsStore.getState().researchTier).toBe("tier_b");
    expect(autosaveMock).toHaveBeenCalledTimes(1);
  });

  it("setSearxngUrl updates state and triggers persistence", () => {
    useSearchSettingsStore.getState().setSearxngUrl("http://127.0.0.1:8080");
    expect(useSearchSettingsStore.getState().searxngUrl).toBe("http://127.0.0.1:8080");
    expect(autosaveMock).toHaveBeenCalledTimes(1);
  });

  it("setResearchModel swaps one stop and ignores garbage", () => {
    useSearchSettingsStore.getState().setResearchModel("deep", "openai/o4-mini-deep-research");
    expect(useSearchSettingsStore.getState().researchModels.deep).toBe(
      "openai/o4-mini-deep-research",
    );
    expect(useSearchSettingsStore.getState().researchModels.normal).toBe("perplexity/sonar");
    expect(autosaveMock).toHaveBeenCalledTimes(1);

    useSearchSettingsStore.getState().setResearchModel("deep", "has spaces!!");
    expect(useSearchSettingsStore.getState().researchModels.deep).toBe(
      "openai/o4-mini-deep-research",
    );
    expect(autosaveMock).toHaveBeenCalledTimes(1); // garbage never persists
  });

  it("does not mutate the frozen defaults when a setter runs", () => {
    useSearchSettingsStore.getState().setResearchTier("tier_b");
    useSearchSettingsStore.getState().setResearchModel("ultra", "x-ai/grok-4.3");
    expect(DEFAULT_SEARCH_SETTINGS.researchTier).toBe("tier_a");
    expect(DEFAULT_RESEARCH_MODELS.ultra).toBe("perplexity/sonar-deep-research");
  });

  // --- Migration (pre-R9 blobs → the two-tier vocabulary) ---------------------

  it("migrateSearchSettings folds every legacy local-class id into tier_a", () => {
    for (const legacy of ["native", "local-searxng"]) {
      const { bundle, tierBNeedsKeyConfirmation } = migrateSearchSettings({ tier: legacy });
      expect(bundle.researchTier, legacy).toBe("tier_a");
      expect(tierBNeedsKeyConfirmation).toBe(false);
    }
    for (const legacy of ["t1_local", "t2_searxng"]) {
      const { bundle } = migrateSearchSettings({ researchTier: legacy });
      expect(bundle.researchTier, legacy).toBe("tier_a");
    }
  });

  it("migrateSearchSettings lands hosted/Exa selections on provisional tier_b", () => {
    const hosted = migrateSearchSettings({ researchTier: "t3_hosted" });
    expect(hosted.bundle.researchTier).toBe("tier_b");
    expect(hosted.tierBNeedsKeyConfirmation).toBe(true);

    const exa = migrateSearchSettings({ tier: "byok-exa", exaDirect: true });
    expect(exa.bundle.researchTier).toBe("tier_b");
    expect(exa.tierBNeedsKeyConfirmation).toBe(true);
  });

  it("migrateSearchSettings treats an R9 tier as authoritative (no key check)", () => {
    const out = migrateSearchSettings({ researchTier: "tier_b", tier: "native" });
    expect(out.bundle.researchTier).toBe("tier_b");
    expect(out.tierBNeedsKeyConfirmation).toBe(false);
  });

  it("migrateSearchSettings drops legacy fields and floors garbage to defaults", () => {
    const { bundle } = migrateSearchSettings({
      tier: "warpdrive",
      hostedEngine: "exa",
      exaDirect: true,
      researchModels: { deep: 42, ultra: "openai/o3-deep-research", bogus: "x" },
      searxngUrl: 9,
    } as never);
    expect(bundle).toEqual({
      researchTier: "tier_a",
      searxngUrl: "",
      researchModels: {
        normal: "perplexity/sonar",
        deep: "perplexity/sonar-reasoning-pro",
        ultra: "openai/o3-deep-research",
      },
    });
    expect("tier" in bundle).toBe(false);
    expect("exaDirect" in bundle).toBe(false);
  });

  it("setAll migrates a pre-R8 native blob onto tier_a", () => {
    useSearchSettingsStore.getState().setAll({ tier: "native", searxngUrl: "" });
    expect(useSearchSettingsStore.getState().researchTier).toBe("tier_a");
  });

  it("setAll migrates a local-searxng blob onto tier_a and keeps the URL", () => {
    useSearchSettingsStore.getState().setAll({
      tier: "local-searxng",
      searxngUrl: "http://localhost:8080",
    });
    const s = useSearchSettingsStore.getState();
    expect(s.researchTier).toBe("tier_a");
    expect(s.searxngUrl).toBe("http://localhost:8080");
  });

  it("setAll keeps a migrated t3_hosted blob on tier_b WHEN the key is configured", async () => {
    getSecretMock.mockImplementation((account: string) =>
      Promise.resolve(account === OPENROUTER_ACCOUNT ? "sk-or-v1-secret" : null),
    );
    useSearchSettingsStore.getState().setAll({ researchTier: "t3_hosted" });
    expect(useSearchSettingsStore.getState().researchTier).toBe("tier_b");
    await flush();
    expect(useSearchSettingsStore.getState().researchTier).toBe("tier_b");
  });

  it("setAll demotes a migrated t3_hosted blob to tier_a when NO key is configured", async () => {
    useSearchSettingsStore.getState().setAll({ researchTier: "t3_hosted" });
    await flush();
    expect(useSearchSettingsStore.getState().researchTier).toBe("tier_a");
  });

  it("setAll demotes a migrated byok-exa blob to tier_a when NO key is configured", async () => {
    useSearchSettingsStore.getState().setAll({ tier: "byok-exa", exaDirect: true });
    await flush();
    expect(useSearchSettingsStore.getState().researchTier).toBe("tier_a");
  });

  it("a keychain failure during migration demotes (it could not serve requests either)", async () => {
    getSecretMock.mockRejectedValue(new Error("keychain locked"));
    useSearchSettingsStore.getState().setAll({ researchTier: "t3_hosted" });
    await flush();
    expect(useSearchSettingsStore.getState().researchTier).toBe("tier_a");
  });

  it("an authoritative R9 tier_b blob is NEVER key-demoted on restore", async () => {
    useSearchSettingsStore.getState().setAll({ researchTier: "tier_b" });
    await flush();
    expect(useSearchSettingsStore.getState().researchTier).toBe("tier_b");
    expect(getSecretMock).not.toHaveBeenCalled();
  });

  it("reconcileMigratedTierB no-ops when the user already switched away", async () => {
    useSearchSettingsStore.getState().setResearchTier("tier_a");
    await reconcileMigratedTierB();
    expect(useSearchSettingsStore.getState().researchTier).toBe("tier_a");
  });

  it("setAll merges over the seed and drops garbled values", () => {
    useSearchSettingsStore.getState().setAll({
      researchTier: "t9_quantum" as never,
      researchModels: "nope" as never,
      searxngUrl: 42 as never,
    });
    const s = useSearchSettingsStore.getState();
    expect(s.researchTier).toBe("tier_a");
    expect(s.researchModels).toEqual(DEFAULT_RESEARCH_MODELS);
    expect(s.searxngUrl).toBe("");
  });

  it("setAll with fields absent entirely keeps the seed values", () => {
    useSearchSettingsStore.getState().setResearchTier("tier_b");
    useSearchSettingsStore.getState().setAll({});
    expect(useSearchSettingsStore.getState().researchTier).toBe("tier_a");
  });

  it("toBundle / searchSettingsBundle snapshot the persistence shape", () => {
    useSearchSettingsStore.getState().setSearxngUrl("http://127.0.0.1:8080");
    useSearchSettingsStore.getState().setResearchTier("tier_b");
    useSearchSettingsStore.getState().setResearchModel("ultra", "openai/o3-deep-research");

    const bundle = searchSettingsBundle();
    expect(bundle).toEqual({
      researchTier: "tier_b",
      searxngUrl: "http://127.0.0.1:8080",
      researchModels: {
        normal: "perplexity/sonar",
        deep: "perplexity/sonar-reasoning-pro",
        ultra: "openai/o3-deep-research",
      },
    });
    // The snapshot is a fresh object, not a live reference into the store.
    expect(bundle).not.toBe(useSearchSettingsStore.getState());
    expect(bundle.researchModels).not.toBe(useSearchSettingsStore.getState().researchModels);
    expect(useSearchSettingsStore.getState().toBundle()).toEqual(bundle);
  });

  it("a bundle round-trips through setAll unchanged (new-blob restore)", () => {
    useSearchSettingsStore.getState().setResearchTier("tier_b");
    useSearchSettingsStore.getState().setResearchModel("deep", "perplexity/sonar-pro");
    const bundle = searchSettingsBundle();
    resetSearchSettingsStoreForTests();
    useSearchSettingsStore.getState().setAll(bundle);
    expect(searchSettingsBundle()).toEqual(bundle);
  });
});
