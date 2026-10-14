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

import registry from "../../sidecar/config/model_registry.json";
import type { LLMProviderId } from "../../types/ai";

/** One provider row of `sidecar/config/model_registry.json` — the single source
 *  of truth for providers, default models and selectable model lists (the
 *  sidecar serves the same file on `GET /llm/providers`). */
export interface RegistryProviderRow {
  id: LLMProviderId;
  label: string;
  requires_key: boolean;
  default_base_url?: string;
  default_model: string;
  known_models: string[];
}

/** The registry's provider rows, imported (never hand-copied) so a
 *  `default_model` or `known_models` edit reaches the frontend with the sidecar
 *  (R15-CODE-AGENT-006). */
export const REGISTRY_PROVIDERS = registry.providers as RegistryProviderRow[];

/** Default model per provider, projected from the registry. */
export const DEFAULT_MODEL_BY_PROVIDER = Object.fromEntries(
  REGISTRY_PROVIDERS.map((row) => [row.id, row.default_model]),
) as Record<LLMProviderId, string>;

/** Curated selectable models per provider for the HUD picker, projected from
 *  the registry. Free-form override is also allowed — the contract keeps model
 *  ids as strings so releases between Vysted versions work. */
export const KNOWN_MODELS_BY_PROVIDER: Record<LLMProviderId, readonly string[]> =
  Object.fromEntries(REGISTRY_PROVIDERS.map((row) => [row.id, row.known_models])) as Record<
    LLMProviderId,
    string[]
  >;

/** Is `model` one of the curated/known models for `provider`? Free-form picks
 *  via {@link ModelSelectionState.setModel} bypass this (the contract keeps
 *  model ids open strings); it gates only the *restore* path, where a persisted
 *  override that is no longer offered (e.g. a model dropped from the editable
 *  registry, or a then-default captured by an older build) must not shadow the
 *  current default forever. */
export function isKnownModel(provider: LLMProviderId, model: string): boolean {
  // OpenRouter is a BROKER with a live, open-ended catalog (hundreds of models
  // fetched at runtime via `GET /llm/models`), so the static list here is a
  // fallback hint, NOT the set of valid ids. Never prune a restored OpenRouter
  // pick against it — otherwise a model the user chose from the live dropdown is
  // silently dropped to the default on relaunch.
  if (provider === "openrouter") return true;
  const known = KNOWN_MODELS_BY_PROVIDER[provider];
  return Array.isArray(known) && known.includes(model);
}

/** Drop any restored override whose model is not currently offered for that
 *  provider, so a stale persisted id can't shadow the live default (the
 *  `llama3.1:8b` regression). Used only for UNTRUSTED/legacy blobs — a current
 *  blob (see {@link ModelSelectionState.setOverrides} `trusted`) skips this,
 *  because the static known-model list can't see the LIVE catalog and would
 *  silently drop a model the user picked from the live dropdown. */
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

/** Keep every string-valued override as-is (no static-list pruning). The caller
 *  has already vouched for the blob's trust (a current `modelOverridesV`), so a
 *  live-catalog model id the static list can't know about is preserved. */
function sanitizeOverrides(
  raw: Partial<Record<LLMProviderId, string>>,
): Partial<Record<LLMProviderId, string>> {
  const next: Partial<Record<LLMProviderId, string>> = {};
  for (const [provider, model] of Object.entries(raw)) {
    if (typeof model === "string") {
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
   *  An UNTRUSTED restore (legacy blob) is validated against the known-model list
   *  (see {@link pruneRestoredOverrides}); a `trusted` restore (a current
   *  `modelOverridesV` blob) is kept verbatim so a live-catalog pick survives. A
   *  direct {@link setModel} pick is never pruned. */
  setOverrides: (
    overrides: Partial<Record<LLMProviderId, string>>,
    opts?: { trusted?: boolean },
  ) => void;
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
  setOverrides: (overrides, opts) =>
    set({
      overrides: opts?.trusted ? sanitizeOverrides(overrides) : pruneRestoredOverrides(overrides),
    }),
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
