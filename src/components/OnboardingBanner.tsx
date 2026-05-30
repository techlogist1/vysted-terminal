"use client";

import { useEffect, useState } from "react";
import { Sparkles, X } from "lucide-react";

import { useProviderKeysStore } from "@/store/provider-keys";
import { useWorkspaceStore } from "@/store/workspace";

/**
 * First-run onboarding banner (Phase 9.5 / Track C).
 *
 * Makes "where do I put my AI key" obvious: shown whenever no key-requiring LLM
 * provider has a key in the keychain, with a one-click jump to Settings → AI
 * Providers. It is driven by real key state (not a one-shot flag), so it
 * disappears the moment a key is saved and reappears only if every key is
 * removed. Dismissible for the session. No-op (renders null) until the first
 * keychain probe completes, so it never flashes before state is known.
 */
export function OnboardingBanner() {
  const probed = useProviderKeysStore((s) => s.probed);
  const hasAnyKey = useProviderKeysStore((s) => s.hasAnyKey());
  const refresh = useProviderKeysStore((s) => s.refresh);
  const openPanel = useWorkspaceStore((s) => s.openPanel);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  if (!probed || hasAnyKey || dismissed) {
    return null;
  }

  return (
    <div
      role="status"
      className="border-charcoal-800 flex shrink-0 items-center gap-3 border-b border-amber-500/20 bg-gradient-to-r from-amber-500/10 to-transparent px-4 py-2"
    >
      <Sparkles className="size-4 shrink-0 text-amber-400" aria-hidden="true" />
      <p className="text-charcoal-200 min-w-0 flex-1 truncate font-mono text-xs">
        Add a cloud provider key, or run a local model (Ollama) — either unlocks the assistant,
        agents, and research tools. Cloud keys stay in your OS keychain.
      </p>
      <button
        type="button"
        onClick={() => openPanel("settings")}
        className="shrink-0 rounded border border-amber-500/40 bg-amber-500/10 px-2.5 py-1 font-mono text-xs text-amber-300 hover:bg-amber-500/20"
      >
        Set up a provider →
      </button>
      <button
        type="button"
        aria-label="Dismiss"
        onClick={() => setDismissed(true)}
        className="text-charcoal-500 hover:text-charcoal-200 shrink-0 rounded p-1"
      >
        <X className="size-3.5" aria-hidden="true" />
      </button>
    </div>
  );
}
