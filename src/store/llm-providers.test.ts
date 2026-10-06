import { beforeEach, describe, expect, it, vi } from "vitest";

import { DEFAULT_PROVIDERS, orderedProviders, useLLMProvidersStore } from "@/store/llm-providers";

const probeMock = vi.hoisted(() => vi.fn());
vi.mock("@/lib/provider-validation", () => ({ probeReadiness: probeMock }));

const NOT_RUNNING = { ok: false, reason: "unreachable", detail: "Ollama is not running." };

describe("promoteKeyedProvider (R15-UI-049)", () => {
  beforeEach(() => {
    probeMock.mockReset();
    useLLMProvidersStore.setState({ providers: DEFAULT_PROVIDERS, defaultProviderId: "ollama" });
  });

  it("a key saved while the keyless default is not ready becomes the default", async () => {
    probeMock.mockResolvedValue(NOT_RUNNING);
    await expect(useLLMProvidersStore.getState().promoteKeyedProvider("openrouter")).resolves.toBe(
      true,
    );
    expect(useLLMProvidersStore.getState().defaultProviderId).toBe("openrouter");
    expect(probeMock).toHaveBeenCalledWith("ollama", "qwen2.5:7b");
  });

  it("a keyless default that is ready is kept", async () => {
    probeMock.mockResolvedValue({ ok: true, reason: null, detail: null });
    await useLLMProvidersStore.getState().promoteKeyedProvider("openrouter");
    expect(useLLMProvidersStore.getState().defaultProviderId).toBe("ollama");
  });

  it("never replaces a keyed default the user chose", async () => {
    useLLMProvidersStore.setState({ defaultProviderId: "anthropic" });
    probeMock.mockResolvedValue(NOT_RUNNING);
    await expect(useLLMProvidersStore.getState().promoteKeyedProvider("openrouter")).resolves.toBe(
      false,
    );
    expect(useLLMProvidersStore.getState().defaultProviderId).toBe("anthropic");
    expect(probeMock).not.toHaveBeenCalled();
  });
});

describe("orderedProviders (R15-UI-087)", () => {
  it("puts the preference order first and keeps unnamed providers in catalog order", () => {
    const ids = orderedProviders(DEFAULT_PROVIDERS, ["groq", "anthropic"]).map((p) => p.id);
    const rest = DEFAULT_PROVIDERS.map((p) => p.id).filter(
      (id) => id !== "groq" && id !== "anthropic",
    );
    expect(ids).toEqual(["groq", "anthropic", ...rest]);
  });
});
