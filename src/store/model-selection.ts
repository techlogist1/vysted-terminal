/**
 * Model-selection store — the active model per provider (FR-004).
 *
 * The agent surface shows the active provider AND model and lets the user switch
 * both by keyboard. Provider selection lives in `llm-providers`; the chosen model
 * per provider lives here. An agent's own `defaultModel` still wins when the call
 * targets that agent; this store holds the user's per-provider override for the
 * raw-chat / default path and surfaces the current model in the HUD. Overrides
 * ride the workspace blob so a relaunch restores the user's model choices.
 */

import { create } from "zustand";

import type { LLMProviderId } from "../../types/ai";

/**
 * Default model per provider — mirrors the sidecar's per-provider fallback
 * table. The user can override per provider via the model HUD.
 */
export const DEFAULT_MODEL_BY_PROVIDER: Record<LLMProviderId, string> = {
  anthropic: "claude-opus-4-7",
  openai: "gpt-4.1-mini",
  gemini: "gemini-2.5-pro",
  groq: "llama-3.3-70b-versatile",
  ollama: "qwen2.5:7b",
  deepseek: "deepseek-chat",
  xai: "grok-2-latest",
};

/** A small, curated set of selectable models per provider for the HUD picker.
 *  Free-form override is also allowed — the contract keeps model ids as strings
 *  (`LLMModelId`) so releases between Vysted versions still work. */
export const KNOWN_MODELS_BY_PROVIDER: Record<LLMProviderId, readonly string[]> = {
  anthropic: ["claude-opus-4-7", "claude-sonnet-4-5", "claude-haiku-4-5"],
  openai: ["gpt-4.1", "gpt-4.1-mini", "o4-mini"],
  gemini: ["gemini-2.5-pro", "gemini-2.5-flash"],
  groq: ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"],
  ollama: ["qwen2.5:7b", "llama3.1:8b"],
  deepseek: ["deepseek-chat", "deepseek-reasoner"],
  xai: ["grok-2-latest", "grok-2-mini"],
};

interface ModelSelectionState {
  /** User overrides, keyed by provider id. */
  overrides: Partial<Record<LLMProviderId, string>>;
  setModel: (provider: LLMProviderId, model: string) => void;
  clearModel: (provider: LLMProviderId) => void;
  /** Replace all overrides — used to restore a persisted selection on launch. */
  setOverrides: (overrides: Partial<Record<LLMProviderId, string>>) => void;
  /** The effective model id for a provider (override → default). */
  modelFor: (provider: LLMProviderId) => string;
}

export const useModelSelectionStore = create<ModelSelectionState>((set, get) => ({
  overrides: {},
  setModel: (provider, model) =>
    set((state) => ({ overrides: { ...state.overrides, [provider]: model } })),
  clearModel: (provider) =>
    set((state) => {
      const next = { ...state.overrides };
      delete next[provider];
      return { overrides: next };
    }),
  setOverrides: (overrides) => set({ overrides: { ...overrides } }),
  modelFor: (provider) => get().overrides[provider] ?? DEFAULT_MODEL_BY_PROVIDER[provider],
}));

/** Convenience: the effective model for a provider (non-reactive read). */
export function modelForProvider(provider: LLMProviderId): string {
  return useModelSelectionStore.getState().modelFor(provider);
}

/** Test helper: reset the model-selection store. */
export function resetModelSelectionStoreForTests(): void {
  useModelSelectionStore.setState({ overrides: {} });
}
