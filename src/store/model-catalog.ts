/**
 * Live model-catalog store.
 *
 * Fetches a provider's LIVE model list from the sidecar's `GET /llm/models`
 * (which queries the provider's own catalog API) and caches it per provider with
 * a TTL. This replaces the stale hardcoded `known_models` in the dropdowns: the
 * picker now reflects what the provider actually serves today — and for an agent
 * that drives tools, which models are tool-calling capable.
 *
 * BYOK: the key is read from the OS keychain here and sent to the sidecar as the
 * `X-LLM-Key` header (the read-only secret-in-a-header pattern) so OpenRouter can
 * narrow to the caller's account-routable models. Without a key the sidecar still
 * serves the public catalog, so the dropdown is live even before a key is set.
 */

import { useEffect } from "react";
import { create } from "zustand";

import { getSecret, KEYCHAIN_NAMESPACES } from "@/lib/keychain";
import { sidecarGet } from "@/lib/sidecar-client";
import { useLLMProvidersStore } from "@/store/llm-providers";
import type { LLMModelOption, LLMProviderId } from "../../types/ai";

/** Cache lifetime — model catalogs change on the order of days, not seconds. */
const CATALOG_TTL_MS = 30 * 60 * 1000;

/** One provider's cached catalog state. */
export interface CatalogEntry {
  models: LLMModelOption[];
  source: "live" | "fallback";
  note?: string | null;
  fetchedAt: number;
  loading: boolean;
  error?: string;
}

/** Raw sidecar `LLMModelCatalog` row (snake_case wire shape). */
interface SidecarCatalogRow {
  provider: LLMProviderId;
  models: {
    id: string;
    label: string;
    context_length?: number | null;
    supports_tools?: boolean | null;
    pricing?: string | null;
  }[];
  source: "live" | "fallback";
  note?: string | null;
}

interface ModelCatalogState {
  byProvider: Partial<Record<LLMProviderId, CatalogEntry>>;
  /** Fetch (and cache) the catalog for a provider; no-op if fresh unless forced. */
  fetchCatalog: (provider: LLMProviderId, opts?: { force?: boolean }) => Promise<void>;
}

export const useModelCatalogStore = create<ModelCatalogState>((set, get) => ({
  byProvider: {},
  fetchCatalog: async (provider, opts) => {
    const existing = get().byProvider[provider];
    const fresh = existing && Date.now() - existing.fetchedAt < CATALOG_TTL_MS;
    // A forced refresh always proceeds — even past a stuck `loading` (e.g. a
    // prior fetch orphaned when the webview suspended) so the refresh control can
    // always recover. Non-forced calls dedupe against an in-flight or fresh fetch.
    if (existing?.loading && !opts?.force) return;
    if (fresh && !opts?.force) return;

    // Keep any prior models visible while refreshing (no empty flicker).
    set((state) => ({
      byProvider: {
        ...state.byProvider,
        [provider]: {
          models: existing?.models ?? [],
          source: existing?.source ?? "fallback",
          note: existing?.note,
          fetchedAt: existing?.fetchedAt ?? 0,
          loading: true,
        },
      },
    }));

    // The key is optional — a keyless call still returns the public catalog.
    let key: string | null = null;
    try {
      key = await getSecret(KEYCHAIN_NAMESPACES.llmProvider(provider));
    } catch {
      key = null;
    }
    const info = useLLMProvidersStore.getState().providers.find((p) => p.id === provider);

    try {
      const row = await sidecarGet<SidecarCatalogRow>(
        "/llm/models",
        { provider, base_url: info?.defaultBaseUrl },
        key ? { "X-LLM-Key": key } : undefined,
      );
      const models: LLMModelOption[] = (row.models ?? []).map((m) => ({
        id: m.id,
        label: m.label,
        contextLength: m.context_length ?? null,
        supportsTools: m.supports_tools ?? null,
        pricing: m.pricing ?? null,
      }));
      set((state) => ({
        byProvider: {
          ...state.byProvider,
          [provider]: {
            models,
            source: row.source,
            note: row.note ?? null,
            fetchedAt: Date.now(),
            loading: false,
          },
        },
      }));
    } catch (err) {
      const prior = get().byProvider[provider];
      set((state) => ({
        byProvider: {
          ...state.byProvider,
          [provider]: {
            models: prior?.models ?? [],
            source: prior?.source ?? "fallback",
            note: prior?.note,
            fetchedAt: Date.now(),
            loading: false,
            error: err instanceof Error ? err.message : "model list unavailable",
          },
        },
      }));
    }
  },
}));

/**
 * Reactive hook: a provider's catalog entry, auto-fetched (once, then on TTL
 * expiry) when the provider changes. Returns the entry plus a `refresh` that
 * forces a re-fetch (e.g. after the user saves a new key).
 */
export function useModelCatalog(provider: LLMProviderId): {
  entry: CatalogEntry | undefined;
  refresh: () => void;
} {
  const entry = useModelCatalogStore((state) => state.byProvider[provider]);
  const fetchCatalog = useModelCatalogStore((state) => state.fetchCatalog);
  useEffect(() => {
    void fetchCatalog(provider);
  }, [provider, fetchCatalog]);
  return { entry, refresh: () => void fetchCatalog(provider, { force: true }) };
}

/** Test helper: clear the cached catalogs. */
export function resetModelCatalogStoreForTests(): void {
  useModelCatalogStore.setState({ byProvider: {} });
}
