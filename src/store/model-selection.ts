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
 * Default model per provider — an OFFLINE FALLBACK mirroring the sidecar's
 * config-driven registry (`sidecar/config/model_registry.json`, served live on
 * `GET /llm/providers` as `defaultModel`/`knownModels` into the llm-providers
 * store). Edit the JSON to change models; keep this in lockstep as the no-sidecar
 * fallback. The user can override per provider via the model HUD.
 */
export const DEFAULT_MODEL_BY_PROVIDER: Record<LLMProviderId, string> = {
  anthropic: "claude-opus-4-8",
  openai: "gpt-4.1-mini",
  gemini: "gemini-2.5-pro",
  groq: "llama-3.3-70b-versatile",
  ollama: "qwen2.5:7b",
  deepseek: "deepseek-chat",
  xai: "grok-2-latest",
  openrouter: "openai/gpt-4o-mini",
};

/** A small, curated set of selectable models per provider for the HUD picker —
 *  the OFFLINE FALLBACK for the config-driven list (see above); the live list
 *  comes from the llm-providers store's `knownModels`. Free-form override is also
 *  allowed — the contract keeps model ids as strings (`LLMModelId`) so releases
 *  between Vysted versions still work. */
export const KNOWN_MODELS_BY_PROVIDER: Record<LLMProviderId, readonly string[]> = {
  anthropic: ["claude-opus-4-8", "claude-sonnet-4-6", "claude-haiku-4-5"],
  openai: ["gpt-4.1", "gpt-4.1-mini", "o4-mini"],
  gemini: ["gemini-2.5-pro", "gemini-2.5-flash"],
  groq: ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"],
  ollama: ["qwen2.5:7b", "llama3.1:8b"],
  deepseek: ["deepseek-chat", "deepseek-reasoner"],
  xai: ["grok-2-latest", "grok-2-mini"],
  openrouter: [
    "openai/gpt-4o-mini",
    "anthropic/claude-3.5-sonnet",
    "google/gemini-2.0-flash-001",
    "qwen/qwen3-30b-a3b-thinking-2507",
    "deepseek/deepseek-chat",
    "openrouter/auto",
  ],
};

/** Is `model` one of the curated/known models for `provider`? Free-form picks
 *  via {@link ModelSelectionState.setModel} bypass this (the contract keeps
 *  model ids open strings); it gates only the *restore* path, where a persisted
 *  override that is no longer offered (e.g. a model dropped from the editable
 *  registry, or a then-default captured by an older build) must not shadow the
 *  current default forever. */
export function isKnownModel(provider: LLMProviderId, model: string): boolean {
  const known = KNOWN_MODELS_BY_PROVIDER[provider];
  return Array.isArray(known) && known.includes(model);
}

/** Drop any restored override whose model is not currently offered for that
 *  provider, so a stale persisted id can't shadow the live default (the
 *  `llama3.1:8b` regression). */
function pruneRestoredOverrides(
  raw: Partial<Record<LLMProviderId, string>>,
): Partial<Record<LLMProviderId, string>> {
  const next: Partial<Record<LLMProviderId, string>> = {};
  for (const [provider, model] of Object.entries(raw)) {
    if (typeof model === "string" && isKnownModel(provider as LLMProviderId, model)) {
      next[provider as LLMProviderId] = model;
    }
  }
  return next;
}

/** The effective model id for a provider (override → default → safe dash so an
 *  unknown/custom provider id never renders `provider · undefined`). */
function resolveModel(
  overrides: Partial<Record<LLMProviderId, string>>,
  provider: LLMProviderId,
): string {
  return overrides[provider] ?? DEFAULT_MODEL_BY_PROVIDER[provider] ?? "—";
}

interface ModelSelectionState {
  /** User overrides, keyed by provider id. */
  overrides: Partial<Record<LLMProviderId, string>>;
  setModel: (provider: LLMProviderId, model: string) => void;
  clearModel: (provider: LLMProviderId) => void;
  /** Replace all overrides — used to restore a persisted selection on launch.
   *  Restored overrides are validated against the known-model list (see
   *  {@link pruneRestoredOverrides}); a direct {@link setModel} pick is not. */
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
  setOverrides: (overrides) => set({ overrides: pruneRestoredOverrides(overrides) }),
  modelFor: (provider) => resolveModel(get().overrides, provider),
}));

/** Convenience: the effective model for a provider (non-reactive read). */
export function modelForProvider(provider: LLMProviderId): string {
  return useModelSelectionStore.getState().modelFor(provider);
}

/** Reactive hook: the effective model for a provider. Single read path so any
 *  override validation applies everywhere (HUD + status chrome) — never
 *  re-implement `overrides[p] ?? default` inline. */
export function useModelForProvider(provider: LLMProviderId): string {
  return useModelSelectionStore((state) => resolveModel(state.overrides, provider));
}

/** Test helper: reset the model-selection store. */
export function resetModelSelectionStoreForTests(): void {
  useModelSelectionStore.setState({ overrides: {} });
}
