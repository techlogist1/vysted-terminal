import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// The store self-persists via `autosaveLayout`; mock it so setters under test
// never touch the network/dockview.
vi.mock("@/lib/workspace", () => ({
  autosaveLayout: vi.fn(() => Promise.resolve()),
}));

// Keychain: keep the real KEYCHAIN_NAMESPACES (the account strings under test
// ARE the contract) but stub the Tauri-backed reads.
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
import {
  buildSearchHeaders,
  encodeResearchModels,
  getOpenrouterApiKey,
} from "@/lib/search-headers";
import { resetSearchSettingsStoreForTests, useSearchSettingsStore } from "@/store/search-settings";

const getSecretMock = vi.mocked(getSecret);
const OPENROUTER_ACCOUNT = KEYCHAIN_NAMESPACES.llmProvider("openrouter");

/** Stub the keychain with a fixed account → secret map (others resolve null). */
function stubKeychain(secrets: Record<string, string | null>) {
  getSecretMock.mockImplementation((account: string) => Promise.resolve(secrets[account] ?? null));
}

describe("buildSearchHeaders — R9 two-tier emit/omit matrix", () => {
  beforeEach(() => {
    resetSearchSettingsStoreForTests();
    getSecretMock.mockReset();
    getSecretMock.mockResolvedValue(null);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("tier_a (default) emits the tier ONLY — no key, no models, no legacy headers", async () => {
    const headers = await buildSearchHeaders();
    expect(headers["X-Vysted-Research-Tier"]).toBe("tier_a");
    expect(headers["X-Vysted-Searxng-Url"]).toBeUndefined();
    expect(headers["X-Vysted-Openrouter-Key"]).toBeUndefined();
    expect(headers["X-Vysted-Research-Models"]).toBeUndefined();
    // The dead R7/R8 wire lanes never ride again.
    expect(headers["X-Vysted-Search-Tier"]).toBeUndefined();
    expect(headers["X-Vysted-Exa-Key"]).toBeUndefined();
    expect(headers["X-Vysted-Search-Engine"]).toBeUndefined();
  });

  it("tier_a never reads ANY keychain slot, even when a key is stored", async () => {
    stubKeychain({ [OPENROUTER_ACCOUNT]: "sk-or-v1-secret" });
    const headers = await buildSearchHeaders();
    expect(headers["X-Vysted-Openrouter-Key"]).toBeUndefined();
    expect(getSecretMock).not.toHaveBeenCalled();
  });

  it("a custom SearXNG URL rides trimmed under EITHER tier (retrieval is one lane)", async () => {
    useSearchSettingsStore.getState().setSearxngUrl("  http://127.0.0.1:8080  ");
    expect((await buildSearchHeaders())["X-Vysted-Searxng-Url"]).toBe("http://127.0.0.1:8080");

    useSearchSettingsStore.getState().setResearchTier("tier_b");
    expect((await buildSearchHeaders())["X-Vysted-Searxng-Url"]).toBe("http://127.0.0.1:8080");
  });

  it("a blank/whitespace SearXNG URL is omitted, never an empty override", async () => {
    useSearchSettingsStore.getState().setSearxngUrl("   ");
    const headers = await buildSearchHeaders();
    expect(headers["X-Vysted-Searxng-Url"]).toBeUndefined();
    expect(Object.values(headers)).not.toContain("");
  });

  it("tier_b emits the key + the per-stop model map", async () => {
    stubKeychain({ [OPENROUTER_ACCOUNT]: "sk-or-v1-secret" });
    useSearchSettingsStore.getState().setResearchTier("tier_b");

    const headers = await buildSearchHeaders();
    expect(headers["X-Vysted-Research-Tier"]).toBe("tier_b");
    expect(headers["X-Vysted-Openrouter-Key"]).toBe("sk-or-v1-secret");
    expect(headers["X-Vysted-Research-Models"]).toBe(
      "normal=perplexity/sonar,deep=perplexity/sonar-reasoning-pro,ultra=perplexity/sonar-deep-research",
    );
  });

  it("tier_b reflects a swapped per-stop model immediately", async () => {
    stubKeychain({ [OPENROUTER_ACCOUNT]: "sk-or-v1-secret" });
    useSearchSettingsStore.getState().setResearchTier("tier_b");
    useSearchSettingsStore.getState().setResearchModel("ultra", "openai/o3-deep-research");

    const headers = await buildSearchHeaders();
    expect(headers["X-Vysted-Research-Models"]).toContain("ultra=openai/o3-deep-research");
  });

  it("tier_b without a stored key emits the tier + models but OMITS the key (never empty)", async () => {
    useSearchSettingsStore.getState().setResearchTier("tier_b");
    const headers = await buildSearchHeaders();
    expect(headers["X-Vysted-Research-Tier"]).toBe("tier_b");
    expect(headers["X-Vysted-Openrouter-Key"]).toBeUndefined();
    expect(headers["X-Vysted-Research-Models"]).toBeTruthy();
    expect(Object.values(headers)).not.toContain("");
  });

  it("tier_b with an empty-string keychain value omits the key", async () => {
    stubKeychain({ [OPENROUTER_ACCOUNT]: "" });
    useSearchSettingsStore.getState().setResearchTier("tier_b");
    expect((await buildSearchHeaders())["X-Vysted-Openrouter-Key"]).toBeUndefined();
  });

  it("a keychain failure on tier_b degrades to key-omitted, never a throw", async () => {
    getSecretMock.mockRejectedValue(new Error("keychain locked"));
    useSearchSettingsStore.getState().setResearchTier("tier_b");
    const headers = await buildSearchHeaders();
    expect(headers["X-Vysted-Research-Tier"]).toBe("tier_b");
    expect(headers["X-Vysted-Openrouter-Key"]).toBeUndefined();
  });

  it("encodeResearchModels emits ordered stop=slug pairs", () => {
    expect(
      encodeResearchModels({
        normal: "perplexity/sonar",
        deep: "openai/o4-mini-deep-research",
        ultra: "x-ai/grok-4.3",
      }),
    ).toBe("normal=perplexity/sonar,deep=openai/o4-mini-deep-research,ultra=x-ai/grok-4.3");
  });

  it("getOpenrouterApiKey reads the AI-Providers slot and maps empty/miss to null", async () => {
    stubKeychain({ [OPENROUTER_ACCOUNT]: "sk-or-v1-secret" });
    expect(await getOpenrouterApiKey()).toBe("sk-or-v1-secret");
    expect(getSecretMock).toHaveBeenCalledWith("llm-provider:openrouter");

    stubKeychain({});
    expect(await getOpenrouterApiKey()).toBeNull();

    stubKeychain({ [OPENROUTER_ACCOUNT]: "" });
    expect(await getOpenrouterApiKey()).toBeNull();
  });
});
