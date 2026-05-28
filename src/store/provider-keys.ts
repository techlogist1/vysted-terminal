/**
 * Provider key-status store (Phase 9.5 / Track C).
 *
 * Tracks, per BYOK LLM provider, whether an API key is currently stored in the
 * OS keychain — without ever holding the key value in frontend state. The
 * Settings "AI Providers" section and the first-run onboarding banner both read
 * this so the "where do I put my key" surface and the "you have no key yet"
 * prompt stay in sync after a save/remove.
 *
 * Status is derived by probing `getSecret(llm-provider:<id>)` for each provider
 * (null => missing). `refresh()` re-probes; call it after the KeyEntryDialog
 * saves or a key is removed. Outside the Tauri shell `getSecret` rejects, which
 * we treat as "unknown" rather than a hard error.
 */

import { create } from "zustand";

import { getSecret, KEYCHAIN_NAMESPACES } from "@/lib/keychain";
import { DEFAULT_PROVIDERS } from "@/store/llm-providers";
import type { LLMProviderId } from "../../types/ai";

export type KeyStatus = "configured" | "missing" | "unknown";

interface ProviderKeysState {
  /** Per-provider key presence. Absent id => not yet probed. */
  status: Partial<Record<LLMProviderId, KeyStatus>>;
  /** True once the first probe completed (so the onboarding banner can wait). */
  probed: boolean;
  /** Re-probe the keychain for every known provider id. */
  refresh: () => Promise<void>;
  /** Re-probe a single provider (after a save/remove). */
  refreshOne: (id: LLMProviderId) => Promise<void>;
  /** True when no key-requiring provider has a configured key (onboarding gate). */
  hasAnyKey: () => boolean;
}

async function probe(id: LLMProviderId): Promise<KeyStatus> {
  try {
    const value = await getSecret(KEYCHAIN_NAMESPACES.llmProvider(id));
    return value && value.length > 0 ? "configured" : "missing";
  } catch {
    return "unknown";
  }
}

export const useProviderKeysStore = create<ProviderKeysState>((set, get) => ({
  status: {},
  probed: false,
  refresh: async () => {
    const ids = DEFAULT_PROVIDERS.map((p) => p.id);
    const results = await Promise.all(ids.map(async (id) => [id, await probe(id)] as const));
    set({ status: Object.fromEntries(results), probed: true });
  },
  refreshOne: async (id) => {
    const next = await probe(id);
    set((state) => ({ status: { ...state.status, [id]: next } }));
  },
  hasAnyKey: () => {
    const { status } = get();
    // Ollama (no key required) doesn't count toward "has configured an AI key".
    return DEFAULT_PROVIDERS.some((p) => p.requiresKey && status[p.id] === "configured");
  },
}));
