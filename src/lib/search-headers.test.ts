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
  EXA_KEYCHAIN_ACCOUNT,
  getOpenrouterApiKey,
} from "@/lib/search-headers";
import { resetSearchSettingsStoreForTests, useSearchSettingsStore } from "@/store/search-settings";

const getSecretMock = vi.mocked(getSecret);
const OPENROUTER_ACCOUNT = KEYCHAIN_NAMESPACES.llmProvider("openrouter");

/** Stub the keychain with a fixed account → secret map (others resolve null). */
function stubKeychain(secrets: Record<string, string | null>) {
  getSecretMock.mockImplementation((account: string) => Promise.resolve(secrets[account] ?? null));
}

describe("buildSearchHeaders — R8 one-truth emit/omit matrix", () => {
  beforeEach(() => {
    resetSearchSettingsStoreForTests();
    getSecretMock.mockReset();
    getSecretMock.mockResolvedValue(null);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("t1 (default) emits the research tier ONLY — no legacy headers, no keys", async () => {
    const headers = await buildSearchHeaders();
    expect(headers["X-Vysted-Research-Tier"]).toBe("t1_local");
    expect(headers["X-Vysted-Search-Tier"]).toBeUndefined();
    expect(headers["X-Vysted-Exa-Key"]).toBeUndefined();
    expect(headers["X-Vysted-Searxng-Url"]).toBeUndefined();
    expect(headers["X-Vysted-Search-Engine"]).toBeUndefined();
    expect(headers["X-Vysted-Openrouter-Key"]).toBeUndefined();
  });

  it("t1 never reads ANY keychain slot, even when keys are stored", async () => {
    stubKeychain({
      [OPENROUTER_ACCOUNT]: "sk-or-v1-secret",
      [EXA_KEYCHAIN_ACCOUNT]: "exa-key-123",
    });
    const headers = await buildSearchHeaders();
    expect(headers["X-Vysted-Openrouter-Key"]).toBeUndefined();
    expect(headers["X-Vysted-Exa-Key"]).toBeUndefined();
    expect(getSecretMock).not.toHaveBeenCalled();
  });

  it("t2 with no custom URL emits the research tier only (managed/autodetect)", async () => {
    useSearchSettingsStore.getState().setResearchTier("t2_searxng");
    const headers = await buildSearchHeaders();
    expect(headers["X-Vysted-Research-Tier"]).toBe("t2_searxng");
    expect(headers["X-Vysted-Searxng-Url"]).toBeUndefined();
    expect(headers["X-Vysted-Search-Tier"]).toBeUndefined();
  });

  it("t2 with a custom URL emits the trimmed URL alongside the tier", async () => {
    useSearchSettingsStore.getState().setResearchTier("t2_searxng");
    useSearchSettingsStore.getState().setSearxngUrl("  http://127.0.0.1:8080  ");
    const headers = await buildSearchHeaders();
    expect(headers["X-Vysted-Research-Tier"]).toBe("t2_searxng");
    expect(headers["X-Vysted-Searxng-Url"]).toBe("http://127.0.0.1:8080");
  });

  it("a custom SearXNG URL is NOT sent off-t2 (no blank/leftover overrides)", async () => {
    useSearchSettingsStore.getState().setSearxngUrl("http://127.0.0.1:8080");
    // researchTier stays t1_local
    const headers = await buildSearchHeaders();
    expect(headers["X-Vysted-Searxng-Url"]).toBeUndefined();
  });

  it("t3 hosted emits the engine and the OpenRouter key when one is stored", async () => {
    stubKeychain({ [OPENROUTER_ACCOUNT]: "sk-or-v1-secret" });
    useSearchSettingsStore.getState().setResearchTier("t3_hosted");

    const headers = await buildSearchHeaders();
    expect(headers["X-Vysted-Research-Tier"]).toBe("t3_hosted");
    expect(headers["X-Vysted-Search-Engine"]).toBe("firecrawl");
    expect(headers["X-Vysted-Openrouter-Key"]).toBe("sk-or-v1-secret");
    expect(headers["X-Vysted-Search-Tier"]).toBeUndefined();
    expect(headers["X-Vysted-Exa-Key"]).toBeUndefined();

    useSearchSettingsStore.getState().setHostedEngine("exa");
    expect((await buildSearchHeaders())["X-Vysted-Search-Engine"]).toBe("exa");
  });

  it("t3 hosted without a stored key emits the engine but OMITS the key (never empty)", async () => {
    useSearchSettingsStore.getState().setResearchTier("t3_hosted");
    const headers = await buildSearchHeaders();
    expect(headers["X-Vysted-Search-Engine"]).toBe("firecrawl");
    expect(headers["X-Vysted-Openrouter-Key"]).toBeUndefined();
    expect(Object.values(headers)).not.toContain("");
  });

  it("t3 hosted with an empty-string keychain value omits the key", async () => {
    stubKeychain({ [OPENROUTER_ACCOUNT]: "" });
    useSearchSettingsStore.getState().setResearchTier("t3_hosted");
    expect((await buildSearchHeaders())["X-Vysted-Openrouter-Key"]).toBeUndefined();
  });

  it("a keychain failure on t3 hosted degrades to key-omitted, never a throw", async () => {
    getSecretMock.mockRejectedValue(new Error("keychain locked"));
    useSearchSettingsStore.getState().setResearchTier("t3_hosted");
    const headers = await buildSearchHeaders();
    expect(headers["X-Vysted-Research-Tier"]).toBe("t3_hosted");
    expect(headers["X-Vysted-Openrouter-Key"]).toBeUndefined();
  });

  // --- t3 "Exa direct" — the legacy byok-exa wire lane -----------------------

  it("Exa direct rides the legacy lane: byok-exa tier + Exa key, NO R7 header", async () => {
    stubKeychain({ [EXA_KEYCHAIN_ACCOUNT]: "exa-key-123" });
    useSearchSettingsStore.getState().setResearchTier("t3_hosted");
    useSearchSettingsStore.getState().setExaDirect(true);

    const headers = await buildSearchHeaders();
    expect(headers["X-Vysted-Search-Tier"]).toBe("byok-exa");
    expect(headers["X-Vysted-Exa-Key"]).toBe("exa-key-123");
    // The R7 header is OMITTED — an explicit R7 tier always wins on the
    // sidecar, so sending it would shadow the Exa-direct lane.
    expect(headers["X-Vysted-Research-Tier"]).toBeUndefined();
    expect(headers["X-Vysted-Search-Engine"]).toBeUndefined();
    expect(headers["X-Vysted-Openrouter-Key"]).toBeUndefined();
  });

  it("Exa direct never reads the OpenRouter keychain slot", async () => {
    stubKeychain({
      [EXA_KEYCHAIN_ACCOUNT]: "exa-key-123",
      [OPENROUTER_ACCOUNT]: "sk-or-v1-secret",
    });
    useSearchSettingsStore.getState().setResearchTier("t3_hosted");
    useSearchSettingsStore.getState().setExaDirect(true);
    await buildSearchHeaders();
    expect(getSecretMock).not.toHaveBeenCalledWith(OPENROUTER_ACCOUNT);
  });

  it("Exa direct without a stored key omits the key (sidecar floors honestly)", async () => {
    useSearchSettingsStore.getState().setResearchTier("t3_hosted");
    useSearchSettingsStore.getState().setExaDirect(true);
    const headers = await buildSearchHeaders();
    expect(headers["X-Vysted-Search-Tier"]).toBe("byok-exa");
    expect(headers["X-Vysted-Exa-Key"]).toBeUndefined();
    expect(Object.values(headers)).not.toContain("");
  });

  it("exaDirect off t3 is inert — t1/t2 ignore the flag entirely", async () => {
    stubKeychain({ [EXA_KEYCHAIN_ACCOUNT]: "exa-key-123" });
    useSearchSettingsStore.getState().setExaDirect(true);
    useSearchSettingsStore.getState().setResearchTier("t2_searxng");
    const headers = await buildSearchHeaders();
    expect(headers["X-Vysted-Research-Tier"]).toBe("t2_searxng");
    expect(headers["X-Vysted-Search-Tier"]).toBeUndefined();
    expect(headers["X-Vysted-Exa-Key"]).toBeUndefined();
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
