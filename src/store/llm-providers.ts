/**
 * LLM provider store.
 *
 * Mirrors the seven BYOK providers the sidecar exposes via
 * ``GET /llm/providers``. The chat sidebar reads from here to populate
 * the provider dropdown and to gate model selection; the Key Entry Dialog
 * reads ``requiresKey`` to decide whether to demand a credential.
 *
 * The list is fetched once at app startup (``refresh()``) and cached.
 * Phase 3 ships the list statically too — it matches the sidecar's
 * ``PROVIDER_INFO`` tuple — so even if the sidecar is unreachable the
 * dropdown still renders the right set.
 */

import { create } from "zustand";

import { sidecarGet } from "@/lib/sidecar-client";
import type { LLMProviderId } from "../../types/ai";

/** One row of provider metadata; mirrors the sidecar Pydantic model. */
export interface LLMProviderInfo {
  id: LLMProviderId;
  label: string;
  /** Whether the user must supply an API key before this provider is usable. */
  requiresKey: boolean;
  /** Default endpoint; Ollama defaults to localhost. */
  defaultBaseUrl?: string;
}

/** Default static catalog — matches ``services/llm/__init__.PROVIDER_INFO``. */
export const DEFAULT_PROVIDERS: LLMProviderInfo[] = [
  { id: "anthropic", label: "Anthropic", requiresKey: true },
  { id: "openai", label: "OpenAI", requiresKey: true },
  { id: "gemini", label: "Google Gemini", requiresKey: true },
  { id: "groq", label: "Groq", requiresKey: true },
  {
    id: "ollama",
    label: "Ollama (local)",
    requiresKey: false,
    defaultBaseUrl: "http://127.0.0.1:11434",
  },
  {
    id: "deepseek",
    label: "DeepSeek",
    requiresKey: true,
    defaultBaseUrl: "https://api.deepseek.com",
  },
  {
    id: "xai",
    label: "xAI",
    requiresKey: true,
    defaultBaseUrl: "https://api.x.ai/v1",
  },
];

interface SidecarProviderRow {
  id: LLMProviderId;
  label: string;
  requires_key: boolean;
  default_base_url?: string | null;
}

interface LLMProvidersState {
  providers: LLMProviderInfo[];
  /** Provider id the chat sidebar uses when the user picks "default". */
  defaultProviderId: LLMProviderId;
  setDefaultProviderId: (id: LLMProviderId) => void;
  /** Refresh from the sidecar (no-op fallback to defaults on error). */
  refresh: () => Promise<void>;
}

export const useLLMProvidersStore = create<LLMProvidersState>((set) => ({
  providers: DEFAULT_PROVIDERS,
  defaultProviderId: "anthropic",
  setDefaultProviderId: (id) => set({ defaultProviderId: id }),
  refresh: async () => {
    try {
      const rows = await sidecarGet<SidecarProviderRow[]>("/llm/providers");
      const providers: LLMProviderInfo[] = rows.map((row) => ({
        id: row.id,
        label: row.label,
        requiresKey: row.requires_key,
        defaultBaseUrl: row.default_base_url ?? undefined,
      }));
      set({ providers });
    } catch {
      // Stay on the static defaults — the dropdown is never empty.
    }
  },
}));
