import { beforeEach, describe, expect, it, vi } from "vitest";

const getSecretMock = vi.hoisted(() => vi.fn(async () => "sk-or-test"));
const sidecarGetMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/keychain", async () => {
  const actual = await vi.importActual<typeof import("@/lib/keychain")>("@/lib/keychain");
  return { ...actual, getSecret: getSecretMock };
});

vi.mock("@/lib/sidecar-client", async () => {
  const actual =
    await vi.importActual<typeof import("@/lib/sidecar-client")>("@/lib/sidecar-client");
  return { ...actual, sidecarGet: sidecarGetMock };
});

import { useModelCatalogStore, resetModelCatalogStoreForTests } from "@/store/model-catalog";

const ROW = {
  provider: "openrouter",
  source: "live",
  note: "Live · routable on your key · 2 models, 1 tool-capable",
  models: [
    {
      id: "a/tool",
      label: "A Tool",
      context_length: 128000,
      supports_tools: true,
      pricing: "free",
    },
    { id: "b/plain", label: "B Plain", supports_tools: false },
  ],
};

describe("useModelCatalogStore.fetchCatalog", () => {
  beforeEach(() => {
    resetModelCatalogStoreForTests();
    getSecretMock.mockClear();
    getSecretMock.mockResolvedValue("sk-or-test");
    sidecarGetMock.mockReset();
    sidecarGetMock.mockResolvedValue(ROW);
  });

  it("maps the snake_case wire shape to camelCase and stores source/note", async () => {
    await useModelCatalogStore.getState().fetchCatalog("openrouter");
    const entry = useModelCatalogStore.getState().byProvider.openrouter;
    expect(entry?.source).toBe("live");
    expect(entry?.note).toContain("routable on your key");
    expect(entry?.models.map((m) => m.id)).toEqual(["a/tool", "b/plain"]);
    expect(entry?.models[0].supportsTools).toBe(true);
    expect(entry?.models[0].contextLength).toBe(128000);
    expect(entry?.models[1].supportsTools).toBe(false);
    expect(entry?.loading).toBe(false);
  });

  it("sends the keychain key as the X-LLM-Key header and the provider param", async () => {
    await useModelCatalogStore.getState().fetchCatalog("openrouter");
    expect(getSecretMock).toHaveBeenCalledWith("llm-provider:openrouter");
    const [path, params, headers] = sidecarGetMock.mock.calls[0];
    expect(path).toBe("/llm/models");
    expect(params).toMatchObject({ provider: "openrouter" });
    expect(headers).toEqual({ "X-LLM-Key": "sk-or-test" });
  });

  it("omits the header when no key is configured (still fetches the public catalog)", async () => {
    getSecretMock.mockResolvedValue(null as unknown as string);
    await useModelCatalogStore.getState().fetchCatalog("openrouter");
    const headers = sidecarGetMock.mock.calls[0][2];
    expect(headers).toBeUndefined();
    expect(sidecarGetMock).toHaveBeenCalledTimes(1);
  });

  it("caches within the TTL and re-fetches only when forced", async () => {
    await useModelCatalogStore.getState().fetchCatalog("openrouter");
    await useModelCatalogStore.getState().fetchCatalog("openrouter");
    expect(sidecarGetMock).toHaveBeenCalledTimes(1); // second call served from cache
    await useModelCatalogStore.getState().fetchCatalog("openrouter", { force: true });
    expect(sidecarGetMock).toHaveBeenCalledTimes(2);
  });

  it("degrades to an error state but keeps prior models on a failed refresh", async () => {
    await useModelCatalogStore.getState().fetchCatalog("openrouter");
    sidecarGetMock.mockRejectedValueOnce(new Error("sidecar down"));
    await useModelCatalogStore.getState().fetchCatalog("openrouter", { force: true });
    const entry = useModelCatalogStore.getState().byProvider.openrouter;
    expect(entry?.error).toContain("sidecar down");
    expect(entry?.models).toHaveLength(2); // prior catalog retained, no empty flicker
    expect(entry?.loading).toBe(false);
  });
});
