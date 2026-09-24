/**
 * LLM provider store.
 *
 * Mirrors the seven BYOK providers the sidecar exposes via
 * ``GET /llm/providers``. The chat sidebar reads from here to populate
 * the provider dropdown and to gate model selection; the Key Entry Dialog
 * reads ``requiresKey`` to decide whether to demand a credential.
 *
 * The list is fetched once at app startup (``refresh()``) and cached. Until
 * then (or when the sidecar is unreachable) it is the registry JSON itself, so
 * the dropdown always renders the right set.
 */

import { create } from "zustand";

import { probeReadiness } from "@/lib/provider-validation";
import { sidecarGet } from "@/lib/sidecar-client";
import { modelForProvider, REGISTRY_PROVIDERS } from "@/store/model-selection";
import type { LLMProviderId } from "../../types/ai";

/** One row of provider metadata; mirrors the sidecar Pydantic model. */
export interface LLMProviderInfo {
  id: LLMProviderId;
  label: string;
  /** Whether the user must supply an API key before this provider is usable. */
  requiresKey: boolean;
  /** Default endpoint; Ollama defaults to localhost. */
  defaultBaseUrl?: string;
  /** Config-driven default model (from the sidecar's model_registry.json). */
  defaultModel?: string;
  /** Config-driven curated model list for the HUD/builder dropdowns. */
  knownModels?: string[];
}

/** The provider catalog, projected from `sidecar/config/model_registry.json`
 *  (the same file `GET /llm/providers` serves; `refresh()` replaces it with the
 *  live rows). Never a hand copy (R15-CODE-AGENT-006). */
export const DEFAULT_PROVIDERS: LLMProviderInfo[] = REGISTRY_PROVIDERS.map((row) => ({
  id: row.id,
  label: row.label,
  requiresKey: row.requires_key,
  defaultBaseUrl: row.default_base_url,
  defaultModel: row.default_model,
  knownModels: row.known_models,
}));

interface SidecarProviderRow {
  id: LLMProviderId;
  label: string;
  requires_key: boolean;
  default_base_url?: string | null;
  default_model?: string | null;
  known_models?: string[] | null;
}

interface LLMProvidersState {
  providers: LLMProviderInfo[];
  /** Provider id the chat sidebar uses when the user picks "default". */
  defaultProviderId: LLMProviderId;
  setDefaultProviderId: (id: LLMProviderId) => void;
  /**
   * After a key is saved for `id`, make it the default when the current default
   * is a keyless lane that is not ready (R15-UI-049) — never over a keyed
   * default the user chose. Resolves `true` when the default moved.
   */
  promoteKeyedProvider: (id: LLMProviderId) => Promise<boolean>;
  /** Refresh from the sidecar (no-op fallback to defaults on error). */
  refresh: () => Promise<void>;
}

export const useLLMProvidersStore = create<LLMProvidersState>((set, get) => ({
  providers: DEFAULT_PROVIDERS,
  defaultProviderId: "ollama",
  setDefaultProviderId: (id) => set({ defaultProviderId: id }),
  promoteKeyedProvider: async (id) => {
    const { defaultProviderId, providers } = get();
    const current = providers.find((p) => p.id === defaultProviderId);
    if (id === defaultProviderId || current?.requiresKey !== false) {
      return false;
    }
    const readiness = await probeReadiness(defaultProviderId, modelForProvider(defaultProviderId));
    // Re-read: the user may have picked a default while the probe ran.
    if (readiness.ok || get().defaultProviderId !== defaultProviderId) {
      return false;
    }
    set({ defaultProviderId: id });
    return true;
  },
  refresh: async () => {
    try {
      const rows = await sidecarGet<SidecarProviderRow[]>("/llm/providers");
      const providers: LLMProviderInfo[] = rows.map((row) => ({
        id: row.id,
        label: row.label,
        requiresKey: row.requires_key,
        defaultBaseUrl: row.default_base_url ?? undefined,
        defaultModel: row.default_model ?? undefined,
        knownModels: row.known_models ?? undefined,
      }));
      set({ providers });
    } catch {
      // Stay on the static defaults — the dropdown is never empty.
    }
  },
}));
