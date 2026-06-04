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
  /** Config-driven default model (from the sidecar's model_registry.json). */
  defaultModel?: string;
  /** Config-driven curated model list for the HUD/builder dropdowns. */
  knownModels?: string[];
}

/**
 * Default static catalog — an OFFLINE FALLBACK that mirrors the sidecar's
 * `model_registry.json`. The real source of truth is that JSON, served live via
 * `refresh()` → `GET /llm/providers`; this list only renders when the sidecar is
 * unreachable at launch. Keep it in lockstep with the JSON when models change.
 */
export const DEFAULT_PROVIDERS: LLMProviderInfo[] = [
  {
    id: "anthropic",
    label: "Anthropic",
    requiresKey: true,
    defaultModel: "claude-opus-4-8",
    knownModels: ["claude-opus-4-8", "claude-sonnet-4-6", "claude-haiku-4-5"],
  },
  {
    id: "openai",
    label: "OpenAI",
    requiresKey: true,
    defaultModel: "gpt-4.1-mini",
    knownModels: ["gpt-4.1", "gpt-4.1-mini", "o4-mini"],
  },
  {
    id: "gemini",
    label: "Google Gemini",
    requiresKey: true,
    defaultModel: "gemini-2.5-pro",
    knownModels: ["gemini-2.5-pro", "gemini-2.5-flash"],
  },
  {
    id: "groq",
    label: "Groq",
    requiresKey: true,
    defaultModel: "llama-3.3-70b-versatile",
    knownModels: ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"],
  },
  {
    id: "ollama",
    label: "Ollama (local)",
    requiresKey: false,
    defaultBaseUrl: "http://127.0.0.1:11434",
    defaultModel: "qwen2.5:7b",
    knownModels: ["qwen2.5:7b", "llama3.1:8b"],
  },
  {
    id: "deepseek",
    label: "DeepSeek",
    requiresKey: true,
    defaultBaseUrl: "https://api.deepseek.com",
    defaultModel: "deepseek-chat",
    knownModels: ["deepseek-chat", "deepseek-reasoner"],
  },
  {
    id: "xai",
    label: "xAI",
    requiresKey: true,
    defaultBaseUrl: "https://api.x.ai/v1",
    defaultModel: "grok-4",
    knownModels: ["grok-4", "grok-3"],
  },
  {
    id: "openrouter",
    label: "OpenRouter (broker)",
    requiresKey: true,
    defaultBaseUrl: "https://openrouter.ai/api/v1",
    defaultModel: "deepseek/deepseek-v4-flash",
    knownModels: [
      "minimax/minimax-m3",
      "deepseek/deepseek-v4-flash",
      "moonshotai/kimi-k2.6",
      "deepseek/deepseek-v4-pro",
      "qwen/qwen3.7-max",
      "qwen/qwen3.7-plus",
      "z-ai/glm-5.1",
      "qwen/qwen3.6-flash",
      "openrouter/auto",
    ],
  },
];

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
  /** Refresh from the sidecar (no-op fallback to defaults on error). */
  refresh: () => Promise<void>;
}

export const useLLMProvidersStore = create<LLMProvidersState>((set) => ({
  providers: DEFAULT_PROVIDERS,
  defaultProviderId: "ollama",
  setDefaultProviderId: (id) => set({ defaultProviderId: id }),
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
