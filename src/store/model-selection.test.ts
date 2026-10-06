import { beforeEach, describe, expect, it, vi } from "vitest";

import registry from "../../sidecar/config/model_registry.json";
import { DEFAULT_PROVIDERS } from "@/store/llm-providers";
import {
  DEFAULT_MODEL_BY_PROVIDER,
  KNOWN_MODELS_BY_PROVIDER,
  modelForProvider,
  resetModelSelectionStoreForTests,
  useModelSelectionStore,
} from "@/store/model-selection";

// R15-CODE-AGENT-006: the three frontend tables are projections of the sidecar's
// model_registry.json, never hand copies (the old guard compared two TS copies).
describe("model-selection — the tables are the registry JSON", () => {
  it("DEFAULT_PROVIDERS / DEFAULT_MODEL_BY_PROVIDER / KNOWN_MODELS_BY_PROVIDER equal its projection", () => {
    expect(DEFAULT_PROVIDERS.map((p) => p.id)).toEqual(registry.providers.map((r) => r.id));
    for (const row of registry.providers) {
      const id = row.id as keyof typeof DEFAULT_MODEL_BY_PROVIDER;
      expect(DEFAULT_MODEL_BY_PROVIDER[id]).toBe(row.default_model);
      expect([...KNOWN_MODELS_BY_PROVIDER[id]]).toEqual(row.known_models);
      expect(DEFAULT_PROVIDERS.find((p) => p.id === id)).toMatchObject({
        label: row.label,
        requiresKey: row.requires_key,
        defaultModel: row.default_model,
        knownModels: row.known_models,
      });
    }
  });

  it("a registry default_model edit is the new default with no override, and a JSON-only model survives restore", async () => {
    const edited = structuredClone(registry);
    const ollama = edited.providers.find((r) => r.id === "ollama")!;
    ollama.default_model = "qwen3:8b";
    ollama.known_models = [...ollama.known_models, "qwen3:8b"];
    vi.resetModules();
    vi.doMock("../../sidecar/config/model_registry.json", () => ({ default: edited }));
    try {
      const fresh = await import("@/store/model-selection");
      expect(fresh.modelForProvider("ollama")).toBe("qwen3:8b");
      fresh.useModelSelectionStore.getState().setOverrides({ ollama: "qwen3:8b" });
      expect(fresh.useModelSelectionStore.getState().overrides).toEqual({ ollama: "qwen3:8b" });
    } finally {
      vi.doUnmock("../../sidecar/config/model_registry.json");
      vi.resetModules();
    }
  });
});

describe("model-selection store (FR-004)", () => {
  beforeEach(() => resetModelSelectionStoreForTests());

  it("returns the per-provider default when no override is set", () => {
    expect(useModelSelectionStore.getState().modelFor("anthropic")).toBe(
      DEFAULT_MODEL_BY_PROVIDER.anthropic,
    );
    expect(modelForProvider("openai")).toBe(DEFAULT_MODEL_BY_PROVIDER.openai);
  });

  it("applies and clears a per-provider override", () => {
    useModelSelectionStore.getState().setModel("anthropic", "claude-sonnet-4-6");
    expect(useModelSelectionStore.getState().modelFor("anthropic")).toBe("claude-sonnet-4-6");
    useModelSelectionStore.getState().clearModel("anthropic");
    expect(useModelSelectionStore.getState().modelFor("anthropic")).toBe(
      DEFAULT_MODEL_BY_PROVIDER.anthropic,
    );
  });

  it("setOverrides replaces the whole map (workspace restore)", () => {
    useModelSelectionStore.getState().setModel("openai", "gpt-4.1");
    useModelSelectionStore.getState().setOverrides({ gemini: "gemini-2.5-flash" });
    expect(useModelSelectionStore.getState().overrides).toEqual({ gemini: "gemini-2.5-flash" });
    expect(useModelSelectionStore.getState().modelFor("openai")).toBe(
      DEFAULT_MODEL_BY_PROVIDER.openai,
    );
  });

  it("untrusted setOverrides prunes a model not in the static known list", () => {
    // A model id the static KNOWN_MODELS_BY_PROVIDER list does not contain — an
    // untrusted (legacy) restore drops it so a stale id can't shadow the default.
    useModelSelectionStore.getState().setOverrides({ openai: "gpt-5-pro-2026" });
    expect(useModelSelectionStore.getState().overrides.openai).toBeUndefined();
  });

  it("trusted setOverrides keeps a live-catalog model the static list can't know", () => {
    // The persistence bug: a model the user picked from the LIVE catalog (not in
    // the static fallback) was pruned on restore. A current blob restores trusted,
    // so it survives.
    useModelSelectionStore.getState().setOverrides({ openai: "gpt-5-pro-2026" }, { trusted: true });
    expect(useModelSelectionStore.getState().modelFor("openai")).toBe("gpt-5-pro-2026");
  });
});
