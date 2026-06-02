import { beforeEach, describe, expect, it } from "vitest";

import {
  DEFAULT_MODEL_BY_PROVIDER,
  modelForProvider,
  resetModelSelectionStoreForTests,
  useModelSelectionStore,
} from "@/store/model-selection";

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
